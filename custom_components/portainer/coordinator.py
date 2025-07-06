"""Portainer coordinator."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from logging import getLogger

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

from .api import PortainerAPI
from .apiparser import parse_api
from .const import (
    CONF_FEATURE_HEALTH_CHECK,  # feature switch
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_HOUR,
    CUSTOM_ATTRIBUTE_ARRAY,
    DEFAULT_FEATURE_HEALTH_CHECK,
    DEFAULT_FEATURE_RESTART_POLICY,
    DEFAULT_FEATURE_UPDATE_CHECK,
    DEFAULT_UPDATE_CHECK_HOUR,
    DOMAIN,
    SCAN_INTERVAL,
)

_LOGGER = getLogger(__name__)


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

        # Update check configuration
        self.update_check_hour = config_entry.options.get(
            CONF_UPDATE_CHECK_HOUR, DEFAULT_UPDATE_CHECK_HOUR
        )
        self.last_update_check: datetime | None = None
        self.force_update_requested: bool = False  # Flag for force update
        self.cached_update_results: dict[str, bool] = {}
        self.cached_registry_responses: dict[
            str, dict
        ] = {}  # Cache registry responses per image name

        # init raw data
        self.raw_data: dict[str, dict] = {
            "endpoints": {},
            "containers": {},
        }

        self.lock = asyncio.Lock()

        self.api = PortainerAPI(
            hass,
            config_entry.data[CONF_HOST],
            config_entry.data[CONF_API_KEY],
            config_entry.data[CONF_SSL],
            config_entry.data[CONF_VERIFY_SSL],
        )
        self.config_entry = config_entry
        self._systemstats_errored: list = []
        self.datasets_hass_device_id = None

        self.config_entry.async_on_unload(self.async_shutdown)

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
        """Update Portainer data."""
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

        self.raw_data["endpoints"] = {}
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
        for eid in self.raw_data["endpoints"]:
            if self.raw_data["endpoints"][eid]["Status"] == 1:
                self.raw_data["containers"][eid] = {}
                self.raw_data["containers"][eid] = parse_api(
                    data=self.raw_data["containers"][eid],
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

                for cid in self.raw_data["containers"][eid]:
                    self.raw_data["containers"][eid][cid]["Environment"] = (
                        self.raw_data["endpoints"][eid]["Name"]
                    )
                    self.raw_data["containers"][eid][cid]["Name"] = self.raw_data[
                        "containers"
                    ][eid][cid]["Names"][0][1:]
                    self.raw_data["containers"][eid][cid]["ConfigEntryId"] = (
                        self.config_entry_id
                    )
                    # avoid shared references given in default
                    self.raw_data["containers"][eid][cid][CUSTOM_ATTRIBUTE_ARRAY] = {}

                # only if some custom feature is enabled
                if (
                    self.features[CONF_FEATURE_HEALTH_CHECK]
                    or self.features[CONF_FEATURE_RESTART_POLICY]
                    or self.features[CONF_FEATURE_UPDATE_CHECK]
                ):
                    for cid in self.raw_data["containers"][eid]:
                        self.raw_data["containers"][eid][cid][
                            CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                        ] = parse_api(
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
                            self.raw_data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY
                            ]["Health_Status"] = self.raw_data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                            ]["Health_Status"]
                        if self.features[CONF_FEATURE_RESTART_POLICY]:
                            self.raw_data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY
                            ]["Restart_Policy"] = self.raw_data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                            ]["Restart_Policy"]
                        if self.features[CONF_FEATURE_UPDATE_CHECK]:
                            # Check if image update is available
                            update_available = self.check_image_updates(
                                eid, self.raw_data["containers"][eid][cid]
                            )
                            self.raw_data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY
                            ]["Update_Available"] = update_available

                        del self.raw_data["containers"][eid][cid][
                            CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                        ]

        # ensure every environment has own set of containers
        self.raw_data["containers"] = {
            f"{eid}{cid}": value
            for eid, t_dict in self.raw_data["containers"].items()
            for cid, value in t_dict.items()
        }

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

        now = datetime.now()

        # If we've never checked, check now
        if self.last_update_check is None:
            _LOGGER.debug("First update check - performing now")
            return True

        # Calculate the next check time (today at configured hour)
        next_check = now.replace(
            hour=self.update_check_hour, minute=0, second=0, microsecond=0
        )

        # If the configured hour has passed today, set next check for tomorrow
        if now.hour >= self.update_check_hour:
            next_check += timedelta(days=1)

        # Check if we've passed the next check time since last check
        result = self.last_update_check < next_check and now >= next_check
        if result:
            _LOGGER.debug("Scheduled update check time reached")
        return result

    # ---------------------------
    #   get_next_update_check_time
    # ---------------------------
    def get_next_update_check_time(self) -> datetime | None:
        """Get the next scheduled update check time."""
        if not self.features[CONF_FEATURE_UPDATE_CHECK]:
            return None

        now = datetime.now()
        today_check = now.replace(
            hour=self.update_check_hour, minute=0, second=0, microsecond=0
        )

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
            _LOGGER.info(
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
        self.last_update_check = datetime.now()

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

    def _parse_image_name(self, image_name: str) -> tuple[str, str]:
        """Parse a Docker image name into repository and tag.

        Handles various formats:
        - nginx -> (nginx, latest)
        - nginx:1.21 -> (nginx, 1.21)
        - registry.com/nginx:latest -> (registry.com/nginx, latest)
        - nginx@sha256:abc123 -> (nginx, latest) [digest removed]
        - nginx:latest@sha256:abc123 -> (nginx, latest) [digest removed]
        - localhost:5000/nginx:latest -> (localhost:5000/nginx, latest)
        - localhost:5000/nginx -> (localhost:5000/nginx, latest)
        """
        if not image_name:
            return "unknown", "latest"

        # Remove digest part if present (everything after @)
        if "@" in image_name:
            image_name = image_name.split("@")[0]

        # Handle cases with no tag
        if ":" not in image_name:
            return image_name, "latest"

        # Strategy: Look for the rightmost colon that is followed by a valid tag
        # A valid tag doesn't contain "/" and isn't purely a port number in context
        parts = image_name.split(":")

        # Simple case: image:tag
        if len(parts) == 2:
            # Check if second part looks like a tag (doesn't contain /)
            if "/" not in parts[1]:
                return parts[0], parts[1]
            # This is likely registry:port/image format
            return image_name, "latest"

        # Complex case: registry:port/namespace/image:tag
        # Find the last colon that separates a tag (no "/" in the part after it)
        for i in range(len(parts) - 1, 0, -1):
            potential_tag = parts[i]
            potential_repo = ":".join(parts[:i])

            # Valid tag: no "/" and not empty
            if "/" not in potential_tag and potential_tag:
                # Additional check: if it's purely numeric and there's more than 2 parts,
                # it might be a port number, so be more careful
                if potential_tag.isdigit() and len(parts) > 2:
                    # Check if this could be a port by looking at context
                    # If the part before this has no "/" after it, likely a port
                    if (
                        i > 0 and "/" not in ":".join(parts[i + 1 :])
                        if i < len(parts) - 1
                        else True
                    ):
                        # This looks like a port, continue searching
                        continue

                return potential_repo, potential_tag

        # Fallback: treat whole thing as repository name
        return image_name, "latest"

    def _invalidate_cache_if_needed(self) -> None:
        """Invalidate cached registry responses if last update check is too old."""
        if self.last_update_check is None:
            return

        # Invalidate cache if last check was more than 24 hours ago
        cache_expiry = timedelta(hours=24)
        if datetime.now() - self.last_update_check > cache_expiry:
            _LOGGER.debug("Invalidating stale registry cache")
            self.cached_registry_responses.clear()

    def check_image_updates(self, eid: str, container_data: dict) -> bool:
        """Check if an image update is available for a container."""
        container_id = container_data.get("Id", "")
        container_name = container_data.get("Name", "").lstrip("/")

        # Get the current image name (without tag if present)
        image_name = container_data.get("Image", "")
        if not image_name:
            _LOGGER.debug(
                "Container %s: No image name found, skipping update check",
                container_name,
            )
            self.cached_update_results[container_id] = False
            return False

        # Parse image name and tag using robust parsing
        image_repo, image_tag = self._parse_image_name(image_name)
        image_key = f"{image_repo}:{image_tag}"

        _LOGGER.debug(
            "Container %s: Parsed image '%s' -> repo='%s', tag='%s'",
            container_name,
            image_name,
            image_repo,
            image_tag,
        )

        # Check only once whether we should perform updates
        should_check = self.should_check_updates()

        # Use cached result if available and not time to check
        if not should_check and container_id in self.cached_update_results:
            return self.cached_update_results[container_id]

        # Invalidate stale cache if needed
        self._invalidate_cache_if_needed()

        try:
            # Only query registry if it's time to check
            if should_check:
                # Use cached registry response if available
                if image_key in self.cached_registry_responses:
                    registry_response = self.cached_registry_responses[image_key]
                else:
                    api_result = self.api.query(
                        f"endpoints/{eid}/docker/images/{image_repo}:{image_tag}/json",
                        "get",
                    )
                    if isinstance(api_result, list) and api_result:
                        registry_response = api_result[0]
                    elif isinstance(api_result, dict):
                        registry_response = api_result
                    else:
                        registry_response = {}
                    self.cached_registry_responses[image_key] = registry_response

                if not registry_response:
                    self.cached_update_results[container_id] = False
                    return False

                # Get and normalize the image IDs for comparison
                registry_image_id = self._normalize_image_id(
                    registry_response.get("Id", "")
                )
                container_image_id = self._normalize_image_id(
                    container_data.get("ImageID", "")
                )

                # Compare the normalized IDs - if they differ, an update is available
                update_available = False
                if registry_image_id and container_image_id:
                    update_available = registry_image_id != container_image_id

                # Info logging only for containers with updates available
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

                # Cache the result
                self.cached_update_results[container_id] = update_available

                # Update the last check time
                self.last_update_check = datetime.now()

                return update_available

            # Return cached result or False if no cache
            return self.cached_update_results.get(container_id, False)

        except (KeyError, ValueError, TypeError) as e:
            _LOGGER.warning(
                "Container %s: Update check failed - %s", container_name, str(e)
            )
            self.cached_update_results[container_id] = False
            return False
