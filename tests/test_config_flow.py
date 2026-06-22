"""Config-flow tests for iDotMatrix.

Run with the HA test harness:
    pip install homeassistant pytest-homeassistant-custom-component
    pytest tests/test_config_flow.py
"""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.idotmatrix.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:85:89"

IDM_SERVICE_INFO = BluetoothServiceInfoBleak(
    name="IDM-858931",
    address=ADDRESS,
    rssi=-39,
    manufacturer_data={21076: b"\x00\x70\x03\x04\x0f\x00\x01\x04"},
    service_data={},
    service_uuids=["000000fa-0000-1000-8000-00805f9b34fb"],
    source="local",
    device=None,  # type: ignore[arg-type]
    advertisement=None,  # type: ignore[arg-type]
    connectable=True,
    time=0.0,
    tx_power=-127,
)


async def test_bluetooth_discovery(hass: HomeAssistant, mock_setup_entry) -> None:
    """A discovered panel can be confirmed and set up."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=IDM_SERVICE_INFO
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ADDRESS: ADDRESS}
    assert result["result"].unique_id == ADDRESS


async def test_user_manual_setup(hass: HomeAssistant, mock_setup_entry) -> None:
    """A panel discovered passively can be picked in the manual flow."""
    with patch(
        "custom_components.idotmatrix.config_flow.async_discovered_service_info",
        return_value=[IDM_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ADDRESS: ADDRESS}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ADDRESS: ADDRESS}


async def test_user_no_devices(hass: HomeAssistant) -> None:
    """The manual flow aborts when nothing is discovered."""
    with patch(
        "custom_components.idotmatrix.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_bluetooth_already_configured(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """A second discovery of the same address aborts as already configured."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={CONF_ADDRESS: ADDRESS})
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=IDM_SERVICE_INFO
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
