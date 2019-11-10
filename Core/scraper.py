from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings
class Scraper:
    def __init__(self):
        try:
            logger.info('Starting Logger')
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
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
    
    def get_links(self,url, id_name=None,class_name=None, element_type=None):
        links = None
        try:
            with self.send_request(url) as resp:

                if (all(x is not id_name for x in ['',None])):
                    soup_object = SoupStrainer(id=id_name)
                elif((all(x is not class_name for x in ['',None]))):
                    soup_object = SoupStrainer(class_=class_name) 
                else:
                    soup_object = None
                
                if (soup_object is None):
                    raise Exception("No css selectors were provided: ")
                if (all(x is not None for x in [id_name, class_name])):
                    warnings.warn('Both css id and class was provided. class will be ignored')                 
                links = BeautifulSoup(resp.content,'html.parser', parse_only=soup_object)
                if (all(x is not element_type for x in ['',None])):
                    links = links.find_all(element_type) 
        except Exception as e:
            logger.exception(e)
            links = e
            print(e)
        finally:
            return links

    def download_file(self, file_url, book_title):
        book_info = None
        try:
            if(not os.path.isfile(config_ini_settings['Values']['download-folder'])):
                raise Exception(config_ini_settings['Values']['download-folder'] + " does not exist")
            if(not os.path.isfile(config_ini_settings['Values']['download-folder']+book_title+'.pdf')):
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
                            scraped_links.writelines(str("\n",book_title,": ",str(size/(1024**2))," Megabytes\n"))
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
