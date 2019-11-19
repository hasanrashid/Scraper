import itertools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings, url_patterns

class Scraper:
    def __init__(self, url):
        try:
            logger.info('Starting Logger')
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
            self.url = url
        except Exception as e:
            logger.exception(e)
            print(e)

    def send_request(self, url):
        resp = None
        try:
            resp = requests.get(url, headers = self.request_header )
            if (resp.status_code is not 200):
                raise Exception("Request returned status code: "+str(resp.status_code))
        except Exception as e:
            logger.exception(e)
            resp = e
            print(e)
        finally:
            return resp
    '''
    Method is given a url, optinal id and/or class name and an element type that defaults to an
    HTML anchor.
    '''
    def get_links(self,url, id_name=None,class_name=None, element_type=None, attribute_=None, css_selector=None):
        links = None
        try:
            with self.send_request(url) as resp:
                null_values = ['',None]

                if(id_name not in null_values):
                    if(element_type is not None):                        
                        soup_object = SoupStrainer(element_type, id=id_name)
                    else:
                        soup_object = SoupStrainer(id=id_name)
                elif(class_name not in null_values):
                    if(element_type is not None):
                        soup_object = SoupStrainer(element_type, id=id_name)
                    else:
                        soup_object = SoupStrainer(class_=class_name)
                else:
                    raise Exception("No css selectors were provided: ")

                if (all(x is not None for x in [id_name, class_name])):
                    warnings.warn('Both css id and class was provided. class will be ignored')                 

                bs = BeautifulSoup(resp.content,'html.parser', parse_only=soup_object)
                if(all(x is None for x in [attribute_, css_selector])):
                    links = list(bs.children)
                elif(attribute_ is not None):
                    links = bs.find_all(attrs=attribute_)
                elif(css_selector is not None):
                    links=bs.select(css_selector)

        except Exception as e:
            logger.exception(e)
            links = e
            print(e)
        finally:
            return links

    def download_file(self, file_url, book_title):
        book_info = None
        try:
            #https://drive.google.com/file/d/0B5Lsnk25QxCFSzg3RDlXU2RRc0k/view

            if(not os.path.exists(config_ini_settings['Values']['download-folder'])):
                raise Exception(config_ini_settings['Values']['download-folder'] + " does not exist")
            if(not os.path.isfile(config_ini_settings['Values']['download-folder']+book_title+'.pdf')):
                '''fu = self.map_download_string_to_url(file_url)
                if fu is None:
                    return None'''
                with self.send_request(file_url) as resp, open(config_ini_settings['Values']['download-folder']+book_title+".pdf",
                'wb') as pdf_file, open(config_ini_settings['Filenames']['scraped-links'], 
                'a+') as scraped_links:
                    size = 0
                    for i, chunk in enumerate(resp.iter_content(chunk_size=128)):
                        if i%1024 == 0:
                            print(".",end='') 
                        pdf_file.write(chunk)
                        size+= len(chunk)
                    book_info = (book_title,size)
                    scraped_links.writelines("\n"+book_title+": "+str(size/(1024**2))+" Megabytes\n")
            else:
                logger.info(book_title+' already exists')
        except Exception as e:
            logger.exception(e)
            print(e)
        finally:
            return book_info

    def download_files(self,file_anchors):
        for f in file_anchors:
            self.download_file(f['href'],f.text)
