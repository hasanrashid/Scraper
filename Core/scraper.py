from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings
class Scraper:
    def __init__(self, site_description):
        try:
            logger.info('Starting Logger')
            self.site_description = site_description
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
        except Exception as e:
            logger.exception(e)
            print(e)

    def send_request(self):
        resp = None
        try:
            resp = requests.get(self.site_description['url'], headers = self.request_header )
            if (resp.status_code is not 200):
                raise Exception("Request returned status code: "+str(resp.status_code))
        except Exception as e:
            logger.exception(e)
            resp = e
            print(e)
        finally:
            return resp
    
    def get_links(self, id_name=None,class_name=None, element_type=None):
        links = None
        try:
            with self.send_request() as resp:

                if (all(x is not id_name for x in ['',None])):
                    soup_object = SoupStrainer(id=id_name)
                elif((all(x is not class_name for x in ['',None]))):
                    soup_object = SoupStrainer(class_=class_name) 
                else:
                    soup_object = None
                
                if (soup_object is None):
                    raise Exception("No css selectors were provided: ")
                if (all(x is not element_type for x in ['',None])):
                    soup_object.searchTag(element_type) 
                if (all(x is not None for x in [id_name, class_name])):
                    warnings.warn('Both css id and class was provided. class will be ignored')                 
                links = BeautifulSoup(resp.content,'html.parser', parse_only=soup_object)
        except Exception as e:
            logger.exception(e)
            links = e
            print(e)
        finally:
            return links

    def download_file(self, file_url, book_title):
        book_info = None
        try:
            if(not os.path.isfile(config_ini_settings['Values']['download-folder']+book_title+'.pdf')):
                with requests.get(file_url, headers = config_ini_settings['Values']['user-agent']).raw as resp:
                    with open(config_ini_settings['Values']['download-folder']
                    +book_title+'.pdf', 'wb') as pdf_file, open(config_ini_settings['Values']['scraped-links']) as scraped_links:
                        size = 0
                        for i, chunk in enumerate(resp.iter_content(chunk_size=128)):
                            if i%1024 == 0:
                                print(".",end='') 
                            pdf_file.write(chunk)
                            size+= len(chunk)
                        book_info = tuple(book_title,size)
                        scraped_links.writelines("\n",book_title,": ",str(size/(1024**2))," Megabytes\n")
            else:
                logger.info(book_title+' already exists')
        except Exception as e:
            logger.exception(e)
            print(e)
        finally:
            return book_info
        