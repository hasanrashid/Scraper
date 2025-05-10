import itertools
import functools
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Core.decorator import Decorator as response_decorator
from Configuration.config import logger, config_ini_settings, expression_mapping, raise_exception
from clint.textui import progress
import  Core.download_strategies as strategies
from tqdm import tqdm

#https://mega.nz/file/rstD0S4a#mcGTRB3h7Q_I1k5LA5YPoo2lYGftStktGenNWersE5o

class Downloader():

    def __init__(self):
        try:
            logger.info('Starting Logger')
            self.scraped_links, self.download_folder, self.download_errors = config_ini_settings['Filenames']['scraped-links'], config_ini_settings['Filenames']['download-folder'], config_ini_settings['Filenames']['download-errors']
            self.request_header = {'user-agent': config_ini_settings['Values']['user-agent']}
            self.session = requests.session()
            self.prepare_function = {'mega.nz':strategies.prepare_mega,'drive.google.com':strategies.prepare_google, 'www.datafilehost.com':strategies.prepare_datafilehost, 'mediafire.com':strategies.no_preparation_download, 'www.mediafire.com':strategies.prepare_mediafire}
        except Exception as e:
            logger.exception(e)
            print(e)

    def __enter__(self):
        return self


    def send_request(self, url, params=None, cookies=None, headers_only=False):

        resp = self.session.get(url, headers = self.request_header, params=params, cookies=cookies, stream=True )
        
        if(resp.status_code != 200):
            raise_exception(self,f"Request returned status code {resp.status_code}")

        return resp

    '''
    file_url is passed to the functtion- this is the actual download URL of the file
    '''
    def download_file(self, file_url, book_title=None):
        book_info = None
        download_host_regex_match = re.search(expression_mapping['Download Link RegEx'], file_url)
        host_correct = False
        file_exists = False
        try:            
            if(not download_host_regex_match):
                print(f"something wrong with the link {file_url} from download host name {download_host}")
                logger.error(f"something wrong with the link {file_url} from download host name {download_host}")
            else:        
                download_host = download_host_regex_match.group(1)
                if(download_host not in expression_mapping["Download URL"]):
                    print(f"{download_host} is not a known URL")
                    logger.error(f"{download_host} is not a known URL")
                else:
                    book_info = None
                    with self.prepare_function[download_host](self,file_url) as resp:
                        d = resp.headers['content-disposition']
                        if(not book_title):
                            book_title = re.findall("filename=\"(.+)\";*", resp.headers["Content-Disposition"])[0]
                        for e in expression_mapping['File Extensions']:
                            if(os.path.isfile(os.getcwd()+self.download_folder+book_title)):
                                file_exists = True
                                break
                        if(not file_exists):
                            with open(os.getcwd()+self.download_folder+book_title, 'wb') as pdf_file, open(self.scraped_links,'a+',encoding='utf-8') as scraped_links:                
                                size = 0
                                total_length = int(resp.headers.get('content-length'))
                                extension = resp.headers['content-type'][-3:]
                                for chunk in progress.bar(resp.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
                                    if chunk:
                                        pdf_file.write(chunk)
                                        pdf_file.flush()
                                book_info = (book_title,size)
                                scraped_links.writelines("\n"+book_title+": "+str(size/(1024**2))+" Megabytes\n")
                        else:
                            logger.info(book_title+' already exists')
                            print(book_title+' already exists')
        except Exception as e:
            print(e)
            logger.error(e)
            with open(download_errors,'r',encoding='utf-8') as d:
                d.writelines("Error downloading: "+book_title+" from "+file_url)
        finally:
            return book_info

