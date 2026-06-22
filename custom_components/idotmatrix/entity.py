"""Base entity for the iDotMatrix integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_MODEL, DOMAIN, MANUFACTURER
from .coordinator import IDotMatrixCoordinator


class IDotMatrixEntity(CoordinatorEntity[IDotMatrixCoordinator]):
    """Common base: device info, unique id, availability from the BLE link."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IDotMatrixCoordinator, key: str) -> None:
        """Initialise with a per-entity key appended to the address."""
        super().__init__(coordinator)
        address = coordinator.address
        self._attr_unique_id = f"{address}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            identifiers={(DOMAIN, address)},
            manufacturer=MANUFACTURER,
            model=DEFAULT_MODEL,
            name=f"iDotMatrix {address.replace(':', '')[-6:]}",
        )

    @property
    def available(self) -> bool:
        """Available only while the BLE link is up."""
        return self.coordinator.connected
