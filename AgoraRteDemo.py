#!python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
from __future__ import annotations
import os
import sys
import time
import math
import json
import types
import ctypes
import random
import datetime
import threading
import traceback
import subprocess
from typing import Any, Callable, Dict, List, Tuple
import util
import agorasdk
import agorasdk as agsdk
if agsdk.ExePath.encode('utf-8') != agsdk.ExePath.encode('ansi'):
    # this error only occurs after compiling to exe by nuitka
    input('程序必须在纯英文路径下运行，不能有中文!\nThe application path must be English characters!\n' * 3)
from transformAppId import transformAppId
from PyQt5.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QColor, QContextMenuEvent, QCursor, QFont, QIcon, QIntValidator, QKeyEvent, QMouseEvent, QPainter, QPixmap, QTextCursor, QTextOption
from PyQt5.QtWidgets import QAction, QApplication, QDesktopWidget, QDialog, QInputDialog, QMainWindow, QMenu, QMessageBox, QWidget, qApp
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QListView, QPushButton, QRadioButton, QSlider, QPlainTextEdit, QTextEdit, QToolTip
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLayout, QSplitter, QVBoxLayout
from QCodeEditor import QCodeEditor
import pyqt5AsyncTask as astask


BUTTON_HEIGHT = 30
DemoTile = 'RteSdkDemo'
IcoPath = os.path.join(agsdk.ExeDir, 'agora-logo.ico')
RtcEngine = None
DevelopDllDir = ''
print = util.printx

#QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
#QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class VideoFrameFile():
    def __init__(self, path: str, videoFormat: agsdk.VideoPixelFormat, width: int, height: int, fps: int = 15):
        self.path = path
        self.videoFormat = videoFormat
        self.width = width
        self.height = height
        self.fps = fps
        self.fileSize = 0
        try:
            self.fobj = open(self.path, 'rb')
            self.fileSize = os.path.getsize(path)
        except Exception as ex:
            self.fobj = None

    def close(self):
        if self.fobj:
            self.fobj.close()
            self.fobj = None
            self.fileSize = 0

    def __del__(self):
        self.close()


class SelectSdkDlg(QDialog):
    def __init__(self, parent: QObject = None, selectCallback: Callable[[str], None] = None):
        super(SelectSdkDlg, self).__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        isX64 = sys.maxsize > 0xFFFFFFFF
        self.setWindowTitle(f'Select SDK Version')
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(300, 200)
        self.selectCallback = selectCallback

        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        tipLabel = QLabel(f'App is {"64" if isX64 else "32"} bit, select a SDK:')
        vLayout.addWidget(tipLabel)
        self.radioButtons = []
        self.sdkDirs = {}
        prefix = f'binx{"64" if isX64 else "86"}_'
        for filePath, isDir, fileName in util.listDir((agsdk.SdkDirFull, True, None)):
            if isDir and fileName.startswith(prefix):
                sdkVersionStr = fileName[len(prefix):]
                self.sdkDirs[sdkVersionStr] = fileName
                radio = QRadioButton(sdkVersionStr)
                radio.setMinimumHeight(BUTTON_HEIGHT)
                vLayout.addWidget(radio)
                self.radioButtons.append(radio)
        if len(self.radioButtons) == 1:
            self.radioButtons[0].setChecked(True)

        useButton = QPushButton('Use')
        useButton.setMinimumHeight(BUTTON_HEIGHT)
        useButton.clicked.connect(self.onClickUse)
        vLayout.addWidget(useButton)

    def onClickUse(self) -> None:
        for radio in self.radioButtons:
            if radio.isChecked():
                break
        else:
            return
        sdkBinDir = self.sdkDirs[radio.text()]
        self.selectCallback(sdkBinDir)
        sdkBinPath = os.path.join(agsdk.agorasdk.SdkBinDirFull, 'agora_rtc_sdk.dll')
        if not os.path.exists(sdkBinPath):
            print(f'---- {sdkBinPath} does not exist')
            # load dll in develop code path
            binDirs = util.getFileText(os.path.join(agsdk.ExeDir, agsdk.ExeNameNoExt + '.dllpath')).splitlines()
            for binDir in binDirs:
                binPath = os.path.join(binDir, 'agora_rtc_sdk.dll')
                if os.path.exists(binPath):
                    global DevelopDllDir
                    DevelopDllDir = binDir
                    print(f'---- add dll dir: {binDir}')
                    os.environ["PATH"] = binDir + os.pathsep + os.environ["PATH"]
                    if agsdk.isPy38OrHigher():
                        os.add_dll_directory(binDir)
                    break
                else:
                    print(f'---- develop dir: {binDir} does not exist')

    def closeEvent(self, event: QCloseEvent) -> None:
        # print('select dlg QCloseEvent')
        pass


class TipDlg(QDialog):
    def __init__(self, parent: QObject = None, tipTime=6):
        super(TipDlg, self).__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)  # Qt.Tool makes no display on taskbar
        self.resize(200, 100)
        self.setMaximumWidth(1280)
        self.gridLayout = QGridLayout()
        self.setLayout(self.gridLayout)
        self.tipLabel = QLabel('No Error')
        self.tipLabel.setMaximumWidth(1200)
        self.tipLabel.setWordWrap(True)
        self.tipLabel.setAlignment(Qt.AlignTop)
        self.tipLabel.setStyleSheet('QLabel{color:rgb(255,0,0);font-size:20px;font-weight:bold;font-family:Verdana;border: 2px solid #FF0000}')
        self.gridLayout.addWidget(self.tipLabel, 0, 0)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.tipTime = tipTime * 1000

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()

    def showTip(self, msg: str = '') -> None:
        self.timer.stop()
        self.timer.start(self.tipTime)
        if msg:
            self.tipLabel.setText(msg)
        self.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.raise_()
        self.activateWindow()


class CodeDlg(QDialog):
    Signal = pyqtSignal(str)

    def __init__(self, parent: QObject = None):
        super(CodeDlg, self).__init__(parent)
        self.mainWindow = parent
        self.threadId = threading.currentThread().ident
        self.setWindowFlags(Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(f"Python {sys.version.split()[0]} Code Executor ")
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(1400, 700)
        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.apiCombox = QComboBox()
        self.apiCombox.setStyleSheet('QAbstractItemView::item {height: 22px;}')
        self.apiCombox.setView(QListView())
        self.apiCombox.setMinimumHeight(24)
        self.apiCombox.currentIndexChanged.connect(self.onComboxApiSelectionChanged)
        hLayout.addWidget(self.apiCombox)

        button = QPushButton('append')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onClickAppend)
        hLayout.addWidget(button)

        button = QPushButton('replace')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onClickReplace)
        hLayout.addWidget(button)

        button = QPushButton('e&xec')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onClickRun)
        hLayout.addWidget(button)

        button = QPushButton('e&val')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onClickRun)
        hLayout.addWidget(button)

        button = QPushButton('reload')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onClickReload)
        hLayout.addWidget(button)

        self.saveButton = QPushButton('save')
        self.saveButton.setMinimumHeight(BUTTON_HEIGHT)
        self.saveButton.clicked.connect(self.onClickSave)
        hLayout.addWidget(self.saveButton)

        button = QPushButton('clearCode')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onClickClearCode)
        hLayout.addWidget(button)

        button = QPushButton('clearOutput')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onClickClearOutput)
        hLayout.addWidget(button)

        self.checkScrollToEnd = QCheckBox('AutoScrollToEnd')
        self.checkScrollToEnd.setChecked(True)
        hLayout.addWidget(self.checkScrollToEnd)

        self.qsplitter = QSplitter(Qt.Vertical)
        vLayout.addWidget(self.qsplitter)
        self.codeEdit = QCodeEditor()
        self.codeEdit.setStyleSheet('QPlainTextEdit{font-size:16px;font-family:Consolas;background-color:rgb(204,232,207);}')
        # self.codeEdit.setPlainText(codeText)
        self.qsplitter.addWidget(self.codeEdit)
        self.outputEdit = QPlainTextEdit()
        self.outputEdit.setStyleSheet('QPlainTextEdit{font-size:14px;font-family:Consolas;background-color:rgb(204,232,207);}')
        self.qsplitter.addWidget(self.outputEdit)
        self.qsplitter.setSizes([100, 100])
        self.Signal.connect(self.outputEdit.appendPlainText)
        agsdk.agorasdk.GuiStreamObj.setLogHandler(self.logCallbackHandler)

        self.loadApiList()

    def onComboxApiSelectionChanged(self, index: int) -> None:
        self.saveButton.setEnabled(index >= len(self.singleApis))

    def onClickSave(self) -> None:
        code = self.codeEdit.toPlainText().strip()
        if not code:
            return
        self.multiApis[self.apiCombox.currentText()] = code
        self.saveApiList()

    def onClickReload(self) -> None:
        self.loadApiList()

    def onClickAppend(self) -> None:
        index = self.apiCombox.currentIndex()
        if index < len(self.singleApis):
            code = self.singleApis[self.apiCombox.currentText()]
            self.codeEdit.appendPlainText(code)
        else:
            code = self.multiApis[self.apiCombox.currentText()]
            self.codeEdit.setPlainText(code)

    def onClickReplace(self) -> None:
        self.onClickClearCode()
        self.onClickAppend()

    def onClickRun(self) -> None:
        button = self.sender()
        if not (button and isinstance(button, QPushButton)):
            return
        self.scrollToEnd()
        try:
            text = self.codeEdit.toPlainText()
            #print(type(text), text)
            if button.text() == 'e&val':
                ret = self.mainWindow.evalCode(text)
                agsdk.log.info(f'eval(...) = {ret}\n')
            else:  # exec
                self.mainWindow.execCode(text)
                agsdk.log.info(f'exec(...) done\n')
        except Exception as ex:
            self.outputEdit.appendPlainText(f'\n{ex}\n{traceback.format_exc()}\n')
        self.scrollToEnd()

    def onClickClearCode(self) -> None:
        self.codeEdit.clear()

    def onClickClearOutput(self) -> None:
        self.outputEdit.clear()

    def scrollToEnd(self) -> None:
        if self.checkScrollToEnd.isChecked():
            currentCursor = self.outputEdit.textCursor()
            currentCursor.movePosition(QTextCursor.End)
            self.outputEdit.setTextCursor(currentCursor)

    def loadApiList(self) -> None:
        curIndex = self.apiCombox.currentIndex()
        apiPath = os.path.join(agsdk.ExeDir, agsdk.ExeNameNoExt + '.code')
        text = util.getFileText(apiPath)
        self.singleApis = {}
        self.multiApis = {}
        self.boundary = '\n----boundary----\n'
        index = 0
        while True:
            name, found = util.getStrBetween(text, left='name=', right='\n', start=index)
            if found < 0:
                break
            index += len(name) + 1
            editable, found = util.getStrBetween(text, left='editable=', right='\n', start=index)
            if found < 0:
                break
            index += len(editable) + 1
            editable = int(editable)
            code, found = util.getStrBetween(text, left='code=', right=self.boundary, start=index)
            if found < 0:
                break
            index += len(code) + len(self.boundary)
            code = code.strip()
            if editable:
                self.multiApis[name] = code
            else:
                self.singleApis[name] = code
        self.apiCombox.clear()
        names = list(self.singleApis.keys())
        names.sort()
        self.apiCombox.addItems(names)
        self.apiCombox.addItems(self.multiApis.keys())
        if self.apiCombox.count() > curIndex:
            self.apiCombox.setCurrentIndex(curIndex)

    def saveApiList(self) -> None:
        apiPath = os.path.join(agsdk.ExeDir, agsdk.ExeNameNoExt + '.code')
        text = '\n'.join(f'name={name}\neditable=0\ncode=\n{content}\n{self.boundary}\n' for name, content in self.singleApis.items())
        util.writeTextFile(text, apiPath)
        text = '\n'.join(f'name={name}\neditable=1\ncode=\n{content}\n{self.boundary}\n' for name, content in self.multiApis.items())
        util.appendTextFile('\n', apiPath)
        util.appendTextFile(text, apiPath)

    def close(self) -> bool:
        agsdk.agorasdk.GuiStreamObj.setLogHandler(None)
        return super(CodeDlg, self).close()

    def logCallbackHandler(self, output: str) -> None:
        if threading.currentThread().ident == self.threadId:
            self.outputEdit.appendPlainText(output)
        else:
            self.Signal.emit(output)


class BeautyOptionsDlg(QDialog):
    def __init__(self, parent: QObject = None, enabledCallback: Callable[[bool], None] = None):
        super(BeautyOptionsDlg, self).__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowTitle("BeautyOptions")
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(300, 200)
        self.enabledCallback = enabledCallback

        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        lighteningContrastLevelLabel = QLabel('LighteningContrastLevel:')
        hLayout.addWidget(lighteningContrastLevelLabel)
        self.lighteningContrastLevelCombox = QComboBox()
        self.lighteningContrastLevelCombox.addItems(f'{it.name} {it.value}' for it in agsdk.LighteningContrastLevel)
        self.lighteningContrastLevelCombox.setCurrentIndex(1)  # Normal
        hLayout.addWidget(self.lighteningContrastLevelCombox)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        lighteningLevelLabel = QLabel('LighteningLevel:')
        hLayout.addWidget(lighteningLevelLabel)
        self.lighteningLevelSlider = QSlider(Qt.Horizontal)
        self.lighteningLevelSlider.setFocusPolicy(Qt.NoFocus)
        self.lighteningLevelSlider.valueChanged.connect(self.onLighteningLevelChanged)
        hLayout.addWidget(self.lighteningLevelSlider)
        self.lighteningLevelLabel = QLabel('0   ')
        hLayout.addWidget(self.lighteningLevelLabel)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        rednessLevelLabel = QLabel('RednessLevel:   ')
        hLayout.addWidget(rednessLevelLabel)
        self.rednessLevelSlider = QSlider(Qt.Horizontal)
        self.rednessLevelSlider.setFocusPolicy(Qt.NoFocus)
        self.rednessLevelSlider.valueChanged.connect(self.onRednessLevelChanged)
        hLayout.addWidget(self.rednessLevelSlider)
        self.rednessLevelLabel = QLabel('0   ')
        hLayout.addWidget(self.rednessLevelLabel)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        sharpnessLevelLabel = QLabel('SharpnessLevel: ')
        hLayout.addWidget(sharpnessLevelLabel)
        self.sharpnessLevelSlider = QSlider(Qt.Horizontal)
        self.sharpnessLevelSlider.setFocusPolicy(Qt.NoFocus)
        self.sharpnessLevelSlider.valueChanged.connect(self.onSharpnessLevelChanged)
        hLayout.addWidget(self.sharpnessLevelSlider)
        self.sharpnessLevelLabel = QLabel('0   ')
        hLayout.addWidget(self.sharpnessLevelLabel)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        smoothnessLevelLabel = QLabel('SmoothnessLevel:')
        hLayout.addWidget(smoothnessLevelLabel)
        self.smoothnessLevelSlider = QSlider(Qt.Horizontal)
        self.smoothnessLevelSlider.setFocusPolicy(Qt.NoFocus)
        self.smoothnessLevelSlider.valueChanged.connect(self.onSmoothnessLevelChanged)
        hLayout.addWidget(self.smoothnessLevelSlider)
        self.smoothnessLevelLabel = QLabel('0   ')
        hLayout.addWidget(self.smoothnessLevelLabel)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        enableBeautyButton = QPushButton('EnableBeauty')
        enableBeautyButton.setToolTip('IRtcEngine::setBeautyEffectOptions(true, BeautyOptions)')
        enableBeautyButton.clicked.connect(self.onClickEnableBeauty)
        hLayout.addWidget(enableBeautyButton)
        disableBeautyButton = QPushButton('DisableBeauty')
        disableBeautyButton.setToolTip('IRtcEngine::setBeautyEffectOptions(false, BeautyOptions)')
        disableBeautyButton.clicked.connect(self.onClickDisableBeauty)
        hLayout.addWidget(disableBeautyButton)

        self.lighteningLevelSlider.setValue(50)
        self.rednessLevelSlider.setValue(50)
        self.sharpnessLevelSlider.setValue(50)
        self.smoothnessLevelSlider.setValue(50)

    def onLighteningLevelChanged(self, value: int) -> None:
        self.lighteningLevelLabel.setText(f'{value/100:.2f}')

    def onRednessLevelChanged(self, value: int) -> None:
        self.rednessLevelLabel.setText(f'{value/100:.2f}')

    def onSharpnessLevelChanged(self, value: int) -> None:
        self.sharpnessLevelLabel.setText(f'{value/100:.2f}')

    def onSmoothnessLevelChanged(self, value: int) -> None:
        self.smoothnessLevelLabel.setText(f'{value/100:.2f}')

    def getBeautyOptions(self) -> agsdk.BeautyOptions:
        beautyOptions = agsdk.BeautyOptions()
        beautyOptions.lighteningContrastLevel = agsdk.LighteningContrastLevel(int(self.lighteningContrastLevelCombox.currentText()[-1]))
        beautyOptions.lighteningLevel = float(self.lighteningLevelLabel.text())
        beautyOptions.rednessLevel = float(self.rednessLevelLabel.text())
        beautyOptions.sharpnessLevel = float(self.sharpnessLevelLabel.text())
        beautyOptions.smoothnessLevel = float(self.smoothnessLevelLabel.text())
        return beautyOptions

    def setEnabledCallback(self, enabledCallback: Callable[[bool], None]) -> None:
        self.enabledCallback = enabledCallback

    def onClickEnableBeauty(self) -> None:
        self.enabledCallback(True)

    def onClickDisableBeauty(self) -> None:
        self.enabledCallback(False)


class TrapezoidCorrectionDlg(QDialog):
    def __init__(self, parent: MainWindow):
        super(TrapezoidCorrectionDlg, self).__init__(parent)
        self.mainWindow = parent
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowTitle("TrapezoidCorrection")
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(400, 200)

        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        self.enableLocalTrapezoidPrimaryCheckBox = QCheckBox('enableLocalTrapezoidCorrection PrimaryCamera')
        self.enableLocalTrapezoidPrimaryCheckBox.setToolTip('IRtcEngine::enableLocalTrapezoidCorrection(enable, sourceType=CameraPrimary)')
        self.enableLocalTrapezoidPrimaryCheckBox.clicked.connect(self.onClickEnableLocalTrapezoidPrimary)
        vLayout.addWidget(self.enableLocalTrapezoidPrimaryCheckBox)

        self.enableLocalTrapezoidSecondaryCheckBox = QCheckBox('enableLocalTrapezoidCorrection SecondaryCamera')
        self.enableLocalTrapezoidSecondaryCheckBox.setToolTip('IRtcEngine::enableLocalTrapezoidCorrection(enable, sourceType=CameraSecondary)')
        self.enableLocalTrapezoidSecondaryCheckBox.clicked.connect(self.onClickEnableLocalTrapezoidSecondary)
        vLayout.addWidget(self.enableLocalTrapezoidSecondaryCheckBox)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.enableRemoteTrapezoidCheckBox = QCheckBox('enableRemoteTrapezoidCorrection')
        self.enableRemoteTrapezoidCheckBox.setToolTip('IRtcEngine::enableRemoteTrapezoidCorrection')
        self.enableRemoteTrapezoidCheckBox.clicked.connect(self.onClickEnableRemoteTrapezoid)
        hLayout.addWidget(self.enableRemoteTrapezoidCheckBox)
        self.remoteUidCombox = QComboBox()
        # self.remoteUidCombox.setMaximumWidth(80)
        hLayout.addWidget(self.remoteUidCombox, stretch=1)
        self.applyToRemoteButton = QPushButton('applyToRemote')
        self.applyToRemoteButton.clicked.connect(self.onClickApplyToRemote)
        hLayout.addWidget(self.applyToRemoteButton)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.assistLineCheckBox = QCheckBox('assistLine')
        self.assistLineCheckBox.clicked.connect(self.onClickAssistLine)
        hLayout.addWidget(self.assistLineCheckBox)
        self.resetTrapezoidButton = QPushButton('reset')
        self.resetTrapezoidButton.clicked.connect(self.onClickResetTrapezoid)
        hLayout.addWidget(self.resetTrapezoidButton)
        self.autoCorrectButton = QPushButton('autoCorrect')
        self.autoCorrectButton.clicked.connect(self.onClickAutoCorrect)
        hLayout.addWidget(self.autoCorrectButton)

    def onClickEnableLocalTrapezoidPrimary(self) -> None:
        if not self.mainWindow.rtcEngine:
            return
        self.mainWindow.localTrapezoidEnabled[0] = self.enableLocalTrapezoidPrimaryCheckBox.isChecked()
        self.mainWindow.rtcEngine.enableLocalTrapezoidCorrection(self.mainWindow.localTrapezoidEnabled[0], agsdk.VideoSourceType.CameraPrimary)

    def onClickEnableLocalTrapezoidSecondary(self) -> None:
        if not self.mainWindow.rtcEngine:
            return
        self.mainWindow.localTrapezoidEnabled[1] = self.enableLocalTrapezoidSecondaryCheckBox.isChecked()
        self.mainWindow.rtcEngine.enableLocalTrapezoidCorrection(self.mainWindow.localTrapezoidEnabled[1], agsdk.VideoSourceType.CameraSecondary)

    def onClickResetTrapezoid(self) -> None:
        if not self.mainWindow.rtcEngine:
            return
        index = int(self.mainWindow.curVideoSourceType)
        if index not in self.mainWindow.localTrapezoidEnabled:
            return
        if self.mainWindow.localTrapezoidEnabled[index]:
            jsInfo = {
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                "resetDragPoints": 1,
            }
            sourceType = agsdk.VideoSourceType(index)
            self.mainWindow.rtcEngine.setLocalTrapezoidCorrectionOptions(jsInfo, sourceType)
        if self.mainWindow.remoteTrapezoidEnabledUid > 0:
            jsInfo = {
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                "resetDragPoints": 1,
            }
            self.mainWindow.rtcEngine.setRemoteTrapezoidCorrectionOptions(self.mainWindow.remoteTrapezoidEnabledUid, jsInfo)

    def onClickAutoCorrect(self) -> None:
        if not self.mainWindow.rtcEngine:
            return
        index = int(self.mainWindow.curVideoSourceType)
        if index not in self.mainWindow.localTrapezoidEnabled:
            return
        if self.mainWindow.localTrapezoidEnabled[index]:
            jsInfo = {
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                "autoCorrect": 1,
            }
            sourceType = agsdk.VideoSourceType(index)
            self.mainWindow.rtcEngine.setLocalTrapezoidCorrectionOptions(jsInfo, sourceType)
        if self.mainWindow.remoteTrapezoidEnabledUid > 0:
            jsInfo = {
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                "autoCorrect": 1,
            }
            self.mainWindow.rtcEngine.setRemoteTrapezoidCorrectionOptions(self.mainWindow.remoteTrapezoidEnabledUid, jsInfo)

    def onClickAssistLine(self) -> None:
        if not self.mainWindow.rtcEngine:
            return
        index = int(self.mainWindow.curVideoSourceType)
        if index not in self.mainWindow.localTrapezoidEnabled:
            return
        if self.mainWindow.localTrapezoidEnabled[index]:
            jsInfo = {
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                # "resetDragPoints": 0,
            }
            sourceType = agsdk.VideoSourceType(index)
            self.mainWindow.rtcEngine.setLocalTrapezoidCorrectionOptions(jsInfo, sourceType)
        if self.mainWindow.remoteTrapezoidEnabledUid > 0:
            jsInfo = {
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                # "resetDragPoints": 0,
            }
            self.mainWindow.rtcEngine.setRemoteTrapezoidCorrectionOptions(self.mainWindow.remoteTrapezoidEnabledUid, jsInfo)

    def onClickEnableRemoteTrapezoid(self) -> None:
        if not self.mainWindow.rtcEngine:
            return
        index = self.remoteUidCombox.currentIndex()
        if index < 0:
            return
        uid = int(self.remoteUidCombox.itemText(index))
        if self.enableRemoteTrapezoidCheckBox.isChecked():
            self.mainWindow.remoteTrapezoidEnabledUid = uid
            self.mainWindow.rtcEngine.enableRemoteTrapezoidCorrection(uid, True)
        else:
            self.mainWindow.rtcEngine.enableRemoteTrapezoidCorrection(uid, False)
            self.mainWindow.remoteTrapezoidEnabledUid = 0

    def onClickApplyToRemote(self) -> None:
        if not self.mainWindow.rtcEngine:
            return
        uid = int(self.remoteUidCombox.currentText())
        self.mainWindow.rtcEngine.applyTrapezoidCorrectionToRemote(uid, self.enableRemoteTrapezoidCheckBox.isChecked())
        self.mainWindow.remoteTrapezoidEnabledUid = False
        self.enableRemoteTrapezoidCheckBox.setChecked(False)


class DataStreamDlg(QDialog):
    def __init__(self, parent: MainWindow, sendStreamCallback: Callable[[str], bool] = None):
        super(DataStreamDlg, self).__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowTitle("DataStreamTest")
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.mainWindow = parent
        self.sendStreamCallback = sendStreamCallback
        self.resize(400, 600)
        self.msgSplitter = ' |&| '
        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        nameLabel = QLabel('MyName:')
        hLayout.addWidget(nameLabel)
        self.nameEdit = QLineEdit(self.mainWindow.configJson['myName'])
        hLayout.addWidget(self.nameEdit)

        historyLabel = QLabel('HistoryMessages:')
        vLayout.addWidget(historyLabel)

        self.historyMsgEdit = QTextEdit()
        self.historyMsgEdit.setReadOnly(True)
        vLayout.addWidget(self.historyMsgEdit, stretch=2)
        self.msgEdit = QTextEdit()
        vLayout.addWidget(self.msgEdit, stretch=1)

        button = QPushButton('&Send(Ctrl+Enter)')
        button.setMinimumHeight(BUTTON_HEIGHT)
        button.clicked.connect(self.onBtnClickSend)
        vLayout.addWidget(button)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_Return:
            event.accept()
            self.onBtnClickSend()

    def onBtnClickSend(self) -> None:
        name = self.nameEdit.text().strip()
        if not name:
            QMessageBox.warning(self, 'Tip', 'MyName can not be empty!')
            return
        if self.mainWindow.configJson['myName'] != name:
            self.mainWindow.configJson['myName'] = name
            util.jsonToFile(self.mainWindow.configJson, self.mainWindow.configPath)
        message = self.msgEdit.toPlainText()
        if not message:
            return
        if self.sendStreamCallback(f'{name}{self.msgSplitter}{message}'):
            t = datetime.datetime.now()
            timeStr = f'{t.year}-{t.month:02}-{t.day:02} {t.hour:02}:{t.minute:02}:{t.second:02}'
            self.historyMsgEdit.append(f'<font color=#7C7CFC>{timeStr}    Me({name}):</font><br>{message}<br>')
            self.scrollToEnd()
            self.msgEdit.clear()
            self.msgEdit.setFocus()

    def scrollToEnd(self) -> None:
        currentCursor = self.historyMsgEdit.textCursor()
        currentCursor.movePosition(QTextCursor.End)
        self.historyMsgEdit.setTextCursor(currentCursor)

    def appendMessage(self, uid: int, message: str) -> None:
        index = message.find(self.msgSplitter)
        if index > 0:
            name, message = message[:index], message[index + len(self.msgSplitter):]
        else:
            name = ''
        t = datetime.datetime.now()
        timeStr = f'{t.year}-{t.month:02}-{t.day:02} {t.hour:02}:{t.minute:02}:{t.second:02}'
        self.historyMsgEdit.append(f'<font color=green>{timeStr}    uid {uid} {name}:</font><br>{message}<br>')
        self.scrollToEnd()


class MainWindow(QMainWindow, astask.AsyncTask):
    CallbackSignal = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        agsdk.log.info(f'sys.paltform={sys.platform}, ExePath={agsdk.ExePath}, cwd={os.getcwd()}, uithread={threading.get_ident()}')
        self.configPath = os.path.join(agsdk.ExeDir, agsdk.ExeNameNoExt + '.config')
        self.configJson = util.jsonFromFile(self.configPath)
        self.configJson.setdefault('appNameList', [])
        self.configJson.setdefault('appNameIndex', 0)
        self.dataStreamId = 0
        self.localUids = []
        self.videoLabels = []
        self.viewUsingIndex = set()
        self.viewCount = 0
        self.mousePressVideoLabelIndex = -1
        self.menuShowVideoLableIndex = -1
        self.mousePressPoint = (0, 0)
        self.mousePressTime = 0
        self.onlyShowVideoLabelIndex = -1
        self.clearViewTimer = QTimer()
        self.clearViewTimer.setSingleShot(True)
        self.clearViewTimer.timeout.connect(self.onClearViewTimeout)
        self.clearViewIndexs = []
        self.rtcEngineEventHandler = {}
        self.initializeEventHandlers()
        self.CallbackSignal.connect(self.onRtcEngineCallback)
        self.inited = False
        self.channelName = ''
        self.channelNameEx = ""
        self.joined = False
        self.joinedEx = False
        self.channelOptions = None
        self.channelExOptions = None
        self.previewed = False
        self.localTrapezoidEnabled = {0: False, 1: False}  # 0 primary, 1 secondary
        self.localTrapezoidCalledWhenMove = False
        self.remoteTrapezoidEnabledUid = 0
        self.remoteTrapezoidCalledWhenMove = False
        self.customViewIndex = -1
        self.uid2ViewIndex = {}  # does not have key 0, local uid is the real uid when join successfully
        self.viewIndex2RenderMode = {}  # Hidden, Fit, Adaptive
        self.viewIndex2RenderMirrorMode = {}
        self.viewIndex2EncoderMirrorMode = {}
        self.viewIndex2BrightnessCorrection = {}
        self.curVideoSourceType = agsdk.VideoSourceType.CameraPrimary
        self.curMediaSourceType = agsdk.MediaSourceType.PrimaryCameraSource
        self.uid2MuteAudio = {}  # has key 0, local uid is 0, todo
        self.uid2MuteVideo = {}  # has key 0, local uid is 0, todo
        self.videoConfig = agsdk.VideoEncoderConfiguration()
        self.videoConfigEx = agsdk.VideoEncoderConfiguration()
        self.defaultRenderMode = self.configJson["defaultRenderMode"]
        self.defaultBrightnessCorrectionMode = self.configJson["defaultBrightnessCorrectionMode"]
        self.autoSubscribeAudioEx = 0
        self.autoSubscribeVideoEx = 1
        self.isPushEx = False
        self.loadedExtensions = []
        # agsdk.chooseSdkBinDir('binx86_3.5.209')
        # self.rtcEngine = agsdk.RtcEngine()
        self.rtcEngine = None
        self.rtcConnection = None
        self.pushTimer = QTimer()
        self.pushTimer.timeout.connect(self.onPushVideoFrameTimer)
        self.pushUid = 0
        self.pushText = ''
        self.painter = None
        self.pixmap = None
        self.pushVideoFrameFile = None

        self.createUI()
        self.initUI()
        self.selectSdkDlg = SelectSdkDlg(self, selectCallback=self.onSelectSdkCallback)
        self.tipDlg = TipDlg(None)
        self.codeDlg = CodeDlg(self)
        self.beautyOptionsDlg = BeautyOptionsDlg(self, enabledCallback=self.onBeautyOptionsEnabledOrDisabled)
        self.dataStreamDlg = DataStreamDlg(self, sendStreamCallback=self.onClickSendStreamMessageCallback)
        self.trapezoidCorrectionDlg = TrapezoidCorrectionDlg(self)
        self.enableLocalTrapezoidPrimaryCheckBox = self.trapezoidCorrectionDlg.enableLocalTrapezoidPrimaryCheckBox
        self.enableLocalTrapezoidSecondaryCheckBox = self.trapezoidCorrectionDlg.enableLocalTrapezoidSecondaryCheckBox
        self.enableRemoteTrapezoidCheckBox = self.trapezoidCorrectionDlg.enableRemoteTrapezoidCheckBox
        self.assistLineCheckBox = self.trapezoidCorrectionDlg.assistLineCheckBox
        self.remoteUidCombox = self.trapezoidCorrectionDlg.remoteUidCombox
        self.selectSdkDlg.exec()
        # after exec, console window is active, set MainWindow active in timer
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.activateWindow)
        self.timer.start(100)

    def evalCode(self, code: str) -> Any:
        return eval(code)

    def execCode(self, code: str) -> Any:
        return exec(code)

    def createUI(self) -> None:
        self.setWindowTitle(DemoTile)
        self.setWindowIcon(QIcon(IcoPath))
        self.resize(1280, 600)
        self.intValidator = QIntValidator()

        mainWg = QWidget()
        self.setCentralWidget(mainWg)
        self.mainLayout = QHBoxLayout()
        mainWg.setLayout(self.mainLayout)

        leftWg = QWidget()
        vLayout = QVBoxLayout()
        vLayout.setSpacing(4)
        vLayout.setContentsMargins(0, 0, 0, 0)
        leftWg.setLayout(vLayout)
        self.mainLayout.addWidget(leftWg)

        # --------
        # left panel

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        scenarioLabel = QLabel("Scenario:")
        hLayout.addWidget(scenarioLabel)
        self.customBtnCombox = QComboBox()
        self.customBtnCombox.setStyleSheet('QAbstractItemView::item {height: 22px;}')
        self.customBtnCombox.setView(QListView())
        self.customBtnCombox.currentIndexChanged.connect(self.onComboxCustomButtonSelectionChanged)
        for btnInfo in self.configJson["customButtons"]:
            self.customBtnCombox.addItem(btnInfo["buttonName"])
        hLayout.addWidget(self.customBtnCombox)
        runCustomButton = QPushButton('run')
        runCustomButton.clicked.connect(self.onClickRunCustomButton)
        hLayout.addWidget(runCustomButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        appNameLabel = QLabel('AppName:')
        hLayout.addWidget(appNameLabel)
        self.appNameComBox = QComboBox()
        self.appNameComBox.setStyleSheet('QAbstractItemView::item {height: 22px;}')
        self.appNameComBox.setView(QListView())
        self.appNameComBox.setEditable(True)
        self.appNameComBox.currentIndexChanged.connect(self.onComboxAppNameSelectionChanged)
        hLayout.addWidget(self.appNameComBox, stretch=1)
        initializeButton = QPushButton('initialize')
        initializeButton.setToolTip('IRtcEngine::initialize')
        initializeButton.clicked.connect(self.onClickInitialize)
        hLayout.addWidget(initializeButton)
        releaseButton = QPushButton('release')
        initializeButton.setToolTip('IRtcEngine::release')
        releaseButton.clicked.connect(self.onClickRelease)
        hLayout.addWidget(releaseButton)
        # hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        setChannelProfileButton = QPushButton('setChannelProfile:')
        setChannelProfileButton.setToolTip('IRtcEngine::setChannelProfile')
        setChannelProfileButton.clicked.connect(self.onClickSetChannelProfile)
        hLayout.addWidget(setChannelProfileButton)
        self.channelProfileCombox = QComboBox()
        self.channelProfileCombox.addItems(f'{it.name} {it.value}' for it in agsdk.ChannelProfile)
        self.channelProfileCombox.setCurrentIndex(1)  # Live
        hLayout.addWidget(self.channelProfileCombox)
        hLayout.addStretch(1)
        # self.channelProfileCombox.currentIndexChanged.connect(self.onChannelProfileSelectionChanged)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        setClientRoleButton = QPushButton('setClientRole:')
        setClientRoleButton.setToolTip('IRtcEngine::setClientRole')
        setClientRoleButton.clicked.connect(self.onClickSetClientRole)
        hLayout.addWidget(setClientRoleButton)
        self.clientRoleCombox = QComboBox()
        self.clientRoleCombox.addItems(f'{it.name} {it.value}' for it in agsdk.ClientRole)
        self.clientRoleCombox.setCurrentIndex(0)  # Broadcaster
        hLayout.addWidget(self.clientRoleCombox)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        registerVideoFrameObBtn = QPushButton('registerVideoFrameObserver')
        registerVideoFrameObBtn.setToolTip('IMediaEngine::registerVideoFrameObserver')
        registerVideoFrameObBtn.clicked.connect(self.onClickRegisterVideoFrameObserver)
        hLayout.addWidget(registerVideoFrameObBtn)
        yuvLabel = QLabel('SaveYuv')
        hLayout.addWidget(yuvLabel)
        self.saveCaptureVideoFrameCheckBox = QCheckBox('C')
        self.saveCaptureVideoFrameCheckBox.setToolTip('Capture Yuv')
        self.saveCaptureVideoFrameCheckBox.clicked.connect(self.onClickSaveCaptureVideoFrame)
        hLayout.addWidget(self.saveCaptureVideoFrameCheckBox)
        self.saveRenderVideoFrameCheckBox = QCheckBox('R')
        self.saveRenderVideoFrameCheckBox.setToolTip('Render Yuv')
        self.saveRenderVideoFrameCheckBox.clicked.connect(self.onClickSaveRenderVideoFrame)
        hLayout.addWidget(self.saveRenderVideoFrameCheckBox)
        self.saveCaptureVideoFrameCountEdit = QLineEdit('100')
        self.saveCaptureVideoFrameCountEdit.setToolTip('Yuv Frame Count')
        self.saveCaptureVideoFrameCountEdit.setMaximumWidth(40)
        self.saveCaptureVideoFrameCountEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.saveCaptureVideoFrameCountEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        enableAudioButton = QPushButton('enableAudio')
        enableAudioButton.setToolTip('IRtcEngine::enableAudio')
        enableAudioButton.clicked.connect(self.onClickEnableAudio)
        hLayout.addWidget(enableAudioButton)
        disableAudioButton = QPushButton('disableAudio')
        disableAudioButton.setToolTip('IRtcEngine::disableAudio')
        disableAudioButton.clicked.connect(self.onClickDisableAudio)
        hLayout.addWidget(disableAudioButton)
        enableVideoButton = QPushButton('enableVideo')
        enableVideoButton.setToolTip('IRtcEngine::enableVideo')
        enableVideoButton.clicked.connect(self.onClickEnableVideo)
        hLayout.addWidget(enableVideoButton)
        disableVideoButton = QPushButton('disableVideo')
        disableVideoButton.setToolTip('IRtcEngine::disableVideo')
        disableVideoButton.clicked.connect(self.onClickDisableVideo)
        hLayout.addWidget(disableVideoButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        enableLocalAudioButton = QCheckBox('enableLocalAudio')
        enableLocalAudioButton.setToolTip('IRtcEngine::enableLocalAudio')
        enableLocalAudioButton.setChecked(True)
        enableLocalAudioButton.clicked.connect(self.onClickEnableLocalAudio)
        hLayout.addWidget(enableLocalAudioButton)
        enableLocalVideoButton = QCheckBox('enableLocalVideo')
        enableLocalVideoButton.setToolTip('IRtcEngine::enableLocalVideo')
        enableLocalVideoButton.setChecked(True)
        enableLocalVideoButton.clicked.connect(self.onClickEnableLocalVideo)
        hLayout.addWidget(enableLocalVideoButton)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        self.videoDevices = []

        videoDevicesLabel = QLabel('VideoDevices:')
        hLayout.addWidget(videoDevicesLabel)
        self.videoDevicesCombox = QComboBox()
        hLayout.addWidget(self.videoDevicesCombox, stretch=1)
        # hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        getVideoDevicesButton = QPushButton('getVideoDevices')
        getVideoDevicesButton.setToolTip('IVideoDeviceManager::enumerateVideoDevices')
        getVideoDevicesButton.clicked.connect(self.onClickGetVideoDevices)
        hLayout.addWidget(getVideoDevicesButton)
        setVideoDeviceIdButton = QPushButton('setVideoDevice')
        setVideoDeviceIdButton.setToolTip('IVideoDeviceManager::setDevice')
        setVideoDeviceIdButton.clicked.connect(self.onClickSetVideoDevice)
        hLayout.addWidget(setVideoDeviceIdButton)
        getVideoDeviceIdButton = QPushButton('getVideoDevice')
        getVideoDeviceIdButton.setToolTip('IVideoDeviceManager::getDevice')
        getVideoDeviceIdButton.clicked.connect(self.onClickGetVideoDevice)
        hLayout.addWidget(getVideoDeviceIdButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        self.loadExtensionProviderButton = QPushButton('loadExtensionProvider')
        self.loadExtensionProviderButton.setToolTip('IRtcEngine::loadExtensionProvider(...), SDK Version must >= 3.6.200')
        self.loadExtensionProviderButton.clicked.connect(self.onClickLoadExtensionProvider)
        hLayout.addWidget(self.loadExtensionProviderButton)

        self.enableExtensionButton = QPushButton('enableExtension')
        self.enableExtensionButton.setToolTip('IRtcEngine::enableExtension(...), SDK Version must >= 3.6.200')
        self.enableExtensionButton.clicked.connect(self.onClickEnableExtension)
        hLayout.addWidget(self.enableExtensionButton)

        self.beautyOptionsButton = QPushButton('BeautyOptions')
        self.beautyOptionsButton.setToolTip('IRtcEngine::setBeautyEffectOptions, SDK Version must >= 3.6.200')
        self.beautyOptionsButton.clicked.connect(self.onClickBeautyOptions)
        hLayout.addWidget(self.beautyOptionsButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        captureWidthLabel = QLabel('CaptureWidth:')
        hLayout.addWidget(captureWidthLabel)
        self.captureWidthEdit = QLineEdit()
        self.captureWidthEdit.setMaximumWidth(50)
        self.captureWidthEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.captureWidthEdit)
        captureHeightLabel = QLabel('Height:')
        hLayout.addWidget(captureHeightLabel)
        self.captureHeightEdit = QLineEdit()
        self.captureHeightEdit.setMaximumWidth(50)
        self.captureHeightEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.captureHeightEdit)
        captureFpsLabel = QLabel('FPS:')
        hLayout.addWidget(captureFpsLabel)
        self.captureFpsCombox = QComboBox()
        self.captureFpsCombox.addItems(['1', '7', '10', '15', '24', '30', '60'])
        self.captureFpsCombox.setEditable(True)
        self.captureFpsCombox.setValidator(self.intValidator)
        self.captureFpsCombox.setCurrentText('15')
        hLayout.addWidget(self.captureFpsCombox)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.setCameraConfigButton = QPushButton('setCameraCapturerConfiguration')
        self.setCameraConfigButton.setToolTip('IRtcEngine::setCameraCapturerConfiguration, SDK Version must >= 3.6.200')
        self.setCameraConfigButton.clicked.connect(self.onClickSetCameraCapturerConfiguration)
        hLayout.addWidget(self.setCameraConfigButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        start1stBtn = QPushButton('start1st')
        start1stBtn.setToolTip('IRtcEngine::startPrimaryCameraCapture')
        start1stBtn.clicked.connect(self.onClickStartPrimaryCameraCapture)
        hLayout.addWidget(start1stBtn)
        stop1stBtn = QPushButton('stop1st')
        stop1stBtn.setToolTip('IRtcEngine::stopPrimaryCameraCapture')
        stop1stBtn.clicked.connect(self.onClickStopPrimaryCameraCapture)
        hLayout.addWidget(stop1stBtn)
        start2ndBtn = QPushButton('start2nd')
        start2ndBtn.setToolTip('IRtcEngine::startSecondaryCameraCapture')
        start2ndBtn.clicked.connect(self.onClickStartSecondaryCameraCapture)
        hLayout.addWidget(start2ndBtn)
        stop2ndBtn = QPushButton('stop2nd')
        stop2ndBtn.setToolTip('IRtcEngine::stopSecondaryCameraCapture')
        stop2ndBtn.clicked.connect(self.onClickStopSecondaryCameraCapture)
        hLayout.addWidget(stop2ndBtn)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        presetLabel = QLabel('Preset:')
        hLayout.addWidget(presetLabel)
        self.presetCombox = QComboBox()
        self.presetCombox.addItems(['320*180', '320*240', '640*360', '640*480', '960*540', '1280*720', '1920*1080'])
        defaultIndex = 2    # 360p
        if self.configJson['defaultResolution'] < self.presetCombox.count():
            defaultIndex = self.configJson['defaultResolution']
        self.presetCombox.setCurrentIndex(defaultIndex)
        self.presetCombox.currentIndexChanged.connect(self.onComboxPresetSelectionChanged)
        hLayout.addWidget(self.presetCombox)
        sourceTypeLabel = QLabel('SourceType:')
        hLayout.addWidget(sourceTypeLabel)
        self.sourceTypeCombox = QComboBox()
        self.sourceTypeCombox.addItems(['Primary', 'Secondary', 'Screen', 'ScreenSecondary', 'Custom'])
        self.sourceTypeCombox.currentIndexChanged.connect(self.onSourceTypeIndexChanged)
        hLayout.addWidget(self.sourceTypeCombox)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        codecLabel = QLabel('Codec:')
        hLayout.addWidget(codecLabel)
        self.codecCombox = QComboBox()
        self.codecCombox.addItems(f'{it.name} {it.value}' for it in agsdk.VideoCodec)
        self.codecCombox.setCurrentIndex(1)  # H264
        # self.codecCombox.currentIndexChanged.connect(self.onCodecSelectionChanged)
        hLayout.addWidget(self.codecCombox)

        mirrorLabel = QLabel('Mirror:')
        hLayout.addWidget(mirrorLabel)
        self.mirrorCombox = QComboBox()
        self.mirrorCombox.addItems(f'{it.name} {it.value}' for it in agsdk.VideoMirrorMode)
        self.mirrorCombox.setCurrentIndex(2)  # Disabled
        hLayout.addWidget(self.mirrorCombox)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        encodeWidthLabel = QLabel('EncodeWidth:')
        hLayout.addWidget(encodeWidthLabel)
        self.encodeWidthEdit = QLineEdit()
        self.encodeWidthEdit.setMaximumWidth(30)
        self.encodeWidthEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.encodeWidthEdit)
        encodeHeightLabel = QLabel('Height:')
        hLayout.addWidget(encodeHeightLabel)
        self.encodeHeightEdit = QLineEdit()
        self.encodeHeightEdit.setMaximumWidth(30)
        self.encodeHeightEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.encodeHeightEdit)
        encodeFpsLabel = QLabel('FPS:')
        hLayout.addWidget(encodeFpsLabel)
        self.encodeFpsCombox = QComboBox()
        self.encodeFpsCombox.addItems(['1', '7', '10', '15', '24', '30', '60'])
        self.encodeFpsCombox.setEditable(True)
        self.encodeFpsCombox.setValidator(self.intValidator)
        self.encodeFpsCombox.setCurrentText('15')
        hLayout.addWidget(self.encodeFpsCombox)
        bitrateLabel = QLabel('Bitrate:')
        hLayout.addWidget(bitrateLabel)
        self.bitrateEdit = QLineEdit('0')
        self.bitrateEdit.setMaximumWidth(30)
        self.bitrateEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.bitrateEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        minBitrateLabel = QLabel('MinBitrate:')
        hLayout.addWidget(minBitrateLabel)
        self.minBitrateEdit = QLineEdit('-1')
        self.minBitrateEdit.setMaximumWidth(30)
        self.minBitrateEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.minBitrateEdit)
        orientionLabel = QLabel('Oriention:')
        hLayout.addWidget(orientionLabel)
        self.orientionCombox = QComboBox()
        self.orientionCombox.addItems(f'{it.name} {it.value}' for it in agsdk.OrientationMode)
        self.orientionCombox.setCurrentIndex(0)
        hLayout.addWidget(self.orientionCombox)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        degradationPreferenceLabel = QLabel('DegradationPreference:')
        hLayout.addWidget(degradationPreferenceLabel)
        self.degradationPreferenceCombox = QComboBox()
        self.degradationPreferenceCombox.addItems(f'{it.name} {it.value}' for it in agsdk.DegradationPreference)
        self.degradationPreferenceCombox.setCurrentIndex(0)
        hLayout.addWidget(self.degradationPreferenceCombox)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        setVideoConfigButton = QPushButton('setVideoEncoderConfiguration')
        setVideoConfigButton.setToolTip('IRtcEngine::setVideoEncoderConfiguration')
        setVideoConfigButton.clicked.connect(self.onClickSetVideoEncoderConfiguration)
        hLayout.addWidget(setVideoConfigButton)
        self.exConfigCheck = QCheckBox('Ex')
        self.exConfigCheck.setToolTip('setVideoEncoderConfigurationEx')
        hLayout.addWidget(self.exConfigCheck)
        setupLocalButton = QPushButton('setupLocalVideo')
        setupLocalButton.setToolTip('IRtcEngine::setupLocalVideo')
        setupLocalButton.clicked.connect(self.onClickSetupLocalVideo)
        hLayout.addWidget(setupLocalButton)
        self.localViewIndexCombox = QComboBox()
        self.localViewIndexCombox.addItems(['0', '1'])
        self.localViewIndexCombox.setCurrentIndex(0)
        self.localViewIndexCombox.hide()
        hLayout.addWidget(self.localViewIndexCombox)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        startPreviewButton = QPushButton('startPreview')
        startPreviewButton.setToolTip('IRtcEngine::startPreview')
        startPreviewButton.clicked.connect(self.onClickStartPreview)
        hLayout.addWidget(startPreviewButton)
        stopPreviewButton = QPushButton('stopPreview')
        stopPreviewButton.setToolTip('IRtcEngine::stopPreview')
        stopPreviewButton.clicked.connect(self.onClickStopPreview)
        hLayout.addWidget(stopPreviewButton)
        self.trapezoidCorrectionButton = QPushButton('TrapezoidCorrection')
        self.trapezoidCorrectionButton.setToolTip('SDK Version must be 3.6.200.10[012]')
        self.trapezoidCorrectionButton.clicked.connect(self.onClickTrapezoidCorrection)
        hLayout.addWidget(self.trapezoidCorrectionButton)
        hLayout.addStretch(1)

        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        channelNameLabel = QLabel('ChannelName:')
        hLayout.addWidget(channelNameLabel)
        self.channelNameEdit = QLineEdit('sdktest')
        self.channelNameEdit.setMaximumWidth(100)
        hLayout.addWidget(self.channelNameEdit)
        uidLabel = QLabel('uid:')
        hLayout.addWidget(uidLabel)
        self.uidEdit = QLineEdit('0')
        self.uidEdit.setMaximumWidth(100)
        self.uidEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.uidEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        tokenLabel = QLabel('token:')
        hLayout.addWidget(tokenLabel)
        self.tokenEdit = QLineEdit()
        self.tokenEdit.setMaximumWidth(120)
        hLayout.addWidget(self.tokenEdit)
        infoLabel = QLabel('info:')
        hLayout.addWidget(infoLabel)
        self.infoEdit = QLineEdit()
        self.infoEdit.setMaximumWidth(120)
        hLayout.addWidget(self.infoEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        joinChannelButton = QPushButton('joinChannel')
        joinChannelButton.setToolTip('IRtcEngine::joinChannel')
        joinChannelButton.clicked.connect(self.onClickJoinChannel)
        hLayout.addWidget(joinChannelButton)
        leaveChannelButton = QPushButton('leaveChannel')
        leaveChannelButton.setToolTip('IRtcEngine::leaveChannel')
        leaveChannelButton.clicked.connect(self.onClickLeaveChannel)
        hLayout.addWidget(leaveChannelButton)
        dataStreamButton = QPushButton('DataStreamTest')
        dataStreamButton.setToolTip('Send/Receive DataStream')
        dataStreamButton.clicked.connect(self.onClickDataStreamTest)
        hLayout.addWidget(dataStreamButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        joinChannelExButton = QPushButton('joinChannelEx')
        joinChannelExButton.setToolTip('IRtcEngineEx::joinChannelEx')
        joinChannelExButton.clicked.connect(self.onClickJoinChannelEx)
        hLayout.addWidget(joinChannelExButton)
        leaveChannelExButton = QPushButton('leaveChannelEx')
        leaveChannelExButton.setToolTip('IRtcEngineEx::leaveChannelEx')
        leaveChannelExButton.clicked.connect(self.onClickLeaveChannelEx)
        hLayout.addWidget(leaveChannelExButton)
        uidLabel = QLabel('uid:')
        hLayout.addWidget(uidLabel)
        self.uidExEdit = QLineEdit('0')
        self.uidExEdit.setMaximumWidth(100)
        self.uidExEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.uidExEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.startScreenCaptureButton = QPushButton('startScreenCaptureByScreenRect')
        self.startScreenCaptureButton.setToolTip('IRtcEngine::startScreenCaptureByScreenRect')
        self.startScreenCaptureButton.clicked.connect(self.onClickStartScreenCaptureByScreenRect)
        hLayout.addWidget(self.startScreenCaptureButton)

        self.stopScreenCaptureButton = QPushButton('stopScreenCapture')
        self.stopScreenCaptureButton.setToolTip('IRtcEngine::stopScreenCapture')
        self.stopScreenCaptureButton.clicked.connect(self.onClickStopScreenCapture)
        hLayout.addWidget(self.stopScreenCaptureButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        self.screenRectEdit = QLineEdit('0,0,1920,1080')
        self.screenRectEdit.setMaximumWidth(82)
        self.screenRectEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.screenRectEdit)
        fpsLabel = QLabel('fps:')
        hLayout.addWidget(fpsLabel)
        self.screenFpsEdit = QLineEdit('15')
        self.screenFpsEdit.setMaximumWidth(20)
        self.screenFpsEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.screenFpsEdit)
        excludeWindowLabel = QLabel('excludeWindows:')
        hLayout.addWidget(excludeWindowLabel)
        self.excludeWindowEdit = QLineEdit(f'0, {int(self.winId())}')
        self.excludeWindowEdit.setMaximumWidth(100)
        hLayout.addWidget(self.excludeWindowEdit)
        hLayout.addStretch(1)

        # ----
        vLayout.addStretch(1)

        # --------
        # right layout
        vLayout = QVBoxLayout()
        self.mainLayout.addLayout(vLayout, stretch=1)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        layoutLabel = QLabel('Layout:')
        hLayout.addWidget(layoutLabel, stretch=0)
        self.layoutCombox = QComboBox()
        self.layoutCombox.addItems(['4', '9', '16', '25', '36', '49'])
        self.layoutCombox.setCurrentIndex(0)
        self.layoutCombox.currentIndexChanged.connect(self.onComboxLayoutSelectionChanged)
        hLayout.addWidget(self.layoutCombox, stretch=0)
        tipBtn = QPushButton('LastError')
        tipBtn.setToolTip('show last error')
        tipBtn.clicked.connect(self.onClickLastError)
        hLayout.addWidget(tipBtn)
        codeBtn = QPushButton('RunCode')
        codeBtn.setToolTip('run python code')
        codeBtn.clicked.connect(self.onClickRunCode)
        hLayout.addWidget(codeBtn)
        self.checkAutoSetupRemoteVideo = QCheckBox('AutoSetupRemoteVideo')
        self.checkAutoSetupRemoteVideo.setToolTip('Auto call setupRemoteVideo when a user joins')
        self.checkAutoSetupRemoteVideo.setChecked(True)
        hLayout.addWidget(self.checkAutoSetupRemoteVideo)
        self.checkAutoSetupRemoteVideoNullView = QCheckBox('AutoResetRemoteVideo')
        self.checkAutoSetupRemoteVideoNullView.setToolTip('Auto call setupRemoteVideo with null view when a user leaves')
        self.checkAutoSetupRemoteVideoNullView.setChecked(True)
        hLayout.addWidget(self.checkAutoSetupRemoteVideoNullView)
        self.checkAutoRepaintVideoBackground = QCheckBox('AutoClearBackground')
        self.checkAutoRepaintVideoBackground.setToolTip('Auto set view to default background color when local video or remote video stops')
        self.checkAutoRepaintVideoBackground.setChecked(True)
        hLayout.addWidget(self.checkAutoRepaintVideoBackground)
        self.checkMuteSecondaryCamera = QCheckBox('MuteSecondaryCamera')
        self.checkMuteSecondaryCamera.setToolTip('mute secondary camera stream')
        self.checkMuteSecondaryCamera.setChecked(True)
        hLayout.addWidget(self.checkMuteSecondaryCamera)
        hLayout.addStretch(1)

        self.gridWidget = QWidget()
        vLayout.addWidget(self.gridWidget, stretch=1)
        self.videoGridLayout = None
        self.onComboxLayoutSelectionChanged(self.layoutCombox.currentIndex())

        self.copyUidAction = QAction('Copy uid', self)
        self.copyUidAction.triggered.connect(self.onActionCopyUid)
        self.copyViewAction = QAction('Copy view', self)
        self.copyViewAction.triggered.connect(self.onActionCopyViewHandle)
        self.renderModeHiddenAction = QAction('Hidden', self, checkable=True)
        self.renderModeHiddenAction.triggered.connect(self.onActionRenderMode)
        self.renderModeFitAction = QAction('Fit', self, checkable=True)
        self.renderModeFitAction.triggered.connect(self.onActionRenderMode)
        self.renderModeAdaptiveAction = QAction('Adaptive', self, checkable=True)
        self.renderModeAdaptiveAction.triggered.connect(self.onActionRenderMode)

        self.renderMirrorAction = QAction('RenderMirror', self, checkable=True)
        self.renderMirrorAction.triggered.connect(self.onActionRenderMirror)
        self.encoderMirrorAction = QAction('EncoderMirror', self, checkable=True)
        self.encoderMirrorAction.triggered.connect(self.onActionEncoderMirror)
        self.brightnessCorrectionAction = QAction('BrightnessCorrection', self, checkable=True)
        self.brightnessCorrectionAction.triggered.connect(self.onActionBrightnessCorrection)
        self.muteAudioAction = QAction('MuteAudio', self, checkable=True)
        self.muteAudioAction.triggered.connect(self.onActionMuteAudio)
        self.muteVideoAction = QAction('MuteVideo', self, checkable=True)
        self.muteVideoAction.triggered.connect(self.onActionMuteVideo)

    def initUI(self) -> None:
        for app in self.configJson['appNameList']:
            self.appNameComBox.addItem(app['appName'])
        if self.configJson['appNameIndex'] >= 0 and self.configJson['appNameIndex'] < len(self.configJson['appNameList']):
            self.appNameComBox.setCurrentIndex(self.configJson['appNameIndex'])
        self.onComboxPresetSelectionChanged(0)
        self.channelNameEdit.setText(self.configJson['channelName'])
        self.uidEdit.setText(self.configJson['uid'])
        self.tokenEdit.setText(self.configJson['tokenChannel'])
        uidEx = random.randint(1000, 10000)
        self.uidExEdit.setText(f'{uidEx}')
        self.checkMuteSecondaryCamera.setChecked(self.configJson['muteSecondaryCamera'])
        self.rtcConnection = agsdk.RtcConnection(self.channelNameEdit.text().strip(), uidEx)

    def onClickRunCustomButton(self) -> None:
        btnInfo = self.configJson["customButtons"][self.customBtnCombox.currentIndex()]
        self.runCustom(btnInfo)

    def runCustom(self, btnInfo: dict) -> None:
        self.continueRunCustom = True
        for funcText in btnInfo["buttonCode"]:
            # if funcText.startswith('util'):
                # print('debug')
            if funcText.startswith('#'):
                continue
            try:
                exec(funcText)
            except Exception as ex:
                agsdk.log.error(f'{funcText}\n{ex}')
                exceptInfo = traceback.format_exc()
                agsdk.log.error(exceptInfo)
                break
            if not self.continueRunCustom:
                break

    def onComboxLayoutSelectionChanged(self, index: int) -> None:
        if index < 0:
            return
        if self.videoGridLayout:
            for n in range(self.viewCount):
                self.videoGridLayout.removeWidget(self.videoLabels[n])
                self.videoLabels[n].hide()
            tempWidget = QWidget()
            tempWidget.setLayout(self.videoGridLayout)
        self.videoGridLayout = QGridLayout()
        self.videoGridLayout.setContentsMargins(0, 0, 0, 0)
        self.videoGridLayout.setSpacing(2)
        self.gridWidget.setLayout(self.videoGridLayout)
        count = int(self.layoutCombox.currentText())
        side = int(math.sqrt(count))
        for row in range(side):
            for col in range(side):
                n = row * side + col
                if n < len(self.videoLabels):
                    view = self.videoLabels[n]
                else:
                    view = QLabel()
                    vtext = 'Remote'
                    if row == 0:
                        if col == 0:
                            vtext = 'Local Primary'
                        elif col == 1:
                            vtext = 'Local Secondary'
                    view.setText(vtext)
                    view.winId()
                    view.setStyleSheet('QLabel{background:rgb(200,200,200)}')
                    view.mouseDoubleClickEvent = self.onVideoLabelDoubleClick
                    view.mousePressEvent = self.onVideoLabelMousePress
                    view.mouseMoveEvent = self.onVideoLabelMouseMove
                    view.mouseReleaseEvent = self.onVideoLabelMouseRelease
                    self.videoLabels.append(view)
                self.videoGridLayout.addWidget(view, row, col)
                view.show()
        self.viewCount = count

    def onVideoLabelDoubleClick(self, event: QMouseEvent) -> None:
        # sender = self.sender()  # is none
        pos = event.pos()
        gpos = event.globalPos()
        index = -1
        for videoLabel in self.videoLabels:
            index += 1
            gpos2 = videoLabel.mapToGlobal(pos)
            if gpos == gpos2:
                break
        # print('click', index, self.onlyShowVideoLabelIndex)
        if self.onlyShowVideoLabelIndex >= 0:
            self.onComboxLayoutSelectionChanged(self.layoutCombox.currentIndex())
            self.onlyShowVideoLabelIndex = -1
        else:
            self.onlyShowVideoLabelIndex = index
            if self.videoGridLayout:
                for n in range(self.viewCount):
                    self.videoGridLayout.removeWidget(self.videoLabels[n])
                    self.videoLabels[n].hide()
                tempWidget = QWidget()
                tempWidget.setLayout(self.videoGridLayout)
            self.videoGridLayout = QGridLayout()
            self.videoGridLayout.setContentsMargins(0, 0, 0, 0)
            self.videoGridLayout.setSpacing(2)
            self.gridWidget.setLayout(self.videoGridLayout)
            self.videoGridLayout.addWidget(self.videoLabels[index], 0, 0)
            self.videoLabels[index].show()

    def onVideoLabelRightMenu(self, index: int) -> None:
        menu = QMenu(self)
        self.copyViewAction.setText(f'Copy view handle 0x{int(self.videoLabels[index].winId()):X}')
        menu.addAction(self.copyViewAction)

        found = False
        uid = -1
        for auid, ix in self.uid2ViewIndex.items():
            if ix == index:
                found = True
                uid = auid
                break
        if found > 0:
            if index in [0, 1]:
                self.copyUidAction.setText(f'Copy self uid {uid}')
            else:
                self.copyUidAction.setText(f'Copy remote uid {uid}')
            menu.addAction(self.copyUidAction)

        if index in self.viewIndex2RenderMode:
            subMenu = QMenu('RenderMode', menu)
            menu.addMenu(subMenu)
            actions = [self.renderModeHiddenAction, self.renderModeFitAction, self.renderModeAdaptiveAction]
            subMenu.addActions(actions)
            for it in agsdk.RenderMode:
                if it.value == self.viewIndex2RenderMode[index]:
                    break
            for act in actions:
                act.setChecked(act.text() == it.name)

        if index in self.viewIndex2RenderMirrorMode:
            mirrorValue = self.viewIndex2RenderMirrorMode[index]
            checked = mirrorValue != agsdk.VideoMirrorMode.Disabled
            self.renderMirrorAction.setChecked(checked)
            menu.addAction(self.renderMirrorAction)

        if index in self.viewIndex2EncoderMirrorMode:
            mirrorValue = self.viewIndex2EncoderMirrorMode[index]
            checked = mirrorValue != agsdk.VideoMirrorMode.Disabled
            self.encoderMirrorAction.setChecked(checked)
            self.encoderMirrorAction.setText('LocalEncoderMirror' if index in [0, 1] else 'RemoteEncoderMirror')
            if index in [0, 1] or agsdk.supportTrapzezoidCorrection():
                menu.addAction(self.encoderMirrorAction)

        if index in self.viewIndex2BrightnessCorrection and agsdk.supportTrapzezoidCorrection():
            enabled = self.viewIndex2BrightnessCorrection[index]
            checked = enabled
            self.brightnessCorrectionAction.setChecked(checked)
            self.brightnessCorrectionAction.setText('LocalBrightnessCorrection' if index in [0, 1] else 'RemoteBrightnessCorrection')
            menu.addAction(self.brightnessCorrectionAction)

        if index == 0:
            if 0 in self.uid2MuteAudio:
                uid = 0
            else:
                uid = -1
        if uid >= 0 and uid in self.uid2MuteAudio:
            muteValue = self.uid2MuteAudio[uid]
            self.muteAudioAction.setChecked(muteValue)
            self.muteAudioAction.setText('muteLocalAudio' if uid == 0 else 'muteRemoteAudio')
            menu.addAction(self.muteAudioAction)

        if index == 0:
            if 0 in self.uid2MuteVideo:
                uid = 0
            else:
                uid = -1
        if uid >= 0 and uid in self.uid2MuteVideo:
            muteValue = self.uid2MuteVideo[uid]
            self.muteVideoAction.setChecked(muteValue)
            self.muteVideoAction.setText('muteLocalVideo' if uid == 0 else 'muteRemoteVideo')
            menu.addAction(self.muteVideoAction)
        self.menuShowVideoLableIndex = index  # must before exec
        menu.exec_(QCursor.pos())

    def onVideoLabelMousePress(self, event: QMouseEvent) -> None:
        # sender = self.sender()  # is none
        pos = event.pos()
        gpos = event.globalPos()
        # print('onVideoLabelMousePress', pos, gpos)
        index = -1
        self.mousePressVideoLabelIndex = -1
        for videoLabel in self.videoLabels:
            index += 1
            gpos2 = videoLabel.mapToGlobal(pos)
            if gpos == gpos2:
                break
        if event.button() == Qt.RightButton:
            self.onVideoLabelRightMenu(index)
            return
        if index in [0, 1]:
            if self.localTrapezoidEnabled[index]:
                self.mousePressVideoLabelIndex = index
                self.mousePressPoint = (pos.x(), pos.y())
                self.mousePressTime = time.perf_counter()
        else:
            if self.remoteTrapezoidEnabledUid > 0:
                if self.uid2ViewIndex[self.remoteTrapezoidEnabledUid] != index:
                    return
                self.mousePressVideoLabelIndex = index
                self.mousePressPoint = (pos.x(), pos.y())
                self.mousePressTime = time.perf_counter()

    def onVideoLabelMouseMove(self, event: QMouseEvent) -> None:
        pos = event.pos()
        #gpos = event.globalPos()
        # print('onVideoLabelMouseMove', pos, gpos)
        if self.mousePressVideoLabelIndex < 0:
            return
        if self.mousePressVideoLabelIndex in [0, 1]:
            if not self.localTrapezoidEnabled[self.mousePressVideoLabelIndex]:
                return
            now = time.perf_counter()
            if now < self.mousePressTime + 0.05:
                return
            x, y = pos.x(), pos.y()
            width, height = self.videoLabels[self.mousePressVideoLabelIndex].width(), self.videoLabels[self.mousePressVideoLabelIndex].height()
            if x < 0:
                x = 0
            if x > width:
                x = width
            if y < 0:
                y = 0
            if y > height:
                y = height
            jsInfo = {
                "setDragPoint": {
                    "dragSrcPoint": {"x": self.mousePressPoint[0] / width, "y": self.mousePressPoint[1] / height},
                    "dragDstPoint": {"x": x / width, "y": y / height},
                    "dragFinished": 0,
                },
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                # "resetDragPoints": 0,
            }

            videoSourceType = agsdk.VideoSourceType(self.mousePressVideoLabelIndex)
            ret = self.rtcEngine.setLocalTrapezoidCorrectionOptions(jsInfo, videoSourceType)
            if ret == 0:
                self.mousePressTime = now
                self.localTrapezoidCalledWhenMove = True
        else:
            if self.remoteTrapezoidEnabledUid == 0:
                return
            if self.uid2ViewIndex[self.remoteTrapezoidEnabledUid] != self.mousePressVideoLabelIndex:
                return
            now = time.perf_counter()
            if now < self.mousePressTime + 0.05:
                return
            self.mousePressTime = now
            x, y = pos.x(), pos.y()
            width, height = self.videoLabels[self.mousePressVideoLabelIndex].width(), self.videoLabels[self.mousePressVideoLabelIndex].height()
            if x < 0:
                x = 0
            if x > width:
                x = width
            if y < 0:
                y = 0
            if y > height:
                y = height
            jsInfo = {
                "setDragPoint": {
                    "dragSrcPoint": {"x": self.mousePressPoint[0] / width, "y": self.mousePressPoint[1] / height},
                    "dragDstPoint": {"x": x / width, "y": y / height},
                    "dragFinished": 0,
                },
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                # "resetDragPoints": 0,
            }

            self.rtcEngine.setRemoteTrapezoidCorrectionOptions(self.remoteTrapezoidEnabledUid, jsInfo)
            self.remoteTrapezoidCalledWhenMove = True

    def onVideoLabelMouseRelease(self, event: QMouseEvent) -> None:
        pos = event.pos()
        gpos = event.globalPos()
        #print('onVideoLabelMouseRelease', pos, gpos)
        if event.button() == Qt.RightButton:
            return
        if self.mousePressVideoLabelIndex < 0:
            return
        if self.mousePressVideoLabelIndex in [0, 1]:
            if not self.localTrapezoidCalledWhenMove:
                return
            x, y = pos.x(), pos.y()
            width, height = self.videoLabels[self.mousePressVideoLabelIndex].width(), self.videoLabels[self.mousePressVideoLabelIndex].height()
            if x < 0:
                x = 0
            if x > width:
                x = width
            if y < 0:
                y = 0
            if y > height:
                y = height
            jsInfo = {
                "setDragPoint": {
                    "dragSrcPoint": {"x": self.mousePressPoint[0] / width, "y": self.mousePressPoint[1] / height},
                    "dragDstPoint": {"x": x / width, "y": y / height},
                    "dragFinished": 1,
                },
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                # "resetDragPoints": 0,
            }

            videoSourceType = agsdk.VideoSourceType(self.mousePressVideoLabelIndex)
            self.rtcEngine.setLocalTrapezoidCorrectionOptions(jsInfo, videoSourceType)
            self.mousePressVideoLabelIndex = -1
            self.localTrapezoidCalledWhenMove = False
        else:
            if not self.remoteTrapezoidCalledWhenMove:
                return
            x, y = pos.x(), pos.y()
            width, height = self.videoLabels[self.mousePressVideoLabelIndex].width(), self.videoLabels[self.mousePressVideoLabelIndex].height()
            if x < 0:
                x = 0
            if x > width:
                x = width
            if y < 0:
                y = 0
            if y > height:
                y = height
            jsInfo = {
                "setDragPoint": {
                    "dragSrcPoint": {"x": self.mousePressPoint[0] / width, "y": self.mousePressPoint[1] / height},
                    "dragDstPoint": {"x": x / width, "y": y / height},
                    "dragFinished": 1,
                },
                "assistLine": int(self.assistLineCheckBox.isChecked()),
                # "resetDragPoints": 0,
            }
            self.rtcEngine.setRemoteTrapezoidCorrectionOptions(self.remoteTrapezoidEnabledUid, jsInfo)
            self.mousePressVideoLabelIndex = -1
            self.remoteTrapezoidCalledWhenMove = False

    def clearViews(self, index: List[int]) -> None:
        self.clearViewIndexs.extend(index)
        self.clearViewTimer.stop()
        self.clearViewTimer.start(300)

    def onClearViewTimeout(self) -> None:
        if self.checkAutoRepaintVideoBackground.isChecked():
            for index in self.clearViewIndexs:
                vtext = 'Remote'
                if index == 0:
                    vtext = 'LocalPrimary'
                elif index == 1:
                    vtext = 'LocalSecondary'
                self.videoLabels[index].setText(vtext)
                self.videoLabels[index].repaint()
        self.clearViewIndexs.clear()

    def getFreeView(self) -> Tuple[int, int]:
        freeView, freeViewIndex = 0, -1
        for i in range(2, self.viewCount):
            if i not in self.viewUsingIndex:
                freeView, freeViewIndex = int(self.videoLabels[i].winId()), i
                break
        return freeView, freeViewIndex

    def onRtcEngineCallbackInThread(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsInfo: str) -> None:
        self.CallbackSignal.emit((userData, callbackTimeSinceEpoch, funcName, jsInfo))
        # print('callback in thread:', threading.get_ident(), callbackTimeSinceEpoch, funcName, jsInfo)

    def onRtcEngineCallback(self, args: Tuple[str, int, str, str]) -> None:
        userData, callbackTimeSinceEpoch, funcName, jsStr = args
        #print(f'callbak to UI thread {threading.get_ident()}: userData {userData} epoch {callbackTimeSinceEpoch} \n{funcName} {jsStr}')
        jsInfo = json.loads(jsStr)
        if funcName in self.rtcEngineEventHandler:
            self.rtcEngineEventHandler[funcName](userData, callbackTimeSinceEpoch, funcName, jsStr, jsInfo)
        else:
            agsdk.log.info(f'there is no handler for {funcName}')

    def onClickLastError(self) -> None:
        self.tipDlg.showTip()

    def threadFuncDemo(self, signal: pyqtSignal, threadId: int, args: Any) -> None:
        count = args  # type: int
        for i in range(count):
            arg = time.time()
            print('thread[{}] sig {} send {} {}'.format(threadId, id(signal), i, arg))
            signal.emit((threadId, 0, i, arg))
            time.sleep(0.01)

    def threadNotifyDemo(self, threadId: int, msgId: int, args: list) -> None:
        print('reveive thread[{}] msg id {}, args: {}'.format(threadId, msgId, args))
        if msgId == MsgIDThreadExit:
            print('thread', threadId, 'exit')

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_Escape:
            event.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        print('closeEvent')
        if self.previewed:
            self.onClickStopPreview()
        if self.joined:
            self.onClickLeaveChannel()
        if self.joinedEx:
            self.onClickLeaveChannelEx()
        self.onClickRelease()
        self.clearViewTimer.stop()
        self.tipDlg.close()
        self.beautyOptionsDlg.close()
        self.trapezoidCorrectionDlg.close()
        self.codeDlg.close()
        self.dataStreamDlg.close()
        event.accept()

    # EngineCallback methods
    def initializeEventHandlers(self) -> None:
        self.rtcEngineEventHandler = {
            'onError': self.onError,
            'onWarning': self.onWarning,
            'onJoinChannelSuccess': self.onJoinChannelSuccess,
            'onUserJoined': self.onUserJoined,
            'onUserOffline': self.onUserOffline,
            'onFirstLocalVideoFrame': self.onFirstLocalVideoFrame,
            'onFirstLocalVideoFramePublished': self.onFirstLocalVideoFramePublished,
            'onFirstRemoteVideoDecoded': self.onFirstRemoteVideoDecoded,
            'onAudioDeviceStateChanged': self.dummyCallback,
            'onLocalAudioStateChanged': self.dummyCallback,
            'onLocalVideoStateChanged': self.onLocalVideoStateChanged,
            'onRemoteVideoStateChanged': self.onRemoteVideoStateChanged,
            'onStreamMessage': self.onStreamMessage,
            'onStreamMessageError': self.onStreamMessageError,
            'onTrapezoidAutoCorrectionFinished': self.onTrapezoidAutoCorrectionFinished,
            'onSnapshotTaken': self.onSnapshotTaken,
            'onServerSuperResolutionResult': self.onServerSuperResolutionResult,

        }

    def dummyCallback(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onSelectSdkCallback(self, sdkBinDir: str) -> None:
        self.selectSdkDlg.close()
        agsdk.chooseSdkBinDir(sdkBinDir)
        if agsdk.agorasdk.SdkVerson < '3.6.200':
            self.setCameraConfigButton.setEnabled(False)
            self.loadExtensionProviderButton.setEnabled(False)
            self.enableExtensionButton.setEnabled(False)
            self.beautyOptionsButton.setEnabled(False)
        if not agsdk.supportTrapzezoidCorrection():
            self.trapezoidCorrectionButton.setEnabled(False)

    def onComboxCustomButtonSelectionChanged(self, currentIndex: int) -> None:
        btnInfo = self.configJson["customButtons"][currentIndex]
        self.customBtnCombox.setToolTip('\n'.join(btnInfo["buttonCode"]))

    def onComboxAppNameSelectionChanged(self, currentIndex: int) -> None:
        pass

    def onComboxPresetSelectionChanged(self, currentIndex: int) -> None:
        width, height = self.presetCombox.currentText().split('*')
        self.captureWidthEdit.setText(width)
        self.captureHeightEdit.setText(height)
        self.encodeWidthEdit.setText(width)
        self.encodeHeightEdit.setText(height)

    def onSourceTypeIndexChanged(self, currentIndex: int) -> None:
        #['Primary', 'Secondary', 'Screen', 'ScreenSecondary', 'Custom']
        curText = self.sourceTypeCombox.currentText()
        if curText == 'Primary':
            self.curVideoSourceType = agsdk.VideoSourceType.CameraPrimary
            self.curMediaSourceType = agsdk.MediaSourceType.PrimaryCameraSource
        elif curText == 'Secondary':
            self.curVideoSourceType = agsdk.VideoSourceType.CameraSecondary
            self.curMediaSourceType = agsdk.MediaSourceType.SecondaryCameraSource
        elif curText == 'Screen':
            self.curVideoSourceType = agsdk.VideoSourceType.Screen
            self.curMediaSourceType = agsdk.MediaSourceType.PrimaryScreenSource
        elif curText == 'ScreenSecondary':
            self.curVideoSourceType = agsdk.VideoSourceType.ScreenSecondary
            self.curMediaSourceType = agsdk.MediaSourceType.SecondaryScreenSource
        elif curText == 'Custom':
            self.curVideoSourceType = agsdk.VideoSourceType.Custom
            self.curMediaSourceType = agsdk.MediaSourceType.CustomVideoSource

        if self.curVideoSourceType == agsdk.VideoSourceType.Custom:
            self.localViewIndexCombox.show()
        else:
            self.localViewIndexCombox.hide()

    def checkSDKResult(self, code: int) -> None:
        if code != 0 and self.rtcEngine:
            errorDesc = self.rtcEngine.getErrorDescription(abs(code))
            errorInfo = f'{agorasdk.agorasdk.LastAPICall}\n\nerror: {code}\nInfo: {errorDesc}'
            agsdk.log.info(errorInfo)
            self.tipDlg.resize(200, 100)
            self.tipDlg.showTip(errorInfo)

    def onClickInitialize(self) -> None:
        if self.rtcEngine is None:
            self.rtcEngine = agsdk.RtcEngine()
        version, build = self.rtcEngine.getVersion()
        self.setWindowTitle(f'{DemoTile} Version={version}, Build={build}, SdkDir={agsdk.agorasdk.SdkBinDir}')
        appName = self.configJson['appNameList'][self.appNameComBox.currentIndex()]['appName']
        appId = self.configJson['appNameList'][self.appNameComBox.currentIndex()]['appId']
        if appId == '00000000000000000000000000000000':
            QMessageBox.warning(None, 'Error', f'You need to set a valid AppId in the config file:\n{self.configPath}')
        elif appName.startswith('Agora'):
            appId = transformAppId(appId)
        self.appId = appId
        context = agsdk.RtcEngineContext(appId)
        context.logConfig.logPath = os.path.join(agsdk.LogDir, 'AgoraSdk_log.log')
        context.channelProfile = agsdk.ChannelProfile.LiveBroadcasting
        ret = self.rtcEngine.initalize(context, self.onRtcEngineCallbackInThread)
        self.checkSDKResult(ret)
        self.inited = True

    def onClickRelease(self) -> None:
        if not self.rtcEngine:
            return
        if self.joinedEx:
            self.onClickLeaveChannelEx()
        if self.joined:
            self.onClickLeaveChannel()
        self.rtcEngine.release(sync=True)
        self.rtcEngine.resetCaptureVideoFrame()
        self.rtcEngine = None
        self.loadedExtensions.clear()
        self.uid2ViewIndex.clear()
        self.viewIndex2RenderMode.clear()
        self.viewIndex2RenderMirrorMode.clear()
        self.viewIndex2EncoderMirrorMode.clear()
        self.viewIndex2BrightnessCorrection.clear()
        self.uid2MuteAudio.clear()
        self.uid2MuteVideo.clear()
        self.viewUsingIndex.clear()
        self.setWindowTitle(DemoTile)
        self.sourceTypeCombox.setCurrentIndex(0)

    def onClickSetChannelProfile(self) -> None:
        if not self.rtcEngine:
            return
        profile = agsdk.ChannelProfile(int(self.channelProfileCombox.currentText()[-1]))
        ret = self.rtcEngine.setChannelProfile(profile)
        self.checkSDKResult(ret)

    def onClickSetClientRole(self) -> None:
        if not self.rtcEngine:
            return
        role = agsdk.ClientRole(int(self.clientRoleCombox.currentText()[-1]))
        ret = self.rtcEngine.setClientRole(role)
        self.checkSDKResult(ret)

    def onClickEnableAudio(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.enableAudio()
        self.checkSDKResult(ret)

    def onClickDisableAudio(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.disableAudio()
        self.checkSDKResult(ret)

    def onClickEnableVideo(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.enableVideo()
        self.checkSDKResult(ret)

    def onClickDisableVideo(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.disableVideo()
        self.checkSDKResult(ret)

    def onClickEnableLocalAudio(self, checked) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.enableLocalAudio(checked)
        self.checkSDKResult(ret)

    def onClickEnableLocalVideo(self, checked) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.enableLocalVideo(checked)
        self.checkSDKResult(ret)

    def onClickRegisterVideoFrameObserver(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.registerVideoFrameObserver()
        self.checkSDKResult(ret)

    def onClickSaveCaptureVideoFrame(self) -> None:
        save = self.saveCaptureVideoFrameCheckBox.isChecked()
        count = int(self.saveCaptureVideoFrameCountEdit.text())
        self.rtcEngine.saveCaptureVideoFrame(save, count)
        self.rtcEngine.saveSecondaryCaptureVideoFrame(save, count)

    def onClickSaveRenderVideoFrame(self) -> None:
        save = self.saveRenderVideoFrameCheckBox.isChecked()
        count = int(self.saveCaptureVideoFrameCountEdit.text())
        self.rtcEngine.saveRenderVideoFrame(save, count)

    def onClickGetVideoDevices(self) -> None:
        if not self.rtcEngine:
            return
        self.videoDevices = self.rtcEngine.enumerateVideoDevices()
        self.videoDevicesCombox.clear()
        if self.videoDevices:
            self.videoDevicesCombox.addItems(it[0] for it in self.videoDevices)
            self.videoDevicesCombox.setCurrentIndex(-1)

    def onClickSetVideoDevice(self) -> None:
        if not self.rtcEngine:
            return
        curIndex = self.videoDevicesCombox.currentIndex()
        if curIndex < 0:
            return
        deviceId = self.videoDevices[curIndex][1]
        ret = self.rtcEngine.setVideoDevice(deviceId)
        self.checkSDKResult(ret)

    def onClickGetVideoDevice(self) -> None:
        if not self.rtcEngine:
            return
        ret, deviceId = self.rtcEngine.getVideoDevice()
        print(f'getVideoDevice result={ret}, deviceId="{deviceId}"')

    def onClickSetCameraCapturerConfiguration(self) -> None:
        if not self.rtcEngine:
            return
        cameraConfig = agsdk.CameraCapturerConfiguration()
        curIndex = self.videoDevicesCombox.currentIndex()
        if self.videoDevices and curIndex >= 0:
            cameraConfig.deviceId = self.videoDevices[curIndex][1]
        cameraConfig.width = int(self.captureWidthEdit.text())
        cameraConfig.height = int(self.captureHeightEdit.text())
        cameraConfig.bitrate = int(self.captureFpsCombox.currentText())
        ret = self.rtcEngine.setCameraCapturerConfiguration(cameraConfig)
        self.checkSDKResult(ret)

    def onClickStartPrimaryCameraCapture(self) -> None:
        if not self.rtcEngine:
            return
        cameraConfig = agsdk.CameraCapturerConfiguration()
        curIndex = self.videoDevicesCombox.currentIndex()
        if self.videoDevices and curIndex >= 0:
            cameraConfig.deviceId = self.videoDevices[curIndex][1]
        cameraConfig.width = int(self.captureWidthEdit.text())
        cameraConfig.height = int(self.captureHeightEdit.text())
        cameraConfig.frameRate = int(self.captureFpsCombox.currentText())
        ret = self.rtcEngine.startPrimaryCameraCapture(cameraConfig)
        self.checkSDKResult(ret)

    def onClickStopPrimaryCameraCapture(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.stopPrimaryCameraCapture()
        self.checkSDKResult(ret)

    def onClickStartSecondaryCameraCapture(self) -> None:
        if not self.rtcEngine:
            return
        cameraConfig = agsdk.CameraCapturerConfiguration()
        curIndex = self.videoDevicesCombox.currentIndex()
        if self.videoDevices and curIndex >= 0:
            cameraConfig.deviceId = self.videoDevices[curIndex][1]
        cameraConfig.width = int(self.captureWidthEdit.text())
        cameraConfig.height = int(self.captureHeightEdit.text())
        cameraConfig.frameRate = int(self.captureFpsCombox.currentText())
        ret = self.rtcEngine.startSecondaryCameraCapture(cameraConfig)
        self.checkSDKResult(ret)

    def onClickStopSecondaryCameraCapture(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.stopSecondaryCameraCapture()
        self.checkSDKResult(ret)

    def onClickSetVideoEncoderConfiguration(self) -> None:
        if not self.rtcEngine:
            return
        videoConfig = agsdk.VideoEncoderConfiguration()
        videoConfig.codecType = agsdk.VideoCodec(int(self.codecCombox.currentText().split()[-1]))
        videoConfig.width = int(self.encodeWidthEdit.text())
        videoConfig.height = int(self.encodeHeightEdit.text())
        videoConfig.frameRate = int(self.encodeFpsCombox.currentText())
        videoConfig.bitrate = int(self.bitrateEdit.text())
        videoConfig.minBitrate = int(self.minBitrateEdit.text())
        videoConfig.mirrorMode = agsdk.VideoMirrorMode(int(self.mirrorCombox.currentText()[-1]))
        videoConfig.orientationMode = agsdk.OrientationMode(int(self.orientionCombox.currentText()[-1]))
        videoConfig.degradationPreference = agsdk.DegradationPreference(int(self.degradationPreferenceCombox.currentText()[-1]))
        if self.painter and (self.pixmap.width() != videoConfig.width or self.pixmap.height() != self.pixmap.height):
            self.painter = None
        if self.exConfigCheck.isChecked():
            self.videoConfigEx = videoConfig
            ret = self.rtcEngine.setVideoEncoderConfigurationEx(videoConfig, self.rtcConnection)
            self.viewIndex2EncoderMirrorMode[1] = videoConfig.mirrorMode
        else:
            self.videoConfig = videoConfig
            ret = self.rtcEngine.setVideoEncoderConfiguration(videoConfig, connectionId=agsdk.DefaultConnectionId)
            self.viewIndex2EncoderMirrorMode[0] = videoConfig.mirrorMode
        self.checkSDKResult(ret)

    def onClickSetupLocalVideo(self) -> None:
        if not self.rtcEngine:
            return
        if self.curVideoSourceType == agsdk.VideoSourceType.Custom:
            viewIndex = int(self.localViewIndexCombox.currentText())
            self.customViewIndex = viewIndex
        else:
            viewIndex = 0 if self.curVideoSourceType in [agsdk.VideoSourceType.CameraPrimary, agsdk.VideoSourceType.Screen] else 1
        viewHandle = int(self.videoLabels[viewIndex].winId())
        mirrorValue = agsdk.VideoMirrorMode(int(self.mirrorCombox.currentText()[-1]))
        canvas = agsdk.VideoCanvas(uid=0, view=viewHandle, mirrorMode=mirrorValue, renderMode=self.defaultRenderMode, sourceType=self.curVideoSourceType)
        if agsdk.agorasdk.SdkVerson >= '3.8.200':
            canvas.setupMode = agsdk.ViewSetupMode.Add
        ret = self.rtcEngine.setupLocalVideo(canvas)
        self.checkSDKResult(ret)
        self.viewIndex2RenderMode[viewIndex] = self.defaultRenderMode
        self.viewIndex2RenderMirrorMode[viewIndex] = mirrorValue
        self.viewIndex2BrightnessCorrection[viewIndex] = False

    def onClickStartPreview(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.startPreview(self.curVideoSourceType)
        self.checkSDKResult(ret)
        self.previewed = True

    def onClickStopPreview(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.stopPreview(self.curVideoSourceType)
        self.checkSDKResult(ret)
        self.previewed = False
        self.clearViews([0])

    def onClickLoadExtensionProvider(self) -> None:
        if not self.rtcEngine:
            return
        if agsdk.agorasdk.SdkVerson < '3.6.200':
            return
        for binName in self.configJson["loadExtensions"]:
            binPath = os.path.join(agsdk.agorasdk.SdkBinDirFull, binName)
            binExists = True
            if not os.path.exists(binPath):
                binExists = False
                if DevelopDllDir:
                    binPath = os.path.join(DevelopDllDir, binName)
                    if os.path.exists(binPath):
                        binExists = True
            if binExists:
                print(f'path={binPath}')
                self.loadedExtensions.append(binName)
                ret = self.rtcEngine.loadExtensionProvider(binPath)
                self.checkSDKResult(ret)

    def onClickEnableExtension(self) -> None:
        if not self.rtcEngine:
            return
        if agsdk.agorasdk.SdkVerson < '3.6.200':
            return
        for extName in self.loadedExtensions:
            if extName.startswith('libagora_video_process'):
                ret = self.rtcEngine.enableExtension('agora', 'beauty', True, self.curMediaSourceType)
                self.checkSDKResult(ret)
                if agsdk.agorasdk.SdkVerson.startswith('3.7.204.dev'):
                    ret = self.rtcEngine.enableExtension('agora', 'remote_beauty', True, agsdk.MediaSourceType.UnknownMediaSource)
                    self.checkSDKResult(ret)
            elif extName.startswith('libagora_segmentation'):
                ret = self.rtcEngine.enableExtension("agora_segmentation", "PortraitSegmentation", True, self.curMediaSourceType)
                self.checkSDKResult(ret)

    def onClickBeautyOptions(self) -> None:
        self.beautyOptionsDlg.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.beautyOptionsDlg.raise_()
        self.beautyOptionsDlg.activateWindow()

    def onClickTrapezoidCorrection(self) -> None:
        self.trapezoidCorrectionDlg.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.trapezoidCorrectionDlg.raise_()
        self.trapezoidCorrectionDlg.activateWindow()

    def onClickDataStreamTest(self) -> None:
        self.dataStreamDlg.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.dataStreamDlg.raise_()
        self.dataStreamDlg.activateWindow()

    def onClickRunCode(self) -> None:
        if self.remoteUidCombox.count() > 0:
            curText = self.codeDlg.codeEdit.toPlainText()
            remoteUid, index = util.getStrBetween(curText, 'remoteUid=', '\n')
            if index > 0 and remoteUid not in (self.remoteUidCombox.itemText(it) for it in range(self.remoteUidCombox.count())):
                newText = curText.replace(f'remoteUid={remoteUid}', f'remoteUid={self.remoteUidCombox.itemText(0)}')
                if curText != newText:
                    self.codeDlg.codeEdit.setPlainText(newText)
        self.codeDlg.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.codeDlg.raise_()
        self.codeDlg.activateWindow()

    def onBeautyOptionsEnabledOrDisabled(self, enabled: bool) -> None:
        if not self.rtcEngine:
            return
        beautyOptions = self.beautyOptionsDlg.getBeautyOptions()
        ret = self.rtcEngine.setBeautyEffectOptions(enabled, beautyOptions, self.curMediaSourceType)
        self.checkSDKResult(ret)

    def onClickSendStreamMessageCallback(self, message: str) -> bool:
        if not self.rtcEngine:
            return
        if not self.joined:
            return
        if self.dataStreamId == 0:
            ret, self.dataStreamId = self.rtcEngine.createDataStream()
        if self.dataStreamId == 0:
            return
        self.rtcEngine.sendStreamMessage(self.dataStreamId, message)
        return True

    def setPushVideoFrameFromFile(self, path: str, videoFormat: agorasdk.VideoPixelFormat = agorasdk.VideoPixelFormat.I420, width: int = 0, height: int = 0, fps: int = 15):
        if path and os.path.exists(path):
            if self.pushVideoFrameFile:
                self.pushVideoFrameFile.close()
                self.pushVideoFrameFile = None
            self.pushVideoFrameFile = VideoFrameFile(path, videoFormat, width, height, fps)
            self.pushTimer.setInterval(1000 // fps)
        else:
            if self.pushVideoFrameFile:
                self.pushVideoFrameFile.close()
                self.pushVideoFrameFile = None

    def onPushVideoFrameTimer(self) -> None:
        rawData = 0
        videoFormat = agsdk.VideoPixelFormat.I420
        videoWidth = 0
        videoHeight = 0
        if self.pushVideoFrameFile and self.pushVideoFrameFile.fobj:
            if self.pushVideoFrameFile.videoFormat == agorasdk.VideoPixelFormat.RGBA:
                frameSize = self.pushVideoFrameFile.width * self.pushVideoFrameFile.height * 4
            elif self.pushVideoFrameFile.videoFormat == agorasdk.VideoPixelFormat.BGRA:
                frameSize = self.pushVideoFrameFile.width * self.pushVideoFrameFile.height * 4
            elif self.pushVideoFrameFile.videoFormat == agorasdk.VideoPixelFormat.I420:
                frameSize = self.pushVideoFrameFile.width * self.pushVideoFrameFile.height * 3 // 2
            elif self.pushVideoFrameFile.videoFormat == agorasdk.VideoPixelFormat.NV21:
                frameSize = self.pushVideoFrameFile.width * self.pushVideoFrameFile.height * 3 // 2
            else:
                frameSize = 0
            if frameSize > 0:
                carraytype = ctypes.c_char * frameSize
                rawData = carraytype()
                videoFormat = self.pushVideoFrameFile.videoFormat
                videoWidth = self.pushVideoFrameFile.width
                videoHeight = self.pushVideoFrameFile.height
                self.pushVideoFrameFile.fobj.readinto(rawData)
                if self.pushVideoFrameFile.fobj.tell() >= self.pushVideoFrameFile.fileSize:
                    self.pushVideoFrameFile.fobj.seek(0, 0)
        else:
            if self.painter is None:
                if self.isPushEx:
                    self.pixmap = QPixmap(self.videoConfigEx.width, self.videoConfigEx.height)
                else:
                    self.pixmap = QPixmap(self.videoConfig.width, self.videoConfig.height)
                #self.pixmap.fill(QColor(204, 232, 207))
                self.painter = QPainter()   # QPainter(self.pixmap)
            self.painter.begin(self.pixmap)
            font = self.painter.font()
            font.setFamilies(['微软雅黑', '黑体', 'Sans-Serif'])
            font.setBold(True)
            font.setPointSize(int(font.pointSize() * self.pixmap.height() / 180))
            self.painter.setFont(font)
            self.painter.fillRect(0, 0, self.pixmap.width(), self.pixmap.height(), QColor(204, 232, 207))
            x, y = 10, 10
            fm = self.painter.fontMetrics()
            text = f"""uid:{self.pushUid} SrcSize: {self.pixmap.width()}*{self.pixmap.height()}
{datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds')}"""
            self.painter.drawText(x, y, self.pixmap.width() - x, self.pixmap.height() - y, Qt.TextWordWrap, text)
            y += (text.count('\n') + 1) * fm.height() + font.pointSize() // 2
            if self.pushText:
                self.painter.drawText(x, y, self.pixmap.width() - x, self.pixmap.height() - y, Qt.TextWordWrap, self.pushText)
            self.painter.end()
            image = self.pixmap.toImage()
            # if not os.path.exists('agorapush.bmp'):
                # image.save('agorapush.bmp')
            bits = image.constBits()    # type(bits) == PyQt5.sip.voidptr
            bits.setsize(image.byteCount())
            rawData = ctypes.c_void_p(int(bits))
            videoFormat = agorasdk.VideoPixelFormat.RGBA
            videoWidth = self.pixmap.width()
            videoHeight = self.pixmap.height()

        if not rawData:
            print('wrong arguments, can not pushVideoFrame')
            return
        if self.isPushEx:
            self.rtcEngine.pushVideoFrameEx(rawData, videoFormat, videoWidth, videoHeight, self.rtcConnection)
        else:
            self.rtcEngine.pushVideoFrame(rawData, videoFormat, videoWidth, videoHeight)

    def onClickJoinChannel(self) -> None:
        if not self.rtcEngine:
            return
        self.channelName = self.channelNameEdit.text().strip()
        uid = int(self.uidEdit.text()) or 0
        while uid in self.localUids:
            uid += 1
            self.uidEdit.setText(str(uid))
        token = self.tokenEdit.text().strip()
        info = self.infoEdit.text().strip()
        if self.curVideoSourceType == agsdk.VideoSourceType.Custom:
            self.rtcEngine.setExternalVideoSource(True)
            self.isPushEx = False
            if self.pushVideoFrameFile and self.pushVideoFrameFile.fobj:
                self.pushTimer.start(1000 // self.pushVideoFrameFile.fps)
            else:
                self.pushTimer.start(1000 // self.videoConfig.frameRate)
            options = agsdk.ChannelMediaOptions(autoSubscribeAudio=True, autoSubscribeVideo=True, publishAudioTrack=True, publishCustomVideoTrack=True)
            self.channelOptions = options
            ret = self.rtcEngine.joinChannelWithOptions(self.channelName, uid, token, options)
        else:
            ret = self.rtcEngine.joinChannel(self.channelName, uid, token, info)
        self.checkSDKResult(ret)
        self.joined = True
        self.localUids.append(uid)
        if 0 not in self.viewIndex2EncoderMirrorMode:
            self.viewIndex2EncoderMirrorMode[0] = agsdk.VideoMirrorMode.Disabled

    def onClickLeaveChannel(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.leaveChannel()
        self.checkSDKResult(ret)
        self.rtcEngine.resetCaptureVideoFrame()
        self.rtcEngine.resetSecondaryCaptureVideoFrame()
        self.rtcEngine.resetRenderVideoFrame()
        self.joined = False
        self.channelName = ''
        self.dataStreamId = 0
        if self.channelOptions and self.channelOptions.publishCustomVideoTrack == 1:
            if self.customViewIndex in self.viewIndex2EncoderMirrorMode:
                self.viewIndex2EncoderMirrorMode.pop(self.customViewIndex)
            self.customViewIndex = -1
            self.pushUid = 0
        else:
            pass
        self.channelOptions = None
        # todo clear all?
        self.uid2ViewIndex.clear()
        self.viewIndex2RenderMirrorMode.clear()
        self.viewIndex2EncoderMirrorMode.clear()
        self.viewIndex2BrightnessCorrection.clear()
        self.uid2MuteAudio.clear()
        self.uid2MuteVideo.clear()
        self.viewUsingIndex.clear()
        self.remoteUidCombox.clear()
        self.clearViews(range(self.viewCount))
        self.uidEdit.setText('0')
        self.enableLocalTrapezoidPrimaryCheckBox.setChecked(False)
        self.enableRemoteTrapezoidCheckBox.setChecked(False)
        self.localTrapezoidEnabled[0] = False
        self.remoteTrapezoidEnabledUid = 0
        if self.pushTimer.isActive():
            self.pushTimer.stop()
            self.rtcEngine.setExternalVideoSource(False)

    def onClickJoinChannelEx(self) -> None:
        if not self.rtcEngine:
            return
        self.channelNameEx = self.channelNameEdit.text().strip()
        uid = int(self.uidExEdit.text()) or 0
        while uid in self.localUids:
            uid += 1
            self.uidExEdit.setText(str(uid))
        if self.checkMuteSecondaryCamera.isChecked():
            self.rtcEngine.muteRemoteAudioStream(uid, True)
            self.rtcEngine.muteRemoteVideoStream(uid, True)
        token = self.tokenEdit.text().strip()
        #info = self.infoEdit.text().strip()
        self.autoSubscribeVideoEx = int(self.channelName != self.channelNameEx)
        options = agsdk.ChannelMediaOptions(autoSubscribeAudio=self.autoSubscribeAudioEx, autoSubscribeVideo=self.autoSubscribeVideoEx)
        if self.curVideoSourceType == agsdk.VideoSourceType.CameraPrimary:
            options.publishCameraTrack = True
        elif self.curVideoSourceType == agsdk.VideoSourceType.CameraSecondary:
            options.publishSecondaryCameraTrack = True
        elif self.curVideoSourceType == agsdk.VideoSourceType.Screen:
            options.publishScreenTrack = True
        elif self.curVideoSourceType == agsdk.VideoSourceType.ScreenSecondary:
            options.publishSecondaryScreenTrack = True
        elif self.curVideoSourceType == agsdk.VideoSourceType.Custom:
            options.publishCustomVideoTrack = True
            self.rtcEngine.setExternalVideoSource(True)
            self.isPushEx = True
            if self.pushVideoFrameFile and self.pushVideoFrameFile.fobj:
                self.pushTimer.start(1000 // self.pushVideoFrameFile.fps)
            else:
                self.pushTimer.start(1000 // self.videoConfigEx.frameRate)
        self.channelExOptions = options
        self.rtcConnection = agsdk.RtcConnection(self.channelNameEx, uid)
        ret = self.rtcEngine.joinChannelEx(self.rtcConnection, token, options)
        self.checkSDKResult(ret)
        self.joinedEx = True
        self.enableLocalTrapezoidSecondaryCheckBox.setChecked(False)
        self.localTrapezoidEnabled[1] = False
        if 1 not in self.viewIndex2EncoderMirrorMode:
            self.viewIndex2EncoderMirrorMode[1] = agsdk.VideoMirrorMode.Disabled

    def onClickLeaveChannelEx(self) -> None:
        if not self.rtcEngine:
            return
        uid = int(self.uidExEdit.text())
        rtcConnection = agsdk.RtcConnection(self.channelNameEx, uid)
        ret = self.rtcEngine.leaveChannelEx(rtcConnection)
        self.checkSDKResult(ret)
        self.joinedEx = False
        self.channelNameEx = ''
        if self.rtcConnection.localUid in self.uid2ViewIndex:
            self.uid2ViewIndex.pop(self.rtcConnection.localUid)
        if self.channelExOptions and self.channelExOptions.publishCustomVideoTrack == 1:
            if self.customViewIndex in self.viewIndex2EncoderMirrorMode:
                self.viewIndex2EncoderMirrorMode.pop(self.customViewIndex)
            self.customViewIndex = -1
            self.pushUid = 0
        else:
            if 1 in self.viewIndex2EncoderMirrorMode:
                self.viewIndex2EncoderMirrorMode.pop(1)
        self.channelExOptions = None
        if self.pushTimer.isActive():
            self.pushTimer.stop()
            self.rtcEngine.setExternalVideoSource(False)

    def onClickStartScreenCaptureByScreenRect(self) -> None:
        if not self.rtcEngine:
            return
        rect = [int(it) for it in self.screenRectEdit.text().split(',')]
        screenFps = int(self.screenFpsEdit.text())
        excludeWindows = []
        for it in self.excludeWindowEdit.text().split(','):
            it = it.strip()
            if it:
                if it[:2] in ['0x', '0X']:
                    excludeWindows.append(int(it, base=16))
                else:
                    excludeWindows.append(int(it, base=10))
        screenRect = agsdk.Rectangle(rect[0], rect[1], rect[2], rect[3])
        regionRect = agsdk.Rectangle(0, 0, 0, 0)
        captureParams = agsdk.ScreenCaptureParameters(1920, 1080, fps=screenFps, bitrate=0, excludeWindowList=excludeWindows)
        ret = self.rtcEngine.startScreenCaptureByScreenRect(screenRect, regionRect, captureParams)
        self.checkSDKResult(ret)

    def onClickStopScreenCapture(self) -> None:
        if not self.rtcEngine:
            return
        ret = self.rtcEngine.stopScreenCapture()
        self.checkSDKResult(ret)

    def onError(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onWarning(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onJoinChannelSuccess(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        uid = jsInfo['uid']
        if userData == 'Channel':
            self.uidEdit.setText(str(uid))
            if self.channelOptions and self.channelOptions.publishCustomVideoTrack == 1 and self.customViewIndex >= 0:
                self.uid2ViewIndex[uid] = self.customViewIndex
                self.pushUid = uid
            else:
                self.uid2ViewIndex[uid] = 0
            self.uid2MuteAudio[0] = False
            self.uid2MuteVideo[0] = False
        elif userData == 'ChannelEx':
            # self.uidExEdit.setText(str(uid))
            if self.channelExOptions and self.channelExOptions.publishCustomVideoTrack == 1 and self.customViewIndex >= 0:
                self.uid2ViewIndex[uid] = self.customViewIndex
                self.pushUid = uid
            else:
                self.uid2ViewIndex[uid] = 1

    def onUserJoined(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        if self.rtcEngine is None:
            return
        if userData == 'ChannelEx' and not self.autoSubscribeVideoEx:
            return
        uid = jsInfo['uid']
        if uid in self.localUids:
            return
        self.remoteUidCombox.addItem(f'{uid}')
        if not self.checkAutoSetupRemoteVideo.isChecked():
            agsdk.log.warn(f'uid {uid} joined, but do not setupRemoteVideo for he/she, AutoSetupRemoteVideo is not checked')
            return
        for i in range(2, self.viewCount):
            if i not in self.viewUsingIndex:
                break
        else:
            index = self.layoutCombox.currentIndex() + 1
            if index < self.layoutCombox.count():
                self.layoutCombox.setCurrentIndex(index)
                # self.onComboxLayoutSelectionChanged(index)
        freeView, freeViewIndex = self.getFreeView()
        self.videoLabels[freeViewIndex].setText(f'Remote uid {uid}')
        mirrorValue = agsdk.VideoMirrorMode.Disabled
        if userData == 'ChannelEx':
            self.rtcEngine.setupRemoteVideoEx(videoCanvas=agsdk.VideoCanvas(uid=uid, view=freeView, mirrorMode=mirrorValue, renderMode=self.defaultRenderMode), connection=self.rtcConnection)
        else:
            self.rtcEngine.setupRemoteVideo(videoCanvas=agsdk.VideoCanvas(uid=uid, view=freeView, mirrorMode=mirrorValue, renderMode=self.defaultRenderMode))
        self.uid2ViewIndex[uid] = freeViewIndex
        self.viewIndex2RenderMode[freeViewIndex] = self.defaultRenderMode
        self.viewIndex2RenderMirrorMode[freeViewIndex] = mirrorValue
        self.viewIndex2EncoderMirrorMode[freeViewIndex] = mirrorValue
        self.viewIndex2BrightnessCorrection[freeViewIndex] = False
        self.uid2MuteAudio[uid] = False
        self.uid2MuteVideo[uid] = False
        self.viewUsingIndex.add(freeViewIndex)

    def onUserOffline(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        if self.rtcEngine is None:
            return
        uid = jsInfo['uid']
        suid = f'{uid}'
        for i in range(self.remoteUidCombox.count()):
            if suid == self.remoteUidCombox.itemText(i):
                self.remoteUidCombox.removeItem(i)
                break
        if not self.checkAutoSetupRemoteVideoNullView.isChecked():
            agsdk.log.warn(f'uid {uid} Offline, but do not setupRemoteVideo null view for he/she, AutoResetRemoteVideo is not checked')
            return
        self.rtcEngine.setupRemoteVideo(videoCanvas=agsdk.VideoCanvas(uid=uid, view=0))
        if uid in self.uid2ViewIndex:
            index = self.uid2ViewIndex.pop(uid)
            if index in self.viewUsingIndex:
                self.videoLabels[index].setText('Remote')
                self.viewUsingIndex.remove(index)
                self.clearViews([index])
            if index in self.viewIndex2RenderMode:
                self.viewIndex2RenderMode.pop(index)
            if index in self.viewIndex2RenderMirrorMode:
                self.viewIndex2RenderMirrorMode.pop(index)
            if index in self.viewIndex2BrightnessCorrection:
                self.viewIndex2BrightnessCorrection.pop(index)
            if index in self.viewIndex2EncoderMirrorMode:
                self.viewIndex2EncoderMirrorMode.pop(index)
        if uid in self.uid2MuteAudio:
            pass
        if uid in self.uid2MuteVideo:
            # the mute state is kept after leaveChannel
            # self.uid2MuteVideo.pop(uid)
            pass

    def onFirstLocalVideoFrame(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onFirstLocalVideoFramePublished(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onFirstRemoteVideoDecoded(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass
        #uid = jsInfo['uid']
        #self.rtcEngine.enableRemoteTrapezoidCorrection(uid, True)

    def onLocalVideoStateChanged(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onRemoteVideoStateChanged(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onVideoSizeChanged(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onActionCopyUid(self) -> None:
        # for uid, index in self.uid2ViewIndex.items():
            # if index == self.menuShowVideoLableIndex:
                # break
        # else:
            # return
        strUid = self.copyUidAction.text().split()[-1]
        QApplication.clipboard().setText(strUid)

    def onActionCopyViewHandle(self) -> None:
        strViewHandle = self.copyViewAction.text().split()[-1]
        QApplication.clipboard().setText(strViewHandle)

    def onActionRenderMode(self) -> None:
        if not self.rtcEngine:
            return
        action = self.sender()
        for it in agsdk.RenderMode:
            if action.text() == it.name:
                break
        renderMode = it.value
        if self.menuShowVideoLableIndex in [0, 1]:
            if self.menuShowVideoLableIndex in self.viewIndex2RenderMode:
                sourceType = agsdk.VideoSourceType(self.menuShowVideoLableIndex)  # trick
                mirrorValue = self.viewIndex2RenderMirrorMode[self.menuShowVideoLableIndex]
                ret = self.rtcEngine.setLocalRenderMode(renderMode, mirrorValue, sourceType)
                self.checkSDKResult(ret)
                self.viewIndex2RenderMode[self.menuShowVideoLableIndex] = renderMode
        else:
            for uid, vindex in self.uid2ViewIndex.items():
                if vindex == self.menuShowVideoLableIndex:
                    break
            else:
                return
            mirrorValue = self.viewIndex2RenderMirrorMode[vindex]
            ret = self.rtcEngine.setRemoteRenderMode(uid, renderMode, mirrorValue)
            self.checkSDKResult(ret)
            self.viewIndex2RenderMode[vindex] = renderMode

    def onActionRenderMirror(self) -> None:
        if not self.rtcEngine:
            return
        enabled = self.renderMirrorAction.isChecked()  # after click, the state have toggled when action is triggered
        mirrorValue = agsdk.VideoMirrorMode.Enabled if enabled else agsdk.VideoMirrorMode.Disabled
        if self.menuShowVideoLableIndex in [0, 1]:
            if self.menuShowVideoLableIndex in self.viewIndex2RenderMirrorMode:
                sourceType = agsdk.VideoSourceType(self.menuShowVideoLableIndex)  # trick
                #viewHandle = int(self.videoLabels[0].winId())
                #canvas = agsdk.VideoCanvas(uid=0, view=viewHandle, mirrorMode=mirrorValue)
                #ret = self.rtcEngine.setupLocalVideo(canvas)
                renderMode = self.viewIndex2RenderMode[self.menuShowVideoLableIndex]
                ret = self.rtcEngine.setLocalRenderMode(renderMode, mirrorValue, sourceType)
                self.checkSDKResult(ret)
                self.viewIndex2RenderMirrorMode[self.menuShowVideoLableIndex] = mirrorValue
        else:
            for uid, vindex in self.uid2ViewIndex.items():
                if vindex == self.menuShowVideoLableIndex:
                    break
            else:
                return
            #viewHandle = int(self.videoLabels[self.menuShowVideoLableIndex].winId())
            #ret = self.rtcEngine.setupRemoteVideo(videoCanvas=agsdk.VideoCanvas(uid=uid, view=viewHandle, mirrorMode=mirrorValue))
            renderMode = self.viewIndex2RenderMode[vindex]
            ret = self.rtcEngine.setRemoteRenderMode(uid, renderMode, mirrorValue)
            self.checkSDKResult(ret)
            self.viewIndex2RenderMirrorMode[self.menuShowVideoLableIndex] = mirrorValue

    def onActionEncoderMirror(self) -> None:
        if not self.rtcEngine:
            return
        enabled = self.encoderMirrorAction.isChecked()  # after click, the state have toggled when action is triggered
        mirrorValue = agsdk.VideoMirrorMode.Enabled if enabled else agsdk.VideoMirrorMode.Disabled
        if self.menuShowVideoLableIndex == 0:
            self.videoConfig.mirrorMode = mirrorValue
            ret = self.rtcEngine.setVideoEncoderConfiguration(self.videoConfig)
            self.viewIndex2EncoderMirrorMode[0] = mirrorValue
            self.checkSDKResult(ret)
        elif self.menuShowVideoLableIndex == 1:
            self.videoConfigEx.mirrorMode = mirrorValue
            ret = self.rtcEngine.setVideoEncoderConfigurationEx(self.videoConfigEx, self.rtcConnection)
            self.viewIndex2EncoderMirrorMode[1] = mirrorValue
            self.checkSDKResult(ret)
        else:
            for uid, vindex in self.uid2ViewIndex.items():
                if vindex == self.menuShowVideoLableIndex:
                    break
            else:
                return
            ret = self.rtcEngine.applyVideoEncoderMirrorToRemote(uid, mirrorValue)
            self.viewIndex2EncoderMirrorMode[self.menuShowVideoLableIndex] = mirrorValue
            self.checkSDKResult(ret)

    def onActionBrightnessCorrection(self) -> None:
        if not self.rtcEngine:
            return
        enabled = self.brightnessCorrectionAction.isChecked()  # after click, the state have toggled when action is triggered
        if self.menuShowVideoLableIndex == 0 or self.menuShowVideoLableIndex == 1:
            if self.menuShowVideoLableIndex in self.viewIndex2BrightnessCorrection:
                sourceType = agsdk.VideoSourceType(self.menuShowVideoLableIndex)  # trick
                ret = self.rtcEngine.enableBrightnessCorrection(enabled, self.defaultBrightnessCorrectionMode, sourceType)
                self.viewIndex2BrightnessCorrection[self.menuShowVideoLableIndex] = enabled
                self.checkSDKResult(ret)
        else:
            for uid, vindex in self.uid2ViewIndex.items():
                if vindex == self.menuShowVideoLableIndex:
                    break
            else:
                return
            ret = self.rtcEngine.applyBrightnessCorrectionToRemote(uid, enabled, self.defaultBrightnessCorrectionMode)
            self.viewIndex2BrightnessCorrection[self.menuShowVideoLableIndex] = enabled
            self.checkSDKResult(ret)

    def onActionMuteAudio(self) -> None:
        if not self.rtcEngine:
            return
        muteValue = self.muteAudioAction.isChecked()  # after click, the state have toggled when action is triggered
        if self.menuShowVideoLableIndex == 0:
            if 0 in self.uid2MuteAudio:
                ret = self.rtcEngine.muteLocalAudioStream(muteValue)
                self.uid2MuteAudio[0] = muteValue
                self.checkSDKResult(ret)
        else:
            for uid, vindex in self.uid2ViewIndex.items():
                if vindex == self.menuShowVideoLableIndex:
                    break
            else:
                return
            ret = self.rtcEngine.muteRemoteAudioStream(uid, muteValue)
            self.uid2MuteAudio[uid] = muteValue
            self.checkSDKResult(ret)

    def onActionMuteVideo(self) -> None:
        if not self.rtcEngine:
            return
        muteValue = self.muteVideoAction.isChecked()  # after click, the state have toggled when action is triggered
        if self.menuShowVideoLableIndex == 0:
            if 0 in self.uid2MuteVideo:
                ret = self.rtcEngine.muteLocalVideoStream(muteValue)
                self.uid2MuteVideo[0] = muteValue
                self.checkSDKResult(ret)
        else:
            for uid, vindex in self.uid2ViewIndex.items():
                if vindex == self.menuShowVideoLableIndex:
                    break
            else:
                return
            ret = self.rtcEngine.muteRemoteVideoStream(uid, muteValue)
            self.uid2MuteVideo[uid] = muteValue
            self.checkSDKResult(ret)

    def onStreamMessage(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        self.dataStreamDlg.appendMessage(jsInfo['uid'], jsInfo['data'])
        if self.dataStreamDlg.isVisible():
            return
        self.onClickDataStreamTest()

    def onStreamMessageError(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onTrapezoidAutoCorrectionFinished(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onSnapshotTaken(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def onServerSuperResolutionResult(self, userData: str, callbackTimeSinceEpoch: int, funcName: str, jsStr: str, jsInfo: Dict) -> None:
        pass

    def testFunc(self) -> None:
        channelName = 'ykstest2'
        uid1 = 1000
        uid2 = 1001
        uid3 = 1003
        token = ''
        info = ''

        if self.rtcEngine is None:
            self.rtcEngine = agsdk.RtcEngine()
        version, build = self.rtcEngine.getVersion()
        self.setWindowTitle(f'{DemoTile} Version={version}, Build={build}, SdkDir={agsdk.agorasdk.SdkBinDir}')
        appName = self.configJson['appNameList'][self.appNameComBox.currentIndex()]['appName']
        appId = self.configJson['appNameList'][self.appNameComBox.currentIndex()]['appId']
        if appId == '00000000000000000000000000000000':
            QMessageBox.warning(None, 'Error', f'You need to set a valid AppId in the config file:\n{self.configPath}')
            return
        elif appName.startswith('Agora'):
            appId = transformAppId(appId)
        self.appId = appId
        context = agsdk.RtcEngineContext(appId)
        context.channelProfile = agsdk.ChannelProfile.LiveBroadcasting
        context.logConfig.logPath = os.path.join(agsdk.LogDir, 'AgoraSdk_log.log')
        ret = self.rtcEngine.initalize(context, self.onRtcEngineCallbackInThread)
        self.checkSDKResult(ret)
        if ret != 0:
            return
        self.inited = True

        ret = self.rtcEngine.setClientRole(agsdk.ClientRole.Broadcaster)
        self.checkSDKResult(ret)
        if ret != 0:
            return

        ret = self.rtcEngine.enableVideo()
        self.checkSDKResult(ret)
        if ret != 0:
            return

        devices = self.rtcEngine.enumerateVideoDevices()

        if len(devices) < 2:
            print('video devices count < 2')
            return
        # primary camera
        uid = uid1
        viewIndex = 0

        sourceType = agsdk.VideoSourceType.CameraPrimary
        videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
        videoCanvas.view = int(self.videoLabels[viewIndex].winId())
        videoCanvas.sourceType = sourceType
        videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
        videoCanvas.renderMode = agsdk.RenderMode.Fit
        videoCanvas.isScreenView = False
        if agsdk.agorasdk.SdkVerson >= '3.8.200':
            videoCanvas.setupMode = agsdk.ViewSetupMode.Add
        self.rtcEngine.setupLocalVideo(videoCanvas)
        self.checkSDKResult(ret)

        # for deviceName, deviceId in devices:
            # pass
        deviceId = devices[0][1]
        cameraConfig = agsdk.CameraCapturerConfiguration()
        cameraConfig.deviceId = deviceId
        cameraConfig.width = 640
        cameraConfig.height = 360
        cameraConfig.frameRate = 15
        ret = self.rtcEngine.startPrimaryCameraCapture(cameraConfig)
        self.checkSDKResult(ret)

        self.rtcEngine.startPreview(sourceType)
        self.checkSDKResult(ret)

        self.channelName = channelName
        uid = uid1

        ret = self.rtcEngine.joinChannel(channelName, uid, token, info)

        #options = agsdk.ChannelMediaOptions()
        #options.autoSubscribeAudio = True
        #options.autoSubscribeVideo = True
        #options.publishAudioTrack = True
        #options.publishCameraTrack = True
        #self.channelOptions = options
        #ret = self.rtcEngine.joinChannelWithOptions(channelName, uid, token, options)

        self.joined = True
        self.localUids.append(uid)
        self.viewUsingIndex.add(viewIndex)
        if 0 not in self.viewIndex2EncoderMirrorMode:
            self.viewIndex2EncoderMirrorMode[viewIndex] = videoCanvas.mirrorMode

        # second camera
        uid = uid2
        token = ''
        viewIndex += 1

        sourceType = agsdk.VideoSourceType.CameraSecondary
        videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
        videoCanvas.view = int(self.videoLabels[viewIndex].winId())
        videoCanvas.sourceType = sourceType
        videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
        videoCanvas.renderMode = agsdk.RenderMode.Fit
        videoCanvas.isScreenView = False
        if agsdk.agorasdk.SdkVerson >= '3.8.200':
            videoCanvas.setupMode = agsdk.ViewSetupMode.Add
        self.rtcEngine.setupLocalVideo(videoCanvas)
        self.checkSDKResult(ret)

        # for deviceName, deviceId in devices:
            # pass
        deviceId = devices[1][1]
        cameraConfig = agsdk.CameraCapturerConfiguration()
        cameraConfig.deviceId = deviceId
        cameraConfig.width = 640
        cameraConfig.height = 360
        cameraConfig.frameRate = 15
        ret = self.rtcEngine.startSecondaryCameraCapture(cameraConfig)
        self.checkSDKResult(ret)

        self.rtcEngine.startPreview(sourceType)
        self.checkSDKResult(ret)

        options = agsdk.ChannelMediaOptions()
        options.autoSubscribeAudio = False
        options.autoSubscribeVideo = False
        options.publishAudioTrack = False
        options.publishCameraTrack = False
        options.publishSecondaryCameraTrack = True

        self.channelNameEx = channelName
        self.channelExOptions = options
        self.rtcConnection = agsdk.RtcConnection(channelName, uid)
        ret = self.rtcEngine.joinChannelEx(self.rtcConnection, token, options)
        self.checkSDKResult(ret)

        self.localUids.append(uid)
        self.viewUsingIndex.add(viewIndex)
        if 0 not in self.viewIndex2EncoderMirrorMode:
            self.viewIndex2EncoderMirrorMode[viewIndex] = videoCanvas.mirrorMode

        # first screen share
        uid = uid3
        token = ''
        viewIndex += 1
        screenRect = agsdk.Rectangle(0, 0, 1920, 1080)
        regionRect = agsdk.Rectangle(0, 0, 0, 0)
        excludeWindows = []
        captureParams = agsdk.ScreenCaptureParameters(screenRect.width, screenRect.height, fps=15, bitrate=0, excludeWindowList=excludeWindows)
        ret = self.rtcEngine.startPrimaryScreenCapture(screenRect, regionRect, captureParams)
        self.checkSDKResult(ret)

        sourceType = agsdk.VideoSourceType.Screen
        videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
        videoCanvas.view = int(self.videoLabels[viewIndex].winId())
        videoCanvas.sourceType = sourceType
        videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
        videoCanvas.renderMode = agsdk.RenderMode.Fit
        videoCanvas.isScreenView = False
        videoCanvas.isScreenView = False
        if agsdk.agorasdk.SdkVerson >= '3.8.200':
            videoCanvas.setupMode = agsdk.ViewSetupMode.Add
        self.rtcEngine.setupLocalVideo(videoCanvas)
        self.checkSDKResult(ret)

        self.rtcEngine.startPreview(sourceType)
        self.checkSDKResult(ret)

        #self.channelNameEx = channelName

        options = agsdk.ChannelMediaOptions()
        options.autoSubscribeAudio = False
        options.autoSubscribeVideo = False
        options.publishAudioTrack = False
        options.publishCameraTrack = False
        options.publishScreenTrack = True

        self.channelExOptions = options
        self.rtcConnection = agsdk.RtcConnection(channelName, uid)
        ret = self.rtcEngine.joinChannelEx(self.rtcConnection, token, options)
        self.checkSDKResult(ret)

        self.localUids.append(uid)
        self.viewUsingIndex.add(viewIndex)


# def IsUserAnAdmin() -> bool:
    # return bool(ctypes.windll.shell32.IsUserAnAdmin())


# def RunScriptAsAdmin(argv: List[str], workingDirectory: str = None, showFlag: int = 1) -> bool:
    #args = ' '.join('"{}"'.format(arg) for arg in argv)
    # return ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, workingDirectory, showFlag) > 32

def _adjustPos(win: MainWindow):
    if sys.platform == 'win32':
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            desktopRect = QDesktopWidget().availableGeometry()
            selfRect = win.frameGeometry()
            selfTopLeft = selfRect.topLeft()
            selfTopLeft.setY(selfTopLeft.y() // 2)
            win.move(selfTopLeft)
            selfRect.moveTopLeft(selfTopLeft)
            cmdX = selfRect.left() - 100
            if cmdX < 0:
                cmdX = 0
            cmdY = selfRect.top() + selfRect.height()
            cmdWidth = selfRect.width()
            cmdHeight = desktopRect.height() - cmdY
            if cmdHeight < 200:
                cmdY -= 200 - cmdHeight
                cmdHeight = 200
            ctypes.windll.user32.SetWindowPos(hwnd, 0, cmdX, cmdY, cmdWidth, cmdHeight, 4)


def _start():
    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(ctypes.c_wchar_p(
            f'{DemoTile} 不要在命令行界面上点击，否则会使UI线程卡住, ConsoleLog: agsdklog\AgoraSdk_py.log, SDKLog: agsdklog\AgoraSdk_log.log'))
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    _adjustPos(win)
    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        _start()
    except Exception as ex:
        print(traceback.format_exc())
        input('\nSomething wrong. Please input Enter to exit.')
    sys.exit(0)
    # if sys.platform == 'win32':
        # if IsUserAnAdmin():
            # _start()
        # else:
            #print('not admin, now run as admin')
            # RunScriptAsAdmin(sys.argv)

