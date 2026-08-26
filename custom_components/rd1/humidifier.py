"""Humidifier platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.humidifier import HumidifierEntity, HumidifierEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity


class Rd1Humidifier(Rd1Entity, HumidifierEntity):
    """A catalog humidifier. When off, target_humidity is reported as None."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_supported_features = HumidifierEntityFeature(0)
        self._attr_min_humidity = desc.get("min_humidity")
        self._attr_max_humidity = desc.get("max_humidity")
        step = desc.get("humidity_step")
        if step is not None:
            self._attr_target_humidity_step = step

    @property
    def is_on(self) -> bool | None:
        return self._attr_bool("is_on")

    @property
    def target_humidity(self) -> float | None:
        if self.is_on is not True:
            return None  # HA convention: no target while the humidifier is off
        value = self._attr("humidity")
        if value is None:
            return None
        return float(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send_command("turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send_command("turn_off")

    async def async_set_humidity(self, humidity: int) -> None:
        await self._send_command("set_humidity", {"humidity": humidity})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Rd1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Rd1Humidifier(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "humidifier"
    )
