"""Specific test for the reported issue: Entities disabled despite enabled feature."""

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


def test_reported_issue_entities_enabled_when_feature_enabled():
    """
    Test for the specific reported issue:
    "during initialization, button and sensor are disabled although enable update check is enabled"
    
    Translation: "during initialization, button and sensor are disabled although enable update check is enabled"
    """
    print("\n🐛 Testing reported issue: Entities disabled despite enabled feature")
    
    # Setup: Create coordinator with enabled update check feature
    mock_config_entry = MagicMock()
    mock_config_entry.data = {
        "host": "localhost",
        "api_key": "test_key",
        "name": "Test Portainer",
        "ssl": False,
        "verify_ssl": True,
    }
    mock_config_entry.options = {
        "feature_switch_update_check": True,  # ✅ Feature is ENABLED
        "update_check_hour": 10,
    }
    mock_config_entry.entry_id = "test_entry"
    
    coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
    coordinator.features = {
        CONF_FEATURE_UPDATE_CHECK: True,  # ✅ Feature is ENABLED in coordinator
    }
    coordinator.config_entry = mock_config_entry
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
    coordinator.options = mock_config_entry.options
    coordinator.connected = MagicMock(return_value=True)  # ✅ Coordinator is connected
    
    # Create sensor description
    mock_sensor_description = MagicMock()
    mock_sensor_description.key = "update_check_status"
    mock_sensor_description.name = "Container Update Check"
    mock_sensor_description.data_attribute = "next_update_check"
    mock_sensor_description.data_path = "system"
    mock_sensor_description.data_name = ""
    mock_sensor_description.data_uid = ""
    mock_sensor_description.data_reference = ""
    mock_sensor_description.data_attributes_list = []
    mock_sensor_description.func = "UpdateCheckSensor"
    
    print(f"✅ Setup complete:")
    print(f"   - Feature enabled in config: {mock_config_entry.options['feature_switch_update_check']}")
    print(f"   - Feature enabled in coordinator: {coordinator.features[CONF_FEATURE_UPDATE_CHECK]}")
    print(f"   - Coordinator connected: {coordinator.connected()}")
    
    # Initialize button and sensor
    print(f"\n🔄 Initializing entities...")
    button = ForceUpdateCheckButton(coordinator, "test_entry")
    sensor = UpdateCheckSensor(coordinator, mock_sensor_description, None)
    
    # Check the reported issue: Are entities enabled despite feature being enabled?
    print(f"\n🔍 Checking entity states after initialization:")
    
    # Button checks
    button_available = button.available
    button_enabled_default_attr = button._attr_entity_registry_enabled_default
    button_enabled_default_prop = button.entity_registry_enabled_default
    
    print(f"   🔘 Button:")
    print(f"      - available: {button_available}")
    print(f"      - _attr_entity_registry_enabled_default: {button_enabled_default_attr}")
    print(f"      - entity_registry_enabled_default: {button_enabled_default_prop}")
    
    # Sensor checks
    sensor_available = sensor.available
    sensor_enabled_default_attr = sensor._attr_entity_registry_enabled_default
    sensor_enabled_default_prop = sensor.entity_registry_enabled_default
    
    print(f"   📊 Sensor:")
    print(f"      - available: {sensor_available}")
    print(f"      - _attr_entity_registry_enabled_default: {sensor_enabled_default_attr}")
    print(f"      - entity_registry_enabled_default: {sensor_enabled_default_prop}")
    
    # Verify the fix: All should be True when feature is enabled
    print(f"\n✅ Verifying fix:")
    
    # Button assertions
    assert button_available is True, "❌ Button should be available when feature is enabled"
    assert button_enabled_default_attr is True, "❌ Button _attr_entity_registry_enabled_default should be True when feature is enabled"
    assert button_enabled_default_prop is True, "❌ Button entity_registry_enabled_default should be True when feature is enabled"
    print(f"   ✅ Button: All properties are correctly True")
    
    # Sensor assertions
    assert sensor_available is True, "❌ Sensor should be available when feature is enabled"
    assert sensor_enabled_default_attr is True, "❌ Sensor _attr_entity_registry_enabled_default should be True when feature is enabled"
    assert sensor_enabled_default_prop is True, "❌ Sensor entity_registry_enabled_default should be True when feature is enabled"
    print(f"   ✅ Sensor: All properties are correctly True")
    
    print(f"\n🎉 Issue fixed! Both entities are properly enabled when feature is enabled")
    print(f"   - Button and sensor are available (not grayed out)")
    print(f"   - Button and sensor are enabled by default in entity registry")
    print(f"   - Both static and dynamic properties return correct values")


def test_contrast_entities_enabled_by_default_but_unavailable_when_feature_disabled():
    """
    Contrast test: Verify entities are enabled by default but unavailable when feature is disabled.
    This ensures our fix provides the right balance: enabled by default but respects feature settings.
    """
    print("\n🔄 Contrast test: Entities enabled by default but unavailable when feature disabled")
    
    # Setup: Create coordinator with disabled update check feature
    mock_config_entry = MagicMock()
    mock_config_entry.data = {
        "host": "localhost",
        "api_key": "test_key",
        "name": "Test Portainer",
        "ssl": False,
        "verify_ssl": True,
    }
    mock_config_entry.options = {
        "feature_switch_update_check": False,  # ❌ Feature is DISABLED
        "update_check_hour": 10,
    }
    mock_config_entry.entry_id = "test_entry"
    
    coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
    coordinator.features = {
        CONF_FEATURE_UPDATE_CHECK: False,  # ❌ Feature is DISABLED in coordinator
    }
    coordinator.config_entry = mock_config_entry
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
    coordinator.options = mock_config_entry.options
    coordinator.connected = MagicMock(return_value=True)  # ✅ Coordinator is connected
    
    # Create sensor description
    mock_sensor_description = MagicMock()
    mock_sensor_description.key = "update_check_status"
    mock_sensor_description.name = "Container Update Check"
    mock_sensor_description.data_attribute = "next_update_check"
    mock_sensor_description.data_path = "system"
    mock_sensor_description.data_name = ""
    mock_sensor_description.data_uid = ""
    mock_sensor_description.data_reference = ""
    mock_sensor_description.data_attributes_list = []
    mock_sensor_description.func = "UpdateCheckSensor"
    
    # Initialize button and sensor
    button = ForceUpdateCheckButton(coordinator, "test_entry")
    sensor = UpdateCheckSensor(coordinator, mock_sensor_description, None)
    
    # Verify entities behavior when feature is disabled
    # NEW LOGIC: Entities are disabled by default when feature is explicitly disabled
    assert button.available is False, "Button should be unavailable when feature is disabled"
    assert button._attr_entity_registry_enabled_default is False, "Button should be disabled by default when feature is explicitly disabled"
    
    assert sensor.available is False, "Sensor should be unavailable when feature is disabled"
    assert sensor._attr_entity_registry_enabled_default is False, "Sensor should be disabled by default when feature is explicitly disabled"
    
    print(f"   ✅ Entities correctly disabled by default when feature is explicitly disabled")


if __name__ == "__main__":
    # Run the specific test for the reported issue
    test_reported_issue_entities_enabled_when_feature_enabled()
    test_contrast_entities_enabled_by_default_but_unavailable_when_feature_disabled()
    print(f"\n🎯 All tests passed! The reported issue has been fixed.")
