"""Sensor platform for Vestel Smart Home."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VestelCoordinator
from .entity import VestelEntity
from .protocol import room_temperature


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator: VestelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VestelRoomTemperature(coordinator, device_id) for device_id in coordinator.data
    )


class VestelRoomTemperature(VestelEntity, SensorEntity):
    """Room temperature measured by the appliance."""

    _attr_translation_key = "room_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: VestelCoordinator, device_id: str) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_room_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the measured temperature."""
        return room_temperature(self.registers)
