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
            # Simple cases
            ("nginx", None, "nginx", "latest"),
            ("nginx:latest", None, "nginx", "latest"),
            ("nginx:1.21", None, "nginx", "1.21"),
            ("nginx:1.21.3", None, "nginx", "1.21.3"),
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
            ("library/nginx:latest", None, "library/nginx", "latest"),
            ("grafana/loki:latest", None, "grafana/loki", "latest"),
            (
                "containrrr/watchtower:latest",
                None,
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
            ("nginx@sha256:abc123def456", None, "nginx", "latest"),
            ("nginx:latest@sha256:abc123def456", None, "nginx", "latest"),
            (
                "registry.com/nginx:1.21@sha256:abc123def456",
                "registry.com",
                "nginx",
                "1.21",
            ),
            # Edge cases
            ("", None, "unknown", "latest"),
            (
                "image-with-dashes:v1.0-beta",
                None,
                "image-with-dashes",
                "v1.0-beta",
            ),
            (
                "image_with_underscores:v1.0_stable",
                None,
                "image_with_underscores",
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
            ("myapp:2.1.0-rc.1", None, "myapp", "2.1.0-rc.1"),
            ("myapp:v2.1.0_alpha", None, "myapp", "v2.1.0_alpha"),
            ("myapp:snapshot-20231201", None, "myapp", "snapshot-20231201"),
        ],
    )
    def test_parse_image_name(
        self, coordinator, image_name, expected_registry, expected_repo, expected_tag
    ):
        """Test parsing various Docker image name formats."""
        registry, repo, tag = coordinator._parse_image_name(image_name)
        assert registry == expected_registry
        assert repo == expected_repo
        assert tag == expected_tag

    def test_parse_image_name_with_none_input(self, coordinator):
        """Test parsing with None input."""
        registry, repo, tag = coordinator._parse_image_name(None)
        assert registry is None
        assert repo == "unknown"
        assert tag == "latest"

    def test_parse_image_name_registry_port_edge_cases(self, coordinator):
        """Test edge cases for registry port parsing."""
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
            registry, repo, tag = coordinator._parse_image_name(image_name)
            assert registry == expected_registry, f"Failed for {image_name}"
            assert repo == expected_repo, f"Failed for {image_name}"
            assert tag == expected_tag, f"Failed for {image_name}"

    def test_parse_image_name_digest_removal(self, coordinator):
        """Test that SHA256 digests are properly removed from image names."""
        test_cases = [
            ("nginx@sha256:abc123", None, "nginx", "latest"),
            ("nginx:1.21@sha256:def456", None, "nginx", "1.21"),
            ("registry.com/app:v1.0@sha256:789xyz", "registry.com", "app", "v1.0"),
        ]

        for image_name, expected_registry, expected_repo, expected_tag in test_cases:
            registry, repo, tag = coordinator._parse_image_name(image_name)
            assert registry == expected_registry, f"Failed for {image_name}"
            assert repo == expected_repo, f"Failed for {image_name}"
            assert tag == expected_tag, f"Failed for {image_name}"

    def test_parse_image_name_numeric_tags(self, coordinator):
        """Test parsing of purely numeric tags."""
        test_cases = [
            ("nginx:123", None, "nginx", "123"),
            ("app:2023", None, "app", "2023"),
            ("service:20240101", None, "service", "20240101"),
        ]

        for image_name, expected_registry, expected_repo, expected_tag in test_cases:
            registry, repo, tag = coordinator._parse_image_name(image_name)
            assert registry == expected_registry, f"Failed for {image_name}"
            assert repo == expected_repo, f"Failed for {image_name}"
            assert tag == expected_tag, f"Failed for {image_name}"


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
