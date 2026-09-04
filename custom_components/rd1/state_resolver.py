"""State resolution for the RD1 catalog.

Catalog descriptors contain *pointers*, not values. Each pointer is resolved
against the /api/status JSON document with the declarative transforms from the
plan: `ptr` (RFC 6901), `valid`, `map`, `map_gt`, `scale`.
"""

from __future__ import annotations

import copy
import math
from typing import Any

MISSING = object()
UNAVAILABLE = object()


def _pointer_walk(doc: Any, ptr: str) -> Any:
    """Resolve an RFC 6901 JSON pointer. Raise KeyError if it can't resolve."""
    if ptr == "":
        return doc
    if not ptr.startswith("/"):
        raise KeyError(ptr)
    cur: Any = doc
    for raw in ptr[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            cur = cur[token]
        elif isinstance(cur, list):
            try:
                cur = cur[int(token)]
            except (ValueError, IndexError) as exc:
                raise KeyError(ptr) from exc
        else:
            raise KeyError(ptr)
    return cur


def _map_key(value: Any) -> str:
    """Stringify a JSON value for `map` lookups, mirroring the C contract:
    booleans become "true"/"false", numbers their decimal form, strings as-is."""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return value
    return str(value)


def resolve(ptr_spec: dict[str, Any], status: dict[str, Any]) -> tuple[Any, bool]:
    """Resolve one state pointer.

    Returns (value, available). `value` is MISSING when the attribute should be
    omitted (e.g. map lookup without a match, or map_gt not satisfied).
    """
    if not isinstance(ptr_spec, dict) or "ptr" not in ptr_spec:
        return MISSING, False

    try:
        value = _pointer_walk(status, ptr_spec["ptr"])
    except (KeyError, TypeError, ValueError):
        return MISSING, False

    available = True
    valid_ptr = ptr_spec.get("valid")
    if valid_ptr is not None:
        try:
            valid = _pointer_walk(status, valid_ptr)
        except (KeyError, TypeError, ValueError):
            valid = None
        if valid is not True:
            available = False

    if "map" in ptr_spec:
        mapping = ptr_spec["map"]
        key = _map_key(value)
        if not isinstance(mapping, dict) or key not in mapping:
            return MISSING, available
        value = mapping[key]

    if "map_gt" in ptr_spec and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value <= ptr_spec["map_gt"]:
            return MISSING, available

    if "scale" in ptr_spec and isinstance(value, (int, float)) and not isinstance(value, bool):
        value = value * ptr_spec["scale"]

    return value, available


def attr(entity_desc: dict[str, Any], attribute: str, status: dict[str, Any]) -> tuple[Any, bool]:
    """Resolve one attribute of an entity descriptor against the status doc."""
    state = entity_desc.get("state") or {}
    ptr_spec = state.get(attribute)
    if ptr_spec is None:
        return MISSING, True
    return resolve(ptr_spec, status)


def attr_bool(entity_desc: dict[str, Any], attribute: str, status: dict[str, Any]) -> bool | None:
    """Resolve a boolean attribute.

    `map_gt` miss (power 0, humidity 0) is a real off, not unknown. A
    pointer that does not resolve stays unknown.
    """
    value, available = attr(entity_desc, attribute, status)
    if value is MISSING:
        return False if available else None
    if value is None:
        return None
    return bool(value)


def entity_available(entity_desc: dict[str, Any], status: dict[str, Any]) -> bool:
    """An entity is available when every declared validity flag is true."""
    state = entity_desc.get("state") or {}
    for ptr_spec in state.values():
        if not isinstance(ptr_spec, dict):
            continue
        valid_ptr = ptr_spec.get("valid")
        if valid_ptr is None:
            continue
        try:
            valid = _pointer_walk(status, valid_ptr)
        except (KeyError, TypeError, ValueError):
            return False
        if valid is not True:
            return False
    return True


def pointer_get(doc: Any, ptr: str) -> Any:
    """Resolve an RFC 6901 JSON pointer. Raise KeyError if it can't resolve."""
    return _pointer_walk(doc, ptr)


def pointer_set(doc: dict[str, Any], ptr: str, value: Any) -> None:
    """Write `value` at an RFC 6901 pointer, creating missing object keys."""
    if not ptr.startswith("/"):
        raise KeyError(ptr)
    tokens = [raw.replace("~1", "/").replace("~0", "~") for raw in ptr[1:].split("/")]
    cur: Any = doc
    for token in tokens[:-1]:
        if isinstance(cur, dict):
            nxt = cur.get(token)
            if not isinstance(nxt, (dict, list)):
                nxt = {}
                cur[token] = nxt
            cur = nxt
        elif isinstance(cur, list):
            cur = cur[int(token)]
        else:
            raise KeyError(ptr)
    last = tokens[-1]
    if isinstance(cur, dict):
        cur[last] = value
    elif isinstance(cur, list):
        cur[int(last)] = value
    else:
        raise KeyError(ptr)


def apply_pointer_patches(status: dict[str, Any], patches: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of status with JSON-pointer patches applied."""
    out = copy.deepcopy(status)
    for ptr, value in patches.items():
        pointer_set(out, ptr, value)
    return out


def _invert_ptr_value(spec: dict[str, Any], ha_value: Any) -> Any:
    """Undo map/scale so a HA service value can be written back into status."""
    value = ha_value
    if "map" in spec and isinstance(spec["map"], dict):
        reverse = {v: k for k, v in spec["map"].items()}
        if ha_value not in reverse:
            return MISSING
        key = reverse[ha_value]
        if key == "true":
            return True
        if key == "false":
            return False
        if isinstance(key, str) and key.lstrip("-").isdigit():
            return int(key)
        return key
    if "scale" in spec and isinstance(value, (int, float)) and not isinstance(value, bool):
        return value / spec["scale"]
    return value


_FIELD_TO_STATE = {
    "value": "value",
    "percentage": "percentage",
    "preset_mode": "preset_mode",
    "hvac_mode": "hvac_mode",
    "temperature": "target_temp",
    "humidity": "humidity",
    "brightness_pct": "brightness_pct",
}


def command_status_patches(
    desc: dict[str, Any],
    command_name: str,
    command: dict[str, Any],
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Predict status-document writes from a catalog command that just succeeded."""
    patches: dict[str, Any] = {}
    state = desc.get("state") or {}

    def write(spec: Any, ha_value: Any, *, raw: bool = False) -> None:
        if not isinstance(spec, dict) or "ptr" not in spec:
            return
        stored = ha_value if raw else _invert_ptr_value(spec, ha_value)
        if stored is MISSING:
            return
        patches[spec["ptr"]] = stored

    for field, attr_name in _FIELD_TO_STATE.items():
        if field in fields:
            write(state.get(attr_name), fields[field])

    raw_value = command.get("value")
    if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
        for attr_name in ("percentage", "value"):
            if attr_name in state:
                write(state[attr_name], raw_value, raw=True)
                break
        if "is_on" in state:
            write(state["is_on"], raw_value > 0, raw=True)

    if command_name == "turn_on":
        write(state.get("is_on"), True, raw=True)
    elif command_name == "turn_off":
        write(state.get("is_on"), False, raw=True)
        for attr_name in ("percentage", "value"):
            if attr_name in state:
                write(state[attr_name], 0, raw=True)

    return patches


def expand_linked_patches(catalog: dict[str, Any], patches: dict[str, Any]) -> dict[str, Any]:
    """When a shared setpoint ptr is patched, also flip sibling is_on pointers."""
    out = dict(patches)
    for entity in catalog.get("entities") or []:
        state = entity.get("state") or {}
        level = None
        for key in ("percentage", "value"):
            spec = state.get(key)
            if isinstance(spec, dict) and spec.get("ptr") in out:
                level = out[spec["ptr"]]
                break
        on_spec = state.get("is_on")
        if (
            level is not None
            and isinstance(on_spec, dict)
            and "ptr" in on_spec
            and isinstance(level, (int, float))
            and not isinstance(level, bool)
        ):
            out.setdefault(on_spec["ptr"], level > 0)
    return out


def build_command(cmd_template: dict[str, Any], service_fields: dict[str, Any]) -> dict[str, Any]:
    """Instantiate a catalog command object from a HA service call.

    `service_fields` maps the declarative `from` names (percentage, temperature,
    humidity, brightness_pct, hvac_mode, preset_mode, on, value) to values.
    """
    out: dict[str, Any] = {}
    for key, raw in cmd_template.items():
        if key == "type":
            if not isinstance(raw, str):
                raise ValueError("command type must be a string")
            out[key] = raw
            continue
        if not isinstance(raw, dict) or "from" not in raw:
            out[key] = raw  # static literal
            continue
        out[key] = _transform_param(raw, service_fields.get(raw["from"]))
    return out


def _transform_param(param: dict[str, Any], value: Any) -> Any:
    """Apply from/map/scale/round to one service-call value."""
    if "map" in param:
        mapping = param["map"]
        if not isinstance(mapping, dict):
            raise ValueError("map must be an object")
        key = _map_key(value)
        if key in mapping:
            value = mapping[key]
        elif value is None:
            raise ValueError(f"no map entry for empty value in {param}")
        else:
            raise ValueError(f"no map entry for {value!r} in {param}")

    if "scale" in param and isinstance(value, (int, float)) and not isinstance(value, bool):
        value = value * param["scale"]

    if "round" in param and isinstance(value, float):
        mode = param["round"]
        if mode == "nearest":
            value = round(value)
        elif mode == "up":
            value = math.ceil(value)
        elif mode == "down":
            value = math.floor(value)
        else:
            raise ValueError(f"unknown round mode {mode!r}")

    return value
