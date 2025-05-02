#!/usr/bin/env python3
import json
from base64 import urlsafe_b64encode
from hashlib import sha256
from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import urlencode

import requests
from pixivpy3 import *

from .AESCipher import AESCipher
from .i18n import i18n as _


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
    aapi = AppPixivAPI()
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
    session_path = Path(__file__).parent / 'data' / 'session'

    def __init__(self):
        self.ensure_session_dir()
        self.login_required()

    def ensure_session_dir(self):
        if not Path(self.session_path).parent.exists():
            self.session_path.parent.mkdir()

    def load_session(self):
        cipher = AESCipher()
        with open(self.session_path, 'rb') as f:
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
        with open(self.session_path, 'wb') as f:
            f.write(enc)

    def parse_token(self, data):
        return data["access_token"], data["refresh_token"]

    def login(self):
        """
        logging to Pixiv
        doc: https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362

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
            f"Please open {LOGIN_URL}?{urlencode(login_params)}\n, and following steps in https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362 to get code")

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
        print(f'refresh token: {self.refresh_token}')
        self.refresh()

    def refresh(self):
        """Use refresh token to get new access token"""
        # self.aapi.auth(refresh_token='cKwCinT4vVbRy4kOitoQTA7Q1lhjBr69tGy44fI-3Ho')
        self.aapi.auth(refresh_token=self.refresh_token)
        self.access_token, self.refresh_token = self.aapi.access_token, self.aapi.refresh_token
        self.save_session()

    def login_required(self):
        if self.session_path.exists():
            if self.load_session():
                self.refresh()

        if not self.access_token:
            print(_('Please login'))
            self.login()

    def get_all_user_illustrations(self, user_id, offset=0, size=-1):
        """

        :param user_id: str
        :param offset: int
        :param size: int, max result length, if < 0, return all
        :return:
         [
            {
              "id": 92990893,
              "title": "-",
              "type": "illust",
              "image_urls": {
                "square_medium": "https://i.pximg.net/c/360x360_70/img-master/img/2021/09/25/00/05/35/92990893_p0_square1200.jpg",
                "medium": "https://i.pximg.net/c/540x540_70/img-master/img/2021/09/25/00/05/35/92990893_p0_master1200.jpg",
                "large": "https://i.pximg.net/c/600x1200_90/img-master/img/2021/09/25/00/05/35/92990893_p0_master1200.jpg"
              },
              "caption": "",
              "restrict": 0,
              "user": {
                "id": 22124330,
                "name": "\u8d85\u51f6\u306e\u72c4\u7490\u5361",
                "account": "swd3e22",
                "profile_image_urls": {
                  "medium": "https://i.pximg.net/user-profile/img/2017/01/10/13/28/42/11988991_bae951a38d31d217fa1eceedc0aafdbe_170.jpg"
                },
                "is_followed": true
              },
              "tags": [
                {
                  "name": "\u5973\u306e\u5b50",
                  "translated_name": "girl"
                },
                {
                  "name": "\u843d\u66f8",
                  "translated_name": "doodle"
                },
                {
                  "name": "closers",
                  "translated_name": null
                },
                {
                  "name": "\u30b7\u30e7\u30fc\u30c8\u30d1\u30f3\u30c4",
                  "translated_name": "short pants"
                },
                {
                  "name": "\u9b45\u60d1\u306e\u9854",
                  "translated_name": "alluring face"
                },
                {
                  "name": "Mirae",
                  "translated_name": null
                },
                {
                  "name": "\u80f8\u30dd\u30c1",
                  "translated_name": "hanging breasts"
                },
                {
                  "name": "\u898b\u305b\u30cf\u30a4\u30ec\u30b0\u30d1\u30f3\u30c4/\u30c1\u30e7\u30fc\u30ab\u30fc/\u30a2\u30fc\u30e0\u30ab\u30d0\u30fc/\u30cf\u30fc\u30cd\u30b9",
                  "translated_name": null
                },
                {
                  "name": "\u7740\u8863\u5de8\u4e73/\u80f8\u306b\u624b/\u30a2\u30e1\u30ea\u30ab\u30f3\u30b9\u30ea\u30fc\u30d6/\u3078\u305d\u51fa\u3057/\u307a\u305f\u3093\u5ea7\u308a",
                  "translated_name": null
                },
                {
                  "name": "\u30c1\u30e3\u30c3\u30af\u4e0b\u308d\u3057/\u6c57/\u64ab\u3067\u56de\u3057\u305f\u3044\u304a\u8179/\u3082\u3082\u3077\u304f",
                  "translated_name": null
                }
              ],
              "tools": [],
              "create_date": "2021-09-25T00:05:35+09:00",
              "page_count": 1,
              "width": 1329,
              "height": 1919,
              "sanity_level": 4,
              "x_restrict": 0,
              "series": null,
              "meta_single_page": {
                "original_image_url": "https://i.pximg.net/img-original/img/2021/09/25/00/05/35/92990893_p0.jpg"
              },
              "meta_pages": [],
              "total_view": 45615,
              "total_bookmarks": 8179,
              "is_bookmarked": false,
              "visible": true,
              "is_muted": false,
              "total_comments": 28
            }
         ]

        """

        r = []
        done = False
        cur_size = 0

        while not done:
            data = self.aapi.user_illusts(user_id, offset=offset)
            try:
                r.extend(data['illusts'])
            except:
                print(data)
            offset += 30
            cur_size += 30
            if not data['next_url'] or (0 <= size <= cur_size):
                done = True
        return r[:size] if size >= 0 else r

    def get_illustration(self, illustration_id):
        """
        get illustration data

        Return: list of illustration instances
        """
        self.login_required()
        return [self.aapi.illust_detail(illustration_id)['illust']]

    def get_ranking_illustrations(self, mode='day', date='', total_page=3):
        """
        fetch illustrations by ranking

        Args:
            mode: [day, week, month, day_male, day_female, week_original, week_rookie, day_manga,
                   day_r18, day_male_r18, day_female_r18, week_r18, week_r18g]
            date: '2015-04-01'
            per_page: int
            page: int

        Return: list of illustration data, same as `get_all_user_illustrations()`
        """
        self.login_required()
        r = []
        page = 0
        offset = 0
        while page <= total_page:
            data = self.aapi.illust_ranking(mode, date=date, offset=offset)
            r.extend(data['illusts'])
            offset += 30
            page += 1
        for index, i in enumerate(r):
            i['rank'] = index + 1
        return r

    def set_timeout(self, timeout):
        self.timeout = timeout
