"""Portainer sensor platform."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import (
    entity_platform as ep,
)
from homeassistant.helpers.typing import StateType

from custom_components.portainer.const import DOMAIN

from .coordinator import PortainerCoordinator
from .entity import PortainerEntity, async_create_sensors
from .sensor_types import SENSOR_SERVICES, SENSOR_TYPES  # noqa: F401


# ---------------------------
#   async_setup_entry
# ---------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities_callback: AddEntitiesCallback,
):
    """Set up the sensor platform for a specific configuration entry."""

    # Set up entry for portainer component.
    dispatcher = {
        "PortainerSensor": PortainerSensor,
        "EndpointSensor": EndpointSensor,
        "ContainerSensor": ContainerSensor,
    }

    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    platform = ep.async_get_current_platform()

    services = platform.platform.SENSOR_SERVICES
    descriptions = platform.platform.SENSOR_TYPES

    for service in services:
        if service[0] not in hass.services.async_services().get(DOMAIN, {}):
            platform.async_register_entity_service(service[0], service[1], service[2])

    entities = await async_create_sensors(coordinator, descriptions, dispatcher)
    async_add_entities_callback(entities, update_before_add=True)

    @callback
    async def async_update_controller(coordinator):
        """Update entities when data changes."""
        platform = ep.async_get_current_platform()
        existing_entities = platform.entities
        new_entities = []
        entities = await async_create_sensors(coordinator, descriptions, dispatcher)
        for entity in entities:
            unique_id = entity.unique_id
            if unique_id in [e.unique_id for e in existing_entities.values()]:
                continue

            new_entities.append(entity)

        if new_entities:
            async_add_entities_callback(new_entities, update_before_add=True)

    # Connect listener per config_entry
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{config_entry.entry_id}_update", async_update_controller
        )
    )


# ---------------------------
#   PortainerSensor
# ---------------------------
class PortainerSensor(PortainerEntity, SensorEntity):
    """Define an Portainer sensor."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self._attr_suggested_unit_of_measurement = (
            self.description.suggested_unit_of_measurement
        )

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self._data[self.description.data_attribute]

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit the value is expressed in."""
        if self.description.native_unit_of_measurement:
            if self.description.native_unit_of_measurement.startswith("data__"):
                uom = self.description.native_unit_of_measurement[6:]
                if uom in self._data:
                    return self._data[uom]

            return self.description.native_unit_of_measurement


# ---------------------------
#   EndpointsSensor
# ---------------------------
class EndpointSensor(PortainerSensor):
    """Define an Portainer sensor."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self.manufacturer = "Portainer"


# ---------------------------
#   ContainerSensor
# ---------------------------
class ContainerSensor(PortainerSensor):
    """Define an Portainer sensor."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self.sw_version = self.coordinator.data["endpoints"][self._data["EndpointId"]][
            "DockerVersion"
        ]
        if self.description.ha_group.startswith("data__"):
            dev_group = self.description.ha_group[6:]
            if (
                dev_group in self._data
                and self._data[dev_group] in self.coordinator.data["endpoints"]
            ):
                self.description.ha_group = self.coordinator.data["endpoints"][
                    self._data[dev_group]
                ]["Name"]
