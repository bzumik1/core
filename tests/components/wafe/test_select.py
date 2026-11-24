"""Tests for the WAFE select platform."""

from unittest.mock import patch

from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit, WriteEvent
import pytest
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

MODE_ENTITY = "select.wafe_w201_operating_mode"


@pytest.mark.usefixtures("mock_get_unit")
async def test_all_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the select matches its snapshot."""
    with patch("homeassistant.components.wafe.PLATFORMS", [Platform.SELECT]):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("option", "coil"),
    [
        pytest.param("intelligent", 0, id="intelligent"),
        pytest.param("scheduler", 1, id="scheduler"),
        pytest.param("manual", 2, id="manual"),
        pytest.param("ultra_saving", 3, id="ultra_saving"),
    ],
)
async def test_select_option(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
    option: str,
    coil: int,
) -> None:
    """Test selecting a mode sets its coil."""
    writes: list[WriteEvent] = []
    mock_unit.on_write(writes.append)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: MODE_ENTITY, ATTR_OPTION: option},
        blocking=True,
    )

    assert [(w.register_type, w.address, w.values) for w in writes] == [
        ("coil", coil, [True])
    ]


async def test_select_option_write_failed(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
) -> None:
    """Test a failed write raises a translated error."""
    mock_unit.fail_write(2, ModbusTimeoutError(), register_type="coil")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: MODE_ENTITY, ATTR_OPTION: "manual"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "write_failed"


async def test_no_single_mode_is_unknown(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_get_unit: object,
    mock_unit: MockModbusUnit,
) -> None:
    """Test the mode is unknown while no single mode coil is set."""
    mock_unit.coil[0] = False
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(MODE_ENTITY).state == STATE_UNKNOWN
