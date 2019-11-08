import configparser, logging, datetime, json

config_ini_settings = configparser.ConfigParser()
config_ini_settings.read("./Configuration/config.ini")

logging.basicConfig(level=config_ini_settings['Logging']['level'],
   format=config_ini_settings['Logging']['formatter'],
   datefmt=config_ini_settings['Logging']['date-format'],
   filename=config_ini_settings['Logging']['main-log']+' '+datetime.datetime.now().strftime('%Y-%m-%d')+'.log',
   filemode='w')
logger = logging.getLogger(config_ini_settings['Logging']['main-logger'])

def get_site_description():
    site_description=None
    try:           
        with open("./site-descriptor.json", "r") as s:
            site_description = json.loads(s)
            print(site_description)
    except Exception as e:
        logger.error(e)
        print(e)
    finally:
        return site_description