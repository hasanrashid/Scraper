import itertools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings, expression_mapping, raise_exception
#from Core.downloader import Downloader
import inspect

class Scraper:
    def __init__(self):
        try:
            logger.info('Starting Logger')
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
            self.session = requests.session()
        except Exception as e:
            logger.exception(e)
            print(e)

    '''
    Method is given a url, optinal id and/or class name and an element type that defaults to an
    HTML anchor.
    '''
    def get_links(self,url, id_name=None,class_name=None, element_type=None, attribute_=None, css_selector=None,features=None,links_only=True):
        links = None
        download_errors = config_ini_settings['Filenames']['download-errors']
        try:
            with requests.get(url, headers = self.request_header) as resp:

                if(resp.status_code != 200):
                    logger.error(f"Request to url{url} came back with status {resp.status_code}")
                else:
                    null_values = ['',None]        

                    if (all(x not in null_values for x in [id_name, class_name])):
                        warnings.warn('Both css id and class was provided. class will be ignored')                 

                    if(id_name is not None):
                        soup_strainer = SoupStrainer(element_type, id=id_name)
                    elif(class_name is not None):
                        soup_strainer = SoupStrainer(element_type, class_=class_name)
                    else:
                        soup_strainer = SoupStrainer(element_type)
                    if(features=='xml'):
                        bs = BeautifulSoup(resp.content,'xml', parse_only=soup_strainer)
                    else:
                        bs = BeautifulSoup(resp.content,'html.parser', parse_only=soup_strainer)

                    if(attribute_ not in null_values):
                        links = bs.find_all(attrs=attribute_)
                    elif(css_selector not in null_values):
                        links=bs.select(css_selector)
                    else:
                        if(features =='xml'):
                            links=bs.find_all('loc')
                        else:
                            if(links_only == True):
                                links=bs.find_all('a')
                            else:
                                links = bs.find_all()
        except:
            logger.error(book_title+'Not available')
            logger.error(e)
            print(e)
            with open(download_errors,'r',encoding='utf-8') as d:
                d.writelines("Error downloading: "+book_title+" from "+file_url)
        finally:
            return links

