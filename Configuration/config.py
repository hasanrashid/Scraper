import configparser, logging, datetime

config_ini_settings = configparser.ConfigParser()
config_ini_settings.read("./Configuration/config.ini")

logging.basicConfig(level=config_ini_settings['Logging']['level'],
        format=config_ini_settings['Logging']['formatter'],
        datefmt=config_ini_settings['Logging']['date-format'],
        filename=config_ini_settings['Logging']['main-log']+' '+datetime.datetime.now().strftime('%Y-%m-%d')+'.log',
        filemode='w')
logger = logging.getLogger(config_ini_settings['Logging']['main-logger'])
