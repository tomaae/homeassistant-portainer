"""Test for correct initialization of button and sensor when feature is enabled."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add custom_components to Python path for testing
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

from portainer.button import ForceUpdateCheckButton  # noqa: E402
from portainer.coordinator import PortainerCoordinator  # noqa: E402
from portainer.sensor import UpdateCheckSensor  # noqa: E402
from portainer.const import CONF_FEATURE_UPDATE_CHECK  # noqa: E402


class TestEntityInitialization:
    """Test proper initialization of entities when feature is enabled."""

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
            "feature_switch_update_check": True,  # Feature explicitly enabled
            "update_check_hour": 10,
        }
        mock_entry.entry_id = "test_entry"
        return mock_entry

    @pytest.fixture
    def coordinator_with_enabled_feature(self, mock_config_entry_enabled):
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
        
        # Mock the connected method to return True
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

    def test_button_initialization_with_enabled_feature(self, coordinator_with_enabled_feature):
        """Test that button is properly initialized when feature is enabled."""
        # Verify feature is enabled in config
        feature_enabled = coordinator_with_enabled_feature.config_entry.options.get(CONF_FEATURE_UPDATE_CHECK, False)
        assert feature_enabled is True, "Feature should be enabled in coordinator config"
        
        # Create button
        button = ForceUpdateCheckButton(coordinator_with_enabled_feature, "test_entry")
        
        # Test initialization properties
        assert button.available is True, "Button should be available when feature is enabled and coordinator connected"
        
        # Test entity registry properties
        assert button._attr_entity_registry_enabled_default is True, "Button should be enabled by default when feature is enabled"
        assert button.entity_registry_enabled_default is True, "Button dynamic property should return True when feature is enabled"
        
        print("✅ Button initialized correctly with enabled feature")

    def test_sensor_initialization_with_enabled_feature(self, coordinator_with_enabled_feature, mock_sensor_description):
        """Test that sensor is properly initialized when feature is enabled."""
        # Verify feature is enabled in config
        feature_enabled = coordinator_with_enabled_feature.config_entry.options.get(CONF_FEATURE_UPDATE_CHECK, False)
        assert feature_enabled is True, "Feature should be enabled in coordinator config"
        
        # Create sensor
        sensor = UpdateCheckSensor(coordinator_with_enabled_feature, mock_sensor_description, None)
        
        # Test initialization properties
        assert sensor.available is True, "Sensor should be available when feature is enabled and coordinator connected"
        
        # Test entity registry properties
        assert sensor._attr_entity_registry_enabled_default is True, "Sensor should be enabled by default when feature is enabled"
        assert sensor.entity_registry_enabled_default is True, "Sensor dynamic property should return True when feature is enabled"
        
        print("✅ Sensor initialized correctly with enabled feature")

    def test_button_and_sensor_consistent_initialization(self, coordinator_with_enabled_feature, mock_sensor_description):
        """Test that both button and sensor are initialized consistently when feature is enabled."""
        # Create both entities
        button = ForceUpdateCheckButton(coordinator_with_enabled_feature, "test_entry")
        sensor = UpdateCheckSensor(coordinator_with_enabled_feature, mock_sensor_description, None)
        
        # Both should have the same availability
        assert button.available == sensor.available == True, "Both entities should be available"
        
        # Both should have the same entity registry default state
        assert button._attr_entity_registry_enabled_default == sensor._attr_entity_registry_enabled_default == True
        assert button.entity_registry_enabled_default == sensor.entity_registry_enabled_default == True
        
        print("✅ Button and sensor initialized consistently")

    def test_feature_status_check_during_initialization(self, coordinator_with_enabled_feature, mock_sensor_description):
        """Test that feature status is correctly checked during initialization."""
        # Verify coordinator setup
        assert coordinator_with_enabled_feature.features[CONF_FEATURE_UPDATE_CHECK] is True
        assert coordinator_with_enabled_feature.config_entry.options["feature_switch_update_check"] is True
        assert coordinator_with_enabled_feature.connected() is True
        
        print(f"Feature in coordinator.features: {coordinator_with_enabled_feature.features[CONF_FEATURE_UPDATE_CHECK]}")
        print(f"Feature in coordinator.config_entry.options: {coordinator_with_enabled_feature.config_entry.options['feature_switch_update_check']}")
        print(f"Coordinator connected: {coordinator_with_enabled_feature.connected()}")
        
        # Create entities and verify they use the correct feature status
        button = ForceUpdateCheckButton(coordinator_with_enabled_feature, "test_entry")
        sensor = UpdateCheckSensor(coordinator_with_enabled_feature, mock_sensor_description, None)
        
        # Both should be properly enabled
        assert button.available is True
        assert sensor.available is True
        assert button._attr_entity_registry_enabled_default is True
        assert sensor._attr_entity_registry_enabled_default is True
        
        print("✅ Feature status correctly checked during initialization")

    def test_debug_initialization_states(self, coordinator_with_enabled_feature, mock_sensor_description):
        """Debug test to show all relevant states during initialization."""
        # Show coordinator state
        print(f"\n🔍 Coordinator state:")
        print(f"  - features[CONF_FEATURE_UPDATE_CHECK]: {coordinator_with_enabled_feature.features[CONF_FEATURE_UPDATE_CHECK]}")
        print(f"  - config_entry.options['feature_switch_update_check']: {coordinator_with_enabled_feature.config_entry.options['feature_switch_update_check']}")
        print(f"  - connected(): {coordinator_with_enabled_feature.connected()}")
        
        # Create and show button state
        button = ForceUpdateCheckButton(coordinator_with_enabled_feature, "test_entry")
        print(f"\n🔘 Button state:")
        print(f"  - available: {button.available}")
        print(f"  - _attr_entity_registry_enabled_default: {button._attr_entity_registry_enabled_default}")
        print(f"  - entity_registry_enabled_default: {button.entity_registry_enabled_default}")
        
        # Create and show sensor state
        sensor = UpdateCheckSensor(coordinator_with_enabled_feature, mock_sensor_description, None)
        print(f"\n📊 Sensor state:")
        print(f"  - available: {sensor.available}")
        print(f"  - _attr_entity_registry_enabled_default: {sensor._attr_entity_registry_enabled_default}")
        print(f"  - entity_registry_enabled_default: {sensor.entity_registry_enabled_default}")
        
        # All should be True when feature is enabled
        assert all([
            button.available,
            button._attr_entity_registry_enabled_default,
            button.entity_registry_enabled_default,
            sensor.available,
            sensor._attr_entity_registry_enabled_default,
            sensor.entity_registry_enabled_default
        ]), "All properties should be True when feature is enabled"
        
        print("\n✅ All states are correct when feature is enabled")
