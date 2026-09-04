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

_DISPLAY_PRECISION = {
    "temperature": 1,
    "humidity": 1,
    "carbon_dioxide": 0,
    "atmospheric_pressure": 0,
}


def sensor_display_precision(desc: dict[str, Any]) -> int | None:
    """UI/recorder decimals: catalog `precision`, else device_class / percent unit."""
    if desc.get("precision") is not None:
        return int(desc["precision"])
    device_class = desc.get("device_class")
    if device_class in _DISPLAY_PRECISION:
        return _DISPLAY_PRECISION[device_class]
    if desc.get("unit") == "%":
        return 1
    return None


class Rd1Sensor(Rd1Entity, SensorEntity):
    """A catalog sensor: value ← state.value pointer."""

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator, desc)
        self._attr_device_class = desc.get("device_class")
        self._attr_state_class = desc.get("state_class")
        self._attr_native_unit_of_measurement = desc.get("unit")
        precision = sensor_display_precision(desc)
        self._attr_suggested_display_precision = precision
        self._attr_native_precision = precision

    @property
    def native_value(self) -> Any:
        value = self._attr("value")
        precision = self._attr_native_precision
        if isinstance(value, float) and precision is not None:
            return round(value, precision)
        return value


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
