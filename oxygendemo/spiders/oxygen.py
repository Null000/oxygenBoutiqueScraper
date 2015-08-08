import scrapy
from scrapy.contrib.spiders import CrawlSpider

from oxygendemo.items import OxygendemoItem

import pyquery


class OxygenSpider(CrawlSpider):
    name = "oxygenboutique.com"
    allowed_domains = ["oxygenboutique.com"]
    start_urls = ['http://www.oxygenboutique.com']

    def parse(self, response):
        # if we can't use it, we ended up somewhere strange
        if self.can_use_xpath(response):
            self.logger.info('checking: %s', response.url)
            if self.is_product_page(response):
                yield self.parse_item(response)

            for href in response.xpath("//a/@href"):
                url = response.urljoin(href.extract())
                # don't go scraping javascript: links
                # TODO filter images and other obviously wrong files
                if url.startswith("http"):
                    yield scrapy.Request(url)

    def is_product_page(self, response):
        if len(response.xpath('//div[@id="product-images"]')) > 0:
            self.logger.info('found product page: %s', response.url)
            return True
        return False

    @staticmethod
    def can_use_xpath(response):
        return getattr(response, 'xpath', None) is not None

    def parse_item(self, response):
        self.pq = pyquery.PyQuery(response.body)
        item = OxygendemoItem()
        # populate item fields here

        return None
