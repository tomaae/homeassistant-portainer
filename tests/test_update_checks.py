"""Tests for Portainer coordinator update check functionality."""

from datetime import datetime, timedelta
from pathlib import Path
import sys
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
        coordinator.last_update_check = {}
        coordinator.update_check_cache = {}

        return coordinator

    def test_should_check_updates_feature_disabled(self, coordinator_with_mock):
        """Test should_check_updates when feature is disabled."""
        coordinator_with_mock.features["feature_switch_update_check"] = False

        result = coordinator_with_mock.should_check_updates("test_container")
        assert result is False

    def test_should_check_updates_force_update(self, coordinator_with_mock):
        """Test should_check_updates with force_update=True."""
        result = coordinator_with_mock.should_check_updates(
            "test_container", force_update=True
        )
        assert result is True

    def test_should_check_updates_first_check(self, coordinator_with_mock):
        """Test should_check_updates for first time check."""
        result = coordinator_with_mock.should_check_updates("new_container")
        assert result is True

    def test_should_check_updates_time_not_reached(self, coordinator_with_mock):
        """Test should_check_updates when check time hasn't been reached."""
        container_id = "test_container"
        # Set last check to 1 hour ago
        coordinator_with_mock.last_update_check[container_id] = (
            datetime.now() - timedelta(hours=1)
        )

        result = coordinator_with_mock.should_check_updates(container_id)
        assert result is False

    def test_should_check_updates_time_reached(self, coordinator_with_mock):
        """Test should_check_updates when enough time has passed."""
        container_id = "test_container"
        # Set last check to 25 hours ago (more than 24 hours)
        coordinator_with_mock.last_update_check[container_id] = (
            datetime.now() - timedelta(hours=25)
        )

        result = coordinator_with_mock.should_check_updates(container_id)
        assert result is True

    def test_normalize_image_id(self, coordinator_with_mock):
        """Test normalize_image_id method."""
        # Test with sha256: prefix
        result = coordinator_with_mock.normalize_image_id("sha256:abc123def456")
        assert result == "abc123def456"

        # Test without prefix
        result = coordinator_with_mock.normalize_image_id("abc123def456")
        assert result == "abc123def456"

        # Test empty string
        result = coordinator_with_mock.normalize_image_id("")
        assert result == ""

    def test_invalidate_cache_if_needed_no_last_check(self, coordinator_with_mock):
        """Test cache invalidation when no last check exists."""
        # Should not raise any errors
        coordinator_with_mock.invalidate_cache_if_needed("test_container")

    def test_invalidate_cache_if_needed_recent_check(self, coordinator_with_mock):
        """Test cache invalidation with recent check."""
        container_id = "test_container"
        coordinator_with_mock.last_update_check[container_id] = (
            datetime.now() - timedelta(hours=1)
        )
        coordinator_with_mock.update_check_cache[container_id] = "cached_data"

        coordinator_with_mock.invalidate_cache_if_needed(container_id)

        # Cache should still exist for recent check
        assert container_id in coordinator_with_mock.update_check_cache

    def test_invalidate_cache_if_needed_old_check(self, coordinator_with_mock):
        """Test cache invalidation with old check."""
        container_id = "test_container"
        coordinator_with_mock.last_update_check[container_id] = (
            datetime.now() - timedelta(hours=25)
        )
        coordinator_with_mock.update_check_cache[container_id] = "cached_data"

        coordinator_with_mock.invalidate_cache_if_needed(container_id)

        # Cache should be cleared for old check
        assert container_id not in coordinator_with_mock.update_check_cache

    def test_check_image_updates_no_image_name(self, coordinator_with_mock):
        """Test check_image_updates with no image name."""
        result = coordinator_with_mock.check_image_updates("container_1", None)
        assert result is None

    def test_check_image_updates_with_cached_result(self, coordinator_with_mock):
        """Test check_image_updates returning cached result."""
        container_id = "test_container"
        cached_result = {"update_available": True}
        coordinator_with_mock.update_check_cache[container_id] = cached_result

        result = coordinator_with_mock.check_image_updates(container_id, "nginx:latest")
        assert result == cached_result

    @patch("portainer.coordinator.PortainerCoordinator.should_check_updates")
    def test_check_image_updates_api_response_dict(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates with API returning dict response."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.check_for_image_update.return_value = {
            "update_available": True
        }

        result = coordinator_with_mock.check_image_updates(
            "test_container", "nginx:latest"
        )
        assert result == {"update_available": True}

    @patch("portainer.coordinator.PortainerCoordinator.should_check_updates")
    def test_check_image_updates_api_response_list(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates with API returning list response."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.check_for_image_update.return_value = [
            {"update_available": True}
        ]

        result = coordinator_with_mock.check_image_updates(
            "test_container", "nginx:latest"
        )
        assert result == {"update_available": True}

    @patch("portainer.coordinator.PortainerCoordinator.should_check_updates")
    def test_check_image_updates_api_error(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates when API raises exception."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.check_for_image_update.side_effect = Exception(
            "API Error"
        )

        result = coordinator_with_mock.check_image_updates(
            "test_container", "nginx:latest"
        )
        assert result is None

    @patch("portainer.coordinator.PortainerCoordinator.should_check_updates")
    def test_check_image_updates_with_complex_image_name(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates with complex image name parsing."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.check_for_image_update.return_value = {
            "update_available": False
        }

        # Test with registry and tag
        result = coordinator_with_mock.check_image_updates(
            "test_container", "registry.example.com/nginx:1.21"
        )
        assert result == {"update_available": False}

        # Verify the API was called with parsed components
        coordinator_with_mock.api.check_for_image_update.assert_called()

    def test_get_next_update_check_time_feature_disabled(self, coordinator_with_mock):
        """Test get_next_update_check_time when feature is disabled."""
        coordinator_with_mock.features["feature_switch_update_check"] = False

        result = coordinator_with_mock.get_next_update_check_time("test_container")
        assert result is None

    @patch("portainer.coordinator.datetime")
    def test_get_next_update_check_time_today_not_reached(
        self, mock_datetime, coordinator_with_mock
    ):
        """Test get_next_update_check_time when today's time hasn't been reached."""
        # Mock current time to 8 AM
        mock_now = datetime(2023, 1, 1, 8, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.combine.side_effect = datetime.combine

        # Set check hour to 10 AM
        coordinator_with_mock.config_entry.options["update_check_hour"] = 10

        result = coordinator_with_mock.get_next_update_check_time("test_container")

        # Should return today at 10 AM
        expected = datetime(2023, 1, 1, 10, 0, 0)
        assert result == expected

    @patch("portainer.coordinator.datetime")
    def test_get_next_update_check_time_today_passed(
        self, mock_datetime, coordinator_with_mock
    ):
        """Test get_next_update_check_time when today's time has passed."""
        # Mock current time to 2 PM
        mock_now = datetime(2023, 1, 1, 14, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.combine.side_effect = datetime.combine

        # Set check hour to 10 AM
        coordinator_with_mock.config_entry.options["update_check_hour"] = 10

        result = coordinator_with_mock.get_next_update_check_time("test_container")

        # Should return tomorrow at 10 AM
        expected = datetime(2023, 1, 2, 10, 0, 0)
        assert result == expected
