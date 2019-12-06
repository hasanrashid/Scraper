import unittest
from ddt import ddt, data, unpack, file_data
from Core.scraper import Scraper
from Core.downloader import Downloader
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

    def test_send_request(self, url):
        assert self.downloader.send_request(self.downloader).status_code is 200

    '''
    Test a single download URL
    '''
    @file_data('test_download_file.json')
    def test_download_file(self, url_, title_):
        self.downloader.download_file(url_,title_)

    '''
    Test multiple anchors at once
    
    @file_data('test_download_files.json')
    def test_download_files(self, id_name=None, class_name=None, element_type=None, element_attribute=None):
        attr_ ={element_attribute['attribute']:re.compile(element_attribute['regex'])} if(element_attribute) else None
        anchors = self.downloader.get_links(self.downloader.url, class_name=class_name, element_type=element_type,attribute_=attr_)
        self.downloader.download_files(anchors)
    '''
    @file_data("test_prepare_response.json")
    def test_prepare_response(self, url):
        self.assertIsNotNone(self.downloader.prepare_response(url))

    '''@file_data('test_google_cookies.json')
    def test_google_cookies(self, id_name, class_name, element_type, element_attribute=None):
        anchors = self.downloader.get_links(self.downloader.url, class_name=class_name, element_type=element_type,attribute_={element_attribute['attribute']:re.compile(element_attribute['regex'])}) if(element_attribute) else self.downloader.get_links(self.downloader.url, class_name=class_name, element_type=element_type)
        self.downloader.download_files(anchors)'''