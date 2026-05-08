"""
Device models for the smart neighbourhood power grid.
Each device generates realistic energy data with daily patterns and noise.
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SolarPanel:
    """
    Simulates a rooftop solar panel array.
    Output follows a bell curve peaking at solar noon (~1 PM).
    Rated capacity in kW.
    """
    panel_id: str
    rated_capacity_kw: float = 5.0  # typical residential
    efficiency: float = 0.85
    cloud_cover: float = 0.0  # 0.0 = clear, 1.0 = fully overcast

    def get_output(self, hour_of_day: float) -> float:
        """Returns current solar output in kW based on time of day."""
        # Bell curve centered at 13:00 (1 PM), width ~4 hours
        solar_peak_hour = 13.0
        solar_width = 4.0

        if hour_of_day < 6.0 or hour_of_day > 20.0:
            return 0.0  # no sun

        # Gaussian curve for solar irradiance
        irradiance = math.exp(-0.5 * ((hour_of_day - solar_peak_hour) / solar_width) ** 2)

        # Apply cloud cover (reduces output)
        cloud_factor = 1.0 - (self.cloud_cover * 0.9)  # even full clouds let some through

        # Add realistic noise (±5%)
        noise = 1.0 + random.uniform(-0.05, 0.05)

        output = self.rated_capacity_kw * self.efficiency * irradiance * cloud_factor * noise
        return max(0.0, round(output, 3))


@dataclass
class House:
    """
    Simulates residential electricity consumption.
    Load follows a double-peak pattern: morning (7-9 AM) and evening (6-10 PM).
    """
    house_id: str
    base_load_kw: float = 0.5  # always-on appliances (fridge, standby, etc.)
    max_load_kw: float = 4.0   # peak consumption
    occupants: int = 4
    _activity_seed: float = field(default_factory=lambda: random.random())

    def get_load(self, hour_of_day: float) -> float:
        """Returns current power consumption in kW."""
        # Morning peak (7-9 AM): cooking, getting ready
        morning_peak = math.exp(-0.5 * ((hour_of_day - 8.0) / 1.0) ** 2) * 0.6

        # Evening peak (7-10 PM): cooking, TV, heating/cooling
        evening_peak = math.exp(-0.5 * ((hour_of_day - 19.5) / 1.5) ** 2) * 1.0

        # Midday baseline bump (lunch, WFH)
        midday = math.exp(-0.5 * ((hour_of_day - 12.5) / 2.0) ** 2) * 0.3

        # Night minimum (sleeping)
        night_factor = 0.1 if (0 <= hour_of_day < 6) else 0.0

        # Combine patterns
        activity = morning_peak + evening_peak + midday + night_factor

        # Scale by occupants (more people = slightly more load)
        occupant_factor = 0.7 + (self.occupants * 0.1)

        # Add realistic noise (±10%) — each house has unique noise pattern
        noise = 1.0 + 0.1 * math.sin(hour_of_day * 3.7 + self._activity_seed * 100)
        noise *= (1.0 + random.uniform(-0.05, 0.05))

        load = self.base_load_kw + (self.max_load_kw - self.base_load_kw) * activity * occupant_factor * noise
        return max(self.base_load_kw * 0.3, round(load, 3))


@dataclass
class EVCharger:
    """
    Simulates an EV charging station.
    EVs typically charge overnight or when plugged in after work.
    """
    charger_id: str
    max_charge_rate_kw: float = 7.2  # Level 2 charger
    current_throttle: float = 1.0    # 0.0 to 1.0 (AI can throttle)
    is_connected: bool = False
    battery_soc: float = 0.5         # State of charge (0-1)
    battery_capacity_kwh: float = 60.0  # Typical EV battery

    def get_load(self, hour_of_day: float) -> float:
        """Returns current charging load in kW."""
        # EV connection probability by time of day
        # High after work (6 PM), stays connected overnight, disconnects 7 AM
        if not self.is_connected:
            connect_prob = self._connection_probability(hour_of_day)
            if random.random() < connect_prob * 0.02:  # small chance each tick
                self.is_connected = True
                self.battery_soc = random.uniform(0.2, 0.6)  # arrives partially charged

        if not self.is_connected:
            return 0.0

        if self.battery_soc >= 0.95:
            # Fully charged, disconnect during morning
            if 6 <= hour_of_day <= 9:
                self.is_connected = False
                return 0.0
            return 0.0  # trickle only

        # Charge at throttled rate
        charge_kw = self.max_charge_rate_kw * self.current_throttle

        # Simulate battery charging (reduce rate near full)
        if self.battery_soc > 0.8:
            charge_kw *= (1.0 - self.battery_soc) / 0.2  # taper off

        # Update SOC (approximate for 2-second intervals)
        energy_delivered = charge_kw * (2.0 / 3600.0)  # kWh in 2 seconds
        self.battery_soc = min(1.0, self.battery_soc + energy_delivered / self.battery_capacity_kwh)

        return max(0.0, round(charge_kw, 3))

    def _connection_probability(self, hour: float) -> float:
        """Probability of an EV connecting at this hour."""
        # Peak connection after work hours
        evening = math.exp(-0.5 * ((hour - 18.0) / 1.5) ** 2)
        return evening

    def set_throttle(self, throttle: float):
        """AI sets charging throttle (0.0 to 1.0)."""
        self.current_throttle = max(0.0, min(1.0, throttle))


@dataclass
class BatteryBank:
    """
    Community battery energy storage system (BESS).
    The AI agent controls charge/discharge decisions.
    """
    battery_id: str = "community_battery"
    capacity_kwh: float = 50.0       # 50 kWh community battery
    current_soc: float = 0.5         # State of charge (0-1)
    max_charge_rate_kw: float = 10.0  # Max charge power
    max_discharge_rate_kw: float = 10.0  # Max discharge power
    efficiency: float = 0.92          # Round-trip efficiency
    min_soc: float = 0.1             # Don't discharge below 10%
    max_soc: float = 0.95            # Don't charge above 95%

    @property
    def current_energy_kwh(self) -> float:
        return self.capacity_kwh * self.current_soc

    @property
    def available_charge_kw(self) -> float:
        """How much power can still be absorbed."""
        if self.current_soc >= self.max_soc:
            return 0.0
        return self.max_charge_rate_kw

    @property
    def available_discharge_kw(self) -> float:
        """How much power can be released."""
        if self.current_soc <= self.min_soc:
            return 0.0
        return self.max_discharge_rate_kw

    def charge(self, power_kw: float, duration_seconds: float = 2.0) -> float:
        """
        Charge the battery. Returns actual power absorbed (kW).
        """
        actual_power = min(power_kw, self.available_charge_kw)
        energy = actual_power * (duration_seconds / 3600.0) * self.efficiency
        new_soc = self.current_soc + (energy / self.capacity_kwh)
        self.current_soc = min(self.max_soc, new_soc)
        return round(actual_power, 3)

    def discharge(self, power_kw: float, duration_seconds: float = 2.0) -> float:
        """
        Discharge the battery. Returns actual power released (kW).
        """
        actual_power = min(power_kw, self.available_discharge_kw)
        energy = actual_power * (duration_seconds / 3600.0) / self.efficiency
        new_soc = self.current_soc - (energy / self.capacity_kwh)
        self.current_soc = max(self.min_soc, new_soc)
        return round(actual_power, 3)

    def get_status(self) -> dict:
        return {
            "battery_id": self.battery_id,
            "soc": round(self.current_soc, 4),
            "energy_kwh": round(self.current_energy_kwh, 2),
            "capacity_kwh": self.capacity_kwh,
            "available_charge_kw": round(self.available_charge_kw, 2),
            "available_discharge_kw": round(self.available_discharge_kw, 2),
        }
