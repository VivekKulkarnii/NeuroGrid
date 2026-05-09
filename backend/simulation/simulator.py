"""
Main asyncio simulation loop with MQTT publishing.
Runs the smart grid simulation and publishes device data to MQTT topics.
"""

import asyncio
import json
import time
import logging
from typing import Optional

import paho.mqtt.client as mqtt

from .devices import SolarPanel, House, EVCharger, BatteryBank
from .price_model import PriceModel
from . import config

logger = logging.getLogger(__name__)


class GridSimulator:
    """
    Async simulation engine that drives all devices and publishes state via MQTT.

    MQTT Topics published:
        grid/solar          - Total solar output + per-panel data
        grid/houses         - Total house load + per-house data
        grid/ev             - Total EV load + per-charger data
        grid/battery        - Battery SOC and status
        grid/price          - Current electricity pricing
        grid/state          - Full aggregated grid state
        grid/metrics        - Running cost and blackout metrics
    """

    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    TICK_INTERVAL = config.TICK_INTERVAL        # seconds between simulation steps
    TIME_ACCELERATION = config.TIME_ACCELERATION  # 1 real second = 120 simulated seconds

    def __init__(self, num_houses=config.NUM_HOUSES, num_solar=config.NUM_SOLAR, num_ev=config.NUM_EV,
                 mqtt_broker="localhost", mqtt_port=1883):
        self.num_houses = num_houses
        self.num_solar = num_solar
        self.num_ev = num_ev

        self.MQTT_BROKER = mqtt_broker
        self.MQTT_PORT = mqtt_port

        # Create devices
        self.solar_panels = [
            SolarPanel(panel_id=f"solar_{i}", rated_capacity_kw=4.0 + i * 0.5)
            for i in range(num_solar)
        ]
        self.houses = [
            House(house_id=f"house_{i}", base_load_kw=0.3 + i * 0.1,
                  max_load_kw=3.0 + i * 0.5, occupants=2 + (i % 4))
            for i in range(num_houses)
        ]
        self.ev_chargers = [
            EVCharger(charger_id=f"ev_{i}") for i in range(num_ev)
        ]
        self.battery = BatteryBank()
        self.price_model = PriceModel()

        # Simulation state
        self.hour_of_day = 6.0  # Start at 6 AM
        self.step_count = 0
        self.total_cost = 0.0
        self.blackout_count = 0
        self.running = False
        self.scenario = "baseline"  # baseline | ai | stress

        # MQTT client
        self.mqtt_client: Optional[mqtt.Client] = None

        # Action buffer (written by AI agent or rule-based controller)
        self.pending_battery_action = 0.0  # -1 to 1
        self.pending_ev_throttle = 1.0     # 0 to 1

    def _setup_mqtt(self):
        """Initialize MQTT client connection."""
        try:
            self.mqtt_client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="grid_simulator"
            )
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.connect(self.MQTT_BROKER, self.MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            logger.info(f"MQTT connected to {self.MQTT_BROKER}:{self.MQTT_PORT}")
        except Exception as e:
            logger.warning(f"MQTT connection failed: {e}. Running without MQTT.")
            self.mqtt_client = None

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        logger.info(f"MQTT connected with result code {rc}")
        # Subscribe to action topics (from AI agent)
        client.subscribe("grid/action/#")
        client.message_callback_add("grid/action/battery", self._on_battery_action)
        client.message_callback_add("grid/action/ev_throttle", self._on_ev_throttle)
        client.message_callback_add("grid/action/scenario", self._on_scenario_change)

    def _on_battery_action(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            self.pending_battery_action = max(-1.0, min(1.0, float(data["action"])))
        except Exception as e:
            logger.error(f"Bad battery action: {e}")

    def _on_ev_throttle(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            self.pending_ev_throttle = max(0.0, min(1.0, float(data["throttle"])))
        except Exception as e:
            logger.error(f"Bad EV throttle: {e}")

    def _on_scenario_change(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            new_scenario = data.get("scenario", "baseline")
            if new_scenario in ("baseline", "ai", "stress"):
                self.scenario = new_scenario
                logger.info(f"Scenario changed to: {self.scenario}")
                if new_scenario == "stress":
                    self.price_model.set_stress_mode(True)
                    for panel in self.solar_panels:
                        panel.cloud_cover = 0.8
                else:
                    self.price_model.set_stress_mode(False)
                    for panel in self.solar_panels:
                        panel.cloud_cover = 0.0
        except Exception as e:
            logger.error(f"Bad scenario change: {e}")

    def _publish(self, topic: str, data: dict):
        """Publish JSON data to MQTT topic."""
        if self.mqtt_client:
            try:
                self.mqtt_client.publish(topic, json.dumps(data), qos=0)
            except Exception as e:
                logger.error(f"MQTT publish error on {topic}: {e}")

    def _apply_actions(self):
        """Apply pending actions from AI/rule-based controller."""
        # Apply EV throttle
        for ev in self.ev_chargers:
            ev.set_throttle(self.pending_ev_throttle)

        # Apply battery action
        battery_power = 0.0
        if self.pending_battery_action > 0:
            charge_kw = self.pending_battery_action * self.battery.max_charge_rate_kw
            battery_power = -self.battery.charge(charge_kw, self.TICK_INTERVAL)
        elif self.pending_battery_action < 0:
            discharge_kw = abs(self.pending_battery_action) * self.battery.max_discharge_rate_kw
            battery_power = self.battery.discharge(discharge_kw, self.TICK_INTERVAL)

        return battery_power

    def _compute_step(self):
        """Run one simulation tick and return state dict."""
        # Get device readings
        solar_output = sum(p.get_output(self.hour_of_day) for p in self.solar_panels)
        house_load = sum(h.get_load(self.hour_of_day) for h in self.houses)
        ev_load = sum(ev.get_load(self.hour_of_day) for ev in self.ev_chargers)

        # Apply control actions
        battery_power = self._apply_actions()

        total_demand = house_load + ev_load
        net_import = total_demand - solar_output - battery_power

        # Pricing
        import_price = self.price_model.get_price(self.hour_of_day)
        export_price = self.price_model.get_export_price(self.hour_of_day)
        step_hours = self.TICK_INTERVAL / 3600.0

        if net_import > 0:
            step_cost = net_import * import_price * step_hours
        else:
            step_cost = net_import * export_price * step_hours
        self.total_cost += step_cost

        # Blackout check
        is_blackout = net_import > 30.0
        if is_blackout:
            self.blackout_count += 1

        state = {
            "timestamp": self.step_count,
            "hour_of_day": round(self.hour_of_day, 2),
            "scenario": self.scenario,
            "solar": {
                "total_kw": round(solar_output, 3),
                "panels": [{"id": p.panel_id, "output_kw": round(p.get_output(self.hour_of_day), 3),
                            "cloud_cover": p.cloud_cover} for p in self.solar_panels],
            },
            "houses": {
                "total_kw": round(house_load, 3),
                "units": [{"id": h.house_id, "load_kw": round(h.get_load(self.hour_of_day), 3)}
                          for h in self.houses],
            },
            "ev_chargers": {
                "total_kw": round(ev_load, 3),
                "units": [{"id": ev.charger_id, "load_kw": round(ev.get_load(self.hour_of_day), 3),
                           "connected": ev.is_connected, "soc": round(ev.battery_soc, 3),
                           "throttle": ev.current_throttle} for ev in self.ev_chargers],
            },
            "battery": self.battery.get_status(),
            "battery_action": round(self.pending_battery_action, 3),
            "price": {
                "import_rate": round(import_price, 4),
                "export_rate": round(export_price, 4),
                "tier": self.price_model._get_tier_name(self.hour_of_day),
            },
            "grid": {
                "net_import_kw": round(net_import, 3),
                "total_demand_kw": round(total_demand, 3),
                "total_supply_kw": round(solar_output, 3),
                "battery_power_kw": round(battery_power, 3),
                "blackout": is_blackout,
            },
            "metrics": {
                "total_cost": round(self.total_cost, 4),
                "step_cost": round(step_cost, 6),
                "blackout_count": self.blackout_count,
            },
        }

        # Publish to individual MQTT topics
        self._publish("grid/solar", state["solar"])
        self._publish("grid/houses", state["houses"])
        self._publish("grid/ev", state["ev_chargers"])
        self._publish("grid/battery", state["battery"])
        self._publish("grid/price", state["price"])
        self._publish("grid/metrics", state["metrics"])
        self._publish("grid/state", state)

        return state

    async def run(self):
        """Standalone async simulation loop (alternative to main.py loop)."""
        self._setup_mqtt()
        self.running = True
        logger.info("Grid simulation started")

        try:
            while self.running:
                state = self._compute_step()

                # Advance time
                self.step_count += 1
                time_delta = self.TICK_INTERVAL * self.TIME_ACCELERATION / 3600.0
                self.hour_of_day = (self.hour_of_day + time_delta) % 24.0

                if self.step_count % 50 == 0:
                    logger.info(
                        f"Step {self.step_count} | "
                        f"Hour: {self.hour_of_day:.1f} | "
                        f"Solar: {state['solar']['total_kw']:.1f}kW | "
                        f"Load: {state['grid']['total_demand_kw']:.1f}kW | "
                        f"Battery: {state['battery']['soc']:.1%} | "
                        f"Cost: ${self.total_cost:.2f}"
                    )

                await asyncio.sleep(self.TICK_INTERVAL)
        finally:
            self.running = False
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            logger.info("Grid simulation stopped")

    def stop(self):
        self.running = False

    def get_current_state(self):
        """Get current state without advancing simulation (for API)."""
        return self._compute_step()
