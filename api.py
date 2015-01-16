#!/usr/bin/env python3
import csv
import datetime
import io
import math
import os
import pickle
import queue
import re
import sys
import threading

import requests


class PixivApi:
    _session = ''
    _phpsessid = ''

    def __init__(self):
        while True:
            if os.path.exists('session'):
                # load session from file
                session = self.load_session()
                if not self.check_expired(session):
                    # not expired
                    self._session = session
                    self._phpsessid = self.get_phpsessid()
                    break

            # failed to load a valid session from file
            session = self.login()
            self._session = session
            self.save_session()

            self._phpsessid = self.get_phpsessid()
            break

    def load_session(self):
        """
        load sessio from file

        Return:
            a session object
        """
        with open('session', 'rb') as f:
            cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
            session = requests.Session()
            session.cookies = cookies
        print('Load session')
        return session

    def check_expired(self, session):
        """
        Check whether the sission is expired

        Retrun:
            True if the session is expired
            False if the session is valid
        """
        print('Check session')
        r = session.get('http://www.pixiv.net')
        if r.url != 'http://www.pixiv.net/mypage.php':
            print('Session expired')
            return True
        print('Session valid')
        return False

    def login(self):
        """
        loging to pixiv, set _SEESION

        Return:
            a session object
        """
        while True:
            pixiv_id = input('Input your pixiv id:')
            password = input('Input your pixiv password:')
            s = requests.Session()
            data = {
                'mode': 'login',
                'skip': '1',
                'pixiv_id': pixiv_id,
                'pass': password
            }
            r = s.post('http://www.pixiv.net/login.php', data=data)
            if r.url == 'http://www.pixiv.net/mypage.php':
                print('Login successfully')
                return s
            else:
                print('Login failed')

    def save_session(self):
        """save session cookie in "session" file"""
        with open('session', 'wb') as f:
            pickle.dump(requests.utils.dict_from_cookiejar(self._session.cookies), f)
        print('Save session')

    def get_phpsessid(self):
        cookies = requests.utils.dict_from_cookiejar(self._session.cookies)
        return cookies['PHPSESSID']

    @property
    def phpsessid(self):
        return self._phpsessid

    @property
    def session(self):
        return self._session


    def parse_page(self, url, params):
        result = []
        r = requests.get(url, params=params)
        if r.text:
            result.extend(r.text.strip().split('\n'))
        print('Got page:', r.url)
        return result

    def get_user_illusts(self, id, number=9999):
        """
        fetch illusts by user id

        Args:
            id: the user's pixiv id string
            number: the number of illusts want to fetch

        Return:
            a list contains the csv data
        """
        total_page = math.ceil(number / 50)
        results = []
        for page in range(1, total_page + 1):
            url = 'http://spapi.pixiv.net/iphone/member_illust.php'
            params = {
                'id': id,
                'p': page,
                'PHPSESSID': self.phpsessid
            }
            current_page_result = self.parse_page(url, params)
            if current_page_result:
                results.extend(current_page_result)
            if len(current_page_result) < 50:
                break
        return results[:number]

    def get_ranking_illusts(self, number=100, content='all', mode='day'):
        """
        fetch illusts by ranking

        Args:
            number: the number of illust want to fetch
            content:[all, male, female, original]
            mode:[day, week, month]

        Return:
            a list contains the csv data
        """
        total_page = math.ceil(number / 50)
        results = []
        for page in range(1, total_page + 1):
            url = 'http://spapi.pixiv.net/iphone/ranking.php'
            params = {
                'content': content,
                'p': page,
                'mode': mode
            }
            current_page_result = self.parse_page(url, params)
            if current_page_result:
                results.extend(current_page_result)
            if len(current_page_result) < 50:
                break

        return results

    def get_history_ranking_illusts(self, number=100, date=None, mode='daily'):
        """
        fetch history illusts by ranking

        Args:
            number: the number of illust want to fetch
            date: a string represent the date, eg:"150113"
            mode: the ranking type,
                  [daily, weekly, monthly, male, female, rookie, daily_r18, weekly_r18, male_r18, female_r18, r18g]
        Return:
            a list contains the csv data
        """
        current_yaer, current_month, current_day = str(datetime.date.today()).split('-')
        if date is None:
            year, month, day = current_yaer, current_month, current_day
        else:
            year, month, day = '20' + date[:2], date[2:4], date[4:]

        total_page = math.ceil(number / 50)
        results = []
        for page in range(1, total_page + 1):
            url = 'http://spapi.pixiv.net/iphone/ranking_log.php'
            params = {
                'Date_Year': year,
                'Date_Month': month,
                'Date_Day': day,
                'mode': mode,
                'p': page,
                'PHPSESSID': self.phpsessid
            }
            current_page_result = self.parse_page(url, params)
            if current_page_result:
                results.extend(current_page_result)
            if len(current_page_result) < 50:
                break
        return results