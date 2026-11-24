"""Constants for the WAFE integration."""

from datetime import timedelta

DOMAIN = "wafe"
MANUFACTURER = "WAFE"

DEFAULT_PORT = 502
# The controller ignores the unit ID, so it is not asked for.
UNIT_ID = 1

READINGS_SCAN_INTERVAL = timedelta(seconds=5)
SETTINGS_SCAN_INTERVAL = timedelta(seconds=5)
