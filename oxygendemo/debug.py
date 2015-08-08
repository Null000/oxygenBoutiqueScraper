__author__ = 'null'
from scrapy import cmdline
cmdline.execute("scrapy crawl oxygenboutique.com -o items.json -t json".split())