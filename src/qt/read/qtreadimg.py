import weakref
import waifu2x
from PySide2 import QtWidgets
from PySide2.QtCore import Qt, QRectF, QPointF, QSizeF, QEvent, QSize, QMimeData
from PySide2.QtGui import QPixmap, QPainter, QColor, QImage
from PySide2.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QApplication, QFrame, QVBoxLayout, QLabel

from conf import config
from src.index.book import BookMgr
from src.qt.com.qtbubblelabel import QtBubbleLabel
from src.qt.com.qtloading import QtLoading
from src.qt.util.qttask import QtTask
from src.qt.struct.qt_define import QtFileData
from src.util import ToolUtil, Log
from src.util.status import Status
from src.util.tool import CTime
from ui.readimg import Ui_ReadImg


class QtImgTool(QtWidgets.QWidget, Ui_ReadImg):

    def __init__(self, parent, *args, **kwargs):
        super(QtImgTool, self).__init__(*args, **kwargs)
        Ui_ReadImg.__init__(self)
        self.setupUi(self)
        self.resize(100, 300)
        self.parent = weakref.ref(parent)
        self.setWindowFlags(
            Qt.Window | Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.X11BypassWindowManagerHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 16)
        layout.addWidget(QLabel("test"))
        self.radioButton.installEventFilter(self)
        self.radioButton_2.installEventFilter(self)

    @property
    def graphicsItem(self):
        return self.parent().graphicsItem

    @property
    def curIndex(self):
        return self.parent().curIndex

    @curIndex.setter
    def curIndex(self, value):
        self.parent().curIndex = value

    @property
    def maxPic(self):
        return self.parent().maxPic

    @property
    def isStripModel(self):
        return self.parent().isStripModel

    @isStripModel.setter
    def isStripModel(self, value):
        self.parent().isStripModel = value

    def Show(self, size):
        self.show()

    def Close(self, size):
        self.show()

    @property
    def qtTool(self):
        return self.parent().qtTool

    @property
    def scaleCnt(self):
        return self.parent().scaleCnt

    @scaleCnt.setter
    def scaleCnt(self, value):
        self.parent().scaleCnt = value

    def NextPage(self):
        if self.curIndex >= self.maxPic-1:
            QtBubbleLabel.ShowMsgEx(self.parent(), "已经最后一页")
            return
        t = CTime()
        self.curIndex += 1
        self.SetData(isInit=True)
        self.parent().ShowImg()
        t.Refresh(self.__class__.__name__)
        return

    def LastPage(self):
        if self.curIndex <= 0:
            QtBubbleLabel.ShowMsgEx(self.parent(), "已经是第一页")
            return
        self.curIndex -= 1
        self.SetData(isInit=True)
        self.parent().ShowImg()
        return

    def SwitchPicture(self):
        if self.radioButton.isChecked():
            self.isStripModel = False
        else:
            self.isStripModel = True
        self.graphicsItem.setPos(0, 0)
        self.scaleCnt = 0
        self.parent().ScalePicture()

    def ReturnPage(self):
        self.parent().hide()
        self.hide()
        self.parent().owner().bookInfoForm.show()
        self.parent().AddHistory()
        self.parent().owner().bookInfoForm.LoadHistory()
        self.parent().Clear()
        return

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress:
            return True
        else:
            return super(self.__class__, self).eventFilter(obj, ev)

    def SetData(self, pSize=None, dataLen=0, state="", waifuSize=None, waifuDataLen=0, waifuState="", waifuTick=0, isInit=False):
        self.epsLabel.setText("位置：{}/{}".format(self.parent().curIndex+1, self.parent().maxPic))
        if pSize or isInit:
            if not pSize:
                pSize = QSize(0, 0)
            self.resolutionLabel.setText("分辨率：{}x{}".format(str(pSize.width()), str(pSize.height())))

        if dataLen or isInit:
            self.sizeLabel.setText("大小: " + ToolUtil.GetDownloadSize(dataLen))

        if waifuSize or isInit:
            if not waifuSize:
                waifuSize = QSize(0, 0)
            self.resolutionWaifu.setText("分辨率：{}x{}".format(str(waifuSize.width()), str(waifuSize.height())))
        if waifuDataLen or isInit:
            self.sizeWaifu.setText("大小：" + ToolUtil.GetDownloadSize(waifuDataLen))

        if state or isInit:
            self.stateLable.setText("状态：" + state)

        if waifuState or isInit:
            self.stateWaifu.setText("状态：" + waifuState)
        if waifuTick or isInit:
            self.tickLabel.setText("耗时：" + str(waifuTick) + "s")

    def CopyPicture(self):
        clipboard = QApplication.clipboard()
        owner = self.parent()

        if self.checkBox.isChecked():
            p = owner.pictureData.get(owner.curIndex)
            if not p or not p.waifuData:
                QtBubbleLabel.ShowErrorEx(owner, "解码还未完成")
                return
            img = QImage()
            img.loadFromData(p.waifuData)
            clipboard.setImage(img)
            QtBubbleLabel.ShowMsgEx(owner, "复制成功")

        else:
            p = owner.pictureData.get(owner.curIndex)
            if not p or not p.data:
                QtBubbleLabel.ShowErrorEx(owner, "下载未完成")
                return
            img = QImage()
            img.loadFromData(p.data)
            clipboard.setImage(img)
            QtBubbleLabel.ShowMsgEx(owner, "复制成功")
        return

    def OpenWaifu(self):
        if self.checkBox.isChecked():
            config.IsOpenWaifu = True
            self.parent().ShowImg(True)
        else:
            config.IsOpenWaifu = False
            self.parent().ShowImg(False)

        return


class QtReadImg(QtWidgets.QWidget):
    def __init__(self, owner):
        super(self.__class__, self).__init__()
        self.owner = weakref.ref(owner)
        self.resize(800, 800)
        self.loadingForm = QtLoading(self)
        self.bookId = ""
        self.epsId = 0
        self.resetCnt = config.ResetCnt
        self.curIndex = 0

        self.pictureData = {}
        self.waitPicData = set()
        self.maxPic = 0

        self.curPreLoadIndex = 0
        self.maxPreLoad = config.PreLoading

        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.qtTool = QtImgTool(self)

        self.graphicsView = QtWidgets.QGraphicsView(self)
        self.graphicsView.setTransformationAnchor(self.graphicsView.AnchorUnderMouse)
        self.graphicsView.setResizeAnchor(self.graphicsView.AnchorUnderMouse)
        self.graphicsView.setFrameStyle(QFrame.NoFrame)
        self.graphicsView.setObjectName("graphicsView")

        self.gridLayout.addWidget(self.graphicsView, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.qtTool, 0, 1)

        self.graphicsView.setBackgroundBrush(QColor(Qt.white))
        self.graphicsView.setCursor(Qt.OpenHandCursor)
        self.graphicsView.setResizeAnchor(self.graphicsView.AnchorViewCenter)
        self.graphicsView.setTransformationAnchor(self.graphicsView.AnchorViewCenter)

        self.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView.setRenderHints(QPainter.Antialiasing | QPainter.HighQualityAntialiasing |
                            QPainter.SmoothPixmapTransform)
        self.graphicsView.setCacheMode(self.graphicsView.CacheBackground)
        self.graphicsView.setViewportUpdateMode(self.graphicsView.SmartViewportUpdate)

        self.graphicsItem = QGraphicsPixmapItem()
        self.graphicsItem.setFlags(QGraphicsPixmapItem.ItemIsFocusable |
                                   QGraphicsPixmapItem.ItemIsMovable)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.ShowAndCloseTool)

        self.graphicsScene = QGraphicsScene(self)  # 场景
        self.graphicsView.setScene(self.graphicsScene)
        self.graphicsScene.addItem(self.graphicsItem)
        rect = QApplication.instance().desktop().availableGeometry(self)
        self.graphicsView.setMinimumSize(10, 10)
        self.pixMap = QPixmap()
        self.graphicsItem.setPixmap(self.pixMap)
        self.scaleCnt = 0

        self.isStripModel = False

        self.graphicsView.installEventFilter(self)
        # self.resize(1200, 1080)
        self.closeFlag = self.__class__.__name__   # 防止切换时异步加载图片错位

        # self.timer = QTimer(self)
        # self.timer.setInterval(100)
        self.waifu2xIdToIndex = {}
        self.indexToWaifu2xId = {}
        self.waitWaifuPicData = set()
        # self.timer.timeout.connect(self.LoadWaifu2x)
        # self.timer.start()
        self.graphicsView.setWindowFlag(Qt.FramelessWindowHint)

    def closeEvent(self, a0) -> None:
        self.ReturnPage()
        self.owner().bookInfoForm.show()
        self.Clear()
        a0.accept()

    def Clear(self):
        self.qtTool.label_2.setText("去噪等级：" + str(config.Noise))
        self.qtTool.label_3.setText("放大倍数：" + str(config.Scale))
        self.qtTool.label_9.setText("转码模式：" + self.owner().settingForm.GetGpuName())
        self.bookId = ""
        self.epsId = 0
        self.maxPic = 0
        self.curIndex = 0
        self.curPreLoadIndex = 0
        self.scaleCnt = 0
        self.pictureData.clear()
        self.waifu2xIdToIndex.clear()
        self.indexToWaifu2xId.clear()
        self.waitWaifuPicData.clear()
        self.waitPicData.clear()
        QtTask().CancelTasks(self.closeFlag)
        QtTask().CancelConver(self.closeFlag)

    def OpenPage(self, bookId, epsId, name):
        if not bookId:
            return
        self.Clear()
        self.qtTool.checkBox.setChecked(config.IsOpenWaifu)
        self.qtTool.SetData(isInit=True)
        self.pixMap.convertFromImage(QImage("加载中"))
        self.graphicsItem.setPixmap(self.pixMap)
        self.qtTool.SetData()
        self.qtTool.show()
        self.bookId = bookId
        self.epsId = epsId
        self.graphicsItem.setPos(0, 0)

        # historyInfo = self.owner().historyForm.GetHistory(bookId)
        # if historyInfo and historyInfo.epsId == epsId:
        #     self.curIndex = historyInfo.picIndex
        # else:
        #     self.AddHistory()
        # self.AddHistory()

        self.loadingForm.show()
        self.StartLoadPicUrl()
        self.setWindowTitle(name)
        self.show()

    def ReturnPage(self):
        self.AddHistory()
        self.owner().bookInfoForm.LoadHistory()
        return

    def RevertPicture(self):
        self.graphicsItem.setPos(0, 0)
        self.scaleCnt = 0
        self.ScalePicture()

    def StartLoadPicUrl(self):
        QtTask().AddHttpTask(lambda x: BookMgr().AddBookEpsPicInfo(self.bookId, self.epsId+1, x),
                                        self.StartLoadPicUrlBack,
                                        self.bookId, cleanFlag=self.closeFlag)

    def CheckLoadPicture(self):
        i = 0
        for i in range(self.curIndex, self.curIndex + self.maxPreLoad):
            if i >= self.maxPic:
                continue
            if i < self.curPreLoadIndex:
                continue

            bookInfo = BookMgr().books.get(self.bookId)
            epsInfo = bookInfo.eps[self.epsId]
            picInfo = epsInfo.pics[i]
            if i not in self.pictureData:
                # 防止重复请求
                if i not in self.waitPicData:
                    self.AddDownloadTask(i, picInfo)
            elif config.IsOpenWaifu and i not in self.waitWaifuPicData:
                if not self.pictureData[i].waifuData:
                    self.AddCovertData(picInfo, i)
        self.curPreLoadIndex = max(i, self.curPreLoadIndex)
        pass

    def StartLoadPicUrlBack(self, msg, bookId):
        if msg != Status.Ok:
            self.StartLoadPicUrl()
        else:
            bookInfo = BookMgr().books.get(self.bookId)
            epsInfo = bookInfo.eps[self.epsId]
            self.maxPic = len(epsInfo.pics)
            self.CheckLoadPicture()
        return

    def CompleteDownloadPic(self, data, st, index):
        self.loadingForm.close()
        p = QtFileData()
        bookInfo = BookMgr().books.get(self.bookId)
        epsInfo = bookInfo.eps[self.epsId]
        picInfo = epsInfo.pics[index]
        self.waitPicData.discard(index)
        if st != Status.Ok:
            p.state = p.DownloadReset
            self.AddDownloadTask(index, picInfo)
        else:
            p.SetData(data)
            self.pictureData[index] = p
            if config.IsOpenWaifu:
                self.AddCovertData(picInfo, index)
            if index == self.curIndex:
                self.ShowImg()
            return

    def ShowImg(self, isShowWaifu=True):
        p = self.pictureData.get(self.curIndex)

        if not p or (not p.data):
            self.qtTool.SetData(state=QtFileData.Downloading)
            self.pixMap = QPixmap()
            self.pixMap.convertFromImage(QImage())
            self.graphicsItem.setPixmap(self.pixMap)
            return

        assert isinstance(p, QtFileData)
        if not isShowWaifu:
            p2 = p.data
            self.qtTool.SetData(waifuSize=QSize(0, 0), waifuDataLen=0)
        elif p.waifuData:
            p2 = p.waifuData
            self.qtTool.SetData(waifuSize=p.waifuQSize, waifuDataLen=p.waifuDataSize,
                                waifuTick=p.waifuTick)
        else:
            p2 = p.data

        self.qtTool.SetData(pSize=p.qSize, dataLen=p.size, state=p.state, waifuState=p.waifuState)
        self.qtTool.label_2.setText("去噪等级：" + str(p.noise))
        self.qtTool.label_3.setText("放大倍数：" + str(p.scale))

        self.pixMap = QPixmap()
        if config.IsLoadingPicture:
            self.pixMap.loadFromData(p2)
        self.graphicsItem.setPixmap(self.pixMap)
        self.graphicsView.setSceneRect(QRectF(QPointF(0, 0), QPointF(self.pixMap.width(), self.pixMap.height())))
        self.ScalePicture()
        self.CheckLoadPicture()
        return True

    def ScalePicture(self):
        if self.isStripModel:
            self.graphicsItem.setPos(0, 0)
        rect = QRectF(self.graphicsItem.pos(), QSizeF(
                self.pixMap.size()))
        flags = Qt.KeepAspectRatio
        unity = self.graphicsView.transform().mapRect(QRectF(0, 0, 1, 1))
        width = unity.width()
        height = unity.height()
        if width <= 0 or height <= 0:
            return
        self.graphicsView.scale(1 / width, 1 / height)
        viewRect = self.graphicsView.viewport().rect()
        sceneRect = self.graphicsView.transform().mapRect(rect)
        if sceneRect.width() <= 0 or sceneRect.height() <= 0:
            return
        x_ratio = viewRect.width() / sceneRect.width()
        y_ratio = viewRect.height() / sceneRect.height()
        if not self.isStripModel:
            x_ratio = y_ratio = min(x_ratio, y_ratio)
        else:
            x_ratio = y_ratio = max(x_ratio, y_ratio)
            # self.graphicsItem.setPos(p.x(), p.y()+height3)
            # self.graphicsView.move(p.x(), p.y()+height2)
            # self.graphicsView.move(p.x(), p.y()+height3)

        self.graphicsView.scale(x_ratio, y_ratio)
        if self.isStripModel:
            height2 = self.pixMap.size().height() / 2
            height3 = self.graphicsView.size().height()/2
            # height4 = self.graphicsView.geometry().height()/2
            # height5 = self.graphicsView.frameGeometry().height()/2
            height3 = height3/x_ratio
            # pos = height2
            p = self.graphicsItem.pos()
            # self.graphicsItem.setPos(0, 0)
            self.graphicsItem.setPos(p.x(), p.y()+height2-height3)

        self.graphicsView.centerOn(rect.center())
        for _ in range(abs(self.scaleCnt)):
            if self.scaleCnt > 0:
                self.graphicsView.scale(1.1, 1.1)
            else:
                self.graphicsView.scale(1/1.1, 1/1.1)

    def resizeEvent(self, event) -> None:
        super(self.__class__, self).resizeEvent(event)
        self.ScalePicture()

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress:
            return True
        else:
            return super(self.__class__, self).eventFilter(obj, ev)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            else:
                self.zoomOut()
        else:
            if event.angleDelta().y() > 0:
                # self.zoomIn()
                point = self.graphicsItem.pos()
                self.graphicsItem.setPos(point.x(), point.y()+100)
            else:
                # self.zoomOut()
                point = self.graphicsItem.pos()
                self.graphicsItem.setPos(point.x(), point.y()-100)

    def zoomIn(self):
        """放大"""
        self.zoom(1.1)

    def zoomOut(self):
        """缩小"""
        self.zoom(1/1.1)

    def zoom(self, factor):
        """缩放
        :param factor: 缩放的比例因子
        """
        _factor = self.graphicsView.transform().scale(
            factor, factor).mapRect(QRectF(0, 0, 1, 1)).width()
        if _factor < 0.07 or _factor > 100:
            # 防止过大过小
            return
        if factor >= 1:
            self.scaleCnt += 1
        else:
            self.scaleCnt -= 1
        self.graphicsView.scale(factor, factor)

    def keyReleaseEvent(self, ev):
        if ev.key() == Qt.Key_Left:
            self.qtTool.LastPage()
            return
        elif ev.key() == Qt.Key_Right:
            self.qtTool.NextPage()
            return
        elif ev.key() == Qt.Key_Escape:
            self.qtTool.ReturnPage()
            return
        elif ev.key() == Qt.Key_Up:
            point = self.graphicsItem.pos()
            self.graphicsItem.setPos(point.x(), point.y()+50)
            return
        elif ev.key() == Qt.Key_Down:
            point = self.graphicsItem.pos()
            self.graphicsItem.setPos(point.x(), point.y()-50)
            return
        super(self.__class__, self).keyReleaseEvent(ev)

    def AddHistory(self):
        bookName = self.owner().bookInfoForm.bookName
        url = self.owner().bookInfoForm.url
        path = self.owner().bookInfoForm.path
        self.owner().historyForm.AddHistory(self.bookId, bookName, self.epsId, self.curIndex, url, path)
        return

    def ShowAndCloseTool(self):
        if self.qtTool.isHidden():
            self.qtTool.show()
        else:
            self.qtTool.hide()

    def Waifu2xBack(self, data, waifu2xId, index, tick):
        self.waitWaifuPicData.discard(index)
        if waifu2xId > 0:
            self.waifu2xIdToIndex[waifu2xId] = index
            self.indexToWaifu2xId[index] = waifu2xId
        if waifu2xId not in self.waifu2xIdToIndex:
            Log.Error("Not found waifu2xId ：{}, index: {}".format(str(waifu2xId), str(index)))
            return
        p = self.pictureData.get(index)
        p.SetWaifuData(data, round(tick, 2))
        if index == self.curIndex:
            self.ShowImg()

    def AddCovertData(self, picInfo, i):
        info = self.pictureData[i]
        if not info and info.data:
            return
        assert isinstance(info, QtFileData)
        data = info.data

        path = self.owner().downloadForm.GetConvertFilePath(self.bookId, self.epsId, i)
        QtTask().AddConvertTask(picInfo.path, data, info.scale, info.noise, info.format, self.Waifu2xBack, i, self.closeFlag, path)
        self.waitWaifuPicData.add(i)

    def AddDownloadTask(self, i, picInfo):
        path = self.owner().downloadForm.GetDonwloadFilePath(self.bookId, self.epsId, i)
        QtTask().AddDownloadTask(picInfo.fileServer, picInfo.path,
                                 completeCallBack=self.CompleteDownloadPic, backParam=i,
                                 isSaveCache=False, cleanFlag=self.closeFlag, filePath=path)
        self.waitPicData.add(i)
