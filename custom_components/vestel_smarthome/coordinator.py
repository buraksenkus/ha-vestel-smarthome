"""Polling coordinator for Vestel Smart Home appliances."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VestelApi, VestelAuthError, VestelError
from .const import DOMAIN, SUPPORTED_DEVICE_TYPES
from .protocol import DeviceSchema

_LOGGER = logging.getLogger(__name__)

# The appliance needs a moment before the cloud reports the new register value.
COMMAND_SETTLE_SECONDS = 6


@dataclass
class DeviceState:
    """Everything known about one appliance."""

    device: dict[str, Any]
    schema: DeviceSchema
    registers: dict[str, str] = field(default_factory=dict)

    @property
    def device_id(self) -> str:
        """Return the cloud identifier of the appliance."""
        return self.device["deviceId"]

    @property
    def available(self) -> bool:
        """Return whether the appliance is reachable."""
        return bool(self.device.get("connected", True)) and bool(self.registers)


class VestelCoordinator(DataUpdateCoordinator[dict[str, DeviceState]]):
    """Fetches the register state of every appliance in a home."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: VestelApi,
        home_id: str,
        scan_interval: timedelta,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
            config_entry=entry,
        )
        self.api = api
        self.home_id = home_id
        self._schemas: dict[str, DeviceSchema] = {}

    async def async_load_devices(self) -> list[dict[str, Any]]:
        """Return the supported appliances, loading their schema once."""
        try:
            devices = await self.api.async_get_devices(self.home_id)
        except VestelAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except VestelError as err:
            raise UpdateFailed(str(err)) from err

        supported = [
            device
            for device in devices
            if device.get("deviceType") in SUPPORTED_DEVICE_TYPES
            and device.get("deviceId")
        ]
        for device in supported:
            device_id = device["deviceId"]
            if device_id not in self._schemas:
                discovery = await self.api.async_get_discovery(device_id)
                self._schemas[device_id] = DeviceSchema(discovery)
        return supported

    async def _async_update_data(self) -> dict[str, DeviceState]:
        try:
            devices = await self.async_load_devices()
            states: dict[str, DeviceState] = {}
            for device in devices:
                device_id = device["deviceId"]
                registers: dict[str, str] = {}
                if device.get("connected", True):
                    registers = await self.api.async_get_status(device_id)
                states[device_id] = DeviceState(
                    device=device,
                    schema=self._schemas[device_id],
                    registers=registers,
                )
        except VestelAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except VestelError as err:
            raise UpdateFailed(str(err)) from err
        return states

    async def async_send_command(self, device_id: str, command: str) -> None:
        """Send a register command and optimistically reflect it."""
        state = (self.data or {}).get(device_id)
        if state is None:
            raise UpdateFailed(f"Unknown device {device_id}")

        try:
            await self.api.async_send_command(state.device, command)
        except VestelAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except VestelError as err:
            raise UpdateFailed(str(err)) from err

        register, value = command[:7], command[7:]
        if value.isdigit():
            state.registers[register] = value
            self.async_set_updated_data(self.data)

        async_call_later(self.hass, COMMAND_SETTLE_SECONDS, self._async_settle)

    async def _async_settle(self, _now: Any) -> None:
        """Re-read the appliance once it has applied the command."""
        await self.async_request_refresh()
