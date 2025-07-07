"""Test fixtures and configuration for Portainer custom component tests."""

import sys
from pathlib import Path

import pytest

# Add the custom component to Python path
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

# Import the official Home Assistant test framework
pytest_plugins = "pytest_homeassistant_custom_component"

# Import after path setup
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.portainer.const import (  # noqa: E402
    CONF_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
    DOMAIN,
)


@pytest.fixture
def mock_config_entry_feature_enabled():
    """Create a mock config entry with update check feature enabled."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer",
        data={"host": "localhost", "name": "Test Portainer"},
        options={
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "04:30",
        },
        entry_id="test_entry_enabled",
    )


@pytest.fixture
def mock_config_entry_feature_disabled():
    """Create a mock config entry with update check feature disabled."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer",
        data={"host": "localhost", "name": "Test Portainer"},
        options={
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: False,
            CONF_UPDATE_CHECK_TIME: "04:30",
        },
        entry_id="test_entry_disabled",
    )


@pytest.fixture
def mock_config_entry_new():
    """Create a mock config entry for new installation (no options set)."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer",
        data={"host": "localhost", "name": "Test Portainer"},
        options={},
        entry_id="test_entry_new",
    )
