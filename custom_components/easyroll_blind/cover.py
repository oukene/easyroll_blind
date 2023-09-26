"""Platform for sensor integration."""
from calendar import c
import logging
import threading
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

async def async_setup_entry(hass, config_entry, async_add_devices):
    hub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for roller in hub.rollers:
        new_devices.append(HelloWorldCover(hass, roller, 'Blind'))
        # new_devices.append(JogCommand(roller, 'job up/down'))
    if new_devices:
        async_add_devices(new_devices)

    refresh_interval = config_entry.options.get(CONF_REFRESH_INTERVAL)
    if refresh_interval == None:
        refresh_interval = DEFAULT_REFRESH_INTERVAL

    for roller in hub.rollers:
        threading.Timer(DEFAULT_REFRESH_INTERVAL, roller.refresh).start()
        _LOGGER.debug("create refresh timer in cover")

class HelloWorldCover(CoverEntity):
    """Representation of a dummy Cover."""

    should_poll = True

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
        self._roller.register_callback(self.async_write_ha_state)
        self._roller.set_cover_entity_id(self.entity_id)

    async def async_will_remove_from_hass(self):
        self._roller.remove_callback(self.async_write_ha_state)

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._roller.roller_id}{self._name}_cover"

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
    def name(self):
        """Return the name of the roller."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._roller._current_position

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
