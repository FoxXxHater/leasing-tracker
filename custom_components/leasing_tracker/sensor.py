"""Sensor platform for Leasing Tracker."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_UNIT_SYSTEM,
    CONF_CURRENT_KM_ENTITY,
    CONF_END_DATE,
    CONF_KM_PER_YEAR,
    CONF_NAME,
    CONF_START_DATE,
    CONF_START_KM,
    DOMAIN,
    SENSOR_ALLOWED_KM_PER_MONTH,
    SENSOR_ALLOWED_KM_THIS_MONTH,
    SENSOR_ALLOWED_KM_THIS_YEAR,
    SENSOR_ALLOWED_KM_TOTAL,
    SENSOR_DAYS_TOTAL,
    SENSOR_ESTIMATED_KM_MONTH_END,
    SENSOR_ESTIMATED_KM_YEAR_END,
    SENSOR_KM_DIFFERENCE,
    SENSOR_KM_DRIVEN_THIS_MONTH,
    SENSOR_KM_DRIVEN_THIS_YEAR,
    SENSOR_KM_PER_DAY_AVERAGE,
    SENSOR_KM_PER_MONTH_AVERAGE,
    SENSOR_PROGRESS_PERCENTAGE,
    SENSOR_REMAINING_DAYS,
    SENSOR_REMAINING_KM_MONTH,
    SENSOR_REMAINING_KM_MONTH_ACTUAL,
    SENSOR_REMAINING_KM_TOTAL,
    SENSOR_REMAINING_KM_YEAR,
    SENSOR_REMAINING_KM_YEAR_ACTUAL,
    SENSOR_REMAINING_MONTHS,
    SENSOR_STATUS,
    SENSOR_TOTAL_KM_DRIVEN,
)

_LOGGER = logging.getLogger(__name__)

# Conversion factors
KM_TO_MILES = 0.621371
MILES_TO_KM = 1.609344


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Leasing Tracker sensors."""
    config = entry.data
    name = config[CONF_NAME]

    sensors = [
        LeasingTrackerSensor(hass, entry, name, SENSOR_REMAINING_KM_TOTAL),
        LeasingTrackerSensor(hass, entry, name, SENSOR_REMAINING_KM_YEAR),
        LeasingTrackerSensor(hass, entry, name, SENSOR_REMAINING_KM_MONTH),
        LeasingTrackerSensor(hass, entry, name, SENSOR_REMAINING_KM_YEAR_ACTUAL),
        LeasingTrackerSensor(hass, entry, name, SENSOR_REMAINING_KM_MONTH_ACTUAL),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_KM_YEAR_END),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_KM_MONTH_END),
        LeasingTrackerSensor(hass, entry, name, SENSOR_REMAINING_DAYS),
        LeasingTrackerSensor(hass, entry, name, SENSOR_REMAINING_MONTHS),
        LeasingTrackerSensor(hass, entry, name, SENSOR_TOTAL_KM_DRIVEN),
        LeasingTrackerSensor(hass, entry, name, SENSOR_KM_DRIVEN_THIS_MONTH),
        LeasingTrackerSensor(hass, entry, name, SENSOR_KM_DRIVEN_THIS_YEAR),
        LeasingTrackerSensor(hass, entry, name, SENSOR_KM_PER_DAY_AVERAGE),
        LeasingTrackerSensor(hass, entry, name, SENSOR_KM_PER_MONTH_AVERAGE),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ALLOWED_KM_TOTAL),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ALLOWED_KM_PER_MONTH),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ALLOWED_KM_THIS_YEAR),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ALLOWED_KM_THIS_MONTH),
        LeasingTrackerSensor(hass, entry, name, SENSOR_DAYS_TOTAL),
        LeasingTrackerSensor(hass, entry, name, SENSOR_PROGRESS_PERCENTAGE),
        LeasingTrackerSensor(hass, entry, name, SENSOR_KM_DIFFERENCE),
        LeasingTrackerSensor(hass, entry, name, SENSOR_STATUS),
    ]

    async_add_entities(sensors, True)


class LeasingTrackerSensor(SensorEntity):
    """Representation of a Leasing Tracker Sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._current_km_entity = entry.data[CONF_CURRENT_KM_ENTITY]
        
        # Get config from entry (always fresh)
        self._is_metric = entry.data.get(CONF_UNIT_SYSTEM, "metric") == "metric"
        _LOGGER.debug("Leasing Tracker: unit_system=%s, is_metric=%s", entry.data.get(CONF_UNIT_SYSTEM, "metric"), self._is_metric)
        
        # Device Info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Leasing Tracker",
            model="Car Leasing Monitor",
        )

        # Sensor-spezifische Attribute
        self._setup_sensor_attributes()

    def _setup_sensor_attributes(self) -> None:
        """Set up sensor-specific attributes."""
        sensor_configs = {
            SENSOR_REMAINING_KM_TOTAL: {
                "translation_key": "remaining_km_total",
                "icon": "mdi:counter",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_YEAR: {
                "translation_key": "remaining_km_year",
                "icon": "mdi:calendar-clock",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_MONTH: {
                "translation_key": "remaining_km_month",
                "icon": "mdi:calendar-month",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_YEAR_ACTUAL: {
                "translation_key": "remaining_km_year_actual",
                "icon": "mdi:calendar-today",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_MONTH_ACTUAL: {
                "translation_key": "remaining_km_month_actual",
                "icon": "mdi:calendar-today",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ESTIMATED_KM_YEAR_END: {
                "translation_key": "estimated_km_year_end",
                "icon": "mdi:chart-timeline-variant",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ESTIMATED_KM_MONTH_END: {
                "translation_key": "estimated_km_month_end",
                "icon": "mdi:chart-timeline-variant",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_DAYS: {
                "translation_key": "remaining_days",
                "icon": "mdi:calendar-end",
                "unit": "days",
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_MONTHS: {
                "translation_key": "remaining_months",
                "icon": "mdi:calendar-month-outline",
                "unit": "months",
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_TOTAL_KM_DRIVEN: {
                "translation_key": "total_km_driven",
                "icon": "mdi:speedometer",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            SENSOR_KM_DRIVEN_THIS_MONTH: {
                "translation_key": "km_driven_this_month",
                "icon": "mdi:calendar-month",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_KM_DRIVEN_THIS_YEAR: {
                "translation_key": "km_driven_this_year",
                "icon": "mdi:calendar",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_KM_PER_DAY_AVERAGE: {
                "translation_key": "km_per_day_average",
                "icon": "mdi:chart-line",
                "unit": "km/day" if self._is_metric else "mi/day",
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_KM_PER_MONTH_AVERAGE: {
                "translation_key": "km_per_month_average",
                "icon": "mdi:chart-bar",
                "unit": "km/month" if self._is_metric else "mi/month",
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_TOTAL: {
                "translation_key": "allowed_km_total",
                "icon": "mdi:sign-direction",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_PER_MONTH: {
                "translation_key": "allowed_km_per_month",
                "icon": "mdi:calendar-month",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_THIS_YEAR: {
                "translation_key": "allowed_km_this_year",
                "icon": "mdi:calendar",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_THIS_MONTH: {
                "translation_key": "allowed_km_this_month",
                "icon": "mdi:calendar-month",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_DAYS_TOTAL: {
                "translation_key": "days_total",
                "icon": "mdi:calendar-range",
                "unit": "days",
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_PROGRESS_PERCENTAGE: {
                "translation_key": "progress_percentage",
                "icon": "mdi:percent",
                "unit": "%",
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_KM_DIFFERENCE: {
                "translation_key": "km_difference",
                "icon": "mdi:delta",
                "unit": UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_STATUS: {
                "translation_key": "status",
                "icon": "mdi:information-outline",
                "device_class": SensorDeviceClass.ENUM,
                "options": ["on_plan", "over_plan", "significantly_over_plan", "under_plan"],
            },
        }

        config = sensor_configs.get(self._sensor_type, {})
        
        # Set translation key instead of name
        self._attr_translation_key = config.get("translation_key")
        self._attr_icon = config.get("icon")
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")
        
        # For enum sensors (like status)
        if config.get("options"):
            self._attr_options = config.get("options")

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        @callback
        def sensor_state_listener(event):
            """Handle sensor state changes."""
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._current_km_entity], sensor_state_listener
            )
        )

    def update(self) -> None:
        """Update the sensor."""
        current_km_state = self.hass.states.get(self._current_km_entity)
        
        if current_km_state is None or current_km_state.state in ["unknown", "unavailable"]:
            self._attr_native_value = None
            self._attr_available = False
            return

        try:
            current_km_raw = float(current_km_state.state)
        except (ValueError, TypeError):
            self._attr_native_value = None
            self._attr_available = False
            return

        self._attr_available = True
        
        # Check sensor's unit and convert if needed
        sensor_unit = current_km_state.attributes.get('unit_of_measurement', 'km')
        
        # Convert sensor value to km (internal calculations use km)
        if sensor_unit in ['mi', 'miles', 'mile']:
            # Sensor is in miles, convert to km
            current_km = current_km_raw * MILES_TO_KM
        else:
            # Sensor is in km (or no unit specified, assume km)
            current_km = current_km_raw

        # Get config values
        start_date = datetime.fromisoformat(self._entry.data[CONF_START_DATE])
        end_date = datetime.fromisoformat(self._entry.data[CONF_END_DATE])
        start_km_config = self._entry.data[CONF_START_KM]
        km_per_year_config = self._entry.data[CONF_KM_PER_YEAR]
        
        # Convert from miles to km if imperial
        if not self._is_metric:
            start_km = start_km_config * MILES_TO_KM
            km_per_year = km_per_year_config * MILES_TO_KM
        else:
            start_km = start_km_config
            km_per_year = km_per_year_config

        # Calculate values
        now = datetime.now()
        total_days = (end_date - start_date).days
        elapsed_days = (now - start_date).days
        remaining_days = (end_date - now).days
        
        # Current year/month
        year_start = datetime(now.year, 1, 1)
        month_start = datetime(now.year, now.month, 1)
        
        # Days in current periods
        days_in_year = (datetime(now.year, 12, 31) - year_start).days + 1
        if now.month == 12:
            days_in_month = (datetime(now.year, 12, 31) - month_start).days + 1
        else:
            next_month = datetime(now.year, now.month + 1, 1)
            days_in_month = (next_month - month_start).days
        
        # Remaining days in periods
        remaining_days_year = (datetime(now.year, 12, 31) - now).days
        if now.month == 12:
            remaining_days_month = (datetime(now.year, 12, 31) - now).days
        else:
            next_month = datetime(now.year, now.month + 1, 1)
            remaining_days_month = (next_month - now).days

        # Total driven
        total_km_driven = current_km - start_km
        
        # Allowed KM
        allowed_km_total = (total_days / 365.25) * km_per_year
        allowed_km_per_month = km_per_year / 12
        
        # Year calculations
        if year_start >= start_date:
            days_into_year = (now - year_start).days
            allowed_km_this_year = (days_into_year / days_in_year) * km_per_year
            
            # Find KM at year start
            if year_start > start_date:
                days_at_year_start = (year_start - start_date).days
                allowed_km_at_year_start = (days_at_year_start / total_days) * allowed_km_total + start_km
            else:
                allowed_km_at_year_start = start_km
                
            km_driven_this_year = current_km - allowed_km_at_year_start
        else:
            km_driven_this_year = total_km_driven
            allowed_km_this_year = (elapsed_days / 365.25) * km_per_year
        
        # Month calculations  
        if month_start >= start_date:
            days_into_month = (now - month_start).days
            allowed_km_this_month = (days_into_month / days_in_month) * allowed_km_per_month
            
            # Find KM at month start
            if month_start > start_date:
                days_at_month_start = (month_start - start_date).days
                allowed_km_at_month_start = (days_at_month_start / total_days) * allowed_km_total + start_km
            else:
                allowed_km_at_month_start = start_km
                
            km_driven_this_month = current_km - allowed_km_at_month_start
        else:
            km_driven_this_month = total_km_driven
            allowed_km_this_month = (elapsed_days / 30.44) * allowed_km_per_month

        # Averages
        if elapsed_days > 0:
            km_per_day = total_km_driven / elapsed_days
            km_per_month = total_km_driven / (elapsed_days / 30.44)
        else:
            km_per_day = 0
            km_per_month = 0

        # Remaining KM
        remaining_km_total = allowed_km_total - total_km_driven
        remaining_km_year_actual = allowed_km_this_year - km_driven_this_year
        remaining_km_month_actual = allowed_km_this_month - km_driven_this_month
        
        # Estimated remaining KM (at current pace)
        remaining_km_year_estimated = remaining_days_year * km_per_day
        remaining_km_month_estimated = remaining_days_month * km_per_day
        
        # Estimated total KM at end of periods
        estimated_km_month_end = current_km + remaining_km_month_estimated
        estimated_km_year_end = current_km + remaining_km_year_estimated
        
        # Difference
        km_difference = total_km_driven - ((elapsed_days / total_days) * allowed_km_total)
        
        # Progress
        progress = (elapsed_days / total_days) * 100 if total_days > 0 else 0
        
        # Status (using translation keys)
        if km_difference < -500:
            status = "under_plan"
        elif km_difference <= 500:
            status = "on_plan"
        elif km_difference <= 2000:
            status = "over_plan"
        else:
            status = "significantly_over_plan"
        
        # Remaining months
        remaining_months = remaining_days / 30.44

        # Set value based on sensor type
        value_map = {
            SENSOR_REMAINING_KM_TOTAL: round(remaining_km_total),
            SENSOR_REMAINING_KM_YEAR: round(remaining_km_year_estimated),
            SENSOR_REMAINING_KM_MONTH: round(remaining_km_month_estimated),
            SENSOR_REMAINING_KM_YEAR_ACTUAL: round(remaining_km_year_actual),
            SENSOR_REMAINING_KM_MONTH_ACTUAL: round(remaining_km_month_actual),
            SENSOR_ESTIMATED_KM_YEAR_END: round(estimated_km_year_end),
            SENSOR_ESTIMATED_KM_MONTH_END: round(estimated_km_month_end),
            SENSOR_REMAINING_DAYS: remaining_days,
            SENSOR_REMAINING_MONTHS: round(remaining_months, 1),
            SENSOR_TOTAL_KM_DRIVEN: round(total_km_driven),
            SENSOR_KM_DRIVEN_THIS_MONTH: round(km_driven_this_month),
            SENSOR_KM_DRIVEN_THIS_YEAR: round(km_driven_this_year),
            SENSOR_KM_PER_DAY_AVERAGE: round(km_per_day, 2),
            SENSOR_KM_PER_MONTH_AVERAGE: round(km_per_month),
            SENSOR_ALLOWED_KM_TOTAL: round(allowed_km_total),
            SENSOR_ALLOWED_KM_PER_MONTH: round(allowed_km_per_month),
            SENSOR_ALLOWED_KM_THIS_YEAR: round(allowed_km_this_year),
            SENSOR_ALLOWED_KM_THIS_MONTH: round(allowed_km_this_month),
            SENSOR_DAYS_TOTAL: total_days,
            SENSOR_PROGRESS_PERCENTAGE: round(progress, 1),
            SENSOR_KM_DIFFERENCE: round(km_difference),
            SENSOR_STATUS: status,
        }

        self._attr_native_value = value_map.get(self._sensor_type)

        # Convert to miles if imperial
        if not self._is_metric and self._attr_native_unit_of_measurement == UnitOfLength.MILES:
            if isinstance(self._attr_native_value, (int, float)):
                self._attr_native_value = round(self._attr_native_value * KM_TO_MILES, 2)
