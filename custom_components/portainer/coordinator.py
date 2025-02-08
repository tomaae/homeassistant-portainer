"""Portainer coordinator."""

from __future__ import annotations

from asyncio import Lock as Asyncio_lock, wait_for as asyncio_wait_for
from datetime import timedelta
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
        }

        self.data = {
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
            await self.hass.async_add_executor_job(self.get_endpoints)
            await self.hass.async_add_executor_job(self.get_containers)
        except Exception as error:
            self.lock.release()
            raise UpdateFailed(error) from error

        self.lock.release()
        return self.data

    # ---------------------------
    #   get_endpoints
    # ---------------------------
    def get_endpoints(self) -> None:
        """Get endpoints."""
        self.data["endpoints"] = parse_api(
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
        if not self.data["endpoints"]:
            return

        for eid in self.data["endpoints"]:
            self.data["endpoints"][eid] = parse_api(
                data=self.data["endpoints"][eid],
                source=self.data["endpoints"][eid]["Snapshots"][0],
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
            del self.data["endpoints"][eid]["Snapshots"]

    # ---------------------------
    #   get_containers
    # ---------------------------
    def get_containers(self) -> None:
        self.data["containers"] = {}
        for eid in self.data["endpoints"]:
            if self.data["endpoints"][eid]["Status"] == 1:
                self.data["containers"][eid] = {}
                self.data["containers"][eid] = parse_api(
                    data=self.data["containers"][eid],
                    source=self.api.query(
                        f"endpoints/{eid}/docker/containers/json", "get", {"all": True}
                    ),
                    key="Id",
                    vals=[
                        {"name": "Id", "default": "unknown"},
                        {"name": "Names", "default": "unknown"},
                        {"name": "Image", "default": "unknown"},
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
                        {"name": CUSTOM_ATTRIBUTE_ARRAY, "default": {}},
                    ],
                )
                for cid in self.data["containers"][eid]:
                    self.data["containers"][eid][cid]["Environment"] = self.data[
                        "endpoints"
                    ][eid]["Name"]
                    self.data["containers"][eid][cid]["Name"] = self.data["containers"][
                        eid
                    ][cid]["Names"][0][1:]
                    self.data["containers"][eid][cid][
                        "ConfigEntryId"
                    ] = self.config_entry_id

                # only if some custom feature is enabled
                if (
                    self.features[CONF_FEATURE_HEALTH_CHECK]
                    or self.features[CONF_FEATURE_RESTART_POLICY]
                ):
                    for cid in self.data["containers"][eid]:
                        self.data["containers"][eid][cid][
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
                            self.data["containers"][eid][cid][CUSTOM_ATTRIBUTE_ARRAY][
                                "Health_Status"
                            ] = self.data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                            ][
                                "Health_Status"
                            ]
                        if self.features[CONF_FEATURE_RESTART_POLICY]:
                            self.data["containers"][eid][cid][CUSTOM_ATTRIBUTE_ARRAY][
                                "Restart_Policy"
                            ] = self.data["containers"][eid][cid][
                                CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                            ][
                                "Restart_Policy"
                            ]
                        del self.data["containers"][eid][cid][
                            CUSTOM_ATTRIBUTE_ARRAY + "_Raw"
                        ]

        # ensure every environment has own set of containers
        self.data["containers"] = {
            f"{eid}{cid}": value
            for eid, t_dict in self.data["containers"].items()
            for cid, value in t_dict.items()
        }
