import itertools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings, expression_mapping
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
    Takes a url, 
    '''
    def send_request(self, url, params=None, cookies=None):
        resp = self.session.get(url, headers = self.request_header, params=params, cookies=cookies, stream=True )
        if (resp.status_code is not 200):
            raise Exception("Request returned status code: "+str(resp.status_code))
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

    def prepare_datafilehost_response(self,datafilehost_url):
        params = {}
        cookies = {}
        try:
            params["file"] = re.search(r"d\/([0-9A-Za-z]*)", datafilehost_url).group(1)
            #params["export"] = "download"
            resp = self.send_request(datafilehost_url)
            for cookie,value in resp.cookies.items():
                if 'PHPSESSID' in cookie:
                    cookies['PHPSESSID']=value
            resp = self.send_request("https://drive.google.com/uc", params=params)
        except Exception as e:
            logger.exception(e)
            print(e)
            resp = None        
        finally:
            return resp

    def prepare_google_response(self, google_url):
        params = {}
        cookies = {}
        try:
            params["id"] = re.search(r"(?:id=|d\/)([a-zA-Z-0-9]*)", google_url).group(1)
            params["export"] = "download"
            resp = self.send_request("https://drive.google.com/uc", params=params)
            for cookie,value in resp.cookies.items():
                if 'download_warning_' in cookie:
                    params['confirm']=value
            resp = self.send_request("https://drive.google.com/uc", params=params)
        except Exception as e:
            logger.exception(e)
            print(e)
            resp = None        
        finally:
            return resp

    def prepare_response(self, url_from_link):
        try:
            download_url = None
            params = {}
            cookies = {}
            for u in expression_mapping['Download URL']:
                if u in url_from_link:
                    resp = self.send_request(u)
                    download_url = expression_mapping['Download URL'][u]['URL']
                    for p,q in expression_mapping['Download URL'][u]['Download Params'].items():
                        params[p] = re.search(q, url_from_link).group(1)
                    if(expression_mapping['Download URL'][u]['action'] == 'construct'):
                        resp = self.send_request(download_url, params=params)
                    for k,v in resp.cookies.items():
                        for c in expression_mapping['Download URL'][u]['Cookies']:
                            if(c['name'] in k):
                                #n = expression_mapping['Download URL'][u]['Cookies']['name'] 
                                cookie_name,cookie_value=list(c['value'].keys())[0], list(c['value'].values())[0]
                                if(c['name'] == cookie_name):
                                    cookies= resp.cookies.get_dict()
                                else:
                                    params[cookie_name] = cookie_value.format(v)
                                break
                    break
            if(download_url is None):
                raise Exception(url_from_link+" is not a known url")
            resp = self.send_request(download_url,params=params, cookies=cookies)
        except Exception as e:
            logger.exception(e)
            print(e)
            resp = None
        finally:
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
