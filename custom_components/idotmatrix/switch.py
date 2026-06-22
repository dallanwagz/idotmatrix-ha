"""Switch platform for iDotMatrix — 180-degree flip."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .coordinator import IDotMatrixConfigEntry, IDotMatrixCoordinator
from .entity import IDotMatrixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IDotMatrixConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the iDotMatrix switches."""
    async_add_entities([IDotMatrixFlipSwitch(entry.runtime_data)])


class IDotMatrixFlipSwitch(IDotMatrixEntity, SwitchEntity):
    """Optimistic 180-degree display flip."""

    _attr_translation_key = "flip"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_assumed_state = True

    def __init__(self, coordinator: IDotMatrixCoordinator) -> None:
        """Initialise the flip switch."""
        super().__init__(coordinator, "flip")

    @property
    def is_on(self) -> bool:
        """Return assumed flip state."""
        return self.coordinator.state.flip

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Flip the display 180 degrees."""
        await self.coordinator.async_send(protocol.set_flip(True))
        self.coordinator.state.flip = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Restore normal orientation."""
        await self.coordinator.async_send(protocol.set_flip(False))
        self.coordinator.state.flip = False
        self.async_write_ha_state()
