"""Climate platform for Vestel Smart Home air conditioners."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VestelCoordinator
from .entity import VestelEntity
from .protocol import (
    MODE_OFF,
    SETTING_FAN_SPEED,
    SETTING_MODE,
    SETTING_TEMPERATURE,
    SETTING_VERTICAL_SWING,
    DeviceSchema,
    encode_updates,
    room_temperature,
)

HVAC_MODES: dict[str, HVACMode] = {
    MODE_OFF: HVACMode.OFF,
    "Auto": HVACMode.AUTO,
    "Cooling": HVACMode.COOL,
    "Dehumidifying": HVACMode.DRY,
    "Ventilating": HVACMode.FAN_ONLY,
    "Heating": HVACMode.HEAT,
}

FAN_MODES: dict[str, str] = {
    "Auto": "auto",
    "Speed1": "1",
    "Speed2": "2",
    "Speed3": "3",
    "Speed4": "4",
    "Speed5": "5",
}

SWING_MODES: dict[str, str] = {
    "Off": "off",
    "Pos1": "1",
    "Pos2": "2",
    "Pos3": "3",
    "Pos4": "4",
    "Pos5": "5",
    "Pos6": "6",
}

DEFAULT_ON_MODE = "Cooling"


def _invert(mapping: dict[str, Any]) -> dict[Any, str]:
    return {value: key for key, value in mapping.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate entities."""
    coordinator: VestelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VestelClimate(coordinator, device_id) for device_id in coordinator.data
    )


class VestelClimate(VestelEntity, ClimateEntity):
    """An air conditioner exposed as a climate entity."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0

    def __init__(self, coordinator: VestelCoordinator, device_id: str) -> None:
        """Initialise the climate entity."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._last_on_mode = DEFAULT_ON_MODE
        schema = self.schema

        self._attr_hvac_modes = [
            HVAC_MODES[name] for name in schema.modes if name in HVAC_MODES
        ]

        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if schema.field(SETTING_TEMPERATURE) is not None:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        fan_names = self._all_fan_names(schema)
        if fan_names:
            self._attr_fan_modes = [FAN_MODES.get(name, name) for name in fan_names]
            features |= ClimateEntityFeature.FAN_MODE

        if schema.supports(SETTING_VERTICAL_SWING):
            self._attr_swing_modes = [
                SWING_MODES.get(name, name) for name in schema.swing_positions()
            ]
            features |= ClimateEntityFeature.SWING_MODE

        self._attr_supported_features = features

    @staticmethod
    def _all_fan_names(schema: DeviceSchema) -> list[str]:
        """Return every fan speed the appliance offers, in schema order."""
        field = schema.field(SETTING_FAN_SPEED)
        if field is None:
            return []
        offered = {
            name for mode in schema.modes for name in schema.fan_speeds_for(mode)
        }
        return [name for name in field.values if name in offered]

    # -------------------------------------------------------------- state

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current operating mode."""
        name = self.schema.mode_name(self.registers)
        if name and name != MODE_OFF:
            self._last_on_mode = name
        return HVAC_MODES.get(name or "")

    @property
    def current_temperature(self) -> float | None:
        """Return the measured room temperature."""
        return room_temperature(self.registers)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature the appliance is set to."""
        return self.schema.temperature(self.registers)

    @property
    def min_temp(self) -> float:
        """Return the lowest selectable temperature."""
        return float(self.schema.temperature_limits(self.registers)[0])

    @property
    def max_temp(self) -> float:
        """Return the highest selectable temperature."""
        return float(self.schema.temperature_limits(self.registers)[1])

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan speed."""
        name = self.schema.fan_speed(self.registers)
        return FAN_MODES.get(name or "", name)

    @property
    def swing_mode(self) -> str | None:
        """Return the current louvre position."""
        field = self.schema.field(SETTING_VERTICAL_SWING)
        if field is None:
            return None
        name = field.name_for(field.decode(self.registers))
        return SWING_MODES.get(name or "", name)

    # -------------------------------------------------------------- commands

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Switch the appliance to another operating mode."""
        name = _invert(HVAC_MODES).get(hvac_mode)
        if name is None or name not in self.schema.modes:
            raise ServiceValidationError(f"Unsupported mode {hvac_mode}")

        updates: list[tuple[str, int]] = [(SETTING_MODE, self.schema.modes[name])]
        updates += self._fan_fixup(name)
        await self.async_send(encode_updates(self.schema, self.registers, updates))

    def _fan_fixup(self, mode: str) -> list[tuple[str, int]]:
        """Return a fan change when the current speed is invalid in ``mode``."""
        allowed = self.schema.fan_speeds_for(mode)
        field = self.schema.field(SETTING_FAN_SPEED)
        if not allowed or field is None:
            return []
        current = self.schema.fan_speed(self.registers)
        if current in allowed:
            return []
        return [(SETTING_FAN_SPEED, field.values[allowed[0]])]

    async def async_turn_on(self) -> None:
        """Turn the appliance back on using the last active mode."""
        await self.async_set_hvac_mode(
            HVAC_MODES.get(self._last_on_mode, HVACMode.COOL)
        )

    async def async_turn_off(self) -> None:
        """Turn the appliance off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        low, high = self.schema.temperature_limits(self.registers)
        if not low <= temperature <= high:
            raise ServiceValidationError(
                f"Temperature must be between {low} and {high} in this mode"
            )
        await self.async_send(
            [self.schema.encode_temperature(self.registers, float(temperature))]
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan speed."""
        field = self.schema.field(SETTING_FAN_SPEED)
        name = _invert(FAN_MODES).get(fan_mode, fan_mode)
        if field is None or name not in field.values:
            raise ServiceValidationError(f"Unsupported fan mode {fan_mode}")
        if not self.schema.fan_selectable(self.registers):
            raise ServiceValidationError(
                "Fan speed cannot be changed while turbo is active"
            )
        mode = self.schema.mode_name(self.registers)
        allowed = self.schema.fan_speeds_for(mode)
        # A mode that lists no speeds (such as PowerOff) does not restrict them.
        if allowed and name not in allowed:
            raise ServiceValidationError(f"Fan mode {fan_mode} is not valid in {mode}")
        await self.async_send(
            encode_updates(
                self.schema, self.registers, [(SETTING_FAN_SPEED, field.values[name])]
            )
        )

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set the louvre position."""
        field = self.schema.field(SETTING_VERTICAL_SWING)
        name = _invert(SWING_MODES).get(swing_mode, swing_mode)
        if field is None or name not in field.values:
            raise ServiceValidationError(f"Unsupported swing mode {swing_mode}")
        await self.async_send(
            encode_updates(
                self.schema,
                self.registers,
                [(SETTING_VERTICAL_SWING, field.values[name])],
            )
        )
