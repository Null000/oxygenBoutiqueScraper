# coding=utf-8
import urllib
from scrapy import Request
from scrapy.contrib.spiders import CrawlSpider
from oxygendemo.items import OxygendemoItem
import pyquery


class OxygenSpider(CrawlSpider):
    name = "oxygenboutique.com"
    allowed_domains = ["oxygenboutique.com"]

    # ?ViewAll=1 is added to show all items on one page
    clothes_url = 'http://www.oxygenboutique.com/clothing.aspx?ViewAll=1'
    shoes_url = 'http://www.oxygenboutique.com/Shoes-All.aspx?ViewAll=1'

    jewelry_urls = ['http://www.oxygenboutique.com/earrings.aspx?ViewAll=1',
                    'http://www.oxygenboutique.com/ring.aspx?ViewAll=1',
                    'http://www.oxygenboutique.com/necklace.aspx?ViewAll=1']
    accessories_url = 'http://www.oxygenboutique.com/accessories-all.aspx?ViewAll=1'

    start_urls = [clothes_url, shoes_url] + jewelry_urls

    jewelry_urls_remaining = set(jewelry_urls)
    urls_before_designers_remaining = set(start_urls + [accessories_url])

    visited_urls = set()

    urls_with_type = {
        clothes_url: 'A',
        shoes_url: 'S',
        accessories_url: 'R'
    }
    for url in jewelry_urls:
        urls_with_type[url] = 'J'

    def parse(self, response):
        url = response.url
        url = urllib.unquote(url)

        self.visited_urls.add(url)
        if url in self.jewelry_urls_remaining:
            self.jewelry_urls_remaining.remove(url)
        if url in self.urls_before_designers_remaining:
            self.urls_before_designers_remaining.remove(url)

        # if we can't use it, we ended up somewhere strange
        if self.can_use_xpath(response):
            self.logger.info('checking: %s', url)

            if self.is_product_page(response):
                yield self.parse_item(response)
            else:
                for href in response.xpath('//div[@id="container"]//div[@class="DataContainer"]//a/@href'):
                    new_url = response.urljoin(href.extract())
                    new_url = urllib.unquote(new_url)

                    if new_url not in self.visited_urls:
                        if url in self.jewelry_urls:
                            self.jewelry_urls_remaining.add(new_url)
                        self.urls_before_designers_remaining.add(new_url)

                        new_request = Request(new_url)
                        if url in self.urls_with_type.keys():
                            new_request.meta['lystType'] = self.urls_with_type[url]
                        yield new_request
            if len(self.jewelry_urls_remaining) == 0:
                # all jewelery done, adding the rest of accessories
                yield Request(self.accessories_url)
            if len(self.urls_before_designers_remaining) == 0:
                # all items by type done, adding designers
                for href in response.xpath('//ul[@id="ctl00_ulDesigners"]//a/@href'):
                    new_url = response.urljoin(href.extract())
                    new_url = urllib.unquote(new_url) + '?ViewAll=1'
                    yield Request(new_url)
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

        root = self.pq('div#container')

        item = OxygendemoItem()
        # Field details
        # -------------
        # - type, try and make a best guess, one of:
        #     - 'A' apparel
        #     - 'S' shoes
        #     - 'B' bags
        #     - 'J' jewelry
        #     - 'R' accessories

        # there is no data for the ones that are only in the designers category
        if 'lystType' in response.request.meta.keys():
            item['type'] = response.request.meta['lystType']

        # - gender, one of:
        # - 'F' female
        # - 'M' male
        item['gender'] = 'F'

        # - designer - manufacturer of the item
        designer = root('.brand_name a').text().strip()
        item['designer'] = designer

        # - code - unique identifier from a retailer perspective
        full_name = root('h2').text().strip()
        item['code'] = full_name

        # - name - short summary of the item
        name = full_name
        if name.startswith(designer + ' '):
            name = name[len(designer):].strip()
        item['name'] = name

        # - description - fuller description and details of the item
        # text of the element after the one with "Description" text
        dropdowns = [x for x in root('#accordion').children().items()]
        i = 0
        for i in range(len(dropdowns)):
            if dropdowns[i].text().strip() == 'Description':
                break

        item['description'] = dropdowns[i + 1].text() \
            .replace(u'\u00a0', ' ') \
            .replace('\r', ' ') \
            .replace('\n', ' ') \
            .strip()

        # - raw_color - best guess of what colour the item is (can be blank if unidentifiable)
        # - image_urls - list of urls of large images representing the item
        item['image_urls'] = [response.urljoin(href.extract()) for href in
                              response.xpath('//div[@id="thumbnails"]//a/@href')]

        # - gbp_price - full (non-discounted) price of the item
        price = root('.price').text().strip()
        if price[0] == u'£':
            price = price[1:].strip()
        price = price.split(' ')
        price = [float(x) for x in price]

        item['gbp_price'] = price[0]
        # - sale_discount - percentage discount for sale items where applicable
        if len(price) > 1:
            item['sale_discount'] = 100 * ((price[0] - price[1]) / price[0])

        # - stock_status - dictionary of sizes to stock status
        # - 1 - out of stock
        # - 3 - in stock
        stock = {}

        sizes = root('select option')
        for size in sizes:
            if 'Please Select' in size.text:
                continue
            elif '- Sold Out' in size.text:
                stock[size.text.replace('- Sold Out', '').strip()] = 1
            else:
                stock[size.text.strip()] = 3
        item['stock_status'] = stock

        # - source_url - url of product page
        item['source_url'] = response.request.url

        return item
