#!/usr/bin/env python3
"""
pixiv

Usage:
    pixiv.py
    pixiv.py <id>...
    pixiv.py -r [-d | --date=<date>]
    pixiv.py -u

Arguments:
    <id>                                       user_ids

Options:
    -r                                         Download by ranking
    -d <date> --date <date>                    Target date
    -u                                         Update exist folder
    -h --help                                  Show this screen
    -v --version                               Show version

Examples:
    pixiv.py 7210261 1980643
    pixiv.py -r -d 2016-09-24
"""
import datetime
import math
import os
import queue
import re
import sys
import threading
import time

import requests
from docopt import docopt

from api import PixivApi
from i18n import i18n as _
from model import PixivIllustModel

_THREADING_NUMBER = 10
_queue_size = 0
_finished_download = 0
_CREATE_FOLDER_LOCK = threading.Lock()
_PROGRESS_LOCK = threading.Lock()
_SPEED_LOCK = threading.Lock()
_Global_Download = 0
_error_count = {}
_fast_mode_size = 20
_MAX_ERROR_COUNT = 5


def get_default_save_path():
    current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    filepath = os.path.join(current_path, 'illustrations')
    if not os.path.exists(filepath):
        with _CREATE_FOLDER_LOCK:
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))
            os.makedirs(filepath)
    return filepath


def get_speed(elapsed):
    """Get current download speed"""
    with _SPEED_LOCK:
        global _Global_Download
        down = _Global_Download
        _Global_Download = 0
    speed = down / elapsed
    if speed == 0:
        return '%8.2f /s' % 0
    units = [' B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit = math.floor(math.log(speed, 1024.0))
    speed /= math.pow(1024.0, unit)
    return '%6.2f %s/s' % (speed, units[unit])


def print_progress():
    global _finished_download, _queue_size
    start = time.time()
    while not _finished_download == _queue_size:
        time.sleep(1)
        elapsed = time.time() - start
        start = time.time()
        number_of_sharp = round(_finished_download / _queue_size * 50)
        number_of_space = 50 - number_of_sharp
        percent = _finished_download / _queue_size * 100
        if number_of_sharp < 21:
            sys.stdout.write('\r[' + '#' * number_of_sharp + ' ' * (number_of_space - 29) +
                             ' %6.2f%% ' % percent + ' ' * 21 + '] (' + str(_finished_download) +
                             '/' + str(_queue_size) + ')' + '[%s]  ' % get_speed(elapsed))
        elif number_of_sharp > 29:
            sys.stdout.write('\r[' + '#' * 21 + ' %6.2f%% ' % percent + '#' *
                             (number_of_sharp - 29) + ' ' * number_of_space + '] (' +
                             str(_finished_download) + '/' + str(_queue_size) + ')' +
                             '[%s]  ' % get_speed(elapsed))
        else:
            sys.stdout.write('\r[' + '#' * 21 + ' %6.2f%% ' % percent + ' ' * 21 + '] (' +
                             str(_finished_download) + '/' + str(_queue_size) + ')' +
                             '[%s]  ' % get_speed(elapsed))


def download_file(url, filepath):
    headers = {'Referer': 'http://www.pixiv.net/'}
    r = requests.get(url, headers=headers, stream=True, timeout=PixivApi.timeout)
    if r.status_code == requests.codes.ok:
        total_length = r.headers.get('content-length')
        if total_length:
            data = []
            for chunk in r.iter_content(1024 * 16):
                data.append(chunk)
                with _SPEED_LOCK:
                    global _Global_Download
                    _Global_Download += len(chunk)
            with open(filepath, 'wb') as f:
                list(map(f.write, data))
    else:
        raise ConnectionError('\r', _('Connection error: %s') % r.status_code)


def download_threading(download_queue):
    global _finished_download
    while not download_queue.empty():
        illustration = download_queue.get()
        filepath = illustration['path']
        filename = illustration['file']
        url = illustration['url']
        count = _error_count.get(url, 0)
        if count < _MAX_ERROR_COUNT:
            if not os.path.exists(filepath):
                with _CREATE_FOLDER_LOCK:
                    if not os.path.exists(os.path.dirname(filepath)):
                        os.makedirs(os.path.dirname(filepath))
                try:
                    download_file(url, filepath)
                    with _PROGRESS_LOCK:
                        _finished_download += 1
                except Exception as e:
                    if count < _MAX_ERROR_COUNT:
                        print(_('%s => %s download error, retry') % (e, filename))
                        download_queue.put(illustration)
                        _error_count[url] = count + 1
        else:
            print(url, 'reach max retries, canceled')
            with _PROGRESS_LOCK:
                _finished_download += 1
        download_queue.task_done()


def start_and_wait_download_threading(download_queue):
    """start download threading and wait till complete"""
    if len(sys.argv) < 2:
        progress_t = threading.Thread(target=print_progress)
        progress_t.daemon = True
        progress_t.start()
    for i in range(_THREADING_NUMBER):
        download_t = threading.Thread(target=download_threading, args=(download_queue,))
        download_t.daemon = True
        download_t.start()

    download_queue.join()
    if len(sys.argv) < 2:
        progress_t.join()


def get_filepath(url, illustration, save_path='.', add_user_folder=False, add_rank=False):
    """return (filename,filepath)"""

    if add_user_folder:
        user_id = illustration.user_id
        user_name = illustration.user_name
        current_path = get_default_save_path()
        cur_dirs = list(filter(os.path.isdir, [os.path.join(current_path, i) for i in os.listdir(current_path)]))
        cur_user_ids = [os.path.basename(cur_dir).split()[0] for cur_dir in cur_dirs]
        if user_id not in cur_user_ids:
            dir_name = re.sub(r'[<>:"/\\|\?\*]', ' ', user_id + ' ' + user_name)
        else:
            dir_name = list(i for i in cur_dirs if os.path.basename(i).split()[0] == user_id)[0]
        save_path = os.path.join(save_path, dir_name)

    filename = url.split('/')[-1]
    if add_rank:
        filename = illustration.rank + ' - ' + filename
    filepath = os.path.join(save_path, filename)
    return filename, filepath


def check_files(illustrations, save_path='.', add_user_folder=False, add_rank=False):
    download_queue = queue.Queue()
    index_list = []
    count = 0
    if illustrations:
        last_i = -1
        for index, illustration in enumerate(illustrations):
            if not illustration.image_urls:
                continue
            else:
                for url in illustration.image_urls:
                    filename, filepath = get_filepath(url, illustration, save_path, add_user_folder, add_rank)
                    if os.path.exists(filepath):
                        continue
                    else:
                        if last_i != index:
                            last_i = index
                            index_list.append(index)
                        download_queue.put({'url': url, 'file': filename, 'path': filepath})
                        count += 1
    return download_queue, count, index_list


def count_illustrations(illustrations):
    return sum(len(i.image_urls) for i in illustrations)


def download_illustrations(user, data_list, save_path='.', add_user_folder=False, add_rank=False):
    """Download illustratons

    Args:
        user: PixivApi()
        data_list: json
        save_path: str, download path of the illustrations
        add_user_folder: bool, whether put the illustration into user folder
        add_rank: bool, add illustration rank at the beginning of filename
    """
    illustrations = PixivIllustModel.from_data(data_list, user)
    download_queue, count = check_files(illustrations, save_path, add_user_folder, add_rank)[0:2]
    if count > 0:
        print(_('Start download, total illustrations '), count)
        global _queue_size, _finished_download, _Global_Download
        _queue_size = count
        _finished_download = 0
        _Global_Download = 0
        start_and_wait_download_threading(download_queue)
        print()
    else:
        print(_('There is no new illustration need to download'))


def download_by_user_id(user, user_ids=None):
    save_path = get_default_save_path()
    if not user_ids:
        user_ids = input(_('Input the artist\'s id:(separate with space)')).split(' ')
    for user_id in user_ids:
        print(_('Artists %s\n') % user_id)
        data_list = user.get_user_illustrations(user_id)
        download_illustrations(user, data_list, save_path, add_user_folder=True)


def download_by_ranking(user):
    today = str(datetime.date.today())
    save_path = os.path.join(get_default_save_path(), today + ' ranking')
    data_list = user.get_ranking_illustrations(per_page=100, mode='daily')
    download_illustrations(user, data_list, save_path, add_rank=True)


def download_by_history_ranking(user, date=''):
    if not date:
        date = input(_('Input the date:(eg:2015-07-10)'))
    if not (re.search("^\d{4}-\d{2}-\d{2}", date)):
        print(_('[invalid]'))
        date = str(datetime.date.today())
    save_path = os.path.join(get_default_save_path(), date + ' ranking')
    data_list = user.get_ranking_illustrations(date=date, per_page=100, mode='daily')
    download_illustrations(user, data_list, save_path, add_rank=True)


def artist_folder_scanner(user, user_id_list, save_path, final_list, fast):
    while not user_id_list.empty():
        user_info = user_id_list.get()
        user_id = user_info['id']
        folder = user_info['folder']
        try:
            per_page = 9999
            if fast:
                per_page = _fast_mode_size
                data_list = user.get_user_illustrations(user_id, per_page=per_page)
                if len(data_list) > 0:
                    file_path = os.path.join(save_path, folder, data_list[-1]['image_urls']['large'].split('/')[-1])
                    while not os.path.exists(file_path) and per_page <= len(data_list):
                        per_page += _fast_mode_size
                        data_list = user.get_user_illustrations(user_id, per_page=per_page)
                        file_path = os.path.join(save_path, folder, data_list[-1]['image_urls']['large'].split('/')[-1])
            else:
                data_list = user.get_user_illustrations(user_id, per_page=per_page)
            illustrations = PixivIllustModel.from_data(data_list, user)
            count, checked_list = check_files(illustrations, save_path, add_user_folder=True, add_rank=False)[1:3]
            if len(sys.argv) < 2 or count:
                try:
                    print(_('Artists %s [%s]') % (folder, count))
                except UnicodeError:
                    print(_('Artists %s ?? [%s]') % (user_id, count))
            with _PROGRESS_LOCK:
                for index in checked_list:
                    final_list.append(data_list[index])
        except Exception as e:
            print(e)
        user_id_list.task_done()


def update_exist(user, fast=True):
    current_path = get_default_save_path()
    final_list = []
    user_id_list = queue.Queue()
    for folder in os.listdir(current_path):
        if os.path.isdir(os.path.join(current_path, folder)):
            user_id = re.search('^(\d+) ', folder)
            if user_id:
                user_id = user_id.group(1)
                user_id_list.put({'id': user_id, 'folder': folder})
    for i in range(_THREADING_NUMBER):
        scan_t = threading.Thread(target=artist_folder_scanner,
                                  args=(user, user_id_list, current_path, final_list, fast,))
        scan_t.daemon = True
        scan_t.start()
    user_id_list.join()
    download_illustrations(user, final_list, current_path, add_user_folder=True)


def remove_repeat(user):
    """Delete xxxxx.img if xxxxx_p0.img exist"""
    choice = input(_('Dangerous Action: continue?(y/n)'))
    if choice == 'y':
        illust_path = get_default_save_path()
        for folder in os.listdir(illust_path):
            if os.path.isdir(os.path.join(illust_path, folder)):
                if re.search('^(\d+) ', folder):
                    path = os.path.join(illust_path, folder)
                    for file_name in os.listdir(path):
                        illustration_id = re.search('^\d+\.', file_name)
                        if illustration_id:
                            if os.path.isfile(os.path.join(path
                                    , illustration_id.string.replace('.', '_p0.'))):
                                os.remove(os.path.join(path, file_name))
                                print('Delete', os.path.join(path, file_name))


def main():
    user = PixivApi()
    if len(sys.argv) > 1:
        print(datetime.datetime.now().strftime('%X %x'))
        ids = arguments['<id>']
        is_rank = arguments['-r']
        date = arguments['--date']
        is_update = arguments['-u']
        if ids:
            download_by_user_id(user, ids)
        elif is_rank:
            if date:
                date = date[0]
                download_by_history_ranking(user, date)
            else:
                download_by_ranking(user)
        elif is_update:
            update_exist(user)
        print(datetime.datetime.now().strftime('%X %x'))
    else:
        print(_(' Pixiv Downloader 2.4 ').center(77, '#'))
        options = {
            '1': download_by_user_id,
            '2': download_by_ranking,
            '3': download_by_history_ranking,
            '4': update_exist,
            '5': remove_repeat
        }

        while True:
            print(_('Which do you want to:'))
            for i in sorted(options.keys()):
                print('\t %s %s' % (i, _(options[i].__name__).replace('_', ' ')))
            choose = input('\t e %s \n:' % _('exit'))
            if choose in [str(i) for i in range(1, len(options) + 1)]:
                print((' ' + _(options[choose].__name__).replace('_', ' ') + ' ').center(60, '#') + '\n')
                if choose == 4:
                    options[choose](user, False)
                else:
                    options[choose](user)
                print('\n' + (' ' + _(options[choose].__name__).replace('_', ' ') + _(' finished ')).center(60,
                                                                                                            '#') + '\n')
            elif choose == 'e':
                break
            else:
                print(_('Wrong input!'))


if __name__ == '__main__':
    arguments = docopt(__doc__, version='pixiv 2.4')
    sys.exit(main())
