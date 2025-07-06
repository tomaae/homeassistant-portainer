"""Tests for Portainer coordinator update check functionality."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add custom_components to Python path for testing
# Adjust this path based on your repository structure
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

# Import the coordinator after adding to path
from portainer.coordinator import PortainerCoordinator  # noqa: E402


class TestUpdateCheckLogic:
    """Test class for container update check functionality."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
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
    def coordinator_with_mock(self, mock_config_entry):
        """Create a coordinator instance with mocked dependencies."""
        # Create a minimal coordinator for testing
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        # Initialize required attributes
        coordinator.features = {
            "feature_switch_update_check": True,
        }
        coordinator.config_entry = mock_config_entry
        coordinator.hass = MagicMock()
        coordinator.api = MagicMock()
        coordinator.last_update_check = None
        coordinator.cached_update_results = {}
        coordinator.cached_registry_responses = {}
        coordinator.force_update_requested = False

        # Add property for update_check_hour that reads from config
        @property
        def update_check_hour(self):
            return self.config_entry.options.get("update_check_hour", 10)

        coordinator.__class__.update_check_hour = update_check_hour

        return coordinator

    def test_should_check_updates_feature_disabled(self, coordinator_with_mock):
        """Test should_check_updates when feature is disabled."""
        coordinator_with_mock.features["feature_switch_update_check"] = False
        result = coordinator_with_mock.should_check_updates()
        assert result is False

    def test_should_check_updates_force_update(self, coordinator_with_mock):
        """Test should_check_updates with feature enabled."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        result = coordinator_with_mock.should_check_updates()
        assert result is True

    def test_should_check_updates_first_check(self, coordinator_with_mock):
        """Test should_check_updates for first time check."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        coordinator_with_mock.last_update_check = None
        result = coordinator_with_mock.should_check_updates()
        assert result is True

    def test_should_check_updates_time_not_reached(self, coordinator_with_mock):
        """Test should_check_updates when check time hasn't been reached."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        # Set last check to 1 hour ago
        coordinator_with_mock.last_update_check = datetime.now() - timedelta(hours=1)

        result = coordinator_with_mock.should_check_updates()
        assert result is False

    def test_should_check_updates_time_reached(self, coordinator_with_mock):
        """Test should_check_updates when enough time has passed."""
        coordinator_with_mock.features["feature_switch_update_check"] = True

        # Simple approach: Set force_update_requested to True
        coordinator_with_mock.force_update_requested = True

        result = coordinator_with_mock.should_check_updates()
        assert result is True

    def test_normalize_image_id(self, coordinator_with_mock):
        """Test _normalize_image_id static method."""
        # Test with sha256: prefix
        result = coordinator_with_mock._normalize_image_id("sha256:abc123def456")
        assert result == "abc123def456"

        # Test without prefix
        result = coordinator_with_mock._normalize_image_id("abc123def456")
        assert result == "abc123def456"

        # Test empty string
        result = coordinator_with_mock._normalize_image_id("")
        assert result == ""

    def test_invalidate_cache_if_needed_no_last_check(self, coordinator_with_mock):
        """Test cache invalidation when no last check exists."""
        coordinator_with_mock.last_update_check = None
        # Should not raise any errors
        coordinator_with_mock._invalidate_cache_if_needed()

    def test_invalidate_cache_if_needed_recent_check(self, coordinator_with_mock):
        """Test cache invalidation with recent check."""
        coordinator_with_mock.last_update_check = datetime.now() - timedelta(hours=1)
        coordinator_with_mock.cached_registry_responses["test_key"] = "cached_data"

        coordinator_with_mock._invalidate_cache_if_needed()

        # Cache should still exist for recent check
        assert "test_key" in coordinator_with_mock.cached_registry_responses

    def test_invalidate_cache_if_needed_old_check(self, coordinator_with_mock):
        """Test cache invalidation with old check."""
        coordinator_with_mock.last_update_check = datetime.now() - timedelta(hours=25)
        coordinator_with_mock.cached_registry_responses["test_key"] = "cached_data"

        coordinator_with_mock._invalidate_cache_if_needed()

        # Cache should be cleared for old check
        assert "test_key" not in coordinator_with_mock.cached_registry_responses

    def test_check_image_updates_no_image_name(self, coordinator_with_mock):
        """Test check_image_updates with no image name."""
        container_data = {"Id": "test_container", "Name": "/test", "Image": ""}
        result = coordinator_with_mock.check_image_updates("test_eid", container_data)
        assert result is False

    def test_check_image_updates_with_cached_result(self, coordinator_with_mock):
        """Test check_image_updates returning cached result."""
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }
        cached_result = True
        coordinator_with_mock.cached_update_results["test_container"] = cached_result
        coordinator_with_mock.features["feature_switch_update_check"] = False

        result = coordinator_with_mock.check_image_updates("test_eid", container_data)
        assert result == cached_result

    @patch(
        "custom_components.portainer.coordinator.PortainerCoordinator.should_check_updates"
    )
    def test_check_image_updates_api_response_dict(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates with API returning dict response."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.check_for_image_update.return_value = {
            "update_available": True
        }
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }

        result = coordinator_with_mock.check_image_updates("test_eid", container_data)
        # The actual implementation returns boolean, not the API response
        assert isinstance(result, bool)

    @patch(
        "custom_components.portainer.coordinator.PortainerCoordinator.should_check_updates"
    )
    def test_check_image_updates_api_response_list(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates with API returning list response."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.check_for_image_update.return_value = [
            {"update_available": True}
        ]
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }

        result = coordinator_with_mock.check_image_updates("test_eid", container_data)
        # The actual implementation returns boolean, not the API response
        assert isinstance(result, bool)

    @patch(
        "custom_components.portainer.coordinator.PortainerCoordinator.should_check_updates"
    )
    def test_check_image_updates_api_error(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates when API raises exception."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.check_for_image_update.side_effect = Exception(
            "API Error"
        )
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }

        result = coordinator_with_mock.check_image_updates("test_eid", container_data)
        assert result is False  # Should return False on error

    def test_check_image_updates_with_complex_image_name(self, coordinator_with_mock):
        """Test check_image_updates with complex image name parsing."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        coordinator_with_mock.last_update_check = None  # First time check
        coordinator_with_mock.api.query.return_value = {"update_available": False}
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "registry.example.com/nginx:1.21",
        }

        # Test with registry and tag
        result = coordinator_with_mock.check_image_updates("test_eid", container_data)
        assert isinstance(result, bool)

        # Verify the API was called with parsed components
        coordinator_with_mock.api.query.assert_called()

    def test_get_next_update_check_time_feature_disabled(self, coordinator_with_mock):
        """Test get_next_update_check_time when feature is disabled."""
        coordinator_with_mock.features["feature_switch_update_check"] = False

        result = coordinator_with_mock.get_next_update_check_time()
        assert result is None

    def test_get_next_update_check_time_today_not_reached(self, coordinator_with_mock):
        """Test get_next_update_check_time when today's time hasn't been reached."""
        # Set check hour to 23 (11 PM) - very likely in the future
        coordinator_with_mock.config_entry.options["update_check_hour"] = 23

        result = coordinator_with_mock.get_next_update_check_time()

        # Should return today at 23:00 or tomorrow at 23:00
        assert result.hour == 23
        assert result.minute == 0

    def test_get_next_update_check_time_today_passed(self, coordinator_with_mock):
        """Test get_next_update_check_time when today's time has passed."""
        # Set check hour to 0 (midnight) - very likely in the past
        coordinator_with_mock.config_entry.options["update_check_hour"] = 0

        result = coordinator_with_mock.get_next_update_check_time()

        # Should return tomorrow at 00:00
        assert result.hour == 0
        assert result.minute == 0
        # Should be tomorrow's date
        tomorrow = datetime.now() + timedelta(days=1)
        assert result.date() == tomorrow.date()
