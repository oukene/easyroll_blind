"""GitHub Custom Component."""
import asyncio
import json
import logging
import aiohttp
import socket

from . import hub
from homeassistant import config_entries, core

from .const import (
    CONF_AREA_NAME, DEFAULT_REFRESH_INTERVAL, DOMAIN, CONF_REFRESH_INTERVAL, 
    CONF_USE_SETUP_MODE, ENDPOINT_END, ENDPOINT_START, SEARCH_TIMEOUT
)
#PLATFORMS = ["switch", "cover", "sensor"]
PLATFORMS = ["switch", "cover"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
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

    refresh_interval = entry.options.get(CONF_USE_SETUP_MODE)
    if refresh_interval == None:
        refresh_interval = DEFAULT_REFRESH_INTERVAL

    area_name = entry.data.get(CONF_AREA_NAME)

    hass.data[DOMAIN][entry.entry_id] = hub.Hub(hass, area_name, use_setup_mode, refresh_interval)
    hub2 = hass.data[DOMAIN][entry.entry_id]

    use_setup_mode = entry.data.get(CONF_USE_SETUP_MODE)
    #_LOGGER.error("config_entry _ init : " + use_setup_mode)

    loop = asyncio.get_event_loop()
    loop.create_task(delayed_update(hass, entry, hub2))

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

async def get_html(hub2, subnet, i):
    _LOGGER.error("call get html")
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://" + subnet + str(i) + ":20318/lstinfo"
            #url = "http://192.168.11.120:20318/lstinfo"
            _LOGGER.error("url : " + url)
            async with await session.get(url, timeout=SEARCH_TIMEOUT) as response:
                raw_data = await response.read()
                data = json.loads(raw_data)
                _LOGGER.error(data)
                _LOGGER.error("response local ip : " + data["local_ip"])
                hub2.rollers.append(hub.Roller(hub2._area_name, data["local_ip"], hub2))
    except Exception:
        """"""
            
async def delayed_update(hass, entry, hub2):
    """Publish updates, with a random delay to emulate interaction with device."""
    _LOGGER.error("call delayed update")
    subnet = get_subnet_ip(extract_ip())

    await asyncio.gather(
            *(get_html(hub2, subnet, i) for i in range(ENDPOINT_START, ENDPOINT_END+1))
        )
    
    # Forward the setup to the sensor platform.
    _LOGGER.error("Hub Size : " + str(len(hub2.rollers)))
    
    for component in PLATFORMS:
        _LOGGER.error("create component : " + component)
        await hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
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
