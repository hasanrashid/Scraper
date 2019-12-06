import itertools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings, expression_mapping
from Core.downloader import Downloader
import inspect

class Scraper:
    def __init__(self, url):
        try:
            logger.info('Starting Logger')
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
            self.url = url
            self.session = requests.session()
        except Exception as e:
            logger.exception(e)
            print(e)
    '''
    Method is given a url, optinal id and/or class name and an element type that defaults to an
    HTML anchor.
    '''
    def get_links(self,url, id_name=None,class_name=None, element_type=None, attribute_=None, css_selector=None):
        links = None
        try:
            with requests.get(url, headers = self.request_header) as resp:
                if(resp.status_code is not 200):
                    raise Exception("Request to url{} came back with status {}".format(url,resp.status_code))
                null_values = ['',None]        
                if (all(x not in null_values for x in [id_name, class_name])):
                    warnings.warn('Both css id and class was provided. class will be ignored')                 
                bs = BeautifulSoup(resp.content,'html.parser', parse_only=SoupStrainer(element_type, id=id_name, class_=class_name))
                if(attribute_ not in null_values):
                    links = bs.find_all(attrs=attribute_)
                elif(css_selector not in null_values):
                    links=bs.select(css_selector)
                else:
                    links=bs.find_all('a')
        except Exception as e:
            logger.exception(e)
            print(e)
        finally:
            return links

