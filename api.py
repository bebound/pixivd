#!/usr/bin/env python3
import datetime
import hashlib
import json
import os
from base64 import urlsafe_b64encode
from hashlib import sha256
from urllib.parse import urlencode

import requests
from secrets import token_urlsafe

from AESCipher import AESCipher
from i18n import i18n as _


class Pixiv_Get_Error(Exception):
    def __init__(self, url, Err=None):
        self.url = url
        self.error = Err

    def __str__(self):
        return 'Failed to get data: ' + self.url


class PixivApi:
    """
    Attribution:
        access_token
        user_id: str, login user id
        User_Agent: str, the version of pixiv app
    """
    user_agent = 'PixivIOSApp/6.4.0'
    hash_secret = '28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c'
    session = ''
    user_id = ''
    image_sizes = ','.join(['px_128x128', 'px_480mw', 'small', 'medium', 'large'])
    profile_image_sizes = ','.join(['px_170x170', 'px_50x50'])
    timeout = 20
    access_token = ''
    refresh_token = ''
    client_id = 'MOBrBDS8blbauoSck0ZfDbtuzpyT'
    client_secret = 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj'
    auth_token_url = 'https://oauth.secure.pixiv.net/auth/token'

    def __init__(self):
        if os.path.exists('session'):
            if self.load_session():
                self.auth()
        self.login_required()

    def load_session(self):
        cipher = AESCipher()
        with open('session', 'rb') as f:
            enc = f.read()
        try:
            plain = cipher.decrypt(enc)
            loaded_session = json.loads(str(plain))
            self.access_token = loaded_session['access_token']
            self.refresh_token = loaded_session['refresh_token']
            return True
        except:
            print("error when load session, please delete session file and try again.")

    def save_session(self):
        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token
        }
        cipher = AESCipher()
        enc = cipher.encrypt(json.dumps(data))
        with open('session', 'wb') as f:
            f.write(enc)

    def _request_pixiv(self, method, url, headers=None, params=None, data=None, retry=3):
        """
        handle all url request

        Args:
            method: str, http method

        """
        local_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
        pixiv_headers = {
            'Referer': 'http://www.pixiv.net/',
            'User-Agent': self.user_agent,
            'X-Client-Time': local_time,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Client-Hash': hashlib.md5((local_time + self.hash_secret).encode('utf-8')).hexdigest(),
        }
        if self.access_token:
            pixiv_headers.update({'Authorization': 'Bearer {}'.format(self.access_token), })
        if headers:
            pixiv_headers.update(headers)

        if not self.session:
            self.session = requests.Session()
        try:
            if method == 'GET':
                r = self.session.get(url, headers=pixiv_headers, params=params, timeout=self.timeout)
                r.encoding = 'utf-8'
                return r
            elif method == 'POST':
                return self.session.post(url, headers=pixiv_headers, params=params, data=data, timeout=self.timeout)
            else:
                raise RuntimeError(_('Unknown Method:'), method)
        except Exception as e:
            if retry > 0:
                return self._request_pixiv(method, url, headers, params, data, retry=retry - 1)
            else:
                raise RuntimeError(_('[ERROR] connection failed!'), e)

    def parse_token(self, data):
        return data["access_token"], data["refresh_token"]

    def login(self):
        """
        logging to Pixiv

        Return:
            a requests session object

        """
        REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
        LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"

        def s256(data):
            """S256 transformation method."""
            return urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode("ascii")

        def oauth_pkce(transform):
            """Proof Key for Code Exchange by OAuth Public Clients (RFC7636)."""

            code_verifier = token_urlsafe(32)
            code_challenge = transform(code_verifier.encode("ascii"))

            return code_verifier, code_challenge

        code_verifier, code_challenge = oauth_pkce(s256)
        login_params = {
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "client": "pixiv-android",
        }

        print(
            f"Please open {LOGIN_URL}?{urlencode(login_params)}, and following steps in https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362 to get code")

        try:
            code = input("Please input code: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        r = requests.post(
            self.auth_token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "include_policy": "true",
                "redirect_uri": REDIRECT_URI,
            },
            headers={"User-Agent": self.user_agent},
        )
        self.access_token, self.refresh_token = self.parse_token(r.json())
        self.save_session()

    def auth(self):
        """Login with password, or use the refresh_token to acquire a new bearer token"""
        local_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
        headers = {
            'User-Agent': self.user_agent,
            'X-Client-Time': local_time,
            'X-Client-Hash': hashlib.md5((local_time + self.hash_secret).encode('utf-8')).hexdigest(),
        }
        data = {
            'get_secure_url': 1,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }

        r = self._request_pixiv('POST', self.auth_token_url, headers=headers, data=data)
        self.access_token, self.refresh_token = self.parse_token(r.json())
        self.save_session()

    def login_required(self):
        if not self.access_token:
            print(_('Please login'))
            self.login()

    @staticmethod
    def parse_result(r):
        """
        parse result from request

        Args:
            r: requests response object

        Return:
            fetched data in JSON format

        """
        data = json.loads(r.text)
        if data['status'] == 'success':
            return data['response']
        elif data['has_error']:
            raise Pixiv_Get_Error(r.url, data['errors'])
        else:
            raise RuntimeError(_('[ERROR] connection failed!'), r.url, data)

    def get_all_user_illustrations(self, user_id):
        r = []
        done = False
        page = 1
        while not done:
            page_data = self.get_user_illustrations(user_id, page=page)
            if page_data:
                r.extend(page_data)
                page += 1
            else:
                done = True
        return r

    def get_user_illustrations(self, user_id, per_page=5000, page=1):
        """
        get illustrations by user id

        Args:
            :param user_id: str, pixiv id to search
            :param per_page: int, the number of illustrations want to get
            :param page: int

        Return:
            a list of dict
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
        url = 'https://public-api.secure.pixiv.net/v1/users/{}/works.json'.format(user_id)

        params = {
            'page': page,
            'per_page': per_page,
            'include_stats': True,
            'include_sanity_level': True,
            'image_sizes': self.image_sizes,
            'profile_image_sizes': self.profile_image_sizes,
        }

        r = self._request_pixiv('GET', url, params=params)
        try:
            return self.parse_result(r)
        except Pixiv_Get_Error as e:
            if e.error['system']:
                if e.error['system']['code'] == 971:
                    print(_('Artist %s Fetch Failed, %s') % (user_id, e.error['system']['message']))
                    return []
            if e.error['system']:
                if e.error['system']['message'] == 404:
                    return []

    def get_illustration(self, illustration_id):
        """
        get illustration data

        Return:
            a list of dict
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
        self.login_required()
        url = 'https://public-api.secure.pixiv.net/v1/works/{}.json'.format(illustration_id)

        params = {
            'profile_image_sizes': self.profile_image_sizes,
            'image_sizes': self.image_sizes,
            'include_stats': 'true',
            'include_sanity_level': 'true',
        }
        r = self._request_pixiv('GET', url, params=params)
        return self.parse_result(r)

    def get_ranking_illustrations(self, mode='daily', date='', per_page=100, page=1):
        """
        fetch illustrations by ranking

        Args:
            mode: [daily, weekly, monthly, male, female, rookie,
                daily_r18, weekly_r18, male_r18, female_r18, r18g]
            date: '2015-04-01'
            per_page: int
            page: int

        Return:
            a list of dict
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

    def set_timeout(self, timeout):
        self.timeout = timeout
