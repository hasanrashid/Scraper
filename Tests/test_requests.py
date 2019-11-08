import unittest
from ddt import ddt, data, unpack
from Core.scraper import Scraper
from Configuration.config import get_site_description
import logging, json
@ddt
class ScrapeMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scraper = Scraper(get_site_description()[0])

    @data((None,None),('BlogArchive1_ArchiveList','posts'), ('BlogArchive1_ArchiveList', None),(None,'posts'),('','posts'),('BlogArchive1_ArchiveList',''))
    @unpack
    def test_get_links(self, i, c):
        self.assertNotIsInstance(self.scraper.get_links(id_name=i,class_name=c),Exception)

    def test_send_request(self):
        assert self.scraper.send_request().status_code is 200

    def test_download_book(self):
        assert self.scraper.download_file is not None