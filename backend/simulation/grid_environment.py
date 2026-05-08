"""
Gymnasium-compatible environment for the smart grid.
Wraps the simulation devices into an RL-trainable environment.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .devices import SolarPanel, House, EVCharger, BatteryBank
from .price_model import PriceModel


class SmartGridEnv(gym.Env):
    """
    Smart Grid Gymnasium Environment.

    Observation space (10 dims): hour, solar, house_load, ev_load,
    battery_soc, price, net_load, price_tier, avail_charge, avail_discharge.

    Action space (2 continuous):
        0: battery_action (-1=discharge, +1=charge)
        1: ev_throttle (0=off, 1=full)
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, num_houses=6, num_solar=4, num_ev=3,
                 sim_step_seconds=2.0, steps_per_episode=43200):
        super().__init__()
        self.num_houses = num_houses
        self.num_solar = num_solar
        self.num_ev = num_ev
        self.sim_step_seconds = sim_step_seconds
        self.steps_per_episode = steps_per_episode

        self.action_space = spaces.Box(
            low=np.array([-1.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0], dtype=np.float32),
        )
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(10,), dtype=np.float32
        )

        self.max_solar_kw = num_solar * 5.0
        self.max_house_kw = num_houses * 4.0
        self.max_ev_kw = num_ev * 7.2
        self.max_price = 0.70

        self._create_devices()
        self.price_model = PriceModel()
        self.current_step = 0
        self.hour_of_day = 0.0
        self.total_cost = 0.0
        self.total_solar_revenue = 0.0
        self.blackout_count = 0
        self.history = []

    def _create_devices(self):
        self.solar_panels = [
            SolarPanel(panel_id=f"solar_{i}", rated_capacity_kw=4.0 + i * 0.5)
            for i in range(self.num_solar)
        ]
        self.houses = [
            House(house_id=f"house_{i}", base_load_kw=0.3 + i * 0.1,
                  max_load_kw=3.0 + i * 0.5, occupants=2 + (i % 4))
            for i in range(self.num_houses)
        ]
        self.ev_chargers = [
            EVCharger(charger_id=f"ev_{i}") for i in range(self.num_ev)
        ]
        self.battery = BatteryBank()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._create_devices()
        self.price_model = PriceModel()
        self.hour_of_day = 0.0 if options is None else options.get("start_hour", 0.0)
        self.current_step = 0
        self.total_cost = 0.0
        self.total_solar_revenue = 0.0
        self.blackout_count = 0
        self.history = []
        return self._get_observation(), {}

    def step(self, action):
        battery_action = float(action[0])
        ev_throttle = float(action[1])

        for ev in self.ev_chargers:
            ev.set_throttle(ev_throttle)

        solar_output = sum(p.get_output(self.hour_of_day) for p in self.solar_panels)
        house_load = sum(h.get_load(self.hour_of_day) for h in self.houses)
        ev_load = sum(ev.get_load(self.hour_of_day) for ev in self.ev_chargers)

        total_demand = house_load + ev_load

        battery_power = 0.0
        if battery_action > 0:
            charge_kw = battery_action * self.battery.max_charge_rate_kw
            battery_power = -self.battery.charge(charge_kw, self.sim_step_seconds)
        elif battery_action < 0:
            discharge_kw = abs(battery_action) * self.battery.max_discharge_rate_kw
            battery_power = self.battery.discharge(discharge_kw, self.sim_step_seconds)

        net_import = total_demand - solar_output - battery_power

        import_price = self.price_model.get_price(self.hour_of_day)
        export_price = self.price_model.get_export_price(self.hour_of_day)

        step_hours = self.sim_step_seconds / 3600.0
        if net_import > 0:
            step_cost = net_import * import_price * step_hours
        else:
            step_cost = net_import * export_price * step_hours

        self.total_cost += step_cost

        grid_capacity_kw = 30.0
        is_blackout = net_import > grid_capacity_kw
        if is_blackout:
            self.blackout_count += 1

        # Reward function
        reward = -step_cost * 100.0
        if is_blackout:
            reward -= 10.0
        soc = self.battery.current_soc
        if 0.3 <= soc <= 0.8:
            reward += 0.1
        elif soc < 0.15 or soc > 0.92:
            reward -= 0.5
        if solar_output > 0 and total_demand > 0:
            reward += min(1.0, total_demand / solar_output) * 0.2

        self.history.append({
            "step": self.current_step, "hour": round(self.hour_of_day, 2),
            "solar_kw": round(solar_output, 3), "house_kw": round(house_load, 3),
            "ev_kw": round(ev_load, 3), "battery_power_kw": round(battery_power, 3),
            "battery_soc": round(soc, 4), "net_import_kw": round(net_import, 3),
            "price": round(import_price, 4), "step_cost": round(step_cost, 6),
            "reward": round(reward, 4), "blackout": is_blackout,
        })

        self.current_step += 1
        self.hour_of_day = (self.hour_of_day + self.sim_step_seconds / 3600.0) % 24.0

        terminated = self.current_step >= self.steps_per_episode
        truncated = False

        return self._get_observation(), reward, terminated, truncated, {
            "total_cost": self.total_cost, "blackout_count": self.blackout_count,
            "solar_output": solar_output, "house_load": house_load,
            "ev_load": ev_load, "net_import": net_import,
        }

    def _get_observation(self) -> np.ndarray:
        solar_output = sum(p.get_output(self.hour_of_day) for p in self.solar_panels)
        house_load = sum(h.get_load(self.hour_of_day) for h in self.houses)
        ev_load = sum(ev.get_load(self.hour_of_day) for ev in self.ev_chargers)
        price = self.price_model.get_price(self.hour_of_day)
        net_load = (house_load + ev_load) - solar_output
        max_net = self.max_house_kw + self.max_ev_kw

        tier_map = {"off_peak": 0.0, "shoulder": 0.5, "peak": 1.0}
        tier = tier_map.get(self.price_model._get_tier_name(self.hour_of_day), 0.5)

        return np.array([
            self.hour_of_day / 24.0,
            min(1.0, solar_output / max(1.0, self.max_solar_kw)),
            min(1.0, house_load / max(1.0, self.max_house_kw)),
            min(1.0, ev_load / max(1.0, self.max_ev_kw)),
            self.battery.current_soc,
            min(1.0, price / self.max_price),
            np.clip((net_load + max_net) / (2 * max_net), 0.0, 1.0),
            tier,
            self.battery.available_charge_kw / self.battery.max_charge_rate_kw,
            self.battery.available_discharge_kw / self.battery.max_discharge_rate_kw,
        ], dtype=np.float32)

    def get_grid_state(self) -> dict:
        """Returns full grid state dict for API/dashboard."""
        solar_output = sum(p.get_output(self.hour_of_day) for p in self.solar_panels)
        house_load = sum(h.get_load(self.hour_of_day) for h in self.houses)
        ev_load = sum(ev.get_load(self.hour_of_day) for ev in self.ev_chargers)
        price = self.price_model.get_price(self.hour_of_day)

        return {
            "timestamp": self.current_step,
            "hour_of_day": round(self.hour_of_day, 2),
            "solar": {
                "total_kw": round(solar_output, 3),
                "panels": [{"id": p.panel_id, "output_kw": p.get_output(self.hour_of_day)}
                           for p in self.solar_panels],
            },
            "houses": {
                "total_kw": round(house_load, 3),
                "units": [{"id": h.house_id, "load_kw": h.get_load(self.hour_of_day)}
                          for h in self.houses],
            },
            "ev_chargers": {
                "total_kw": round(ev_load, 3),
                "units": [{"id": ev.charger_id, "load_kw": ev.get_load(self.hour_of_day),
                           "connected": ev.is_connected, "soc": round(ev.battery_soc, 3),
                           "throttle": ev.current_throttle} for ev in self.ev_chargers],
            },
            "battery": self.battery.get_status(),
            "price": {
                "import_rate": round(price, 4),
                "export_rate": round(self.price_model.get_export_price(self.hour_of_day), 4),
                "tier": self.price_model._get_tier_name(self.hour_of_day),
            },
            "grid": {
                "net_import_kw": round((house_load + ev_load) - solar_output, 3),
                "total_demand_kw": round(house_load + ev_load, 3),
                "total_supply_kw": round(solar_output, 3),
            },
            "metrics": {
                "total_cost": round(self.total_cost, 4),
                "blackout_count": self.blackout_count,
            },
        }
