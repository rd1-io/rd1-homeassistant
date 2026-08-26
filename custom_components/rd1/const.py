"""Constants for the RD1 local REST integration."""

from datetime import timedelta

DOMAIN = "rd1"

CONF_HOST = "host"
CONF_SERIAL = "serial"

CATALOG_PATH = "/api/ha"
STATUS_PATH = "/api/status"
CMD_PATH = "/api/cmd"

PLATFORMS = [
    "sensor",
    "binary_sensor",
    "switch",
    "button",
    "number",
    "light",
    "fan",
    "climate",
    "humidifier",
]

POLL_INTERVAL = timedelta(seconds=5)
REQUEST_TIMEOUT = 8

# Serial pattern from prime/schemas/about.json
SERIAL_RE = r"^RD1S-[0-9A-F]{6}$"
