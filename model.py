#!/usr/bin/env python3
from abc import abstractmethod, ABCMeta
import csv
import io

from utils import PivivUtils


class PixivModel(object):
    """
    store illust/novel data

    Attribute
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def parse(self, data):
        """parse the data to a dict"""
        pass


class PixivIllustModel(PixivModel):
    @classmethod
    def from_data(cls, data):
        """parse data to dict contains illust information

        Return:
            result: a dict contains illust information
        """
        data = data.replace('\x00', '')
        reader = csv.reader(io.StringIO(data))
        content = list(reader)[0]
        illust = cls()
        illust.illust_id = content[0]
        illust.user_id = content[1]
        illust.illust_ext = content[2]
        illust.title = content[3]
        illust.image_server = content[4]
        illust.user_name = content[5]
        illust.illust128 = content[6]
        illust.illust480 = content[9]
        illust.time = content[12]
        illust.tags = content[13]
        illust.software = content[14]
        illust.vote = content[15]
        illust.point = content[16]
        illust.view_count = content[17]
        illust.description = content[18][1:]
        # pages '' if page is 0
        illust.pages = content[19]
        illust.bookmarks = content[22]
        illust.comment = content[23]
        illust.user_login_id = content[24]
        # is_r18:0 is safe, 1 is R-18, 2 is R-18G
        illust.is_r18 = content[26]
        # novel_series_id:blank for illustrations and novels not part of a series
        illust.novel_series_id = content[26]
        illust.user_profile_image_url = content[29]

        original_urls = PivivUtils.get_original_links(illust)
        illust.original_urls = original_urls
        return illust
