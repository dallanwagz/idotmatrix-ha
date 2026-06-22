"""Light platform for iDotMatrix — the panel as an RGB light."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .coordinator import IDotMatrixConfigEntry, IDotMatrixCoordinator
from .entity import IDotMatrixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IDotMatrixConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the iDotMatrix light."""
    async_add_entities([IDotMatrixLight(entry.runtime_data)])


def _pct_to_255(percent: int) -> int:
    return round(percent * 255 / 100)


def _255_to_pct(value: int) -> int:
    return round(value * 100 / 255)


class IDotMatrixLight(IDotMatrixEntity, LightEntity):
    """The panel as an optimistic RGB light.

    on/off -> screen power; brightness -> set_brightness; rgb -> fullscreen colour.
    There is no readable state, so all values are assumed (optimistic).
    """

    _attr_name = None  # primary entity uses the device name
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_assumed_state = True

    def __init__(self, coordinator: IDotMatrixCoordinator) -> None:
        """Initialise the light entity."""
        super().__init__(coordinator, "light")

    @property
    def is_on(self) -> bool:
        """Return assumed power state."""
        return self.coordinator.state.power

    @property
    def brightness(self) -> int:
        """Return assumed brightness (0-255)."""
        return _pct_to_255(self.coordinator.state.brightness)

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return assumed RGB colour."""
        return self.coordinator.state.rgb

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the panel on, optionally setting brightness/colour."""
        state = self.coordinator.state
        await self.coordinator.async_send(protocol.set_screen(True))
        state.power = True

        if ATTR_BRIGHTNESS in kwargs:
            pct = _255_to_pct(kwargs[ATTR_BRIGHTNESS])
            await self.coordinator.async_send(protocol.set_brightness(pct))
            state.brightness = pct

        if ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
            await self.coordinator.async_send(protocol.set_fullscreen_color(*rgb))
            state.rgb = rgb
            state.color_active = True

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the panel off."""
        await self.coordinator.async_send(protocol.set_screen(False))
        self.coordinator.state.power = False
        self.async_write_ha_state()
