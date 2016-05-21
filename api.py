#!/usr/bin/env python3
import getpass
import json
import os
import re
import sys

import requests

from AESCipher import AESCipher
from i18n import i18n as _


class Pixiv_Get_Error(Exception):
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return 'Failed to get data: ' + self.url


class PixivApi:
    """
    Attribution:
        session_id
        access_token
        user_id: str, login user id
        User_Agent: str, the version of pixiv app
    """
    User_Agent = 'PixivIOSApp/5.8.3'
    session_id = None
    access_token = None
    session = ''
    user_id = ''
    image_sizes = ','.join(['px_128x128', 'px_480mw', 'small', 'medium', 'large'])
    profile_image_sizes = ','.join(['px_170x170', 'px_50x50'])
    timeout = 10
    username = ''
    password = ''

    def __init__(self):
        if os.path.exists('session'):
            if self.load_session():
                self.login(self.username, self.password)
                if self.check_expired():
                    return
        self.login_required()

    def load_session(self):
        loaded_session = None
        cipher = AESCipher()
        with open('session', 'rb') as f:
            enc = f.read()
        try:
            plain = cipher.decrypt(enc).decode()
            loaded_session = json.loads(str(plain))
            self.username = loaded_session['username']
            self.password = loaded_session['passwd']
        finally:
            return loaded_session

    def check_expired(self):
        url = 'https://public-api.secure.pixiv.net/v1/ios_magazine_banner.json'
        print(_('Checking session'), end="", flush=True)

        valid = False
        try:
            r = self._request_pixiv('GET', url)

            if r.status_code in [200, 301, 302]:
                try:
                    respond = json.loads(r.text)
                    valid = respond['status'] == 'success'
                except Exception as e:
                    print(e)
                    valid = False
                finally:
                    pass
        except Exception as e:
            print(e)
        if valid:
            print(_(' [VALID]'))
        else:
            print(_(' [EXPIRED]'))
            self.access_token = None
        return valid

    def save_session(self):
        data = {
            'username': self.username,
            'passwd': self.password
        }
        cipher = AESCipher()
        enc = cipher.encrypt(json.dumps(data))
        with open('session', 'wb') as f:
            f.write(enc)

    def _request_pixiv(self, method, url, headers=None, params=None, data=None, retry=3):
        """
        handle all url request

        Args:
            :param url: str
            :param method: str

        """
        pixiv_headers = {
            'Referer': 'http://www.pixiv.net/',
            'User-Agent': self.User_Agent,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        if self.access_token:
            pixiv_headers.update({'Authorization': 'Bearer {}'.format(self.access_token),
                                  'Cookie': 'PHPSESSID={}'.format(self.session_id)})
        if headers:
            pixiv_headers.update(headers)

        if not self.session:
            self.session = requests.Session()
        try:
            if method == 'GET':
                return self.session.get(url, headers=pixiv_headers, params=params, timeout=self.timeout)
            elif method == 'POST':
                return self.session.post(url, headers=pixiv_headers, params=params, data=data, timeout=self.timeout)
            else:
                raise RuntimeError(_('Unknown Method:'), method)
        except Exception as e:
            if retry > 0:
                return self._request_pixiv(method, url, headers, params, data, retry=retry - 1)
            else:
                raise RuntimeError(_('[ERROR] connection failed!'), e)

    def login(self, username, password):
        """
        logging to Pixiv

        Args:
            :param password: str
            :param username: str

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

        if r.status_code in [200, 301, 302]:
            respond = json.loads(r.text)

            self.access_token = respond['response']['access_token']
            self.user_id = str(respond['response']['user']['id'])

            cookie = r.headers['Set-Cookie']
            self.session_id = re.search(r'PHPSESSID=(.*?);', cookie).group(1)
            # For relogin purpose
            self.password = password
            self.username = username
            self.save_session()
        else:
            raise RuntimeError(_('[ERROR] connection failed!'), r.status_code)

    def login_required(self):
        if not self.access_token:
            print(_('Please login'))
            username = input(_('username:'))
            password = getpass.getpass(_('password:'))
            try:
                self.login(username, password)
            except Exception as e:
                print('Login failed:', end="")
                print(e)
                if input('Retry? y/n') == 'y':
                    self.login_required()
                else:
                    sys.exit()

    @staticmethod
    def parse_result(r):
        """
        parse result from request

        Args:
            :param r:

        Return:
            fetched data in JSON format

        """
        data = json.loads(r.text)
        if data['status'] == 'success':
            return data['response']
        elif ['has_error']:
            raise Pixiv_Get_Error(r.url)
        else:
            raise RuntimeError(_('[ERROR] connection failed!'), r.url, data)

    def get_user_illustrations(self, user_id, per_page=9999, page=1):
        """
        get illustrations by user id

        Args:
            :param user_id: str, pixiv id to search
            :param per_page: int, the number of illustrations want to get
            :param page: int

        Return:
            a list contains dicts, which contains illustrations data
            JSON Sample
            illustrations_data.json

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
        except Pixiv_Get_Error:
            if self.username:
                self.login(self.username, self.password)
            else:
                self.check_expired()
            return self.get_user_illustrations(user_id, per_page, page)

    def get_illustration(self, illustration_id):
        """
        get illustration data

        Args:
            :param illustration_id:

        Return:
            a list contains one dict
            JSON Sample
            dict.json


        """
        self.login_required()
        url = 'https://public-api.secure.pixiv.net/v1/works/{}.json'.format(illustration_id)

        params = {
            'profile_image_sizes': self.profile_image_sizes,
            'image_sizes': self.image_sizes,
            'include_stats': 'true',
            'include_sanity_level': True,
        }
        r = self._request_pixiv('GET', url, params=params)
        return self.parse_result(r)

    def get_ranking_illustrations(self, mode='daily', date='', per_page=100, page=1):
        """
        fetch illustrations by ranking

        Args:
            :param mode: [daily, weekly, monthly, male, female, rookie,
                daily_r18, weekly_r18, male_r18, female_r18, r18g]
            :param date: '2015-04-01'
            :param per_page: int
            :param page: int

        Return:
            a list contains the illustrations data
            JSON Sample
            illustrations_data.json

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
