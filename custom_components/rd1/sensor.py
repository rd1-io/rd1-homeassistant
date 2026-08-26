"""Sensor platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity


class Rd1Sensor(Rd1Entity, SensorEntity):
    """A catalog sensor: value ← state.value pointer."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_device_class = desc.get("device_class")
        self._attr_state_class = desc.get("state_class")
        self._attr_native_unit_of_measurement = desc.get("unit")

    @property
    def native_value(self) -> Any:
        return self._attr("value")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Rd1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Rd1Sensor(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "sensor"
    )
