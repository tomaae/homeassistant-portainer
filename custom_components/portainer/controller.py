"""Portainer Controller."""
from asyncio import Lock as Asyncio_lock, wait_for as asyncio_wait_for
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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_entries_for_config_entry
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .apiparser import parse_api
from .api import PortainerAPI

_LOGGER = getLogger(__name__)


# ---------------------------
#   PortainerControllerData
# ---------------------------
class PortainerControllerData(object):
    """PortainerControllerData Class."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize PortainerController."""
        self.hass = hass
        self.config_entry = config_entry
        self.name = config_entry.data[CONF_NAME]
        self.host = config_entry.data[CONF_HOST]

        self.data = {
            "endpoints": {},
        }

        self.listeners = []
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

        self._force_update_callback = None

    # ---------------------------
    #   async_init
    # ---------------------------
    async def async_init(self) -> None:
        """Initialize."""
        self._force_update_callback = async_track_time_interval(
            self.hass, self.force_update, timedelta(seconds=60)
        )

    # ---------------------------
    #   signal_update
    # ---------------------------
    @property
    def signal_update(self) -> str:
        """Event to signal new data."""
        return f"{DOMAIN}-update-{self.name}"

    # ---------------------------
    #   async_reset
    # ---------------------------
    async def async_reset(self) -> bool:
        """Reset dispatchers."""
        for unsub_dispatcher in self.listeners:
            unsub_dispatcher()

        self.listeners = []
        return True

    # ---------------------------
    #   connected
    # ---------------------------
    def connected(self) -> bool:
        """Return connected state."""
        return self.api.connected()

    # ---------------------------
    #   force_update
    # ---------------------------
    @callback
    async def force_update(self, _now=None) -> None:
        """Trigger update by timer."""
        await self.async_update()

    # ---------------------------
    #   async_update
    # ---------------------------
    async def async_update(self):
        """Update Portainer data."""
        try:
            await asyncio_wait_for(self.lock.acquire(), timeout=10)
        except Exception:
            return

        await self.hass.async_add_executor_job(self.get_endpoints)
        # if self.api.connected():
        #     await self.hass.async_add_executor_job(self.get_systemstats)


        async_dispatcher_send(self.hass, self.signal_update)
        self.lock.release()
    # ---------------------------
    #   get_endpoints
    # ---------------------------
    def get_endpoints(self):
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

        for uid in self.data["endpoints"]:
            self.data["endpoints"][uid] = parse_api(
                data=self.data["endpoints"][uid],
                source=self.data["endpoints"][uid]["Snapshots"][0],
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
                ],
            )
            del self.data["endpoints"][uid]["Snapshots"]

