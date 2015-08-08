from scrapy import Request
from scrapy.contrib.spiders import CrawlSpider

from oxygendemo.items import OxygendemoItem

import pyquery


class OxygenSpider(CrawlSpider):
    name = "oxygenboutique.com"
    allowed_domains = ["oxygenboutique.com"]
    start_urls = ['http://www.oxygenboutique.com/Mini-Bella-Ear-Jacket-Gold.aspx',  # DEVEL for testing
                  'http://www.oxygenboutique.com'
                  ]

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
                if url.startswith("http")\
                        and not url.startswith('http://www.oxygenboutique.com/SearchResults.aspx?') \
                        and not url.startswith('https://www.oxygenboutique.com/SearchResults.aspx?') \
                        and not url.startswith('http://www.oxygenboutique.com/GetImage/') \
                        and not url.startswith('https://www.oxygenboutique.com/GetImage/'):
                    yield Request(url)
        else:
            # log these so you can figure out what not to follow
            self.logger.info('not checking: %s', response.url)

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

        root = self.pq('div #container')

        item = OxygendemoItem()
        # Field details
        # -------------
        # - type, try and make a best guess, one of:
        #     - 'A' apparel
        #     - 'S' shoes
        #     - 'B' bags
        #     - 'J' jewelry
        #     - 'R' accessories
        item['type'] = 'A'  # TODO check request meta

        # - gender, one of:
        # - 'F' female
        # - 'M' male
        item['gender'] = 'F'

        # - designer - manufacturer of the item
        designer = root('.brand_name a').text().strip()
        item['designer'] = designer

        # - code - unique identifier from a retailer perspective
        # - name - short summary of the item
        name = root('h2').text().strip()
        if name.startswith(designer + ' '):
            name = name[len(designer):].strip()
        item['name'] = name
        # - description - fuller description and details of the item
        # text of the element after the one with "Description" text

        bla = [x for x in root('#accordion').children().items()]
        i = 0
        for i in range(len(bla)):
            if bla[i].text().strip() == 'Description':
                break

        item['description'] = bla[i+1].text().strip()

        # - raw_color - best guess of what colour the item is (can be blank if unidentifiable)
        # - image_urls - list of urls of large images representing the item
        # - gbp_price - full (non-discounted) price of the item
        # - sale_discount - percentage discount for sale items where applicable
        # - stock_status - dictionary of sizes to stock status
        # - 1 - out of stock
        # - 3 - in stock
        # - source_url - url of product page
        item['source_url'] = response.request.url

        return item
