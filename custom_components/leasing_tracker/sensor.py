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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CONF_UNIT_SYSTEM,
    CONF_CURRENCY,
    CONF_CURRENT_KM_ENTITY,
    CONF_END_DATE,
    CONF_EXCESS_PRICE,
    CONF_KM_PER_YEAR,
    CONF_NAME,
    CONF_START_DATE,
    CONF_START_KM,
    CURRENCY_ISO_CODES,
    CURRENCY_SYMBOLS,
    DOMAIN,
    SENSOR_ALLOWED_KM_PER_MONTH,
    SENSOR_ALLOWED_KM_THIS_MONTH,
    SENSOR_ALLOWED_KM_THIS_YEAR,
    SENSOR_ALLOWED_KM_TOTAL,
    SENSOR_DAYS_TOTAL,
    SENSOR_END_DATE,
    SENSOR_ESTIMATED_EXCESS_COST,
    SENSOR_ESTIMATED_EXCESS_KM,
    SENSOR_ESTIMATED_KM_LEASE_END,
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

# Recognized unit strings for miles (case-insensitive)
MILE_UNITS = {"mi", "miles", "mile"}
# Recognized unit strings for kilometers (case-insensitive)
KM_UNITS = {"km", "kilometer", "kilometers", "kilometre", "kilometres"}


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
        LeasingTrackerSensor(hass, entry, name, SENSOR_END_DATE),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_KM_LEASE_END),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_EXCESS_KM),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_EXCESS_COST),
    ]

    async_add_entities(sensors, True)


def _detect_source_unit_is_metric(
    hass: HomeAssistant, source_entity_id: str, fallback_is_metric: bool
) -> tuple[bool, str]:
    """Detect the unit system from the source entity's unit_of_measurement.

    Falls back to the user-provided choice (CONF_UNIT_SYSTEM) when the source
    entity is unavailable or has no unit_of_measurement attribute (e.g.
    input_number helpers without a unit).

    Returns a tuple of (is_metric, reason) where reason explains where the
    decision came from. This makes debugging unit-detection issues possible
    without ambiguity.
    """
    state = hass.states.get(source_entity_id)
    if state is None:
        return fallback_is_metric, "fallback (source entity not found)"

    unit = state.attributes.get("unit_of_measurement")
    if unit is None:
        return fallback_is_metric, "fallback (source has no unit_of_measurement)"

    unit_normalized = str(unit).strip().lower()
    if unit_normalized in MILE_UNITS:
        return False, f"source unit '{unit}' -> miles"
    if unit_normalized in KM_UNITS:
        return True, f"source unit '{unit}' -> kilometers"

    # Unknown unit -> use the user-provided choice as fallback
    return fallback_is_metric, f"fallback (unknown source unit '{unit}')"


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

        # Fallback unit system from the user's manual choice in the config flow.
        # This is only used if the source entity has no unit_of_measurement.
        self._fallback_is_metric = (
            entry.data.get(CONF_UNIT_SYSTEM, "metric") == "metric"
        )

        # Excess mileage pricing (optional). Price is per displayed distance
        # unit (km or miles) — the same unit the user sees in the UI.
        self._excess_price = float(entry.data.get(CONF_EXCESS_PRICE, 0.0) or 0.0)
        # The config selector stores a lowercase key (e.g. "eur"); map it to the
        # ISO 4217 code (e.g. "EUR") that HA's monetary device_class expects.
        currency_key = str(entry.data.get(CONF_CURRENCY, "eur")).lower()
        self._currency = CURRENCY_ISO_CODES.get(currency_key, "EUR")
        self._currency_symbol = CURRENCY_SYMBOLS.get(self._currency, self._currency)

        # Detect unit system from the source entity (preferred). If the source
        # entity isn't available yet, this falls back to the manual choice.
        self._is_metric, reason = _detect_source_unit_is_metric(
            hass, self._current_km_entity, self._fallback_is_metric
        )
        _LOGGER.debug(
            "Leasing Tracker (%s): is_metric=%s via %s (source=%s, fallback_metric=%s)",
            sensor_type,
            self._is_metric,
            reason,
            self._current_km_entity,
            self._fallback_is_metric,
        )

        # Device Info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Leasing Tracker",
            model="Car Leasing Monitor",
        )

        # Sensor-specific attributes (units, icons, device class, ...)
        self._setup_sensor_attributes()

    def _refresh_unit_system(self) -> bool:
        """Re-detect the unit system from the source entity.

        Returns True if the unit system changed (and attributes were refreshed).
        """
        new_is_metric, reason = _detect_source_unit_is_metric(
            self.hass, self._current_km_entity, self._fallback_is_metric
        )
        if new_is_metric != self._is_metric:
            _LOGGER.debug(
                "Leasing Tracker (%s): unit system changed metric=%s -> metric=%s via %s",
                self._sensor_type,
                self._is_metric,
                new_is_metric,
                reason,
            )
            self._is_metric = new_is_metric
            self._setup_sensor_attributes()
            # Also push the new unit into the entity registry so HA stops
            # auto-converting based on the old override.
            self._sync_registry_unit()
            return True
        return False

    def _setup_sensor_attributes(self) -> None:
        """Set up sensor-specific attributes."""
        distance_unit = (
            UnitOfLength.KILOMETERS if self._is_metric else UnitOfLength.MILES
        )
        per_day_unit = "km/day" if self._is_metric else "mi/day"
        per_month_unit = "km/month" if self._is_metric else "mi/month"

        sensor_configs = {
            SENSOR_REMAINING_KM_TOTAL: {
                "translation_key": "remaining_km_total",
                "icon": "mdi:counter",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_YEAR: {
                "translation_key": "remaining_km_year",
                "icon": "mdi:calendar-clock",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_MONTH: {
                "translation_key": "remaining_km_month",
                "icon": "mdi:calendar-month",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_YEAR_ACTUAL: {
                "translation_key": "remaining_km_year_actual",
                "icon": "mdi:calendar-today",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_REMAINING_KM_MONTH_ACTUAL: {
                "translation_key": "remaining_km_month_actual",
                "icon": "mdi:calendar-today",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ESTIMATED_KM_YEAR_END: {
                "translation_key": "estimated_km_year_end",
                "icon": "mdi:chart-timeline-variant",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ESTIMATED_KM_MONTH_END: {
                "translation_key": "estimated_km_month_end",
                "icon": "mdi:chart-timeline-variant",
                "unit": distance_unit,
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
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            SENSOR_KM_DRIVEN_THIS_MONTH: {
                "translation_key": "km_driven_this_month",
                "icon": "mdi:calendar-month",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_KM_DRIVEN_THIS_YEAR: {
                "translation_key": "km_driven_this_year",
                "icon": "mdi:calendar",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_KM_PER_DAY_AVERAGE: {
                "translation_key": "km_per_day_average",
                "icon": "mdi:chart-line",
                "unit": per_day_unit,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_KM_PER_MONTH_AVERAGE: {
                "translation_key": "km_per_month_average",
                "icon": "mdi:chart-bar",
                "unit": per_month_unit,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_TOTAL: {
                "translation_key": "allowed_km_total",
                "icon": "mdi:sign-direction",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_PER_MONTH: {
                "translation_key": "allowed_km_per_month",
                "icon": "mdi:calendar-month",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_THIS_YEAR: {
                "translation_key": "allowed_km_this_year",
                "icon": "mdi:calendar",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ALLOWED_KM_THIS_MONTH: {
                "translation_key": "allowed_km_this_month",
                "icon": "mdi:calendar-month",
                "unit": distance_unit,
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
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_STATUS: {
                "translation_key": "status",
                "icon": "mdi:information-outline",
                "device_class": SensorDeviceClass.ENUM,
                "options": ["on_plan", "over_plan", "significantly_over_plan", "under_plan"],
            },
            SENSOR_END_DATE: {
                "translation_key": "end_date",
                "icon": "mdi:calendar-end",
                "device_class": SensorDeviceClass.TIMESTAMP,
            },
            SENSOR_ESTIMATED_KM_LEASE_END: {
                "translation_key": "estimated_km_lease_end",
                "icon": "mdi:map-marker-distance",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ESTIMATED_EXCESS_KM: {
                "translation_key": "estimated_excess_km",
                "icon": "mdi:alert-circle-outline",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ESTIMATED_EXCESS_COST: {
                "translation_key": "estimated_excess_cost",
                "icon": "mdi:cash-multiple",
                "unit": self._currency,
                "device_class": SensorDeviceClass.MONETARY,
            },
        }

        config = sensor_configs.get(self._sensor_type, {})

        # Set translation key instead of name
        self._attr_translation_key = config.get("translation_key")
        self._attr_icon = config.get("icon")
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")

        # For DISTANCE sensors, Home Assistant would otherwise auto-convert
        # the displayed unit based on the user's HA-wide unit system. Setting
        # suggested_unit_of_measurement explicitly tells HA to use OUR unit
        # regardless of the global metric/imperial setting. This is what
        # actually makes the sensor display in the unit we want.
        if config.get("device_class") == SensorDeviceClass.DISTANCE:
            self._attr_suggested_unit_of_measurement = config.get("unit")
        else:
            self._attr_suggested_unit_of_measurement = None

        # For enum sensors (like status)
        if config.get("options"):
            self._attr_options = config.get("options")

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        # The source entity may not have been ready when __init__ ran.
        # Re-check now so the unit picks up correctly on the first refresh.
        self._refresh_unit_system()

        # Sync the entity registry's stored unit_of_measurement to the unit we
        # want. This is necessary because:
        #  1. For DISTANCE sensors HA auto-converts the display to the user's
        #     HA-wide unit system unless an explicit override is stored.
        #  2. suggested_unit_of_measurement only takes effect on FIRST
        #     registration; existing entities keep whatever override was
        #     stored before. So we update the override directly here so the
        #     fix also works for users who installed an older version.
        self._sync_registry_unit()

        @callback
        def sensor_state_listener(event):
            """Handle sensor state changes."""
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._current_km_entity], sensor_state_listener
            )
        )

    @callback
    def _sync_registry_unit(self) -> None:
        """Make sure the entity registry's unit override matches our unit.

        For DISTANCE sensors only — these are the ones HA would otherwise
        auto-convert. For all other sensors HA leaves the unit alone.
        """
        if self._attr_device_class != SensorDeviceClass.DISTANCE:
            return
        if self.entity_id is None:
            return

        desired_unit = self._attr_native_unit_of_measurement
        if desired_unit is None:
            return

        registry = er.async_get(self.hass)
        entry = registry.async_get(self.entity_id)
        if entry is None:
            return

        # The "effective" stored unit comes from sensor options first
        # (which is what suggested_unit_of_measurement gets persisted to),
        # then falls back to the top-level unit_of_measurement.
        sensor_options = entry.options.get("sensor", {}) if entry.options else {}
        current_unit = sensor_options.get("unit_of_measurement")
        if current_unit is None:
            current_unit = entry.unit_of_measurement

        if current_unit != desired_unit:
            _LOGGER.debug(
                "Leasing Tracker (%s): updating registry unit %s -> %s",
                self._sensor_type,
                current_unit,
                desired_unit,
            )
            registry.async_update_entity_options(
                self.entity_id,
                "sensor",
                {"unit_of_measurement": desired_unit},
            )

    def update(self) -> None:
        """Update the sensor."""
        # Always re-check the source entity's unit of measurement. Some
        # integrations only set it after the first state update.
        self._refresh_unit_system()

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

        # Determine the source entity's unit explicitly (independent of the
        # sensor's own display unit) so the value is converted correctly.
        sensor_unit = current_km_state.attributes.get("unit_of_measurement")
        if sensor_unit is not None:
            sensor_unit_normalized = str(sensor_unit).strip().lower()
        else:
            # No unit on the source -> assume it matches the user's choice
            sensor_unit_normalized = "km" if self._fallback_is_metric else "mi"

        source_is_miles = sensor_unit_normalized in MILE_UNITS

        # All internal calculations are done in kilometers. Convert the source
        # value to km if necessary.
        if source_is_miles:
            current_km = current_km_raw * MILES_TO_KM
        else:
            current_km = current_km_raw

        # Get config values
        start_date = datetime.fromisoformat(self._entry.data[CONF_START_DATE])
        end_date = datetime.fromisoformat(self._entry.data[CONF_END_DATE])
        start_km_config = self._entry.data[CONF_START_KM]
        km_per_year_config = self._entry.data[CONF_KM_PER_YEAR]

        # The user enters start_km / km_per_year in whichever unit matches the
        # display unit (i.e. the source entity's unit). Convert those config
        # values to km so the internal math stays in km.
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

        # Status thresholds in km
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

        # --- Lease-end projection (all in km internally) ---
        # Estimated total odometer reading at the end of the lease, based on
        # the average distance per day driven so far.
        if remaining_days > 0:
            estimated_km_lease_end = current_km + (remaining_days * km_per_day)
        else:
            # Lease already ended -> use the current reading
            estimated_km_lease_end = current_km

        # Estimated total distance driven over the whole lease.
        estimated_total_driven = estimated_km_lease_end - start_km

        # Estimated excess distance = projected total driven minus the total
        # allowance. Clamped at 0 (no negative excess).
        estimated_excess_km = estimated_total_driven - allowed_km_total
        if estimated_excess_km < 0:
            estimated_excess_km = 0

        # Estimated excess cost. The price was entered per DISPLAY unit
        # (km or miles), so convert the excess to the display unit first.
        if not self._is_metric:
            estimated_excess_display = estimated_excess_km * KM_TO_MILES
        else:
            estimated_excess_display = estimated_excess_km
        estimated_excess_cost = estimated_excess_display * self._excess_price

        # The end_date is a naive datetime (local midnight). TIMESTAMP device
        # class requires a timezone-aware datetime. start_of_local_day returns
        # midnight of the given date in HA's configured timezone, correctly
        # handling DST and historical offsets (unlike a plain tzinfo replace).
        end_date_localized = dt_util.start_of_local_day(end_date.date())

        # Set value based on sensor type (distance values still in km here)
        value_map = {
            SENSOR_REMAINING_KM_TOTAL: remaining_km_total,
            SENSOR_REMAINING_KM_YEAR: remaining_km_year_estimated,
            SENSOR_REMAINING_KM_MONTH: remaining_km_month_estimated,
            SENSOR_REMAINING_KM_YEAR_ACTUAL: remaining_km_year_actual,
            SENSOR_REMAINING_KM_MONTH_ACTUAL: remaining_km_month_actual,
            SENSOR_ESTIMATED_KM_YEAR_END: estimated_km_year_end,
            SENSOR_ESTIMATED_KM_MONTH_END: estimated_km_month_end,
            SENSOR_REMAINING_DAYS: remaining_days,
            SENSOR_REMAINING_MONTHS: round(remaining_months, 1),
            SENSOR_TOTAL_KM_DRIVEN: total_km_driven,
            SENSOR_KM_DRIVEN_THIS_MONTH: km_driven_this_month,
            SENSOR_KM_DRIVEN_THIS_YEAR: km_driven_this_year,
            SENSOR_KM_PER_DAY_AVERAGE: km_per_day,
            SENSOR_KM_PER_MONTH_AVERAGE: km_per_month,
            SENSOR_ALLOWED_KM_TOTAL: allowed_km_total,
            SENSOR_ALLOWED_KM_PER_MONTH: allowed_km_per_month,
            SENSOR_ALLOWED_KM_THIS_YEAR: allowed_km_this_year,
            SENSOR_ALLOWED_KM_THIS_MONTH: allowed_km_this_month,
            SENSOR_DAYS_TOTAL: total_days,
            SENSOR_PROGRESS_PERCENTAGE: round(progress, 1),
            SENSOR_KM_DIFFERENCE: km_difference,
            SENSOR_STATUS: status,
            SENSOR_END_DATE: end_date_localized,
            SENSOR_ESTIMATED_KM_LEASE_END: estimated_km_lease_end,
            SENSOR_ESTIMATED_EXCESS_KM: estimated_excess_km,
            SENSOR_ESTIMATED_EXCESS_COST: round(estimated_excess_cost, 2),
        }

        value = value_map.get(self._sensor_type)

        # Distance-class sensors are stored/calculated in km. Convert to miles
        # for display when the sensor's display unit is miles.
        distance_sensors = {
            SENSOR_REMAINING_KM_TOTAL,
            SENSOR_REMAINING_KM_YEAR,
            SENSOR_REMAINING_KM_MONTH,
            SENSOR_REMAINING_KM_YEAR_ACTUAL,
            SENSOR_REMAINING_KM_MONTH_ACTUAL,
            SENSOR_ESTIMATED_KM_YEAR_END,
            SENSOR_ESTIMATED_KM_MONTH_END,
            SENSOR_TOTAL_KM_DRIVEN,
            SENSOR_KM_DRIVEN_THIS_MONTH,
            SENSOR_KM_DRIVEN_THIS_YEAR,
            SENSOR_ALLOWED_KM_TOTAL,
            SENSOR_ALLOWED_KM_PER_MONTH,
            SENSOR_ALLOWED_KM_THIS_YEAR,
            SENSOR_ALLOWED_KM_THIS_MONTH,
            SENSOR_KM_DIFFERENCE,
            SENSOR_ESTIMATED_KM_LEASE_END,
            SENSOR_ESTIMATED_EXCESS_KM,
        }

        if self._sensor_type in distance_sensors and isinstance(value, (int, float)):
            if not self._is_metric:
                value = value * KM_TO_MILES
            value = round(value)
        elif self._sensor_type == SENSOR_KM_PER_DAY_AVERAGE and isinstance(
            value, (int, float)
        ):
            if not self._is_metric:
                value = value * KM_TO_MILES
            value = round(value, 2)
        elif self._sensor_type == SENSOR_KM_PER_MONTH_AVERAGE and isinstance(
            value, (int, float)
        ):
            if not self._is_metric:
                value = value * KM_TO_MILES
            value = round(value)

        self._attr_native_value = value
