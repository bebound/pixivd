#!/usr/bin/env python3
from abc import abstractmethod, ABCMeta


class PixivModel(object):
    """
    store illust/novel data

    Attribute
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def from_data(self, data):
        """parse the data to a dict"""
        pass


class PixivIllustModel(PixivModel):
    @classmethod
    def create_illust_from_data(cls, data):
        illust = cls()
        for k, v in data.items():
            setattr(illust, k, v)
        illust.user_id = str(illust.user['id'])
        illust.user_name = illust.user['name']
        if data['meta_single_page']:
            illust.image_urls = [data['meta_single_page']['original_image_url']]
            if data['type'] == 'ugoira':
                illust.image_urls = [
                    illust.image_urls[0].replace('img-original', 'img-zip-ugoira')
                        .replace('ugoira0.jpg', 'ugoira600x600.zip')
                        .replace('ugoira0.png', 'ugoira600x600.zip')]
        elif data['meta_pages']:
            illust.image_urls = [i['image_urls']['original'] for i in data['meta_pages']]
        return illust

    @classmethod
    def from_data(cls, data_list):
        """parse data to dict contains illust information

        Return:
            result: a list of instance contains illust information
        """
        illusts = []
        for data in list(data_list):
            illust = cls.create_illust_from_data(data)
            illusts.append(illust)
        return illusts
