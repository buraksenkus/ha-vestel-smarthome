"""Diagnostics support for Vestel Smart Home."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import CONF_REFRESH_TOKEN, DOMAIN
from .coordinator import VestelCoordinator

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    "mac",
    "serialNumber",
    "orderNumber",
    "registeredBy",
    "pubTopic",
    "subTopic",
    "homeConnectivityTopic",
    "homeStatusTopic",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: VestelCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "devices": [
            {
                "device": async_redact_data(state.device, TO_REDACT),
                "registers": state.registers,
                "discovery": state.schema.raw,
            }
            for state in (coordinator.data or {}).values()
        ],
    }
