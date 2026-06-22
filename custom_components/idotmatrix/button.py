"""Button platform for iDotMatrix — sync time and reset."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .coordinator import IDotMatrixConfigEntry, IDotMatrixCoordinator
from .entity import IDotMatrixEntity


@dataclass(frozen=True, kw_only=True)
class IDotMatrixButtonDescription(ButtonEntityDescription):
    """Describes an iDotMatrix button and the frame it sends."""

    frame: Callable[[], bytes]


BUTTONS: tuple[IDotMatrixButtonDescription, ...] = (
    IDotMatrixButtonDescription(
        key="sync_time",
        translation_key="sync_time",
        entity_category=EntityCategory.CONFIG,
        frame=protocol.set_time,
    ),
    IDotMatrixButtonDescription(
        key="reset",
        translation_key="reset",
        entity_category=EntityCategory.CONFIG,
        device_class=None,
        frame=protocol.reset_device,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IDotMatrixConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the iDotMatrix buttons."""
    async_add_entities(
        IDotMatrixButton(entry.runtime_data, description) for description in BUTTONS
    )


class IDotMatrixButton(IDotMatrixEntity, ButtonEntity):
    """A stateless action button."""

    entity_description: IDotMatrixButtonDescription

    def __init__(
        self,
        coordinator: IDotMatrixCoordinator,
        description: IDotMatrixButtonDescription,
    ) -> None:
        """Initialise the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Send the button's frame."""
        await self.coordinator.async_send(self.entity_description.frame())
