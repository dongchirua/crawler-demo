# -*- coding: utf-8 -*-

import os
import re
import pdb

import scrapy

from amazon_page_parser.parsers import DetailParser
from amazon_us_demo.utils import MARKETPLACE_HOST_MAPPING


class DetailLoaderSpider(scrapy.Spider):
    name = 'detail_loader'
    allowed_domains = ['www.amazon.com']
    start_urls = ['https://www.amazon.com/']
    custom_settings = {
        'FIELDS_TO_EXPORT': [
            'asin', 'rank', 'star', 'reviews', 'categories', 'images', 'author', 'bylines',
           'title', 'details', 'feature_bullets', 'book_description', 'product_description'
        ]
    }

    def start_requests(self):
        asins_path = getattr(self, 'asins_path', None)
        if asins_path is None:
            self.logger.critical(
                '[InvalidArguments] You must supply "asins_path" argument to run detail_loader spider.')
            return

        marketplace = getattr(self, 'marketplace', 'us').lower()
        if marketplace not in MARKETPLACE_HOST_MAPPING:
            self.logger.critical(
                '[InvalidArguments] Marketplace %s is not supported', marketplace)
            return

        asins_path = os.path.abspath(os.path.expanduser(asins_path))
        if not os.path.exists(asins_path):
            self.logger.critical('[InvalidArguments] Given "asins_path" does not exist!')
            return

        asin_files = self._find_asin_files(asins_path)
        for asin_file in asin_files:
            with open(asin_file) as asin_fh:
                for line in asin_fh:
                    asin = line.strip()
                    if self._is_valid_asin(asin):
                        yield self._generate_asin_url(asin, marketplace)

    def parse(self, response):
        parser = DetailParser(response.text)
        try:
            info = parser.parse()
            info['asin'] = self._extract_asin(response)
            yield info
        except Exception as e:
            self.logger.exception(e)

    def _extract_asin(self, response):
        matched = re.match(r'.*www\.amazon\.com\/dp\/([0-9A-Z]{10}).*', response.url)
        return '' if matched is None or len(matched.groups()) <= 0 else matched.groups()[0]

    def _find_asin_files(self, asins_path):
        asin_files = []
        if os.path.isfile(asins_path):
            asin_files.append(asins_path)
            self.logger.debug('[FoundAsinFile] %s', asins_path)
        else:
            for dirpath, dirnames, filenames in os.walk(asins_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    self.logger.debug('[FoundAsinFile] %s', file_path)
                    asin_files.append(file_path)

        return asin_files

    def _is_valid_asin(self, asin):
        valid = bool(
            asin and not asin.isspace() and re.match('[0-9]{9}[0-9Xx]{1}|[A-Z]{1}[0-9A-Z]{9}', asin))
        if not valid:
            self.logger.info('[InvalidASIN] %s', asin)

        return valid

    def _generate_asin_url(self, asin, marketplace):
        base = 'https://' + MARKETPLACE_HOST_MAPPING[marketplace]
        url = base + '/dp/' + asin
        referer = base + '/s/ref=nb_sb_noss_2?url=search-alias=aps&field-keywords='
        referer = referer + asin

        request = scrapy.Request(url, headers={'Referer': referer})
        # request.meta['dont_redirect'] = True

        return request
