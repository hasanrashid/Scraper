import unittest
from ddt import ddt, data, unpack, file_data
from Core.scraper import Scraper
from Configuration.config import get_site_description, logger
import logging, json
@ddt
class ScrapeMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scraper = Scraper()

    @file_data("test_get_links.json")
    def test_get_links(self, id_name, class_name):
        if(all(x is None for x in [id_name,class_name])):
            self.assertIsInstance(self.scraper.get_links('http://banglaclassicbooks.blogspot.com/', id_name=id_name,class_name=class_name),Exception)
        else:
            self.assertNotIsInstance(self.scraper.get_links('http://banglaclassicbooks.blogspot.com/',id_name=id_name,class_name=class_name),Exception)

    def test_send_request(self):
        assert self.scraper.send_request('http://banglaclassicbooks.blogspot.com/').status_code is 200

    @file_data('test_download_file.json')
    def test_download_file(self, url_, title_):
        self.scraper.download_file(url_,title_)
        not self.assertLogs(logger,"Error")
    
    @file_data('test_download_files.json')
    def test_download_files(self, id_name,class_name):
        anchors = self.scraper.get_links('http://banglaclassicbooks.blogspot.com/', class_name=class_name, element_type='a')
        #self.scraper.download_files(anchors)