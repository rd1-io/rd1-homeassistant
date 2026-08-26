"""Climate platform for the RD1 catalog."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Rd1Coordinator
from .entity import Rd1Entity

_HVAC_ACTIONS = {
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
    "drying": HVACAction.DRYING,
    "fan": HVACAction.FAN,
    "idle": HVACAction.IDLE,
    "off": HVACAction.OFF,
}


class Rd1Climate(Rd1Entity, ClimateEntity):
    """A catalog climate entity."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_hvac_modes = [HVACMode(m) for m in desc.get("hvac_modes") or []]
        self._attr_min_temp = desc.get("min_temp")
        self._attr_max_temp = desc.get("max_temp")
        step = desc.get("target_temp_step")
        self._attr_target_temperature_step = step
        self._attr_precision = step

    @property
    def hvac_mode(self) -> HVACMode | None:
        value = self._attr("hvac_mode")
        if value is None:
            return None
        try:
            return HVACMode(str(value))
        except ValueError:
            return None

    @property
    def current_temperature(self) -> float | None:
        value = self._attr("current_temp")
        return None if value is None else float(value)

    @property
    def target_temperature(self) -> float | None:
        value = self._attr("target_temp")
        return None if value is None else float(value)

    @property
    def hvac_action(self) -> HVACAction | None:
        value = self._attr("hvac_action")
        if value is None:
            return None
        return _HVAC_ACTIONS.get(str(value))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._send_command("set_hvac_mode", {"hvac_mode": hvac_mode.value})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get("temperature")
        if temperature is not None:
            await self._send_command("set_temperature", {"temperature": temperature})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Rd1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Rd1Climate(coordinator, desc)
        for desc in coordinator.entities
        if desc["platform"] == "climate"
    )
