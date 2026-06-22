"""Fixtures for iDotMatrix tests.

The config-flow/integration tests require the Home Assistant test harness:
    pip install homeassistant pytest-homeassistant-custom-component
The protocol tests (test_protocol.py) have no such dependency and run standalone,
so the HA plugin is only registered when it is importable.
"""

from importlib.util import find_spec

_HAS_HA_HARNESS = find_spec("pytest_homeassistant_custom_component") is not None

if _HAS_HA_HARNESS:
    from collections.abc import Generator
    from unittest.mock import patch

    import pytest

    pytest_plugins = ["pytest_homeassistant_custom_component"]

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
        """Enable loading custom integrations in all tests."""
        return

    @pytest.fixture
    def mock_setup_entry() -> "Generator[None]":
        """Prevent the real entry setup (BLE connect) during config-flow tests."""
        with patch(
            "custom_components.idotmatrix.async_setup_entry", return_value=True
        ) as mock:
            yield mock


def pytest_ignore_collect(collection_path, config):
    """Skip HA-harness tests when the harness isn't installed."""
    if not _HAS_HA_HARNESS and collection_path.name in {
        "test_config_flow.py",
        "test_init.py",
    }:
        return True
    return None
