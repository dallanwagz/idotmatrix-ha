"""Config flow for the iDotMatrix integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, NAME_PREFIX


def _title(address: str) -> str:
    """Human-friendly entry title from a BLE address."""
    return f"iDotMatrix {address.replace(':', '')[-6:]}"


class IDotMatrixConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle discovery and manual setup of an iDotMatrix panel."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise discovery bookkeeping."""
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a panel found by HA's Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": _title(discovery_info.address)}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a discovered panel."""
        assert self._discovery is not None
        if user_input is not None:
            return self.async_create_entry(
                title=_title(self._discovery.address),
                data={CONF_ADDRESS: self._discovery.address},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": _title(self._discovery.address)},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup by picking from discovered panels."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=_title(address), data={CONF_ADDRESS: address})

        current = self._async_current_ids()
        for info in async_discovered_service_info(self.hass):
            if (
                info.address not in current
                and info.address not in self._discovered
                and info.name
                and info.name.startswith(NAME_PREFIX)
            ):
                self._discovered[info.address] = f"{info.name} ({info.address})"

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered)}
            ),
        )
