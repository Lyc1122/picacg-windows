import json

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Qt, QSize, QEvent
from PySide2.QtGui import QColor, QFont, QPixmap, QIcon
from PySide2.QtWidgets import QListWidgetItem, QLabel, QApplication, QHBoxLayout, QLineEdit, QPushButton, \
    QVBoxLayout, QDesktopWidget, QScroller, QAbstractItemView

from conf import config
from qss.qss import QssDataMgr
from resources.resources import DataMgr
from src.index.book import BookMgr
from src.qt.com.qtmsg import QtMsgLabel
from src.qt.com.qtimg import QtImgMgr
from src.qt.com.qtloading import QtLoading
from src.qt.qtmain import QtOwner
from src.qt.util.qttask import QtTaskBase
from src.server import req, Log, ToolUtil
from src.server.sql_server import SqlServer
from src.util.status import Status
from ui.bookinfo import Ui_BookInfo
from ui.qtlistwidget import QtBookList


class QtBookInfo(QtWidgets.QWidget, Ui_BookInfo, QtTaskBase):
    def __init__(self):
        super(self.__class__, self).__init__()
        Ui_BookInfo.__init__(self)
        QtTaskBase.__init__(self)
        self.setupUi(self)
        self.commentWidget.InitReq(req.GetComments, req.SendComment, req.CommentsLikeReq, req.CommentsReportReq)
        self.loadingForm = QtLoading(self)
        self.bookId = ""
        self.url = ""
        self.path = ""
        self.bookName = ""
        self.lastEpsId = -1
        self.lastIndex = 0
        self.pictureData = None
        self.isFavorite = False
        self.isLike = False
        self.tabWidget.setCurrentIndex(0)

        self.msgForm = QtMsgLabel(self)
        self.picture.installEventFilter(self)
        self.title.setWordWrap(True)
        self.title.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.autorList.itemClicked.connect(self.ClickAutorItem)
        self.idLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.description.setTextInteractionFlags(Qt.TextBrowserInteraction)
        # self.description.setWordWrap(True)
        # self.description.setAlignment(Qt.AlignTop)
        p = QPixmap()
        p.loadFromData(DataMgr.GetData("ic_get_app_black_36dp"))
        self.downloadButton.setIcon(QIcon(p))
        self.starButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.starButton.setIconSize(QSize(50, 50))
        self.downloadButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.downloadButton.setIconSize(QSize(50, 50))
        self.favoriteButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.favoriteButton.setIconSize(QSize(50, 50))
        self.starButton.setCursor(Qt.PointingHandCursor)
        self.downloadButton.setCursor(Qt.PointingHandCursor)
        self.favoriteButton.setCursor(Qt.PointingHandCursor)
        self.description.adjustSize()
        self.title.adjustSize()

        self.categoriesList.itemClicked.connect(self.ClickCategoriesItem)

        self.tagsList.itemClicked.connect(self.ClickTagsItem)

        self.epsListWidget.setFlow(self.epsListWidget.LeftToRight)
        self.epsListWidget.setWrapping(True)
        self.epsListWidget.setFrameShape(self.epsListWidget.NoFrame)
        self.epsListWidget.setResizeMode(self.epsListWidget.Adjust)

        self.epsListWidget.clicked.connect(self.OpenReadImg)

        ToolUtil.SetIcon(self)
        desktop = QDesktopWidget()
        self.resize(desktop.width()//4*1, desktop.height()//4*3)
        self.move(desktop.width()//8*3, desktop.height()//8*1)

        QScroller.grabGesture(self.epsListWidget, QScroller.LeftMouseButtonGesture)
        self.epsListWidget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.epsListWidget.verticalScrollBar().setStyleSheet(QssDataMgr().GetData('qt_list_scrollbar'))
        self.epsListWidget.verticalScrollBar().setSingleStep(30)
        self.user_name.setCursor(Qt.PointingHandCursor)
        self.user_icon.setCursor(Qt.PointingHandCursor)
        self.user_name.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.user_icon.radius = 50
        self.userIconData = None
        self.user_name.installEventFilter(self)
        self.user_icon.installEventFilter(self)

    def UpdateFavoriteIcon(self):
        p = QPixmap()
        if self.isFavorite:
            p.loadFromData(DataMgr.GetData("icon_like"))
        else:
            p.loadFromData(DataMgr.GetData("icon_like_off"))
        self.favoriteButton.setIcon(QIcon(p.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)))

    def UpdateLikeIcon(self):
        p = QPixmap()
        if self.isLike:
            p.loadFromData(DataMgr.GetData("icon_bookmark_on"))
        else:
            p.loadFromData(DataMgr.GetData("icon_bookmark_off"))
        self.starButton.setIcon(QIcon(p.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)))

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.stackedWidget.currentIndex() == 1:
            self.stackedWidget.setCurrentIndex(0)
            QtOwner().owner.qtReadImg.AddHistory()
            self.LoadHistory()
            a0.ignore()
        else:
            a0.accept()

    def Clear(self):
        self.stackedWidget.setCurrentIndex(0)
        self.ClearTask()
        self.epsListWidget.clear()
        self.commentWidget.ClearCommnetList()

    def OpenBook(self, bookId):
        self.bookId = bookId
        self.setWindowTitle(self.bookId)
        self.setFocus()
        self.Clear()
        self.show()
        self.loadingForm.show()
        self.tabWidget.setCurrentIndex(0)
        self.OpenLocalBack()

    def OpenLocalBack(self):
        self.AddSqlTask("book", self.bookId, SqlServer.TaskTypeCacheBook, callBack=self.SendLocalBack)

    def SendLocalBack(self, books):
        self.AddHttpTask(req.GetComicsBookReq(self.bookId), self.OpenBookBack)

    def OpenBookBack(self, msg):
        self.loadingForm.close()
        self.categoriesList.clear()
        self.tagsList.clear()
        self.autorList.clear()
        info = BookMgr().books.get(self.bookId)
        if info:
            self.autorList.AddItem(info.author)
            if hasattr(info, "chineseTeam"):
                self.autorList.AddItem(info.chineseTeam)
            title = info.title
            if info.pagesCount:
                title += "<font color=#d5577c>{}</font>".format("(" + str(info.pagesCount) + "P)")
            if info.finished:
                title += "<font color=#d5577c>{}</font>".format("(完)")
            self.title.setText(title)
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            self.title.setFont(font)
            self.idLabel.setText(info.id)

            self.bookName = info.title
            self.description.setPlainText(info.description)

            for name in info.categories:
                self.categoriesList.AddItem(name)
            for name in info.tags:
                self.tagsList.AddItem(name)
            self.starButton.setText(str(info.totalLikes))
            self.views.setText(str(info.totalViews))
            self.isFavorite = info.isFavourite
            self.isLike = info.isLiked
            self.UpdateFavoriteIcon()
            self.UpdateLikeIcon()
            self.picture.setText(self.tr("图片加载中..."))
            self.tabWidget.setTabText(1, self.tr("评论") + "({})".format(str(info.commentsCount)))
            fileServer = info.thumb.get("fileServer")
            path = info.thumb.get("path")
            name = info.thumb.get("originalName")
            self.url = fileServer
            self.path = path
            dayStr = ToolUtil.GetUpdateStr(info.updated_at)
            self.updateTick.setText(str(dayStr) + self.tr("更新"))
            if config.IsLoadingPicture:
                self.AddDownloadTask(fileServer, path, completeCallBack=self.UpdatePicture)
            self.commentWidget.bookId = self.bookId

            self.AddHttpTask(req.GetComicsBookEpsReq(self.bookId), self.GetEpsBack)
            self.startRead.setEnabled(False)
            if hasattr(info, "_creator"):
                creator = info._creator
                self.user_name.setText(creator.get("name"))
                url2 = creator.get("avatar").get("fileServer")
                path2 = creator.get("avatar").get("path")
                if url2:
                    self.AddDownloadTask(url2, path2, None, self.LoadingPictureComplete)
        else:
            # QtWidgets.QMessageBox.information(self, '加载失败', msg, QtWidgets.QMessageBox.Yes)
            self.msgForm.ShowError(QtOwner().owner.GetStatusStr(msg))

            self.hide()

        if msg == Status.UnderReviewBook:
            self.msgForm.ShowError(QtOwner().owner.GetStatusStr(msg))

        return

    def LoadingPictureComplete(self, data, status):
        if status == Status.Ok:
            self.userIconData = data
            self.user_icon.SetPicture(data)

    def UpdatePicture(self, data, status):
        if status == Status.Ok:
            self.pictureData = data
            pic = QtGui.QPixmap()
            pic.loadFromData(data)
            newPic = pic.scaled(self.picture.size(), QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.picture.setPixmap(newPic)
            # self.picture.setScaledContents(True)
            self.update()
        else:
            self.picture.setText(self.tr("图片加载失败"))
        return

    def GetEpsBack(self, st):
        if st == Status.Ok:
            self.UpdateEpsData()
            self.lastEpsId = -1
            self.LoadHistory()
            return
        else:
            self.msgForm.ShowError(self.tr("章节加载失败,") + "{}".format(QtOwner().owner.GetStatusStr(st)))
        return

    def UpdateEpsData(self):
        self.epsListWidget.clear()
        info = BookMgr().books.get(self.bookId)
        if not info:
            return
        self.startRead.setEnabled(True)
        downloadIds = QtOwner().owner.downloadForm.GetDownloadCompleteEpsId(self.bookId)
        for index, epsInfo in enumerate(info.eps):
            label = QLabel(str(index+1) + "-" + epsInfo.title)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: rgb(196, 95, 125);")
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            label.setFont(font)
            # label.setWordWrap(True)
            # label.setContentsMargins(20, 10, 20, 10)
            item = QListWidgetItem(self.epsListWidget)
            if index in downloadIds:
                item.setBackground(QColor(18, 161, 130))
            else:
                item.setBackground(QColor(0,0,0,0))
            item.setSizeHint(label.sizeHint() + QSize(20, 20))
            item.setToolTip(epsInfo.title)
            self.epsListWidget.setItemWidget(item, label)
        self.tabWidget.setTabText(0, self.tr("章节") + "({})".format(str(len(info.eps))))
        return

    def AddDownload(self):
        QtOwner().owner.epsInfoForm.OpenEpsInfo(self.bookId)
        # if self.owner().downloadForm.AddDownload(self.bookId):
        #     QtMsgLabel.ShowMsgEx(self, "添加下载成功")
        # else:
        #     QtMsgLabel.ShowMsgEx(self, "已在下载列表")
        # self.download.setEnabled(False)

    def AddBookLike(self):
        self.AddHttpTask(req.BookLikeReq(self.bookId))
        self.isLike = not self.isLike
        if self.isLike:
            self.starButton.setText(str(int(self.starButton.text()) + 1))
        else:
            self.starButton.setText(str(int(self.starButton.text()) - 1))
        self.UpdateLikeIcon()

    def AddFavorite(self):
        self.AddHttpTask(req.FavoritesAdd(self.bookId))
        self.isFavorite = not self.isFavorite
        self.UpdateFavoriteIcon()
        if self.isFavorite:
            QtMsgLabel.ShowMsgEx(self, self.tr("添加收藏成功"))
            QtOwner().owner.favoriteForm.AddFavorites(self.bookId)
        else:
            QtOwner().owner.favoriteForm.DelAndFavoritesBack("", self.bookId)

    def OpenReadImg(self, modelIndex):
        index = modelIndex.row()
        self.OpenReadIndex(index)

    def OpenReadIndex(self, index, pageIndex=-1):
        item = self.epsListWidget.item(index)
        if not item:
            return
        widget = self.epsListWidget.itemWidget(item)
        if not widget:
            return
        name = widget.text()
        self.hide()
        QtOwner().owner.qtReadImg.OpenPage(self.bookId, index, name, pageIndex=pageIndex)
        # self.stackedWidget.setCurrentIndex(1)

    def StartRead(self):
        if self.lastEpsId >= 0:
            self.OpenReadIndex(self.lastEpsId, self.lastIndex)
        else:
            self.OpenReadIndex(0)
        return

    def LoadHistory(self):
        info = QtOwner().owner.historyForm.GetHistory(self.bookId)
        if not info:
            self.startRead.setText(self.tr("观看第1章"))
            return
        if self.lastEpsId == info.epsId:
            self.lastIndex = info.picIndex
            self.startRead.setText(self.tr("上次看到第") + str(self.lastEpsId + 1) + self.tr("章") + str(info.picIndex+1) + self.tr("页"))
            return

        if self.lastEpsId >= 0:
            item = self.epsListWidget.item(self.lastEpsId)
            if item:
                downloadIds = QtOwner().owner.downloadForm.GetDownloadCompleteEpsId(self.bookId)
                if self.lastEpsId in downloadIds:
                    item.setBackground(QColor(18, 161, 130))
                else:
                    item.setBackground(QColor(0,0,0,0))

        item = self.epsListWidget.item(info.epsId)
        if not item:
            return
        item.setBackground(QColor(238, 162, 164))
        self.epsListWidget.update()
        self.lastEpsId = info.epsId
        self.lastIndex = info.picIndex
        self.startRead.setText(self.tr("上次看到第") + str(self.lastEpsId + 1) + self.tr("章") + str(info.picIndex+1) + self.tr("页"))

    def ClickCategoriesItem(self, item):
        text = item.text()
        QtOwner().owner.searchForm.SearchCategories(text)
        return

    def ClickAutorItem(self, item):
        text = item.text()
        QtOwner().owner.searchForm.SearchAutor(text)
        return

    def ClickTagsItem(self, item):
        text = item.text()
        QtOwner().owner.searchForm.SearchTags(text)
        return

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                if obj == self.picture:
                    if self.pictureData:
                        QtImgMgr().ShowImg(self.pictureData)
                elif obj == self.user_icon:
                    if self.userIconData:
                        QtImgMgr().ShowImg(self.userIconData)
                elif obj == self.user_name:
                    QtOwner().owner.searchForm.SearchCreator(self.user_name.text())
                return True
            else:
                return False
        else:
            return super(self.__class__, self).eventFilter(obj, event)

    def keyPressEvent(self, ev):
        key = ev.key()
        if Qt.Key_Escape == key:
            self.close()
        return super(self.__class__, self).keyPressEvent(ev)

    def ChangeTab(self, index):
        if index == 1:
            if not self.commentWidget.listWidget.count():
                self.commentWidget.loadingForm2.show()
                self.commentWidget.LoadComment()
        return