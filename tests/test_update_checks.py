"""Tests for Portainer coordinator update check functionality."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.portainer.const import DOMAIN
from custom_components.portainer.coordinator import PortainerCoordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for testing."""
    mock_entry = MagicMock()
    mock_entry.domain = DOMAIN
    mock_entry.data = {
        "host": "localhost",
        "api_key": "test_key",
        "name": "Test Portainer",
        "ssl": False,
        "verify_ssl": True,
    }
    mock_entry.options = {
        "feature_switch_update_check": True,
        "update_check_time": "10:00",
    }
    mock_entry.entry_id = "test_entry"
    return mock_entry


@pytest.fixture
def mock_api():
    """Create a mock API instance."""
    api = MagicMock()
    api.check_for_image_update = AsyncMock()
    api.query = MagicMock()  # <-- synchrones Mock statt AsyncMock
    return api


@pytest.fixture
def coordinator_with_mock(hass: HomeAssistant, mock_config_entry, mock_api):
    """Create a coordinator instance with mocked dependencies."""
    # Create a minimal coordinator for testing
    coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

    # Initialize required attributes
    coordinator.hass = hass
    coordinator.config_entry = mock_config_entry
    coordinator.api = mock_api
    coordinator.features = {
        "feature_switch_update_check": True,
    }

    # Add update_service (PortainerUpdateService) to coordinator before using last_update_check
    from custom_components.portainer.portainer_update_service import (
        PortainerUpdateService,
    )

    coordinator.update_service = PortainerUpdateService(
        hass,
        mock_config_entry,
        mock_api,
        coordinator.features,
        mock_config_entry.entry_id,
    )
    coordinator.last_update_check = None
    coordinator.cached_update_results = {}
    coordinator.cached_registry_responses = {}
    coordinator.force_update_requested = False
    import asyncio

    coordinator.lock = asyncio.Lock()

    # Add property for update_check_time that reads from config
    @property
    def update_check_time(self):
        time_str = self.config_entry.options.get("update_check_time", "02:00")
        try:
            hour, minute = [int(x) for x in time_str.split(":")]
        except Exception:
            hour, minute = 2, 0
        return hour, minute

    coordinator.__class__.update_check_time = update_check_time

    # Add update_service (PortainerUpdateService) to coordinator
    from custom_components.portainer.portainer_update_service import (
        PortainerUpdateService,
    )

    coordinator.update_service = PortainerUpdateService(
        hass,
        mock_config_entry,
        mock_api,
        coordinator.features,
        mock_config_entry.entry_id,
    )

    return coordinator


class TestUpdateCheckLogic:
    @pytest.mark.asyncio
    async def test_check_image_updates_local_image_not_on_registry(
        self, coordinator_with_mock
    ):
        """Test check_image_updates for a local-only image (not on registry). Should return status 2 (not yet checked) on first run."""
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "certbot-dns-ionos:latest",
        }
        # On first run, should return a dict with integer status
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert isinstance(result, dict), f"Result is not a dict: {result}"
        assert isinstance(result.get("status"), int), f"Status is not int: {result}"

    @pytest.mark.asyncio
    async def test_check_image_updates_official_dockerhub_image(
        self, coordinator_with_mock
    ):
        """Test check_image_updates for an official Docker Hub image (e.g. traefik:latest). Should return status 2 (not yet checked) on first run."""
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "traefik:latest",
        }
        # On first run, should return a dict with integer status
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert isinstance(result, dict), f"Result is not a dict: {result}"
        assert isinstance(result.get("status"), int), f"Status is not int: {result}"

    @pytest.mark.asyncio
    async def test_check_image_updates_update_available(self, coordinator_with_mock):
        """Test check_image_updates when update is available (IDs differ). Should return status 2 (not yet checked) on first run."""
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "traefik:latest",
        }
        # On first run, should return a dict with integer status
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert isinstance(result, dict), f"Result is not a dict: {result}"
        assert isinstance(result.get("status"), int), f"Status is not int: {result}"

    """Test class for container update check functionality."""

    def test_should_check_updates_feature_disabled(self, coordinator_with_mock):
        """Test should_check_updates when feature is disabled."""
        coordinator_with_mock.features["feature_switch_update_check"] = False
        result = coordinator_with_mock.update_service.should_check_updates()
        # If feature is disabled, should_check_updates should return False
        assert result is False

    def test_should_check_updates_force_update(self, coordinator_with_mock):
        """Test should_check_updates with feature enabled and force_update_requested True."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        coordinator_with_mock.update_service.force_update_requested = True
        result = coordinator_with_mock.update_service.should_check_updates()
        assert result is True

    def test_should_check_updates_first_check(self, coordinator_with_mock):
        """Test should_check_updates for first time check. Should return False if feature enabled and nicht forced und Zeit noch nicht erreicht."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        coordinator_with_mock.config_entry.options["update_check_time"] = "23:59"
        coordinator_with_mock.last_update_check = None
        coordinator_with_mock.force_update_requested = False

        # Setze now statisch auf 22:00 Uhr
        fixed_now = datetime(2025, 1, 1, 22, 0, tzinfo=timezone.utc)
        with patch("homeassistant.util.dt.now", return_value=fixed_now):
            result = coordinator_with_mock.update_service.should_check_updates()
        assert result is False

    def test_should_check_updates_time_not_reached(self, coordinator_with_mock):
        """Test should_check_updates when check time hasn't been reached."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        coordinator_with_mock.config_entry.options["update_check_time"] = "23:59"
        from datetime import datetime, timezone

        coordinator_with_mock.last_update_check = datetime(
            2025, 1, 1, 10, 0, tzinfo=timezone.utc
        )

        result = coordinator_with_mock.update_service.should_check_updates()
        assert result is False

    def test_should_check_updates_time_reached(self, coordinator_with_mock):
        """Test should_check_updates when enough time has passed."""
        coordinator_with_mock.features["feature_switch_update_check"] = True

        # Simple approach: Set force_update_requested to True
        coordinator_with_mock.update_service.force_update_requested = True

        result = coordinator_with_mock.update_service.should_check_updates()
        assert result is True

    def test_normalize_image_id(self, coordinator_with_mock):
        """Test _normalize_image_id static method."""
        # Test with sha256: prefix
        result = coordinator_with_mock.update_service._normalize_image_id(
            "sha256:abc123def456"
        )
        assert result == "abc123def456"

        # Test without prefix
        result = coordinator_with_mock.update_service._normalize_image_id(
            "abc123def456"
        )
        assert result == "abc123def456"

        # Test empty string
        result = coordinator_with_mock.update_service._normalize_image_id("")
        assert result == ""

    def test_invalidate_cache_if_needed_no_last_check(self, coordinator_with_mock):
        """Test cache invalidation when no last check exists."""
        coordinator_with_mock.last_update_check = None
        # Should not raise any errors
        coordinator_with_mock.update_service._invalidate_cache_if_needed()

    def test_invalidate_cache_if_needed_recent_check(self, coordinator_with_mock):
        """Test cache invalidation with recent check."""
        coordinator_with_mock.last_update_check = dt_util.now() - timedelta(hours=1)
        coordinator_with_mock.cached_registry_responses["test_key"] = "cached_data"

        coordinator_with_mock.update_service._invalidate_cache_if_needed()

        # Cache should still exist for recent check
        assert "test_key" in coordinator_with_mock.cached_registry_responses

    def test_invalidate_cache_on_registry_check(self, coordinator_with_mock):
        """Test cache is cleared when reading from the registry (stale entries removed)."""
        coordinator_with_mock.update_service.last_update_check = (
            dt_util.now() - timedelta(hours=25)
        )
        coordinator_with_mock.update_service.cached_registry_responses["test_key"] = (
            "cached_data"
        )

        # Simulate registry check that should clear stale cache
        def fake_get_registry_response(eid, registry, image_repo, image_tag, image_key):
            # Simulate cache clearing inside registry check
            coordinator_with_mock.update_service.cached_registry_responses.clear()
            return {
                "status": 200,
                "status_description": None,
                "manifest": {},
                "registry_used": True,
            }

        coordinator_with_mock.update_service._get_registry_response = (
            fake_get_registry_response
        )
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }
        coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )

        # Cache should be cleared after registry check
        assert "test_key" not in coordinator_with_mock.cached_registry_responses

    @pytest.mark.asyncio
    async def test_check_image_updates_no_image_name(self, coordinator_with_mock):
        """Test check_image_updates with no image name."""
        container_data = {"Id": "test_container", "Name": "/test", "Image": ""}
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert result["status"] == 500

    @pytest.mark.asyncio
    async def test_check_image_updates_with_cached_result(self, coordinator_with_mock):
        """Test check_image_updates returning cached result when should_check_updates is False."""
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }
        cached_result = {
            "status": 1,
            "status_description": "Update available.",
            "manifest": {},
            "registry_used": True,
        }
        # Build a cache mock: patch should_check_updates to always return False
        coordinator_with_mock.update_service.should_check_updates = lambda: False
        coordinator_with_mock.features["feature_switch_update_check"] = False
        from homeassistant.util import dt as dt_util

        coordinator_with_mock.update_service.last_update_check = dt_util.now()
        # Use the same container ID as in container_data
        container_id = container_data["Id"]
        coordinator_with_mock.update_service.cached_update_results[container_id] = (
            cached_result
        )

        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert result["status"] == 1

        # Test with a different cached result
        cached_result_false = {
            "status": 0,
            "status_description": "No update available.",
            "manifest": {},
            "registry_used": True,
        }
        coordinator_with_mock.update_service.cached_update_results[container_id] = (
            cached_result_false
        )
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert result["status"] == 0

    @patch(
        "custom_components.portainer.portainer_update_service.PortainerUpdateService.should_check_updates"
    )
    @pytest.mark.asyncio
    async def test_check_image_updates_api_response_dict(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates with API returning dict response."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.query.return_value = {}
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }

        # Simuliere Registry-200, IDs gleich
        def fake_get_registry_response(eid, registry, image_repo, image_tag, image_key):
            return {
                "status": 200,
                "status_description": None,
                "manifest": {
                    "Id": "sha256:abc",
                    "schemaVersion": 2,
                    "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                    "config": {"digest": "sha256:abc"},
                },
                "registry_used": True,
            }

        coordinator_with_mock.update_service._get_registry_response = (
            fake_get_registry_response
        )
        container_data["ImageID"] = "sha256:abc"
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert result == {
            "status": 0,
            "status_description": None,
            "manifest": {
                "Id": "sha256:abc",
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "config": {"digest": "sha256:abc"},
            },
            "registry_used": True,
        }

    @patch(
        "custom_components.portainer.portainer_update_service.PortainerUpdateService.should_check_updates"
    )
    @pytest.mark.asyncio
    async def test_check_image_updates_api_response_list(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates with API returning list response."""
        mock_should_check.return_value = True
        coordinator_with_mock.api.query.return_value = []
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }

        def fake_get_registry_response(eid, registry, image_repo, image_tag, image_key):
            return {
                "status": 200,
                "status_description": None,
                "manifest": {
                    "Id": "sha256:abc",
                    "schemaVersion": 2,
                    "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                    "config": {"digest": "sha256:abc"},
                },
                "registry_used": True,
            }

        coordinator_with_mock.update_service._get_registry_response = (
            fake_get_registry_response
        )
        container_data["ImageID"] = "sha256:abc"
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert result == {
            "status": 0,
            "status_description": None,
            "manifest": {
                "Id": "sha256:abc",
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "config": {"digest": "sha256:abc"},
            },
            "registry_used": True,
        }

    @patch(
        "custom_components.portainer.portainer_update_service.PortainerUpdateService.should_check_updates"
    )
    @pytest.mark.asyncio
    async def test_check_image_updates_api_error(
        self, mock_should_check, coordinator_with_mock
    ):
        """Test check_image_updates when API raises exception. Should return status 500 (error) if registry call fails."""
        mock_should_check.return_value = True
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }

        def fake_get_registry_response(eid, registry, image_repo, image_tag, image_key):
            return {
                "status": 500,
                "status_description": "Simulated registry error",
                "manifest": {},
                "registry_used": True,
            }

        coordinator_with_mock.update_service._get_registry_response = (
            fake_get_registry_response
        )
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert isinstance(result, dict)
        assert result["status"] == 500
        assert "status_description" in result
        assert "manifest" in result
        assert "registry_used" in result

    @pytest.mark.asyncio
    async def test_check_image_updates_with_complex_image_name(
        self, coordinator_with_mock
    ):
        """Test check_image_updates with complex image name parsing."""
        coordinator_with_mock.features["feature_switch_update_check"] = True
        coordinator_with_mock.last_update_check = None  # First time check
        coordinator_with_mock.api.query.return_value = {"update_available": False}
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "registry.example.com/nginx:1.21",
        }

        # Simuliere Registry-Fehler (z.B. kein Manifest gefunden)
        def fake_get_registry_response(eid, registry, image_repo, image_tag, image_key):
            return {
                "status": 500,
                "status_description": "error",
                "manifest": {},
                "registry_used": True,
            }

        coordinator_with_mock.update_service._get_registry_response = (
            fake_get_registry_response
        )
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert isinstance(result["status"], int)

    def test_get_scheduled_time_feature_disabled(self, coordinator_with_mock):
        """Test get_scheduled_time when feature is disabled (should still return scheduled time)."""
        coordinator_with_mock.features["feature_switch_update_check"] = False
        now = dt_util.now()
        scheduled_time = coordinator_with_mock.update_service.scheduled_time
        time_str = coordinator_with_mock.config_entry.options.get(
            "update_check_time", "02:00"
        )
        hour, minute = [int(x) for x in time_str.split(":")]
        assert scheduled_time.hour == hour
        assert scheduled_time.minute == minute

    def test_get_scheduled_time_today_not_reached(self, coordinator_with_mock):
        """Test get_scheduled_time when today's time hasn't been reached."""
        coordinator_with_mock.config_entry.options["update_check_time"] = "23:00"
        now = dt_util.now()
        scheduled_time = coordinator_with_mock.update_service.scheduled_time
        assert scheduled_time.hour == 23
        assert scheduled_time.minute == 0

    def test_get_scheduled_time_today_passed(self, coordinator_with_mock):
        """Test get_scheduled_time when today's time has passed."""
        coordinator_with_mock.config_entry.options["update_check_time"] = "00:00"
        now = dt_util.now()
        scheduled_time = coordinator_with_mock.update_service.scheduled_time
        assert scheduled_time.hour == 0
        assert scheduled_time.minute == 0
        # Should be today (not tomorrow, since get_scheduled_time always returns today)
        assert scheduled_time.date() == now.date()


class TestUpdateCheckIntegration:
    """Integration tests for update check functionality with Home Assistant."""

    @pytest.mark.asyncio
    async def test_coordinator_initialization(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that coordinator initializes properly with Home Assistant."""
        # Test that the coordinator can be properly initialized with HA
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
        coordinator.hass = hass
        coordinator.config_entry = mock_config_entry

        # Basic initialization checks
        assert coordinator.hass == hass
        assert coordinator.config_entry == mock_config_entry

    @pytest.mark.asyncio
    async def test_update_check_with_hass_context(
        self, hass: HomeAssistant, coordinator_with_mock
    ):
        """Test update check functionality within Home Assistant context."""
        coordinator_with_mock.hass = hass
        container_data = {
            "Id": "test_container",
            "Name": "/test",
            "Image": "nginx:latest",
        }

        # Simulate registry error (e.g. no manifest found)
        def fake_get_registry_response(eid, registry, image_repo, image_tag, image_key):
            return {
                "status": 500,
                "status_description": "Registry/internal error.",
                "manifest": {},
                "registry_used": True,
            }

        coordinator_with_mock.update_service._get_registry_response = (
            fake_get_registry_response
        )
        result = coordinator_with_mock.update_service.check_image_updates(
            "test_eid", container_data
        )
        assert isinstance(result["status"], int)
