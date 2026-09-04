"""Fan platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity


def fan_supported_features(desc: dict[str, Any]) -> FanEntityFeature:
    """Declare HA fan features from the catalog (HA 2024.8+ requires on/off flags)."""
    commands = desc.get("commands") or {}
    features = FanEntityFeature(0)
    if "turn_on" in commands:
        features |= FanEntityFeature.TURN_ON
    if "turn_off" in commands:
        features |= FanEntityFeature.TURN_OFF
    if desc.get("percentage_step") is not None:
        features |= FanEntityFeature.SET_SPEED
    if desc.get("preset_modes") and "set_preset_mode" in commands:
        features |= FanEntityFeature.PRESET_MODE
    return features


class Rd1Fan(Rd1Entity, FanEntity):
    """A catalog fan: is_on/percentage/preset_mode ← state pointers."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_supported_features = fan_supported_features(desc)
        if desc.get("percentage_step") is not None:
            self._attr_percentage_step = float(desc["percentage_step"])
        self._attr_preset_modes = list(desc.get("preset_modes") or [])

    @property
    def is_on(self) -> bool | None:
        return self._attr_bool("is_on")

    @property
    def percentage(self) -> int | None:
        value = self._attr("percentage")
        return None if value is None else int(value)

    @property
    def preset_mode(self) -> str | None:
        value = self._attr("preset_mode")
        return None if value is None else str(value)

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        if preset_mode is not None and (self.desc.get("commands") or {}).get("set_preset_mode"):
            await self._send_command("set_preset_mode", {"preset_mode": preset_mode})
            return
        if percentage is not None and (self.desc.get("commands") or {}).get("set_percentage"):
            await self._send_command("set_percentage", {"percentage": percentage})
            return
        await self._send_command("turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send_command("turn_off")

    async def async_set_percentage(self, percentage: int) -> None:
        await self._send_command("set_percentage", {"percentage": percentage})

    async def async_set_preset_mode(self, preset_mode: str | None) -> None:
        # preset_mode None (clear preset) maps via the catalog's "" map entry.
        await self._send_command("set_preset_mode", {"preset_mode": preset_mode})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Rd1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Rd1Fan(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "fan"
    )
