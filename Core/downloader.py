import itertools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings, expression_mapping

class Downloader():
    def __init__(self):
        try:
            logger.info('Starting Logger')
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
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

    def prepare_response(self,file_url):
        params = {}
        cookies = {}
        resp=None
        #https://drive.google.com/file/d/13mpttO8wxgPyxoJ2-9YP0nFQ1DbD5jK3/view
        try:
            json_entry = expression_mapping["Download URL"][re.search(r"\/\/(.*?)\/", file_url).group(1)]
            if(json_entry['action'] == 'download'):
                resp = self.send_request(json_entry['URL'])
            elif(json_entry['action'] == 'construct'):
                if(json_entry['Request Params']):
                    for r in json_entry['Request Params']:                
                        if(r['type'] == "regex"):
                            params[r["name"]] = re.search(r['value'], file_url).group(1)
                            continue
                        if(r['type'] == "text"):
                            params[r["name"]] = r["value"]
                            continue
                    resp = self.send_request(json_entry['First URL'], params) if json_entry['First URL'] != 'unchanged' else self.send_request(file_url)
                    if(json_entry['Cookies']):
                        for cookie,value in resp.cookies.items():                
                            for c in json_entry['Cookies']:
                                if(c['name'] in cookie):
                                    if(c['action'] == "attach"):
                                        cookies[cookie] = value
                                        continue
                                    if(c['action'] == "read"):
                                        params[c['value']] = value
                                        continue
                    if(json_entry['Second URL']):
                        resp = self.send_request(json_entry['Second URL'], params=params, cookies=cookies)
        except Exception as e:
            logger.exception(e)
            print(e)
        finally:
            return resp

