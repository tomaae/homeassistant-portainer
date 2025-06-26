"""Portainer HA shared entity model."""

from __future__ import annotations

from collections.abc import Mapping
from logging import getLogger
from typing import Any

from homeassistant.const import ATTR_ATTRIBUTION, CONF_HOST, CONF_NAME, CONF_SSL
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    ATTRIBUTION,
    DOMAIN,
    CUSTOM_ATTRIBUTE_ARRAY,
    DEVICE_ATTRIBUTES_CONTAINERS_UNIQUE,
)
from .coordinator import PortainerCoordinator
from .helper import format_attribute, format_camel_case

_LOGGER = getLogger(__name__)


# ---------------------------
#   async_create_sensors
# ---------------------------
async def async_create_sensors(
    coordinator: PortainerCoordinator, descriptions: list, dispatcher: dict
) -> list[PortainerEntity]:
    hass = coordinator.hass
    config_entry = coordinator.config_entry
    for description in descriptions:
        data = coordinator.data[description.data_path]
        if not description.data_reference:
            if data.get(description.data_attribute) is None:
                continue
            obj = dispatcher[description.func](coordinator, description)
            hass.data[DOMAIN].setdefault(config_entry.entry_id, {}).setdefault(
                "entities", {}
            )[obj.unique_id] = obj
        else:
            for uid in data:
                obj = dispatcher[description.func](coordinator, description, uid)
                hass.data[DOMAIN].setdefault(config_entry.entry_id, {}).setdefault(
                    "entities", {}
                )[obj.unique_id] = obj
    return list(hass.data[DOMAIN][config_entry.entry_id]["entities"].values())


# ---------------------------
#   PortainerEntity
# ---------------------------
class PortainerEntity(CoordinatorEntity[PortainerCoordinator], Entity):
    """Define entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator)
        self.manufacturer = "Docker"
        self.sw_version = ""
        self.coordinator = coordinator
        self.description = description
        self._inst = coordinator.config_entry.data[CONF_NAME]
        self._attr_extra_state_attributes = {ATTR_ATTRIBUTION: ATTRIBUTION}
        self._uid = uid
        self._data = coordinator.data[self.description.data_path]
        if self._uid:
            self._data = coordinator.data[self.description.data_path][self._uid]
            # build _attr_unique_id (with _uid)
            slug = ""
            for key in DEVICE_ATTRIBUTES_CONTAINERS_UNIQUE:
                if key in self._data:
                    slug = slug + " " + self._data[key]
            slug = format_camel_case(slug).lower()
            self._attr_unique_id = (
                f"{self._inst.lower()}-{self.description.key}-{slugify(slug)}"
            )
        else:
            # build _attr_unique_id (no _uid)
            self._attr_unique_id = f"{self._inst.lower()}-{self.description.key}-{slugify(self.get_config_entry_id()).lower()}"

    @callback
    def _handle_coordinator_update(self) -> None:
        try:
            self._data = self.coordinator.data[self.description.data_path]
            if self._uid:
                self._data = self.coordinator.data[self.description.data_path][
                    self._uid
                ]
            super()._handle_coordinator_update()
        except KeyError:
            _LOGGER.debug("Error while updating entity %s", self.unique_id)
            pass

    @property
    def name(self) -> str:
        """Return the name for this entity."""
        if not self._uid:
            return f"{self.description.name}"

        if self.description.name:
            return f"{self._data[self.description.data_name]} {self.description.name}"

        return f"{self._data[self.description.data_name]}"

    @property
    def available(self) -> bool:
        """Return if controller is available."""
        return self.coordinator.connected()

    @property
    def device_info(self) -> DeviceInfo:
        """Return a description for device registry."""
        dev_connection = DOMAIN
        dev_connection_value = f"{self.coordinator.name}_{self.description.ha_group}"
        dev_group = self.description.ha_group
        if self.description.ha_group.startswith("data__"):
            dev_group = self.description.ha_group[6:]
            if dev_group in self._data:
                dev_group = self._data[dev_group]
                dev_connection_value = dev_group

        if self.description.ha_connection:
            dev_connection = self.description.ha_connection

        if self.description.ha_connection_value:
            dev_connection_value = self.description.ha_connection_value
            if dev_connection_value.startswith("data__"):
                dev_connection_value = dev_connection_value[6:]
                dev_connection_value = self._data[dev_connection_value]

        # handle multiple environments on server side
        if (
            self.description.ha_group == dev_group
            and dev_group == "local"
            and "Environment" in self._data
        ):
            dev_group = self._data["Environment"]
            dev_connection_value = f"{self.coordinator.name}_{dev_group}"

        # make connection unique accross configurations
        if self.coordinator:
            dev_connection_value += f"_{self.get_config_entry_id()}"

        if self.description.ha_group == "System":
            return DeviceInfo(
                connections={(dev_connection, f"{dev_connection_value}")},
                identifiers={(dev_connection, f"{dev_connection_value}")},
                name=f"{self._inst} {dev_group}",
                manufacturer=f"{self.manufacturer}",
                sw_version=f"{self.sw_version}",
                configuration_url=f"http{'s' if self.coordinator.config_entry.data[CONF_SSL] else ''}://{self.coordinator.config_entry.data[CONF_HOST]}",
            )
        else:
            return DeviceInfo(
                connections={(dev_connection, f"{dev_connection_value}")},
                default_name=f"{self._inst} {dev_group}",
                default_manufacturer=f"{self.manufacturer}",
            )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        attributes = super().extra_state_attributes
        for variable in self.description.data_attributes_list:
            if variable in self._data:
                if variable != CUSTOM_ATTRIBUTE_ARRAY:
                    attributes[format_attribute(variable)] = self._data[variable]
                else:
                    for custom_variable in self._data[variable]:
                        attributes[format_attribute(custom_variable)] = self._data[
                            variable
                        ][custom_variable]

        return attributes

    @property
    def icon(self) -> str:
        """Return the icon."""
        return self.description.icon

    async def start(self):
        """Run function."""
        raise NotImplementedError()

    async def stop(self):
        """Stop function."""
        raise NotImplementedError()

    async def restart(self):
        """Restart function."""
        raise NotImplementedError()

    async def reload(self):
        """Reload function."""
        raise NotImplementedError()

    async def snapshot(self):
        """Snapshot function."""
        raise NotImplementedError()

    def get_config_entry_id(self):
        if self.coordinator and self.coordinator.config_entry:
            return self.coordinator.config_entry.entry_id
        return self.hass.config_entries.async_get_entry(self.handler)
