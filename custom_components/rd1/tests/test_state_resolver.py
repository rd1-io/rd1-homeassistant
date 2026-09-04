"""Pure-logic tests for the declarative state resolver and command builder."""

from custom_components.rd1.state_resolver import (
    MISSING,
    apply_pointer_patches,
    attr_bool,
    build_command,
    command_status_patches,
    entity_available,
    expand_linked_patches,
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


def test_attr_bool_map_gt_zero_is_off_not_unknown():
    desc = {"state": {"is_on": {"ptr": "/climate/target_humidity", "map_gt": 0}}}
    assert attr_bool(desc, "is_on", STATUS) is True
    assert attr_bool(desc, "is_on", {"climate": {"target_humidity": 0}}) is False


def test_attr_bool_commanded_on():
    desc = {"state": {"is_on": {"ptr": "/ventilation/on"}}}
    assert attr_bool(desc, "is_on", {"ventilation": {"on": True}}) is True
    assert attr_bool(desc, "is_on", {"ventilation": {"on": False}}) is False
    assert attr_bool(desc, "is_on", {}) is None


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


FAN = {
    "state": {
        "is_on": {"ptr": "/ventilation/on"},
        "percentage": {"ptr": "/ventilation/power_level", "scale": 20},
    },
    "commands": {
        "turn_on": {"type": "set_power", "value": 3},
        "turn_off": {"type": "set_power", "value": 0},
        "set_percentage": {
            "type": "set_power",
            "value": {"from": "percentage", "scale": 0.05, "round": "nearest"},
        },
    },
}

NUMBER = {
    "state": {"value": {"ptr": "/ventilation/power_level", "scale": 20}},
    "commands": {
        "set_value": {
            "type": "set_power",
            "value": {"from": "value", "scale": 0.05, "round": "nearest"},
        },
    },
}


def test_command_patches_number_set_value():
    cmd = build_command(NUMBER["commands"]["set_value"], {"value": 80})
    patches = command_status_patches(NUMBER, "set_value", cmd, {"value": 80})
    assert patches["/ventilation/power_level"] == 4
    linked = expand_linked_patches({"entities": [FAN, NUMBER]}, patches)
    assert linked["/ventilation/on"] is True


def test_command_patches_fan_turn_off():
    cmd = build_command(FAN["commands"]["turn_off"], {})
    patches = command_status_patches(FAN, "turn_off", cmd, {})
    assert patches["/ventilation/power_level"] == 0
    assert patches["/ventilation/on"] is False


def test_stale_status_keeps_optimistic_power():
    status = {"ventilation": {"power_level": 0, "on": False}}
    patches = {"/ventilation/power_level": 4, "/ventilation/on": True}
    merged = apply_pointer_patches(status, patches)
    assert merged["ventilation"]["power_level"] == 4
    assert merged["ventilation"]["on"] is True
    assert status["ventilation"]["power_level"] == 0
