"""A demonstration 'hub' that connects several devices."""
# In a real implementation, this would be in an external library that's on PyPI.
# The PyPI package needs to be included in the `requirements` section of manifest.json
# See https://developers.home-assistant.io/docs/creating_integration_manifest
# for more information.
# This dummy hub always returns 3 rollers.
import asyncio
import random
import logging
import aiohttp
import threading
import json

import requests
from timeit import default_timer as dt

from homeassistant.components.cover import DOMAIN, SUPPORT_SET_POSITION

from custom_components.easyroll_blind.const import DEFAULT_CMD_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)

class Hub:
    """Dummy hub for Hello World example."""

    manufacturer = "Demonstration Corp"
    
    def __init__(self, hass, area_name, setup_mode, refresh_interval):
        """Init dummy hub."""
        self._hass = hass
        self._area_name = area_name
        self._id = area_name
        self._setup_mode = setup_mode
        self._refresh_interval = refresh_interval

        self.rollers = [
            #Roller(f"{self._id}_1", f"{self._name} 1", self),
            #Roller(f"{self._id}_2", f"{self._name} 2", self),
            #Roller(f"{self._id}_3", f"{self._name} 3", self),
        ]
        self.online = True

    async def leveling(self, position):
        for roller in self.rollers:
            await roller.set_position(position)

    @property
    def hub_id(self):
        """ID for dummy hub."""
        return self._id

    async def test_connection(self):
        """Test connectivity to the Dummy hub is OK."""
        await asyncio.sleep(1)
        return True


class Roller:
    """Dummy roller (device for HA) for Hello World example."""

    def __init__(self, name, local_ip, hub):
        """Init dummy roller."""
        self._id = name + "_" + local_ip
        self.hub = hub
        self._setup_mode = hub._setup_mode
        self._refresh_interval = hub._refresh_interval
        self._name = local_ip
        self._local_ip = local_ip
        self._callbacks = set()
        self._loop = asyncio.get_event_loop()
        self._target_position = 0
        self._current_position = 0
        self._cmd_refresh_timer = None
        # Reports if the roller is moving up or down.
        # >0 is up, <0 is down. This very much just for demonstration.
        self.moving = 0
        self._memory = [None, None, None]

        # Some static information about this device
        self.firmware_version = "0.0.1"
        self.model = "Test Device"

        self._loop.create_task(self.easyroll_command("lstinfo", ""))

    @property
    def roller_id(self):
        """Return ID for roller."""
        return self._id
    
    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._id)}}

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name}"

    @property
    def position(self):
        """Return position for roller."""
        return self._current_position

    def get_memory(self, order):
        # _LOGGER.error("get memory memory : %s", self._memory[order])
        return self._memory[order]

    def set_memory(self, order):
        _LOGGER.error("set memory current position : %s", self._current_position)
        self._memory[order] = self._current_position
        self._loop.create_task(self.delayed_update())

    async def set_stop(self):
        #self.set_position(self._current_position)
        #await self.publish_updates(self._current_position)
        await self._loop.create_task(self.easyroll_command("general", "SS"))
        await self._loop.create_task(self.easyroll_command("lstinfo", ""))
        #self._target_position = self._current_position
        #await self._loop.create_task(self.easyroll_command("lstinfo", ""))

    async def set_position(self, position):
        """
        Set dummy cover to the given position.

        State is announced a random number of seconds later.
        """
        self._target_position = position
        self.moving = 1
        # Update the moving status, and broadcast the update
        #self.moving = position - 50
        # self._current_position = position
        self._loop.create_task(self.easyroll_command("level", str(100 - position)))
        threading.Timer(DEFAULT_CMD_REFRESH_INTERVAL, self.cmd_refresh).start()
        #self._loop.create_task(self.easyroll_command("lstinfo", ""))

    async def move_m1(self):
        _LOGGER.info("call move m1")
        self._loop.create_task(self.easyroll_command("general", "M1"))
        
    async def move_m2(self):
        _LOGGER.info("call move m2")
        self._loop.create_task(self.easyroll_command("general", "M2"))

    async def move_m3(self):
        _LOGGER.info("call move m3")
        self._loop.create_task(self.easyroll_command("general", "M3"))

    async def jog_up(self):
        _LOGGER.info("call jog up")
        if self._setup_mode == True:
            self._loop.create_task(self.easyroll_command("force", "FSU"))
        else:
            self._loop.create_task(self.easyroll_command("general", "SU"))

        self._loop.create_task(self.easyroll_command("lstinfo", ""))

    async def jog_down(self):
        _LOGGER.info("call jog down")
        if self._setup_mode == True:
            self._loop.create_task(self.easyroll_command("force", "FSD"))
        else:
            self._loop.create_task(self.easyroll_command("general", "SD"))

        self._loop.create_task(self.easyroll_command("lstinfo", ""))
    
    async def find_me(self):
        _LOGGER.info("find me")
        if self._current_position <= 0:
            self._loop.create_task(self.easyroll_command("general", "SU"))
            self._loop.create_task(self.easyroll_command("general", "SD"))
        elif self._current_position >= 100:
            self._loop.create_task(self.easyroll_command("general", "SD"))
            self._loop.create_task(self.easyroll_command("general", "SU"))

        self._loop.create_task(self.easyroll_command("lstinfo", ""))


    async def auto_leveling(self):
        _LOGGER.info("auto leveling") 
        await self.hub.leveling(self._current_position)

    async def save_top(self):
        _LOGGER.info("save top") 
        self._loop.create_task(self.easyroll_command("save", "ST"))

    async def save_bottom(self):
        _LOGGER.info("save bottom") 
        self._loop.create_task(self.easyroll_command("save", "SB"))
        
    async def save_m1(self):
        _LOGGER.info("save m1") 
        self._loop.create_task(self.easyroll_command("save", "SM1"))

    async def save_m2(self):
        _LOGGER.info("save m2") 
        self._loop.create_task(self.easyroll_command("save", "SM2"))

    async def save_m3(self):
        _LOGGER.info("save m3") 
        self._loop.create_task(self.easyroll_command("save", "SM3"))

    async def force_up(self):
        _LOGGER.info("force up") 
        self._loop.create_task(self.easyroll_command("force", "FTU"))

        self._loop.create_task(self.easyroll_command("lstinfo", ""))

    async def force_down(self):
        self._loop.create_task(self.easyroll_command("force", "FBD"))

        self._loop.create_task(self.easyroll_command("lstinfo", ""))


    async def delayed_update(self):
        """Publish updates, with a random delay to emulate interaction with device."""
        await asyncio.sleep(random.randint(1, 10))
        self.moving = 0
        await self.publish_updates()

    def register_callback(self, callback):
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    # In a real implementation, this library would call it's call backs when it was
    # notified of any state changeds for the relevant device.
    async def publish_updates(self, position):
        """Schedule call all registered callbacks."""
        self._current_position = 100 - position

        if self._target_position == self._current_position:
            self.moving = 0
        #if self._target_position == -1:
        #    self._target_position = self._current_position
        #self._current_position = self._target_position
        #if self._target_position == self._current_position:
        #    _LOGGER.error("set moving state zero")
        #    self.moving = 0

        for callback in self._callbacks:
            callback()

    def refresh(self):
        _LOGGER.debug("refresh!!")
        self._loop.create_task(self.easyroll_command("lstinfo", ""))
        threading.Timer(self._refresh_interval, self.refresh).start()
        #await threading.Timer(3, self.refresh).start()

    def cmd_refresh(self):
        _LOGGER.debug("cmd refresh")
        self._loop.create_task(self.easyroll_command("lstinfo", ""))
        if self.moving != 0:
            threading.Timer(DEFAULT_CMD_REFRESH_INTERVAL, self.cmd_refresh).start()
            

    async def easyroll_command(self, mode, command):
        try:
            if mode == "lstinfo":
                async with aiohttp.ClientSession() as session:
                    _LOGGER.error("url : " + self._local_ip)
                    async with session.get("http://" + self._local_ip + "/" + mode) as response:
                        raw_data = await response.read()
                        data = json.loads(raw_data)
                        _LOGGER.error("device position : " + str(data["position"]) + ", set position : " + str(self._current_position))
                        await self.publish_updates(round(float(data["position"])))

            else:
                async with aiohttp.ClientSession() as session:
                    _LOGGER.error("url : " + self._local_ip)
                    async with session.post("http://" + self._local_ip + "/action", json = {"mode": mode, "command": command  }) as response:
                        data = await response.json()
                        #_LOGGER.error("response.data() : " + data)
        except Exception as e:
            _LOGGER.error("command timeout : " + str(e))

    '''
    @property
    def online(self):
        """Roller is online."""
        # The dummy roller is offline about 10% of the time. Returns True if online,
        # False if offline.
        return random.random() > 0.1

    @property
    def battery_level(self):
        """Battery level as a percentage."""
        return random.randint(0, 100)

    @property
    def battery_voltage(self):
        """Return a random voltage roughly that of a 12v battery."""
        return round(random.random() * 3 + 10, 2)

    @property
    def illuminance(self):
        """Return a sample illuminance in lux."""
        return random.randint(0, 500)
    '''
