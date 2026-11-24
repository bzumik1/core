"""The WAFE integration: heat recovery units with the ACE2 controller."""

from modbus_connection import ModbusTcpParams
from wafe_modbus import WafeUnit

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .const import DOMAIN, READINGS_SCAN_INTERVAL, SETTINGS_SCAN_INTERVAL, UNIT_ID
from .coordinator import WafeConfigEntry, WafeDataUpdateCoordinator, WafeRuntimeData

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: WafeConfigEntry) -> None:
    """Set up a WAFE unit from a config entry."""
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        UNIT_ID,
    )
    device = WafeUnit(unit)
    readings = WafeDataUpdateCoordinator(
        hass,
        entry,
        entry.title,
        device,
        device.async_update_readings,
        READINGS_SCAN_INTERVAL,
    )
    settings = WafeDataUpdateCoordinator(
        hass,
        entry,
        f"{entry.title} settings",
        device,
        device.async_update_settings,
        SETTINGS_SCAN_INTERVAL,
    )
    await readings.async_config_entry_first_refresh()
    if str(device.unit_id) != entry.unique_id:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="wrong_unit",
        )
    await settings.async_config_entry_first_refresh()
    entry.runtime_data = WafeRuntimeData(readings, settings)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: WafeConfigEntry) -> None:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
