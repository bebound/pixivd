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


def get_default_save_path():
    current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    filepath = os.path.join(current_path, 'illustrations')
    if not os.path.exists(filepath):
        with _CREATE_FOLDER_LOCK:
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))
            os.makedirs(filepath)
    return filepath


def get_speed(t0):
    """Get current download speed"""
    with _SPEED_LOCK:
        global _Global_Download
        down = _Global_Download
        _Global_Download = 0
    speed = down / t0
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
        t0 = time.time() - start
        start = time.time()
        number_of_sharp = round(_finished_download / _queue_size * 50)
        number_of_space = 50 - number_of_sharp
        percent = _finished_download / _queue_size * 100
        if number_of_sharp < 21:
            sys.stdout.write('\r[' + '#' * number_of_sharp + ' ' * (number_of_space - 29) +
                             ' %6.2f%% ' % percent + ' ' * 21 + '] (' + str(_finished_download) + '/' +
                             str(_queue_size) + ')' + '[%s]  ' % get_speed(t0))
        elif number_of_sharp > 29:
            sys.stdout.write('\r[' + '#' * 21 + ' %6.2f%% ' % percent + '#' * (number_of_sharp - 29) +
                             ' ' * number_of_space + '] (' + str(_finished_download) + '/' + str(_queue_size) + ')' +
                             '[%s]  ' % get_speed(t0))
        else:
            sys.stdout.write('\r[' + '#' * 21 + ' %6.2f%% ' % percent + ' ' * 21 + '] (' + str(_finished_download) +
                             '/' + str(_queue_size) + ')' + '[%s]  ' % get_speed(t0))


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


def download_threading(download_queue, save_path='.', add_user_folder=False, add_rank=False):
    while not download_queue.empty():
        illustration = download_queue.get()
        for url in illustration.image_urls:
            filename, filepath = get_filepath(url, illustration, save_path, add_user_folder, add_rank)
            try:
                if not os.path.exists(filepath):
                    with _CREATE_FOLDER_LOCK:
                        if not os.path.exists(os.path.dirname(filepath)):
                            os.makedirs(os.path.dirname(filepath))
                    download_file(url, filepath)

                    with _PROGRESS_LOCK:
                        global _finished_download
                        _finished_download += 1

            except Exception as e:
                print(_('\r%s => %s download error, retry') % (e, filename))
                download_queue.put(illustration)
                break

        download_queue.task_done()


def start_and_wait_download_threading(download_queue, save_path='.', add_user_folder=False, add_rank=False):
    """start download threading and wait till complete"""
    p = threading.Thread(target=print_progress)
    p.daemon = True
    p.start()
    for i in range(_THREADING_NUMBER):
        t = threading.Thread(target=download_threading,
                             args=(download_queue, save_path, add_user_folder, add_rank))
        t.daemon = True
        t.start()

    download_queue.join()
    p.join()


def get_filepath(url, illustration, save_path='.', add_user_folder=False, add_rank=False):
    """return (filename,filepath)"""

    if add_user_folder:
        user_id = illustration.user_id
        user_name = illustration.user_name
        current_path = get_default_save_path()

        cur_dirs = list(filter(os.path.isdir, [os.path.join(current_path, i) for i in os.listdir(current_path)]))
        cur_user_ids = [cur_dir.split('/')[-1].split()[0] for cur_dir in cur_dirs]

        if user_id not in cur_user_ids:
            dir_name = re.sub(r'[<>:"/\\|\?\*]', ' ', user_id + ' ' + user_name)
        else:
            dir_name = list(i for i in cur_dirs if i.split('/')[-1].split()[0] == user_id)[0]
        save_path = os.path.join(save_path, dir_name)

    filename = url.split('/')[-1]
    if add_rank:
        filename = illustration.rank + ' - ' + filename
    filepath = os.path.join(save_path, filename)

    return filename, filepath


def check_files(illustrations, save_path='.', add_user_folder=False, add_rank=False):
    if illustrations:
        for illustration in illustrations.copy():
            for url in illustration.image_urls.copy():
                _, filepath = get_filepath(url, illustration, save_path, add_user_folder, add_rank)
                if os.path.exists(filepath):
                    illustration.image_urls.remove(url)
            if not illustration.image_urls:
                illustrations.remove(illustration)


def count_illustrations(illustrations):
    return sum(len(i.image_urls) for i in illustrations)


def download_illustrations(data_list, save_path='.', add_user_folder=False, add_rank=False):
    """Download illustratons

    Args:
        data_list: json
        save_path: str, download path of the illustrations
        add_user_folder: bool, whether put the illustration into user folder
        add_rank: bool, add illustration rank at the beginning of filename
    """
    illustrations = PixivIllustModel.from_data(data_list)
    check_files(illustrations, save_path, add_user_folder, add_rank)

    if count_illustrations(illustrations) > 0:
        print(_('Start download, total illustrations'), count_illustrations(illustrations))

        download_queue = queue.Queue()
        for illustration in illustrations:
            download_queue.put(illustration)

        global _queue_size, _finished_download, _Global_Download
        _queue_size = count_illustrations(illustrations)
        _finished_download = 0
        _Global_Download = 0
        start_and_wait_download_threading(download_queue, save_path, add_user_folder, add_rank)
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
        download_illustrations(data_list, save_path, add_user_folder=True)


def download_by_ranking(user):
    today = str(datetime.date.today())
    save_path = os.path.join(get_default_save_path(), today + ' ranking')
    data_list = user.get_ranking_illustrations(per_page=100, mode='daily')
    download_illustrations(data_list, save_path, add_rank=True)


def download_by_history_ranking(user, date=''):
    if not date:
        date = input(_('Input the date:(eg:2015-07-10)'))
    if not (re.search("^\d{4}-\d{2}-\d{2}", date)):
        print(_('[invalid]'))
        date = str(datetime.date.today())
    save_path = os.path.join(get_default_save_path(), date + ' ranking')
    data_list = user.get_ranking_illustrations(date=date, per_page=100, mode='daily')
    download_illustrations(data_list, save_path, add_rank=True)


def update_exist(user):
    current_path = get_default_save_path()
    for folder in os.listdir(get_default_save_path()):
        if os.path.isdir(os.path.join(current_path, folder)):
            try:
                user_id = re.search('^(\d+) ', folder)
                if user_id:
                    user_id = user_id.group(1)
                    try:
                        print(_('Artists %s\n') % folder, end='')
                    except UnicodeError:
                        print(_('Artists %s ??\n') % user_id, end='')
                    save_path = current_path
                    data_list = user.get_user_illustrations(user_id)
                    download_illustrations(data_list, save_path, add_user_folder=True)
            except Exception as e:
                print(e)


def remove_repeat(user):
    """Delete xxxxx.img if xxxxx_p0.img exist"""
    choice = input(_('Dangerous Action: continue?(y/n)'))
    if choice == 'y':
        illust_path = get_default_save_path()
        for folder in os.listdir(illust_path):
            if os.path.isdir(os.path.join(illust_path, folder)):
                if re.search('^(\d+) ', folder):
                    path = os.path.join(illust_path, folder)
                    for f in os.listdir(path):
                        illustration_id = re.search('^\d+\.', f)
                        if illustration_id:
                            if os.path.isfile(os.path.join(path, illustration_id.string.replace('.', '_p0.'))):
                                os.remove(os.path.join(path, f))
                                print('Delete', os.path.join(path, f))


def main():
    print(_(' Pixiv Downloader 2.4 ').center(77, '#'))
    user = PixivApi()

    if len(sys.argv) > 1:
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
    else:
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
