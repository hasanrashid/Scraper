import unittest
from ddt import ddt, data, unpack, file_data
from Core.scraper import Scraper
from Core.downloader import Downloader
from Core.decorator import Decorator as response_decorator
from Configuration.config import expression_mapping, logger
import logging, json
import re

@ddt
class DownloaderMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.downloader = Downloader()
    
    @classmethod
    def tearDownClass(cls):
        cls.downloader.session.close()

    '''
    Test a single download URL
    '''
    @file_data('test_download_file.json')
    def test_download_file(self, url_, title_):
        self.assertIsNotNone(self.downloader.download_file(url_,title_))

    @file_data("test_prepare_response_datafilehost.json")
    def test_prepare_datafilehost(self, url):
        self.assertIsNotNone(self.downloader.prepare_datafilehost(self.downloader, url))

    @file_data("test_prepare_response_google.json")
    def test_prepare_google(self, url):
        self.assertIsNotNone(self.downloader.prepare_google(self.downloader, url))

    @file_data("test_prepare_response_mediafire.json")
    def test_prepare_mediafire(self, url):
        self.assertIsNotNone(self.downloader.prepare_mediafire(self.downloader, url))

