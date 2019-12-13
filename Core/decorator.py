import itertools
import functools
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Configuration.config import logger, config_ini_settings, expression_mapping, raise_exception

class Decorator(object):

    def __init__(self, host_response):
        self.host_response = host_response

    def __call__(self, downloader, file_url):
        
        host_url = re.search(r"\/\/(.*?)\/", file_url).group(1)
        
        if(host_url not in expression_mapping["Download URL"]):
            raise_exception(self,f"{host_url} is not a known URL")
        
        json_entry = expression_mapping["Download URL"][host_url]
        
        if(not all([json_entry['File ID regex'], json_entry['Cookie']])):
            raise_exception(self,f"Error in expression-mapping.json. Check {expression_mapping['Download URL']}")

        params  = re.search(json_entry['File ID regex'], file_url).groupdict()

        if not params:
            raise_exception(self,f"regex {json_entry['File ID regex']} did not return a match for {file_url}. Please check expression in expression-mappings.json")
        
        return self.host_response(downloader, file_url, json_entry,params)
