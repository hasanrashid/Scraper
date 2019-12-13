import itertools
import functools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Core.decorator import Decorator as response_decorator
from Configuration.config import logger, config_ini_settings, expression_mapping, raise_exception


class Downloader():
    def __init__(self):
        try:
            logger.info('Starting Logger')
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
            self.session = requests.session()
            self.prepare_function = {'drive.google.com':self.prepare_google, 'www.datafilehost.com':self.prepare_datafilehost}
        except Exception as e:
            logger.exception(e)
            print(e)
    
    def send_request(self, url, params=None, cookies=None):
        resp = self.session.get(url, headers = self.request_header, params=params, cookies=cookies, stream=True )
        if (resp.status_code is not 200):
            raise_exception(self,f"Request returned status code {resp.status_code}")
        return resp
    
    @response_decorator
    def prepare_google(self, g_url, json_entry, params=None):
        params.update(json_entry['Request Params'])
        resp = self.send_request(json_entry['URL'], params=params)
        for cookie, value in resp.cookies.items():
            if json_entry['Cookie'] in cookie:
                params['confirm'] = value
                break            
        resp = self.send_request(json_entry['URL'], params=params)
        return resp            

    @response_decorator
    def prepare_datafilehost(self,dfh_url, json_entry, params=None):
        cookies = {}
        resp = self.send_request(dfh_url)
        for cookie, value in resp.cookies.items():
            if 'PHPSESSID' in json_entry['Cookie']:
                cookies[cookie]=value
                break                
        resp = self.send_request(json_entry['URL'], params, cookies)
        return resp            

    def download_file(self, file_url, book_title):
        book_info = None

        scraped_links, download_folder = config_ini_settings['Filenames']['scraped-links'], config_ini_settings['Filenames']['download-folder']

        download_host = re.search(r"\/\/(.*?)\/", file_url).group(1)        
        
        if(download_host not in expression_mapping["Download URL"]):
            raise_exception(self,f"{download_host} is not a known URL")

        if not download_host:
            raise_exception(self,f"something wrong with the download host name {download_host}")

        if(not os.path.isfile(download_folder+book_title+'.pdf')):
            with self.prepare_function[download_host](self,file_url) as resp, open(download_folder+book_title+".pdf",
            'wb') as pdf_file, open(scraped_links,'a+') as scraped_links:                
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
