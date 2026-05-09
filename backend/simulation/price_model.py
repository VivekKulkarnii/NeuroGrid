"""
Electricity pricing model with time-of-use tariffs.
Simulates realistic retail electricity pricing with peak, shoulder, and off-peak rates.
"""

import math
import random
from dataclasses import dataclass

from . import config


@dataclass
class PriceModel:
    """
    Time-of-use (TOU) electricity pricing.

    Rate tiers (based on typical Australian / US TOU tariffs):
        Off-peak:   11 PM - 7 AM    → $0.08/kWh
        Shoulder:   7 AM - 2 PM, 8 PM - 11 PM  → $0.18/kWh
        Peak:       2 PM - 8 PM     → $0.35/kWh

    The model also provides a feed-in tariff (FIT) for solar export.
    """
    off_peak_rate: float = config.PRICE_OFF_PEAK_INR   # ₹/kWh
    shoulder_rate: float = config.PRICE_SHOULDER_INR   # ₹/kWh
    peak_rate: float = config.PRICE_PEAK_INR       # ₹/kWh
    feed_in_tariff: float = config.PRICE_FEED_IN_TARIFF  # ₹/kWh (solar export credit)
    demand_charge: float = config.PRICE_DEMAND_CHARGE   # ₹/kW for peak demand (monthly)
    stress_multiplier: float = 1.0  # For stress test scenario

    def get_price(self, hour_of_day: float) -> float:
        """
        Returns current electricity import price in ₹/kWh.
        Includes small noise for realism.
        """
        base_price = self._get_tier_price(hour_of_day)

        # Add smooth price transitions instead of hard steps
        price = self._smooth_price(hour_of_day, base_price)

        # Apply stress multiplier (for stress test scenario)
        price *= self.stress_multiplier

        # Add market noise (±3%)
        noise = 1.0 + random.uniform(-0.03, 0.03)
        price *= noise

        return round(price, 4)

    def _get_tier_price(self, hour: float) -> float:
        """Returns the base tier price for the given hour."""
        if 23 <= hour or hour < 7:
            return self.off_peak_rate
        elif 14 <= hour < 20:
            return self.peak_rate
        else:
            return self.shoulder_rate

    def _smooth_price(self, hour: float, base_price: float) -> float:
        """
        Smooth price transitions between tiers using sigmoid blending.
        Prevents hard jumps in price signal.
        """
        # Transition points and their widths
        transitions = [
            (7.0, self.off_peak_rate, self.shoulder_rate),    # off-peak → shoulder
            (14.0, self.shoulder_rate, self.peak_rate),       # shoulder → peak
            (20.0, self.peak_rate, self.shoulder_rate),       # peak → shoulder
            (23.0, self.shoulder_rate, self.off_peak_rate),   # shoulder → off-peak
        ]

        for t_hour, from_price, to_price in transitions:
            distance = hour - t_hour
            if abs(distance) < 1.0:
                # Sigmoid blend over 1 hour window
                blend = 1.0 / (1.0 + math.exp(-5 * distance))
                return from_price + (to_price - from_price) * blend

        return base_price

    def get_export_price(self, hour_of_day: float) -> float:
        """Returns feed-in tariff for solar export in ₹/kWh."""
        # FIT is slightly higher during peak (some utilities do this)
        if 14 <= hour_of_day < 20:
            return round(self.feed_in_tariff * 1.2, 4)
        return self.feed_in_tariff

    def get_price_forecast(self, current_hour: float, horizon_hours: int = 24) -> list[dict]:
        """
        Returns price forecast for the next N hours.
        Useful for RL agent lookahead.
        """
        forecast = []
        for h in range(horizon_hours):
            future_hour = (current_hour + h) % 24.0
            forecast.append({
                "hour": round(future_hour, 1),
                "import_price": self.get_price(future_hour),
                "export_price": self.get_export_price(future_hour),
                "tier": self._get_tier_name(future_hour),
            })
        return forecast

    def _get_tier_name(self, hour: float) -> str:
        if 23 <= hour or hour < 7:
            return "off_peak"
        elif 14 <= hour < 20:
            return "peak"
        else:
            return "shoulder"

    def set_stress_mode(self, enabled: bool):
        """Enable/disable stress pricing (2x normal rates)."""
        self.stress_multiplier = 2.0 if enabled else 1.0
