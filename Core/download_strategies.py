import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Core.decorator import Decorator as response_decorator
from Configuration.config import logger, config_ini_settings, expression_mapping, raise_exception
from Core.scraper import Scraper 
# from mega import Mega  # Temporarily disabled due to version compatibility issues

@response_decorator
def no_preparation_download(self, url, json_entry=None, params=None):
    resp = self.send_request(url)   
    return resp     

@response_decorator
def prepare_google(self, g_url, json_entry, params=None,headers_only=False):
    params.update(json_entry['Request Params'])
    resp = self.send_request(json_entry['URL'], params=params,headers_only=headers_only)
    for cookie, value in resp.cookies.items():
        if json_entry['Cookie'] in cookie:
            params['confirm'] = value
            break            
    resp = self.send_request(json_entry['URL'], params=params)
    return resp            

@response_decorator
def prepare_mediafire(self,mediafire_url, json_entry=None, params=None,headers_only=False):
    s = Scraper()
    download_link = s.get_links(mediafire_url,element_type='a',id_name="downloadButton")
    resp = self.send_request(download_link[0]['href'],headers_only=headers_only)
    return resp            

@response_decorator
def prepare_us_archive(self,us_archive_url, json_entry=None, params=None,headers_only=False):

    resp = self.send_request(us_archive_url,headers_only=headers_only)
    return resp            


@response_decorator
def prepare_datafilehost(self,dfh_url, json_entry, params=None,headers_only=False):
    cookies = {}
    resp = self.send_request(dfh_url,headers_only=headers_only)
    for cookie, value in resp.cookies.items():
        if 'PHPSESSID' in json_entry['Cookie']:
            cookies[cookie]=value
            break                
    resp = self.send_request(json_entry['URL'], params, cookies,headers_only=headers_only)
    return resp            

@response_decorator
def prepare_mega(self, mega_url, json_entry, params=None, headers_only=False):
    # TODO: Re-enable when mega.py compatibility is fixed
    raise NotImplementedError("Mega.nz downloads temporarily disabled due to dependency compatibility issues")
    # cookies = {}
    # mega = Mega()
    # mega.download_url(mega_url)
    # file = mega.download()
    # resp = self.send_request(json_entry['URL'], params, cookies, headers_only=headers_only)
    # return resp

