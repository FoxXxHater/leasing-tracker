"""Shared calculation coordinator for Leasing Tracker.

All sensors of a single config entry derive their value from the same set of
calculations. Instead of every sensor recomputing the full set (and throwing
all but one number away), the coordinator computes the complete value map once
per source-entity change and every sensor reads its own key from it.
"""
from __future__ import annotations

from datetime import date, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CURRENT_KM_ENTITY,
    CONF_END_DATE,
    CONF_EXCESS_PRICE,
    CONF_HAS_REFUND,
    CONF_HAS_TOLERANCE,
    CONF_KM_PER_YEAR,
    CONF_MAX_REFUND_DISTANCE,
    CONF_REFUND_LIMIT_MODE,
    CONF_REFUND_PRICE,
    CONF_START_DATE,
    CONF_START_KM,
    CONF_TOLERANCE_OVER,
    CONF_TOLERANCE_UNDER,
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

# States that mean the source entity has no usable numeric value.
_UNUSABLE_STATES = ("unknown", "unavailable")


class LeasingTrackerCoordinator(DataUpdateCoordinator[dict[str, Any] | None]):
    """Compute every Leasing Tracker value once per source-entity change.

    The coordinator is push-driven: it has no polling interval and is refreshed
    by a state-change listener on the source odometer entity (registered in
    ``__init__.py``). ``data`` is the full value map, or ``None`` when the
    source entity is missing or does not hold a number.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Parse the (static) contract config once and prepare the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=None,
        )
        self.source_entity_id: str = entry.data[CONF_CURRENT_KM_ENTITY]

        # Contract config is static for the life of the entry: an options change
        # reloads the entry and rebuilds the coordinator, so it is safe (and
        # cheaper) to parse these once here instead of on every update.
        self._start_date = datetime.fromisoformat(entry.data[CONF_START_DATE])
        self._end_date = datetime.fromisoformat(entry.data[CONF_END_DATE])
        self._start_distance = float(entry.data[CONF_START_KM])
        self._distance_per_year = float(entry.data[CONF_KM_PER_YEAR])

        self._has_tolerance = bool(entry.data.get(CONF_HAS_TOLERANCE, False))
        self._tolerance_over = float(entry.data.get(CONF_TOLERANCE_OVER, 0) or 0)
        self._tolerance_under = float(entry.data.get(CONF_TOLERANCE_UNDER, 0) or 0)

        self._excess_price = float(entry.data.get(CONF_EXCESS_PRICE, 0.0) or 0.0)

        self._has_refund = bool(entry.data.get(CONF_HAS_REFUND, False))
        self._refund_price = float(entry.data.get(CONF_REFUND_PRICE, 0.0) or 0.0)
        self._refund_limit_mode = str(
            entry.data.get(CONF_REFUND_LIMIT_MODE, "unlimited")
        ).lower()
        self._max_refund_distance = float(
            entry.data.get(CONF_MAX_REFUND_DISTANCE, 0) or 0
        )

    async def _async_update_data(self) -> dict[str, Any] | None:
        """Return the full value map (pure computation, never raises)."""
        return self._compute()

    @callback
    def _handle_source_change(self, event: Event) -> None:
        """React to a source-entity state change by recomputing synchronously.

        The computation is pure and cheap, so there is no need to hop through
        the executor; setting the data directly on the loop is both correct and
        faster than scheduling an async refresh.
        """
        self.async_set_updated_data(self._compute())

    @callback
    def _compute(self) -> dict[str, Any] | None:
        """Compute every sensor value from the current source-entity state.

        Returns ``None`` when the source entity is unavailable or its state is
        not a number, which the sensors surface as "unavailable".
        """
        state = self.hass.states.get(self.source_entity_id)
        if state is None or state.state in _UNUSABLE_STATES:
            return None

        try:
            current_distance = float(state.state)
        except (ValueError, TypeError):
            return None

        # ------------------------------------------------------------------
        # UNIT MODEL
        #
        # The display unit is derived from the source entity's unit. The source
        # value is therefore ALREADY in the display unit, and the user enters
        # start_distance, distance_per_year, the tolerance band and all prices
        # in that same unit. Consequently NO unit conversion happens here: every
        # value below is in the display unit. The only unit-sensitive logic is
        # the status fallback, which is expressed as a fraction of the allowance
        # and is therefore unit-free by construction.
        # ------------------------------------------------------------------
        start_distance = self._start_distance
        distance_per_year = self._distance_per_year

        # Work in local calendar dates. Using dates (not datetimes) keeps the
        # day arithmetic exact: a datetime carries a time-of-day component, so
        # e.g. (Dec 31 00:00 - now) would floor to -1 on the afternoon of the
        # last day. dt_util.now() is Home Assistant's timezone-aware "now";
        # taking .date() gives today's local calendar date.
        today = dt_util.now().date()
        start_date = self._start_date.date()
        end_date = self._end_date.date()

        total_days = (end_date - start_date).days
        elapsed_days = (today - start_date).days
        remaining_days = (end_date - today).days

        # Current year/month
        year_start = date(today.year, 1, 1)
        year_end = date(today.year, 12, 31)
        month_start = date(today.year, today.month, 1)

        # Days in current periods
        days_in_year = (year_end - year_start).days + 1
        if today.month == 12:
            days_in_month = (year_end - month_start).days + 1
        else:
            next_month = date(today.year, today.month + 1, 1)
            days_in_month = (next_month - month_start).days

        # Remaining days in periods
        remaining_days_year = (year_end - today).days
        if today.month == 12:
            remaining_days_month = (year_end - today).days
        else:
            next_month = date(today.year, today.month + 1, 1)
            remaining_days_month = (next_month - today).days

        # Total driven
        total_distance_driven = current_distance - start_distance

        # Allowed distance
        allowed_distance_total = (total_days / 365.25) * distance_per_year
        allowed_distance_per_month = distance_per_year / 12

        # Year calculations
        if year_start >= start_date:
            days_into_year = (today - year_start).days
            allowed_distance_this_year = (days_into_year / days_in_year) * distance_per_year

            # Find distance at year start
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
            days_into_month = (today - month_start).days
            allowed_distance_this_month = (days_into_month / days_in_month) * allowed_distance_per_month

            # Find distance at month start
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

        # Remaining distance
        remaining_distance_total = allowed_distance_total - total_distance_driven
        remaining_distance_year_actual = allowed_distance_this_year - distance_driven_this_year
        remaining_distance_month_actual = allowed_distance_this_month - distance_driven_this_month

        # Estimated remaining distance (at current pace)
        remaining_distance_year_estimated = remaining_days_year * distance_per_day
        remaining_distance_month_estimated = remaining_days_month * distance_per_day

        # Estimated total distance at end of periods
        estimated_distance_month_end = current_distance + remaining_distance_month_estimated
        estimated_distance_year_end = current_distance + remaining_distance_year_estimated

        # Difference and progress. total_days is >= 1 in practice (the config
        # flow rejects end <= start), but guard the division anyway so a bad
        # entry can never raise ZeroDivisionError.
        if total_days > 0:
            pro_rata_fraction = elapsed_days / total_days
        else:
            pro_rata_fraction = 0
        distance_difference = total_distance_driven - (pro_rata_fraction * allowed_distance_total)
        progress = pro_rata_fraction * 100

        # --- Tolerance band (already in the display unit) -------------------
        tolerance_over = self._tolerance_over
        tolerance_under = self._tolerance_under

        # --- Status ---------------------------------------------------------
        # distance_difference is the signed deviation from the pro-rata
        # allowance, in the display unit. Thresholds come from the configured
        # tolerance band when the contract has one, otherwise from a fraction of
        # the total allowance so the result is identical in km and miles.
        if self._has_tolerance:
            status_tol_over = tolerance_over
            status_tol_under = tolerance_under
        else:
            default_tol = abs(allowed_distance_total) * STATUS_DEFAULT_TOLERANCE_FRACTION
            status_tol_over = default_tol
            status_tol_under = default_tol

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

        # --- Lease-end projection -------------------------------------------
        if remaining_days > 0:
            estimated_distance_lease_end = current_distance + (remaining_days * distance_per_day)
        else:
            # Lease already ended -> use the current reading
            estimated_distance_lease_end = current_distance

        estimated_total_driven = estimated_distance_lease_end - start_distance

        # Signed deviation from the total allowance at lease end.
        deviation = estimated_total_driven - allowed_distance_total

        # Apply the tolerance band ("goodwill"). Distance inside the band is
        # neither charged nor refunded. Both sides are independent.
        if deviation > tolerance_over:
            estimated_excess = deviation - tolerance_over
            estimated_under = 0.0
        elif deviation < -tolerance_under:
            estimated_excess = 0.0
            estimated_under = abs(deviation) - tolerance_under
        else:
            estimated_excess = 0.0
            estimated_under = 0.0

        # Cap the refundable distance if the contract limits it.
        if self._refund_limit_mode == REFUND_LIMIT_LIMITED:
            refundable_under = min(estimated_under, self._max_refund_distance)
        else:
            refundable_under = estimated_under

        # Prices are per display unit, and the distances above are already in
        # the display unit, so these multiply directly.
        estimated_excess_cost = estimated_excess * self._excess_price
        estimated_refund = refundable_under * self._refund_price

        # Net settlement: what you pay minus what you get back.
        estimated_net_cost = estimated_excess_cost - estimated_refund

        # TIMESTAMP device class requires a timezone-aware datetime.
        # start_of_local_day returns midnight of the given date in HA's
        # configured timezone, correctly handling DST and historical offsets.
        end_date_localized = dt_util.start_of_local_day(end_date)

        return {
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
