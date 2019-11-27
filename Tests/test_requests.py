import unittest
from ddt import ddt, data, unpack, file_data
from Core.scraper import Scraper
from Configuration.config import expression_mapping, logger
import logging, json
import re
@ddt
class ScrapeMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scraper = Scraper('http://banglaclassicbooks.blogspot.com/')
    
    @classmethod
    def tearDownClass(cls):
        cls.scraper.session.close()

    @file_data("test_get_links.json")
    def test_get_links(self, id_name=None, class_name=None, element_type=None, element_attribute=None, css_selector=None):
        attr_ = {element_attribute['attribute']:re.compile(element_attribute['regex'])} if(element_attribute is not None) else None
        self.assertIsNotNone(self.scraper.get_links(self.scraper.url, id_name=id_name,class_name=class_name, element_type=element_type, attribute_=attr_, css_selector=css_selector))


    def test_send_request(self):
        assert self.scraper.send_request(self.scraper.url).status_code is 200

    '''
    Test a single download URL
    '''
    @file_data('test_download_file.json')
    def test_download_file(self, url_, title_):
        self.scraper.download_file(url_,title_)
        not self.assertLogs(logger,"Error")

    '''
    Test multiple anchors at once
    '''
    @file_data('test_download_files.json')
    def test_download_files(self, id_name=None, class_name=None, element_type=None, element_attribute=None):
        attr_ ={element_attribute['attribute']:re.compile(element_attribute['regex'])} if(element_attribute) else None
        anchors = self.scraper.get_links(self.scraper.url, class_name=class_name, element_type=element_type,attribute_=attr_)
        self.scraper.download_files(anchors)
    
    @file_data("test_prepare_response.json")
    def test_prepare_response(self, url):
        self.assertIsNotNone(self.scraper.prepare_response(url))

    '''@file_data('test_google_cookies.json')
    def test_google_cookies(self, id_name, class_name, element_type, element_attribute=None):
        anchors = self.scraper.get_links(self.scraper.url, class_name=class_name, element_type=element_type,attribute_={element_attribute['attribute']:re.compile(element_attribute['regex'])}) if(element_attribute) else self.scraper.get_links(self.scraper.url, class_name=class_name, element_type=element_type)
        self.scraper.download_files(anchors)'''