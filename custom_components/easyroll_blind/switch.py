import logging

from homeassistant.components.switch import (
    SwitchEntity,
)
from homeassistant.components.switch import ENTITY_ID_FORMAT
from homeassistant.helpers.entity import async_generate_entity_id
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    use_setup_mode = bool(config_entry.options.get(CONF_USE_SETUP_MODE))
    if use_setup_mode == None:
        use_setup_mode = False

    new_devices = []
    for roller in hub.rollers:
        new_devices.append(CommandSwitch(hass, roller, SNAME_MOVE_M1))
        new_devices.append(CommandSwitch(hass, roller, SNAME_MOVE_M2))
        new_devices.append(CommandSwitch(hass, roller, SNAME_MOVE_M3))
        if roller._group_device == False:
            new_devices.append(CommandSwitch(hass, roller, SNAME_JOG_UP))
            new_devices.append(CommandSwitch(hass, roller, SNAME_JOG_DOWN))
            new_devices.append(CommandSwitch(hass, roller, SNAME_FIND_ME))
        new_devices.append(CommandSwitch(hass, roller, SNAME_AUTO_LEVELING))

        if use_setup_mode == True and roller._group_device == False:
            new_devices.append(CommandSwitch(hass, roller, SNAME_SAVE_TOP))
            new_devices.append(CommandSwitch(hass, roller, SNAME_SAVE_BOTTOM))
            new_devices.append(CommandSwitch(hass, roller, SNAME_SAVE_M1))
            new_devices.append(CommandSwitch(hass, roller, SNAME_SAVE_M2))
            new_devices.append(CommandSwitch(hass, roller, SNAME_SAVE_M3))
            new_devices.append(CommandSwitch(hass, roller, SNAME_FORCE_UP))
            new_devices.append(CommandSwitch(hass, roller, SNAME_FORCE_DOWN))
    if new_devices:
        async_add_devices(new_devices)


class SwitchBase(SwitchEntity):
    """Base representation of a Hello World Sensor."""

    should_poll = False

    def __init__(self, roller):
        """Initialize the sensor."""
        self._roller = roller
        self._state = "off"

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._roller._name)},
            "name": self._roller._name,
            "sw_version": self._roller.firmware_version,
            "model": self._roller.model,
            "manufacturer": self._roller.hub.manufacturer,
        }

    @property
    def is_on(self):
        return self._state

    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return True

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._roller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._roller.remove_callback(self.async_write_ha_state)


class CommandSwitch(SwitchBase):
    """Representation of a Sensor."""

    # The class of this device. Note the value should come from the homeassistant.const
    # module. More information on the available devices classes can be seen here:
    # https://developers.home-assistant.io/docs/core/entity/sensor
    # device_class = DEVICE_CLASS_BATTERY

    def __init__(self, hass, roller, name):
        """Initialize the sensor."""
        super().__init__(roller)
        self._name = name
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, "{}_{}".format(roller.roller_id, name), hass=hass)
        self.functions = {
            SNAME_MOVE_M1: self._roller.move_m1,
            SNAME_MOVE_M2: self._roller.move_m2,
            SNAME_MOVE_M3: self._roller.move_m3,
            SNAME_JOG_UP: self._roller.jog_up,
            SNAME_JOG_DOWN: self._roller.jog_down,
            SNAME_FIND_ME: self._roller.find_me,
            SNAME_AUTO_LEVELING: self._roller.auto_leveling,
            SNAME_SAVE_TOP: self._roller.save_top,
            SNAME_SAVE_BOTTOM: self._roller.save_bottom,
            SNAME_SAVE_M1: self._roller.save_m1,
            SNAME_SAVE_M2: self._roller.save_m2,
            SNAME_SAVE_M3: self._roller.save_m3,
            SNAME_FORCE_UP: self._roller.force_up,
            SNAME_FORCE_DOWN: self._roller.force_down,
        }

    # As per the sensor, this must be a unique value within this domain. This is done
    # by using the device ID, and appending "_battery"
    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._roller.roller_id}_{self._name}"

    # This property can return additional metadata about this device. Here it's
    # returning the voltage of the battery. The actual percentage is returned in
    # the state property below. These values are displayed in the entity details
    # screen at the bottom below the history graph.
    # A number of defined attributes are available, see the homeassistant.const module
    # for constants starting with ATTR_*.
    # Again, if these values change, the async_write_ha_state method should be called.
    # in this implementation, these values are assumed to be static.
    # Note this functionality to display addition data on an entity appears to be
    # exclusive to sensors. This information is not shown in the UI for a cover.
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        return attr

    # The value of this sensor. As this is a DEVICE_CLASS_BATTERY, this value must be
    # the battery level as a percentage (between 0 and 100)
    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    # The unit of measurement for this entity. As it's a DEVICE_CLASS_BATTERY, this
    # should be PERCENTAGE. A number of units are supported by HA, for some
    # examples, see:
    # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes

    # The same of this entity, as displayed in the entity UI.
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name}"

    async def async_turn_on(self, **kargs):
        """turn the entity"""
        self._roller.moving = 0
        func = self.functions[self._name]
        await func()
        self._state = "off"

        #self._roller.set_memory(self._order)
        #self._state = "off"

    async def async_turn_off(self, **kargs):
        """turn the entity"""

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
