"""Connection manager for an iDotMatrix panel.

The panel exposes no readable runtime state and reverts to its idle animation
whenever the BLE link drops, so this is not a polling coordinator. It is a
persistent-connection manager that:

* owns a single :class:`bleak.BleakClient` (the panel accepts ONE central),
* reconnects with capped exponential backoff,
* re-asserts the last assumed state (time + power + brightness + colour) on every
  (re)connect, and
* drives optimistic entities, which keep their own assumed state.

It subclasses :class:`DataUpdateCoordinator` purely to reuse the listener/teardown
machinery (``async_update_listeners``, ``async_add_listener``); there is no polling
(``update_interval`` is ``None``).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import BleakError, establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import protocol
from .const import (
    LOGGER,
    RECONNECT_BACKOFF_MAX,
    RECONNECT_BACKOFF_MIN,
)

type IDotMatrixConfigEntry = ConfigEntry[IDotMatrixCoordinator]


@dataclass
class AssumedState:
    """Optimistic state we believe the panel is in (it cannot be read back)."""

    power: bool = True
    brightness: int = 100  # percent
    rgb: tuple[int, int, int] = (255, 255, 255)
    # Whether the active scene is a solid colour (vs a clock/timer/etc.).
    color_active: bool = False
    flip: bool = False
    clock_style: int | None = None
    extra: dict[str, object] = field(default_factory=dict)


class IDotMatrixCoordinator(DataUpdateCoordinator[None]):
    """Owns the BLE connection to one panel and serialises writes to it."""

    config_entry: IDotMatrixConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: IDotMatrixConfigEntry,
        address: str,
    ) -> None:
        """Initialise the connection manager."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"iDotMatrix {address}",
            update_interval=None,
        )
        self.address = address
        self.state = AssumedState()
        self._client: BleakClient | None = None
        self._lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self._expected_disconnect = False
        self._reconnect_task: asyncio.Task[None] | None = None
        self._closing = False

    @property
    def connected(self) -> bool:
        """Return True when the BLE link is up."""
        return self._client is not None and self._client.is_connected

    async def async_start(self) -> None:
        """Establish the initial connection (raises on failure for setup retry)."""
        await self._async_connect()

    async def async_stop(self) -> None:
        """Tear down the connection and cancel reconnection."""
        self._closing = True
        self._expected_disconnect = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        if self._client is not None:
            try:
                await self._client.disconnect()
            except BleakError as err:  # pragma: no cover - best effort
                LOGGER.debug("Error disconnecting %s: %s", self.address, err)
            self._client = None

    async def _async_connect(self) -> None:
        """Connect to the panel and prime it."""
        async with self._connect_lock:
            if self.connected:
                return
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if device is None:
                raise HomeAssistantError(
                    f"iDotMatrix panel {self.address} not found by any Bluetooth adapter"
                )
            self._expected_disconnect = False
            client = await establish_connection(
                BleakClient,
                device,
                self.address,
                disconnected_callback=self._on_disconnect,
            )
            await client.start_notify(protocol.NOTIFY_UUID, self._on_notify)
            self._client = client
            LOGGER.debug("Connected to iDotMatrix %s", self.address)
            await self._async_reassert()
            self.async_update_listeners()

    @callback
    def _on_disconnect(self, _client: BleakClient) -> None:
        """Handle an unexpected disconnect by scheduling a reconnect."""
        self._client = None
        self.async_update_listeners()
        if self._expected_disconnect or self._closing:
            return
        LOGGER.debug("iDotMatrix %s disconnected; scheduling reconnect", self.address)
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = self.config_entry.async_create_background_task(
                self.hass, self._reconnect_loop(), f"idotmatrix-reconnect-{self.address}"
            )

    async def _reconnect_loop(self) -> None:
        """Reconnect with capped exponential backoff until successful."""
        delay = RECONNECT_BACKOFF_MIN
        while not self._closing and not self.connected:
            try:
                await self._async_connect()
                return
            except (BleakError, HomeAssistantError, TimeoutError) as err:
                LOGGER.debug(
                    "Reconnect to %s failed (%s); retrying in %ss",
                    self.address,
                    err,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_BACKOFF_MAX)

    @callback
    def _on_notify(self, _char: BleakGATTCharacteristic, data: bytearray) -> None:
        """Log inbound ACK frames from fa03 (status only; nothing to read back)."""
        status = protocol.parse_status(bytes(data))
        LOGGER.debug("iDotMatrix %s notify %s -> %s", self.address, data.hex(), status.ack.name)

    async def _async_reassert(self) -> None:
        """Re-apply assumed state after a (re)connect."""
        await self._write(protocol.set_time())
        await self._write(protocol.set_screen(self.state.power))
        if not self.state.power:
            return
        await self._write(protocol.set_brightness(self.state.brightness))
        if self.state.color_active:
            await self._write(protocol.set_fullscreen_color(*self.state.rgb))

    async def async_send(self, frame: bytes) -> None:
        """Send a single control frame, connecting first if needed."""
        if not self.connected:
            await self._async_connect()
        await self._write(frame)

    async def _write(self, frame: bytes) -> None:
        """Serialise a write to the command characteristic."""
        async with self._lock:
            client = self._client
            if client is None or not client.is_connected:
                raise HomeAssistantError(f"iDotMatrix {self.address} is not connected")
            try:
                await client.write_gatt_char(protocol.WRITE_UUID, frame, response=False)
            except BleakError as err:
                raise HomeAssistantError(
                    f"Failed to write to iDotMatrix {self.address}: {err}"
                ) from err
