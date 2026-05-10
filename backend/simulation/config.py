"""
Central configuration file for all simulation inputs and grid parameters.
Modify these values to test different scenarios and neighborhood sizes.
"""

# ==========================================
# 🏘️ GRID ARCHITECTURE
# ==========================================
NUM_HOUSES = 8               # Total homes in the neighborhood
NUM_SOLAR = 5                # Homes equipped with solar panels
NUM_EV = 4                   # Total electric vehicles in the neighborhood

# ==========================================
# ☀️ SOLAR PANEL SETTINGS
# ==========================================
SOLAR_EFFICIENCY = 0.82      # Accounts for heat/dust losses (82% usable)
SOLAR_PEAK_HOUR = 12.5       # Time of day for max sunlight (12:30 PM)
SOLAR_PEAK_WIDTH = 3.5       # How many hours the sun stays strong

# ==========================================
# 🏠 HOUSE LOAD SETTINGS
# ==========================================
HOUSE_MORNING_PEAK_HOUR = 7.5  # Typical morning rush (7:30 AM)
HOUSE_EVENING_PEAK_HOUR = 20.0 # Typical evening peak (8:00 PM)
HOUSE_OCCUPANT_SCALAR = 0.12   # Extra power used per additional person

# ==========================================
# 🚗 EV CHARGER SETTINGS
# ==========================================
EV_MAX_CHARGE_RATE_KW = 7.4    # Max speed of car chargers (Standard AC)
EV_BATTERY_CAPACITY_KWH = 45.0 # Average car battery size (e.g. Nexon EV)
EV_PEAK_CONNECTION_HOUR = 18.5 # When most people plug in (6:30 PM)

# ==========================================
# 🔋 COMMUNITY BATTERY SETTINGS
# ==========================================
BATTERY_CAPACITY_KWH = 60.0          # Total storage capacity of the grid
BATTERY_MAX_CHARGE_RATE_KW = 25.0    # Speed of filling the battery
BATTERY_MAX_DISCHARGE_RATE_KW = 30.0 # Speed of draining the battery
BATTERY_EFFICIENCY = 0.90            # Energy lost during charging/discharging
BATTERY_MIN_SOC = 0.15               # Minimum 15% charge (protects battery)
BATTERY_MAX_SOC = 0.95               # Maximum 95% charge (prevents overcharge)

# ==========================================
# ⏱️ SIMULATION ENGINE SETTINGS
# ==========================================
TICK_INTERVAL = 2.0        # Real seconds between dashboard updates
TIME_ACCELERATION = 120.0  # Speed factor (1s real = 120s simulated)

# ==========================================
# 💰 ELECTRICITY PRICING (INR ₹)
# ==========================================
PRICE_OFF_PEAK_INR = 4.50    # Night rate (10 PM - 6 AM)
PRICE_SHOULDER_INR = 8.20    # Standard daytime rate
PRICE_PEAK_INR = 13.50       # High-demand evening rate (6 PM - 10 PM)
PRICE_FEED_IN_TARIFF = 3.80  # What you earn for selling solar to grid
PRICE_DEMAND_CHARGE = 250.0  # Fine for pulling too much power at once