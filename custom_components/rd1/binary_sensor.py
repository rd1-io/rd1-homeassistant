"""Binary sensor platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity


class Rd1BinarySensor(Rd1Entity, BinarySensorEntity):
    """A catalog binary sensor: is_on ← state.is_on pointer."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_device_class = desc.get("device_class")

    @property
    def is_on(self) -> bool | None:
        return self._attr_bool("is_on")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Rd1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Rd1BinarySensor(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "binary_sensor"
    )
