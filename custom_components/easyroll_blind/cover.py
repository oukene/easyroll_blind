"""Platform for sensor integration."""
from calendar import c
import logging
from optparse import Option
import threading
# These constants are relevant to the type of entity we are using.
# See below for how they are used.
from homeassistant.components.cover import (
    ATTR_POSITION,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    DEVICE_CLASS_BLIND,
    CoverEntity,
)

from typing import Optional
from .const import CONF_REFRESH_INTERVAL, DOMAIN, DEFAULT_REFRESH_INTERVAL

from homeassistant.components.cover import ENTITY_ID_FORMAT
from homeassistant.helpers.entity import async_generate_entity_id

_LOGGER = logging.getLogger(__name__)

# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add cover for passed config_entry in HA."""
    # The hub is loaded from the associated hass.data entry that was created in the
    # __init__.async_setup_entry function
    hub = hass.data[DOMAIN][config_entry.entry_id]

    # The next few lines find all of the entities that will need to be added
    # to HA. Note these are all added to a list, so async_add_devices can be
    # called just once.
    new_devices = []
    for roller in hub.rollers:
        new_devices.append(HelloWorldCover(hass, roller, 'Blind'))
        # new_devices.append(JogCommand(roller, 'job up/down'))
    # If we have any new devices, add them
    if new_devices:
        async_add_devices(new_devices)

    refresh_interval = config_entry.options.get(CONF_REFRESH_INTERVAL)
    if refresh_interval == None:
        refresh_interval = DEFAULT_REFRESH_INTERVAL

    for roller in hub.rollers:
        threading.Timer(DEFAULT_REFRESH_INTERVAL, roller.refresh).start()
        _LOGGER.debug("create refresh timer in cover")
# This entire class could be written to extend a base class to ensure common attributes
# are kept identical/in sync. It's broken apart here between the Cover and Sensors to
# be explicit about what is returned, and the comments outline where the overlap is.
class HelloWorldCover(CoverEntity):
    """Representation of a dummy Cover."""

    # Our dummy class is PUSH, so we tell HA that it should not be polled
    should_poll = False
    # The supported features of a cover are done using a bitmask. Using the constants
    # imported above, we can tell HA the features that are supported by this entity.
    # If the supported features were dynamic (ie: different depending on the external
    # device it connected to), then this should be function with an @property decorator.

    def __init__(self, hass, roller, name):
        """Initialize the sensor."""
        # Usual setup is done here. Callbacks are added in async_added_to_hass.
        self._roller = roller
        self._name = "{} {}".format(roller._name, name)
        self.hass = hass
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "{}_{}".format(roller.roller_id, name), hass=hass)
        self._device_class = DEVICE_CLASS_BLIND
        if roller._group_device == True:
            self._supported_features = SUPPORT_SET_POSITION | SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
        else:
            self._supported_features = SUPPORT_SET_POSITION | SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        # Importantly for a push integration, the module that will be getting updates
        # needs to notify HA of changes. The dummy device has a registercallback
        # method, so to this we add the 'self.async_write_ha_state' method, to be
        # called where ever there are changes.
        # The call back registration is done once this entity is registered with HA
        # (rather than in the __init__)
        self._roller.register_callback(self.async_write_ha_state)
        self._roller.set_cover_entity_id(self.entity_id)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._roller.remove_callback(self.async_write_ha_state)

    # A unique_id for this entity with in this domain. This means for example if you
    # have a sensor on this cover, you must ensure the value returned is unique,
    # which is done here by appending "_cover". For more information, see:
    # https://developers.home-assistant.io/docs/entity_registry_index/#unique-id-requirements
    # Note: This is NOT used to generate the user visible Entity ID used in automations.
    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._roller.roller_id}{self._name}_cover"

    # Information about the devices that is partially visible in the UI.
    # The most critical thing here is to give this entity a name so it is displayed
    # as a "device" in the HA UI. This name is used on the Devices overview table,
    # and the initial screen when the device is added (rather than the entity name
    # property below). You can then associate other Entities (eg: a battery
    # sensor) with this device, so it shows more like a unified element in the UI.
    # For example, an associated battery sensor will be displayed in the right most
    # column in the Configuration > Devices view for a device.
    # To associate an entity with this device, the device_info must also return an
    # identical "identifiers" attribute, but not return a name attribute.
    # See the sensors.py file for the corresponding example setup.
    # Additional meta data can also be returned here, including sw_version (displayed
    # as Firmware), model and manufacturer (displayed as <model> by <manufacturer>)
    # shown on the device info screen. The Manufacturer and model also have their
    # respective columns on the Devices overview table. Note: Many of these must be
    # set when the device is first added, and they are not always automatically
    # refreshed by HA from it's internal cache.
    # For more information see:
    # https://developers.home-assistant.io/docs/device_registry_index/#device-properties
    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._roller._name)},
            # If desired, the name for the device could be different to the entity
            "name": self._roller._name,
            "sw_version": self._roller.firmware_version,
            "model": self._roller.model,
            "manufacturer": self._roller.hub.manufacturer,
        }

    # This is the name for this *entity*, the "name" attribute from "device_info"
    # is used as the device name for device screens in the UI. This name is used on
    # entity screens, and used to build the Entity ID that's used is automations etc.
    @property
    def name(self):
        """Return the name of the roller."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._roller._current_position

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        #return self._roller.online and self._roller.hub.online
        return True

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def supported_features(self) -> Optional[int]:
        return self._supported_features
    # The follwing properties are how HA knows the current state of the device.
    # These must return a value from memory, not make a live query to the device/hub
    # etc when called (hence they are properties). For a push based integration,
    # HA is notified of changes via the async_write_ha_state call. See the __init__
    # method for hos this is implemented in this example.
    # The properties that are expected for a cover are based on the supported_features
    # property of the object. In the case of a cover, see the following for more
    # details: https://developers.home-assistant.io/docs/core/entity/cover/
    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        if self._roller._group_device == True:
            return 50
        return self._roller._current_position

    @property
    def is_closed(self):
        """Return if the cover is closed, same as position 0."""
        return self._roller._current_position == 0

    @property
    def is_opening(self):
        return self._roller._state == "opening"

    @property
    def is_closing(self):
        return self._roller._state == "closing"

    #@property
    #def is_closing(self):
    #    """Return if the cover is closing or not."""
    #    return self._roller._target_position < self._roller._current_position

    #@property
    #def is_opening(self):
    #    """Return if the cover is opening or not."""
    #    return self._roller._target_position > self._roller._current_position

    # These methods allow HA to tell the actual device what to do. In this case, move
    # the cover to the desired position, or open and close it all the way.
    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._roller.set_position(100)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self._roller.set_position(0)

    async def async_set_cover_position(self, **kwargs):
        """Close the cover."""
        await self._roller.set_position(kwargs[ATTR_POSITION])

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._roller.set_stop()
