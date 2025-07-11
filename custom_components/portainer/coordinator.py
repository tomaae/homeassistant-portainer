"""Portainer coordinator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_SSL,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import PortainerAPI
from .apiparser import parse_api
from .const import (
    CONF_FEATURE_HEALTH_CHECK,  # feature switch
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CUSTOM_ATTRIBUTE_ARRAY,
    DEFAULT_FEATURE_HEALTH_CHECK,
    DEFAULT_FEATURE_RESTART_POLICY,
    DEFAULT_FEATURE_UPDATE_CHECK,
    DOMAIN,
    SCAN_INTERVAL,
)
from .docker_registry import DockerRegistryError

_LOGGER = logging.getLogger(__name__)

TRANSLATION_UPDATE_CHECK_STATUS_STATE = (
    "component.portainer.entity.sensor.update_check_status.state"
)


# ---------------------------
#   PortainerControllerData
# ---------------------------
class PortainerCoordinator(DataUpdateCoordinator):
    """PortainerControllerData Class."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize PortainerController."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.hass = hass
        self.data = config_entry.data
        self.name = config_entry.data[CONF_NAME]
        self.host = config_entry.data[CONF_HOST]
        self.config_entry_id = config_entry.entry_id

        # init custom features
        self.features = {
            CONF_FEATURE_HEALTH_CHECK: config_entry.options.get(
                CONF_FEATURE_HEALTH_CHECK, DEFAULT_FEATURE_HEALTH_CHECK
            ),
            CONF_FEATURE_RESTART_POLICY: config_entry.options.get(
                CONF_FEATURE_RESTART_POLICY, DEFAULT_FEATURE_RESTART_POLICY
            ),
            CONF_FEATURE_UPDATE_CHECK: config_entry.options.get(
                CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
            ),
        }

        self.last_update_check: datetime | None = None
        self.force_update_requested: bool = False  # Flag for force update
        self.cached_update_results: dict[str, bool] = {}
        self.cached_registry_responses: dict[str, dict] = {}

        # init raw data
        self.raw_data: dict[str, dict] = {
            "endpoints": {},
            "containers": {},
        }

        self.lock = asyncio.Lock()

        self.api = PortainerAPI(
            self.hass,
            self.host,
            self.data[CONF_API_KEY],
            self.data[CONF_SSL],
            self.data[CONF_VERIFY_SSL],
        )
        self.config_entry = config_entry
        self._systemstats_errored: list = []
        self.datasets_hass_device_id = None

        self.config_entry.async_on_unload(self.async_shutdown)

    @property
    def update_check_time(self):
        """Return the update check time (hour, minute) from config_entry options or default."""
        time_str = self.config_entry.options.get("update_check_time", "02:00")
        try:
            hour, minute = [int(x) for x in time_str.split(":")]
        except Exception:
            hour, minute = 2, 0  # fallback
        return hour, minute

    # ---------------------------
    #   async_shutdown
    # ---------------------------
    async def async_update_entry(self, config_entry):
        """Handle config entry update (called after options change)."""
        self.config_entry = config_entry
        # Update features from new options
        self.features = {
            CONF_FEATURE_HEALTH_CHECK: config_entry.options.get(
                CONF_FEATURE_HEALTH_CHECK, DEFAULT_FEATURE_HEALTH_CHECK
            ),
            CONF_FEATURE_RESTART_POLICY: config_entry.options.get(
                CONF_FEATURE_RESTART_POLICY, DEFAULT_FEATURE_RESTART_POLICY
            ),
            CONF_FEATURE_UPDATE_CHECK: config_entry.options.get(
                CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
            ),
        }
        # Reset last_update_check so the new schedule is taken over immediately
        self.last_update_check = None
        await self.async_request_refresh()

    # ---------------------------
    #   async_shutdown
    # ---------------------------
    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        if self.lock.locked():
            self.lock.release()

    # ---------------------------
    #   connected
    # ---------------------------
    def connected(self) -> bool:
        """Return connected state."""
        return self.api.connected()

    # ---------------------------
    #   _async_update_data
    # ---------------------------
    async def _async_update_data(self) -> dict[str, dict]:
        """Update Portainer data. Triggers update check at scheduled time without recursion."""
        try:
            await asyncio.wait_for(self.lock.acquire(), timeout=10)
        except TimeoutError:
            return {}

        try:
            self.raw_data = {}
            await self.hass.async_add_executor_job(self.get_endpoints)
            await self.hass.async_add_executor_job(self.get_containers)
            await self.hass.async_add_executor_job(self.get_system_data)
        except Exception as error:
            self.lock.release()
            raise UpdateFailed(error) from error

        self.lock.release()
        _LOGGER.debug("data: %s", self.raw_data)

        # Notify entities of new data
        async_dispatcher_send(self.hass, f"{self.config_entry.entry_id}_update", self)

        return self.raw_data

    # ---------------------------
    #   get_system_data
    # ---------------------------
    def get_system_data(self) -> None:
        """Get system-level data."""
        update_enabled = self.features[CONF_FEATURE_UPDATE_CHECK]
        next_update = self.get_next_update_check_time() if update_enabled else None

        if not update_enabled:
            # Feature is disabled
            next_update_value = "disabled"
        elif next_update:
            # Feature is enabled and next check is scheduled
            next_update_value = next_update.isoformat()
        else:
            # Feature is enabled but no check scheduled (should not happen normally)
            next_update_value = "never"

        system_data = {
            "next_update_check": next_update_value,
            "update_feature_enabled": update_enabled,
            "last_update_check": (
                self.last_update_check.isoformat()
                if self.last_update_check
                else "never"
            ),
        }

        self.raw_data["system"] = system_data
        _LOGGER.debug("System data created: %s", system_data)

    # ---------------------------
    #   get_endpoints
    # ---------------------------
    def get_endpoints(self) -> None:
        """Get endpoints."""

        self.raw_data["endpoints"] = parse_api(
            data={},
            source=self.api.query("endpoints"),
            key="Id",
            vals=[
                {"name": "Id", "default": 0},
                {"name": "Name", "default": "unknown"},
                {"name": "Snapshots", "default": "unknown"},
                {"name": "Type", "default": 0},
                {"name": "Status", "default": 0},
            ],
        )
        if not self.raw_data["endpoints"]:
            return

        for eid in self.raw_data["endpoints"]:
            self.raw_data["endpoints"][eid] = parse_api(
                data=self.raw_data["endpoints"][eid],
                source=self.raw_data["endpoints"][eid]["Snapshots"][0],
                vals=[
                    {"name": "DockerVersion", "default": "unknown"},
                    {"name": "Swarm", "default": False},
                    {"name": "TotalCPU", "default": 0},
                    {"name": "TotalMemory", "default": 0},
                    {"name": "RunningContainerCount", "default": 0},
                    {"name": "StoppedContainerCount", "default": 0},
                    {"name": "HealthyContainerCount", "default": 0},
                    {"name": "UnhealthyContainerCount", "default": 0},
                    {"name": "VolumeCount", "default": 0},
                    {"name": "ImageCount", "default": 0},
                    {"name": "ServiceCount", "default": 0},
                    {"name": "StackCount", "default": 0},
                    {"name": "ConfigEntryId", "default": self.config_entry_id},
                ],
            )
            del self.raw_data["endpoints"][eid]["Snapshots"]

    # ---------------------------
    #   get_containers
    # ---------------------------
    def get_containers(self) -> None:
        """Get containers from all endpoints."""
        self.raw_data["containers"] = {}
        registry_checked = False

        for eid in self.raw_data["endpoints"]:
            if self.raw_data["endpoints"][eid]["Status"] != 1:
                continue
            self.raw_data["containers"][eid] = self._parse_containers_for_endpoint(eid)
            self._set_container_environment_and_config(eid)
            if self._custom_features_enabled():
                registry_checked = self._handle_custom_features_for_endpoint(
                    eid, registry_checked
                )

        self.raw_data["containers"] = self._flatten_containers_dict(
            self.raw_data["containers"]
        )

        if registry_checked:
            self.last_update_check = dt_util.now()

    def _parse_containers_for_endpoint(self, eid: str) -> dict:
        """Parse containers for a given endpoint."""
        return parse_api(
            data={},
            source=self.api.query(
                f"endpoints/{eid}/docker/containers/json", "get", {"all": True}
            ),
            key="Id",
            vals=[
                {"name": "Id", "default": "unknown"},
                {"name": "Names", "default": "unknown"},
                {"name": "Image", "default": "unknown"},
                {"name": "ImageID", "default": "unknown"},
                {"name": "State", "default": "unknown"},
                {"name": "Ports", "default": "unknown"},
                {
                    "name": "Network",
                    "source": "HostConfig/NetworkMode",
                    "default": "unknown",
                },
                {
                    "name": "Compose_Stack",
                    "source": "Labels/com.docker.compose.project",
                    "default": "",
                },
                {
                    "name": "Compose_Service",
                    "source": "Labels/com.docker.compose.service",
                    "default": "",
                },
                {
                    "name": "Compose_Version",
                    "source": "Labels/com.docker.compose.version",
                    "default": "",
                },
            ],
            ensure_vals=[
                {"name": "Name", "default": "unknown"},
                {"name": "EndpointId", "default": eid},
                {"name": CUSTOM_ATTRIBUTE_ARRAY, "default": None},
            ],
        )

    def _set_container_environment_and_config(self, eid: str) -> None:
        """Set environment and config for containers in an endpoint."""
        for cid in self.raw_data["containers"][eid]:
            container = self.raw_data["containers"][eid][cid]
            container["Environment"] = self.raw_data["endpoints"][eid]["Name"]
            container["Name"] = container["Names"][0][1:]
            container["ConfigEntryId"] = self.config_entry_id
            container[CUSTOM_ATTRIBUTE_ARRAY] = {}

    def _custom_features_enabled(self) -> bool:
        """Check if any custom feature is enabled."""
        return (
            self.features[CONF_FEATURE_HEALTH_CHECK]
            or self.features[CONF_FEATURE_RESTART_POLICY]
            or self.features[CONF_FEATURE_UPDATE_CHECK]
        )

    def _handle_custom_features_for_endpoint(
        self, eid: str, registry_checked: bool
    ) -> bool:
        """Handle custom features for containers in an endpoint."""
        for cid in self.raw_data["containers"][eid]:
            container = self.raw_data["containers"][eid][cid]
            container[CUSTOM_ATTRIBUTE_ARRAY + "_Raw"] = parse_api(
                data={},
                source=self.api.query(
                    f"endpoints/{eid}/docker/containers/{cid}/json",
                    "get",
                    {"all": True},
                ),
                vals=[
                    {
                        "name": "Health_Status",
                        "source": "State/Health/Status",
                        "default": "unknown",
                    },
                    {
                        "name": "Restart_Policy",
                        "source": "HostConfig/RestartPolicy/Name",
                        "default": "unknown",
                    },
                ],
                ensure_vals=[
                    {"name": "Health_Status", "default": "unknown"},
                    {"name": "Restart_Policy", "default": "unknown"},
                ],
            )
            if self.features[CONF_FEATURE_HEALTH_CHECK]:
                container[CUSTOM_ATTRIBUTE_ARRAY]["Health_Status"] = container[
                    CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                ]["Health_Status"]
            if self.features[CONF_FEATURE_RESTART_POLICY]:
                container[CUSTOM_ATTRIBUTE_ARRAY]["Restart_Policy"] = container[
                    CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                ]["Restart_Policy"]
            if self.features[CONF_FEATURE_UPDATE_CHECK]:
                update_available = self.check_image_updates(eid, container)
                if update_available["registry_used"]:
                    registry_checked = True
                container[CUSTOM_ATTRIBUTE_ARRAY]["Update_Available"] = (
                    update_available["status"]
                )
                container[CUSTOM_ATTRIBUTE_ARRAY]["Update_Description"] = (
                    update_available["status_description"]
                )
            del container[CUSTOM_ATTRIBUTE_ARRAY + "_Raw"]
        return registry_checked

    def _get_update_description(self, status, registry_name=None, translations=None):
        """Return a user-facing description for a given update status code, using translations if available."""
        desc_key = f"update_status_{status}"
        if translations is None:
            translations = getattr(self.hass, "translations", {})
        if (
            translations
            and TRANSLATION_UPDATE_CHECK_STATUS_STATE in translations
            and desc_key in translations[TRANSLATION_UPDATE_CHECK_STATUS_STATE]
        ):
            text = translations[TRANSLATION_UPDATE_CHECK_STATUS_STATE][desc_key]
            # If the translation text contains {registry}, replace it if registry_name is provided
            if "{registry}" in text and registry_name:  # NOSONAR
                return text.replace("{registry}", registry_name)
            return text
        # Fallback default
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
        if "{registry}" in text and registry_name:
            return text.replace("{registry}", registry_name)
        return text

    # ---------------------------
    #   should_check_updates
    # ---------------------------
    def should_check_updates(self) -> bool:
        """Check if it's time to check for updates."""
        if not self.features[CONF_FEATURE_UPDATE_CHECK]:
            return False

        # If force update was requested, always return True
        if self.force_update_requested:
            _LOGGER.debug("Force update requested - bypassing time checks")
            return True

        now = dt_util.now()
        hour, minute = self.update_check_time
        scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If now is before scheduled time today
        if now < scheduled_time:
            # Not yet time for today's check
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

    # ---------------------------
    #   get_next_update_check_time
    # ---------------------------
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

        # ---------------------------
        #   force_update_check
        # ---------------------------

    async def force_update_check(self) -> None:
        """Force an immediate update check for all containers."""
        if not self.features[CONF_FEATURE_UPDATE_CHECK]:
            _LOGGER.error(
                "Force update check requested but update check feature is disabled"
            )
            return

        _LOGGER.info("Force update check initiated for all containers")

        # Set force update flag to bypass time checks
        self.force_update_requested = True

        # Clear cached results to force fresh check
        self.cached_update_results.clear()
        self.cached_registry_responses.clear()

        # Update last check time to now to reset the cache expiry timer
        self.last_update_check = dt_util.now()

        # Trigger data refresh
        await self.async_request_refresh()

        # Reset force update flag after refresh is complete
        self.force_update_requested = False

        _LOGGER.info("Force update check completed")

    @staticmethod
    def _normalize_image_id(image_id: str) -> str:
        """Normalize an image ID by removing the sha256: prefix if present."""
        if image_id.startswith("sha256:"):
            return image_id[7:]  # Remove "sha256:" prefix
        return image_id

    def _get_registry_response(
        self,
        eid: str,
        registry: str,
        image_repo: str,
        image_tag: str,
        image_key: str,
    ) -> dict:
        """Fetch the image manifest from the registry using DockerRegistry. Returns a dict with status, description, manifest, registry_used."""
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
        """Handle exceptions from registry requests. Returns dict for _get_registry_response."""
        if isinstance(e, requests.HTTPError):
            return self._handle_http_error(
                e, registry, image_key, get_status_description, translations
            )
        elif isinstance(e, ValueError):
            return self._handle_value_error(
                e, registry, image_key, get_status_description, translations
            )
        elif isinstance(e, DockerRegistryError):
            return self._handle_docker_registry_error(
                e, image_key, get_status_description, translations
            )
        else:
            return self._handle_unexpected_error(
                e, image_key, get_status_description, translations
            )

    def _handle_http_error(
        self, e, registry, image_key, get_status_description, translations
    ):
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

    def check_image_updates(self, eid: str, container_data: dict) -> dict:
        """Check if an image update is available for a container. Returns dict with status, description, manifest, registry_used."""
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

        from .docker_registry import BaseRegistry

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

            # If the registry response is not successful, return the result directly
            if result["status"] != 200:
                self.cached_update_results[container_id] = result
                return result

            # If the registry response is successful, compare image IDs
            update_available = self._compare_image_ids(
                result["manifest"],
                container_data,
                container_id,
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

    def _log_and_cache_no_image(self, container_id: str, container_name: str) -> None:
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

    def _get_arch_and_os(self, eid: str, image_key: str) -> tuple[str, str]:
        """Get architecture and OS for the image."""
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
        """Add digest as 'Id' to manifest if present."""
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

    # ---------------------------
    #   _compare_image_ids
    # ---------------------------
    def _compare_image_ids(
        self,
        registry_response: dict,
        container_data: dict,
        container_id: str,
        container_name: str,
        image_name: str,
    ) -> bool:
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

    def _flatten_containers_dict(self, containers: dict) -> dict:
        """Flatten the containers dictionary so each environment has its own set of containers."""
        return {
            f"{eid}{cid}": value
            for eid, t_dict in containers.items()
            for cid, value in t_dict.items()
        }

    def _invalidate_cache_if_needed(self):
        """Invalidate cached registry responses if the last check is older than 24 hours."""
        if self.last_update_check is None:
            self.cached_registry_responses.clear()
            return
        now = dt_util.now()
        if (now - self.last_update_check).total_seconds() > 86400:
            self.cached_registry_responses.clear()
        # Otherwise, do nothing (cache remains)
