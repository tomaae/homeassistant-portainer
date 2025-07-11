"""Test fixtures and configuration for Portainer custom component tests."""

import os
import sys
from pathlib import Path

import pytest

# Add the custom component to Python path
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

# Set environment variables for testing
os.environ["TESTING"] = "true"

# Import the official Home Assistant test framework
pytest_plugins = ["pytest_homeassistant_custom_component"]


# Import after path setup

from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.portainer.const import (  # noqa: E402
    CONF_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
    DOMAIN,
)


# Global pytest configuration for VS Code test discovery
def pytest_configure(config):
    """Configure pytest for VS Code test discovery."""
    # Add custom markers
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


def pytest_collection_modifyitems(config, items):
    """Modify test items for better organization in VS Code."""
    for item in items:
        # Add markers based on file paths and test names
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_homeassistant" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


# Constant for test config entry title and name
TEST_PORTAINER_TITLE = "Test Portainer"


@pytest.fixture
def mock_config_entry_feature_enabled():
    """Create a mock config entry with update check feature enabled."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TEST_PORTAINER_TITLE,
        data={"host": "localhost", "name": TEST_PORTAINER_TITLE},
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
        title=TEST_PORTAINER_TITLE,
        data={"host": "localhost", "name": TEST_PORTAINER_TITLE},
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
        title=TEST_PORTAINER_TITLE,
        data={"host": "localhost", "name": TEST_PORTAINER_TITLE},
        options={},
        entry_id="test_entry_new",
    )
