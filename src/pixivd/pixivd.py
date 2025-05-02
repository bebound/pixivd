#!/usr/bin/env python3
"""
pixiv

Usage:
    pixivd
    pixivd <id>...
    pixivd -r [-d | --date=<date>]
    pixivd -u

Arguments:
    <id>                                       user_ids

Options:
    -r                                         Download by ranking
    -d <date> --date <date>                    Target date
    -u                                         Update exist folder
    -h --help                                  Show this screen
    -v --version                               Show version

Examples:
    pixivd 7210261 1980643
    pixivd -r -d 2016-09-24
"""
import datetime
import math
import os
import queue
import re
import sys
import threading
import time
import traceback

import requests
from docopt import docopt
from tqdm import tqdm

from .api import PixivApi
from .i18n import i18n as _
from .model import PixivIllustModel

_THREADING_NUMBER = 10
_finished_download = 0
_CREATE_FOLDER_LOCK = threading.Lock()
_PROGRESS_LOCK = threading.Lock()
_SPEED_LOCK = threading.Lock()
_Global_Download = 0
_error_count = {}
_ILLUST_PER_PAGE = 30
_MAX_ERROR_COUNT = 5

__version__ = '3.0'


def get_default_save_path():
    current_path = os.getcwd()
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


def print_progress(max_size):
    global _finished_download
    pbar = tqdm(total=max_size)

    last = 0
    while _finished_download != max_size:
        pbar.update(_finished_download - last)
        last = _finished_download
        time.sleep(0.5)
    pbar.update(_finished_download - last)
    pbar.close()


def download_file(url, filepath):
    headers = {'Referer': 'https://www.pixiv.net/', 'User-Agent': PixivApi.user_agent}
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


def start_and_wait_download_threading(download_queue, count):
    """start download threading and wait till complete"""
    progress_t = threading.Thread(target=print_progress, args=(count,))
    progress_t.daemon = True
    progress_t.start()
    for i in range(_THREADING_NUMBER):
        download_t = threading.Thread(target=download_threading, args=(download_queue,))
        download_t.daemon = True
        download_t.start()

    progress_t.join()
    download_queue.join()


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
        filename = f'{illustration.rank} - {filename}'
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


def is_manga(illustrate):
    return True if illustrate.is_manga or illustrate.type == 'manga' else False


def download_illustrations(user, data_list, save_path='.', add_user_folder=False, add_rank=False, skip_manga=False):
    """Download illustratons

    Args:
        user: PixivApi()
        data_list: json
        save_path: str, download path of the illustrations
        add_user_folder: bool, whether put the illustration into user folder
        add_rank: bool, add illustration rank at the beginning of filename
    """
    illustrations = PixivIllustModel.from_data(data_list)
    if skip_manga:
        manga_number = sum([is_manga(i) for i in illustrations])
        if manga_number:
            print('skip', manga_number, 'manga')
            illustrations = list(filter(lambda x: not is_manga(x), illustrations))
    download_queue, count = check_files(illustrations, save_path, add_user_folder, add_rank)[0:2]
    if count > 0:
        print(_('Start download, total illustrations '), count)
        global _finished_download, _Global_Download
        _finished_download = 0
        _Global_Download = 0
        start_and_wait_download_threading(download_queue, count)
        print()
    else:
        print(_('There is no new illustration need to download'))


def download_by_user_id(user, user_ids=None):
    save_path = get_default_save_path()
    if not user_ids:
        user_ids = input(_('Input the artist\'s id:(separate with space)')).strip().split(' ')
    for user_id in user_ids:
        print(_('Artists %s') % user_id)
        data_list = user.get_all_user_illustrations(user_id)
        download_illustrations(user, data_list, save_path, add_user_folder=True)


def download_by_ranking(user):
    today = str(datetime.date.today())
    save_path = os.path.join(get_default_save_path(), today + ' ranking')
    data_list = user.get_ranking_illustrations()
    download_illustrations(user, data_list, save_path, add_rank=True)


def download_by_history_ranking(user, date=''):
    if not date:
        date = input(_('Input the date:(eg:2015-07-10)'))
    if not (re.search(r"^\d{4}-\d{2}-\d{2}", date)):
        print(_('[invalid date format]'))
        date = str(datetime.date.today() - datetime.timedelta(days=1))
    save_path = os.path.join(get_default_save_path(), date + ' ranking')
    data_list = user.get_ranking_illustrations(date=date)
    download_illustrations(user, data_list, save_path, add_rank=True)


def artist_folder_scanner(user, user_id_list, save_path, final_list, fast):
    while not user_id_list.empty():
        user_info = user_id_list.get()
        user_id = user_info['id']
        folder = user_info['folder']
        try:
            if fast:
                data_list = []
                offset = 0
                page_result = user.get_all_user_illustrations(user_id, offset, _ILLUST_PER_PAGE)
                if len(page_result) > 0:
                    data_list.extend(page_result)
                    file_path = os.path.join(save_path, folder, data_list[-1]['image_urls']['large'].split('/')[-1])
                    while not os.path.exists(file_path) and len(page_result) == _ILLUST_PER_PAGE:
                        offset += _ILLUST_PER_PAGE
                        page_result = user.get_all_user_illustrations(user_id, offset, _ILLUST_PER_PAGE)
                        data_list.extend(page_result)
                        file_path = os.path.join(save_path, folder, data_list[-1]['image_urls']['large'].split('/')[-1])
                        # prevent rate limit
                        time.sleep(1)
            else:
                data_list = user.get_all_user_illustrations(user_id)
            illustrations = PixivIllustModel.from_data(data_list)
            count, checked_list = check_files(illustrations, save_path, add_user_folder=True, add_rank=False)[1:3]
            if len(sys.argv) < 2 or count:
                try:
                    print(_('Artists %s [%s]') % (folder, count))
                except UnicodeError:
                    print(_('Artists %s ?? [%s]') % (user_id, count))
            with _PROGRESS_LOCK:
                for index in checked_list:
                    final_list.append(data_list[index])
        except Exception:
            traceback.print_exc()
        user_id_list.task_done()


def update_exist(user, fast=True):
    current_path = get_default_save_path()
    final_list = []
    user_id_list = queue.Queue()
    for folder in os.listdir(current_path):
        if os.path.isdir(os.path.join(current_path, folder)):
            user_id = re.search(r'^(\d+) ', folder)
            if user_id:
                user_id = user_id.group(1)
                user_id_list.put({'id': user_id, 'folder': folder})
    for i in range(1):
        # use one thread to prevent Rate Limit in new App API
        scan_t = threading.Thread(target=artist_folder_scanner,
                                  args=(user, user_id_list, current_path, final_list, fast,))
        scan_t.daemon = True
        scan_t.start()
    user_id_list.join()
    download_illustrations(user, final_list, current_path, add_user_folder=True)


def remove_repeat(_):
    """Delete xxxxx.img if xxxxx_p0.img exist"""
    choice = input(_('Dangerous Action: continue?(y/n)'))
    if choice == 'y':
        illust_path = get_default_save_path()
        for folder in os.listdir(illust_path):
            if os.path.isdir(os.path.join(illust_path, folder)):
                if re.search(r'^(\d+) ', folder):
                    path = os.path.join(illust_path, folder)
                    for file_name in os.listdir(path):
                        illustration_id = re.search(r'^\d+\.', file_name)
                        if illustration_id:
                            if os.path.isfile(os.path.join(path
                                    , illustration_id.string.replace('.', '_p0.'))):
                                os.remove(os.path.join(path, file_name))
                                print('Delete', os.path.join(path, file_name))


def main():
    arguments = docopt(__doc__)
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
        print(_(f' Pixiv Downloader {__version__}').center(77, '#'))
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
    sys.exit(main())
