#!/usr/bin/env python3
import copy
import datetime
import os
import queue
import re
import sys
import threading
import time

import math
import requests

from api import PixivApi
from model import PixivIllustModel

import gettext
t = gettext.translation('messages', "locale")
_ = t.gettext

_THREADING_NUMBER = 5
_queue_size = 0
_finished_download = 0
_CREATE_FOLDER_LOCK = threading.Lock()
_PROGRESS_LOCK = threading.Lock()
_SPEED_LOCK = threading.Lock()
_Global_Download = 0


def get_default_save_path():
    current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    file_path = os.path.join(current_path, 'illustrations')
    if not os.path.exists(file_path):
        with _CREATE_FOLDER_LOCK:
            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))
            os.makedirs(file_path)
    return file_path


def get_file_path(illustration, save_path='.'):
    """chose a file path by user id and name, if the current path has a folder start with the user id,
    use the old folder instead

    Args:
        :param save_path:
        :param illustration:

    Return:
        file_path: a string represent complete folder path.

    """
    user_id = illustration.user_id
    user_name = illustration.user_name

    cur_dirs = list(filter(os.path.isfile, os.listdir(save_path)))
    cur_user_ids = [cur_dir.split()[0] for cur_dir in cur_dirs]
    if user_id not in cur_user_ids:
        dir_name = re.sub(r'[<>:"/\\|\?\*]', ' ', user_id + ' ' + user_name)
    else:
        dir_name = list(filter(lambda x: x.split()[0] == user_id, cur_dirs))[0]

    file_path = os.path.join(save_path, dir_name)

    return file_path


def get_speed(t0):
    with _SPEED_LOCK:
        global _Global_Download
        down = _Global_Download
        _Global_Download = 0
    speed = down // t0
    if speed == 0:
        return '0 /s'
    speed /= 8
    units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit = math.floor(math.log(speed, 1024.0))
    speed /= math.pow(1024.0, unit)
    return '%6.2f %s/s' % (speed, units[unit])


def print_progress(download_queue):
    start = time.clock()
    global _finished_download, _queue_size
    while not _finished_download == _queue_size:
        time.sleep(1)
        t0 = time.clock() - start
        start = time.clock()
        number_of_sharp = round(_finished_download / _queue_size * 50)
        number_of_space = 50 - number_of_sharp
        percent = _finished_download / _queue_size * 100
        if number_of_sharp < 21:
            sys.stdout.write('\r[' + '#' * number_of_sharp + ' ' * (number_of_space - 29) +
                             ' %6.2f%% ' % percent + ' ' * 21 + '] (' + str(_finished_download) + '/' +
                             str(_queue_size) + ')' + '[%s]' % get_speed(t0))
        elif number_of_sharp > 29:
            sys.stdout.write('\r[' + '#' * 21 + ' %6.2f%% ' % percent + '#' * (number_of_sharp - 29) +
                             ' ' * number_of_space + '] (' + str(_finished_download) + '/' + str(_queue_size) + ')' +
                             '[%s]' % get_speed(t0))
        else:
            sys.stdout.write('\r[' + '#' * 21 + ' %6.2f%% ' % percent + ' ' * 21 + '] (' + str(_finished_download) +
                             '/' + str(_queue_size) + ')' + '[%s]' % get_speed(t0))


def download_threading(download_queue, save_path='.', add_rank=False, refresh=False):
    headers = {'Referer': 'http://www.pixiv.net/'}
    while not download_queue.empty():
        illustration = download_queue.get()
        failed = False
        for url in illustration.image_urls:
            file_name = url.split('/')[-1]
            if add_rank:
                file_name = illustration.rank + ' - ' + file_name
            file_path = os.path.join(save_path, file_name)
            try:
                if not os.path.exists(file_path) or refresh:
                    with _CREATE_FOLDER_LOCK:
                        if not os.path.exists(os.path.dirname(file_path)):
                            current_dir = os.path.dirname(file_path)
                            while not os.path.exists(os.path.dirname(file_path)):
                                if not os.path.exists(os.path.dirname(current_dir)):
                                    current_dir = os.path.dirname(current_dir)
                                elif not os.path.exists(current_dir):
                                    os.makedirs(current_dir)
                                    current_dir = os.path.dirname(file_path)
                            if not os.path.exists(os.path.dirname(file_path)):
                                os.makedirs(os.path.dirname(file_path))
                    r = requests.get(url, headers=headers, stream=True, timeout=PixivApi.timeout)
                    if r.status_code == requests.codes.ok:
                        with open(file_path, 'wb') as f:
                            total_length = r.headers.get('content-length')
                            if total_length:
                                for chunk in r.iter_content(1024):
                                    f.write(chunk)
                                    with _SPEED_LOCK:
                                        global _Global_Download
                                        _Global_Download += len(chunk)
                            else:
                                f.write(r.content)
                    else:
                        raise ConnectionError(_('Connection error: %s') % r.status_code)
            except KeyboardInterrupt:
                print(_('process cancelled'))
            except ConnectionError as e:
                print(_('%s => %s download failed') % (e, file_name))
            except Exception as e:
                print(_('%s => %s download error, retry') % (e, file_name))
                if os.path.exists(file_path):
                    os.remove(file_path)
                download_queue.put(copy.copy(illustration))
                failed = True
        if failed:
            download_queue.task_done()
            continue
        with _PROGRESS_LOCK:
            global _finished_download
            _finished_download += 1


def start_and_wait_download_trending(download_queue, save_path='.', add_rank=False, refresh=False):
    """start download trending and wait till complete
    :param refresh:
    :param add_rank:
    :param save_path:
    :param download_queue:
    """
    th = []
    for i in range(_THREADING_NUMBER + 1):
        if not i:
            t = threading.Thread(target=print_progress, args=(download_queue,))
            t.start()
        else:
            t = threading.Thread(target=download_threading, args=(download_queue, save_path, add_rank, refresh))
            t.start()
        th.append(t)

    for t in th:
        t.join()


def check_files(illustrations, save_path='.', add_rank=False):
    if len(illustrations) > 0:
        for illustration in illustrations[:]:
            count = len(illustration.image_urls)
            for url in illustration.image_urls:
                file_name = url.split('/')[-1]
                if add_rank:
                    file_name = illustration.rank + ' - ' + file_name
                file_path = os.path.join(save_path, file_name)
                if os.path.exists(file_path):
                    count -= 1
            if not count:
                illustrations.remove(illustration)


def download_illustrations(data_list, save_path='.', add_user_folder=False, add_rank=False, refresh=False):
    illustrations = PixivIllustModel.from_data(data_list)

    if not refresh:
        check_files(illustrations, save_path, add_rank)

    if len(illustrations) > 0:
        print(_('Start download, total illustrations '), len(illustrations))

        if add_user_folder:
            save_path = get_file_path(illustrations[0], save_path)

        download_queue = queue.Queue()
        for illustration in illustrations:
            download_queue.put(illustration)

        global _queue_size, _finished_download, _Global_Download
        _queue_size = len(illustrations)
        _finished_download = 0
        _Global_Download = 0
        start_and_wait_download_trending(download_queue, save_path, add_rank, refresh)

    else:
        print(_('There is no new illustration need to download'))


def download_by_user_id(user):
    save_path = get_default_save_path()
    user_ids = input(_('Input the artist\'s id:(separate with space)'))
    for user_id in user_ids.split(' '):
        print(_('Artists %s ??\n') % user_id)
        data_list = user.get_user_illustrations(user_id)
        download_illustrations(data_list, save_path, add_user_folder=True)


def download_by_ranking(user):
    today = str(datetime.date.today())
    save_path = os.path.join(get_default_save_path(), today + ' ranking')
    data_list = user.get_ranking_illustrations(per_page=100, mode='daily')
    download_illustrations(data_list, save_path, add_rank=True)


def download_by_history_ranking(user):
    date = input(_('Input the date:(eg:2015-07-10)'))
    if not (re.search("^\d{4}-\d{2}-\d{2}", date)):
        print(_('[invalid]'))
        date = str(datetime.date.today())
    save_path = os.path.join(get_default_save_path(), date + ' ranking')
    data_list = user.get_ranking_illustrations(date=date, per_page=100, mode='daily')
    download_illustrations(data_list, save_path, add_rank=True)


def update_exist(user):
    issue_exist(user, False)


def refresh_exist(user):
    issue_exist(user, True)


def issue_exist(user, refresh):
    current_path = get_default_save_path()
    for root, dirs, files in os.walk(current_path):
        try:
            for folder in dirs:
                get_id = re.search('^\d+ ', folder)
                if get_id:
                    get_id = get_id.group().replace(' ', '')
                    try:
                        print(_('Artists %s\n') % folder)
                    except UnicodeError:
                        print(_('Artists %s ??\n') % get_id)
                    save_path = os.path.join(current_path, folder)
                    data_list = user.get_user_illustrations(get_id)
                    download_illustrations(data_list, save_path, refresh=refresh)
        except Exception as e:
            print(e)


def main():
    print(_(' Pixiv Downloader 2.2 ').center(77, '#'))
    user = PixivApi()
    options = {
        '1': download_by_user_id,
        '2': download_by_ranking,
        '3': download_by_history_ranking,
        '4': update_exist,
        '5': refresh_exist
    }

    while True:
        print(_('Which do you want to:'))
        for i in sorted(options.keys()):
            print('\t %s %s' % (i, _(options[i].__name__).replace('_', ' ')))
        choose = input('\t e %s \n:' % _('exit'))
        if choose in [str(i) for i in range(6)]:
            print((' ' + _(options[choose].__name__).replace('_', ' ') + ' ').center(60, '#') + '\n')
            options[choose](user)
            print('\n' + (' ' + _(options[choose].__name__).replace('_', ' ') + _(' finished ')).center(60, '#') + '\n')
        elif choose == 'e':
            break
        else:
            print(_('Wrong input!'))


if __name__ == '__main__':
    sys.exit(main())
