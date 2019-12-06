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
