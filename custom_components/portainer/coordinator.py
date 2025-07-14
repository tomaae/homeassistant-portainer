"""Portainer coordinator."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

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
from .portainer_update_service import PortainerUpdateService

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

        self.api = PortainerAPI(
            self.hass,
            self.host,
            self.data[CONF_API_KEY],
            self.data[CONF_SSL],
            self.data[CONF_VERIFY_SSL],
        )

        self.update_service = PortainerUpdateService(
            hass,
            config_entry,
            self.api,
            self.features,
            self.config_entry_id,
        )

        # init raw data
        self.raw_data: dict[str, dict] = {
            "endpoints": {},
            "containers": {},
        }

        self.lock = asyncio.Lock()
        self.config_entry = config_entry
        self._systemstats_errored: list = []
        self.datasets_hass_device_id = None

        self.config_entry.async_on_unload(self.async_shutdown)

    @property
    def update_check_time(self):
        """Return the update check time (hour, minute) from config_entry options or default."""
        return self.update_service.update_check_time

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
        # Delegate update entry to update_service
        await self.update_service.async_update_entry(config_entry)
        await self.async_request_refresh()

    # ---------------------------
    #   async_shutdown
    # ---------------------------
    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        if self.lock.locked():
            try:
                self.lock.release()
            except RuntimeError:
                # Lock was not acquired by this task, ignore
                pass

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
        except asyncio.TimeoutError:
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

    def _flatten_containers_dict(self, containers: dict) -> dict:
        """Flatten the containers dictionary so each environment has its own set of containers."""
        return {
            f"{eid}{cid}": value
            for eid, t_dict in containers.items()
            for cid, value in t_dict.items()
        }

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
                update_available = self.update_service.check_image_updates(
                    eid, container
                )
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
        return self.update_service.should_check_updates()

    # ---------------------------
    #   force_update_check
    # ---------------------------
    async def force_update_check(self) -> None:
        """Force an immediate update check for all containers."""
        _LOGGER.info("Force update check initiated for all containers")
        self.update_service.force_update_requested = True
        self.update_service.force_update_check()
        await self.async_request_refresh()
        self.update_service.force_update_requested = False
        self.last_update_check = dt_util.now()
        _LOGGER.info("Force update check completed")

    @property
    def last_update_check(self):
        """Return the last update check time from update_service."""
        return self.update_service.last_update_check

    @last_update_check.setter
    def last_update_check(self, value):
        """Set the last update check time in update_service."""
        self.update_service.last_update_check = value

    def get_next_update_check_time(self):
        """Return the next scheduled update check time from update_service."""
        return self.update_service.get_next_update_check_time()
