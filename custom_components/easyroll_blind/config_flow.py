"""Config flow for Hello World integration."""
from copy import deepcopy
from distutils.command.config import config
import logging
from unicodedata import name
import aiohttp
import asyncio
import json
from markupsafe import string
import voluptuous as vol
import socket
from typing import Any, Dict, Optional

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

import homeassistant.helpers.entity_registry

from homeassistant.helpers.device_registry import (
    async_get,
    async_entries_for_config_entry
)

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.config import CONF_NAME

from .const import (CONF_ADD_ANODHER, CONF_ADD_GROUP_DEVICE, CONF_AREA_NAME, CONF_DEVICES, CONF_HOST, 
            CONF_USE_SETUP_MODE, DOMAIN, CONF_REFRESH_INTERVAL, SEARCH_TIMEOUT, DEFAULT_REFRESH_INTERVAL,
            ENDPOINT_END, ENDPOINT_START, SNAME_FORCE_DOWN, SNAME_FORCE_UP, SNAME_SAVE_BOTTOM, SNAME_SAVE_M1, SNAME_SAVE_M2, SNAME_SAVE_M3, SNAME_SAVE_TOP)
from .hub import Hub

_LOGGER = logging.getLogger(__name__)

def extract_ip():
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:       
        st.connect(('10.255.255.255', 1))
        IP = st.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        st.close()
    return IP

def get_subnet_ip(ip):
    t = ip.split(".")

    n = 0
    subnet = ""
    for i in t:
        subnet = subnet + i + "."
        n = n + 1
        if n == 3:
            break
    return subnet

async def get_html(subnet, i, devices):
    #_LOGGER.debug("call get html")
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://" + subnet + str(i) + ":20318/lstinfo"
            #url = "http://192.168.11.120:20318/lstinfo"
            #_LOGGER.debug("url : " + url)
            async with await session.get(url, timeout=SEARCH_TIMEOUT) as response:
                raw_data = await response.read()
                data = json.loads(raw_data)
                #_LOGGER.debug("response local ip : " + data["local_ip"])
                devices.append(subnet + str(i))
                #hub2.rollers.append(hub.Roller(hub2._area_name+"2", data["local_ip"], hub2))
    except Exception:
        """"""
            
async def get_available_device():
    """Publish updates, with a random delay to emulate interaction with device."""
    subnet = get_subnet_ip(extract_ip())

    available_devices = []

    await asyncio.gather(
            *(get_html(subnet, i, available_devices) for i in range(ENDPOINT_START, ENDPOINT_END+1))
        )

    return available_devices
    #threading.Timer(SEARCH_PERIOD, await delayed_update(hass, entry, hub2)).start()

async def test_connection(host):
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://" + host + ":20318/lstinfo"
            #url = "http://192.168.11.120:20318/lstinfo"
            _LOGGER.debug("url : " + url)
            async with await session.get(url, timeout=10) as response:
                raw_data = await response.read()
                data = json.loads(raw_data)
                return True
                #hub2.rollers.append(hub.Roller(hub2._area_name+"2", data["local_ip"], hub2))
    except Exception:
        return False

async def validate_input(host):

    if len(host) < 3:
        raise InvalidHost

    result = await test_connection(host)
    if False == result:
        raise CannotConnect

    return {"title": host}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hello World."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle the initial step."""
        # This goes through the steps to take the user through the setup process.
        # Using this it is possible to update the UI and prompt for additional
        # information. This example provides a single form (built from `DATA_SCHEMA`),
        # and when that has some validated input, it calls `async_create_entry` to
        # actually create the HA config entry. Note the "title" value is returned by
        # `validate_input` above.
        errors = {}
        if user_input is not None:
            #if user_input[CONF_NETWORK_SEARCH] == True:
            #    return self.async_create_entry(title=user_input[CONF_AREA_NAME], data=user_input)
            #else:
            self.data = user_input
            self.data[CONF_DEVICES] = []
            #self.devices = await get_available_device()
            #return await self.async_step_hosts()
            return self.async_create_entry(title=self.data[CONF_AREA_NAME], data=self.data)

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema( 
            {
                vol.Required(CONF_AREA_NAME): cv.string,
                #vol.Required(CONF_ADD_GROUP_DEVICE): cv.boolean
            })
            , errors=errors
        )

    async def async_step_hosts(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a repo to watch."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(
                    user_input[CONF_HOST]
                )
            except ValueError:
                errors["base"] = "invalid_host"

            if not errors:
                # Input is valid, set data.
                self.data[CONF_DEVICES].append(
                    {
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_NAME: user_input.get(CONF_NAME, user_input[CONF_HOST]),
                    }
                )
                # If user ticked the box show this form again so they can add an
                # additional repo.
                if user_input.get(CONF_ADD_ANODHER, False):
                    self.devices.remove(user_input[CONF_HOST])
                    if len(self.devices) <= 0:
                        return self.async_create_entry(title=self.data[CONF_AREA_NAME], data=self.data)
                    else:
                        return await self.async_step_hosts()
                # User is done adding repos, create the config entry.
                return self.async_create_entry(title=self.data[CONF_AREA_NAME], data=self.data)

        return self.async_show_form(
            step_id="hosts", 
            data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST, default=None): vol.In(self.devices),
                        vol.Optional(CONF_NAME): cv.string,
                        vol.Optional(CONF_ADD_ANODHER): cv.boolean,
                    }
                ), errors=errors
            )
        
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Handle a option flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry
        self.data = {}
        self.data[CONF_AREA_NAME] = config_entry.data[CONF_AREA_NAME]
        self.data[CONF_DEVICES] = config_entry.data[CONF_DEVICES]
        self.data[CONF_REFRESH_INTERVAL] = config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        #self.data[CONF_ADD_ANODHER] = config_entry.data[CONF_ADD_ANODHER]
        #self.data[CONF_ADD_GROUP_DEVICE] = config_entry.data[CONF_ADD_GROUP_DEVICE]
        #self.data[CONF_USE_SETUP_MODE] = config_entry.data[CONF_USE_SETUP_MODE]

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}
        # Grab all configured repos from the entity registry so we can populate the
        # multi-select dropdown that will allow a user to remove a repo.
        #entity_registry = await async_get_registry(self.hass)
        
        #entries = async_entries_for_config_entry(
        #    entity_registry, self.config_entry.entry_id
        #)
        #for e in entries:
        #    _LOGGER.debug("entries : " + e.entity_id)
        # Default value for our multi-select.
        #entity_map = {e.entity_id : e for e in entries}
        self.devices = await get_available_device()
        all_devices = {}
        all_devices_by_host = {}

        entity_registry = await homeassistant.helpers.entity_registry.async_get(self.hass)
        entities = homeassistant.helpers.entity_registry.async_entries_for_config_entry(entity_registry, self.config_entry.entry_id)
        
        device_registry = await async_get(self.hass)
        devices = async_entries_for_config_entry(device_registry, self.config_entry.entry_id)

        for e in entities:
            _LOGGER.debug("entity id : %s, name : %s", e.entity_id, e.original_name)

        # Default value for our multi-select.

        for host in self.data[CONF_DEVICES]:
            for d in devices:
                if d.name == host[CONF_NAME]:
                    name = d.name
                    if d.name_by_user is not None:
                        name = d.name_by_user

                    all_devices[d.id] = '{} - {}'.format(name, host[CONF_HOST])
                    all_devices_by_host[ (host[CONF_HOST], host[CONF_NAME] ) ] = d.id
                    try:
                        self.devices.remove(host[CONF_HOST])
                    except Exception:
                        """"""
                    break

        if user_input is not None:
            if user_input.get(CONF_ADD_ANODHER, False):
                if len(self.devices) <= 0:
                    errors["base"] = "no_more_device"

            if not errors:
                # If user ticked the box show this form again so they can add an
                # additional repo.
                # remove devices
                self.data[CONF_DEVICES].clear()
                remove_devices = []
                self.data[CONF_ADD_GROUP_DEVICE] = user_input[CONF_ADD_GROUP_DEVICE]
                self.data[CONF_USE_SETUP_MODE] = user_input[CONF_USE_SETUP_MODE]
                self.data[CONF_REFRESH_INTERVAL] = user_input[CONF_REFRESH_INTERVAL]
                if user_input[CONF_ADD_GROUP_DEVICE] == False:
                    for d in devices:
                        if d.name == self.data[CONF_AREA_NAME] + ":GROUP":
                            remove_devices.append(d.id)

                for key in all_devices_by_host:
                    if all_devices_by_host[key] not in user_input[CONF_DEVICES]:
                        #_LOGGER.debug("add remove device host : %s, id : %d", key, all_devices_by_host[key])
                        remove_devices.append(all_devices_by_host[key])
                        #self.config_entry.data[CONF_DEVICES].remove( { host[CONF_HOST], [e.name for e in devices if e.id == all_devices_by_host[host[CONF_HOST]]] })
                    else:
                        self.data[CONF_DEVICES].append(
                            {
                                CONF_HOST: key[0],
                                CONF_NAME: key[1],
                            }
                        )

                for device_id in remove_devices:
                    #_LOGGER.debug("remove device device id : %d", str(device_id))
                    device_registry.async_remove_device(device_id)

                # 설정용 entity들 삭제
                if user_input[CONF_USE_SETUP_MODE] == False:
                    for e in entities:
                        if e.original_name == SNAME_SAVE_TOP or e.original_name == SNAME_SAVE_BOTTOM or e.original_name == SNAME_SAVE_M1 or e.original_name == SNAME_SAVE_M2 \
                            or e.original_name == SNAME_SAVE_M3 or e.original_name == SNAME_FORCE_DOWN or e.original_name == SNAME_FORCE_UP:
                            entity_registry.async_remove(e.entity_id)
                
                if user_input.get(CONF_ADD_ANODHER, False):
                    #if len(self.devices) <= 0:
                    #    return self.async_create_entry(title=self.config_entry.data[CONF_AREA_NAME], data=self.config_entry.data)
                    #else:
                    return await self.async_step_hosts()

                # User is done adding repos, create the config entry.
                return self.async_create_entry(title=self.data[CONF_AREA_NAME], data=self.data)

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_DEVICES, default=list(all_devices)): cv.multi_select(all_devices),
                vol.Optional(CONF_REFRESH_INTERVAL, default=self.config_entry.options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(1, 600)),
                vol.Optional(CONF_USE_SETUP_MODE, default=self.config_entry.options.get(CONF_USE_SETUP_MODE, False)): cv.boolean,
                vol.Optional(CONF_ADD_GROUP_DEVICE, default=self.config_entry.options.get(CONF_ADD_GROUP_DEVICE, False)): cv.boolean,
                vol.Optional(CONF_ADD_ANODHER): cv.boolean,

                #vol.Optional(CONF_USE_SETUP_MODE, False, cv.boolean),
                #vol.Optional(CONF_ADD_GROUP_DEVICE, False, cv.boolean),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )

    async def async_step_hosts(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a repo to watch."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(
                    user_input[CONF_HOST]
                )
            except ValueError:
                errors["base"] = "invalid_host"

            if not errors:
                # Input is valid, set data.
                self.data[CONF_DEVICES].append(
                    {
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_NAME: user_input.get(CONF_NAME, user_input[CONF_HOST]),
                    }
                )

                # If user ticked the box show this form again so they can add an
                # additional repo.
                if user_input.get(CONF_ADD_ANODHER, False):
                    self.devices.remove(user_input[CONF_HOST])
                    if len(self.devices) <= 0:
                        return self.async_create_entry(title=self.data[CONF_AREA_NAME], data=self.data)
                    else:
                        return await self.async_step_hosts()
                # User is done adding repos, create the config entry.
                return self.async_create_entry(title=self.data[CONF_AREA_NAME], data=self.data)

        return self.async_show_form(
            step_id="hosts", 
            data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST, default=None): vol.In(self.devices),
                        vol.Optional(CONF_NAME): cv.string,
                        vol.Optional(CONF_ADD_ANODHER): cv.boolean,
                    }
                ), errors=errors
            )


"""class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        conf = self.config_entry
        if conf.source == config_entries.SOURCE_IMPORT:
            return self.async_show_form(step_id="init", data_schema=None)
        if user_input is not None:
            updated_hosts = deepcopy(self.config_entry.data[CONF_HOST])
            removed_entities = [
                entity_id
                for entity_id in repo_map.keys()
                if entity_id not in user_input["repos"]
            ]
            return self.async_create_entry(title="", data=user_input)

        options_schema = {}
        data_list = [CONF_REFRESH_INTERVAL, CONF_USE_SETUP_MODE]
        for name, default, validation in OPTIONS:
            to_default = conf.options.get(name, default)
            if name in data_list and conf.options.get(name, default) == default:
                to_default = conf.data.get(name, default)
            key = vol.Optional(name, default=to_default)
            options_schema[key] = validation
            
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(options_schema)
        )"""


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""