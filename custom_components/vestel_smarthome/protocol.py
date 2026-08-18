"""Encoding and decoding of the legacy register protocol.

Appliance state is exposed by the cloud as a handful of numeric registers
(``ACGENSI``, ``ACFANPO``, ``ACTEMOT`` ...). Each register packs several
settings into bit ranges. The layout is not hard coded here: it is read from
the ``/device/discovery`` response so other models keep working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PREFIX = "Climate.AirConditioner.Setting."

SETTING_MODE = f"{PREFIX}Mode"
SETTING_TEMPERATURE = f"{PREFIX}Temperature"
SETTING_FAN_SPEED = f"{PREFIX}Fan.Speed"
SETTING_TURBO = f"{PREFIX}Fan.Turbo"
SETTING_ECO = f"{PREFIX}Fan.Eco"
SETTING_IONIZER = f"{PREFIX}Fan.Ionizer"
SETTING_SLEEP = f"{PREFIX}Fan.SleepMode"
SETTING_VERTICAL_SWING = f"{PREFIX}Fan.VerticalSwing"
SETTING_HORIZONTAL_SWING = f"{PREFIX}Fan.HorizontalSwing"

TOGGLE_SETTINGS = (SETTING_TURBO, SETTING_ECO, SETTING_IONIZER, SETTING_SLEEP)

# Registers holding the temperature encode ``celsius - 16`` in four bits.
TEMPERATURE_OFFSET = 16

MODE_OFF = "PowerOff"
FAN_AUTO = "Auto"

REGISTER_ROOM_TEMPERATURE = "ACROOTE"
REGISTER_ERROR = "ACERROR"


@dataclass(frozen=True)
class Field:
    """A bit range inside one numeric register."""

    command: str
    position: int
    length: int
    value_type: str
    values: dict[str, int] = field(default_factory=dict)

    @property
    def mask(self) -> int:
        """Return the bit mask for this field."""
        return (1 << self.length) - 1

    def decode(self, registers: dict[str, str]) -> int | None:
        """Read this field out of a status payload."""
        try:
            raw = int(registers[self.command])
        except (KeyError, TypeError, ValueError):
            return None
        return (raw >> self.position) & self.mask

    def encode(self, registers: dict[str, str], value: int) -> str:
        """Return the command string that writes ``value`` into this field."""
        try:
            current = int(registers.get(self.command) or 0)
        except (TypeError, ValueError):
            current = 0
        updated = (current & ~(self.mask << self.position)) | (
            (value & self.mask) << self.position
        )
        return f"{self.command}{updated:05d}"

    def name_for(self, value: int | None) -> str | None:
        """Return the symbolic name of a raw value."""
        if value is None:
            return None
        for name, candidate in self.values.items():
            if candidate == value:
                return name
        return None


@dataclass
class ModeCapabilities:
    """What a single operating mode allows."""

    temp_min: int | None = None
    temp_max: int | None = None
    fan_speeds: list[str] = field(default_factory=list)
    extras: set[str] = field(default_factory=set)


def _short(key: str) -> str:
    return key.rsplit(".", 1)[-1]


class DeviceSchema:
    """Parsed ``/device/discovery`` payload."""

    def __init__(self, discovery: dict[str, Any]) -> None:
        """Parse the capability document."""
        self.raw = discovery
        self.device_model: str = discovery.get("deviceModel", "")
        self.variant: str = discovery.get("variant", "")
        self.fields: dict[str, Field] = {}
        self.modes: dict[str, int] = {}
        self.capabilities: dict[str, ModeCapabilities] = {}
        self._relations: list[dict[str, Any]] = discovery.get("settingRelations") or []

        for setting in discovery.get("settings") or []:
            key = setting.get("key")
            command = setting.get("commandName")
            if not key or not command:
                continue
            values = {
                _short(value["value"]): value["commandValue"]
                for value in setting.get("values") or []
                if "value" in value and "commandValue" in value
            }
            self.fields[key] = Field(
                command=command,
                position=int(setting.get("position", 0)),
                length=int(setting.get("length", 1)),
                value_type=setting.get("valueType", "BinaryInteger"),
                values=values,
            )
            if key == SETTING_MODE:
                self.modes = values
                self._parse_mode_capabilities(setting)

    def _parse_mode_capabilities(self, mode_setting: dict[str, Any]) -> None:
        for value in mode_setting.get("values") or []:
            name = _short(value["value"])
            caps = ModeCapabilities()
            for included in value.get("includedSettings") or []:
                key = included.get("key", "")
                if key == SETTING_TEMPERATURE:
                    limits = included.get("valueLimits") or {}
                    caps.temp_min = limits.get("min")
                    caps.temp_max = limits.get("max")
                elif key == SETTING_FAN_SPEED:
                    listed = included.get("values")
                    caps.fan_speeds = (
                        [_short(item["value"]) for item in listed]
                        if listed
                        else list(self.fields.get(key, Field("", 0, 0, "")).values)
                    )
                else:
                    caps.extras.add(key)
            self.capabilities[name] = caps

    # ------------------------------------------------------------------ helpers

    def field(self, key: str) -> Field | None:
        """Return the bit layout of a setting, if the model has it."""
        return self.fields.get(key)

    def supports(self, key: str) -> bool:
        """Return whether any mode exposes this setting."""
        if key not in self.fields:
            return False
        return any(key in caps.extras for caps in self.capabilities.values())

    def mode_name(self, registers: dict[str, str]) -> str | None:
        """Return the current operating mode."""
        mode_field = self.fields.get(SETTING_MODE)
        if mode_field is None:
            return None
        return mode_field.name_for(mode_field.decode(registers))

    def toggle_state(self, key: str, registers: dict[str, str]) -> bool | None:
        """Return the state of a boolean setting."""
        toggle = self.fields.get(key)
        if toggle is None:
            return None
        value = toggle.decode(registers)
        return None if value is None else bool(value)

    def temperature(self, registers: dict[str, str]) -> int | None:
        """Return the target temperature in degrees Celsius."""
        temp = self.fields.get(SETTING_TEMPERATURE)
        if temp is None:
            return None
        value = temp.decode(registers)
        return None if value is None else value + TEMPERATURE_OFFSET

    def encode_temperature(self, registers: dict[str, str], celsius: float) -> str:
        """Return the command that sets the target temperature."""
        temp = self.fields[SETTING_TEMPERATURE]
        return temp.encode(registers, int(round(celsius)) - TEMPERATURE_OFFSET)

    def fan_speed(self, registers: dict[str, str]) -> str | None:
        """Return the current fan speed name."""
        fan = self.fields.get(SETTING_FAN_SPEED)
        if fan is None:
            return None
        return fan.name_for(fan.decode(registers))

    def temperature_limits(self, registers: dict[str, str]) -> tuple[int, int]:
        """Return the min/max target temperature for the current state."""
        mode = self.mode_name(registers) or ""
        caps = self.capabilities.get(mode, ModeCapabilities())
        low, high = caps.temp_min, caps.temp_max
        for override in self._relation_limits(SETTING_TEMPERATURE, registers):
            low, high = override
        if low is None or high is None:
            return self.overall_temperature_limits()
        return (int(low), int(high))

    def overall_temperature_limits(self) -> tuple[int, int]:
        """Return the widest temperature range across every mode."""
        lows = [c.temp_min for c in self.capabilities.values() if c.temp_min is not None]
        highs = [c.temp_max for c in self.capabilities.values() if c.temp_max is not None]
        if not lows or not highs:
            return (TEMPERATURE_OFFSET, TEMPERATURE_OFFSET + 15)
        return (int(min(lows)), int(max(highs)))

    def _relation_limits(
        self, key: str, registers: dict[str, str]
    ) -> list[tuple[int, int]]:
        results: list[tuple[int, int]] = []
        for relation in self._relations:
            if relation.get("key") != key:
                continue
            for rule in relation.get("relations") or []:
                conditions = rule.get("andCondition") or []
                if not all(
                    self._condition_met(condition.get("key", ""), registers)
                    for condition in conditions
                ):
                    continue
                for statement in rule.get("statements") or []:
                    limits = statement.get("valueLimits")
                    if limits and "min" in limits and "max" in limits:
                        results.append((limits["min"], limits["max"]))
        return results

    def _condition_met(self, key: str, registers: dict[str, str]) -> bool:
        if key.startswith(f"{SETTING_MODE}."):
            return self.mode_name(registers) == _short(key)
        return bool(self.toggle_state(key, registers))

    def fan_speeds_for(self, mode: str | None) -> list[str]:
        """Return the fan speeds selectable in a mode."""
        caps = self.capabilities.get(mode or "", ModeCapabilities())
        return list(caps.fan_speeds)

    def fan_selectable(self, registers: dict[str, str]) -> bool:
        """Return whether the fan speed can currently be changed."""
        for relation in self._relations:
            if relation.get("key") != SETTING_FAN_SPEED:
                continue
            for rule in relation.get("relations") or []:
                conditions = rule.get("andCondition") or []
                if not all(
                    self._condition_met(condition.get("key", ""), registers)
                    for condition in conditions
                ):
                    continue
                for statement in rule.get("statements") or []:
                    if statement.get("isSelectable") is False:
                        return False
        return True

    def swing_positions(self) -> list[str]:
        """Return the vertical swing positions the model exposes."""
        swing = self.fields.get(SETTING_VERTICAL_SWING)
        return list(swing.values) if swing else []


def room_temperature(registers: dict[str, str]) -> float | None:
    """Return the measured room temperature."""
    try:
        return float(int(registers[REGISTER_ROOM_TEMPERATURE]))
    except (KeyError, TypeError, ValueError):
        return None


def error_code(registers: dict[str, str]) -> int | None:
    """Return the appliance error code, 0 meaning healthy."""
    try:
        return int(registers[REGISTER_ERROR])
    except (KeyError, TypeError, ValueError):
        return None


def encode_updates(
    schema: DeviceSchema,
    registers: dict[str, str],
    updates: list[tuple[str, int]],
) -> list[str]:
    """Return one command per register touched by ``updates``.

    Several settings share a register (mode and fan speed both live in
    ``ACGENSI``), so changes are merged before being turned into commands.
    """
    working = dict(registers)
    touched: list[str] = []
    for key, value in updates:
        target = schema.fields.get(key)
        if target is None:
            continue
        command = target.encode(working, value)
        working[target.command] = command[len(target.command) :]
        if target.command not in touched:
            touched.append(target.command)
    return [f"{name}{int(working[name]):05d}" for name in touched]
