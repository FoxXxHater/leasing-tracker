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
CONF_CURRENCY = "currency"  # "EUR", "USD", "GBP", "CHF"

# Currency symbols
CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "CHF": "CHF",
}

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
