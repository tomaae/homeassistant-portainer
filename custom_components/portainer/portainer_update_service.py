"""Portainer update-check and registry interaction service."""

import logging
from datetime import datetime, timedelta

import requests
from homeassistant.util import dt as dt_util

from .const import CONF_FEATURE_UPDATE_CHECK
from .docker_registry import BaseRegistry

_LOGGER = logging.getLogger(__name__)
TRANSLATION_UPDATE_CHECK_STATUS_STATE = (
    "component.portainer.entity.sensor.update_check_status.state"
)


class PortainerUpdateService:
    """Service to handle Portainer update checks and registry interactions."""

    REGISTRY_LITERAL = "{registry}"

    def __init__(self, hass, config_entry, api, features, config_entry_id):
        self.hass = hass
        self.config_entry = config_entry
        self.api = api
        self.features = features
        self.config_entry_id = config_entry_id
        self.cached_update_results = {}
        self.cached_registry_responses = {}
        self.last_update_check: datetime | None = None
        self.force_update_requested: bool = False  # Flag for force update

    @property
    def update_check_time(self):
        """Return the update check time (hour, minute) from config_entry options or default."""
        time_str = self.config_entry.options.get("update_check_time", "02:00")
        try:
            hour, minute = [int(x) for x in time_str.split(":")]
        except Exception:
            hour, minute = 2, 0  # fallback
        return hour, minute

    def check_image_updates(self, eid: str, container_data: dict) -> dict:
        """Check for updates for a given container image."""
        container_id = container_data.get("Id", "")
        container_name = container_data.get("Name", "").lstrip("/")
        image_name = container_data.get("Image", "")

        if not image_name:
            self._log_and_cache_no_image(container_id, container_name)
            translations = getattr(self.hass, "translations", {})
            status_description = self._get_update_description(500, None, translations)
            _LOGGER.error(
                "Container %s: No image name found, skipping update check (error)",
                container_name,
            )
            return {
                "status": 500,
                "status_description": status_description,
                "manifest": {},
                "registry_used": False,
            }

        image_info = BaseRegistry.parse_image_name(image_name)
        registry = image_info["registry"]
        image_repo = image_info["image_repo"]
        image_tag = image_info["image_tag"]
        image_key = image_info["image_key"]

        _LOGGER.debug(
            "Container %s: Parsed image '%s' -> registry='%s', repo='%s', tag='%s'",
            container_name,
            image_name,
            registry,
            image_repo,
            image_tag,
        )

        should_check = self.should_check_updates()
        self._invalidate_cache_if_needed()

        if should_check:
            result = self._get_registry_response(
                eid,
                registry,
                image_repo,
                image_tag,
                image_key,
            )

            if result["status"] != 200:
                self.cached_update_results[container_id] = result
                return result

            update_available = self._compare_image_ids(
                result["manifest"],
                container_data,
                container_name,
                image_name,
            )
            if update_available:
                result["status"] = 1
                translations = getattr(self.hass, "translations", {})
                result["status_description"] = self._get_update_description(
                    1, None, translations
                )
                self.cached_update_results[container_id] = result
            else:
                result["status"] = 0
            self.cached_update_results[container_id] = result
            return result
        else:
            if container_id in self.cached_update_results:
                return self.cached_update_results[container_id]
            else:
                _LOGGER.debug(
                    "Container %s: No cache entry for update check (new container or not yet checked)",
                    container_name,
                )
                translations = getattr(self.hass, "translations", {})
                status_description = self._get_update_description(2, None, translations)
                return {
                    "status": 2,
                    "status_description": status_description,
                    "manifest": {},
                    "registry_used": False,
                }

    def should_check_updates(self) -> bool:
        """Determine if an update check should be performed."""
        if not self.features[CONF_FEATURE_UPDATE_CHECK]:
            return False

        # If force update was requested, always return True
        if self.force_update_requested:
            return True

        now = dt_util.now()
        scheduled_time = self.get_next_update_check_time()

        # If now is before scheduled time today
        if now < scheduled_time:
            return False

        # Now is after or at scheduled time today
        if self.last_update_check is None:
            _LOGGER.debug("Scheduled update check time reached (first run)")
            return True
        # If last check was before today's scheduled time, trigger
        if self.last_update_check < scheduled_time:
            _LOGGER.debug(
                "Scheduled update check time reached (last check before today)"
            )
            return True
        # Already checked after scheduled time today
        return False

    def get_next_update_check_time(self) -> datetime | None:
        """Get the next scheduled update check time."""
        if not self.features[CONF_FEATURE_UPDATE_CHECK]:
            return None

        now = dt_util.now()
        hour, minute = self.update_check_time
        today_check = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if now < today_check:
            # Today's check hasn't happened yet
            return today_check

        # Next check is tomorrow
        return today_check + timedelta(days=1)

    def get_scheduled_time(self, now=None) -> datetime:
        """Return the scheduled update check time for today as a datetime object."""
        if now is None:
            now = dt_util.now()
        time_str = self.config_entry.options.get("update_check_time", "02:00")
        hour, minute = [int(x) for x in time_str.split(":")]
        scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return scheduled_time

    def _invalidate_cache_if_needed(self):
        """Invalidate cached registry responses if last update check is older than 24 hours."""
        if self.last_update_check is None:
            self.cached_registry_responses.clear()
            return
        now = dt_util.now()
        if (now - self.last_update_check).total_seconds() > 86400:
            self.cached_registry_responses.clear()

    def _get_registry_response(
        self,
        eid: str,
        registry: str,
        image_repo: str,
        image_tag: str,
        image_key: str,
    ) -> dict:
        """Fetch the registry response for a given image."""
        translations = getattr(self.hass, "translations", {})
        arch, os = self._get_arch_and_os(eid, image_key)
        try:
            from .docker_registry import BaseRegistry

            registry_client = BaseRegistry.for_registry(image_repo, registry)
            manifest = registry_client.get_manifest(image_tag, arch=arch, os=os)
            self._add_digest_to_manifest(manifest)
            self.cached_registry_responses[image_key] = manifest
            return {
                "status": 200,
                "status_description": self._get_update_description(
                    0, None, translations
                ),
                "manifest": manifest,
                "registry_used": True,
            }
        except Exception as e:
            return self._handle_registry_exception(
                e, registry, image_key, self._get_update_description, translations
            )

    def _handle_registry_exception(
        self,
        e: Exception,
        registry: str,
        image_key: str,
        get_status_description,
        translations=None,
    ) -> dict:
        """Handle exceptions from registry interactions."""
        if isinstance(e, requests.HTTPError):
            return self._handle_http_error(
                e, registry, image_key, get_status_description, translations
            )
        elif isinstance(e, ValueError):
            return self._handle_value_error(
                e, registry, image_key, get_status_description, translations
            )
        else:
            return self._handle_unexpected_error(
                e, image_key, get_status_description, translations
            )

    def _handle_http_error(
        self, e, registry, image_key, get_status_description, translations
    ):
        """Handle HTTP errors from registry interactions."""
        status_code = None
        if hasattr(e, "response") and e.response is not None:
            status_code = getattr(e.response, "status", None)
            if status_code is None:
                status_code = getattr(e.response, "status_code", None)
        if status_code == 401:
            _LOGGER.warning(
                "Unauthorized (HTTP 401) from registry '%s' for image '%s'. Check credentials.",
                registry,
                image_key,
            )
            return {
                "status": 401,
                "status_description": get_status_description(
                    401, registry, translations
                ),
                "manifest": {},
                "registry_used": True,
            }
        if status_code == 404:
            _LOGGER.info(
                "Image '%s' not found on registry '%s' (HTTP 404) – treating as not found on registry.",
                image_key,
                registry,
            )
            return {
                "status": 404,
                "status_description": get_status_description(
                    404, registry, translations
                ),
                "manifest": {},
                "registry_used": True,
            }
        if status_code == 429:
            _LOGGER.warning(
                "Rate limit (HTTP 429) from registry for image '%s'. Handling gracefully.",
                image_key,
            )
            return {
                "status": 429,
                "status_description": get_status_description(429, None, translations),
                "manifest": {},
                "registry_used": True,
            }
        _LOGGER.warning(
            "Failed to fetch registry data for image '%s': %s",
            image_key,
            str(e),
        )
        return {
            "status": status_code or 500,
            "status_description": get_status_description(
                status_code or 500, None, translations
            ),
            "manifest": {},
            "registry_used": True,
        }

    def _handle_value_error(
        self, e, registry, image_key, get_status_description, translations
    ):
        """Handle ValueError exceptions from registry interactions."""
        _LOGGER.warning(
            "No matching manifest found for image '%s' on registry '%s': %s",
            image_key,
            registry,
            str(e),
        )
        return {
            "status": 404,
            "status_description": get_status_description(404, registry, translations),
            "manifest": {},
            "registry_used": True,
        }

    def _handle_docker_registry_error(
        self, e, image_key, get_status_description, translations
    ):
        """Handle DockerRegistry specific errors."""
        _LOGGER.warning("DockerRegistry error for image '%s': %s", image_key, str(e))
        return {
            "status": 500,
            "status_description": get_status_description(500, None, translations),
            "manifest": {},
            "registry_used": True,
        }

    def _handle_unexpected_error(
        self, e, image_key, get_status_description, translations
    ):
        """Handle unexpected errors from registry interactions."""
        _LOGGER.warning(
            "Unexpected error fetching registry data for image '%s': %s",
            image_key,
            str(e),
        )
        return {
            "status": 500,
            "status_description": get_status_description(500, None, translations),
            "manifest": {},
            "registry_used": True,
        }

    def _get_arch_and_os(self, eid: str, image_key: str) -> tuple[str, str]:
        """Get the architecture and OS for a given image."""
        images = self.api.query(f"endpoints/{eid}/docker/images/json")
        arch, os = None, None
        for img in images:
            if image_key in img.get("RepoTags", []) or img.get("Id") == image_key:
                arch = img.get("Architecture")
                os = img.get("Os")
                break
        if not arch or not os:
            info = self.api.query(f"endpoints/{eid}/docker/info")
            arch = arch or info.get("Architecture", "amd64")
            os = os or info.get("OSType", "linux")
        if arch == "x86_64":
            arch = "amd64"
        return arch, os

    def _add_digest_to_manifest(self, manifest: dict) -> None:
        """Add digest to manifest if not already present."""
        if (
            manifest.get("schemaVersion") == 2
            and manifest.get("mediaType", "")
            in (
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
            )
            and "config" in manifest
            and "digest" in manifest["config"]
        ):
            manifest["Id"] = manifest["config"]["digest"]

    def _compare_image_ids(
        self,
        registry_response: dict,
        container_data: dict,
        container_name: str,
        image_name: str,
    ) -> bool:
        """Compare the image IDs from the registry and the container."""
        registry_image_id = self._normalize_image_id(registry_response.get("Id", ""))
        container_image_id = self._normalize_image_id(container_data.get("ImageID", ""))
        update_available = False
        if registry_image_id and container_image_id:
            update_available = registry_image_id != container_image_id
        if update_available:
            _LOGGER.info(
                "Update available: %s (%s) - Current: %s, Registry: %s",
                container_name,
                image_name,
                container_image_id[-12:] if container_image_id else "None",
                registry_image_id[-12:] if registry_image_id else "None",
            )
        else:
            _LOGGER.debug(
                "No update: %s (%s) - Current: %s, Registry: %s",
                container_name,
                image_name,
                container_image_id if container_image_id else "None",
                registry_image_id if registry_image_id else "None",
            )
        return update_available

    @staticmethod
    def _normalize_image_id(image_id: str) -> str:
        """Normalize the image ID by removing the 'sha256:' prefix if present."""
        if image_id.startswith("sha256:"):
            return image_id[7:]
        return image_id

    def _get_update_description(self, status, registry_name=None, translations=None):
        """Get a human-readable description for the update status."""
        desc_key = f"update_status_{status}"
        if translations is None:
            translations = getattr(self.hass, "translations", {})
        if (
            translations
            and TRANSLATION_UPDATE_CHECK_STATUS_STATE in translations
            and desc_key in translations[TRANSLATION_UPDATE_CHECK_STATUS_STATE]
        ):
            text = translations[TRANSLATION_UPDATE_CHECK_STATUS_STATE][desc_key]
            if self.REGISTRY_LITERAL in text and registry_name:
                return text.replace(self.REGISTRY_LITERAL, registry_name)
            return text
        default_map = {
            0: "No update available.",
            1: "Update available!",
            2: "Update status not yet checked.",
            401: "Unauthorized (registry credentials required or invalid) for registry {registry}.",
            404: "Image not found on registry ({registry}).",
            429: "Registry rate limit reached.",
            500: "Registry/internal error.",
        }
        text = default_map.get(status, f"Status code: {status}")
        if self.REGISTRY_LITERAL in text and registry_name:
            return text.replace(self.REGISTRY_LITERAL, registry_name)
        return text

    def _log_and_cache_no_image(self, container_id: str, container_name: str) -> None:
        """Log and cache the case where no image name is found."""
        _LOGGER.debug(
            "Container %s: No image name found, skipping update check",
            container_name,
        )
        translations = getattr(self.hass, "translations", {})
        status_description = self._get_update_description(500, None, translations)
        self.cached_update_results[container_id] = {
            "status": 500,
            "status_description": status_description,
            "manifest": {},
            "registry_used": False,
        }

    def force_update_check(self) -> None:
        """Force an immediate update check for all containers."""
        if not self.features[CONF_FEATURE_UPDATE_CHECK]:
            _LOGGER.error(
                "Force update check requested but update check feature is disabled"
            )
            return

        # Clear cached results to force fresh check
        self.cached_update_results.clear()
        self.cached_registry_responses.clear()
