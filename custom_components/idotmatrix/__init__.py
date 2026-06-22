"""The iDotMatrix integration."""

from __future__ import annotations

from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import IDotMatrixConfigEntry, IDotMatrixCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: IDotMatrixConfigEntry) -> bool:
    """Set up iDotMatrix from a config entry."""
    coordinator = IDotMatrixCoordinator(hass, entry, entry.data[CONF_ADDRESS])
    await coordinator.async_start()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IDotMatrixConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    # Remove the (global) service only when the last entry goes away.
    if not hass.config_entries.async_loaded_entries(DOMAIN):
        from .const import SERVICE_SEND_COMMAND

        hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
    return unloaded
