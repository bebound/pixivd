import urllib
import http.cookiejar
import re
import os
import html.parser
from bs4 import BeautifulSoup
import threading


allIllustID = []
totalIllust=0
curIllust=1
printLock=threading.Lock()
illustLock=threading.Lock()
maxConnections = 5

def getAllIllustID(userID):
    url = "http://www.pixiv.net/member_illust.php?id=" + str(userID)
    end = 0
    while end != 1:
        nextUrl = getPage(url, userID)
        if not nextUrl:
            end = 1
        else:
            url = nextUrl
    global totalIllust
    totalIllust=len(allIllustID)
    print('total ',totalIllust,':',allIllustID)
    
            
        
def getPage(url, userID):  
    printInfo = "GetPage " + url
    print (printInfo.center(80, '*'))
    htmlSrc = urlOpener.open(url).read().decode('utf-8')
    parser = BeautifulSoup(htmlSrc)
    illustLink = parser.select('a.work')
    userLink = parser.select('h1.user')
    
    findIllustID = re.compile(r'_id=(.*)"><img')
    findUser = re.compile(r'"user">(.*)</h1>')
    
    userName = findUser.search(str(userLink)).group(1)
    
    if not os.path.isdir((str(userID) + ' ' + userName)):
        os.mkdir((str(userID) + ' ' + userName))
    for item in illustLink:
        illustID = findIllustID.search(str(item)).group(1)
        filePath = str(os.path.abspath(str(userID)) + ' ' + userName)
        filePath += "\\" + illustID + ".jpg"
        filePath2 = str(os.path.abspath(str(userID)) + ' ' + userName)
        filePath2 += "\\" + illustID + ".png"
        if os.path.exists(filePath) or os.path.exists(filePath2):
            print (illustID, " Already Saved")
        else:
            #print(illustID, " Added")
            allIllustID.append(illustID)

    if len(parser.select('div.pager-container span.next')[0])!=0:
        nextPage=parser.select('div.pager-container span.next')[0]
        findNextPage = re.compile(r'<a class="_button" href="(.*)" rel="next".*')
        nextPageUrl = 'http://www.pixiv.net/member_illust.php' + html.parser.HTMLParser().unescape(findNextPage.search(str(nextPage)).group(1))
        return nextPageUrl
    else:
        return False
        

def downloadAll():
    urlOpener.addheaders = [('Referer', r'http://www.pixiv.net/')]
    connectionLock = threading.BoundedSemaphore(maxConnections)
    for illustID in allIllustID:
        connectionLock.acquire()
        t=threading.Thread(target=downloadIllust,args=(illustID,connectionLock,printLock,illustLock))
        t.start()

def ownPrint(sentence,printLock):
    printLock.acquire()
    print (sentence)
    printLock.release()

def downloadIllust(illustID,connectionLock,printLock,illustLock):
    global curIllust
    illust = parseIllust(illustID)
    
    try:
        if(illust['pages'] == ''):
            fileName = illust['illustID'] + '.' + illust['illustExt']
            filePath = str(os.path.abspath(illust['userID']) + ' ' + illust['userName'])
            filePath += "\\" + fileName
            parseIllustUrl = illust['illust128'][:illust['illust128'].find(r'mobile/')]
            parseIllustUrl+=fileName

            ownPrint('{0}/{1}:Getting {2}'.format(curIllust,totalIllust,parseIllustUrl),printLock)
            
            #tempparseIllust = urlOpener.open(parseIllustUrl)      
            #fileSize = tempparseIllust.getheader('Content-Length').strip()
            #print ("Downloading: %s Bytes: %s" % (fileName, fileSize))
            tempFile = urlOpener.open(parseIllustUrl).read()
            with open(filePath, 'wb') as file:
                file.write(tempFile)
 
            ownPrint('{0}/{1}:{2} Saved'.format(curIllust,totalIllust,fileName),printLock)

        else:
            pages = int(illust['pages'])
            for i in range(pages):
                fileName = illust['illustID'] + '_p' + str(i) + '.' + illust['illustExt']
                filePath = str(os.path.abspath(illust['userID']) + ' ' + illust['userName'])
                filePath += "\\" + fileName
                if not os.path.exists(filePath):
                    parseIllustUrl = illust['illust128'][:illust['illust128'].find(r'mobile/')]
                    parseIllustUrl+=fileName

                    ownPrint('{0}/{1}:Getting {2}'.format(curIllust,totalIllust,parseIllustUrl),printLock)

                    #tempparseIllust = urlOpener.open(parseIllustUrl)      
                    #fileSize = tempparseIllust.getheader('Content-Length').strip()
                    #print ("Downloading: %s Bytes: %s" % (fileName, fileSize))
                    tempFile = urlOpener.open(parseIllustUrl).read()
                    with open(filePath, 'wb') as file:
                        file.write(tempFile)

                    ownPrint('{0}/{1}:{2} Saved'.format(curIllust,totalIllust,fileName),printLock)

            fileName = illust['illustID'] + '.' + illust['illustExt']
            filePath = str(os.path.abspath(illust['userID']) + ' ' + illust['userName'])
            filePath += "\\" + fileName
            with open(filePath, 'wb') as file:
                pass
                
        
    except  Exception as e:
        ownPrint(e)
    finally:
        if curIllust==totalIllust:
            ownPrint('Finished',printLock)
        illustLock.acquire()
        curIllust+=1
        illustLock.release()
        connectionLock.release()
        
        
def parseIllust(illustID):
    url = "http://spapi.pixiv.net/iphone/illust.php?illust_id=" + illustID
    htmlSrc = urlOpener.open(url).read().decode('utf-8')
    list = htmlSrc.split(',')
    finalList = []
    for i in list:
        finalList.append(i.strip('"'))
    parseIllust = {}
    parseIllust['illustID'] = finalList[0]
    parseIllust['userID'] = finalList[1]
    parseIllust['illustExt'] = finalList[2]
    parseIllust['title'] = finalList[3]
    parseIllust['userName'] = finalList[5]
    parseIllust['illust128'] = finalList[6]
    parseIllust['illust480'] = finalList[9]
    parseIllust['time'] = finalList[12]
    parseIllust['tags'] = finalList[13]
    parseIllust['software'] = finalList[14]
    parseIllust['vote'] = finalList[15]
    parseIllust['point'] = finalList[16]
    parseIllust['views'] = finalList[17]
    parseIllust['description'] = finalList[18]
    parseIllust['pages'] = finalList[19]
    parseIllust['userLonginID'] = finalList[24]
    parseIllust['userProfileImageUrl'] = finalList[29]
    return parseIllust
       
    
def login():
    urlOpener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0')]
    urllib.request.install_opener(urlOpener)
    if not os.path.exists(r"cookie.txt"):
        PixivID = input("ID:")
        password = input("Password:")
        post_data = {
               'mode':'login',
               'skip':'1'
               }
        post_data["pixiv_id"] = PixivID
        post_data["pass"] = password
        request = urllib.request.Request('http://www.pixiv.net/login.php', urllib.parse.urlencode(post_data).encode(encoding='utf_8'))
        urlOpener.open(request)
        cookiejar.save("cookie.txt")
    else:
        cookiejar.load("cookie.txt")


def main():
    info = " Pixiv Downloader  Ver 1.1 by:KK "
    print (info.center(80, '#'))
    login()
    #IDNumber = 141132
    IDNumber = input("输入作者Pixiv ID:")
    getAllIllustID(IDNumber)
    downloadAll()
    

if __name__ == '__main__':
    cookiejar = http.cookiejar.LWPCookieJar()
    urlOpener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar), urllib.request.HTTPHandler())
    main()
