"""Constants for the iDotMatrix integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "idotmatrix"
LOGGER: Final = logging.getLogger(__package__)

MANUFACTURER: Final = "iDotMatrix"
DEFAULT_MODEL: Final = "HXS-002 (32x32)"

# BLE name prefix the panels advertise with.
NAME_PREFIX: Final = "IDM-"

# Reconnect backoff (seconds): capped exponential.
RECONNECT_BACKOFF_MIN: Final = 3
RECONNECT_BACKOFF_MAX: Final = 300

# Panel pixel dimensions (deviceType 3 = 32x32).
PANEL_WIDTH: Final = 32
PANEL_HEIGHT: Final = 32

# Services.
SERVICE_SEND_COMMAND: Final = "send_command"
ATTR_COMMAND: Final = "command"
ATTR_PARAMS: Final = "params"
SERVICE_SET_IMAGE: Final = "set_image"
ATTR_PATH: Final = "path"
