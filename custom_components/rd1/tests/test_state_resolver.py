"""Pure-logic tests for the declarative state resolver and command builder."""

from custom_components.rd1.state_resolver import (
    MISSING,
    build_command,
    entity_available,
    resolve,
)

STATUS = {
    "ventilation": {
        "power_level": 3,
        "supply_running": True,
        "auto": True,
        "balance_pct": 100,
    },
    "climate": {
        "mode": 1,
        "current_c": 22.5,
        "target_c": 23.0,
        "heating": True,
        "cooling": False,
        "action": "heating",
        "sensor_valid": True,
        "target_humidity": 45,
    },
    "sensors": {"co2": {"co2_ppm": 800, "valid": True}},
    "lights": [{"on": True, "level_pct": 80}],
}


def test_plain_pointer():
    assert resolve({"ptr": "/ventilation/power_level"}, STATUS) == (3, True)


def test_climate_action_string():
    assert resolve({"ptr": "/climate/action"}, STATUS) == ("heating", True)


def test_array_index_pointer():
    assert resolve({"ptr": "/lights/0/on"}, STATUS) == (True, True)


def test_scale():
    assert resolve({"ptr": "/ventilation/power_level", "scale": 20}, STATUS) == (60, True)


def test_map_bool_key():
    assert resolve({"ptr": "/ventilation/auto", "map": {"true": "auto"}}, STATUS) == ("auto", True)


def test_map_gt_satisfied_and_not():
    assert resolve({"ptr": "/climate/target_humidity", "map_gt": 0}, STATUS) == (45, True)
    assert resolve({"ptr": "/ventilation/power_level", "map_gt": 3}, STATUS) == (MISSING, True)


def test_valid_false_makes_unavailable():
    status = {"t": 5, "t_valid": False}
    value, available = resolve({"ptr": "/t", "valid": "/t_valid"}, status)
    assert value == 5
    assert available is False


def test_missing_pointer():
    assert resolve({"ptr": "/nope"}, STATUS) == (MISSING, False)


def test_entity_available():
    desc = {"state": {"value": {"ptr": "/sensors/co2/co2_ppm", "valid": "/sensors/co2/valid"}}}
    assert entity_available(desc, STATUS) is True
    assert entity_available(desc, {"sensors": {"co2": {"co2_ppm": 0, "valid": False}}}) is False


def test_build_command_literal_and_from():
    assert build_command({"type": "set_power", "value": 3}, {}) == {"type": "set_power", "value": 3}
    assert build_command(
        {"type": "set_power", "value": {"from": "percentage", "scale": 0.05, "round": "nearest"}},
        {"percentage": 60},
    ) == {"type": "set_power", "value": 3}


def test_build_command_mode_map():
    cmd = build_command(
        {"type": "set_climate", "mode": {"from": "hvac_mode", "map": {"off": 0, "heat": 1}}},
        {"hvac_mode": "heat"},
    )
    assert cmd == {"type": "set_climate", "mode": 1}


def test_build_command_preset_none_uses_empty_key():
    cmd = build_command(
        {"type": "set_power", "auto": {"from": "preset_mode", "map": {"auto": True, "": False}}},
        {"preset_mode": None},
    )
    assert cmd == {"type": "set_power", "auto": False}
