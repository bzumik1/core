"""Diagnostics support for WAFE heat recovery units."""

from typing import Any

from modbus_connection import ModbusError

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import WafeConfigEntry

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: WafeConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, with the raw register map."""
    runtime_data = entry.runtime_data
    device = runtime_data.readings.device
    raw: dict[str, Any] | None = None
    read_error: str | None = None
    try:
        raw = await device.async_read_raw()
    except ModbusError as err:
        read_error = type(err).__name__

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "model": device.model.name if device.model is not None else None,
        "readings": {
            "updated": sorted(runtime_data.readings.data.updated),
            "failed": {
                name: str(err)
                for name, err in runtime_data.readings.data.failed.items()
            },
        },
        "settings": {
            "updated": sorted(runtime_data.settings.data.updated),
            "failed": {
                name: str(err)
                for name, err in runtime_data.settings.data.failed.items()
            },
        },
        "read_error": read_error,
        "registers": raw,
    }
