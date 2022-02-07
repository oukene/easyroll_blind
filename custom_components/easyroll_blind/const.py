"""Constants for the Detailed Hello World Push integration."""
"""Constants for the Detailed Hello World Push integration."""
from typing import DefaultDict
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import DEVICE_CLASS_TEMPERATURE, PLATFORM_SCHEMA
from homeassistant.config import CONF_NAME
# This is the internal name of the integration, it should also match the directory
# name for the integration.
DOMAIN = "easyroll_blind"
VERSION = "1.0.0"

ENDPOINT_START = 1
ENDPOINT_END = 254

SEARCH_TIMEOUT = 1
SEARCH_PERIOD = 120

DEVICE_PORT=20318

CONF_AREA_NAME = "area_name"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_USE_SETUP_MODE = "use_setup"
CONF_DEVICES = "conf_devices"
CONF_HOST = "host"
CONF_ADD_ANODHER = "add_another"
CONF_ADD_GROUP_DEVICE = "add_group_device"

SNAME_SAVE_TOP = "Save Top"
SNAME_SAVE_BOTTOM = "Save Buttom"
SNAME_SAVE_M1 = "Save M1"
SNAME_SAVE_M2 = "Save M2"
SNAME_SAVE_M3 = "Save M3"

SNAME_MOVE_M1 = "Move M1"
SNAME_MOVE_M2 = "Move M2"
SNAME_MOVE_M3 = "Move M3"

SNAME_FORCE_UP = "Force Up"
SNAME_FORCE_DOWN = "Force Down"

SNAME_JOG_UP = "Jog Up"
SNAME_JOG_DOWN = "Jog Down"

SNAME_FIND_ME = "Fine Me"
SNAME_AUTO_LEVELING = "Leveling"

DEFAULT_REFRESH_INTERVAL = 10
DEFAULT_CMD_REFRESH_INTERVAL = 1

DEFAULT_SEND_PLATFORM_INFO_INTERVAL = 10

