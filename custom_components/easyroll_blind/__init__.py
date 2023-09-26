"""GitHub Custom Component."""
import asyncio
import json
import logging
import aiohttp
import socket

from . import hub
from homeassistant import config_entries, core

from .const import *

from homeassistant.const import CONF_NAME
#PLATFORMS = ["switch", "cover", "sensor"]
PLATFORMS = ["button", "cover"]

_LOGGER = logging.getLogger(__name__)

async def update_listener(hass, entry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)
    
    entry.async_on_unload(entry.add_update_listener(update_listener))

    use_setup_mode = bool(entry.options.get(CONF_USE_SETUP_MODE))
    if use_setup_mode == None:
        use_setup_mode = False

    add_group_device = bool(entry.options.get(CONF_ADD_GROUP_DEVICE))
    if add_group_device == None:
        add_group_device = False

    refresh_interval = entry.options.get(CONF_REFRESH_INTERVAL)
    if refresh_interval == None:
        refresh_interval = DEFAULT_REFRESH_INTERVAL

    area_name = entry.data.get(CONF_AREA_NAME)
    hass.data[DOMAIN][entry.entry_id] = hub.Hub(hass, area_name, use_setup_mode, refresh_interval, add_group_device)
    hub2 = hass.data[DOMAIN][entry.entry_id]

    for host in entry.data[CONF_DEVICES]:
            """"""
            hub2.rollers.append(hub.Roller(area_name, host.get(CONF_HOST), DEVICE_PORT, host.get(CONF_NAME), hub2))     

    if add_group_device == True:
        hub2.rollers.append(hub.Roller(area_name, "0.0.0.0", 0, "GROUP", hub2))

    for component in PLATFORMS:
        _LOGGER.debug("create component : " + component)
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    """
    if network_search == False:
        for host in entry.data[CONF_HOST]:
            """"""
            hub2.rollers.append(hub.Roller(area_name, host.get(CONF_HOST) + ":20318", hub2))        

        if len(hub2.rollers) >= 1 and add_group_device == True:
            hub2.rollers.append(hub.Roller(hub2._area_name, "Group", hub2))

        for component in PLATFORMS:
            _LOGGER.debug("create component : " + component)
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
            )
    else:
        loop = asyncio.get_event_loop()
        loop.create_task(delayed_update(hass, entry, hub2))
    """
    return True

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

async def get_html(entry, hub2, subnet, i):
    _LOGGER.debug("call get html")
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://" + subnet + str(i) + ":20318/lstinfo"
            #url = "http://192.168.11.120:20318/lstinfo"
            _LOGGER.debug("url : " + url)
            async with await session.get(url, timeout=SEARCH_TIMEOUT) as response:
                raw_data = await response.read()
                data = json.loads(raw_data)
                #_LOGGER.debug("response local ip : " + data["local_ip"])
                hub2.rollers.append(hub.Roller(hub2._area_name, data["local_ip"], hub2))
                #hub2.rollers.append(hub.Roller(hub2._area_name+"2", data["local_ip"], hub2))
    except Exception:
        """"""

async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""

    hub = hass.data[DOMAIN][entry.entry_id]
    for roller in hub.rollers:
        roller.remove = True

    unload_ok = all(
        await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, component)
                    for component in PLATFORMS
                ]
            )
    )
    # Remove options_update_listener.
    #hass.data[DOMAIN][entry.entry_id]["unsub_options_update_listener"]()

    # Remove config entry from domain.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the GitHub Custom component from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True
