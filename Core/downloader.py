import itertools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings, expression_mapping
import inspect

class Downloader():
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
    Takes a url, 
    '''
    def send_request(self, url, params=None, cookies=None):
        resp = self.session.get(url, headers = self.request_header, params=params, cookies=cookies, stream=True )
        if (resp.status_code is not 200):
            raise Exception("Request returned status code: "+str(resp.status_code))
        return resp

    def prepare_response(self, url_from_link):
            resp = self.send_request(url_from_link)
            return resp

    def download_file(self, file_url, book_title):
        book_info = None
        if(not os.path.exists(config_ini_settings['Values']['download-folder'])):
            raise Exception(config_ini_settings['Values']['download-folder'] + " does not exist")
        if(not os.path.isfile(config_ini_settings['Values']['download-folder']+book_title+'.pdf')):
            with self.prepare_response(file_url) as resp, open(config_ini_settings['Values']['download-folder']+book_title+".pdf",
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
        return book_info

    def download_files(self,file_anchors):
        books_downloaded = []
        try:
            for f in file_anchors:
                books_downloaded.append(self.download_file(f['href'],f.text))
        except Exception as e:
            logger.exception(e)
            print(e)
        finally:
            return books_downloaded
