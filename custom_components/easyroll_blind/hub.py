"""A demonstration 'hub' that connects several devices."""
# In a real implementation, this would be in an external library that's on PyPI.
# The PyPI package needs to be included in the `requirements` section of manifest.json
# See https://developers.home-assistant.io/docs/creating_integration_manifest
# for more information.
# This dummy hub always returns 3 rollers.
import asyncio
from email import message
from io import BytesIO
import random
import logging
from turtle import position
import aiohttp
import threading
import json
import time

from urllib.parse import parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from timeit import default_timer as dt

from homeassistant.components.cover import DOMAIN, SUPPORT_SET_POSITION
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE

from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.helpers.entity import async_generate_entity_id
from rfc3986 import is_valid_uri
from custom_components.easyroll_blind.__init__ import extract_ip
import custom_components.easyroll_blind.const as const
from custom_components.easyroll_blind.const import DEFAULT_CMD_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL, DEFAULT_SEND_PLATFORM_INFO_INTERVAL, VERSION

_LOGGER = logging.getLogger(__name__)

def _is_valid_state(state) -> bool:
    return state != STATE_UNKNOWN and state != STATE_UNAVAILABLE and state != None

class MyHttpServer(HTTPServer):
    def __init__(self, hub, *args, **kargs):
        HTTPServer.__init__(self, *args, **kargs)
        self.hub = hub

class MyHTTPRequestHandler( BaseHTTPRequestHandler ):
    #def do_GET(self):
    #    if self.path == "/push-state":
    #        _LOGGER.debug( 'get방식 요청' )

    def do_POST(self):
        
        request = urlparse(self.path)
        if request.path == "/push-state":
            
            content_length = int(self.headers.get('Content-Length'))
            
            post_body = self.rfile.read(content_length)
            body = parse_qs(post_body.decode("utf-8"))
            
            if "position" in body:
                _LOGGER.debug(body["position"][0])
                
                try:
                    #self.server.hub.rollers[self.client_address[0]]._current_position = int(body["position"][0])
                    self.server.hub.rollers[self.client_address[0]]._loop.create_task(self.server.hub.rollers[self.client_address[0]].publish_updates(int(body["position"][0])))
                    
                    message = {"result": "success"}

                    self.send_response(200)
                    self.send_header("Content-Type","application/json;charset=UTF-8")
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps(message), "utf-8"))
                    
                except Exception:
                    """"""
                
class Hub:
    """Dummy hub for Hello World example."""
    manufacturer = const.DOMAIN
    
    def __init__(self, hass, area_name, setup_mode, refresh_interval, add_group_device):
        """Init dummy hub."""
        self._hass = hass
        self._area_name = area_name
        self._id = area_name
        self._setup_mode = setup_mode
        self._refresh_interval = refresh_interval
        self.hass = hass
        self._add_group_device = add_group_device

        self.rollers = {}
            #Roller(f"{self._id}_1", f"{self._name} 1", self),
            #Roller(f"{self._id}_2", f"{self._name} 2", self),
            #Roller(f"{self._id}_3", f"{self._name} 3", self),
        self.online = True
        threading.Timer(0, self.start_server).start()

    def start_server(self):
        httpd = MyHttpServer(self, ("0.0.0.0", 20319), MyHTTPRequestHandler)
        _LOGGER.debug("start http server")
        httpd.serve_forever()

    async def leveling(self, position):
        for roller in self.rollers:
            if roller._group_device == True:
                continue
            entity_state = self.hass.states.get(roller._cover_entity_id)
            if _is_valid_state(entity_state) == False:
                continue
            await roller.set_position(position)

    async def leveling_group(self):
        _LOGGER.debug("call set level group")
        _position = None
        for roller in self.rollers:
            if roller._group_device == True:
                continue

            entity_state = self.hass.states.get(roller._cover_entity_id)
            if _is_valid_state(entity_state) == False:
                continue

            _position = roller._current_position
            _LOGGER.debug("set leveling position : " + str(_position))
            break
        
        await self.leveling(_position)


    async def move_m1(self):
        for roller in self.rollers:
            if roller._group_device == True:
                continue
            await roller.move_m1()

    async def move_m2(self):
        for roller in self.rollers:
            if roller._group_device == True:
                continue
            await roller.move_m2()

    async def move_m3(self):
        for roller in self.rollers:
            if roller._group_device == True:
                continue
            await roller.move_m3()

    async def set_position(self, position):
        for roller in self.rollers:
            if roller._group_device == True:
                continue
            await roller.set_position(position)

    async def set_stop(self):
        for roller in self.rollers:
            if roller._group_device == True:
                continue
            await roller.set_stop()


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

    def __init__(self, area_name, local_ip, port, name, hub):
        """Init dummy roller."""
        if name == "GROUP":
            self._id = area_name + ":" + name
            self._group_device = True
            self._name = self._id
        else:
            self._id = name
            self._group_device = False
            self._name = name

        self.hub = hub
        self.hass = hub._hass
        self._setup_mode = hub._setup_mode
        self._refresh_interval = hub._refresh_interval
        self._local_ip = local_ip
        self._port = port
        self._callbacks = set()
        self._loop = asyncio.get_event_loop()
        self._target_position = 0
        self._current_position = 0
        self._cmd_refresh_count = 0
        self._cover_entity_id = None
        # self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "{}_{}".format(self._id, name), hass=hub._hass)
        # Reports if the roller is moving up or down.
        # >0 is up, <0 is down. This very much just for demonstration.
        self.moving = 0
        self.remove = False
        self._memory = [None, None, None]

        # Some static information about this device
        self.firmware_version = const.VERSION
        self.model = const.DOMAIN

        self._loop.create_task(self.easyroll_command("lstinfo", ""))

        threading.Timer(DEFAULT_REFRESH_INTERVAL, self.refresh).start()
        threading.Timer(DEFAULT_SEND_PLATFORM_INFO_INTERVAL, self.send_platform_info).start()

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
        return self._memory[order]

    def set_memory(self, order):
        _LOGGER.debug("set memory current position : %s", self._current_position)
        self._memory[order] = self._current_position
        self._loop.create_task(self.delayed_update())

    def set_cover_entity_id(self, entity_id):
        self._cover_entity_id = entity_id

    async def set_stop(self):
        #self.set_position(self._current_position)
        #await self.publish_updates(self._current_position)
        if self._group_device == True:
            await self.hub.set_stop()
            return

        await self._loop.create_task(self.easyroll_command("general", "SS"))
        await self._loop.create_task(self.easyroll_command("lstinfo", ""))
        self.moving = 0
        #self._target_position = self._current_position
        #await self._loop.create_task(self.easyroll_command("lstinfo", ""))

    async def set_position(self, position):
        """
        Set dummy cover to the given position.

        State is announced a random number of seconds later.
        """
        if self._group_device == True:
            await self.hub.set_position(position)
            return

        if self._cover_entity_id == None:
            return
        entity_state = self.hass.states.get(self._cover_entity_id)
        
        if _is_valid_state(entity_state) == False:
            return

        self._target_position = position
        # Update the moving status, and broadcast the update
        #self.moving = position - 50
        # self._current_position = position
        self._loop.create_task(self.easyroll_command("level", str(100 - position)))
        # 여기도 끝나고 나면 풀어줘야 함
        #threading.Timer(DEFAULT_CMD_REFRESH_INTERVAL, self.cmd_refresh).start()
        #self._loop.create_task(self.easyroll_command("lstinfo", ""))

    async def move_m1(self):
        if self._group_device == True:
            await self.hub.move_m1()
            return
        _LOGGER.debug("call move m1")
        
        self._loop.create_task(self.easyroll_command("general", "M1"))
        
    async def move_m2(self):
        if self._group_device == True:
            await self.hub.move_m2()
            return
        _LOGGER.debug("call move m2")
        self._loop.create_task(self.easyroll_command("general", "M2"))

    async def move_m3(self):
        _LOGGER.debug("call move m3")
        if self._group_device == True:
            await self.hub.move_m3()
            return
        self._loop.create_task(self.easyroll_command("general", "M3"))

    async def jog_up(self):
        _LOGGER.debug("call jog up")
        if self._setup_mode == True:
            self._loop.create_task(self.easyroll_command("force", "FSU"))
        else:
            self._loop.create_task(self.easyroll_command("general", "SU"))

        self._loop.create_task(self.easyroll_command("lstinfo", ""))

    async def jog_down(self):
        _LOGGER.debug("call jog down")
        if self._setup_mode == True:
            self._loop.create_task(self.easyroll_command("force", "FSD"))
        else:
            self._loop.create_task(self.easyroll_command("general", "SD"))

        self._loop.create_task(self.easyroll_command("lstinfo", ""))
    
    async def find_me(self):
        _LOGGER.debug("find me")
        _LOGGER.debug("current position : " + str(self._current_position))
        if self._current_position <= 0:
            # 닫겨 있는 상태
            pos = self._current_position
            await self.set_position(pos + 2)
            time.sleep(1)
            await self.set_position(pos)
        else:
            # 열려 있는 상태
            pos = self._current_position
            await self.set_position(pos - 2)
            time.sleep(1)
            await self.set_position(pos)


    async def auto_leveling(self):
        _LOGGER.debug("auto leveling") 
        if self._group_device == True:
            await self.hub.leveling_group()
            _LOGGER.debug("call group leveling")
        else:
            await self.hub.leveling(self._current_position)

    async def save_top(self):
        _LOGGER.debug("save top") 
        self._loop.create_task(self.easyroll_command("save", "ST"))

    async def save_bottom(self):
        _LOGGER.debug("save bottom") 
        self._loop.create_task(self.easyroll_command("save", "SB"))
        
    async def save_m1(self):
        _LOGGER.debug("save m1") 
        if self._group_device == True:
            await self.hub.move_m1()
            return
        self._loop.create_task(self.easyroll_command("save", "SM1"))

    async def save_m2(self):
        _LOGGER.debug("save m2") 
        if self._group_device == True:
            await self.hub.move_m2()
            return
        self._loop.create_task(self.easyroll_command("save", "SM2"))

    async def save_m3(self):
        _LOGGER.debug("save m3") 
        if self._group_device == True:
            await self.hub.move_m3()
            return
        self._loop.create_task(self.easyroll_command("save", "SM3"))

    async def force_up(self):
        _LOGGER.debug("force up") 
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
        self._loop.create_task(self.easyroll_command("lstinfo", ""))
        if self.remove == False and self._group_device == False:
            _LOGGER.debug("refresh!!, refresh interval : " + str(self._refresh_interval))
            threading.Timer(self._refresh_interval, self.refresh).start()
        #await threading.Timer(3, self.refresh).start()

    def cmd_refresh(self):
        _LOGGER.debug("cmd refresh")
        self._loop.create_task(self.easyroll_command("lstinfo", ""))
        self._cmd_refresh_count = self._cmd_refresh_count + 1
        if self._cmd_refresh_count >= 60:
            self.moving = 0
        if self.moving != 0 and self._group_device == False:
            """"""
            # 이 부분 풀어줘야 함
            #threading.Timer(DEFAULT_CMD_REFRESH_INTERVAL, self.cmd_refresh).start()

    def send_platform_info(self):
        self._loop.create_task(self._send_platform_info("homeassistant", self._local_ip, 20319))
        if self.remove == False and self._group_device == False:
            threading.Timer(DEFAULT_SEND_PLATFORM_INFO_INTERVAL, self.send_platform_info).start()
        #await threading.Timer(3, self.refresh).start()
            
    async def _send_platform_info(self, name, ip, port):
        try:
            async with aiohttp.ClientSession() as session:
                _LOGGER.debug("send platform info url : " + self._local_ip + ":" + str(self._port))
                _LOGGER.debug("name : %s, ip : %s, port : %d", name, ip, port)
                async with session.post("http://" + self._local_ip + ":" + str(self._port) + "/platform", json = {"name": name, "ip": ip, "port": str(port) }) as response:
                    raw_data = await response.read()
                    data = json.loads(raw_data)
                    _LOGGER.debug("end send platform info")
        except Exception as e:
            _LOGGER.error("command error : " + str(e))

    async def easyroll_command(self, mode, command):
        if self._group_device == True:
            return
        try:
            if mode == "lstinfo":
                async with aiohttp.ClientSession() as session:
                    _LOGGER.debug("url : " + self._local_ip + ":" + str(self._port))
                    async with session.get("http://" + self._local_ip + ":" + str(self._port) + "/" + mode) as response:
                        raw_data = await response.read()
                        data = json.loads(raw_data)
                        _LOGGER.debug("device position : " + str(data["position"]) + ", set position : " + str(self._current_position))
                        await self.publish_updates(round(float(data["position"])))

            else:
                async with aiohttp.ClientSession() as session:
                    _LOGGER.debug("url : " + self._local_ip + ":" + str(self._port))
                    async with session.post("http://" + self._local_ip + ":" + str(self._port) + "/action", json = {"mode": mode, "command": command  }) as response:
                        raw_data = await response.read()
                        data = json.loads(raw_data)

                        if mode == "level":
                            self.moving = 1
                        else:
                            self.moving = 0
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
