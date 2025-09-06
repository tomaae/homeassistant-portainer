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
    CUSTOM_ATTRIBUTE_ARRAY,
    DEVICE_ATTRIBUTES_CONTAINERS_UNIQUE,
    DOMAIN,
)
from .coordinator import PortainerCoordinator
from .entity_factory import EntityFactory
from .helper import format_attribute, format_camel_case

_LOGGER = getLogger(__name__)


def create_sensors(coordinator, descriptions, dispatcher):
    """Create Portainer sensor entities using EntityFactory."""
    factory = EntityFactory(coordinator, dispatcher)
    return factory.create_sensors(descriptions)


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

        # Always ensure we have a valid unique_id
        if self._uid:
            self._data = coordinator.data[self.description.data_path][self._uid]

            # For endpoints, use endpoint-specific attributes for unique ID
            if self.description.data_path == "endpoints":
                # Use endpoint ID, name, and config entry ID for uniqueness
                endpoint_id = self._data.get("Id", self._uid)
                endpoint_name = self._data.get("Name", "unknown")
                config_entry_id = self.get_config_entry_id()

                # Create a safe slug without using slugify to preserve our underscore separators
                # Replace any problematic characters but keep underscores
                safe_endpoint_id = str(endpoint_id).replace(" ", "-").replace("/", "-")
                safe_endpoint_name = (
                    str(endpoint_name).replace(" ", "-").replace("/", "-").lower()
                )
                safe_config_id = (
                    str(config_entry_id).replace(" ", "-").replace("/", "-")
                )

                slug = f"{safe_endpoint_id}_{safe_endpoint_name}_{safe_config_id}"
                self._attr_unique_id = f"{self._inst.lower().replace(' ', '-')}-{self.description.key}-{slug}"
                _LOGGER.debug(
                    "Created endpoint unique_id: %s for endpoint %s (ID: %s, config_entry: %s)",
                    self._attr_unique_id,
                    endpoint_name,
                    endpoint_id,
                    config_entry_id,
                )
            else:
                # For containers and other entities, use the original logic
                slug = ""
                for key in DEVICE_ATTRIBUTES_CONTAINERS_UNIQUE:
                    if key in self._data:
                        slug = slug + " " + self._data[key]
                slug = format_camel_case(slug).lower()
                self._attr_unique_id = (
                    f"{self._inst.lower()}-{self.description.key}-{slugify(slug)}"
                )
                _LOGGER.debug(
                    "Created unique_id with uid: %s for %s",
                    self._attr_unique_id,
                    self.description.key,
                )
        else:
            # build _attr_unique_id (no _uid)
            config_entry_id = self.get_config_entry_id()
            self._attr_unique_id = f"{self._inst.lower()}-{self.description.key}-{slugify(config_entry_id).lower()}"
            _LOGGER.debug(
                "Created unique_id without uid: %s for %s",
                self._attr_unique_id,
                self.description.key,
            )

        # Safety check: Ensure unique_id is never None or empty
        if not self._attr_unique_id:
            fallback_id = (
                f"fallback-{getattr(description, 'key', 'unknown')}-{id(self)}"
            )
            _LOGGER.error(
                "unique_id was None or empty for entity %s, using fallback: %s",
                getattr(description, "key", "unknown"),
                fallback_id,
            )
            self._attr_unique_id = fallback_id

        # Final validation
        _LOGGER.debug(
            "Entity initialized: key=%s, unique_id=%s, name=%s",
            getattr(description, "key", "unknown"),
            self._attr_unique_id,
            self.name,
        )

        # Additional safety check: ensure name is never empty
        entity_name = self.name
        if not entity_name or entity_name.strip() == "":
            _LOGGER.error(
                "Entity name is empty for %s, this will cause entity_id issues",
                getattr(description, "key", "unknown"),
            )

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

    @property
    def name(self) -> str:
        """Return the name for this entity."""
        try:
            if not self._uid:
                # Ensure description.name is not None
                desc_name = getattr(self.description, "name", None)
                if desc_name:
                    result = str(desc_name)
                else:
                    result = f"Portainer {getattr(self.description, 'key', 'Entity')}"
                _LOGGER.debug("Entity name (no uid): %s", result)
                return result

            # With uid - ensure data_name exists and is not None
            if not hasattr(self, "_data") or self._data is None:
                _LOGGER.warning(
                    "_data not available yet for entity %s",
                    getattr(self.description, "key", "unknown"),
                )
                return f"Container {self._uid}"

            data_name_key = getattr(self.description, "data_name", None)
            if (
                data_name_key
                and data_name_key in self._data
                and self._data[data_name_key]
            ):
                base_name = str(self._data[data_name_key])
            else:
                base_name = f"Container {self._uid}"

            desc_name = getattr(self.description, "name", None)
            if desc_name:
                result = f"{base_name} {desc_name}"
            else:
                result = base_name

            _LOGGER.debug("Entity name (with uid %s): %s", self._uid, result)
        except (AttributeError, KeyError, TypeError) as e:
            _LOGGER.error(
                "Error getting entity name for %s: %s",
                getattr(self.description, "key", "unknown"),
                e,
            )
            result = f"Portainer {getattr(self.description, 'key', 'Entity')}"
            if self._uid:
                result += f" {self._uid}"
        else:
            return result

        return result

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

    @property
    def unique_id(self) -> str:
        """Return unique ID for this entity."""
        if not self._attr_unique_id:
            _LOGGER.error(
                "unique_id is None or empty for entity %s",
                getattr(self.description, "key", "unknown"),
            )
            return f"fallback-{getattr(self.description, 'key', 'unknown')}"
        return self._attr_unique_id

    async def start(self):
        """Run function."""
        raise NotImplementedError

    async def stop(self):
        """Stop function."""
        raise NotImplementedError

    async def restart(self):
        """Restart function."""
        raise NotImplementedError

    async def reload(self):
        """Reload function."""
        raise NotImplementedError

    async def snapshot(self):
        """Snapshot function."""
        raise NotImplementedError

    def get_config_entry_id(self):
        """Get the config entry ID."""
        if self.coordinator and self.coordinator.config_entry:
            return self.coordinator.config_entry.entry_id
        return "unknown"
