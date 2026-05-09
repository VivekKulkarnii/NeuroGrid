"""
Central configuration file for all simulation inputs and grid parameters.
Modify these values to test different scenarios and neighborhood sizes.
"""

# ==========================================
# 🏘️ GRID ARCHITECTURE
# ==========================================
NUM_HOUSES = 6
NUM_SOLAR = 4
NUM_EV = 3

# ==========================================
# ☀️ SOLAR PANEL SETTINGS
# ==========================================
SOLAR_EFFICIENCY = 0.85
SOLAR_PEAK_HOUR = 13.0     # 1 PM
SOLAR_PEAK_WIDTH = 4.0     # Hours of effective sunlight spread

# ==========================================
# 🏠 HOUSE LOAD SETTINGS
# ==========================================
HOUSE_MORNING_PEAK_HOUR = 8.0
HOUSE_EVENING_PEAK_HOUR = 19.5
HOUSE_OCCUPANT_SCALAR = 0.1  # Load increase per occupant

# ==========================================
# 🚗 EV CHARGER SETTINGS
# ==========================================
EV_MAX_CHARGE_RATE_KW = 7.2
EV_BATTERY_CAPACITY_KWH = 60.0
EV_PEAK_CONNECTION_HOUR = 18.0  # 6 PM

# ==========================================
# 🔋 COMMUNITY BATTERY SETTINGS
# ==========================================
BATTERY_CAPACITY_KWH = 50.0
BATTERY_MAX_CHARGE_RATE_KW = 10.0
BATTERY_MAX_DISCHARGE_RATE_KW = 10.0
BATTERY_EFFICIENCY = 0.92
BATTERY_MIN_SOC = 0.1      # Don't drain below 10%
BATTERY_MAX_SOC = 0.95     # Don't charge above 95%

# ==========================================
# ⏱️ SIMULATION ENGINE SETTINGS
# ==========================================
TICK_INTERVAL = 2.0        # Real seconds between simulation steps
TIME_ACCELERATION = 120.0  # 1 real second = 120 simulated seconds (2 mins)

# ==========================================
# 💰 ELECTRICITY PRICING (INR ₹)
# ==========================================
PRICE_OFF_PEAK_INR = 4.00    # ₹/kWh (11 PM - 7 AM)
PRICE_SHOULDER_INR = 7.50    # ₹/kWh (7 AM - 2 PM, 8 PM - 11 PM)
PRICE_PEAK_INR = 12.00       # ₹/kWh (2 PM - 8 PM)
PRICE_FEED_IN_TARIFF = 3.50  # ₹/kWh (Solar export credit)
PRICE_DEMAND_CHARGE = 10.00  # ₹/kW (Peak demand penalty)
