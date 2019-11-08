from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings
class Scraper:
    def __init__(self, url):
        try:
            logger.info('Starting Logger')
            self.url = url
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
        except Exception as e:
            logger.exception(e)
            print(e)

    def send_request(self):
        resp = None
        try:
            resp = requests.get(self.url, headers = self.request_header )
            if (resp.status_code is not 200):
                raise Exception("Request returned status code: "+str(resp.status_code))
        except Exception as e:
            logger.exception(e)
            print(e)
        finally:
            return resp

    def get_links(self, id_name=None,class_name=None):
        links = None
        try:
            with self.send_request() as resp:
                soup_object = SoupStrainer(id=id_name) if id_name is not None  else SoupStrainer(class_=class_name) if class_name is not None else None
                if (soup_object is None):
                    raise Exception("No css selectors were provided: ")
                if (all(x is not None for x in [id_name, class_name])):
                    warnings.warn('Both css id and class was provided. class will be ignored')                 
                links = BeautifulSoup(resp.content,'html.parser', parse_only=soup_object)
        except Exception as e:
            logger.exception(e)
            print(e)
        finally:
            return links
