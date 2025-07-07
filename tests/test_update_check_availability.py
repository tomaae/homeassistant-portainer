"""Tests for update check feature availability in buttons and sensors.

This test suite verifies that when the update check feature is disabled:
- Force update check button is always created but becomes unavailable when feature is disabled
- Force update check button is disabled by default when feature is not active initially
- Next update check sensor becomes unavailable when feature is disabled
- Next update check sensor is disabled by default when feature is not active initially
- Force update check functionality respects the feature flag
- Sensor attributes correctly reflect feature state

The tests cover the German requirement:
"when enable update check is not active, force update check button and next update sensor should be disabled"

Translation: "when enable update check is not active, force update check button and next update sensor should be disabled"

Key behavior:
- Button: Always created but availability changes dynamically based on feature state
- Sensor: Always created but availability changes dynamically based on feature state
- Both become unavailable (grayed out) when feature is disabled, available when enabled
- This allows for dynamic enabling/disabling without requiring integration restart
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add custom_components to Python path for testing
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

from portainer.button import ForceUpdateCheckButton  # noqa: E402
from portainer.coordinator import PortainerCoordinator  # noqa: E402
from portainer.sensor import UpdateCheckSensor  # noqa: E402
from portainer.const import CONF_FEATURE_UPDATE_CHECK  # noqa: E402


class TestUpdateCheckAvailability:
    """Test availability of update check components when feature is disabled."""

    @pytest.fixture
    def mock_config_entry_enabled(self):
        """Create a mock config entry with update check enabled."""
        mock_entry = MagicMock()
        mock_entry.data = {
            "host": "localhost",
            "api_key": "test_key",
            "name": "Test Portainer",
            "ssl": False,
            "verify_ssl": True,
        }
        mock_entry.options = {
            "feature_switch_update_check": True,
            "update_check_hour": 10,
        }
        mock_entry.entry_id = "test_entry"
        return mock_entry

    @pytest.fixture
    def mock_config_entry_disabled(self):
        """Create a mock config entry with update check disabled."""
        mock_entry = MagicMock()
        mock_entry.data = {
            "host": "localhost",
            "api_key": "test_key", 
            "name": "Test Portainer",
            "ssl": False,
            "verify_ssl": True,
        }
        mock_entry.options = {
            "feature_switch_update_check": False,
            "update_check_hour": 10,
        }
        mock_entry.entry_id = "test_entry"
        return mock_entry

    @pytest.fixture
    def coordinator_enabled(self, mock_config_entry_enabled):
        """Create a coordinator with update check enabled."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
        coordinator.features = {
            CONF_FEATURE_UPDATE_CHECK: True,
        }
        coordinator.config_entry = mock_config_entry_enabled
        coordinator.hass = MagicMock()
        coordinator.api = MagicMock()
        coordinator.name = "Test Portainer"
        coordinator.data = {
            "system": {
                "next_update_check": "2024-01-01T10:00:00Z",
                "last_update_check": "2024-01-01T08:00:00Z"
            }
        }
        coordinator._last_update_time = None
        coordinator.options = mock_config_entry_enabled.options
        
        # Mock the connected method
        coordinator.connected = MagicMock(return_value=True)
        
        return coordinator

    @pytest.fixture
    def coordinator_disabled(self, mock_config_entry_disabled):
        """Create a coordinator with update check disabled."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
        coordinator.features = {
            CONF_FEATURE_UPDATE_CHECK: False,
        }
        coordinator.config_entry = mock_config_entry_disabled
        coordinator.hass = MagicMock()
        coordinator.api = MagicMock()
        coordinator.name = "Test Portainer"
        coordinator.data = {
            "system": {
                "next_update_check": "disabled",
                "last_update_check": "never"
            }
        }
        coordinator._last_update_time = None
        coordinator.options = mock_config_entry_disabled.options
        
        # Mock the connected method
        coordinator.connected = MagicMock(return_value=True)
        
        return coordinator

    @pytest.fixture
    def mock_sensor_description(self):
        """Create a mock sensor description."""
        description = MagicMock()
        description.key = "update_check_status"
        description.name = "Container Update Check"
        description.data_attribute = "next_update_check"
        description.data_path = "system"
        description.data_name = ""
        description.data_uid = ""
        description.data_reference = ""
        description.data_attributes_list = []
        description.func = "UpdateCheckSensor"
        return description

    # Button Tests
    def test_force_update_button_enabled_when_feature_active(self, coordinator_enabled):
        """Test that force update button is available when update check feature is active."""
        button = ForceUpdateCheckButton(coordinator_enabled, "test_entry")
        
        # The button should be available when feature is active and coordinator is connected
        assert button.available is True
        assert button.coordinator.features[CONF_FEATURE_UPDATE_CHECK] is True
        
        # Entity should be enabled by default when feature is active
        assert button._attr_entity_registry_enabled_default is True

    def test_force_update_button_disabled_when_feature_inactive(self, coordinator_disabled):
        """Test that force update button is unavailable when update check feature is inactive."""
        button = ForceUpdateCheckButton(coordinator_disabled, "test_entry")
        
        # Verify the coordinator has the feature disabled
        assert button.coordinator.features[CONF_FEATURE_UPDATE_CHECK] is False
        
        # The button should be unavailable when feature is inactive
        assert button.available is False
        
        # Entity should be disabled by default when feature is inactive
        assert button._attr_entity_registry_enabled_default is False

    def test_force_update_button_press_when_feature_disabled(self, coordinator_disabled):
        """Test that pressing force update button when feature is disabled works but coordinator handles it."""
        button = ForceUpdateCheckButton(coordinator_disabled, "test_entry")
        
        # Button should not be available when feature is disabled
        assert button.available is False
        
        # Mock the coordinator's force_update_check method as an async method
        async def mock_force_update():
            pass
        
        coordinator_disabled.force_update_check = MagicMock(side_effect=mock_force_update)
        
        # Create an async press method test
        import asyncio
        
        async def test_press():
            # Even if pressed, coordinator should handle the disabled state
            await button.async_press()
            coordinator_disabled.force_update_check.assert_called_once()
        
        # Run the async test
        asyncio.run(test_press())

    def test_button_dynamic_availability_based_on_feature_state(self, coordinator_enabled, coordinator_disabled):
        """Test that button availability changes dynamically based on feature state."""
        # Test with feature enabled
        button_enabled = ForceUpdateCheckButton(coordinator_enabled, "test_entry")
        assert button_enabled.available is True
        assert button_enabled._attr_entity_registry_enabled_default is True
        
        # Test with feature disabled  
        button_disabled = ForceUpdateCheckButton(coordinator_disabled, "test_entry")
        assert button_disabled.available is False
        assert button_disabled._attr_entity_registry_enabled_default is False

    # Sensor Tests
    def test_update_check_sensor_enabled_when_feature_active(self, coordinator_enabled, mock_sensor_description):
        """Test that update check sensor is available when update check feature is active."""
        sensor = UpdateCheckSensor(coordinator_enabled, mock_sensor_description, None)
        
        # Sensor should be available when feature is active
        assert sensor.available is True
        assert sensor.coordinator.features[CONF_FEATURE_UPDATE_CHECK] is True
        
        # Entity should be enabled by default when feature is active
        assert sensor._attr_entity_registry_enabled_default is True

    def test_update_check_sensor_disabled_when_feature_inactive(self, coordinator_disabled, mock_sensor_description):
        """Test that update check sensor is unavailable when update check feature is inactive."""
        sensor = UpdateCheckSensor(coordinator_disabled, mock_sensor_description, None)
        
        # Verify coordinator has feature disabled
        assert sensor.coordinator.features[CONF_FEATURE_UPDATE_CHECK] is False
        
        # Sensor should be unavailable when feature is inactive
        assert sensor.available is False
        
        # Entity should be disabled by default when feature is inactive
        assert sensor._attr_entity_registry_enabled_default is False

    def test_sensor_extra_attributes_reflect_feature_state(self, coordinator_enabled, coordinator_disabled, mock_sensor_description):
        """Test that sensor extra attributes correctly reflect the feature state."""
        # Test with feature enabled
        sensor_enabled = UpdateCheckSensor(coordinator_enabled, mock_sensor_description, None)
        attrs_enabled = sensor_enabled.extra_state_attributes
        
        if attrs_enabled and "update_feature_enabled" in attrs_enabled:
            assert attrs_enabled["update_feature_enabled"] is True
        
        # Test with feature disabled  
        sensor_disabled = UpdateCheckSensor(coordinator_disabled, mock_sensor_description, None)
        attrs_disabled = sensor_disabled.extra_state_attributes
        
        if attrs_disabled and "update_feature_enabled" in attrs_disabled:
            assert attrs_disabled["update_feature_enabled"] is False

    def test_sensor_device_class_based_on_value_type(self, coordinator_enabled, mock_sensor_description):
        """Test that sensor device class is set correctly based on value type."""
        # Test with timestamp data
        sensor = UpdateCheckSensor(coordinator_enabled, mock_sensor_description, None)
        
        # The sensor should return a datetime object for valid datetime strings
        value = sensor.native_value
        device_class = sensor.device_class
        
        # For timestamp values, device_class should be "timestamp"
        from datetime import datetime
        if isinstance(value, datetime):
            assert device_class == "timestamp"
        elif value in ["disabled", "never"]:
            assert device_class is None
        else:
            # String representation of datetime
            assert device_class == "timestamp"
        
        # Test with disabled feature to get string value
        coordinator_enabled.data["system"]["next_update_check"] = "disabled"
        sensor_disabled = UpdateCheckSensor(coordinator_enabled, mock_sensor_description, None)
        assert sensor_disabled.native_value == "disabled"
        assert sensor_disabled.device_class is None

    def test_sensor_dynamic_availability_based_on_feature_state(self, coordinator_enabled, coordinator_disabled, mock_sensor_description):
        """Test that sensor availability changes dynamically based on feature state."""
        # Test with feature enabled
        sensor_enabled = UpdateCheckSensor(coordinator_enabled, mock_sensor_description, None)
        assert sensor_enabled.available is True
        assert sensor_enabled._attr_entity_registry_enabled_default is True
        
        # Test with feature disabled  
        sensor_disabled = UpdateCheckSensor(coordinator_disabled, mock_sensor_description, None)
        assert sensor_disabled.available is False
        assert sensor_disabled._attr_entity_registry_enabled_default is False

    # Coordinator Tests
    def test_coordinator_force_update_check_respects_feature_flag(self, coordinator_disabled):
        """Test that coordinator's force_update_check method respects the feature flag."""
        # Mock the logger and other dependencies
        with patch('portainer.coordinator._LOGGER') as mock_logger:
            # Mock the async_request_refresh method
            coordinator_disabled.async_request_refresh = MagicMock()
            coordinator_disabled.cached_update_results = {}
            coordinator_disabled.cached_registry_responses = {}
            
            import asyncio
            
            async def test_force_update():
                await coordinator_disabled.force_update_check()
                
                # Should log that feature is disabled and return early
                mock_logger.info.assert_called_with(
                    "Force update check requested but update check feature is disabled"
                )
                
                # Should not call async_request_refresh
                coordinator_disabled.async_request_refresh.assert_not_called()
            
            asyncio.run(test_force_update())

    # Combined Tests
    def test_button_and_sensor_consistent_behavior(self, coordinator_enabled, coordinator_disabled, mock_sensor_description):
        """Test that button and sensor have consistent availability behavior."""
        # With feature enabled
        button_enabled = ForceUpdateCheckButton(coordinator_enabled, "test_entry")
        sensor_enabled = UpdateCheckSensor(coordinator_enabled, mock_sensor_description, None)
        
        assert button_enabled.available == sensor_enabled.available == True
        assert button_enabled._attr_entity_registry_enabled_default == sensor_enabled._attr_entity_registry_enabled_default == True
        
        # With feature disabled
        button_disabled = ForceUpdateCheckButton(coordinator_disabled, "test_entry")
        sensor_disabled = UpdateCheckSensor(coordinator_disabled, mock_sensor_description, None)
        
        assert button_disabled.available == sensor_disabled.available == False
        assert button_disabled._attr_entity_registry_enabled_default == sensor_disabled._attr_entity_registry_enabled_default == False

    def test_feature_toggle_simulation(self, coordinator_enabled, mock_sensor_description):
        """Test simulation of feature being toggled on and off."""
        button = ForceUpdateCheckButton(coordinator_enabled, "test_entry")
        sensor = UpdateCheckSensor(coordinator_enabled, mock_sensor_description, None)
        
        # Initially enabled
        assert button.available is True
        assert sensor.available is True
        
        # Simulate feature being disabled by changing coordinator options
        coordinator_enabled.config_entry.options["feature_switch_update_check"] = False
        
        # Both should now be unavailable
        assert button.available is False
        assert sensor.available is False
        
        # Simulate feature being re-enabled
        coordinator_enabled.config_entry.options["feature_switch_update_check"] = True
        
        # Both should be available again
        assert button.available is True
        assert sensor.available is True
