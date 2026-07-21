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
    CONF_HAS_REFUND,
    CONF_HAS_TOLERANCE,
    CONF_KM_PER_YEAR,
    CONF_MAX_REFUND_DISTANCE,
    CONF_NAME,
    CONF_REFUND_LIMIT_MODE,
    CONF_REFUND_PRICE,
    CONF_START_DATE,
    CONF_START_KM,
    CONF_TOLERANCE_OVER,
    CONF_TOLERANCE_UNDER,
    DEFAULT_CURRENCY,
    DOMAIN,
    REFUND_LIMIT_LIMITED,
    STATUS_DEFAULT_TOLERANCE_FRACTION,
    STATUS_SIGNIFICANT_FRACTION,
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
    SENSOR_ESTIMATED_NET_COST,
    SENSOR_ESTIMATED_REFUND,
    SENSOR_ESTIMATED_UNDER_KM,
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
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_UNDER_KM),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_REFUND),
        LeasingTrackerSensor(hass, entry, name, SENSOR_ESTIMATED_NET_COST),
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
        # Currency is a free-text ISO 4217 code. Fall back to the currency
        # configured in Home Assistant (hass.config.currency), and finally to
        # EUR. It is used as the unit of the monetary sensors.
        currency = entry.data.get(CONF_CURRENCY)
        if not currency:
            currency = getattr(hass.config, "currency", None) or DEFAULT_CURRENCY
        self._currency = str(currency).strip().upper()

        # --- Contract terms -------------------------------------------------
        # Tolerance band ("goodwill"): distance above/below the allowance that
        # is not charged and not refunded. Entered in the DISPLAY unit.
        self._has_tolerance = bool(entry.data.get(CONF_HAS_TOLERANCE, False))
        self._tolerance_over = float(entry.data.get(CONF_TOLERANCE_OVER, 0) or 0)
        self._tolerance_under = float(entry.data.get(CONF_TOLERANCE_UNDER, 0) or 0)

        # Refund for under-driven distance. Also entered in the DISPLAY unit.
        self._has_refund = bool(entry.data.get(CONF_HAS_REFUND, False))
        self._refund_price = float(entry.data.get(CONF_REFUND_PRICE, 0.0) or 0.0)
        self._refund_limit_mode = str(
            entry.data.get(CONF_REFUND_LIMIT_MODE, "unlimited")
        ).lower()
        self._max_refund_distance = float(
            entry.data.get(CONF_MAX_REFUND_DISTANCE, 0) or 0
        )

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
            SENSOR_ESTIMATED_UNDER_KM: {
                "translation_key": "estimated_under_km",
                "icon": "mdi:arrow-down-circle-outline",
                "unit": distance_unit,
                "device_class": SensorDeviceClass.DISTANCE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            SENSOR_ESTIMATED_REFUND: {
                "translation_key": "estimated_refund",
                "icon": "mdi:cash-refund",
                "unit": self._currency,
                "device_class": SensorDeviceClass.MONETARY,
            },
            SENSOR_ESTIMATED_NET_COST: {
                "translation_key": "estimated_net_cost",
                "icon": "mdi:scale-balance",
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
            current_raw = float(current_km_state.state)
        except (ValueError, TypeError):
            self._attr_native_value = None
            self._attr_available = False
            return

        self._attr_available = True

        # ------------------------------------------------------------------
        # UNIT MODEL
        #
        # The display unit is *derived from* the source entity's unit
        # (see _detect_source_unit_is_metric). When the source reports miles,
        # the sensors display miles; when it reports km, they display km.
        # The source value is therefore ALREADY in the display unit.
        #
        # The user also enters start_distance, distance_per_year, the tolerance band and
        # all prices in that same display unit.
        #
        # Consequently every value below is in the display unit and NO unit
        # conversion happens anywhere in this method. Converting to km and
        # back would be a lossy no-op, and it used to produce wrong results
        # when the source carried an unrecognised unit (the raw value was
        # read as km while the config values were read as miles).
        #
        # The only unit-sensitive logic left is the status fallback, which is
        # expressed as a *fraction* of the allowance and is therefore
        # unit-free by construction.
        # ------------------------------------------------------------------
        current_distance = current_raw

        # Get config values (already in the display unit)
        start_date = datetime.fromisoformat(self._entry.data[CONF_START_DATE])
        end_date = datetime.fromisoformat(self._entry.data[CONF_END_DATE])
        start_distance = float(self._entry.data[CONF_START_KM])
        distance_per_year = float(self._entry.data[CONF_KM_PER_YEAR])

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
        total_distance_driven = current_distance - start_distance

        # Allowed KM
        allowed_distance_total = (total_days / 365.25) * distance_per_year
        allowed_distance_per_month = distance_per_year / 12

        # Year calculations
        if year_start >= start_date:
            days_into_year = (now - year_start).days
            allowed_distance_this_year = (days_into_year / days_in_year) * distance_per_year

            # Find KM at year start
            if year_start > start_date:
                days_at_year_start = (year_start - start_date).days
                allowed_distance_at_year_start = (days_at_year_start / total_days) * allowed_distance_total + start_distance
            else:
                allowed_distance_at_year_start = start_distance

            distance_driven_this_year = current_distance - allowed_distance_at_year_start
        else:
            distance_driven_this_year = total_distance_driven
            allowed_distance_this_year = (elapsed_days / 365.25) * distance_per_year

        # Month calculations
        if month_start >= start_date:
            days_into_month = (now - month_start).days
            allowed_distance_this_month = (days_into_month / days_in_month) * allowed_distance_per_month

            # Find KM at month start
            if month_start > start_date:
                days_at_month_start = (month_start - start_date).days
                allowed_distance_at_month_start = (days_at_month_start / total_days) * allowed_distance_total + start_distance
            else:
                allowed_distance_at_month_start = start_distance

            distance_driven_this_month = current_distance - allowed_distance_at_month_start
        else:
            distance_driven_this_month = total_distance_driven
            allowed_distance_this_month = (elapsed_days / 30.44) * allowed_distance_per_month

        # Averages
        if elapsed_days > 0:
            distance_per_day = total_distance_driven / elapsed_days
            distance_per_month = total_distance_driven / (elapsed_days / 30.44)
        else:
            distance_per_day = 0
            distance_per_month = 0

        # Remaining KM
        remaining_distance_total = allowed_distance_total - total_distance_driven
        remaining_distance_year_actual = allowed_distance_this_year - distance_driven_this_year
        remaining_distance_month_actual = allowed_distance_this_month - distance_driven_this_month

        # Estimated remaining KM (at current pace)
        remaining_distance_year_estimated = remaining_days_year * distance_per_day
        remaining_distance_month_estimated = remaining_days_month * distance_per_day

        # Estimated total KM at end of periods
        estimated_distance_month_end = current_distance + remaining_distance_month_estimated
        estimated_distance_year_end = current_distance + remaining_distance_year_estimated

        # Difference
        distance_difference = total_distance_driven - ((elapsed_days / total_days) * allowed_distance_total)

        # Progress
        progress = (elapsed_days / total_days) * 100 if total_days > 0 else 0

        # --- Tolerance band (already in the display unit) -------------------
        tolerance_over = self._tolerance_over
        tolerance_under = self._tolerance_under

        # --- Status -----------------------------------------------------------
        # distance_difference is the signed deviation from the pro-rata
        # allowance, in the display unit.
        #
        # Thresholds come from the configured tolerance band when the contract
        # has one. Otherwise they fall back to a *fraction* of the total
        # allowance. Because both sides of the comparison are in the same unit
        # and the fallback is relative, the status is identical whether the
        # user tracks kilometers or miles.
        if self._has_tolerance:
            status_tol_over = tolerance_over
            status_tol_under = tolerance_under
        else:
            default_tol = abs(allowed_distance_total) * STATUS_DEFAULT_TOLERANCE_FRACTION
            status_tol_over = default_tol
            status_tol_under = default_tol

        # Beyond this, the overage is "significant" rather than merely "over".
        significant_over = status_tol_over + (
            abs(allowed_distance_total) * STATUS_SIGNIFICANT_FRACTION
        )

        if distance_difference < -status_tol_under:
            status = "under_plan"
        elif distance_difference <= status_tol_over:
            status = "on_plan"
        elif distance_difference <= significant_over:
            status = "over_plan"
        else:
            status = "significantly_over_plan"

        # Remaining months
        remaining_months = remaining_days / 30.44

        # --- Lease-end projection (all in km internally) ---
        # Estimated total odometer reading at the end of the lease, based on
        # the average distance per day driven so far.
        if remaining_days > 0:
            estimated_distance_lease_end = current_distance + (remaining_days * distance_per_day)
        else:
            # Lease already ended -> use the current reading
            estimated_distance_lease_end = current_distance

        # Estimated total distance driven over the whole lease.
        estimated_total_driven = estimated_distance_lease_end - start_distance

        # Signed deviation from the total allowance at lease end.
        # Positive -> driving too much, negative -> driving too little.
        deviation = estimated_total_driven - allowed_distance_total

        # Apply the tolerance band ("goodwill"). Distance inside the band is
        # neither charged nor refunded. Both sides are independent, so a
        # contract can allow e.g. +2500 but only -1000.
        if deviation > tolerance_over:
            estimated_excess = deviation - tolerance_over
            estimated_under = 0.0
        elif deviation < -tolerance_under:
            estimated_excess = 0.0
            estimated_under = abs(deviation) - tolerance_under
        else:
            # Inside the tolerance band -> nothing to charge, nothing to refund
            estimated_excess = 0.0
            estimated_under = 0.0

        # Cap the refundable distance if the contract limits it.
        # `unlimited` means no cap; `limited` caps at max_refund_distance.
        if self._refund_limit_mode == REFUND_LIMIT_LIMITED:
            refundable_under = min(estimated_under, self._max_refund_distance)
        else:
            refundable_under = estimated_under

        # Prices are per display unit, and the distances above are already in
        # the display unit, so these multiply directly.
        estimated_excess_cost = estimated_excess * self._excess_price
        estimated_refund = refundable_under * self._refund_price

        # Net settlement: what you pay minus what you get back.
        # Negative means the lessor owes you money.
        estimated_net_cost = estimated_excess_cost - estimated_refund

        # The end_date is a naive datetime (local midnight). TIMESTAMP device
        # class requires a timezone-aware datetime. start_of_local_day returns
        # midnight of the given date in HA's configured timezone, correctly
        # handling DST and historical offsets (unlike a plain tzinfo replace).
        end_date_localized = dt_util.start_of_local_day(end_date.date())

        # Set value based on sensor type (distance values still in km here)
        value_map = {
            SENSOR_REMAINING_KM_TOTAL: remaining_distance_total,
            SENSOR_REMAINING_KM_YEAR: remaining_distance_year_estimated,
            SENSOR_REMAINING_KM_MONTH: remaining_distance_month_estimated,
            SENSOR_REMAINING_KM_YEAR_ACTUAL: remaining_distance_year_actual,
            SENSOR_REMAINING_KM_MONTH_ACTUAL: remaining_distance_month_actual,
            SENSOR_ESTIMATED_KM_YEAR_END: estimated_distance_year_end,
            SENSOR_ESTIMATED_KM_MONTH_END: estimated_distance_month_end,
            SENSOR_REMAINING_DAYS: remaining_days,
            SENSOR_REMAINING_MONTHS: round(remaining_months, 1),
            SENSOR_TOTAL_KM_DRIVEN: total_distance_driven,
            SENSOR_KM_DRIVEN_THIS_MONTH: distance_driven_this_month,
            SENSOR_KM_DRIVEN_THIS_YEAR: distance_driven_this_year,
            SENSOR_KM_PER_DAY_AVERAGE: distance_per_day,
            SENSOR_KM_PER_MONTH_AVERAGE: distance_per_month,
            SENSOR_ALLOWED_KM_TOTAL: allowed_distance_total,
            SENSOR_ALLOWED_KM_PER_MONTH: allowed_distance_per_month,
            SENSOR_ALLOWED_KM_THIS_YEAR: allowed_distance_this_year,
            SENSOR_ALLOWED_KM_THIS_MONTH: allowed_distance_this_month,
            SENSOR_DAYS_TOTAL: total_days,
            SENSOR_PROGRESS_PERCENTAGE: round(progress, 1),
            SENSOR_KM_DIFFERENCE: distance_difference,
            SENSOR_STATUS: status,
            SENSOR_END_DATE: end_date_localized,
            SENSOR_ESTIMATED_KM_LEASE_END: estimated_distance_lease_end,
            SENSOR_ESTIMATED_EXCESS_KM: estimated_excess,
            SENSOR_ESTIMATED_EXCESS_COST: round(estimated_excess_cost, 2),
            SENSOR_ESTIMATED_UNDER_KM: estimated_under,
            SENSOR_ESTIMATED_REFUND: round(estimated_refund, 2),
            SENSOR_ESTIMATED_NET_COST: round(estimated_net_cost, 2),
        }

        value = value_map.get(self._sensor_type)

        # Every distance value above is already in the display unit (see the
        # UNIT MODEL note at the top of this method), so all that is left is
        # rounding for presentation.
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
            SENSOR_ESTIMATED_UNDER_KM,
        }

        if self._sensor_type in distance_sensors and isinstance(value, (int, float)):
            value = round(value)
        elif self._sensor_type == SENSOR_KM_PER_DAY_AVERAGE and isinstance(
            value, (int, float)
        ):
            value = round(value, 2)
        elif self._sensor_type == SENSOR_KM_PER_MONTH_AVERAGE and isinstance(
            value, (int, float)
        ):
            value = round(value)

        self._attr_native_value = value
