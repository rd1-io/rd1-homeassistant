"""Catalog → HA feature / precision mapping."""

import pytest

pytest.importorskip("homeassistant")

from custom_components.rd1.climate import climate_supported_features
from custom_components.rd1.config_flow import entry_title
from custom_components.rd1.fan import fan_supported_features
from custom_components.rd1.sensor import sensor_display_precision
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.fan import FanEntityFeature

VENT_FAN = {
    "percentage_step": 20,
    "preset_modes": ["auto"],
    "commands": {
        "turn_on": {"type": "set_power", "value": 3},
        "turn_off": {"type": "set_power", "value": 0},
        "set_percentage": {"type": "set_power"},
        "set_preset_mode": {"type": "set_power"},
    },
}

VENT_CLIMATE = {
    "hvac_modes": ["off", "heat", "cool", "auto"],
    "state": {"target_temp": {"ptr": "/climate/target_c"}},
    "commands": {"set_temperature": {"type": "set_climate"}},
}


def test_fan_declares_on_off_speed_and_preset():
    features = fan_supported_features(VENT_FAN)
    assert features & FanEntityFeature.TURN_ON
    assert features & FanEntityFeature.TURN_OFF
    assert features & FanEntityFeature.SET_SPEED
    assert features & FanEntityFeature.PRESET_MODE


def test_fan_without_commands_has_no_on_off():
    features = fan_supported_features({"percentage_step": 10})
    assert features == FanEntityFeature.SET_SPEED


def test_climate_declares_temperature_and_on_off():
    features = climate_supported_features(VENT_CLIMATE)
    assert features & ClimateEntityFeature.TARGET_TEMPERATURE
    assert features & ClimateEntityFeature.TURN_ON
    assert features & ClimateEntityFeature.TURN_OFF


def test_entry_title_includes_host():
    assert entry_title("Ventilation1 Controller", "192.168.1.73") == (
        "Ventilation1 Controller · 192.168.1.73"
    )
    assert entry_title("Ventilation1 Controller", "rd1-35fd94.local.") == (
        "Ventilation1 Controller · rd1-35fd94.local"
    )


def test_sensor_precision_defaults():
    assert sensor_display_precision({"device_class": "humidity"}) == 1
    assert sensor_display_precision({"device_class": "temperature"}) == 1
    assert sensor_display_precision({"device_class": "carbon_dioxide"}) == 0
    assert sensor_display_precision({"unit": "%"}) == 1
    assert sensor_display_precision({"precision": 2, "device_class": "humidity"}) == 2
    assert sensor_display_precision({"device_class": "power"}) is None
