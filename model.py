#!/usr/bin/env python3
from abc import abstractmethod, ABCMeta

from utils import get_image_url_per_illust


class PixivModel(object):
    """
    store illust/novel data

    Attribute
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def from_data(self, data):
        """parse the data to a dict"""
        pass


class PixivIllustModel(PixivModel):
    @staticmethod
    def extract_common_information(illust, data):
        if 'work' in data:
            illust.rank = str(data['rank'])
            illust.previous_rank = str(data['previous_rank'])
            data = data['work']
        illust.id = str(data['id'])
        illust.user_id = str(data['user']['id'])
        illust.user_name = data['user']['name']
        illust.title = data['title']
        return illust

    @classmethod
    def from_data(cls, data_list):
        """parse data to dict contains illust information

        Return:
            result: a list of instance contains illust information
        """
        illusts = []
        for data in data_list:
            # ranking
            if 'date' in data:
                works = data['works']
                for work in works:
                    illust = cls()
                    cls.extract_common_information(illust, work)
                    image_urls = get_image_url_per_illust(work)
                    illust.image_urls = image_urls
                    illusts.append(illust)

            # user_illusts or illust
            else:
                illust = cls()
                cls.extract_common_information(illust, data)
                image_urls = get_image_url_per_illust(data)
                illust.image_urls = image_urls
                illusts.append(illust)
        return illusts
