"""Config flow for Leasing Tracker integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_CURRENCY,
    CONF_CURRENT_KM_ENTITY,
    CONF_END_DATE,
    CONF_EXCESS_PRICE,
    CONF_HAS_EXCESS_CHARGE,
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
    CONF_UNIT_SYSTEM,
    DOMAIN,
    REFUND_LIMIT_UNLIMITED,
)

_LOGGER = logging.getLogger(__name__)


def _distance_number() -> selector.NumberSelector:
    """Number selector for a distance value in the display unit."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _price_number() -> selector.NumberSelector:
    """Number selector for a price per distance unit."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            step=0.01,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _refund_limit_select() -> selector.SelectSelector:
    """Selector deciding whether the refund is capped."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=["unlimited", "limited"],
            translation_key="refund_limit_mode",
        )
    )


def _needs_contract_step(data: dict[str, Any]) -> bool:
    """Return True if any contract term was enabled in the first step."""
    return bool(
        data.get(CONF_HAS_TOLERANCE)
        or data.get(CONF_HAS_EXCESS_CHARGE)
        or data.get(CONF_HAS_REFUND)
    )


def _build_contract_schema(
    flags: dict[str, Any], current: dict[str, Any] | None = None
) -> vol.Schema:
    """Build the second-step schema from the answers given in the first step.

    Only the fields belonging to the enabled contract terms are shown.
    `current` pre-fills the fields when editing existing options.
    """
    current = current or {}
    fields: dict[Any, Any] = {}

    if flags.get(CONF_HAS_TOLERANCE):
        fields[
            vol.Optional(
                CONF_TOLERANCE_OVER,
                default=current.get(CONF_TOLERANCE_OVER, 0),
            )
        ] = _distance_number()
        fields[
            vol.Optional(
                CONF_TOLERANCE_UNDER,
                default=current.get(CONF_TOLERANCE_UNDER, 0),
            )
        ] = _distance_number()

    if flags.get(CONF_HAS_EXCESS_CHARGE):
        fields[
            vol.Optional(
                CONF_EXCESS_PRICE,
                default=current.get(CONF_EXCESS_PRICE, 0.0),
            )
        ] = _price_number()

    if flags.get(CONF_HAS_REFUND):
        fields[
            vol.Optional(
                CONF_REFUND_PRICE,
                default=current.get(CONF_REFUND_PRICE, 0.0),
            )
        ] = _price_number()
        fields[
            vol.Required(
                CONF_REFUND_LIMIT_MODE,
                default=current.get(CONF_REFUND_LIMIT_MODE, REFUND_LIMIT_UNLIMITED),
            )
        ] = _refund_limit_select()
        fields[
            vol.Optional(
                CONF_MAX_REFUND_DISTANCE,
                default=current.get(CONF_MAX_REFUND_DISTANCE, 0),
            )
        ] = _distance_number()

    return vol.Schema(fields)


def _apply_contract_defaults(data: dict[str, Any]) -> dict[str, Any]:
    """Fill in neutral defaults for every contract term that is disabled.

    This keeps the sensor code simple: it can always read the keys without
    having to know which parts of the contract the user enabled.
    """
    if not data.get(CONF_HAS_TOLERANCE):
        data[CONF_TOLERANCE_OVER] = 0
        data[CONF_TOLERANCE_UNDER] = 0
    if not data.get(CONF_HAS_EXCESS_CHARGE):
        data[CONF_EXCESS_PRICE] = 0.0
    if not data.get(CONF_HAS_REFUND):
        data[CONF_REFUND_PRICE] = 0.0
        data[CONF_REFUND_LIMIT_MODE] = REFUND_LIMIT_UNLIMITED
        data[CONF_MAX_REFUND_DISTANCE] = 0
    return data


class LeasingTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Leasing Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: base data plus the contract questions."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                if user_input[CONF_END_DATE] <= user_input[CONF_START_DATE]:
                    errors["base"] = "end_before_start"
                else:
                    await self.async_set_unique_id(
                        f"leasing_{user_input[CONF_NAME].lower().replace(' ', '_')}"
                    )
                    self._abort_if_unique_id_configured()

                    self._data = dict(user_input)

                    if _needs_contract_step(self._data):
                        return await self.async_step_contract()

                    return self.async_create_entry(
                        title=self._data[CONF_NAME],
                        data=_apply_contract_defaults(self._data),
                    )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Mein Leasing"): cv.string,
                vol.Required(CONF_CURRENT_KM_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                    )
                ),
                vol.Required(CONF_START_DATE): selector.DateSelector(),
                vol.Required(CONF_END_DATE): selector.DateSelector(),
                vol.Required(CONF_START_KM, default=0): cv.positive_int,
                vol.Required(CONF_KM_PER_YEAR, default=10000): cv.positive_int,
                vol.Required(CONF_UNIT_SYSTEM, default="metric"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["metric", "imperial"],
                        translation_key="unit_system",
                    )
                ),
                vol.Required(CONF_CURRENCY, default="eur"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["eur", "usd", "gbp", "chf"],
                        translation_key="currency",
                    )
                ),
                vol.Optional(CONF_HAS_TOLERANCE, default=False): selector.BooleanSelector(),
                vol.Optional(
                    CONF_HAS_EXCESS_CHARGE, default=False
                ): selector.BooleanSelector(),
                vol.Optional(CONF_HAS_REFUND, default=False): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_contract(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second step: the contract terms the user said they have."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data[CONF_NAME],
                    data=_apply_contract_defaults(self._data),
                )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="contract",
            data_schema=_build_contract_schema(self._data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LeasingTrackerOptionsFlow:
        """Get the options flow for this handler."""
        return LeasingTrackerOptionsFlow(config_entry)


class LeasingTrackerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Leasing Tracker."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the base options and the contract questions."""
        errors: dict[str, str] = {}
        existing = self._config_entry.data

        if user_input is not None:
            try:
                if user_input[CONF_END_DATE] <= user_input[CONF_START_DATE]:
                    errors["base"] = "end_before_start"
                else:
                    self._data = dict(user_input)

                    if _needs_contract_step(self._data):
                        return await self.async_step_contract()

                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data=_apply_contract_defaults(self._data),
                    )
                    return self.async_create_entry(title="", data={})
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Migration: entries created before the contract questions existed
        # only have `excess_price`. Derive the flags from what is stored.
        default_has_excess = existing.get(
            CONF_HAS_EXCESS_CHARGE, float(existing.get(CONF_EXCESS_PRICE, 0) or 0) > 0
        )
        default_has_tolerance = existing.get(
            CONF_HAS_TOLERANCE,
            bool(existing.get(CONF_TOLERANCE_OVER) or existing.get(CONF_TOLERANCE_UNDER)),
        )
        default_has_refund = existing.get(
            CONF_HAS_REFUND, float(existing.get(CONF_REFUND_PRICE, 0) or 0) > 0
        )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME,
                    default=existing.get(CONF_NAME, "Mein Leasing"),
                ): cv.string,
                vol.Required(
                    CONF_CURRENT_KM_ENTITY,
                    default=existing.get(CONF_CURRENT_KM_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                    )
                ),
                vol.Required(
                    CONF_START_DATE,
                    default=existing.get(CONF_START_DATE),
                ): selector.DateSelector(),
                vol.Required(
                    CONF_END_DATE,
                    default=existing.get(CONF_END_DATE),
                ): selector.DateSelector(),
                vol.Required(
                    CONF_START_KM,
                    default=existing.get(CONF_START_KM, 0),
                ): cv.positive_int,
                vol.Required(
                    CONF_KM_PER_YEAR,
                    default=existing.get(CONF_KM_PER_YEAR, 10000),
                ): cv.positive_int,
                vol.Required(
                    CONF_UNIT_SYSTEM,
                    default=existing.get(CONF_UNIT_SYSTEM, "metric"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["metric", "imperial"],
                        translation_key="unit_system",
                    )
                ),
                vol.Required(
                    CONF_CURRENCY,
                    default=existing.get(CONF_CURRENCY, "eur"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["eur", "usd", "gbp", "chf"],
                        translation_key="currency",
                    )
                ),
                vol.Optional(
                    CONF_HAS_TOLERANCE, default=default_has_tolerance
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_HAS_EXCESS_CHARGE, default=default_has_excess
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_HAS_REFUND, default=default_has_refund
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )

    async def async_step_contract(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second options step: the enabled contract terms."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self._data.update(user_input)
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=_apply_contract_defaults(self._data),
                )
                return self.async_create_entry(title="", data={})
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="contract",
            data_schema=_build_contract_schema(
                self._data, dict(self._config_entry.data)
            ),
            errors=errors,
        )
