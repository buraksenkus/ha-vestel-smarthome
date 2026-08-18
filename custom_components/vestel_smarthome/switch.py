"""Switch platform for Vestel Smart Home extras."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VestelCoordinator
from .entity import VestelEntity
from .protocol import (
    SETTING_ECO,
    SETTING_IONIZER,
    SETTING_SLEEP,
    SETTING_TURBO,
    encode_updates,
)


@dataclass(frozen=True, kw_only=True)
class VestelSwitchDescription(SwitchEntityDescription):
    """Describes a boolean appliance setting."""

    setting: str


SWITCHES: tuple[VestelSwitchDescription, ...] = (
    VestelSwitchDescription(
        key="turbo",
        translation_key="turbo",
        setting=SETTING_TURBO,
    ),
    VestelSwitchDescription(
        key="eco",
        translation_key="eco",
        setting=SETTING_ECO,
    ),
    VestelSwitchDescription(
        key="ionizer",
        translation_key="ionizer",
        setting=SETTING_IONIZER,
    ),
    VestelSwitchDescription(
        key="sleep",
        translation_key="sleep",
        setting=SETTING_SLEEP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches supported by each appliance."""
    coordinator: VestelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VestelSwitch(coordinator, device_id, description)
        for device_id, state in coordinator.data.items()
        for description in SWITCHES
        if state.schema.supports(description.setting)
    )


class VestelSwitch(VestelEntity, SwitchEntity):
    """A boolean appliance setting such as turbo or eco."""

    entity_description: VestelSwitchDescription

    def __init__(
        self,
        coordinator: VestelCoordinator,
        device_id: str,
        description: VestelSwitchDescription,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return whether the setting is active."""
        return self.schema.toggle_state(self.entity_description.setting, self.registers)

    async def _async_set(self, value: int) -> None:
        await self.async_send(
            encode_updates(
                self.schema,
                self.registers,
                [(self.entity_description.setting, value)],
            )
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the setting."""
        await self._async_set(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the setting."""
        await self._async_set(0)
