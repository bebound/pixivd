import urllib
import http.cookiejar
import re
import os
import csv
import io
import html.parser
from bs4 import BeautifulSoup
import threading
import queue
import http.client


fetch_timeout = 10
downloaded = []
PHPSESSID = ''
illustQuene = queue.Queue()
downloadIllustList = []
curIllustNumber = 0
totalIllust = 0
curFilePath = ''
curIllustNumberLock = threading.Lock()
fileLock = threading.Lock()


def getAllIllustID(userID):
    global curFilePath

    if os.path.exists('downloaded.txt'):
        for line in open('downloaded.txt', 'r'):
            downloaded.append(line.strip())
    else:
        with open('downloaded.txt', 'wb'):
            pass
    baseUrl = "http://spapi.pixiv.net/iphone/member_illust.php?id=" + str(userID) + "&PHPSESSID=" + PHPSESSID

    page = 1
    while True:
        url = baseUrl + "&p=" + str(page)
        print(url)
        htmlSrc = urlOpener.open(url).read().decode('utf-8')
        if htmlSrc:
            for line in htmlSrc.split('\n'):
                if line:
                    tempIllust = parseIllust(line)
                    if tempIllust['illustID'] in downloaded:
                        print(tempIllust['illustID'], "already saved")
                    else:
                        downloadIllustList.append(tempIllust)
                        print(tempIllust['illustID'], "added")
        else:
            print("获取完成".center(80, '*'))
            break

        page += 1

    if downloadIllustList:
        curUserName = downloadIllustList[0]['userName']
        global curFilePath
        curFilePath = str(os.path.abspath(userID) + ' ' + curUserName)
        if not os.path.isdir(userID + ' ' + curUserName):
            os.mkdir(userID + ' ' + curUserName)

    global totalIllust, curIllustNumber
    totalIllust = len(downloadIllustList)
    curIllustNumber = 0
    print('total', len(downloadIllustList))
    for i in downloadIllustList:
        illustQuene.put(i)


def downloadAll():
    urlOpener.addheaders = [('Referer', r'http://www.pixiv.net/')]
    th = []
    for i in range(5):
        t = threading.Thread(target=downloadIllust)
        t.start()
        th.append(t)
    for i in th:
        i.join()
    print('Finished')


def downloadIllust():
    global curIllustNumber
    while not illustQuene.empty():
        illust = illustQuene.get()
        try:
            if (illust and illust['pages'] == ''):
                fileName = illust['illustID'] + '.' + illust['illustExt']
                filePath = curFilePath
                filePath += "\\" + fileName

                if not os.path.exists(filePath):
                    trueIllustUrl = illust['illust480'][:illust['illust480'].find(r'mobile/')]
                    trueIllustUrl += fileName
                    print('Getting', trueIllustUrl)
                    tempFile = urlOpener.open(trueIllustUrl).read()
                    with open(filePath, 'wb') as file:
                        file.write(tempFile)

                print(fileName, 'Saved')

            else:
                pages = int(illust['pages'])
                for i in range(pages):
                    fileName = illust['illustID'] + '_p' + str(i) + '.' + illust['illustExt']
                    filePath = curFilePath
                    filePath += "\\" + fileName
                    if not os.path.exists(filePath):
                        trueIllustUrl = illust['illust480'][:illust['illust480'].find(r'mobile/')]
                        trueIllustUrl += fileName
                        print('Getting', trueIllustUrl)
                        tempFile = urlOpener.open(trueIllustUrl).read()
                        with open(filePath, 'wb') as file:
                            file.write(tempFile)

                    print(fileName, 'Saved')

            with fileLock:
                with open("downloaded.txt", "a") as myfile:
                    myfile.write(illust['illustID'] + '\n')

            downloadProgress()
            downloaded.append(illust)

        except  Exception as e:
            print(e)
            illustQuene.put(illust)

        finally:
            illustQuene.task_done()


def downloadProgress():
    global curIllustNumber
    with curIllustNumberLock:
        curIllustNumber += 1
        print('Progress:', curIllustNumber, '/', totalIllust)


def parseIllust(line):
    reader = csv.reader(io.StringIO(line))
    finalList = list(reader)[0]
    parseIllust = {}
    parseIllust['illustID'] = finalList[0]
    parseIllust['userID'] = finalList[1]
    parseIllust['illustExt'] = finalList[2]
    parseIllust['title'] = finalList[3]
    parseIllust['imageServer'] = finalList[4]
    parseIllust['userName'] = finalList[5]
    parseIllust['illust128'] = finalList[6]
    parseIllust['illust480'] = finalList[9]
    parseIllust['time'] = finalList[12]
    parseIllust['tags'] = finalList[13]
    parseIllust['software'] = finalList[14]
    parseIllust['vote'] = finalList[15]
    parseIllust['point'] = finalList[16]
    parseIllust['viewCount'] = finalList[17]
    parseIllust['description'] = finalList[18][1:]
    parseIllust['pages'] = finalList[19]
    parseIllust['bookmarks'] = finalList[22]
    parseIllust['userLoginID'] = finalList[24]
    parseIllust['userProfileImageUrl'] = finalList[29]
    return parseIllust


def login():
    urlOpener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0')]
    urllib.request.install_opener(urlOpener)

    print("输入登录信息：")
    PixivID = input("ID:")
    password = input("Password:")
    post_data = {
        'mode': 'login',
        'skip': '1'
    }
    post_data["pixiv_id"] = PixivID
    post_data["pass"] = password
    request = urllib.request.Request('http://www.pixiv.net/login.php',
                                     urllib.parse.urlencode(post_data).encode(encoding='utf_8'))
    urlOpener.open(request)
    cookiejar.save("cookie.txt")


def main():
    info = " Pixiv Downloader  Ver 1.2.1 by:KK "
    print(info.center(80, '#'))
    if os.path.exists(r"cookie.txt"):
        cookiejar.load("cookie.txt")
    else:
        login()

    global PHPSESSID
    for i in cookiejar:
        if i.name == "PHPSESSID":
            PHPSESSID = i.value

    #IDNumber = 141132
    IDNumber = input("输入作者Pixiv ID(以空格间隔):")
    for i in IDNumber.split():
        getAllIllustID(i)
        downloadAll()


if __name__ == '__main__':
    cookiejar = http.cookiejar.LWPCookieJar()
    urlOpener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar), urllib.request.HTTPHandler())
    main()
