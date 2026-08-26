"""Light platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity


class Rd1Light(Rd1Entity, LightEntity):
    """A catalog light: is_on / brightness_pct ← state pointers."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_supported_color_modes = set()
        if desc.get("supports_brightness") is True:
            self._attr_supported_color_modes = {"brightness"}

    @property
    def is_on(self) -> bool | None:
        return self._attr_bool("is_on")

    @property
    def brightness(self) -> int | None:
        pct = self._attr("brightness_pct")
        if pct is None:
            return None
        return round(float(pct) * 255 / 100)

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get("brightness")
        if brightness is not None and (self.desc.get("commands") or {}).get("set_brightness"):
            pct = round(float(brightness) * 100 / 255)
            await self._send_command("set_brightness", {"brightness_pct": pct})
            return
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
        Rd1Light(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "light"
    )
