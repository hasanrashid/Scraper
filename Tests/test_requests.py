import unittest
from ddt import ddt, data, unpack, file_data
from Core.scraper import Scraper
from Configuration.config import url_patterns, logger
import logging, json
import re
@ddt
class ScrapeMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scraper = Scraper('http://banglaclassicbooks.blogspot.com/')

    @file_data("test_get_links.json")
    def test_get_links(self, id_name=None, class_name=None, element_type=None, element_attribute=None, css_selector=None):
        attr_ = {element_attribute['attribute']:re.compile(element_attribute['regex'])} if(element_attribute is not None) else None
        if(all(x is None for x in [id_name,class_name])):
            self.assertIsInstance(self.scraper.get_links(self.scraper.url, id_name=id_name,class_name=class_name, element_type=element_type, attribute_=attr_, css_selector=css_selector),Exception)
        else:
            self.assertNotIsInstance(self.scraper.get_links(self.scraper.url,id_name=id_name,class_name=class_name, element_type=element_type, attribute_=attr_, css_selector=css_selector),Exception)

    def test_send_request(self):
        assert self.scraper.send_request(self.scraper.url).status_code is 200

    @file_data('test_download_file.json')
    def test_download_file(self, url_, title_):
        self.scraper.download_file(url_,title_)
        not self.assertLogs(logger,"Error")
    
    @file_data('test_download_files.json')
    def test_download_files(self, id_name, class_name, element_type, element_attribute=None):
        anchors = self.scraper.get_links(self.scraper.url, class_name=class_name, element_type=element_type,attribute_={element_attribute['attribute']:re.compile(element_attribute['regex'])}) if(element_attribute) else self.scraper.get_links(self.scraper.url, class_name=class_name, element_type=element_type)
        #self.scraper.download_files(anchors)