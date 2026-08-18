"""The Vestel Smart Home integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VestelApi
from .const import (
    CONF_HOME_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import VestelCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vestel Smart Home from a config entry."""
    api = VestelApi(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data.get(CONF_PASSWORD),
        entry.data.get(CONF_REFRESH_TOKEN),
    )

    seconds = entry.options.get(
        CONF_SCAN_INTERVAL_SECONDS, int(DEFAULT_SCAN_INTERVAL.total_seconds())
    )
    coordinator = VestelCoordinator(
        hass, entry, api, entry.data[CONF_HOME_ID], timedelta(seconds=seconds)
    )
    await coordinator.async_config_entry_first_refresh()

    if api.refresh_token and api.refresh_token != entry.data.get(CONF_REFRESH_TOKEN):
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_REFRESH_TOKEN: api.refresh_token}
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
