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

import configparser, logging, datetime, json
import os
from pathlib import Path

def raise_exception(message):
    e = Exception(message)
    logger.exception(e)
    raise e

config_ini_settings = configparser.ConfigParser()
config_ini_settings.read("./Configuration/config.ini")
with open("./Configuration/expression-mapping.json", "r") as s:
    expression_mapping = json.load(s)

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

download_folder_path = os.path.join(os.getcwd(), config_ini_settings['Filenames']['download-folder'])
if(not os.path.exists(download_folder_path)):
    os.makedirs(download_folder_path, exist_ok=True)
    logger.info(f"Created download folder: {download_folder_path}")

if(not all([config_ini_settings['Filenames']['scraped-links'], config_ini_settings['Filenames']['download-folder']])):
    e = Exception("One of the following file name or location is not right: scraped links, download folder")            
    logger.exception(e)
    raise e


