"""Tests for Portainer coordinator Docker image tag parsing functionality."""

import pytest

from custom_components.portainer.coordinator import PortainerCoordinator


@pytest.fixture
def coordinator():
    """Create a basic coordinator instance for testing static methods."""
    return PortainerCoordinator.__new__(PortainerCoordinator)


class TestDockerImageTagParsing:
    """Test class for Docker image name parsing functionality."""

    @pytest.mark.parametrize(
        ("image_name", "expected_registry", "expected_repo", "expected_tag"),
        [
            # Simple cases (Docker Hub official images should return 'library/<name>')
            ("nginx", "docker.io", "library/nginx", "latest"),
            ("nginx:latest", "docker.io", "library/nginx", "latest"),
            ("nginx:1.21", "docker.io", "library/nginx", "1.21"),
            ("nginx:1.21.3", "docker.io", "library/nginx", "1.21.3"),
            # Registry cases
            ("registry.example.com/nginx", "registry.example.com", "nginx", "latest"),
            (
                "registry.example.com/nginx:latest",
                "registry.example.com",
                "nginx",
                "latest",
            ),
            (
                "registry.example.com/nginx:1.21",
                "registry.example.com",
                "nginx",
                "1.21",
            ),
            # Registry with port
            ("localhost:5000/nginx", "localhost:5000", "nginx", "latest"),
            ("localhost:5000/nginx:latest", "localhost:5000", "nginx", "latest"),
            (
                "registry.example.com:443/nginx:latest",
                "registry.example.com:443",
                "nginx",
                "latest",
            ),
            ("127.0.0.1:5000/myapp:v1.0", "127.0.0.1:5000", "myapp", "v1.0"),
            # Namespace/organization
            ("library/nginx:latest", "docker.io", "library/nginx", "latest"),
            ("grafana/loki:latest", "docker.io", "grafana/loki", "latest"),
            (
                "containrrr/watchtower:latest",
                "docker.io",
                "containrrr/watchtower",
                "latest",
            ),
            # Multi-level namespaces
            (
                "registry.com/namespace/repo:tag",
                "registry.com",
                "namespace/repo",
                "tag",
            ),
            # Complex registry cases
            (
                "gcr.io/google-containers/pause:3.1",
                "gcr.io",
                "google-containers/pause",
                "3.1",
            ),
            # Digest cases (SHA256 should be removed)
            ("nginx@sha256:abc123def456", "docker.io", "library/nginx", "latest"),
            (
                "nginx:latest@sha256:abc123def456",
                "docker.io",
                "library/nginx",
                "latest",
            ),
            (
                "registry.com/nginx:1.21@sha256:abc123def456",
                "registry.com",
                "nginx",
                "1.21",
            ),
            # Edge cases
            ("", "docker.io", "unknown", "latest"),
            (
                "image-with-dashes:v1.0-beta",
                "docker.io",
                "library/image-with-dashes",
                "v1.0-beta",
            ),
            (
                "image_with_underscores:v1.0_stable",
                "docker.io",
                "library/image_with_underscores",
                "v1.0_stable",
            ),
            (
                "registry-with-dashes.com:443/app:latest",
                "registry-with-dashes.com:443",
                "app",
                "latest",
            ),
            # Complex registry:port combinations
            (
                "docker.io:443/library/nginx:1.21",
                "docker.io:443",
                "library/nginx",
                "1.21",
            ),
            (
                "quay.io:8080/prometheus/node-exporter:v1.3.1",
                "quay.io:8080",
                "prometheus/node-exporter",
                "v1.3.1",
            ),
            # Complex version tags
            ("myapp:2.1.0-rc.1", "docker.io", "library/myapp", "2.1.0-rc.1"),
            ("myapp:v2.1.0_alpha", "docker.io", "library/myapp", "v2.1.0_alpha"),
            (
                "myapp:snapshot-20231201",
                "docker.io",
                "library/myapp",
                "snapshot-20231201",
            ),
        ],
    )
    def test_parse_image_name(
        self, image_name, expected_registry, expected_repo, expected_tag
    ):
        """Test parsing various Docker image name formats."""
        from custom_components.portainer.docker_registry import BaseRegistry

        result = BaseRegistry.parse_image_name(image_name)
        assert result["registry"] == expected_registry
        assert result["image_repo"] == expected_repo
        assert result["image_tag"] == expected_tag

    def test_parse_image_name_with_none_input(self):
        """Test parsing with None input."""
        from custom_components.portainer.docker_registry import BaseRegistry

        result = BaseRegistry.parse_image_name(None)
        assert result["registry"] == "docker.io"
        assert result["image_repo"] == "unknown"
        assert result["image_tag"] == "latest"

    def test_parse_image_name_registry_port_edge_cases(self):
        """Test edge cases for registry port parsing."""
        from custom_components.portainer.docker_registry import BaseRegistry

        # Test various combinations of registries with ports
        test_cases = [
            ("localhost:5000/app", "localhost:5000", "app", "latest"),
            ("192.168.1.100:8080/service:v1", "192.168.1.100:8080", "service", "v1"),
            (
                "registry.local:443/namespace/app:latest",
                "registry.local:443",
                "namespace/app",
                "latest",
            ),
        ]

        for image_name, expected_registry, expected_repo, expected_tag in test_cases:
            result = BaseRegistry.parse_image_name(image_name)
            assert result["registry"] == expected_registry, f"Failed for {image_name}"
            assert result["image_repo"] == expected_repo, f"Failed for {image_name}"
            assert result["image_tag"] == expected_tag, f"Failed for {image_name}"

    def test_parse_image_name_digest_removal(self):
        """Test that SHA256 digests are properly removed from image names."""
        from custom_components.portainer.docker_registry import BaseRegistry

        test_cases = [
            ("nginx@sha256:abc123", "docker.io", "library/nginx", "latest"),
            ("nginx:1.21@sha256:def456", "docker.io", "library/nginx", "1.21"),
            ("registry.com/app:v1.0@sha256:789xyz", "registry.com", "app", "v1.0"),
        ]

        for image_name, expected_registry, expected_repo, expected_tag in test_cases:
            result = BaseRegistry.parse_image_name(image_name)
            assert result["registry"] == expected_registry, f"Failed for {image_name}"
            assert result["image_repo"] == expected_repo, f"Failed for {image_name}"
            assert result["image_tag"] == expected_tag, f"Failed for {image_name}"

    def test_parse_image_name_numeric_tags(self):
        """Test parsing of purely numeric tags."""
        from custom_components.portainer.docker_registry import BaseRegistry

        test_cases = [
            ("nginx:123", "docker.io", "library/nginx", "123"),
            ("app:2023", "docker.io", "library/app", "2023"),
            ("service:20240101", "docker.io", "library/service", "20240101"),
        ]

        for image_name, expected_registry, expected_repo, expected_tag in test_cases:
            result = BaseRegistry.parse_image_name(image_name)
            assert result["registry"] == expected_registry, f"Failed for {image_name}"
            assert result["image_repo"] == expected_repo, f"Failed for {image_name}"
            assert result["image_tag"] == expected_tag, f"Failed for {image_name}"

    @pytest.mark.parametrize(
        "image_name,expected_registry,expected_repo,expected_tag",
        [
            ("docker.io/nginx:latest", "docker.io", "library/nginx", "latest"),
            ("docker.io/library/nginx:latest", "docker.io", "library/nginx", "latest"),
            (
                "registry-1.docker.io/nginx:latest",
                "registry-1.docker.io",
                "library/nginx",
                "latest",
            ),
            ("docker.io:443/nginx:latest", "docker.io:443", "library/nginx", "latest"),
            (
                "docker.io:443/library/nginx:latest",
                "docker.io:443",
                "library/nginx",
                "latest",
            ),
        ],
    )
    def test_parse_image_name_dockerio_variants(
        self, image_name, expected_registry, expected_repo, expected_tag
    ):
        """Test parsing of docker.io and registry-1.docker.io variants."""
        from custom_components.portainer.docker_registry import BaseRegistry

        result = BaseRegistry.parse_image_name(image_name)
        assert result["registry"] == expected_registry
        assert result["image_repo"] == expected_repo
        assert result["image_tag"] == expected_tag


class TestImageIdNormalization:
    """Test class for Docker image ID normalization functionality."""

    def test_normalize_image_id_with_sha256_prefix(self, coordinator):
        """Test normalization of image IDs with sha256: prefix."""
        image_id = "sha256:abc123def456789"
        result = coordinator._normalize_image_id(image_id)
        assert result == "abc123def456789"

    def test_normalize_image_id_without_prefix(self, coordinator):
        """Test normalization of image IDs without prefix."""
        image_id = "abc123def456789"
        result = coordinator._normalize_image_id(image_id)
        assert result == "abc123def456789"

    def test_normalize_image_id_empty_string(self, coordinator):
        """Test normalization of empty string."""
        result = coordinator._normalize_image_id("")
        assert result == ""

    def test_normalize_image_id_short_id(self, coordinator):
        """Test normalization of short image IDs."""
        image_id = "sha256:abc123"
        result = coordinator._normalize_image_id(image_id)
        assert result == "abc123"

    def test_normalize_image_id_only_sha256_prefix(self, coordinator):
        """Test normalization when input is only the sha256 prefix."""
        result = coordinator._normalize_image_id("sha256:")
        assert result == ""
