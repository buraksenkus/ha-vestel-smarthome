"""Shared entity base for Vestel Smart Home."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DeviceState, VestelCoordinator
from .protocol import DeviceSchema


def _device_options(device: dict[str, Any]) -> dict[str, str]:
    """Return the appliance ``options`` blob as a dict."""
    try:
        parsed = json.loads(device.get("options") or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def build_device_info(device: dict[str, Any]) -> DeviceInfo:
    """Return the Home Assistant device registry entry for an appliance."""
    options = _device_options(device)
    model = device.get("deviceModel") or options.get("WGMODEL") or "Air conditioner"
    if options.get("MODELCD"):
        model = f"{model} {options['MODELCD']}"

    info = DeviceInfo(
        identifiers={(DOMAIN, device["deviceId"])},
        manufacturer=str(device.get("oemBrand", "Vestel")).capitalize(),
        model=model,
        name=device.get("deviceName"),
        serial_number=device.get("serialNumber"),
        sw_version=device.get("wifiVersion"),
        hw_version=options.get("MAINBHW"),
        suggested_area=device.get("roomName"),
    )
    if device.get("mac"):
        info["connections"] = {(CONNECTION_NETWORK_MAC, format_mac(device["mac"]))}
    return info


class VestelEntity(CoordinatorEntity[VestelCoordinator]):
    """Base entity bound to one appliance."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VestelCoordinator, device_id: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_info = build_device_info(self.device_state.device)

    @property
    def device_state(self) -> DeviceState:
        """Return the coordinator record for this appliance."""
        return self.coordinator.data[self._device_id]

    @property
    def registers(self) -> dict[str, str]:
        """Return the raw register values."""
        return self.device_state.registers

    @property
    def schema(self) -> DeviceSchema:
        """Return the capability schema."""
        return self.device_state.schema

    @property
    def available(self) -> bool:
        """Return whether the appliance is online."""
        return (
            super().available
            and self._device_id in (self.coordinator.data or {})
            and self.device_state.available
        )

    async def async_send(self, commands: list[str]) -> None:
        """Send one or more register commands."""
        for command in commands:
            await self.coordinator.async_send_command(self._device_id, command)
