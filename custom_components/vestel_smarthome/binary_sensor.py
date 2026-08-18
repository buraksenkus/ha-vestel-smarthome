"""Binary sensor platform for Vestel Smart Home."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VestelCoordinator
from .entity import VestelEntity
from .protocol import error_code


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator: VestelCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[VestelEntity] = []
    for device_id in coordinator.data:
        entities.append(VestelConnectivity(coordinator, device_id))
        entities.append(VestelProblem(coordinator, device_id))
    async_add_entities(entities)


class VestelConnectivity(VestelEntity, BinarySensorEntity):
    """Whether the appliance is reachable through the cloud."""

    _attr_translation_key = "connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VestelCoordinator, device_id: str) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_connectivity"

    @property
    def available(self) -> bool:
        """Stay available so the offline state itself can be reported."""
        return self._device_id in (self.coordinator.data or {})

    @property
    def is_on(self) -> bool:
        """Return whether the appliance is online."""
        return bool(self.device_state.device.get("connected", False))


class VestelProblem(VestelEntity, BinarySensorEntity):
    """Whether the appliance reports an error code."""

    _attr_translation_key = "problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VestelCoordinator, device_id: str) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_problem"

    @property
    def is_on(self) -> bool | None:
        """Return whether an error is active."""
        code = error_code(self.registers)
        return None if code is None else code != 0

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Expose the raw error code."""
        code = error_code(self.registers)
        return None if code is None else {"error_code": code}
