"""Tests for the WAFE binary sensor platform."""

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import (
    MockConfigEntry,
    async_fire_time_changed,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.wafe.const import SCAN_INTERVAL
from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

BYPASS_ENTITY = "binary_sensor.wafe_w201_bypass"
HOLIDAY_VENTILATION_ENTITY = "binary_sensor.wafe_w201_holiday_ventilation"


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "mock_get_unit")
async def test_all_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all binary sensors match their snapshot."""
    with patch("homeassistant.components.wafe.PLATFORMS", [Platform.BINARY_SENSOR]):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("sub_mode", "bypass", "holiday_ventilation"),
    [
        pytest.param(0b01, STATE_ON, STATE_OFF, id="bypass"),
        pytest.param(0b10, STATE_OFF, STATE_ON, id="holiday_ventilation"),
        pytest.param(0b1111, STATE_ON, STATE_ON, id="all"),
    ],
)
async def test_sub_mode_bits(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
    sub_mode: int,
    bypass: str,
    holiday_ventilation: str,
) -> None:
    """Test each binary sensor reads its own sub-mode bit."""
    mock_unit.input[1003] = sub_mode
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(BYPASS_ENTITY).state == bypass
    assert hass.states.get(HOLIDAY_VENTILATION_ENTITY).state == holiday_ventilation
