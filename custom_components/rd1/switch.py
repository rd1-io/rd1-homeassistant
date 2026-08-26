"""Switch platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity


class Rd1Switch(Rd1Entity, SwitchEntity):
    """A catalog switch: is_on ← state.is_on, turn_on/turn_off commands."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_device_class = desc.get("device_class")

    @property
    def is_on(self) -> bool | None:
        return self._attr_bool("is_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send_command("turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send_command("turn_off")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Rd1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Rd1Switch(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "switch"
    )
