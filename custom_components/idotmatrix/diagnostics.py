"""Diagnostics support for iDotMatrix."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .coordinator import IDotMatrixConfigEntry

TO_REDACT = {CONF_ADDRESS}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IDotMatrixConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    state = coordinator.state
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "connected": coordinator.connected,
        "assumed_state": {
            "power": state.power,
            "brightness": state.brightness,
            "rgb": list(state.rgb),
            "color_active": state.color_active,
            "flip": state.flip,
            "clock_style": state.clock_style,
        },
    }
