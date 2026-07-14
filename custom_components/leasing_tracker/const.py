"""Constants for the Leasing Tracker integration."""

DOMAIN = "leasing_tracker"

# Configuration
CONF_NAME = "name"
CONF_CURRENT_KM_ENTITY = "current_km_entity"
CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_START_KM = "start_km"
CONF_KM_PER_YEAR = "km_per_year"
CONF_UNIT_SYSTEM = "unit_system"  # "metric" or "imperial"
CONF_EXCESS_PRICE = "excess_price"  # price per excess km/mile over the allowance
CONF_CURRENCY = "currency"  # free-text ISO 4217 code, e.g. "EUR", "SEK", "PLN"

# --- Contract terms (asked in step 1, filled in step 2) ---
# Gating questions
CONF_HAS_TOLERANCE = "has_tolerance"  # contract has a goodwill / tolerance band
CONF_HAS_EXCESS_CHARGE = "has_excess_charge"  # charges apply for excess distance
CONF_HAS_REFUND = "has_refund"  # refund is paid for under-driven distance

# Tolerance band (entered in the DISPLAY unit: km or miles)
CONF_TOLERANCE_OVER = "tolerance_over"  # goodwill above the allowance
CONF_TOLERANCE_UNDER = "tolerance_under"  # goodwill below the allowance

# Refund terms
CONF_REFUND_PRICE = "refund_price"  # refund per under-driven km/mile
CONF_REFUND_LIMIT_MODE = "refund_limit_mode"  # "unlimited" or "limited"
CONF_MAX_REFUND_DISTANCE = "max_refund_distance"  # cap when mode == "limited"

# Refund limit modes (lowercase for hassfest translation keys)
REFUND_LIMIT_UNLIMITED = "unlimited"
REFUND_LIMIT_LIMITED = "limited"

# Status thresholds used when no tolerance band is configured.
# Expressed as a fraction of the total allowance so they scale with the
# contract size and work identically in km and miles.
STATUS_DEFAULT_TOLERANCE_FRACTION = 0.02  # 2% of total allowance
STATUS_SIGNIFICANT_FRACTION = 0.05  # a further 5% -> "significantly over plan"

# Fallback currency when neither the config entry nor hass.config provide one.
DEFAULT_CURRENCY = "EUR"

# Sensor types
SENSOR_REMAINING_KM_TOTAL = "remaining_km_total"
SENSOR_REMAINING_KM_YEAR = "remaining_km_year"
SENSOR_REMAINING_KM_MONTH = "remaining_km_month"
SENSOR_REMAINING_KM_YEAR_ACTUAL = "remaining_km_year_actual"
SENSOR_REMAINING_KM_MONTH_ACTUAL = "remaining_km_month_actual"
SENSOR_ESTIMATED_KM_YEAR_END = "estimated_km_year_end"
SENSOR_ESTIMATED_KM_MONTH_END = "estimated_km_month_end"
SENSOR_REMAINING_DAYS = "remaining_days"
SENSOR_REMAINING_MONTHS = "remaining_months"
SENSOR_TOTAL_KM_DRIVEN = "total_km_driven"
SENSOR_KM_DRIVEN_THIS_MONTH = "km_driven_this_month"
SENSOR_KM_DRIVEN_THIS_YEAR = "km_driven_this_year"
SENSOR_KM_PER_DAY_AVERAGE = "km_per_day_average"
SENSOR_KM_PER_MONTH_AVERAGE = "km_per_month_average"
SENSOR_ALLOWED_KM_TOTAL = "allowed_km_total"
SENSOR_ALLOWED_KM_PER_MONTH = "allowed_km_per_month"
SENSOR_ALLOWED_KM_THIS_YEAR = "allowed_km_this_year"
SENSOR_ALLOWED_KM_THIS_MONTH = "allowed_km_this_month"
SENSOR_DAYS_TOTAL = "days_total"
SENSOR_PROGRESS_PERCENTAGE = "progress_percentage"
SENSOR_KM_DIFFERENCE = "km_difference"
SENSOR_STATUS = "status"
SENSOR_END_DATE = "end_date"
SENSOR_ESTIMATED_KM_LEASE_END = "estimated_km_lease_end"
SENSOR_ESTIMATED_EXCESS_KM = "estimated_excess_km"
SENSOR_ESTIMATED_EXCESS_COST = "estimated_excess_cost"
SENSOR_ESTIMATED_UNDER_KM = "estimated_under_km"
SENSOR_ESTIMATED_REFUND = "estimated_refund"
SENSOR_ESTIMATED_NET_COST = "estimated_net_cost"
