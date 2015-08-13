# coding=utf-8
from scrapy.spiders import CrawlSpider
from oxygendemo.items import OxygendemoItem
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor
import pyquery


def add_sale(url_array):
    return url_array + [url + '&S=1' for url in url_array]

class OxygenSpider(CrawlSpider):
    name = "oxygenboutique.com"
    allowed_domains = ["oxygenboutique.com"]

    # ViewAll=1 is added to show all items on one page
    # S=1 is for sale items
    clothes_urls = add_sale(['http://www.oxygenboutique.com/clothing.aspx?ViewAll=1'])
    shoes_urls = add_sale(['http://www.oxygenboutique.com/Shoes-All.aspx?ViewAll=1'])
    jewelry_urls = add_sale(['http://www.oxygenboutique.com/earrings.aspx?ViewAll=1',
                             'http://www.oxygenboutique.com/ring.aspx?ViewAll=1',
                             'http://www.oxygenboutique.com/necklace.aspx?ViewAll=1'])
    accessories_urls = add_sale(['http://www.oxygenboutique.com/hats.aspx?ViewAll=1',
                                 'http://www.oxygenboutique.com/iphone-cases.aspx?ViewAll=1',
                                 'http://www.oxygenboutique.com/HOMEWEAR.aspx?ViewAll=1',
                                 'http://www.oxygenboutique.com/Tattoos.aspx?ViewAll=1',
                                 'http://www.oxygenboutique.com/Crystal-Tattoos.aspx?ViewAll=1'])

    start_urls = clothes_urls + shoes_urls + accessories_urls

    rules = [
        Rule(LinkExtractor(restrict_xpaths='//div[@id="container"]//div[@class="DataContainer"]'),
             callback='parse_item')
    ]

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
        referer = response.request.headers.get('Referer')

        item_type = 'A'
        if referer in self.shoes_urls:
            item_type = 'S'
        elif referer in self.jewelry_urls:
            item_type = 'J'
        elif referer in self.accessories_urls:
            item_type = 'R'
        item['type'] = item_type

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
