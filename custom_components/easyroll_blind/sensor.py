import random
import logging

from homeassistant.const import (
    PERCENTAGE,
)
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.error("create sensor")
    new_devices = []
    for roller in hub.rollers.values():
        new_devices.append(MemorySensor(roller, 0, "M1"))
        new_devices.append(MemorySensor(roller, 1, "M2"))
        new_devices.append(MemorySensor(roller, 2, "M3"))
    if new_devices:
        async_add_devices(new_devices)

class SensorBase(Entity):
    """Base representation of a Hello World Sensor."""

    should_poll = False

    def __init__(self, roller):
        """Initialize the sensor."""
        self._roller = roller

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._roller.roller_id)},
            "name": self._roller._name,
            "sw_version": self._roller.firmware_version,
            "model": self._roller.model,
            "manufacturer": self._roller.hub.manufacturer,
        }

    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        #return self._roller.online and self._roller.hub.online
        return True

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._roller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._roller.remove_callback(self.async_write_ha_state)


class MemorySensor(SensorBase):
    """Representation of a Sensor."""

    def __init__(self, roller, order, name):
        """Initialize the sensor."""
        super().__init__(roller)
        self._state = random.randint(0, 100)
        self._name = name
        self._order = order

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._roller.roller_id}{self._name}_sensor"

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        return attr

    @property
    def state(self):
        """Return the state of the sensor."""
        self._state = self._roller.get_memory(self._order)
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return PERCENTAGE

    # The same of this entity, as displayed in the entity UI.
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name}"

