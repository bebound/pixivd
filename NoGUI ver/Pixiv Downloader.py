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
allIllust = []
illustQuene = queue.Queue()
curIllustNumber = 0
totalIllust = 0
curFilePath = ''
printLock = threading.Lock()
fileLock = threading.Lock()


def getAllIllustID(userID):
    global curFilePath

    if os.path.exists('downloaded.txt'):
        for line in open('downloaded.txt', 'r'):
            downloaded.append(line.strip())
    else:
        with open('downloaded.txt', 'wb'):
            pass

    url = "http://www.pixiv.net/member_illust.php?id=" + str(userID)
    end = 0

    htmlSrc = urlOpener.open(url).read().decode('utf-8')
    parser = BeautifulSoup(htmlSrc)
    userLink = parser.select('h1.user')
    findUserName = re.compile(r'"user">(.*)</h1>')
    curUserName = findUserName.search(str(userLink)).group(1)
    curFilePath = str(os.path.abspath(userID) + ' ' + curUserName)
    if not os.path.isdir(userID + ' ' + curUserName):
        os.mkdir(userID + ' ' + curUserName)

    while end != 1:
        nextUrl = getPage(url, userID)
        if not nextUrl:
            end = 1
        else:
            url = nextUrl

    global totalIllust, curIllustNumber
    curIllustNumber = 1
    totalIllust = len(allIllust)
    print('total', len(allIllust), ':', allIllust)
    for i in allIllust:
        illustQuene.put(i)


def getPage(url, userID):
    printInfo = "GetPage " + url
    print(printInfo.center(80, '*'))
    htmlSrc = urlOpener.open(url, timeout=fetch_timeout).read().decode('utf-8')
    parser = BeautifulSoup(htmlSrc)
    illustLink = parser.select('a.work')
    findIllustID = re.compile(r'_id=(.*)"><img')

    for item in illustLink:
        illustID = findIllustID.search(str(item)).group(1)
        filePath = curFilePath
        filePath += "\\" + illustID + ".jpg"
        filePath2 = curFilePath
        filePath2 += "\\" + illustID + ".png"
        if os.path.exists(filePath) or os.path.exists(filePath2) or str(illustID) in downloaded:
            print(illustID, "Already Saved")
        else:
            print(illustID, "Added")
            allIllust.append(illustID)
    try:
        if len(parser.select('div.pager-container span.next')[0]) != 0:
            nextPage = parser.select('div.pager-container span.next')[0]
            findNextPage = re.compile(r'<a class="_button" href="(.*)" rel="next".*')
            nextPageUrl = 'http://www.pixiv.net/member_illust.php' + html.parser.HTMLParser().unescape(
                findNextPage.search(str(nextPage)).group(1))
            return nextPageUrl
        else:
            return False
    except:
        return False


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
        curIllust = illustQuene.get()
        illust = parseIllust(curIllust)
        try:
            if (illust and illust['pages'] == ''):
                fileName = illust['illustID'] + '.' + illust['illustExt']
                filePath = curFilePath
                filePath += "\\" + fileName
                parseIllustUrl = illust['illust128'][:illust['illust128'].find(r'mobile/')]
                parseIllustUrl += fileName
                print('Getting', parseIllustUrl)

                #tempparseIllust = urlOpener.open(parseIllustUrl)
                #fileSize = tempparseIllust.getheader('Content-Length').strip()
                #print ("Downloading: %s Bytes: %s" % (fileName, fileSize))
                tempFile = urlOpener.open(parseIllustUrl).read()
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
                        parseIllustUrl = illust['illust128'][:illust['illust128'].find(r'mobile/')]
                        parseIllustUrl += fileName

                        print('Getting', parseIllustUrl)

                        #tempparseIllust = urlOpener.open(parseIllustUrl)
                        #fileSize = tempparseIllust.getheader('Content-Length').strip()
                        #print ("Downloading: %s Bytes: %s" % (fileName, fileSize))
                        tempFile = urlOpener.open(parseIllustUrl).read()
                        with open(filePath, 'wb') as file:
                            file.write(tempFile)

                        print(fileName, 'Saved')

                with fileLock:
                    with open("downloaded.txt", "a") as myfile:
                        myfile.write(curIllust + '\n')

            downloadProgress()
            downloaded.append(curIllust)

        except  Exception as e:
            print(e)
            illustQuene.put(curIllust)

        finally:
            illustQuene.task_done()


def downloadProgress():
    global curIllustNumber
    with printLock:
        print('Progress:', curIllustNumber, '/', totalIllust)
        curIllustNumber += 1


def parseIllust(illustID):
    url = "http://spapi.pixiv.net/iphone/illust.php?PHPSESSID=" + PHPSESSID + "&illust_id=" + illustID
    htmlSrc = urlOpener.open(url).read().decode('utf-8')
    if not htmlSrc:
        return False
    reader = csv.reader(io.StringIO(htmlSrc))
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
    if not os.path.exists(r"cookie.txt"):
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
    else:
        cookiejar.load("cookie.txt")


def main():
    info = " Pixiv Downloader  Ver 1.2 by:KK "
    print(info.center(80, '#'))
    login()
    global PHPSESSID
    for i in cookiejar:
        if i.name == "PHPSESSID":
            PHPSESSID = i.value

    #IDNumber = 141132
    IDNumber = input("输入作者Pixiv ID:")
    for i in IDNumber.split():
        getAllIllustID(i)
        downloadAll()


if __name__ == '__main__':
    cookiejar = http.cookiejar.LWPCookieJar()
    urlOpener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar), urllib.request.HTTPHandler())
    main()
