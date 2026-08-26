"""Number platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity


class Rd1Number(Rd1Entity, NumberEntity):
    """A catalog number: value ← state.value, set_value command."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_native_min_value = desc.get("min")
        self._attr_native_max_value = desc.get("max")
        self._attr_native_step = desc.get("step")
        self._attr_native_unit_of_measurement = desc.get("unit")

    @property
    def native_value(self) -> float | None:
        value = self._attr("value")
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self._send_command("set_value", {"value": value})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Rd1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Rd1Number(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "number"
    )
