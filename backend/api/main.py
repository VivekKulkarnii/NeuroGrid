"""
FastAPI backend with WebSocket streaming for the smart grid dashboard.
Runs the simulation loop and streams state to connected clients.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import List, Optional
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.simulator import GridSimulator
from simulation.price_model import PriceModel
from ai.rule_based import RuleBasedController
from ai.rl_agent import RLAgent
from api.database import init_db, save_snapshot, save_action, get_recent_snapshots, get_recent_actions, get_scenario_comparison

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Global state ---
simulator: Optional[GridSimulator] = None
rule_controller = RuleBasedController()
rl_agent = RLAgent()
connected_clients: List[WebSocket] = []
simulation_task: Optional[asyncio.Task] = None
current_scenario = "baseline"
simulation_paused = False
state_history: list = []  # In-memory ring buffer for quick access
MAX_HISTORY = 500


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global simulator, simulation_task

    # Initialize database
    init_db()

    # Try to load trained RL model
    rl_agent.load_model()

    # Create simulator (MQTT integration)
    simulator = GridSimulator(
        num_houses=6, num_solar=4, num_ev=3,
        mqtt_broker="localhost", mqtt_port=1883
    )
    simulator._setup_mqtt()

    # Start simulation loop
    simulation_task = asyncio.create_task(simulation_loop())
    logger.info("Smart Grid backend started")

    yield

    # Shutdown
    if simulator and simulator.mqtt_client:
        simulator.mqtt_client.loop_stop()
        simulator.mqtt_client.disconnect()
    if simulation_task:
        simulation_task.cancel()
    logger.info("Smart Grid backend stopped")


app = FastAPI(
    title="Smart Grid IoT Dashboard API",
    description="Real-time smart neighbourhood power grid simulation with AI optimization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Simulation Loop ---

async def simulation_loop():
    """Main simulation loop that ticks every 2 seconds."""
    global simulator, current_scenario, state_history, simulation_paused

    if not simulator:
        return

    logger.info("Simulation loop started")
    step = 0

    while True:
        try:
            # If paused, just sleep and continue
            if simulation_paused:
                await asyncio.sleep(0.5)
                continue

            # Get current grid state
            state = simulator._compute_step()
            state["scenario"] = current_scenario
            state["paused"] = simulation_paused

            # Run controller based on scenario
            action = None
            if current_scenario == "baseline":
                action = rule_controller.decide(state)
            elif current_scenario in ("ai", "stress"):
                action = rl_agent.decide(state)

            # Apply actions to simulator
            if action:
                simulator.pending_battery_action = action["battery_action"]
                simulator.pending_ev_throttle = action["ev_throttle"]
                state["ai_action"] = action

            # Advance simulation time
            simulator.step_count += 1
            time_delta = simulator.TICK_INTERVAL * simulator.TIME_ACCELERATION / 3600.0
            simulator.hour_of_day = (simulator.hour_of_day + time_delta) % 24.0

            # Store in history
            state_history.append(state)
            if len(state_history) > MAX_HISTORY:
                state_history = state_history[-MAX_HISTORY:]

            # Save to database (every 5th step to reduce I/O)
            if step % 5 == 0:
                save_snapshot(state, action)
                if action:
                    save_action(step, action)

            # Broadcast to all connected WebSocket clients
            await broadcast_state(state)

            step += 1
            await asyncio.sleep(simulator.TICK_INTERVAL)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Simulation error: {e}", exc_info=True)
            await asyncio.sleep(1)


async def broadcast_state(state: dict):
    """Send state to all connected WebSocket clients."""
    if not connected_clients:
        return

    message = json.dumps(state, default=str)
    disconnected = []

    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        connected_clients.remove(ws)


# --- WebSocket Endpoint ---

@app.websocket("/ws/grid")
async def websocket_grid(websocket: WebSocket):
    """
    WebSocket endpoint for real-time grid state streaming.
    Also accepts commands from the frontend (scenario changes, stress events).
    """
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"Client connected. Total: {len(connected_clients)}")

    # Send recent history on connect
    try:
        if state_history:
            await websocket.send_text(json.dumps({
                "type": "history",
                "data": state_history[-100:]
            }, default=str))
    except Exception:
        pass

    try:
        while True:
            # Listen for commands from frontend
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                await handle_ws_command(cmd)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(connected_clients)}")


async def handle_ws_command(cmd: dict):
    """Handle commands sent via WebSocket."""
    global current_scenario, simulator, simulation_paused

    action = cmd.get("action")

    if action == "set_scenario":
        new_scenario = cmd.get("scenario", "baseline")
        if new_scenario in ("baseline", "ai", "stress"):
            current_scenario = new_scenario
            logger.info(f"Scenario changed to: {current_scenario}")

            if new_scenario == "stress" and simulator:
                simulator.price_model.set_stress_mode(True)
                for panel in simulator.solar_panels:
                    panel.cloud_cover = 0.85
                # Force some EVs to connect
                for ev in simulator.ev_chargers:
                    ev.is_connected = True
                    ev.battery_soc = 0.3
            else:
                if simulator:
                    simulator.price_model.set_stress_mode(False)
                    for panel in simulator.solar_panels:
                        panel.cloud_cover = 0.0

            # Broadcast scenario change
            await broadcast_state({
                "type": "scenario_change",
                "scenario": current_scenario
            })

    elif action == "inject_event":
        event_type = cmd.get("event_type", "cloud_cover")
        intensity = cmd.get("intensity", 1.0)

        if simulator:
            if event_type == "cloud_cover":
                for panel in simulator.solar_panels:
                    panel.cloud_cover = intensity * 0.95
                logger.info(f"Injected cloud cover: {intensity:.0%}")

            elif event_type == "ev_surge":
                for ev in simulator.ev_chargers:
                    ev.is_connected = True
                    ev.battery_soc = 0.2
                    ev.current_throttle = 1.0
                logger.info("Injected EV surge")

            elif event_type == "price_spike":
                simulator.price_model.stress_multiplier = 1.0 + intensity * 2.0
                logger.info(f"Injected price spike: {simulator.price_model.stress_multiplier}x")

    elif action == "pause":
        simulation_paused = True
        logger.info("Simulation paused")
        await broadcast_state({"type": "pause_state", "paused": True})

    elif action == "resume":
        simulation_paused = False
        logger.info("Simulation resumed")
        await broadcast_state({"type": "pause_state", "paused": False})

    elif action == "reset":
        if simulator:
            simulator.hour_of_day = 6.0
            simulator.step_count = 0
            simulator.total_cost = 0.0
            simulator.blackout_count = 0
            simulator.battery.current_soc = 0.5
            simulator.price_model.set_stress_mode(False)
            for panel in simulator.solar_panels:
                panel.cloud_cover = 0.0
            current_scenario = "baseline"
            simulation_paused = False
            state_history.clear()
            logger.info("Simulation reset")


# --- REST Endpoints ---

@app.get("/")
async def root():
    return {"status": "running", "project": "Smart Grid IoT Dashboard"}


@app.get("/api/state")
async def get_current_state():
    """Get current grid state."""
    if simulator:
        return simulator.get_current_state()
    raise HTTPException(status_code=503, detail="Simulator not running")


@app.get("/api/history")
async def get_history(limit: int = 200, scenario: Optional[str] = None):
    """Get historical grid snapshots."""
    return get_recent_snapshots(limit, scenario)


@app.get("/api/actions")
async def get_actions(limit: int = 50):
    """Get recent AI action log."""
    if current_scenario == "ai" or current_scenario == "stress":
        return rl_agent.action_log[-limit:]
    return rule_controller.action_log[-limit:]


@app.get("/api/comparison")
async def get_comparison():
    """Get scenario comparison metrics."""
    return get_scenario_comparison()


@app.get("/api/price-forecast")
async def get_price_forecast():
    """Get 24-hour price forecast."""
    if simulator:
        return simulator.price_model.get_price_forecast(simulator.hour_of_day)
    return []


@app.post("/api/scenario/{scenario}")
async def set_scenario(scenario: str):
    """Change active scenario."""
    global current_scenario

    if scenario not in ("baseline", "ai", "stress"):
        raise HTTPException(400, "Invalid scenario. Use: baseline, ai, stress")

    cmd = {"action": "set_scenario", "scenario": scenario}
    await handle_ws_command(cmd)
    return {"scenario": current_scenario}


@app.post("/api/inject/{event_type}")
async def inject_event(event_type: str, intensity: float = 1.0):
    """Inject a stress event."""
    if event_type not in ("cloud_cover", "ev_surge", "price_spike"):
        raise HTTPException(400, "Invalid event. Use: cloud_cover, ev_surge, price_spike")

    cmd = {"action": "inject_event", "event_type": event_type, "intensity": intensity}
    await handle_ws_command(cmd)
    return {"event": event_type, "intensity": intensity}


@app.post("/api/reset")
async def reset_simulation():
    """Reset simulation to initial state."""
    await handle_ws_command({"action": "reset"})
    return {"status": "reset"}


@app.post("/api/pause")
async def pause_simulation():
    """Pause or resume simulation."""
    global simulation_paused
    simulation_paused = not simulation_paused
    state = "paused" if simulation_paused else "running"
    await broadcast_state({"type": "pause_state", "paused": simulation_paused})
    return {"status": state, "paused": simulation_paused}


if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
