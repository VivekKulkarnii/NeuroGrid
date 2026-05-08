"""
Rule-based controller (baseline) for comparison with RL agent.
Uses simple threshold logic — no learning, no optimization.
"""

import logging

logger = logging.getLogger(__name__)


class RuleBasedController:
    """
    Simple threshold-based battery/EV controller.
    This is the 'dumb' baseline for Scenario 1.
    
    Strategy:
        - Charge battery when solar > demand (excess solar)
        - Discharge battery when demand > solar (deficit)
        - No EV throttling — always charge at full rate
        - No price awareness — ignores time-of-use pricing
    """

    def __init__(self):
        self.name = "rule_based"
        self.action_log = []

    def decide(self, state: dict) -> dict:
        """
        Make a control decision based on current grid state.
        
        Args:
            state: Grid state dict from simulator
            
        Returns:
            dict with battery_action (-1 to 1) and ev_throttle (0 to 1)
        """
        solar = state["solar"]["total_kw"]
        demand = state["grid"]["total_demand_kw"]
        battery_soc = state["battery"]["soc"]
        net_import = state["grid"]["net_import_kw"]

        battery_action = 0.0
        ev_throttle = 1.0  # always full — rule-based doesn't optimize EV
        reason = "idle"

        # Simple threshold logic
        if net_import < -2.0 and battery_soc < 0.9:
            # Excess solar — charge battery
            battery_action = 0.6
            reason = "charging: excess solar"
        elif net_import > 5.0 and battery_soc > 0.2:
            # High demand — discharge battery
            battery_action = -0.5
            reason = "discharging: high demand"
        elif battery_soc < 0.15:
            # Emergency charge
            battery_action = 0.3
            reason = "emergency charge: low SOC"

        action = {
            "battery_action": battery_action,
            "ev_throttle": ev_throttle,
            "reason": reason,
            "controller": self.name,
        }

        self.action_log.append({
            "hour": state.get("hour_of_day", 0),
            **action
        })

        # Keep log manageable
        if len(self.action_log) > 500:
            self.action_log = self.action_log[-250:]

        return action
