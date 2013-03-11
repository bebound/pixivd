import urllib
import http.cookiejar
import re
import os
import shutil
from bs4 import BeautifulSoup



def HomePage(IDNumber):
    Url = r"http://www.pixiv.net/member_illust.php?id=" + IDNumber
    Page = 1
    
    GetPage(Url, IDNumber, Page)
    Page = Page + 1
    Url2 = Url + "&p=" + str(Page)
    
    while(GetPage(Url2, IDNumber, Page) != 1):
        Page = Page + 1
        Url2 = Url + "&p=" + str(Page)
    PrintInfo = " ID:" + str(IDNumber) + " Over "
    print (PrintInfo.center(60, '*'), "\n")


def GetPage(Url, IDNumber, Page):
    PrintInfo = " ID:" + str(IDNumber) + " Page:" + str(Page) + " "
    print (PrintInfo.center(60, '*'), "\n")
    print ("GetPage", Url, "\n")
    html_src = urlOpener.open(Url).read().decode('utf-8')
    PageOver = "抱歉，未找到任何相关结果"
    if PageOver in str(html_src):
        return 1
    else:
        parser = BeautifulSoup(html_src)
        Picture_Link = parser.select('a.work')
        Pix_Name = parser.select('h1.user')
        FindPixName = re.compile(r'"user">(.*)</h1>')
        FindPicLink = re.compile(r'src="(.*?)(\?.*)*"')
        FindPicNumber = re.compile(r'.*/(.*)/.')
        FindPicName = re.compile(r'.*/(.*)')
        PixName = FindPixName.search(str(Pix_Name)).group(1)
        if not os.path.isdir((str(IDNumber) + ' ' + PixName)):
            os.mkdir((str(IDNumber) + ' ' + PixName))
        for item in Picture_Link:
            OriPicLink = FindPicLink.search(str(item))
            PicUrl = OriPicLink.group(1).replace("_s.", ".")
            RefUrl = "http://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + FindPicNumber.search(PicUrl).group(1)
            FileName = FindPicName.search(PicUrl).group(1)
            FilePath = str(os.path.abspath(str(IDNumber)) + ' ' + PixName)
            FilePath += "\\" + FileName
            if os.path.exists(FilePath):
                print (FileName, " Already Saved")
            else:
                GetPicture(PicUrl, RefUrl, FileName, FilePath, 1, 0, IDNumber)
 
 
def IncPic(PicUrl, RefUrl, FileName, FilePath, IsFirst, kk): 
    kk = kk + 1
    FindNewPicUrl = re.compile(r'(.*)_p.*(\..*)')
    FindNewPath = re.compile(r'(.*\\)')
    FindNewFileName = re.compile(r'.*/(.*)')
    NewPicUrl = FindNewPicUrl.search(PicUrl).group(1) + "_p" + str(kk) + FindNewPicUrl.search(PicUrl).group(2)
    NewFileName = FindNewFileName.search(NewPicUrl).group(1)
    print ("IncPic", NewFileName)
    NewFileName = FindNewFileName.search(NewPicUrl).group(1)
    NewFilePath = FindNewPath.search(FilePath).group(1) + NewFileName
    GetPicture(NewPicUrl, RefUrl, NewFileName, NewFilePath, 0, kk, IDNumber)
# try    
    # if存在 跳过
    # else 下载
    #    if 是递归中 增加图片编号 继续下载
# except
    # if 第一次 增加图片编号
    # else 写入空图片占位 完成该画集下载

def GetPicture(PicUrl, RefUrl, FileName, FilePath, IsFirst, kk, IDNumber):
    print ("\nGetPicture", PicUrl, "\n")
    try:  
        if os.path.exists(FilePath):
            print (FileName, " Already Saved")

        else:
            urlOpener.addheaders = [('Referer', RefUrl)]
            picture = urlOpener.open(PicUrl)      
            file_size = picture.getheader('Content-Length').strip()
            print ("Downloading: %s Bytes: %s" % (FileName, file_size))
            with open(FilePath, 'wb') as file:
                shutil.copyfileobj(picture, file, 1024 * 1024)
# file.open(FilePath, 'wb')
# file.write(picture.read())
            print (FileName, ' Saved')
            if IsFirst != 1:
                IncPic(PicUrl, RefUrl, FileName, FilePath, IsFirst, kk)
            
    except urllib.request.HTTPError:
        print (FileName, "Not Exist")
        if(IsFirst == 1):
            FindNewPicUrl = re.compile(r'(.*/)(.*)(\..*)')
            FindNewFileName = re.compile(r'.*/(.*)')
            FindNewPath = re.compile(r'(.*\\)')
            NewPicUrl = FindNewPicUrl.search(PicUrl).group(1) + FindNewPicUrl.search(PicUrl).group(2) + "_p" + str(kk) + FindNewPicUrl.search(PicUrl).group(3)
            NewRefUrl = RefUrl.replace('medium', 'manga')
            NewFileName = FindNewFileName.search(NewPicUrl).group(1)
            NewFilePath = FindNewPath.search(FilePath).group(1) + NewFileName
            GetPicture(NewPicUrl, NewRefUrl, NewFileName, NewFilePath, 0, kk, IDNumber)
        else:
            FindLastFilePath = re.compile(r'(.*)_p.*(\..*)')
            LastFilePath = FindLastFilePath.search(FilePath).group(1) + FindLastFilePath.search(FilePath).group(2)
            file = open(LastFilePath, "wb")
            file.close()
            
    
    
cookiejar = http.cookiejar.LWPCookieJar()
urlOpener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar), urllib.request.HTTPHandler())
urlOpener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0')]
# proxies = {'http': 'http://proxy.example.com:8080/'}
# opener = urllib.request.FancyURLopener(proxies)
urllib.request.install_opener(urlOpener)
info = " Pixiv Downloader  Ver 1.0 by:KK "
print (info.center(60, '#'))
if not os.path.exists(r"cookie.txt"):
    PixivID = input("ID:")
    password = input("Password:")
    post_data = {
           'mode':'login',
           'skip':'1'
           }
    
    post_data["pixiv_id"] = PixivID
    post_data["pass"] = password
    request = urllib.request.Request('http://www.pixiv.net/login.php',urllib.parse.urlencode(post_data).encode(encoding='utf_8'))
    urlOpener.open(request)
    cookiejar.save("cookie.txt")
else:
    cookiejar.load("cookie.txt")



#AllID = "94883"
AllID = input("输入作者Pixiv ID,以空格间隔：")
AllID = str(AllID).split()

for IDNumber in AllID:
    HomePage(IDNumber)