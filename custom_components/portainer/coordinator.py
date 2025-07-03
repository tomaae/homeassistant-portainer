"""Portainer coordinator."""

from __future__ import annotations

from asyncio import Lock as Asyncio_lock, wait_for as asyncio_wait_for
from datetime import timedelta, datetime
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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    CUSTOM_ATTRIBUTE_ARRAY,
    # fature switch
    CONF_FEATURE_HEALTH_CHECK,
    DEFAULT_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    DEFAULT_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    DEFAULT_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_HOUR,
    DEFAULT_UPDATE_CHECK_HOUR,
)
from .apiparser import parse_api
from .api import PortainerAPI

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
        self.last_update_check = None
        self.cached_update_results = {}

        # init raw data
        self.raw_data = {
            "endpoints": {},
            "containers": {},
        }

        self.lock = Asyncio_lock()

        self.api = PortainerAPI(
            hass,
            config_entry.data[CONF_HOST],
            config_entry.data[CONF_API_KEY],
            config_entry.data[CONF_SSL],
            config_entry.data[CONF_VERIFY_SSL],
        )

        self._systemstats_errored = []
        self.datasets_hass_device_id = None

        self.config_entry.async_on_unload(self.async_shutdown)

    # ---------------------------
    #   connected
    # ---------------------------
    def connected(self) -> bool:
        """Return connected state."""
        return self.api.connected()

    # ---------------------------
    #   _async_update_data
    # ---------------------------
    async def _async_update_data(self) -> None:
        """Update Portainer data."""
        try:
            await asyncio_wait_for(self.lock.acquire(), timeout=10)
        except Exception:
            return

        try:
            self.raw_data = {}
            await self.hass.async_add_executor_job(self.get_endpoints)
            await self.hass.async_add_executor_job(self.get_containers)
        except Exception as error:
            self.lock.release()
            raise UpdateFailed(error) from error

        self.lock.release()
        _LOGGER.debug("data: %s", self.raw_data)
        return self.raw_data

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
                    self.raw_data["containers"][eid][cid][
                        "ConfigEntryId"
                    ] = self.config_entry_id
                    # avoid shared references given in default
                    self.raw_data["containers"][eid][cid][CUSTOM_ATTRIBUTE_ARRAY] = {}

                # only if some custom feature is enabled
                if (
                    self.features[CONF_FEATURE_HEALTH_CHECK]
                    or self.features[CONF_FEATURE_RESTART_POLICY]
                    or self.features[CONF_FEATURE_UPDATE_CHECK]
                ):
                    for cid in self.raw_data["containers"][eid].keys():
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
                            ][
                                "Health_Status"
                            ]
                        if self.features[CONF_FEATURE_RESTART_POLICY]:
                            self.raw_data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY
                            ]["Restart_Policy"] = self.raw_data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                            ][
                                "Restart_Policy"
                            ]
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
            
        now = datetime.now()
        
        # If we've never checked, check now
        if self.last_update_check is None:
            return True
            
        # Calculate the next check time (today at configured hour)
        next_check = now.replace(hour=self.update_check_hour, minute=0, second=0, microsecond=0)
        
        # If the configured hour has passed today, set next check for tomorrow
        if now.hour >= self.update_check_hour:
            next_check += timedelta(days=1)
            
        # Check if we've passed the next check time since last check
        return self.last_update_check < next_check and now >= next_check

    # ---------------------------
    #   check_image_updates
    # ---------------------------
    def check_image_updates(self, eid: str, container_data: dict) -> bool:
        """Check if an image update is available for a container."""
        container_id = container_data.get("Id", "")
        
        # Use cached result if available and not time to check
        if not self.should_check_updates() and container_id in self.cached_update_results:
            return self.cached_update_results[container_id]
            
        try:
            # Get the current image name (without tag if present)
            image_name = container_data.get("Image", "")
            if not image_name:
                self.cached_update_results[container_id] = False
                return False

            # Parse image name and tag
            if ":" in image_name:
                image_repo, image_tag = image_name.rsplit(":", 1)
            else:
                image_repo = image_name
                image_tag = "latest"

            # Only query registry if it's time to check
            if self.should_check_updates():
                _LOGGER.debug("Checking for updates for container %s (image: %s)", 
                             container_data.get("Name", ""), image_name)
                
                # Query the registry for the latest image info
                registry_response = self.api.query(
                    f"endpoints/{eid}/docker/images/{image_repo}:{image_tag}/json",
                    "get",
                )

                if not registry_response:
                    self.cached_update_results[container_id] = False
                    return False

                # Get the current ImageID from the registry
                registry_image_id = registry_response.get("Id", "")
                container_image_id = container_data.get("ImageID", "")

                # Compare the IDs - if they differ, an update is available
                update_available = False
                if registry_image_id and container_image_id:
                    update_available = registry_image_id != container_image_id

                # Cache the result
                self.cached_update_results[container_id] = update_available
                
                # Update the last check time
                self.last_update_check = datetime.now()
                
                return update_available
            else:
                # Return cached result or False if no cache
                return self.cached_update_results.get(container_id, False)

        except Exception as e:
            _LOGGER.debug("Error checking image updates for container: %s", e)
            self.cached_update_results[container_id] = False

        return False
