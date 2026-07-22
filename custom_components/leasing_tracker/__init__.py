"""Leasing Tracker Integration für Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType

from .coordinator import LeasingTrackerCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "leasing_tracker"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Leasing Tracker component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Leasing Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = LeasingTrackerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # A single listener on the source odometer entity refreshes every sensor of
    # this entry at once, instead of each sensor subscribing separately.
    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            [coordinator.source_entity_id],
            coordinator._handle_source_change,
        )
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
