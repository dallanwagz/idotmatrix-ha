"""Services for the iDotMatrix integration."""

from __future__ import annotations

from collections.abc import Callable

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from . import protocol
from .const import (
    ATTR_COMMAND,
    ATTR_PARAMS,
    ATTR_PATH,
    DOMAIN,
    PANEL_HEIGHT,
    PANEL_WIDTH,
    SERVICE_SEND_COMMAND,
    SERVICE_SET_IMAGE,
)
from .coordinator import IDotMatrixConfigEntry

# Whitelist of protocol builders exposed through the generic service. Each maps a
# friendly command name to the pure builder in ``protocol``.
COMMAND_BUILDERS: dict[str, Callable[..., bytes]] = {
    "set_time": protocol.set_time,
    "set_brightness": protocol.set_brightness,
    "set_fullscreen_color": protocol.set_fullscreen_color,
    "set_clock": protocol.set_clock,
    "set_countdown": protocol.set_countdown,
    "set_chronograph": protocol.set_chronograph,
    "set_scoreboard": protocol.set_scoreboard,
    "set_flip": protocol.set_flip,
    "set_text_speed": protocol.set_text_speed,
    "set_screen": protocol.set_screen,
    "set_time_indicator": protocol.set_time_indicator,
    "set_eco": protocol.set_eco,
    "set_screen_light_time": protocol.set_screen_light_time,
    "enter_diy": protocol.enter_diy,
    "draw_pixel": protocol.draw_pixel,
    "reset_device": protocol.reset_device,
}

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_COMMAND): vol.In(sorted(COMMAND_BUILDERS)),
        vol.Optional(ATTR_PARAMS, default=list): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
    }
)


IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PATH): cv.string,
        vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
    }
)


def _load_rgb(path: str) -> bytes:
    """Load an image file and return panel-sized row-major RGB bytes (blocking)."""
    from PIL import Image  # bundled with Home Assistant core

    with Image.open(path) as img:
        img = img.convert("RGB").resize((PANEL_WIDTH, PANEL_HEIGHT))
        return img.tobytes()


def _coordinators_for_call(
    hass: HomeAssistant, call: ServiceCall
) -> list[IDotMatrixConfigEntry]:
    """Resolve the targeted device ids to loaded iDotMatrix config entries."""
    device_reg = dr.async_get(hass)
    entries: list[IDotMatrixConfigEntry] = []
    for device_id in call.data.get("device_id", []):
        device = device_reg.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown device id: {device_id}")
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if (
                entry is not None
                and entry.domain == DOMAIN
                and entry.state is ConfigEntryState.LOADED
            ):
                entries.append(entry)  # type: ignore[arg-type]
    if not entries:
        raise ServiceValidationError("No iDotMatrix device targeted")
    return entries


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async def _async_send_command(call: ServiceCall) -> None:
        command: str = call.data[ATTR_COMMAND]
        params: list[int] = call.data[ATTR_PARAMS]
        builder = COMMAND_BUILDERS[command]
        try:
            frame = builder(*params)
        except TypeError as err:
            raise ServiceValidationError(
                f"Wrong params for '{command}': {err}"
            ) from err
        for entry in _coordinators_for_call(hass, call):
            try:
                await entry.runtime_data.async_send(frame)
            except HomeAssistantError as err:
                raise HomeAssistantError(
                    f"Failed sending '{command}' to {entry.title}: {err}"
                ) from err

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_COMMAND, _async_send_command, schema=SERVICE_SCHEMA
    )

    async def _async_set_image(call: ServiceCall) -> None:
        path: str = call.data[ATTR_PATH]
        if not hass.config.is_allowed_path(path):
            raise ServiceValidationError(f"Path not allowed: {path}")
        try:
            rgb = await hass.async_add_executor_job(_load_rgb, path)
        except (OSError, ValueError) as err:
            raise ServiceValidationError(f"Could not load image '{path}': {err}") from err
        for entry in _coordinators_for_call(hass, call):
            try:
                await entry.runtime_data.async_send_image(rgb)
            except HomeAssistantError as err:
                raise HomeAssistantError(
                    f"Failed uploading image to {entry.title}: {err}"
                ) from err

    hass.services.async_register(
        DOMAIN, SERVICE_SET_IMAGE, _async_set_image, schema=IMAGE_SCHEMA
    )
