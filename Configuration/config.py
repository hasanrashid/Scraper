import configparser, logging, datetime, json

config_ini_settings = configparser.SafeConfigParser()
config_ini_settings.read("./Configuration/config.ini")
with open("./Configuration/expression-mapping.json", "r") as s:
    expression_mapping = json.load(s)

logging.basicConfig(level=config_ini_settings['Logging']['level'],
   format=config_ini_settings['Logging']['formatter'],
   datefmt=config_ini_settings['Logging']['date-format'],
   filename=config_ini_settings['Logging']['main-log']+' '+datetime.datetime.now().strftime('%Y-%m-%d')+'.log',
   filemode='w')
logger = logging.getLogger(config_ini_settings['Logging']['main-logger'])
