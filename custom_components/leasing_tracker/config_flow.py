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
    CONF_KM_PER_YEAR,
    CONF_NAME,
    CONF_START_DATE,
    CONF_START_KM,
    CONF_UNIT_SYSTEM,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class LeasingTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Leasing Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validierung
            try:
                # Prüfe ob das End-Datum nach dem Start-Datum liegt
                if user_input[CONF_END_DATE] <= user_input[CONF_START_DATE]:
                    errors["base"] = "end_before_start"
                else:
                    # Erstelle eindeutige ID
                    await self.async_set_unique_id(
                        f"leasing_{user_input[CONF_NAME].lower().replace(' ', '_')}"
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input,
                    )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Schema für das Formular
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
                vol.Optional(CONF_EXCESS_PRICE, default=0.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(CONF_CURRENCY, default="eur"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["eur", "usd", "gbp", "chf"],
                        translation_key="currency",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validierung
            try:
                if user_input[CONF_END_DATE] <= user_input[CONF_START_DATE]:
                    errors["base"] = "end_before_start"
                else:
                    # Update der Config Entry
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data=user_input,
                    )
                    return self.async_create_entry(title="", data={})
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Schema mit aktuellen Werten vorbelegen
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME,
                    default=self._config_entry.data.get(CONF_NAME, "Mein Leasing"),
                ): cv.string,
                vol.Required(
                    CONF_CURRENT_KM_ENTITY,
                    default=self._config_entry.data.get(CONF_CURRENT_KM_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                    )
                ),
                vol.Required(
                    CONF_START_DATE,
                    default=self._config_entry.data.get(CONF_START_DATE),
                ): selector.DateSelector(),
                vol.Required(
                    CONF_END_DATE,
                    default=self._config_entry.data.get(CONF_END_DATE),
                ): selector.DateSelector(),
                vol.Required(
                    CONF_START_KM,
                    default=self._config_entry.data.get(CONF_START_KM, 0),
                ): cv.positive_int,
                vol.Required(
                    CONF_KM_PER_YEAR,
                    default=self._config_entry.data.get(CONF_KM_PER_YEAR, 10000),
                ): cv.positive_int,
                vol.Required(
                    CONF_UNIT_SYSTEM,
                    default=self._config_entry.data.get(CONF_UNIT_SYSTEM, "metric"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["metric", "imperial"],
                        translation_key="unit_system",
                    )
                ),
                vol.Optional(
                    CONF_EXCESS_PRICE,
                    default=self._config_entry.data.get(CONF_EXCESS_PRICE, 0.0),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_CURRENCY,
                    default=self._config_entry.data.get(CONF_CURRENCY, "eur"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["eur", "usd", "gbp", "chf"],
                        translation_key="currency",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
