"""Test fixtures and configuration for Portainer custom component tests."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add the custom component to Python path
# Adjust this path based on your repository structure
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry for testing."""
    mock_entry = Mock()
    mock_entry.options = {
        "feature_switch_update_check": True,
        "update_check_hour": 12,
    }
    mock_entry.data = {"host": "localhost", "port": 9000}
    return mock_entry


@pytest.fixture
def mock_hass():
    """Return a mock Home Assistant instance."""
    mock = Mock()
    mock.data = {}
    return mock


@pytest.fixture
def mock_portainer_api():
    """Return a mock Portainer API instance."""
    mock_api = Mock()
    mock_api.host = "localhost"
    mock_api.port = 9000
    mock_api.username = "admin"
    return mock_api
