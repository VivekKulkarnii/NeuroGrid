"""
RL Agent for smart grid energy management.
Uses PPO from stable-baselines3 for training, with a lightweight
inference mode for real-time control.
"""

import os
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import stable-baselines3, fall back gracefully
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    logger.warning("stable-baselines3 not installed. RL training disabled.")


class RLAgent:
    """
    Reinforcement Learning agent for grid energy management.
    
    Uses PPO (Proximal Policy Optimization) to learn:
    - When to charge/discharge the community battery
    - How to throttle EV charging
    
    What the agent discovers on its own:
    - Charge battery at noon (peak solar, low price)
    - Discharge at 7 PM (peak demand, high price)
    - Delay EV charging to late night (cheap rate)
    """

    MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
    MODEL_PATH = os.path.join(MODEL_DIR, "ppo_smart_grid")

    def __init__(self):
        self.name = "rl_agent"
        self.model: Optional[object] = None
        self.action_log = []
        self._loaded = False

    def load_model(self) -> bool:
        """Load a pre-trained model from disk."""
        if not SB3_AVAILABLE:
            logger.error("stable-baselines3 not available")
            return False

        model_file = self.MODEL_PATH + ".zip"
        if os.path.exists(model_file):
            try:
                self.model = PPO.load(self.MODEL_PATH)
                self._loaded = True
                logger.info(f"Loaded RL model from {model_file}")
                return True
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return False
        else:
            logger.warning(f"No trained model found at {model_file}")
            return False

    def decide(self, state: dict) -> dict:
        """
        Make a control decision using the trained RL model.
        Falls back to a smart heuristic if no model is loaded.
        
        Args:
            state: Grid state dict from simulator
            
        Returns:
            dict with battery_action, ev_throttle, reason
        """
        if self._loaded and self.model is not None:
            return self._decide_rl(state)
        else:
            return self._decide_heuristic(state)

    def _decide_rl(self, state: dict) -> dict:
        """Use the trained PPO model for inference."""
        obs = self._state_to_observation(state)
        action, _ = self.model.predict(obs, deterministic=True)

        battery_action = float(np.clip(action[0], -1.0, 1.0))
        ev_throttle = float(np.clip(action[1], 0.0, 1.0))

        reason = self._describe_action(battery_action, ev_throttle, state)

        result = {
            "battery_action": round(battery_action, 3),
            "ev_throttle": round(ev_throttle, 3),
            "reason": reason,
            "controller": "rl_ppo",
        }
        self._log_action(state, result)
        return result

    def _decide_heuristic(self, state: dict) -> dict:
        """
        Smart heuristic that mimics what a trained RL agent would learn.
        Used when no trained model is available — still much better than rule-based.
        """
        hour = state.get("hour_of_day", 12.0)
        solar = state["solar"]["total_kw"]
        demand = state["grid"]["total_demand_kw"]
        battery_soc = state["battery"]["soc"]
        price_tier = state["price"]["tier"]
        import_price = state["price"]["import_rate"]
        net_import = state["grid"]["net_import_kw"]

        battery_action = 0.0
        ev_throttle = 1.0
        reason = "monitoring"

        # === Battery Strategy ===
        # Charge during solar peak (10 AM - 3 PM) when prices are moderate
        if 10 <= hour <= 15 and solar > demand * 0.5:
            if battery_soc < 0.85:
                # Charge proportional to excess solar
                excess = solar - demand
                if excess > 0:
                    battery_action = min(1.0, excess / 10.0)
                    reason = f"charging battery: solar surplus {excess:.1f}kW"
                elif battery_soc < 0.5 and price_tier != "peak":
                    battery_action = 0.4
                    reason = "pre-charging: anticipating evening peak"

        # Discharge during evening peak (5 PM - 9 PM) 
        elif 17 <= hour <= 21:
            if battery_soc > 0.2 and price_tier == "peak":
                discharge_rate = min(1.0, (demand - solar) / 10.0)
                battery_action = -max(0.3, discharge_rate)
                reason = f"discharging: peak pricing ${import_price:.2f}/kWh"

        # Off-peak cheap charging (11 PM - 5 AM)
        elif (hour >= 23 or hour < 5):
            if battery_soc < 0.6:
                battery_action = 0.5
                reason = "off-peak charging: lowest rates"

        # Emergency responses
        if battery_soc < 0.12:
            battery_action = max(battery_action, 0.3)
            reason = "emergency: battery critically low"
        elif battery_soc > 0.93:
            battery_action = min(battery_action, -0.1)
            reason = "battery near full: gentle discharge"

        # === EV Strategy ===
        # Throttle EV during peak pricing
        if price_tier == "peak" and 17 <= hour <= 21:
            ev_throttle = 0.3  # reduce to 30%
            reason += " | EV throttled: peak pricing"
        elif net_import > 20:
            ev_throttle = 0.5  # reduce if grid is stressed
            reason += " | EV throttled: high grid load"
        # Full speed during off-peak
        elif (hour >= 23 or hour < 6):
            ev_throttle = 1.0

        result = {
            "battery_action": round(battery_action, 3),
            "ev_throttle": round(ev_throttle, 3),
            "reason": reason,
            "controller": "rl_heuristic",
        }
        self._log_action(state, result)
        return result

    def _state_to_observation(self, state: dict) -> np.ndarray:
        """Convert grid state dict to normalized observation vector."""
        solar = state["solar"]["total_kw"]
        house = state["houses"]["total_kw"]
        ev = state["ev_chargers"]["total_kw"]
        price = state["price"]["import_rate"]
        tier_map = {"off_peak": 0.0, "shoulder": 0.5, "peak": 1.0}

        return np.array([
            state["hour_of_day"] / 24.0,
            min(1.0, solar / 20.0),
            min(1.0, house / 24.0),
            min(1.0, ev / 21.6),
            state["battery"]["soc"],
            min(1.0, price / 0.70),
            np.clip(((house + ev - solar) + 45.6) / 91.2, 0.0, 1.0),
            tier_map.get(state["price"]["tier"], 0.5),
            state["battery"]["available_charge_kw"] / 10.0,
            state["battery"]["available_discharge_kw"] / 10.0,
        ], dtype=np.float32)

    def _describe_action(self, battery_action: float, ev_throttle: float,
                         state: dict) -> str:
        """Generate human-readable description of the AI's decision."""
        parts = []

        if battery_action > 0.3:
            parts.append(f"charging battery at {battery_action*100:.0f}%")
        elif battery_action < -0.3:
            parts.append(f"discharging battery at {abs(battery_action)*100:.0f}%")
        else:
            parts.append("battery idle")

        if ev_throttle < 0.5:
            parts.append(f"EV throttled to {ev_throttle*100:.0f}%")
        elif ev_throttle < 1.0:
            parts.append(f"EV at {ev_throttle*100:.0f}%")

        price_tier = state["price"]["tier"]
        if price_tier == "peak":
            parts.append("peak pricing active")

        return " | ".join(parts)

    def _log_action(self, state: dict, action: dict):
        """Log action for dashboard display."""
        self.action_log.append({
            "hour": state.get("hour_of_day", 0),
            "step": state.get("timestamp", 0),
            **action
        })
        if len(self.action_log) > 500:
            self.action_log = self.action_log[-250:]
