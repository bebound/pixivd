#!/usr/bin/env python3
import json
import getpass
import re

import requests

from utils import Pixiv_Get_Error


class PixivApi:
    """
    Attribution:
        session_id
        access_token
        user_id: str, login user id
    """
    session_id = None
    access_token = None
    user_id = ''
    image_sizes = ','.join(['px_128x128', 'px_480mw', 'small', 'medium', 'large'])
    profile_image_sizes = ','.join(['px_170x170', 'px_50x50'])
    timeout=10

    def __init__(self):
        self.session=''

    def _request_pixiv(self, method, url, headers=None, params=None, data=None):
        """
        handle all url request
        """
        pixiv_headers = {
            'Referer': 'http://www.pixiv.net/',
            'User-Agent': 'PixivIOSApp/5.7.2',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        if self.access_token:
            pixiv_headers.update({'Authorization': 'Bearer {}'.format(self.access_token),
                                  'Cookie': 'PHPSESSID={}'.format(self.session_id)})
        if headers:
            pixiv_headers.update(headers)

        if not self.session:
            self.session=requests.Session()

        if method == 'GET':
            return self.session.get(url, headers=pixiv_headers, params=params, timeout=self.timeout)
        elif method == 'POST':
            return self.session.post(url, headers=pixiv_headers, params=params, data=data, timeout=self.timeout)
        else:
            raise RuntimeError('Unknown Method:', method)

    def login(self, username, password):
        """
        logging to Pixiv

        Return:
            a session object
        """
        url = 'https://oauth.secure.pixiv.net/auth/token'

        data = {
            'username': username,
            'password': password,
            'grant_type': 'password',
            'client_id': 'bYGKuGVw91e0NMfPGp44euvGt59s',
            'client_secret': 'HP3RmkgAmEGro0gn1x9ioawQE8WMfvLXDz3ZqxpK',
        }

        r = self._request_pixiv('POST', url, data=data)

        if not r.status_code in [200, 301, 302]:
            raise RuntimeError('[ERROR] login() failed!')

        respond = json.loads(r.text)

        self.access_token = respond['response']['access_token']
        self.user_id = str(respond['response']['user']['id'])

        cookie = r.headers['Set-Cookie']
        self.session_id = re.search(r'PHPSESSID=(.*?);', cookie).group(1)

    def login_required(self):
        if not self.access_token:
            print('Please login')
            username = input('Please input your Pixiv username:')
            password = getpass.getpass('Please input your Pixiv username:')
            self.login(username, password)

    def parse_result(self, r):
        """
        parse result from request
        """
        data = json.loads(r.text)
        if data['status'] == 'success':
            return data['response']
        else:
            raise Pixiv_Get_Error(r.url)

    def get_user_illusts(self, id, per_page=9999, page=1):
        """
        get illusts by user id

        Args:
            id: str, pixiv id to search
            number: int, the number of illusts want to get

        Return:
            a list contains dicts, which contains illusts data
            [
                {
                    'image_urls': {
                        'small': 'http://i3.pixiv.net/c/150x150/img-master/img/2015/07/09/00/05/01/51320366_p0_master1200.jpg',
                        'large': 'http://i3.pixiv.net/img-original/img/2015/07/09/00/05/01/51320366_p0.jpg',
                        'medium': 'http://i3.pixiv.net/c/600x600/img-master/img/2015/07/09/00/05/01/51320366_p0_master1200.jpg',
                        'px_480mw': 'http://i3.pixiv.net/c/480x960/img-master/img/2015/07/09/00/05/01/51320366_p0_master1200.jpg',
                        'px_128x128': 'http://i3.pixiv.net/c/128x128/img-master/img/2015/07/09/00/05/01/51320366_p0_square1200.jpg'
                    },
                    'type': 'illustration',
                    'favorite_id': 0,
                    'width': 800,
                    'stats': {
                        'favorited_count': {
                            'private': 236,
                            'public': 3246
                        },
                        'views_count': 62043,
                        'commented_count': 54,
                        'score': 25741,
                        'scored_count': 2600
                    },
                    'book_style': 'none',
                    'content_type': None,
                    'is_liked': False,
                    'metadata': None,
                    'age_limit': 'all-age',
                    'user': {
                        'is_following': True,
                        'name': 'KD',
                        'id': 395595,
                        'account': 'cadillac',
                        'is_friend': False,
                        'profile': None,
                        'is_follower': False,
                        'profile_image_urls': {
                            'px_50x50': 'http://i2.pixiv.net/img20/profile/cadillac/8457709_s.jpg'
                        },
                        'is_premium': None,
                        'stats': None
                    },
                    'title': 'ドルフィンシンフォニー',
                    'sanity_level': 'white',
                    'reuploaded_time': '2015-07-09 00:05:01',
                    'tools': [
                        'Photoshop',
                        'SAI'
                    ],
                    'id': 51320366,
                    'publicity': 0,
                    'created_time': '2015-07-09 00:05:01',
                    'page_count': 1,
                    'is_manga': False,
                    'height': 1131,
                    'caption': '今年もミニスカとthe太ももの季節がやってきました！',
                    'tags': [
                        '女子高生',
                        'オリジナル',
                        'セーラー服',
                        'イルカ',
                        '黒ハイソックス',
                        'MDR-Z1000',
                        '青',
                        'ヘッドホン'
                    ]
                },XXX
            ]


        """
        self.login_required()
        url = 'https://public-api.secure.pixiv.net/v1/users/{}/works.json'.format(id)

        params = {
            'page': page,
            'per_page': per_page,
            'include_stats': True,
            'include_sanity_level': True,
            'image_sizes': self.image_sizes,
            'profile_image_sizes': self.profile_image_sizes,
        }

        r = self._request_pixiv('GET', url, params=params)
        return self.parse_result(r)

    def get_illust(self, illust_id):
        """
        get illust data

        Args:
            illust id: str, illust id

        Return:
            a list contains one dict
            [
                {
                    'image_urls': {
                        'small': 'http://i1.pixiv.net/c/150x150/img-master/img/2015/06/24/00/07/22/51055528_p0_master1200.jpg',
                        'large': 'http://i1.pixiv.net/img-original/img/2015/06/24/00/07/22/51055528_p0.jpg',
                        'medium': 'http://i1.pixiv.net/c/600x600/img-master/img/2015/06/24/00/07/22/51055528_p0_master1200.jpg',
                        'px_480mw': 'http://i1.pixiv.net/c/480x960/img-master/img/2015/06/24/00/07/22/51055528_p0_master1200.jpg',
                        'px_128x128': 'http://i1.pixiv.net/c/128x128/img-master/img/2015/06/24/00/07/22/51055528_p0_square1200.jpg'
                    },
                    'type': 'illustration',
                    'favorite_id': 0,
                    'width': 1000,
                    'stats': {
                        'favorited_count': {
                            'private': 469,
                            'public': 5767
                        },
                        'views_count': 139847,
                        'commented_count': 175,
                        'score': 53870,
                        'scored_count': 5466
                    },
                    'book_style': 'right_to_left',
                    'content_type': None,
                    'is_liked': False,
                    'metadata': None,
                    'age_limit': 'all-age',
                    'user': {
                        'is_following': True,
                        'name': 'KD',
                        'id': 395595,
                        'account': 'cadillac',
                        'is_friend': False,
                        'profile': None,
                        'is_follower': False,
                        'profile_image_urls': {
                            'px_50x50': 'http://i2.pixiv.net/img20/profile/cadillac/8457709_s.jpg'
                        },
                        'is_premium': None,
                        'stats': None
                    },
                    'title': 'ゆき',
                    'sanity_level': 'white',
                    'reuploaded_time': '2015-06-24 00:07:22',
                    'tools': [
                        'Photoshop',
                        'SAI'
                    ],
                    'id': 51055528,
                    'publicity': 0,
                    'created_time': '2015-06-24 00:07:22',
                    'page_count': 1,
                    'is_manga': False,
                    'height': 1414,
                    'caption': '感谢Facebook网友的写真参考https://www.facebook.com/profile.php?id=1272330679\r\nWorldCosplay- http://worldcosplay.net/photo/3499488',
                    'tags': [
                        '女子高生',
                        'オリジナル',
                        'セーラー服',
                        '黒髪ロング',
                        '模写',
                        'オリジナル5000users入り'
                    ]
                }
            ]
        """
        url = 'https://public-api.secure.pixiv.net/v1/works/{}.json'.format(illust_id)

        params = {
            'profile_image_sizes': self.profile_image_sizes,
            'image_sizes': self.image_sizes,
            'include_stats': 'true',
            'include_sanity_level': True,
        }
        r = self._request_pixiv('GET', url, params=params)
        return self.parse_result(r)

    def get_ranking_illusts(self, mode='daily', date='', per_page=100, page=1):
        """
        fetch illusts by ranking

        Args:
            mode: [daily, weekly, monthly, male, female, rookie, daily_r18, weekly_r18, male_r18, female_r18, r18g]
            date: '2015-04-01'
            per_page: int
            page: int

        Return:
            a list contains the illusts data
            [
                {
                'mode': 'daily',
                'date': '2015-07-10',
                'content': 'all',
                'works': [
                    {
                        'rank': 1,
                        'previous_rank': 7,
                        'work': {
                            'image_urls': {
                                'small': 'http://i3.pixiv.net/c/150x150/img-master/img/2015/07/09/00/05/01/51320366_p0_master1200.jpg',
                                'large': 'http://i3.pixiv.net/img-original/img/2015/07/09/00/05/01/51320366_p0.jpg',
                                'medium': 'http://i3.pixiv.net/c/600x600/img-master/img/2015/07/09/00/05/01/51320366_p0_master1200.jpg',
                                'px_480mw': 'http://i3.pixiv.net/c/480x960/img-master/img/2015/07/09/00/05/01/51320366_p0_master1200.jpg',
                                'px_128x128': 'http://i3.pixiv.net/c/128x128/img-master/img/2015/07/09/00/05/01/51320366_p0_square1200.jpg'
                            },
                            'type': 'illustration',
                            'favorite_id': None,
                            'width': 800,
                            'stats': {
                                'favorited_count': {
                                    'private': None,
                                    'public': None
                                },
                                'views_count': 42718,
                                'commented_count': None,
                                'score': 6392,
                                'scored_count': 644
                            },
                            'book_style': 'none',
                            'content_type': None,
                            'is_liked': None,
                            'metadata': None,
                            'age_limit': 'all-age',
                            'user': {
                                'is_following': None,
                                'name': 'KD',
                                'id': 395595,
                                'account': 'cadillac',
                                'is_friend': None,
                                'profile': None,
                                'is_follower': None,
                                'profile_image_urls': {
                                    'px_170x170': 'http://i2.pixiv.net/img20/profile/cadillac/8457709.jpg',
                                    'px_50x50': 'http://i2.pixiv.net/img20/profile/cadillac/8457709_s.jpg'
                                },
                                'is_premium': None,
                                'stats': None
                            },
                            'title': 'ドルフィンシンフォニー',
                            'sanity_level': 'white',
                            'reuploaded_time': '2015-07-09 00:05:01',
                            'tools': None,
                            'id': 51320366,
                            'publicity': 0,
                            'created_time': '2015-07-09 00:05:00',
                            'page_count': 1,
                            'is_manga': None,
                            'height': 1131,
                            'caption': None,
                            'tags': [
                                '女子高生',
                                'オリジナル',
                                'セーラー服',
                                'イルカ',
                                '黒ハイソックス',
                                'MDR-Z1000',
                                '青',
                                'ヘッドホン'
                            ]
                        }
                    },XXX]
                }
            ]

        """
        self.login_required()
        url = 'https://public-api.secure.pixiv.net/v1/ranking/all'
        params = {
            'mode': mode,
            'page': page,
            'per_page': per_page,
            'include_stats': True,
            'include_sanity_level': True,
            'image_sizes': self.image_sizes,
            'profile_image_sizes': self.profile_image_sizes,
        }
        if date:
            params['date'] = date

        r = self._request_pixiv('GET', url, params=params)
        return self.parse_result(r)

    def set_timeout(self,timeout):
        self.timeout=timeout
