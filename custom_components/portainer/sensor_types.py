"""Definitions for TrueNAS sensor entities."""
from dataclasses import dataclass, field
from typing import List

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory


DEVICE_ATTRIBUTES_ENDPOINTS = [
    "Id",
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

@dataclass
class PortainerSensorEntityDescription(SensorEntityDescription):
    """Class describing portainer entities."""

    ha_group: str = ""
    ha_connection: str = ""
    ha_connection_value: str = ""
    data_path: str = ""
    data_attribute: str = ""
    data_name: str = ""
    data_uid: str = ""
    data_reference: str = ""
    data_attributes_list: List = field(default_factory=lambda: [])
    func: str = "PortainerSensor"


SENSOR_TYPES = {
    "endpoints": PortainerSensorEntityDescription(
        key="endpoints",
        name="",
        icon="mdi:text-box-multiple-outline",
        entity_category=None,
        ha_group="Endpoints",
        data_path="endpoints",
        data_attribute="RunningContainerCount",
        data_name="Name",
        data_uid="",
        data_reference="Id",
        data_attributes_list=DEVICE_ATTRIBUTES_ENDPOINTS,
    ),
}

SENSOR_SERVICES = [
]
