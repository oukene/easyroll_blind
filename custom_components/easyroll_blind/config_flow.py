"""Config flow for Hello World integration."""
import logging
import aiohttp
import asyncio
import json
import voluptuous as vol
import socket
from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.config import CONF_NAME

from .const import (CONF_ADD_ANODHER, CONF_AREA_NAME, CONF_HOST, CONF_NETWORK_SEARCH, 
            CONF_USE_SETUP_MODE, DOMAIN, CONF_REFRESH_INTERVAL, OPTIONS, SEARCH_TIMEOUT,
            CONF_NETWORK_SEARCH, DATA_SCHEMA, ENDPOINT_END, ENDPOINT_START)
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
    _LOGGER.debug("call get html")
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://" + subnet + str(i) + ":20318/lstinfo"
            #url = "http://192.168.11.120:20318/lstinfo"
            _LOGGER.debug("url : " + url)
            async with await session.get(url, timeout=SEARCH_TIMEOUT) as response:
                raw_data = await response.read()
                data = json.loads(raw_data)
                _LOGGER.debug("response local ip : " + data["local_ip"])
                devices.append(subnet + str(i))
                #hub2.rollers.append(hub.Roller(hub2._area_name+"2", data["local_ip"], hub2))
    except Exception:
        """"""
            
async def get_available_device():
    """Publish updates, with a random delay to emulate interaction with device."""
    _LOGGER.debug("call delayed update")
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
            if user_input[CONF_NETWORK_SEARCH] == True:
                return self.async_create_entry(title=user_input[CONF_AREA_NAME], data=user_input)
            else:
                self.data = user_input
                self.data[CONF_HOST] = []
                self.devices = await get_available_device()
                return await self.async_step_hosts()

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
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
                self.data[CONF_HOST].append(
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
    """Handle a option flow for Naver Weather."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle options flow."""
        conf = self.config_entry
        if conf.source == config_entries.SOURCE_IMPORT:
            return self.async_show_form(step_id="init", data_schema=None)
        if user_input is not None:
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
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""