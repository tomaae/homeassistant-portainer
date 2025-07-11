from custom_components.portainer.coordinator import PortainerCoordinator
from custom_components.portainer.docker_registry import BaseRegistry


class DummyHass:
    translations = {
        "component.portainer.entity.sensor.update_check_status.state": {
            "update_status_2": "Update status not yet checked."
        }
    }


def test_check_image_updates_new_container_status_code():
    """Test that a new container not in cache returns status code 2 and logs info."""
    hass = DummyHass()

    class MockEntry:
        def __init__(self):
            self.data = {
                "host": "localhost",
                "api_key": "test_key",
                "name": "Test Portainer",
                "ssl": False,
                "verify_ssl": True,
            }
            self.options = {
                "feature_switch_update_check": True
                # Do not include update_check_hour, let coordinator use default
            }
            self.entry_id = "test_entry"

        def async_on_unload(self, x):
            # This is a stub for the async_on_unload method, which is not needed for this test.
            pass

    config_entry = MockEntry()
    coordinator = PortainerCoordinator(hass, config_entry)
    coordinator.features["feature_switch_update_check"] = (
        False  # disables registry check, forces cache path
    )
    # Patch: ensure required attributes are set for test
    coordinator.last_update_check = None
    coordinator.cached_registry_responses = {}
    coordinator.cached_update_results = {}
    container_data = {
        "Id": "new_container",
        "Name": "/new_container",
        "Image": "nginx:latest",
    }
    # No cache entry for this container
    result = coordinator.check_image_updates("eid", container_data)
    assert result["status"] == 2
    # Description should match new status code
    desc = coordinator._get_update_description(2)
    assert "not yet checked" in desc.lower()


def test_parse_image_name_staticmethod():
    # Test the static method on BaseRegistry (dict return)
    result = BaseRegistry.parse_image_name("nginx")
    assert result["registry"] == "docker.io"
    assert result["image_repo"] == "library/nginx"
    assert result["image_tag"] == "latest"

    result = BaseRegistry.parse_image_name("nginx:1.21")
    assert result["registry"] == "docker.io"
    assert result["image_repo"] == "library/nginx"
    assert result["image_tag"] == "1.21"

    result = BaseRegistry.parse_image_name("registry.com/nginx:latest")
    assert result["registry"] == "registry.com"
    assert result["image_repo"] == "nginx"
    assert result["image_tag"] == "latest"

    result = BaseRegistry.parse_image_name("ghcr.io/home-assistant/home-assistant:dev")
    assert result["registry"] == "ghcr.io"
    assert result["image_repo"] == "home-assistant/home-assistant"
    assert result["image_tag"] == "dev"

    result = BaseRegistry.parse_image_name("nginx@sha256:abc123")
    assert result["registry"] == "docker.io"
    assert result["image_repo"] == "library/nginx"
    assert result["image_tag"] == "latest"

    result = BaseRegistry.parse_image_name("localhost:5000/nginx:latest")
    assert result["registry"] == "localhost:5000"
    assert result["image_repo"] == "nginx"
    assert result["image_tag"] == "latest"
