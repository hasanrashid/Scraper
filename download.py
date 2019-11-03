from bs4 import BeautifulSoup
import requests
import os
import re
import json
from bs4 import SoupStrainer
import sys
import re
import traceback
import logging
import configparser

url = 'https://banlassicbooks.blogspot.com/'
headers = {'user-agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}

def get_links(url,headers):
    post_links = None
    try:
        with requests.get(url, headers = headers) as resp:
            if (any(int(x) == resp.status_code for x in ['404','503'])):
                raise Exception("Request returned status code: "+str(resp.status_code))
            post_links = BeautifulSoup(resp.text,'html.parser', parse_only=SoupStrainer(id='BlogArchive1_ArchiveList')).find_all(SoupStrainer(class_="post-count-link"))
    except requests.exceptions.HTTPError as e:
        print(e)
    finally:
        post_links


with open("download7.txt","w") as f:
    for p in get_links(url,headers):
        f.writelines(p['href']+"\n")
