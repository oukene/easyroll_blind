"""GitHub Custom Component."""
import asyncio
import json
import logging
import aiohttp
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from . import hub
from homeassistant import config_entries, core

from .const import (
    CONF_ADD_GROUP_DEVICE, CONF_AREA_NAME, CONF_DEVICES, DEFAULT_REFRESH_INTERVAL, DEVICE_PORT, DOMAIN, CONF_REFRESH_INTERVAL, 
    CONF_USE_SETUP_MODE, ENDPOINT_END, ENDPOINT_START, SEARCH_TIMEOUT, SEARCH_PERIOD, CONF_HOST
)

from homeassistant.const import CONF_NAME
#PLATFORMS = ["switch", "cover", "sensor"]
PLATFORMS = ["switch", "cover"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)
    # Registers update listener to update config entry when options are updated.
    #unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    #hass_data["unsub_options_update_listener"] = unsub_options_update_listener

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
            hub2.rollers[host.get(CONF_HOST)] = hub.Roller(area_name, host.get(CONF_HOST), DEVICE_PORT, host.get(CONF_NAME), hub2)     

    if add_group_device == True:
        hub2.rollers["0.0.0.0"] = hub.Roller(area_name, "0.0.0.0", 0, "GROUP", hub2)

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
            
async def delayed_update(hass, entry, hub2):
    """Publish updates, with a random delay to emulate interaction with device."""
    _LOGGER.debug("call delayed update")
    subnet = get_subnet_ip(extract_ip())

    await asyncio.gather(
            *(get_html(entry, hub2, subnet, i) for i in range(ENDPOINT_START, ENDPOINT_END+1))
        )
    
    # Forward the setup to the sensor platform.
    _LOGGER.debug("Hub Size : " + str(len(hub2.rollers)))
    if len(hub2.rollers) >= 1 and hub2._add_group_device == True:
        hub2.rollers.append(hub.Roller(hub2._area_name, "Group", hub2))
    
    for component in PLATFORMS:
        _LOGGER.debug("create component : " + component)
        await hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    #threading.Timer(SEARCH_PERIOD, await delayed_update(hass, entry, hub2)).start()

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
    for roller in hub.rollers.values():
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
