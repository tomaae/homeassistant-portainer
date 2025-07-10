import os
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests

DOCKER_IO = "docker.io"
DOCKER_IO_REGISTRY = "registry-1.docker.io"
GHCR_IO = "ghcr.io"


class DockerRegistryError(Exception):
    """
    Custom exception for DockerRegistry errors.
    Raised for non-HTTP errors in DockerRegistry operations.
    """

    pass


class BaseRegistry(ABC):

    @staticmethod
    def parse_image_name(image_name: str) -> dict:
        """Parse a Docker image name into a dict with registry, image_repo, image_tag, image_key."""
        if not image_name:
            return {
                "registry": DOCKER_IO,
                "image_repo": "unknown",
                "image_tag": "latest",
                "image_key": f"{DOCKER_IO}/unknown:latest",
            }

        # Remove digest if present
        if "@" in image_name:
            image_name = image_name.split("@", 1)[0]
        tag = "latest"

        repo, tag = BaseRegistry._split_repo_and_tag(image_name, tag)
        registry, repo = BaseRegistry._detect_registry(repo)

        repo = BaseRegistry._prepend_library_if_needed(registry, repo)

        image_key = f"{registry}/{repo}:{tag}" if registry else f"{repo}:{tag}"

        return {
            "registry": registry,
            "image_repo": repo,
            "image_tag": tag,
            "image_key": image_key,
        }

    @staticmethod
    def _split_repo_and_tag(image_name: str, default_tag: str):
        if ":" in image_name:
            parts = image_name.rsplit(":", 1)
            if "/" in parts[1]:
                # e.g. localhost:5000/nginx
                return image_name, default_tag
            else:
                return parts[0], parts[1]
        else:
            return image_name, default_tag

    @staticmethod
    def _detect_registry(repo: str):
        if "/" in repo:
            first = repo.split("/")[0]
            if "." in first or ":" in first:
                registry = first
                repo = "/".join(repo.split("/")[1:])
                return registry, repo
        return DOCKER_IO, repo

    @staticmethod
    def _prepend_library_if_needed(registry, repo):
        dockerio_registries = (
            None,
            DOCKER_IO,
            DOCKER_IO_REGISTRY,
            f"{DOCKER_IO}:443",
            f"{DOCKER_IO_REGISTRY}:443",
        )
        if registry in dockerio_registries and "/" not in repo:
            return f"library/{repo}"
        return repo

    """
    Abstract base class for Docker registries.
    """

    def __init__(self, image_repo: str, registry: str):
        self.image_repo = image_repo
        self.registry = registry
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    @abstractmethod
    def _get_token(self) -> Optional[str]:
        pass

    @abstractmethod
    def _get_manifest_url(self, tag_or_digest: str) -> str:
        pass

    def _get_valid_token(self) -> Optional[str]:
        if self._token is None or time.time() > self._token_expiry:
            return self._get_token()
        return self._token

    def get_manifest(
        self, tag: str, arch: Optional[str] = None, os: Optional[str] = None
    ) -> dict:
        token = self._get_valid_token()
        url = self._get_manifest_url(tag)
        headers = {
            "Accept": (
                "application/vnd.oci.image.index.v1+json,"
                "application/vnd.oci.image.manifest.v1+json,"
                "application/vnd.docker.distribution.manifest.list.v2+json,"
                "application/vnd.docker.distribution.manifest.v2+json"
            )
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise requests.HTTPError(
                f"Failed to fetch manifest: {resp.status_code}", response=resp
            )
        manifest = resp.json()
        if (
            arch
            and os
            and manifest.get("mediaType", "")
            in (
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.index.v1+json",
            )
            and "manifests" in manifest
        ):
            return self._get_platform_manifest(arch, os, manifest, token)
        return manifest

    def _get_platform_manifest(
        self, arch: str, os: str, manifest_list: dict, token: Optional[str] = None
    ) -> dict:
        if not token:
            token = self._get_valid_token()
        for entry in manifest_list.get("manifests", []):
            platform = entry.get("platform", {})
            if platform.get("architecture") == arch and platform.get("os") == os:
                digest = entry.get("digest")
                if not digest:
                    continue
                sub_url = self._get_manifest_url(digest)
                headers = {
                    "Accept": (
                        "application/vnd.oci.image.manifest.v1+json,"
                        "application/vnd.docker.distribution.manifest.v2+json"
                    )
                }
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                resp = requests.get(sub_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    return resp.json()
                else:
                    raise requests.HTTPError(
                        f"Failed to fetch platform manifest: {resp.status_code}",
                        response=resp,
                    )
        raise ValueError(f"No matching platform manifest found for arch={arch} os={os}")

    @staticmethod
    def for_registry(image_repo: str, registry: str) -> "BaseRegistry":
        # Treat empty or None registry as Docker Hub
        if not registry:
            registry = DOCKER_IO
        if registry in (DOCKER_IO, DOCKER_IO_REGISTRY):
            return DockerIORegistry(image_repo, registry)
        elif registry == GHCR_IO:
            return GHCRRegistry(image_repo, registry)
        else:
            return GenericRegistry(image_repo, registry)


class DockerIORegistry(BaseRegistry):
    def _get_token(self) -> Optional[str]:
        token_url = f"https://auth.{DOCKER_IO}/token?service=registry.{DOCKER_IO}&scope=repository:{self.image_repo}:pull"
        resp = requests.get(token_url, timeout=10)
        if resp.status_code != 200:
            raise requests.HTTPError(
                f"Failed to get Docker registry token: {resp.status_code}"
            )
        data = resp.json()
        self._token = data.get("token")
        expires_in = data.get("expires_in", 3600)
        self._token_expiry = time.time() + expires_in - 30
        return self._token

    def _get_manifest_url(self, tag_or_digest: str) -> str:
        return f"https://{DOCKER_IO_REGISTRY}/v2/{self.image_repo}/manifests/{tag_or_digest}"


class GHCRRegistry(BaseRegistry):
    def __init__(self, image_repo: str, registry: str, token: Optional[str] = None):
        super().__init__(image_repo, registry)
        self._token = token or os.environ.get("GHCR_TOKEN")
        self._token_expiry = float("inf") if self._token else 0.0

    def _get_token(self) -> Optional[str]:
        # Use provided token (PAT or env), or try anonymous token if not set
        if self._token:
            return self._token
        # Try to get anonymous token (public image)
        token_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{self.image_repo}:pull"
        resp = requests.get(token_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            self._token = data.get("token")
            expires_in = data.get("expires_in", 3600)
            self._token_expiry = time.time() + expires_in - 30
            return self._token
        # If anonymous token fails, return None (will cause 401 on manifest fetch)
        return None

    def _get_manifest_url(self, tag_or_digest: str) -> str:
        return f"https://{GHCR_IO}/v2/{self.image_repo}/manifests/{tag_or_digest}"


class GenericRegistry(BaseRegistry):
    def _get_token(self) -> Optional[str]:
        # No token logic for generic registries (extend as needed)
        return None

    def _get_manifest_url(self, tag_or_digest: str) -> str:
        if self.registry.startswith("localhost") or re.match(
            r"^\d+\.\d+\.\d+\.\d+", self.registry
        ):
            return (
                f"http://{self.registry}/v2/{self.image_repo}/manifests/{tag_or_digest}"
            )
        else:
            return f"https://{self.registry}/v2/{self.image_repo}/manifests/{tag_or_digest}"
