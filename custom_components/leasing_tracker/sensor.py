"""Sensor platform for Leasing Tracker."""
from __future__ import annotations

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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import LeasingTrackerCoordinator
from .const import (
    CONF_UNIT_SYSTEM,
    CONF_CURRENCY,
    CONF_CURRENT_KM_ENTITY,
    CONF_NAME,
    DEFAULT_CURRENCY,
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

# The order in which the sensors are created (one entity per key).
SENSOR_TYPES: tuple[str, ...] = (
    SENSOR_REMAINING_KM_TOTAL,
    SENSOR_REMAINING_KM_YEAR,
    SENSOR_REMAINING_KM_MONTH,
    SENSOR_REMAINING_KM_YEAR_ACTUAL,
    SENSOR_REMAINING_KM_MONTH_ACTUAL,
    SENSOR_ESTIMATED_KM_YEAR_END,
    SENSOR_ESTIMATED_KM_MONTH_END,
    SENSOR_REMAINING_DAYS,
    SENSOR_REMAINING_MONTHS,
    SENSOR_TOTAL_KM_DRIVEN,
    SENSOR_KM_DRIVEN_THIS_MONTH,
    SENSOR_KM_DRIVEN_THIS_YEAR,
    SENSOR_KM_PER_DAY_AVERAGE,
    SENSOR_KM_PER_MONTH_AVERAGE,
    SENSOR_ALLOWED_KM_TOTAL,
    SENSOR_ALLOWED_KM_PER_MONTH,
    SENSOR_ALLOWED_KM_THIS_YEAR,
    SENSOR_ALLOWED_KM_THIS_MONTH,
    SENSOR_DAYS_TOTAL,
    SENSOR_PROGRESS_PERCENTAGE,
    SENSOR_KM_DIFFERENCE,
    SENSOR_STATUS,
    SENSOR_END_DATE,
    SENSOR_ESTIMATED_KM_LEASE_END,
    SENSOR_ESTIMATED_EXCESS_KM,
    SENSOR_ESTIMATED_EXCESS_COST,
    SENSOR_ESTIMATED_UNDER_KM,
    SENSOR_ESTIMATED_REFUND,
    SENSOR_ESTIMATED_NET_COST,
)

# Distance sensors are rounded to whole units for display. All values are
# already in the display unit (see the UNIT MODEL note in coordinator.py).
_DISTANCE_SENSORS: frozenset[str] = frozenset(
    {
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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Leasing Tracker sensors."""
    coordinator: LeasingTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    async_add_entities(
        LeasingTrackerSensor(coordinator, entry, name, sensor_type)
        for sensor_type in SENSOR_TYPES
    )


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


class LeasingTrackerSensor(CoordinatorEntity[LeasingTrackerCoordinator], SensorEntity):
    """Representation of a Leasing Tracker Sensor.

    All calculations are shared: the entity reads its own value from the
    coordinator's value map and only owns its presentation (unit, icon, rounding).
    """

    _attr_has_entity_name = True
    # Fully push-driven: the coordinator refreshes every sensor when the source
    # odometer changes, so there is nothing to poll for.
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: LeasingTrackerCoordinator,
        entry: ConfigEntry,
        name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._current_km_entity = entry.data[CONF_CURRENT_KM_ENTITY]

        # Fallback unit system from the user's manual choice in the config flow.
        # This is only used if the source entity has no unit_of_measurement.
        self._fallback_is_metric = (
            entry.data.get(CONF_UNIT_SYSTEM, "metric") == "metric"
        )

        # Currency is a free-text ISO 4217 code. Fall back to the currency
        # configured in Home Assistant (hass.config.currency), and finally to
        # EUR. It is used as the unit of the monetary sensors.
        currency = entry.data.get(CONF_CURRENCY)
        if not currency:
            currency = getattr(coordinator.hass.config, "currency", None) or DEFAULT_CURRENCY
        self._currency = str(currency).strip().upper()

        # Detect unit system from the source entity (preferred). If the source
        # entity isn't available yet, this falls back to the manual choice.
        self._is_metric, reason = _detect_source_unit_is_metric(
            coordinator.hass, self._current_km_entity, self._fallback_is_metric
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
        Must run on the event loop: it may update the entity registry.
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
        """Register callbacks and reconcile the stored unit."""
        await super().async_added_to_hass()

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
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        Runs on the event loop, so it is safe to re-detect the unit system and
        update the entity registry here (unlike the old executor-bound update()).
        """
        self._refresh_unit_system()
        super()._handle_coordinator_update()

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

    @property
    def available(self) -> bool:
        """Available only when the coordinator produced a usable value map."""
        return super().available and self.coordinator.data is not None

    @property
    def native_value(self) -> Any:
        """Return this sensor's value from the shared value map."""
        data = self.coordinator.data
        if data is None:
            return None

        value = data.get(self._sensor_type)

        # Every distance value is already in the display unit (see the UNIT
        # MODEL note in coordinator.py), so all that is left is presentation
        # rounding.
        if self._sensor_type in _DISTANCE_SENSORS and isinstance(value, (int, float)):
            return round(value)
        if self._sensor_type == SENSOR_KM_PER_DAY_AVERAGE and isinstance(
            value, (int, float)
        ):
            return round(value, 2)
        if self._sensor_type == SENSOR_KM_PER_MONTH_AVERAGE and isinstance(
            value, (int, float)
        ):
            return round(value)

        return value
