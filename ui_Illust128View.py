# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Illust128View.ui'
#
# Created: Mon Jul 15 18:39:11 2013
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Widget(object):
    def setupUi(self, Widget):
        Widget.setObjectName(_fromUtf8("Widget"))
        Widget.resize(132, 151)
        Widget.setMinimumSize(QtCore.QSize(128, 151))
        self.toolButton = QtGui.QToolButton(Widget)
        self.toolButton.setGeometry(QtCore.QRect(0, 0, 128, 150))
        self.toolButton.setMinimumSize(QtCore.QSize(128, 145))
        self.toolButton.setStyleSheet(_fromUtf8("QToolButton{\n"
"border:None;\n"
"border-radius:7px;\n"
"}\n"
"\n"
"QToolButton:checked,QToolButton:pressed{\n"
"border:3px solid rgb(0,170,248);\n"
"}\n"
"\n"
"QToolButton:hover{\n"
"border:3px solid rgb(95,205,255)\n"
"}\n"
"\n"
"QToolButton:checked:hover{\n"
"border:3px solid rgb(0,170,248);\n"
"}"))
        self.toolButton.setText(_fromUtf8(""))
        self.toolButton.setIconSize(QtCore.QSize(128, 128))
        self.toolButton.setCheckable(True)
        self.toolButton.setPopupMode(QtGui.QToolButton.DelayedPopup)
        self.toolButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.toolButton.setObjectName(_fromUtf8("toolButton"))

        self.retranslateUi(Widget)
        QtCore.QMetaObject.connectSlotsByName(Widget)

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(_translate("Widget", "Form", None))

