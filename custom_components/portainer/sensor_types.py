"""Definitions for sensor entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from homeassistant.components.sensor import SensorEntityDescription

from .const import CUSTOM_ATTRIBUTE_ARRAY

DEVICE_ATTRIBUTES_ENDPOINTS = [
    "Type",
    "Status",
    "DockerVersion",
    "Swarm",
    "TotalCPU",
    "TotalMemory",
    "RunningContainerCount",
    "StoppedContainerCount",
    "HealthyContainerCount",
    "UnhealthyContainerCount",
    "VolumeCount",
    "ImageCount",
    "ServiceCount",
    "StackCount",
]

DEVICE_ATTRIBUTES_CONTAINERS = [
    "Image",
    "ImageID",
    "Network",
    "Compose_Stack",
    "Compose_Service",
    "Compose_Version",
    "Environment",
    # add all attributes form CUSTOM_ATTRIBUTE_ARRAY
    CUSTOM_ATTRIBUTE_ARRAY,
]


@dataclass
class PortainerSensorEntityDescription(SensorEntityDescription):
    """Class describing portainer entities."""

    key: str | None = None
    name: str | None = None
    icon: str | None = None
    entity_category: str | None = None
    ha_group: str | None = None
    ha_connection: str | None = None
    ha_connection_value: str | None = None
    data_path: str | None = None
    data_attribute: str | None = None
    data_name: str | None = None
    data_uid: str | None = None
    data_reference: str | None = None
    data_attributes_list: List = field(default_factory=lambda: [])
    func: str = "PortainerSensor"


SENSOR_TYPES: tuple[PortainerSensorEntityDescription, ...] = (
    PortainerSensorEntityDescription(
        key="endpoints",
        name="",
        icon="mdi:truck-cargo-container",
        entity_category=None,
        ha_group="Endpoints",
        data_path="endpoints",
        data_attribute="RunningContainerCount",
        data_name="Name",
        data_uid="",
        data_reference="Name",
        data_attributes_list=DEVICE_ATTRIBUTES_ENDPOINTS,
        func="EndpointSensor",
    ),
    PortainerSensorEntityDescription(
        key="containers",
        name="",
        icon="mdi:train-car-container",
        entity_category=None,
        ha_group="data__EndpointId",
        data_path="containers",
        data_attribute="State",
        data_name="Name",
        data_uid="",
        data_reference="Id",
        data_attributes_list=DEVICE_ATTRIBUTES_CONTAINERS,
        func="ContainerSensor",
    ),
    PortainerSensorEntityDescription(
        key="update_check_status",
        name="Container Update Check",
        icon="mdi:clock-outline",
        entity_category="diagnostic",
        ha_group="System",  # Create special system device for update checks
        data_path="system",  # Use system data path
        data_attribute="next_update_check",  # Correct attribute name from coordinator
        data_name="",
        data_uid="",
        data_reference="",  # No reference = single entity
        data_attributes_list=[],
        func="UpdateCheckSensor",
    ),
)

SENSOR_SERVICES: list[PortainerSensorEntityDescription] = []
