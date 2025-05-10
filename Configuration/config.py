import configparser, logging, datetime, json
import os
from pathlib import Path

def raise_exception(message):
    e = Exception(message)
    logger.exception(e)
    raise e

config_ini_settings = configparser.RawConfigParser()
config_ini_settings.read("./Configuration/config.ini")
with open("./Configuration/expression-mapping.json", "r") as s:
    expression_mapping = json.load(s)

logging.basicConfig(level=config_ini_settings['Logging']['level'],
   format=config_ini_settings['Logging']['formatter'],
   datefmt=config_ini_settings['Logging']['date-format'],
   filename=config_ini_settings['Logging']['logs-folder']+"\\"+config_ini_settings['Logging']['main-log']+' '+datetime.datetime.now().strftime('%Y-%m-%d')+'.log',
   filemode='w')
logger = logging.getLogger(config_ini_settings['Logging']['main-logger'])

if not expression_mapping["Download URL"]:
    raise_exception("Could not map hostname to download url. Check expression-mapping.json")

if(not os.path.exists(os.getcwd()+'/'+config_ini_settings['Filenames']['download-folder'])):
    raise_exception(f"{config_ini_settings['Filenames']['download-folder']}does not exist")

if(not all([config_ini_settings['Filenames']['scraped-links'], config_ini_settings['Filenames']['download-folder']])):
    e = Exception("One of the following file name or location is not right: scraped links, download folder")            
    logger.exception(e)
    raise e


