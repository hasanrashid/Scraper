import unittest
from ddt import ddt, data, unpack, file_data
from Core.downloader import Downloader
from Core.decorator import Decorator as response_decorator
from Configuration.config import expression_mapping, logger
import Core.download_strategies as strategies
import logging, json
import re

@ddt
class DownloaderMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.downloader = Downloader()
        cls.strategies = strategies
    
    @classmethod
    def tearDownClass(cls):
        cls.downloader.session.close()

    @file_data("test_download_file_exceptions.json")
    def test_download_errors(self, url_, title_):
        book_info = self.downloader.download_file(url_,title_)
        self.assertIsNone(book_info)

    @file_data("test_prepare_response_datafilehost_exceptions.json")
    def test_prepare_datafilehost_errors(self, url):
        self.assertRaises(Exception, self.strategies.prepare_datafilehost, self.downloader, url)

    @file_data("test_prepare_response_google_exceptions.json")
    def test_prepare_google_errors(self, url):
        self.assertRaises(Exception, self.strategies.prepare_google, self.downloader, url)
