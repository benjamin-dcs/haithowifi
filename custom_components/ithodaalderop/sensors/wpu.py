"""Sensor class for handling WPU sensors."""

import copy
import json

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from ..const import MQTT_BASETOPIC, MQTT_STATETOPIC, WPU_STATUS
from ..definitions.wpu import (
    WPU_BINARY_SENSORS,
    WPU_ERROR_CODE_BYTE_TEMPLATE,
    WPU_SENSORS,
    WPU_THERMOSTAT,
)
from .base import IthoBaseSensor, IthoBinarySensor


def get_wpu_binary_sensors(config_entry: ConfigEntry):
    """Create binary sensors for WPU."""
    sensors = []
    topic = f"{MQTT_BASETOPIC["wpu"]}/{MQTT_STATETOPIC["wpu"]}"
    for description in WPU_BINARY_SENSORS:
        description.topic = topic
        sensors.append(IthoBinarySensor(description, config_entry))

    return sensors


def get_wpu_sensors(config_entry: ConfigEntry):
    """Create sensors for WPU."""
    sensors = []
    topic = f"{MQTT_BASETOPIC["wpu"]}/{MQTT_STATETOPIC["wpu"]}"
    for x in range(6):
        x = str(x)
        description = copy.deepcopy(WPU_ERROR_CODE_BYTE_TEMPLATE)
        description.topic = topic
        description.json_field = description.json_field + x
        description.translation_placeholders = {"num": x}
        description.unique_id = description.unique_id_template.replace("x", x)
        sensors.append(IthoSensorWPU(description, config_entry))

    for description in WPU_SENSORS:
        description.topic = topic
        sensors.append(IthoSensorWPU(description, config_entry))

    return sensors


def get_wpu_thermostat(config_entry: ConfigEntry):
    """Create virtual thermostat for WPU."""
    topic = f"{MQTT_BASETOPIC["wpu"]}/{MQTT_STATETOPIC["wpu"]}"

    description = WPU_THERMOSTAT
    description.topic = topic

    return [IthoThermostatWPU(description, config_entry)]


class IthoSensorWPU(IthoBaseSensor):
    """Representation of Itho add-on sensor for WPU that is updated via MQTT."""

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT events."""

        @callback
        def message_received(message):
            """Handle new MQTT messages."""
            payload = json.loads(message.payload)
            json_field = self.entity_description.json_field
            if json_field not in payload:
                value = None
            else:
                value = payload[json_field]
                if json_field == "Status":
                    self._extra_state_attributes = {
                        "Code": value,
                    }
                    value = WPU_STATUS.get(int(value), "Unknown status")

            self._attr_native_value = value
            self.async_write_ha_state()

        await mqtt.async_subscribe(
            self.hass, self.entity_description.topic, message_received, 1
        )


class IthoThermostatWPU(IthoBaseSensor):
    """Representation of Itho add-on sensor for WPU that is updated via MQTT."""

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT events."""

        @callback
        def message_received(message):
            """Handle new MQTT messages."""
            payload = json.loads(message.payload)

            if payload.get("ECO selected on thermostat", 0) == 1:
                value = "Eco"
            if payload.get("Comfort selected on thermostat", 0) == 1:
                value = "Comfort"
            if payload.get("Boiler boost from thermostat", 0) == 1:
                value = "Boost"
            if payload.get("Boiler blocked from thermostat", 0) == 1:
                value = "Off"
            if payload.get("Venting from thermostat", 0) == 1:
                value = "Venting"

            self._attr_native_value = value
            self.async_write_ha_state()

        await mqtt.async_subscribe(
            self.hass, self.entity_description.topic, message_received, 1
        )
