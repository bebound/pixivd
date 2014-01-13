import urllib
import urllib.request
import http.cookiejar
import re
import os
import math
import queue
import sys
import threading
from PyQt4 import QtGui
from PyQt4 import QtCore
import html.parser
import time
from bs4 import BeautifulSoup
import csv
import io
import ui_Pixiv
import ui_PixivMainWindow
import ui_Illust128View


__appname__ = 'Pixiv Download (beta)'

cookiejar = http.cookiejar.LWPCookieJar()
urlOpener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar), urllib.request.HTTPHandler())
urlOpener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0')]
urlOpener.addheaders = [('Referer', r'http://www.pixiv.net/')]
urllib.request.install_opener(urlOpener)

fetch_timeout = 15     #urllib超时时间
curSearchAllIllustID = []     #根据搜索条件获取到的IllustID
parsedIllust=[]         #parse过的illust
curNeedStopThreads=[]    #可停止进程
curViewIllust=[]         #当前viewWidget的128们
curCheckedIllustID=[]    #当前选择的128们
curDownloadingIllustID=[]  #正在下载的illust
curManageIllust=[]       #manageWidget的row
maxDownloadThread=5
startDownload=0
downloadQuene=queue.Queue()
parseLock = threading.BoundedSemaphore(20)

basePath=os.path.split(os.path.realpath(sys.argv[0]))[0]


class Illust128View(QtGui.QWidget,ui_Illust128View.Ui_Widget):
    sigClicked=QtCore.pyqtSignal(str)

    def __init__(self,illustID=None,illust128=None,parent=None):
        super(Illust128View, self).__init__(parent)
        self.setupUi(self)
        self.illustID=illustID
        self.toolButton.setText(str(illustID))
        self.toolButton.clicked.connect(self.iconClicked)

    def setPic(self,filePath):
        self.toolButton.setIcon(QtGui.QIcon(filePath))

    def iconClicked(self):
        self.sigClicked.emit(str(self.illustID))

    def check(self):
        if not self.toolButton.isChecked():
            self.toolButton.click()

    def changeCheckStatus(self):
        self.toolButton.click()




class PixivMainWindow(QtGui.QMainWindow, ui_PixivMainWindow.Ui_mainWindow):
    def __init__(self, parent=None):
        super(PixivMainWindow, self).__init__(parent)
        self.setupUi(self)
        self.centralWidget = PixivMainWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.move(QtGui.QApplication.desktop().screen().rect().center() - self.rect().center())
        self.resize(750,530)
        self.setWindowTitle(__appname__)
        self.centralWidget.sigChangeStatus.connect(self.changeStatus)
        self.centralWidget.initWidget()
        self.checkTemp()

    def changeStatus(self, status):
        self.statusbar.showMessage(status)

    def checkTemp(self):
        if not os.path.exists(r"temp"):
            os.mkdir('temp')


class PixivMainWidget(QtGui.QWidget, ui_Pixiv.Ui_mainWidget):
    sigChangeStatus = QtCore.pyqtSignal(str)
    sigAllIllustSearchOver = QtCore.pyqtSignal(list)
    sigWarningMessage = QtCore.pyqtSignal(str, str)
    sigPageIllustSearchOver = QtCore.pyqtSignal(int,list)
    sigParseIllust128Over=QtCore.pyqtSignal(dict)

    viewCurPage=1
    viewMaxPage=-1
    viewCurUserID=0


    def __init__(self, parent=None):
        super(PixivMainWidget, self).__init__(parent)
        self.setupUi(self)
        self.loginButton.clicked.connect(lambda: self.changeIndex(0))
        self.accountButton.clicked.connect(lambda: self.changeIndex(1))
        self.downloadButton.clicked.connect(lambda: self.changeIndex(2))
        self.viewButton.clicked.connect(lambda: self.changeIndex(3))
        self.manageButton.clicked.connect(lambda: self.changeIndex(4))
        self.settingButton.clicked.connect(lambda: self.changeIndex(5))
        self.aboutButton.clicked.connect(lambda: self.changeIndex(6))

        self.stackLoginButton.clicked.connect(self.loginFunction)
        self.sigWarningMessage.connect(self.showWarningMessage)
        self.stackSearchButton.clicked.connect(self.startSearch)
        self.stackLogoutButton.clicked.connect(self.logoutFunction)
        self.stackUserID.textChanged.connect(self.changeStackSearchButton)
        self.sigAllIllustSearchOver.connect(self.printAllIllust)
        self.sigPageIllustSearchOver.connect(self.updateViewWidget)
        self.prevPage.clicked.connect(lambda: self.gotoPage(self.viewCurPage-1))
        self.nextPage.clicked.connect(lambda: self.gotoPage(self.viewCurPage+1))
        self.downloadChecked.clicked.connect(self.addDownloadingIllustID)
        self.sigParseIllust128Over.connect(self.addPicIllust128)
        self.checkAll.clicked.connect(self.checkAllFunction)
        self.invertCheckAll.clicked.connect(self.invertCheckAllFunction)

        self.manageTableWidget.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.manageTableWidget.setUpdatesEnabled(True)

    def initWidget(self):
        self.viewButton.setEnabled(False)
        self.manageButton.setEnabled(False)
        if self.loadCookie():
            self.changeStateLogin()
            t = threading.Thread(target=self.loadAvatar, args=())
            t.start()
        else:
            self.changeStateLogout()

    def changeStateLogin(self):
        self.accountButton.setVisible(True)
        self.downloadButton.setEnabled(True)
        self.loginButton.setVisible(False)
        self.sigChangeStatus.emit('已登录')
        self.changeIndex(2)

    def changeStateLogout(self):
        self.loginButton.setVisible(True)
        self.accountButton.setVisible(False)
        self.sigChangeStatus.emit('未登录,请先登录')
        self.accountButton.setVisible(False)
        self.downloadButton.setEnabled(False)
        self.changeIndex(0)

    def changeStackSearchButton(self, userID):
        try:
            int(userID.strip())
            if userID.strip() != '':
                self.stackSearchButton.setEnabled(True)
            else:
                self.stackSearchButton.setEnabled(False)
        except:
            self.stackSearchButton.setEnabled(False)

    def loadCookie(self):
        if os.path.exists(r"cookie.txt"):
            cookiejar.load("cookie.txt")
            #验证cookie过期 有更快的方法没？
            if urlOpener.open('http://www.pixiv.net').geturl()=='http://www.pixiv.net/mypage.php':
                return 1
        return 0

    def showWarningMessage(self, type, content):
        QtGui.QMessageBox.warning(self, type, content, buttons=QtGui.QMessageBox.Ok,
                                  defaultButton=QtGui.QMessageBox.NoButton)

    def getAvatar(self):
        html_src = urlOpener.open('http://www.pixiv.net/mypage.php')
        parser = BeautifulSoup(html_src)

        findUrl = re.compile(r'src="(.*)" width=')
        avatarUrl = findUrl.search(str(parser.select('div.user-image-container img'))).group(1).replace('_s', '')
        tempFile = urlOpener.open(avatarUrl).read()
        filePath = 'temp\\' + 'avatar.' + avatarUrl.split('.')[-1]
        with open(filePath, 'wb') as file:
            file.write(tempFile)
        myPixmap = QtGui.QPixmap(filePath)
        myScaledPixmap = myPixmap.scaled(self.stackAvatar.size(), QtCore.Qt.KeepAspectRatio)
        self.stackAvatar.setPixmap(myScaledPixmap)

    def loadAvatar(self):
        if os.path.exists('temp\\avatar.jpg'):
            myPixmap = QtGui.QPixmap('temp\\avatar.jpg')
            myScaledPixmap = myPixmap.scaled(self.stackAvatar.size(), QtCore.Qt.KeepAspectRatio)
            self.stackAvatar.setPixmap(myScaledPixmap)
        elif os.path.exists('temp\\avatar.png'):
            myPixmap = QtGui.QPixmap('temp\\avatar.png')
            myScaledPixmap = myPixmap.scaled(self.stackAvatar.size(), QtCore.Qt.KeepAspectRatio)
            self.stackAvatar.setPixmap(myScaledPixmap)
        elif os.path.exists('temp\\avatar.gif'):
            myPixmap = QtGui.QPixmap('temp\\avatar.gif')
            myScaledPixmap = myPixmap.scaled(self.stackAvatar.size(), QtCore.Qt.KeepAspectRatio)
            self.stackAvatar.setPixmap(myScaledPixmap)
        else:
            self.getAvatar()

    def startSearch(self):
        global curNeedStopThreads
        for i in curNeedStopThreads:
            i._stop()
        curNeedStopThreads=[]

        self.viewCurPage=1
        self.viewMaxPage=-1
        self.viewCurUserID=self.stackUserID.text().strip()
        self.viewButton.setEnabled(True)
        self.changeIndex(3)


        self.curPage.setText('第1页')
        self.prevPage.setEnabled(False)

        t1=threading.Thread(target=self.downloadPixivUserInfo, args=(self.viewCurUserID,))
        t1.start()
        curNeedStopThreads.append(t1)

        t2=threading.Thread(target=self.gotoPage, args=(1,))
        t2.start()
        curNeedStopThreads.append(t2)

    def downloadPixivUserInfo(self,userID):
        url = "http://www.pixiv.net/member_illust.php?id=" + userID
        htmlSrc = urlOpener.open(url, timeout=fetch_timeout).read().decode('utf-8')
        parser = BeautifulSoup(htmlSrc)
        userLink = parser.select('h1.user')
        findUserName = re.compile(r'"user">(.*)</h1>')
        userName = findUserName.search(str(userLink)).group(1)
        self.pixivUserName.setText(userName)

    def searchALLUserID(self):
        t = threading.Thread(target=self.getAllIllustID, args=(self.stackUserID.text().strip(),))
        t.start()

    def getAllIllustID(self, userID):
        allIllust = []
        page = 1
        pageResult = self.getPageIllustID(userID, page)
        while pageResult:
            allIllust.extend(pageResult)
            page += 1
            pageResult = self.getPageIllustID(userID, page)
        self.sigAllIllustSearchOver.emit(allIllust)

    def getPageIllustID(self, userID, page,returnSig=''):
        url = ''
        if page == 1:
            url = "http://www.pixiv.net/member_illust.php?id=" + str(userID)
        else:
            url = "http://www.pixiv.net/member_illust.php?id=" + str(userID) + '&p=' + str(page)
        htmlSrc = urlOpener.open(url, timeout=fetch_timeout).read().decode('utf-8')
        tempPageIllust = []
        if not '抱歉，未找到任何相关结果。' in htmlSrc:
            parser = BeautifulSoup(htmlSrc)
            illustLink = parser.select('a.work')
            findIllustID = re.compile(r'_id=(.*)"><img')

            for item in illustLink:
                illustID = findIllustID.search(str(item)).group(1)
                tempPageIllust.append(illustID)

            if returnSig!='':
                self.sigPageIllustSearchOver.emit(page,tempPageIllust)
            return tempPageIllust
        else:
            if returnSig!='':
                self.sigPageIllustSearchOver.emit(page,tempPageIllust)
            return False

    def printAllIllust(self, allIllust):
        print(allIllust)

    #初始化widget并开始parse线程
    def updateViewWidget(self,page,illustID):
        global curViewIllust
        if illustID:
            self.downloadChecked.setEnabled(False)
            self.viewCurPage=page
            curPageText='第'+str(page)+'页'
            self.curPage.setText(curPageText)
            if len(illustID)<20:
                self.viewMaxPage=page
            if self.viewCurPage>1:
                self.prevPage.setEnabled(True)
            else:
                self.prevPage.setEnabled(False)
            if self.viewMaxPage!=-1:
                if self.viewCurPage<self.viewMaxPage:
                    self.nextPage.setEnabled(True)
                else:
                    self.nextPage.setEnabled(False)

            tempWidget=QtGui.QWidget()

            grid= QtGui.QGridLayout()
            grid.setSpacing(5)

            curViewIllust=[]
            for i,j in enumerate(illustID):
                k=Illust128View(j)
                k.sigClicked.connect(self.changeCheckedIllustID)
                curViewIllust.append(k)
                grid.addWidget(k,i/5,i%5)

            for i in range(math.ceil(len(illustID)/5)):
                grid.setRowMinimumHeight(i,151)
            for i in range(5):
                grid.setColumnMinimumWidth(i,132)

            tempWidget.setLayout(grid)
            self.viewWidget.setWidget(tempWidget)
            self.viewWidget.setWidgetResizable(True)

            t=threading.Thread(target=self.downloadIllust128, args=(illustID,))
            t.start()
        else:
            self.sigWarningMessage.emit('Error', '已到达最后一页')
            self.viewMaxPage=self.viewCurPage
            self.nextPage.setEnabled(False)

    #开始parse所需的ID线程
    def downloadIllust128(self,illustList):
        for i in illustList:
            t=threading.Thread(target=self.parseIllust, args=(i,'returnSig','lock'))
            t.start()
            curNeedStopThreads.append(t)

    #接收到parse完成的ID后，下载128图片并添加图标
    def addPicIllust128(self,parsedIllust):
        for i in curViewIllust:
            if i.illustID==parsedIllust['illustID']:
                imgLink=parsedIllust['illust128']

                filePath = 'temp\\' + imgLink.split('/')[-1]
                if not os.path.exists(filePath):
                    tempFile = urlOpener.open(imgLink).read()
                    with open(filePath, 'wb') as file:
                        file.write(tempFile)

                i.setPic(filePath)

    def changeCheckedIllustID(self,illustID):

        illustID=int(illustID)
        global curCheckedIllustID
        if illustID in curCheckedIllustID:
            curCheckedIllustID.pop(curCheckedIllustID.index(illustID))
        else:
            curCheckedIllustID.append(illustID)
        if len(curCheckedIllustID)==0:
            self.downloadChecked.setEnabled(False)
        else:
            self.downloadChecked.setEnabled(True)

    def checkAllFunction(self):
        for i in curViewIllust:
            i.check()

    def invertCheckAllFunction(self):
        for i in curViewIllust:
            i.changeCheckStatus()

    #停止不需要的线程 开始获取下一页的
    def gotoPage(self,page):
        for i in curNeedStopThreads:
            i._stop()
        t=threading.Thread(target=self.getPageIllustID, args=(self.viewCurUserID,page,'returnSig'))
        t.start()
        curNeedStopThreads.append(t)

    def loginFunction(self):
        try:
            post_data = {
                'mode': 'login',
                'skip': '1',
            }
            post_data["pixiv_id"] = self.stackPixivIDLineEdit.text()
            post_data["pass"] = self.stackPassWordLineEdit.text()
            request = urllib.request.Request('http://www.pixiv.net/login.php',
                                             urllib.parse.urlencode(post_data).encode(encoding='utf_8'))

            if urlOpener.open(request).geturl() == 'http://www.pixiv.net/login.php':
                self.sigWarningMessage.emit('Error', '用户名或密码错误')

            else:
                cookiejar.save("cookie.txt")
                self.sigChangeStatus.emit('已登录')
                t = threading.Thread(target=self.getAvatar, args=())
                t.start()
                self.changeStateLogin()

        except Exception as ex:
            print(ex)

    def logoutFunction(self):
        urlOpener.open('http://www.pixiv.net/logout.php')
        self.changeStateLogout()
        if os.path.exists('cookie.txt'):
            os.remove('cookie.txt')

    def changeIndex(self, number):
        self.stackedWidget.setCurrentIndex(number)
        if number==0:
            self.loginButton.toggle()
        elif number==1:
            self.accountButton.toggle()
        elif number==2:
            self.downloadButton.toggle()
        elif number==3:
            self.viewButton.toggle()
        elif number==4:
            self.manageButton.toggle()
        elif number==5:
            self.settingButton.toggle()
        else:
            self.aboutButton.toggle()

    def parseIllust(self,illustID,returnSig='',lock=''):
        ok=0
        if lock!='':
            parseLock.acquire()
        for i in parsedIllust:
            if illustID==i['illustID']:
                tempParsedIllust=i
                ok=1
                break

        if ok==0:
            url = "http://spapi.pixiv.net/iphone/illust.php?illust_id=" + str(illustID)
            htmlSrc = urlOpener.open(url).read().decode('utf-8')
            reader = csv.reader(io.StringIO(htmlSrc))
            finalList=list(reader)[0]
            tempParsedIllust = {}
            tempParsedIllust['illustID'] = finalList[0]
            tempParsedIllust['userID'] = finalList[1]
            tempParsedIllust['illustExt'] = finalList[2]
            tempParsedIllust['title'] = finalList[3]
            tempParsedIllust['imageServer'] = finalList[4]
            tempParsedIllust['userName'] = finalList[5]
            tempParsedIllust['illust128'] = finalList[6]
            tempParsedIllust['illust480'] = finalList[9]
            tempParsedIllust['time'] = finalList[12]
            tempParsedIllust['tags'] = finalList[13]
            tempParsedIllust['software'] = finalList[14]
            tempParsedIllust['vote'] = finalList[15]
            tempParsedIllust['point'] = finalList[16]
            tempParsedIllust['views'] = finalList[17]
            tempParsedIllust['description'] = finalList[18][1:]
            tempParsedIllust['pages'] = finalList[19]
            tempParsedIllust['userLonginID'] = finalList[24]
            tempParsedIllust['userProfileImageUrl'] = finalList[29]
            parsedIllust.append(tempParsedIllust)
        if returnSig!='':
            self.sigParseIllust128Over.emit(tempParsedIllust)
        if lock!='':
            parseLock.release()
        return tempParsedIllust

    #将选中Illust加入下载列表 更新ManageWidget
    def addDownloadingIllustID(self):
        addItems=[]
        for i in curCheckedIllustID:
            if i not in curDownloadingIllustID:
                addItems.append(i)
        curDownloadingIllustID.extend(addItems)

        for i in addItems:
            downloadQuene.put(i)

        tempStatus='新添加下载:'+str(addItems)
        self.sigChangeStatus.emit(tempStatus)
        self.manageButton.setEnabled(True)
        self.addManageWidget(addItems)
        global startDownload
        if not startDownload:
            self.startDownload()
            startDownload=1

    def addManageWidget(self,illustID):
        if illustID:
            for i in illustID:
                row=self.manageTableWidget.rowCount()
                self.manageTableWidget.insertRow(row)
                tempItem=QtGui.QTableWidgetItem(str(i))
                self.manageTableWidget.setItem(row,1,tempItem)
                curManageIllust.append(tempItem)

    def startDownload(self):
        for i in range(maxDownloadThread):
            t=threading.Thread(target=self.downloadIllust)
            t.start()



    def downloadIllust(self,):
        while True:
            if not downloadQuene.empty():

                illustID=downloadQuene.get()
                ok=0
                curIllust={}
                for i in range(self.manageTableWidget.rowCount()):
                    if self.manageTableWidget.item(i,1).text()==str(illustID):
                        tempItem=QtGui.QTableWidgetItem('下载中')
                        self.manageTableWidget.setItem(i,0,tempItem)
                        self.manageTableWidget.update()
                        break

                for i in parsedIllust:
                    if i['illustID']==illustID:
                        ok=1
                        curIllust=i
                        break
                if ok==0:
                    curIllust=self.parseIllust(illustID)


                fileDir=basePath +'\\' +curIllust['userID']+' ' +curIllust['userName']
                if not os.path.isdir(fileDir):
                    os.makedirs(fileDir)
                if(curIllust['pages'] == ''):
                    fileName = curIllust['illustID'] + '.' + curIllust['illustExt']
                    filePath = basePath +'\\' +curIllust['userID']+' ' +curIllust['userName']+"\\" + fileName
                    if not os.path.exists(filePath):
                        parseIllustUrl = curIllust['illust128'][:curIllust['illust128'].find(r'mobile/')]+fileName
                        # tempparseIllust = urlOpener.open(parseIllustUrl)
                        # fileSize = tempparseIllust.getheader('Content-Length').strip()
                        # print ("Downloading: %s Bytes: %s" % (fileName, fileSize))
                        tempFile = urlOpener.open(parseIllustUrl).read()
                        with open(filePath, 'wb') as file:
                            file.write(tempFile)

                else:
                    pages = int(curIllust['pages'])
                    for i in range(pages):
                        fileName = curIllust['illustID'] + '_p' + str(i) + '.' + curIllust['illustExt']
                        filePath = basePath +'\\'+curIllust['userID']+' ' +curIllust['userName']+"\\" + fileName
                        if not os.path.exists(filePath):
                            parseIllustUrl = curIllust['illust128'][:curIllust['illust128'].find(r'mobile/')]+fileName
                            # tempparseIllust = urlOpener.open(parseIllustUrl)
                            # fileSize = tempparseIllust.getheader('Content-Length').strip()
                            # print ("Downloading: %s Bytes: %s" % (fileName, fileSize))
                            tempFile = urlOpener.open(parseIllustUrl).read()
                            with open(filePath, 'w+b') as file:
                                file.write(tempFile)

                downloadQuene.task_done()

                for i in range(self.manageTableWidget.rowCount()):
                    if self.manageTableWidget.item(i,1).text()==str(illustID):
                        self.manageTableWidget.item(i,0).setText('')
                        tempItem=QtGui.QTableWidgetItem('已完成')
                        self.manageTableWidget.setItem(i,2,tempItem)
                        self.manageTableWidget.update()
                        break
            else:
                time.sleep(1)



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    form = PixivMainWindow()
    form.show()
    sys.exit(app.exec_())

