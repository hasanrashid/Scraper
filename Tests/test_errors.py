import unittest
from ddt import ddt, data, unpack, file_data
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

    def test_send_request_error(self, url):
        assert self.downloader.send_request(self.downloader).status_code is not 200

    @file_data("test_download_file_exceptions.json")
    def test_download_errors(self, url_, title_):
        self.assertRaises(Exception, self.downloader.download_file, url_,title_)

    @file_data("test_prepare_response_datafilehost_exceptions.json")
    def test_prepare_datafilehost_errors(self, url):
        self.assertRaises(Exception, self.downloader.prepare_datafilehost, self.downloader, url)

    @file_data("test_prepare_response_google_exceptions.json")
    def test_prepare_google_errors(self, url):
        self.assertRaises(Exception, self.downloader.prepare_google, self.downloader, url)
