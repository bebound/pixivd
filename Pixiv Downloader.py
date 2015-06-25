#!/usr/bin/env python3
import datetime
import os
import queue
import re
import sys
import threading

import requests

from api import PixivApi
from model import PixivIllustModel

_THREADING_NUMBER = 5
_queue_size = 0
_finished_download = 0
_FILE_LOCK = threading.Lock()
_CREATE_FOLDER_LOCK = threading.Lock()
_PROGRESS_LOCK = threading.Lock()


def skip_download(illusts):
    """remove the item which is in the 'downloaded.txt'"""
    if os.path.exists('downloaded.txt'):
        with open('downloaded.txt') as f:
            downloaded = [line.strip() for line in f.readlines()]
        for illust in illusts:
            if illust.illust_id in downloaded:
                illusts.remove(illust)


def get_file_path(illust, save_path='.'):
    """chose a file path by user id and name, if the current path has a folder start with the user id,
    use the old folder instead

    Return:
        file_path: a string represent complete folder path.
    """
    user_id = illust.user_id
    user_name = illust.user_name

    cur_dirs = list(filter(os.path.isfile, os.listdir(save_path)))
    cur_user_ids = [dir.split()[0] for dir in cur_dirs]
    if user_id not in cur_user_ids:
        dir_name = re.sub(r'[<>:"/\\|\?\*]', ' ', user_id + ' ' + user_name)
    else:
        dir_name = list(filter(lambda x: x.split()[0] == user_id, cur_dirs))[0]

    file_path = os.path.join(save_path, dir_name)

    return file_path


def add_downloadedtxt(illust):
    """Append illust to dowloaded.txt"""
    with _FILE_LOCK:
        with open('downloaded.txt', 'a') as f:
            f.write(illust.illust_id + '\n')


def print_progress():
    with _PROGRESS_LOCK:
        global _finished_download
        _finished_download += 1

        number_of_sharp = round(_finished_download / _queue_size * 60)
        number_of_space = 60 - number_of_sharp
        sys.stdout.write('\r' + str(_finished_download) + '/' + str(
            _queue_size) + '[' + '#' * number_of_sharp + ' ' * number_of_space + ']')


def download_threading(download_queue, user, save_path='.'):
    headers = {'Referer': 'http://www.pixiv.net/'}
    while not download_queue.empty():
        illust = download_queue.get()
        try:
            for url in illust.original_urls:
                file_name = url.split('/')[-1]
                cur_file_path = os.path.join(save_path, file_name)
                if not os.path.exists(cur_file_path):
                    with _CREATE_FOLDER_LOCK:
                        if not os.path.exists(os.path.dirname(cur_file_path)):
                            os.makedirs(os.path.dirname(cur_file_path))
                    r = user.session.get(url, headers=headers, stream=True)
                    if r.status_code == requests.codes.ok:
                        temp_chunk = r.content
                        with open(cur_file_path, 'wb') as f:
                            f.write(temp_chunk)
                add_downloadedtxt(illust)
            print_progress()
        except Exception as e:
            print(e)
            download_queue.put(illust)
        finally:
            download_queue.task_done()


def start_and_wait_download_threadings(download_queue, user, save_path='.'):
    """start download threadings and wait till complete"""
    th = []
    for _ in range(_THREADING_NUMBER):
        t = threading.Thread(target=download_threading, args=(download_queue, user, save_path))
        t.start()
        th.append(t)

    for t in th:
        t.join()

    print('\nFininsh')


def download_illusts(data_list, user, save_path='.', add_user_folder=False):
    illusts = []
    for data in data_list:
        illust = PixivIllustModel.from_data(data)
        illusts.append(illust)

    # skip_download(illusts)
    if len(illusts) > 0:
        print('Start download, total illusts', len(illusts))

        if add_user_folder:
            save_path = get_file_path(illusts[0], save_path)

        download_queue = queue.Queue()
        for illust in illusts:
            download_queue.put(illust)

        global _queue_size, _finished_download
        _queue_size = len(illusts)
        _finished_download = 0

        start_and_wait_download_threadings(download_queue, user, save_path)

    else:
        print('There is no new illust need to download')


def download_by_user_id(user):
    current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    save_path = os.path.join(current_path, 'illustrations')
    user_id = input('Input the user id:')
    data_list = user.get_user_illusts(user_id)
    download_illusts(data_list, user, save_path, True)


def download_by_ranking(user):
    today = str(datetime.date.today()).replace('-', '')
    current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    save_path = os.path.join(os.path.join(current_path, 'illustrations'), today + ' ranking')
    data_list = user.get_ranking_illusts(100)
    download_illusts(data_list, user, save_path)


def download_by_history_ranking(user):
    date = input('Input the date:(eg:150101)')
    current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    save_path = os.path.join(os.path.join(current_path, 'illustrations'), date + ' ranking')
    data_list = user.get_history_ranking_illusts(100, date)
    download_illusts(data_list, user, save_path)


def main():
    print('Pixiv Downloader 2.1'.center(80, '#'))
    user = PixivApi()
    options = {
        '1': download_by_user_id,
        '2': download_by_ranking,
        '3': download_by_history_ranking
    }

    while True:
        choose = input('Which do you want to download:\n1 From user id\n2 From ranking\n3 From history ranking\n')

        if choose in [str(i) for i in range(1, 4)]:
            options[choose](user)
        else:
            print('Wrong input!')


if __name__ == '__main__':
    sys.exit(main())
