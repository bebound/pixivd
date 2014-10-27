import csv
import io
import os
import pickle
import queue
import re
import threading

import requests

SESSION = ''
PHPSESSID = ''
skip_download = []
THREADING_NUMBER = 5
SAVE_PATH = os.path.dirname(os.path.abspath(__file__))
queue_size = 0
finished_download = 0
PROGRESS_LOCK = threading.Lock()
FILE_LOCK = threading.Lock()


def save_session():
    with open('session', 'wb') as f:
        pickle.dump(requests.utils.dict_from_cookiejar(SESSION.cookies), f)
        print('Save session')


def login():
    """loging to pixiv, set SEESION and save seesion to file."""
    ok = 0
    s = requests.session()
    print("Please input the login information：")
    while not ok:
        Pixiv_ID = input("Pixiv ID:")
        password = input("Password:")
        data = {
            'mode': 'login',
            'skip': '1',
            'pixiv_id': Pixiv_ID,
            'pass': password
        }
        r = s.post('http://www.pixiv.net/login.php', data=data)
        if r.url == 'http://www.pixiv.net/mypage.php':
            ok = 1

    global SESSION
    SESSION = s
    save_session()


def load_session():
    """load sessio from file, if the cookie is expired, call login()"""
    global SESSION
    with open('session', 'rb') as f:
        cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
        SESSION = requests.Session()
        SESSION.cookies = cookies
        print('Load session')
        if check_expired():
            login()


def check_expired():
    print('Checking expired')
    r = SESSION.get('http://www.pixiv.net')
    if r.url != 'http://www.pixiv.net/mypage.php':
        return True
    return False


def get_PHPSESSID():
    global PHPSESSID
    cookies = requests.utils.dict_from_cookiejar(SESSION.cookies)
    PHPSESSID = cookies['PHPSESSID']


def login_or_load_sesson():
    """set SESSION and PHPSESSID"""
    if not os.path.exists('session'):
        login()
    else:
        load_session()
    get_PHPSESSID()


def update_skip_download():
    """create the skip list for download"""
    if os.path.exists('downloaded.txt'):
        for line in open('downloaded.txt'):
            skip_download.append(line.strip())
    else:
        with open('downloaded.txt', 'wb'):
            pass


def url_generator(user):
    """generate http://spapi.pixiv.net urls for user

    Args:
        user: a string represent the user ID.
    """
    page = 1
    base_url = 'http://spapi.pixiv.net/iphone/member_illust.php?id='
    url_without_page = base_url + user + "&PHPSESSID=" + PHPSESSID
    url = url_without_page
    while True:
        yield url
        page += 1
        url = url_without_page + '&p=' + str(page)


def parse_line(line):
    """parse lines to dict contains illust information

    Return:
        result: a dict contains illust information
    """
    line = line.replace('\x00', '')
    reader = csv.reader(io.StringIO(line))
    content = list(reader)[0]
    result = {}
    result['illust_id'] = content[0]
    result['user_id'] = content[1]
    result['illust_ext'] = content[2]
    result['title'] = content[3]
    result['image_server'] = content[4]
    result['user_name'] = content[5]
    result['illust128'] = content[6]
    result['illust480'] = content[9]
    result['time'] = content[12]
    result['tags'] = content[13]
    result['software'] = content[14]
    result['vote'] = content[15]
    result['point'] = content[16]
    result['view_count'] = content[17]
    result['description'] = content[18][1:]
    result['pages'] = content[19]
    result['bookmarks'] = content[22]
    result['user_login_id'] = content[24]
    result['user_profile_image_url'] = content[29]
    return result


def parse_page(html):
    illust_list = []
    lines = html.strip().split('\n')
    for line in lines:
        illust_list.append(parse_line(line))
    return illust_list


def get_user_illust_list(user):
    """get user illust list

    Return:
        user_illust: a list
    """
    user_illust = []
    page = 1
    for url in url_generator(user):
        print('Getting page:', page)
        r = requests.get(url)
        if not r.text:
            break
        else:
            user_illust.extend(parse_page(r.text))
        page += 1
    user_illust = list(filter(lambda x: x['illust_id'] not in skip_download, user_illust))
    return user_illust


def old_url(illust, page=None):
    base_url = illust['illust480'][:illust['illust480'].find(r'mobile/')]
    if page is None:
        file_name = illust['illust_id'] + '.' + illust['illust_ext']
    else:
        file_name = illust['illust_id'] + '_p' + str(page) + '.' + illust['illust_ext']
    return base_url + file_name


def new_url(illust, page=None):
    base_url = illust['illust480'][:illust['illust480'].find(r'_480mw') - len(illust['illust_id'])]
    if page is None:
        base_url = base_url.replace('c/480x960/img-master/', 'img-original/')
        file_name = illust['illust_id'] + '_p0.' + illust['illust_ext']
    else:
        base_url = base_url.replace('480x960', '1200x1200')
        file_name = illust['illust_id'] + '_p' + str(page) + '_master1200.' + illust['illust_ext']
    return base_url + file_name


def get_real_url(illust):
    """A generator returns the illust download url"""
    if (illust['pages'] == ''):
        if 'mobile' in illust['illust480']:
            yield old_url(illust)
        else:
            yield new_url(illust)
    else:
        pages = int(illust['pages'])
        for i in range(pages):
            if 'mobile' in illust['illust480']:
                yield old_url(illust, i)
            else:
                yield old_url(illust, i)


def add_downloadedtxt(illust):
    """Append illust to dowloaded.txt"""
    with FILE_LOCK:
        with open('downloaded.txt', 'a') as f:
            f.write(illust['illust_id'] + '\n')


def print_progress():
    global finished_download
    with PROGRESS_LOCK:
        finished_download += 1
        print(finished_download, '/', queue_size)


def get_file_path(illust):
    """chose a file path by user id and name, if the current path has a folder start with the user id,
    use the old folder instead

    Return:
        file_path: a string represent complete folder path.
    """
    user_id = illust['user_id']
    user_name = illust['user_name']

    cur_dirs = list(filter(os.path.isfile, os.listdir(SAVE_PATH)))
    cur_user_ids = [dir.split()[0] for dir in cur_dirs]
    if user_id not in cur_user_ids:
        dir_name = re.sub(r'[<>:"/\\|\?\*]', ' ', user_id + ' ' + user_name)
    else:
        dir_name = list(filter(lambda x: x.split()[0] == user_id, cur_dirs))[0]

    file_path = os.path.join(SAVE_PATH, dir_name)

    if not os.path.exists(file_path):
        os.makedirs(file_path)

    return file_path


def download_threading(download_queue, file_path):
    headers = {'Referer': 'http://www.pixiv.net/'}
    while not download_queue.empty():
        illust = download_queue.get()
        for url in get_real_url(illust):
            file_name = url.split('/')[-1]
            cur_file_path = os.path.join(file_path, file_name)
            if not os.path.exists(cur_file_path):
                r = SESSION.get(url, headers=headers, stream=True)
                if r.status_code == requests.codes.ok:
                    temp_chunk = r.content
                    with open(cur_file_path, 'wb') as f:
                        f.write(temp_chunk)
            print('Download complete:', file_name)
            add_downloadedtxt(illust)
        print_progress()


def start_threadings(download_queue, file_path):
    th = []
    for i in range(THREADING_NUMBER):
        t = threading.Thread(target=download_threading, args=(download_queue, file_path))
        t.start()
        th.append(t)
    for t in th:
        t.join()


def download_illusts(illusts):
    """start download illusts

    Args:
        illusts: a list contains the illusts information to be download.
    """
    download_queue = queue.Queue()
    for illust in illusts:
        download_queue.put(illust)
    file_path = get_file_path(illusts[0])
    start_threadings(download_queue, file_path)


def download_user_illust(user):
    """get user illusts and start download illusts"""
    info = 'Downloading user ID:' + user
    print(info.center(80, '#'))
    update_skip_download()
    illusts = get_user_illust_list(user)
    print('Total illust:', len(illusts))

    global queue_size, finished_download
    queue_size = len(illusts)
    finished_download = 0

    if queue_size > 0:
        print('Start download')
        download_illusts(illusts)
    print('Finished')


def main():
    print(SAVE_PATH)
    print('Pixiv Downloader 2.0 by:KK'.center(80, '#'))
    login_or_load_sesson()
    users = input("Please input Pixiv IDs(seperate with space):").split()
    for user in users:
        download_user_illust(user)


if __name__ == '__main__':
    main()