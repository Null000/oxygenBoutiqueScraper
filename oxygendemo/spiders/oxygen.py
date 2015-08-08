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
        if self.canUseXPath(response):
            self.logger.info('checking: %s', response.url)
            self.isProductPage(response)

            for href in response.xpath("//a/@href"):
                url = response.urljoin(href.extract())
                # don't go scraping javascript: links
                if url.startswith("http"):
                    yield scrapy.Request(url)

    def isProductPage(self, response):
        if len(response.xpath('//div[@id="product-images"]')) > 0:
            self.logger.info('found product page: %s', response.url)
            return True
        return False

    def canUseXPath(self, response):
        return getattr(response, 'xpath', None) is not None

    def parse_item(self, response):
        self.pq = pyquery.PyQuery(response.body)
        item = OxygendemoItem()
        # populate item fields here

        return None
