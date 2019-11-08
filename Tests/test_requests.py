import unittest
from Core.scraper import Scraper
from Configuration.config import get_site_description
import logging, json

class ResponseTests(unittest.TestCase):
    def setUp(self):
        #logger = logging.getLogger('TestLog')
        self.scraper = Scraper('http://bengalitreasuretrove.blogspot.com/')
        site_description = get_site_description()
        print(site_description)    
    def test_get_links(self):
        assert self.scraper.get_links(id_name='BlogArchive1_ArchiveList',class_name='posts') is not None
    def test_send_request(self):
        assert self.scraper.send_request().status_code is 200
