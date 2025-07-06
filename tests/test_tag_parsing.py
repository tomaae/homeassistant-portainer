"""Tests for Portainer coordinator Docker image tag parsing functionality."""

import sys
from pathlib import Path

import pytest

# Add custom_components to Python path for testing
# Adjust this path based on your repository structure
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

# Import the coordinator after adding to path
from portainer.coordinator import PortainerCoordinator  # noqa: E402


class TestDockerImageTagParsing:
    """Test class for Docker image name parsing functionality."""

    @pytest.mark.parametrize(
        ("image_name", "expected_repo", "expected_tag"),
        [
            # Simple cases
            ("nginx", "nginx", "latest"),
            ("nginx:latest", "nginx", "latest"),
            ("nginx:1.21", "nginx", "1.21"),
            ("nginx:1.21.3", "nginx", "1.21.3"),
            # Registry cases
            ("registry.example.com/nginx", "registry.example.com/nginx", "latest"),
            (
                "registry.example.com/nginx:latest",
                "registry.example.com/nginx",
                "latest",
            ),
            ("registry.example.com/nginx:1.21", "registry.example.com/nginx", "1.21"),
            # Registry with port
            ("localhost:5000/nginx", "localhost:5000/nginx", "latest"),
            ("localhost:5000/nginx:latest", "localhost:5000/nginx", "latest"),
            (
                "registry.example.com:443/nginx:latest",
                "registry.example.com:443/nginx",
                "latest",
            ),
            ("127.0.0.1:5000/myapp:v1.0", "127.0.0.1:5000/myapp", "v1.0"),
            # Namespace/organization
            ("library/nginx:latest", "library/nginx", "latest"),
            ("grafana/loki:latest", "grafana/loki", "latest"),
            ("containrrr/watchtower:latest", "containrrr/watchtower", "latest"),
            # Multi-level namespaces
            ("registry.com/namespace/repo:tag", "registry.com/namespace/repo", "tag"),
            (
                "gcr.io/google-containers/pause:3.1",
                "gcr.io/google-containers/pause",
                "3.1",
            ),
            # Digest cases (digest should be removed)
            ("nginx@sha256:abc123def456", "nginx", "latest"),
            ("nginx:latest@sha256:abc123def456", "nginx", "latest"),
            (
                "registry.com/nginx:1.21@sha256:abc123def456",
                "registry.com/nginx",
                "1.21",
            ),
            # Edge cases
            ("", "unknown", "latest"),
            ("image-with-dashes:v1.0-beta", "image-with-dashes", "v1.0-beta"),
            (
                "image_with_underscores:v1.0_stable",
                "image_with_underscores",
                "v1.0_stable",
            ),
            (
                "registry-with-dashes.com:443/app:latest",
                "registry-with-dashes.com:443/app",
                "latest",
            ),
            # Complex registry:port combinations
            ("docker.io:443/library/nginx:1.21", "docker.io:443/library/nginx", "1.21"),
            (
                "quay.io:8080/prometheus/node-exporter:v1.3.1",
                "quay.io:8080/prometheus/node-exporter",
                "v1.3.1",
            ),
            # Tags with special characters
            ("myapp:2.1.0-rc.1", "myapp", "2.1.0-rc.1"),
            ("myapp:v2.1.0_alpha", "myapp", "v2.1.0_alpha"),
            ("myapp:snapshot-20231201", "myapp", "snapshot-20231201"),
        ],
    )
    def test_parse_image_name(self, image_name, expected_repo, expected_tag):
        """Test image name parsing with various formats."""
        # Create a minimal coordinator instance for testing static methods
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        repo, tag = coordinator._parse_image_name(image_name)
        assert repo == expected_repo, (
            f"Expected repo '{expected_repo}', got '{repo}' for '{image_name}'"
        )
        assert tag == expected_tag, (
            f"Expected tag '{expected_tag}', got '{tag}' for '{image_name}'"
        )

    def test_parse_image_name_with_none_input(self):
        """Test that None input is handled gracefully."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        repo, tag = coordinator._parse_image_name(None)
        assert repo == "unknown"
        assert tag == "latest"

    def test_parse_image_name_registry_port_edge_cases(self):
        """Test edge cases with registry ports."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        # Test case where port could be confused with tag
        test_cases = [
            ("registry.com:5000", "registry.com:5000", "latest"),
            ("registry.com:443/app", "registry.com:443/app", "latest"),
            ("localhost:8080/myapp:v1.0", "localhost:8080/myapp", "v1.0"),
        ]

        for image_name, expected_repo, expected_tag in test_cases:
            repo, tag = coordinator._parse_image_name(image_name)
            assert repo == expected_repo, (
                f"Expected repo '{expected_repo}', got '{repo}' for '{image_name}'"
            )
            assert tag == expected_tag, (
                f"Expected tag '{expected_tag}', got '{tag}' for '{image_name}'"
            )

    def test_parse_image_name_digest_removal(self):
        """Test that SHA digests are properly removed."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        # Test various digest formats
        test_cases = [
            (
                "nginx@sha256:1234567890abcdef",
                "nginx",
                "latest",
            ),
            (
                "registry.com/app:v1.0@sha256:abcdef1234567890",
                "registry.com/app",
                "v1.0",
            ),
        ]

        for image_name, expected_repo, expected_tag in test_cases:
            repo, tag = coordinator._parse_image_name(image_name)
            assert repo == expected_repo
            assert tag == expected_tag

    def test_parse_image_name_numeric_tags(self):
        """Test handling of numeric tags vs ports."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        # These should be treated as tags, not ports
        test_cases = [
            ("myapp:123", "myapp", "123"),
            ("registry.com/myapp:456", "registry.com/myapp", "456"),
            ("localhost:5000/app:789", "localhost:5000/app", "789"),
        ]

        for image_name, expected_repo, expected_tag in test_cases:
            repo, tag = coordinator._parse_image_name(image_name)
            assert repo == expected_repo
            assert tag == expected_tag


class TestImageIdNormalization:
    """Test class for image ID normalization functionality."""

    def test_normalize_image_id_with_sha256_prefix(self):
        """Test normalization with sha256: prefix."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        image_id = "sha256:1234567890abcdef"
        normalized = coordinator.normalize_image_id(image_id)
        assert normalized == "1234567890abcdef"

    def test_normalize_image_id_without_prefix(self):
        """Test normalization without sha256: prefix."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        image_id = "1234567890abcdef"
        normalized = coordinator.normalize_image_id(image_id)
        assert normalized == "1234567890abcdef"

    def test_normalize_image_id_empty_string(self):
        """Test normalization with empty string."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        image_id = ""
        normalized = coordinator.normalize_image_id(image_id)
        assert normalized == ""

    def test_normalize_image_id_short_id(self):
        """Test normalization with short image ID."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        image_id = "sha256:abc123"
        normalized = coordinator.normalize_image_id(image_id)
        assert normalized == "abc123"

    def test_normalize_image_id_only_sha256_prefix(self):
        """Test normalization with only sha256: prefix."""
        coordinator = PortainerCoordinator.__new__(PortainerCoordinator)

        image_id = "sha256:"
        normalized = coordinator.normalize_image_id(image_id)
        assert normalized == ""
