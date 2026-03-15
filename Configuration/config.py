"""
DEPRECATED: This configuration module is deprecated in favor of ConfigManager.

This module is kept for backward compatibility with legacy code.
New code should use Core.config_manager.ConfigManager instead.

The regex patterns from this file have been moved to:
- Configuration/regex_patterns.json (organized patterns)
- Core/regex_manager.py (pattern management)
"""

import warnings
warnings.warn(
    "Configuration.config is deprecated. Use Core.config_manager.ConfigManager instead.",
    DeprecationWarning,
    stacklevel=2
)

import configparser, logging, datetime, json, tempfile
import os
from pathlib import Path

def raise_exception(message):
    e = Exception(message)
    logger.exception(e)
    raise e

config_ini_settings = configparser.ConfigParser()

# Get the directory where this config.py file is located
config_dir = os.path.dirname(os.path.abspath(__file__))

# Read config files relative to this directory
config_ini_settings.read(os.path.join(config_dir, "config.ini"))
with open(os.path.join(config_dir, "expression-mapping.json"), "r") as s:
    expression_mapping = json.load(s)


def _runtime_base_dir() -> Path:
    cwd = Path.cwd()
    if os.access(cwd, os.W_OK):
        return cwd
    return Path(tempfile.gettempdir())


def _resolve_runtime_path(path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str(_runtime_base_dir() / path)

# Azure deployments can occasionally miss or fail to read config.ini.
# Keep legacy module import-safe by applying minimal defaults.
if 'Logging' not in config_ini_settings:
    config_ini_settings['Logging'] = {
        'logs-folder': 'Logs',
        'main-log': 'scraper-log',
        'test-log': 'unit-test-log',
        'date-format': '%%m-%%d %%H:%%M',
        'formatter': '%%(asctime)s %%(name)-12s %%(levelname)-8s %%(filename)s %%(funcName)s %%(lineno)d %%(message)s',
        'main-logger': 'ScraperLog',
        'test-logger': 'TestLog',
        'level': 'INFO',
    }

if 'Filenames' not in config_ini_settings:
    config_ini_settings['Filenames'] = {
        'scraped-links': 'scraped_links.txt',
        'download-folder': 'Books/',
        'download-errors': 'download_errors.txt',
    }

config_ini_settings['Logging']['logs-folder'] = _resolve_runtime_path(
    config_ini_settings['Logging']['logs-folder']
)
config_ini_settings['Filenames']['download-folder'] = _resolve_runtime_path(
    config_ini_settings['Filenames']['download-folder']
)
config_ini_settings['Filenames']['scraped-links'] = _resolve_runtime_path(
    config_ini_settings['Filenames']['scraped-links']
)
config_ini_settings['Filenames']['download-errors'] = _resolve_runtime_path(
    config_ini_settings['Filenames']['download-errors']
)

# Create logs directory if it doesn't exist
logs_dir = config_ini_settings['Logging']['logs-folder']
os.makedirs(logs_dir, exist_ok=True)

log_filename = os.path.join(
    logs_dir,
    config_ini_settings['Logging']['main-log'] + ' ' + datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
)

logging.basicConfig(level=config_ini_settings['Logging']['level'],
   format=config_ini_settings['Logging']['formatter'],
   datefmt=config_ini_settings['Logging']['date-format'],
   filename=log_filename,
   filemode='w')
logger = logging.getLogger(config_ini_settings['Logging']['main-logger'])

if not expression_mapping["Download URL"]:
    raise_exception("Could not map hostname to download url. Check expression-mapping.json")

download_folder_path = config_ini_settings['Filenames']['download-folder']
if(not os.path.exists(download_folder_path)):
    os.makedirs(download_folder_path, exist_ok=True)
    logger.info(f"Created download folder: {download_folder_path}")

if(not all([config_ini_settings['Filenames']['scraped-links'], config_ini_settings['Filenames']['download-folder']])):
    e = Exception("One of the following file name or location is not right: scraped links, download folder")            
    logger.exception(e)
    raise e


