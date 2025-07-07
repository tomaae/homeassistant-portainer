"""Test button and sensor availability fix."""

from unittest.mock import MagicMock

import pytest

from custom_components.portainer.button import ForceUpdateCheckButton
from custom_components.portainer.coordinator import PortainerCoordinator
from custom_components.portainer.sensor import UpdateCheckSensor
from custom_components.portainer.sensor_types import SENSOR_TYPES


@pytest.fixture
def mock_config_entry_no_options():
    """Create a mock config entry without options (new integration)."""
    mock_entry = MagicMock()
    mock_entry.data = {
        "host": "localhost:9000",
        "api_key": "ptr_test_key",
        "name": "Test Portainer",
        "ssl": False,
        "verify_ssl": True,
    }
    mock_entry.options = {}  # No options set yet (new integration)
    mock_entry.entry_id = "test_entry_new"
    return mock_entry


@pytest.fixture
def mock_config_entry_feature_enabled():
    """Create a mock config entry with feature enabled."""
    mock_entry = MagicMock()
    mock_entry.data = {
        "host": "localhost:9000",
        "api_key": "ptr_test_key",
        "name": "Test Portainer",
        "ssl": False,
        "verify_ssl": True,
    }
    mock_entry.options = {
        "feature_switch_update_check": True,
        "update_check_hour": 10,
    }
    mock_entry.entry_id = "test_entry_enabled"
    return mock_entry


@pytest.fixture
def mock_config_entry_feature_disabled():
    """Create a mock config entry with feature disabled."""
    mock_entry = MagicMock()
    mock_entry.data = {
        "host": "localhost:9000",
        "api_key": "ptr_test_key",
        "name": "Test Portainer",
        "ssl": False,
        "verify_ssl": True,
    }
    mock_entry.options = {
        "feature_switch_update_check": False,
        "update_check_hour": 10,
    }
    mock_entry.entry_id = "test_entry_disabled"
    return mock_entry


@pytest.fixture
def coordinator_base():
    """Create a base coordinator."""
    coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
    coordinator.hass = MagicMock()
    coordinator.api = MagicMock()
    coordinator.name = "Test Portainer"
    coordinator.connected = MagicMock(return_value=True)
    # Add required data structure
    coordinator.data = {"system": {"next_update_check": "2025-07-07T10:00:00Z"}}
    return coordinator


@pytest.fixture
def update_check_description():
    """Get the update check sensor description."""
    for desc in SENSOR_TYPES:
        if desc.key == "update_check_status":
            return desc
    pytest.fail("Could not find update_check_status sensor description")


class TestEntityAvailabilityFix:
    """Test entity availability and enabled state fix."""

    def test_button_enabled_default_new_integration(
        self, coordinator_base, mock_config_entry_no_options
    ):
        """Test button is enabled by default for new integration without options due to DEFAULT_FEATURE_UPDATE_CHECK=True."""
        coordinator_base.config_entry = mock_config_entry_no_options

        button = ForceUpdateCheckButton(
            coordinator_base, mock_config_entry_no_options.entry_id
        )

        # Should be enabled by default due to DEFAULT_FEATURE_UPDATE_CHECK=True
        assert button._attr_entity_registry_enabled_default is True

    def test_button_enabled_default_feature_enabled(
        self, coordinator_base, mock_config_entry_feature_enabled
    ):
        """Test button is enabled by default when feature is enabled."""
        coordinator_base.config_entry = mock_config_entry_feature_enabled

        button = ForceUpdateCheckButton(
            coordinator_base, mock_config_entry_feature_enabled.entry_id
        )

        # Should be enabled by default
        assert button._attr_entity_registry_enabled_default is True

    def test_button_enabled_default_feature_disabled(
        self, coordinator_base, mock_config_entry_feature_disabled
    ):
        """Test button is disabled by default when feature is explicitly disabled."""
        coordinator_base.config_entry = mock_config_entry_feature_disabled

        button = ForceUpdateCheckButton(
            coordinator_base, mock_config_entry_feature_disabled.entry_id
        )

        # Should be disabled by default when feature is explicitly disabled
        assert button._attr_entity_registry_enabled_default is False

    def test_button_availability_no_options(
        self, coordinator_base, mock_config_entry_no_options
    ):
        """Test button availability when no options are set - should be available due to DEFAULT_FEATURE_UPDATE_CHECK=True."""
        coordinator_base.config_entry = mock_config_entry_no_options

        button = ForceUpdateCheckButton(
            coordinator_base, mock_config_entry_no_options.entry_id
        )

        # Should be available since DEFAULT_FEATURE_UPDATE_CHECK=True
        assert button.available is True

    def test_button_availability_feature_enabled(
        self, coordinator_base, mock_config_entry_feature_enabled
    ):
        """Test button availability when feature is enabled."""
        coordinator_base.config_entry = mock_config_entry_feature_enabled

        button = ForceUpdateCheckButton(
            coordinator_base, mock_config_entry_feature_enabled.entry_id
        )

        # Should be available since feature is enabled and coordinator is connected
        assert button.available is True

    def test_button_availability_feature_disabled(
        self, coordinator_base, mock_config_entry_feature_disabled
    ):
        """Test button availability when feature is disabled."""
        coordinator_base.config_entry = mock_config_entry_feature_disabled

        button = ForceUpdateCheckButton(
            coordinator_base, mock_config_entry_feature_disabled.entry_id
        )

        # Should not be available since feature is disabled
        assert button.available is False

    def test_sensor_enabled_default_new_integration(
        self, coordinator_base, mock_config_entry_no_options, update_check_description
    ):
        """Test sensor is enabled by default for new integration without options due to DEFAULT_FEATURE_UPDATE_CHECK=True."""
        coordinator_base.config_entry = mock_config_entry_no_options

        sensor = UpdateCheckSensor(coordinator_base, update_check_description)

        # Should be enabled by default due to DEFAULT_FEATURE_UPDATE_CHECK=True
        assert sensor._attr_entity_registry_enabled_default is True

    def test_sensor_enabled_default_feature_enabled(
        self,
        coordinator_base,
        mock_config_entry_feature_enabled,
        update_check_description,
    ):
        """Test sensor is enabled by default when feature is enabled."""
        coordinator_base.config_entry = mock_config_entry_feature_enabled

        sensor = UpdateCheckSensor(coordinator_base, update_check_description)

        # Should be enabled by default
        assert sensor._attr_entity_registry_enabled_default is True

    def test_sensor_enabled_default_feature_disabled(
        self,
        coordinator_base,
        mock_config_entry_feature_disabled,
        update_check_description,
    ):
        """Test sensor is disabled by default when feature is explicitly disabled."""
        coordinator_base.config_entry = mock_config_entry_feature_disabled

        sensor = UpdateCheckSensor(coordinator_base, update_check_description)

        # Should be disabled by default when feature is explicitly disabled
        assert sensor._attr_entity_registry_enabled_default is False

    def test_sensor_availability_no_options(
        self, coordinator_base, mock_config_entry_no_options, update_check_description
    ):
        """Test sensor availability when no options are set - should be available due to DEFAULT_FEATURE_UPDATE_CHECK=True."""
        coordinator_base.config_entry = mock_config_entry_no_options

        sensor = UpdateCheckSensor(coordinator_base, update_check_description)

        # Should be available since DEFAULT_FEATURE_UPDATE_CHECK=True
        assert sensor.available is True

    def test_sensor_availability_feature_enabled(
        self,
        coordinator_base,
        mock_config_entry_feature_enabled,
        update_check_description,
    ):
        """Test sensor availability when feature is enabled."""
        coordinator_base.config_entry = mock_config_entry_feature_enabled

        sensor = UpdateCheckSensor(coordinator_base, update_check_description)

        # Should be available since feature is enabled and coordinator is connected
        assert sensor.available is True

    def test_sensor_availability_feature_disabled(
        self,
        coordinator_base,
        mock_config_entry_feature_disabled,
        update_check_description,
    ):
        """Test sensor availability when feature is disabled."""
        coordinator_base.config_entry = mock_config_entry_feature_disabled

        sensor = UpdateCheckSensor(coordinator_base, update_check_description)

        # Should not be available since feature is disabled
        assert sensor.available is False
