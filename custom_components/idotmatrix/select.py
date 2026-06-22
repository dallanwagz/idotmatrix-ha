"""Select platform for iDotMatrix — clock face style."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .coordinator import IDotMatrixConfigEntry, IDotMatrixCoordinator
from .entity import IDotMatrixEntity

# option label -> ClockStyle value
CLOCK_OPTIONS: dict[str, int] = {style.name.lower(): int(style) for style in protocol.ClockStyle}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IDotMatrixConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the iDotMatrix selects."""
    async_add_entities([IDotMatrixClockSelect(entry.runtime_data)])


class IDotMatrixClockSelect(IDotMatrixEntity, SelectEntity):
    """Choose a clock face (selecting one shows that clock)."""

    _attr_translation_key = "clock_face"
    _attr_options = list(CLOCK_OPTIONS)
    _attr_assumed_state = True

    def __init__(self, coordinator: IDotMatrixCoordinator) -> None:
        """Initialise the clock-face select."""
        super().__init__(coordinator, "clock_face")

    @property
    def current_option(self) -> str | None:
        """Return the assumed selected clock face, if a clock is active."""
        style = self.coordinator.state.clock_style
        if style is None:
            return None
        for name, value in CLOCK_OPTIONS.items():
            if value == style:
                return name
        return None

    async def async_select_option(self, option: str) -> None:
        """Show the chosen clock face."""
        style = CLOCK_OPTIONS[option]
        await self.coordinator.async_send(protocol.set_clock(style))
        self.coordinator.state.clock_style = style
        self.coordinator.state.color_active = False
        self.async_write_ha_state()
