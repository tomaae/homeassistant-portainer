"""Unit tests for unique ID generation fix in endpoint sensors."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add custom_components to Python path for testing
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

from portainer.coordinator import PortainerCoordinator  # noqa: E402
from portainer.sensor import EndpointSensor  # noqa: E402
from portainer.sensor_types import SENSOR_TYPES  # noqa: E402


class TestUniqueIdGeneration:
    """Test unique ID generation for endpoint sensors."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
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
        mock_entry.entry_id = "test_entry_01jzj6vmef68emftp5vwhrhg63"
        return mock_entry

    @pytest.fixture
    def coordinator(self, mock_config_entry):
        """Create a coordinator with endpoint data."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
        coordinator.config_entry = mock_config_entry
        coordinator.hass = MagicMock()
        coordinator.api = MagicMock()
        coordinator.name = "Test Portainer"
        coordinator.connected = MagicMock(return_value=True)
        
        # Mock endpoint data that could cause duplicate IDs
        coordinator.data = {
            "endpoints": {
                "1": {
                    "Id": 1,
                    "Name": "primary",
                    "Type": 1,
                    "Status": 1,
                    "DockerVersion": "20.10.17",
                    "Swarm": False,
                    "TotalCPU": 4,
                    "TotalMemory": 8000000000,
                    "RunningContainerCount": 5,
                    "StoppedContainerCount": 2,
                    "HealthyContainerCount": 5,
                    "UnhealthyContainerCount": 0,
                    "VolumeCount": 10,
                    "ImageCount": 15,
                    "ServiceCount": 0,
                    "StackCount": 2,
                },
                "2": {
                    "Id": 2,
                    "Name": "primary",  # Same name as endpoint 1
                    "Type": 2,
                    "Status": 1,
                    "DockerVersion": "20.10.18",
                    "Swarm": True,
                    "TotalCPU": 8,
                    "TotalMemory": 16000000000,
                    "RunningContainerCount": 10,
                    "StoppedContainerCount": 3,
                    "HealthyContainerCount": 9,
                    "UnhealthyContainerCount": 1,
                    "VolumeCount": 20,
                    "ImageCount": 25,
                    "ServiceCount": 5,
                    "StackCount": 3,
                },
                "3": {
                    "Id": 3,
                    "Name": "secondary",
                    "Type": 1,
                    "Status": 1,
                    "DockerVersion": "20.10.19",
                    "Swarm": False,
                    "TotalCPU": 2,
                    "TotalMemory": 4000000000,
                    "RunningContainerCount": 3,
                    "StoppedContainerCount": 1,
                    "HealthyContainerCount": 3,
                    "UnhealthyContainerCount": 0,
                    "VolumeCount": 5,
                    "ImageCount": 8,
                    "ServiceCount": 0,
                    "StackCount": 1,
                }
            }
        }
        return coordinator

    @pytest.fixture
    def endpoints_description(self):
        """Get the endpoints sensor description."""
        for desc in SENSOR_TYPES:
            if desc.key == "endpoints":
                return desc
        pytest.fail("Could not find endpoints sensor description")

    def test_endpoint_unique_ids_are_unique(self, coordinator, endpoints_description):
        """Test that all endpoint sensors have unique IDs."""
        sensors = []
        unique_ids = []
        
        for endpoint_id in coordinator.data["endpoints"]:
            sensor = EndpointSensor(coordinator, endpoints_description, endpoint_id)
            sensors.append(sensor)
            unique_ids.append(sensor.unique_id)
        
        # Verify all unique IDs are actually unique
        assert len(unique_ids) == len(set(unique_ids)), f"Duplicate unique IDs found: {unique_ids}"
        
        # Verify no unique ID is None or empty
        for unique_id in unique_ids:
            assert unique_id is not None, "unique_id should not be None"
            assert unique_id.strip() != "", "unique_id should not be empty"

    def test_endpoint_unique_id_format(self, coordinator, endpoints_description):
        """Test that endpoint unique IDs follow the expected format."""
        endpoint_id = "1"
        sensor = EndpointSensor(coordinator, endpoints_description, endpoint_id)
        
        # Expected format: {instance_name}-{description_key}-{endpoint_id}_{endpoint_name}_{config_entry_id}
        # Note: No slugify applied to preserve underscores
        expected_parts = [
            "test-portainer",  # instance name (lowercased, spaces to hyphens)
            "endpoints",        # description key
            "1_primary_test_entry_01jzj6vmef68emftp5vwhrhg63"  # endpoint_id_name_config_entry_id
        ]
        expected_unique_id = "-".join(expected_parts)
        
        assert sensor.unique_id == expected_unique_id

    def test_endpoints_with_same_name_different_ids(self, coordinator, endpoints_description):
        """Test that endpoints with the same name but different IDs get unique IDs."""
        # Both endpoint 1 and 2 have name "primary"
        sensor1 = EndpointSensor(coordinator, endpoints_description, "1")
        sensor2 = EndpointSensor(coordinator, endpoints_description, "2")
        
        assert sensor1.unique_id != sensor2.unique_id
        assert "1_primary" in sensor1.unique_id
        assert "2_primary" in sensor2.unique_id

    def test_endpoint_missing_id_uses_uid(self, coordinator, endpoints_description):
        """Test that endpoint without ID falls back to using uid."""
        # Remove the Id field from endpoint data
        endpoint_data = coordinator.data["endpoints"]["1"].copy()
        del endpoint_data["Id"]
        coordinator.data["endpoints"]["test_uid"] = endpoint_data
        
        sensor = EndpointSensor(coordinator, endpoints_description, "test_uid")
        
        # Should use the uid as endpoint_id
        assert "test_uid_primary" in sensor.unique_id

    def test_endpoint_missing_name_uses_unknown(self, coordinator, endpoints_description):
        """Test that endpoint without name uses 'unknown' as fallback."""
        # Create new endpoint data without Name field
        endpoint_data = {
            "Id": 4,
            "Type": 1,
            "Status": 1,
            "DockerVersion": "20.10.20",
            "Swarm": False,
            "TotalCPU": 2,
            "TotalMemory": 4000000000,
            "RunningContainerCount": 2,
            "StoppedContainerCount": 0,
            "HealthyContainerCount": 2,
            "UnhealthyContainerCount": 0,
            "VolumeCount": 3,
            "ImageCount": 5,
            "ServiceCount": 0,
            "StackCount": 0,
        }
        # Note: No "Name" field
        coordinator.data["endpoints"]["4"] = endpoint_data
        
        sensor = EndpointSensor(coordinator, endpoints_description, "4")
        
        # Should use 'unknown' as endpoint name
        assert "4_unknown" in sensor.unique_id

    def test_multiple_config_entries_different_unique_ids(self, endpoints_description):
        """Test that the same endpoint in different config entries gets different unique IDs."""
        # Create two coordinators with different config entries
        mock_entry1 = MagicMock()
        mock_entry1.data = {"name": "Portainer1"}
        mock_entry1.entry_id = "config_entry_1"
        
        mock_entry2 = MagicMock()
        mock_entry2.data = {"name": "Portainer2"}
        mock_entry2.entry_id = "config_entry_2"
        
        # Same endpoint data
        endpoint_data = {
            "endpoints": {
                "1": {
                    "Id": 1,
                    "Name": "primary",
                    "RunningContainerCount": 5,
                }
            }
        }
        
        coordinator1 = PortainerCoordinator.__new__(PortainerCoordinator)
        coordinator1.config_entry = mock_entry1
        coordinator1.data = endpoint_data
        
        coordinator2 = PortainerCoordinator.__new__(PortainerCoordinator)
        coordinator2.config_entry = mock_entry2
        coordinator2.data = endpoint_data
        
        sensor1 = EndpointSensor(coordinator1, endpoints_description, "1")
        sensor2 = EndpointSensor(coordinator2, endpoints_description, "1")
        
        # Should have different unique IDs due to different config entry IDs
        assert sensor1.unique_id != sensor2.unique_id
        assert "config_entry_1" in sensor1.unique_id
        assert "config_entry_2" in sensor2.unique_id

    def test_error_scenario_reproduction(self, coordinator, endpoints_description):
        """Test that the original error scenario is now fixed."""
        # The original error was: "ID portainer-endpoints-primary01jzj6vmef68emftp5vwhrhg63 already exists"
        # This suggests the old format was missing separators between name and config entry ID
        
        # Create a sensor with the data that would have caused the original error
        sensor = EndpointSensor(coordinator, endpoints_description, "1")
        
        # Verify the new format doesn't match the problematic old format
        old_problematic_format = "test-portainer-endpoints-primary01jzj6vmef68emftp5vwhrhg63"
        assert sensor.unique_id != old_problematic_format
        
        # Verify the new format has proper separators with underscores preserved
        assert "1_primary_test_entry_01jzj6vmef68emftp5vwhrhg63" in sensor.unique_id
        
        # Verify the format specifically to ensure underscores are preserved
        expected_format = "test-portainer-endpoints-1_primary_test_entry_01jzj6vmef68emftp5vwhrhg63"
        assert sensor.unique_id == expected_format

    def test_unique_id_consistency(self, coordinator, endpoints_description):
        """Test that the same endpoint always generates the same unique ID."""
        # Create the same sensor multiple times
        sensor1 = EndpointSensor(coordinator, endpoints_description, "1")
        sensor2 = EndpointSensor(coordinator, endpoints_description, "1")
        sensor3 = EndpointSensor(coordinator, endpoints_description, "1")
        
        # Should always generate the same unique ID
        assert sensor1.unique_id == sensor2.unique_id == sensor3.unique_id
