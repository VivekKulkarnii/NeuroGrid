"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class DeviceReading(BaseModel):
    id: str
    output_kw: Optional[float] = None
    load_kw: Optional[float] = None
    connected: Optional[bool] = None
    soc: Optional[float] = None
    throttle: Optional[float] = None
    cloud_cover: Optional[float] = None


class SolarState(BaseModel):
    total_kw: float
    panels: List[DeviceReading]


class HouseState(BaseModel):
    total_kw: float
    units: List[DeviceReading]


class EVState(BaseModel):
    total_kw: float
    units: List[DeviceReading]


class BatteryState(BaseModel):
    battery_id: str
    soc: float
    energy_kwh: float
    capacity_kwh: float
    available_charge_kw: float
    available_discharge_kw: float


class PriceState(BaseModel):
    import_rate: float
    export_rate: float
    tier: str


class GridState(BaseModel):
    net_import_kw: float
    total_demand_kw: float
    total_supply_kw: float
    battery_power_kw: Optional[float] = 0.0
    blackout: Optional[bool] = False


class MetricsState(BaseModel):
    total_cost: float
    step_cost: Optional[float] = 0.0
    blackout_count: int


class FullGridState(BaseModel):
    timestamp: int
    hour_of_day: float
    scenario: Optional[str] = "baseline"
    solar: SolarState
    houses: HouseState
    ev_chargers: EVState
    battery: BatteryState
    price: PriceState
    grid: GridState
    metrics: MetricsState
    battery_action: Optional[float] = 0.0


class ActionCommand(BaseModel):
    battery_action: float = Field(ge=-1.0, le=1.0)
    ev_throttle: float = Field(ge=0.0, le=1.0)
    reason: Optional[str] = ""
    controller: Optional[str] = ""


class ScenarioRequest(BaseModel):
    scenario: str = Field(pattern="^(baseline|ai|stress)$")


class StressEvent(BaseModel):
    event_type: str  # "cloud_cover" | "ev_surge" | "price_spike"
    intensity: float = Field(ge=0.0, le=1.0, default=1.0)
    duration_steps: int = Field(ge=1, le=500, default=100)
