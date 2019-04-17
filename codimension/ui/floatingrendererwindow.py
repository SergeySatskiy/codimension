# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2019  Sergey Satskiy <sergey.satskiy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Detached renderer window"""


from utils.globals import GlobalData
from .qt import (QMainWindow, QTimer, QStackedWidget, QLabel, QVBoxLayout,
                 QWidget, QPalette, Qt, QFrame)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class DetachedRendererWindow(QMainWindow):

    """Detached flow ui/markdown renderer window"""

    def __init__(self, settings, em):
        QMainWindow.__init__(self, None)

        self.settings = settings
        self.em = em

        self.__widgets = QStackedWidget(self)
        self.__widgets.setContentsMargins(1, 1, 1, 1)
        self.__noRenderLabel = QLabel('\nNo rendering available for the current tab')
        self.__noRenderLabel.setFrameShape(QFrame.StyledPanel)
        self.__noRenderLabel.setAlignment(Qt.AlignHCenter)
        self.__noRenderLabel.setAutoFillBackground(True)
        font = self.__noRenderLabel.font()
        font.setPointSize(font.pointSize() + 4)
        self.__noRenderLabel.setFont(font)
        palette = self.__noRenderLabel.palette()
        palette.setColor(QPalette.Background,
                         GlobalData().skin['nolexerPaper'])
        self.__noRenderLabel.setPalette(palette)
        self.__widgets.addWidget(self.__noRenderLabel)
        self.setCentralWidget(self.__widgets)

        self.__ideClosing = False
        self.__initialisation = True

        # The size restore is done twice to avoid huge flickering
        # This one is approximate, the one in restoreWindowPosition()
        # is precise
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != settings['screenwidth'] or \
           screenSize.height() != settings['screenheight']:
            # The screen resolution has been changed, use the default pos
            defXPos, defYpos, \
            defWidth, defHeight = settings.getDefaultRendererWindowGeometry()
            self.resize(defWidth, defHeight)
            self.move(defXPos, defYpos)
        else:
            # No changes in the screen resolution
            self.resize(settings['rendererwidth'], settings['rendererheight'])
            self.move(settings['rendererxpos'] + settings['xdelta'],
                      settings['rendererypos'] + settings['ydelta'])


    def closeEvent(self, event):
        """Renderer is closed: explicit close via X or IDE is closed"""
        if not self.__ideClosing:
            # Update the IDE button and memorize the setting
            self.settings['floatingRenderer'] = not self.settings['floatingRenderer']
            GlobalData().mainWindow.floatingRendererButton.setChecked(False)
            self.hide()
            return

    def __registerWidget(self, widget):
        """Registers one widget basing on info from the editors manager"""
        renderLayout = QVBoxLayout()
        renderLayout.setContentsMargins(0, 0, 0, 0)
        renderLayout.setSpacing(0)
        for wid in widget.popRenderingWidgets():
            renderLayout.addWidget(wid)
        renderWidget = QWidget()
        renderWidget.setLayout(renderLayout)

        renderWidget.setObjectName(widget.getUUID())
        self.__widgets.addWidget(renderWidget)

    def show(self):
        """Overwritten show method"""
        self.__connectSignals()

        # grab the widgets
        for index in range(self.em.count()):
            widget = self.em.widget(index)
            if widget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
                self.__registerWidget(widget)

        self.updateCurrent()

        QMainWindow.show(self)
        if self.__initialisation:
            self.restoreWindowPosition()

    def hide(self):
        """Overwritten hide method"""
        QMainWindow.hide(self)
        self.__disconnectSignals()

        # return widgets
        while self.__widgets.count() > 1:
            widget = self.__widgets.widget(1)
            uuid = widget.objectName()

            toBeReturned = []
            layout = widget.layout()
            for index in range(layout.count()):
                w = layout.itemAt(index).widget()
                if w is not None:
                    toBeReturned.append(w)
            for w in toBeReturned:
                layout.removeWidget(w)

            self.__widgets.removeWidget(widget)

            for index in range(self.em.count()):
                widget = self.em.widget(index)
                if widget.getUUID() == uuid:
                    widget.pushRenderingWidgets(toBeReturned)
                    break

    def __connectSignals(self):
        """Connects to all the required sugnals"""
        self.em.sigTabClosed.connect(self.__onTabClosed)
        self.em.currentChanged.connect(self.__onCurrentTabChanged)
        self.em.sigTextEditorTabAdded.connect(self.__onTextEditorTabAdded)
        self.em.sigFileTypeChanged.connect(self.__onFileTypeChanged)
        self.em.sigFileUpdated.connect(self.__onFileUpdated)
        self.em.sigBufferSavedAs.connect(self.__onBufferSavedAs)

    def __disconnectSignals(self):
        """Disconnects the signals"""
        self.em.sigBufferSavedAs.disconnect(self.__onBufferSavedAs)
        self.em.sigFileUpdated.disconnect(self.__onFileUpdated)
        self.em.sigTextEditorTabAdded.disconnect(self.__onTextEditorTabAdded)
        self.em.currentChanged.disconnect(self.__onCurrentTabChanged)
        self.em.sigTabClosed.disconnect(self.__onTabClosed)
        self.em.sigFileTypeChanged.disconnect(self.__onFileTypeChanged)

    def resizeEvent(self, resizeEv):
        """Triggered when the window is resized"""
        del resizeEv    # unused argument
        QTimer.singleShot(1, self.__resizeEventdelayed)

    def __resizeEventdelayed(self):
        """Memorizes the new window size"""
        if self.__initialisation or self.__guessMaximized():
            return

        self.settings['rendererwidth'] = self.width()
        self.settings['rendererheight'] = self.height()

    def moveEvent(self, moveEv):
        """Triggered when the window is moved"""
        del moveEv  # unused argument
        QTimer.singleShot(1, self.__moveEventDelayed)

    def __moveEventDelayed(self):
        """Memorizes the new window position"""
        if not self.__initialisation and not self.__guessMaximized():
            self.settings['rendererxpos'] = self.x()
            self.settings['rendererypos'] = self.y()

    def __guessMaximized(self):
        """True if the window is maximized"""
        # Ugly but I don't see any better way.
        # It is impossible to catch the case when the main window is maximized.
        # Especially when networked XServer is used (like xming)
        # So, make a wild guess instead and do not save the status if
        # maximized.
        availGeom = GlobalData().application.desktop().availableGeometry()
        if self.width() + abs(self.settings['xdelta']) > availGeom.width() or \
           self.height() + abs(self.settings['ydelta']) > availGeom.height():
            return True
        return False

    def restoreWindowPosition(self):
        """Makes sure that the window frame delta is proper"""
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != self.settings['screenwidth'] or \
           screenSize.height() != self.settings['screenheight']:
            # The screen resolution has been changed, save the new values
            self.settings['screenwidth'] = screenSize.width()
            self.settings['screenheight'] = screenSize.height()
            self.settings['xdelta'] = self.settings['xpos'] - self.x()
            self.settings['ydelta'] = self.settings['ypos'] - self.y()
            self.settings['rendererxpos'] = self.x()
            self.settings['rendererypos'] = self.y()
        else:
            # Screen resolution is the same as before
            if self.settings['rendererxpos'] != self.x() or \
               self.settings['rendererypos'] != self.y():
                # The saved delta is incorrect, update it
                self.settings['xdelta'] = self.settings['rendererxpos'] - self.x() + \
                                          self.settings['xdelta']
                self.settings['ydelta'] = self.settings['rendererypos'] - self.y() + \
                                          self.settings['ydelta']
                self.settings['rendererxpos'] = self.x()
                self.settings['rendererypos'] = self.y()
        self.__initialisation = False

    def close(self):
        """Overwritten close method. Called when the IDE is closed"""
        self.__ideClosing = True
        while self.__widgets.count() > 0:
            self.__widgets.removeWidget(self.__widgets.widget(0))
        QMainWindow.close(self)

    def __onTabClosed(self, tabUUID):
        """Triggered when the editor tab is closed"""
        for index in range(self.__widgets.count()):
            if self.__widgets.widget(index).objectName() == tabUUID:
                self.__widgets.removeWidget(self.__widgets.widget(index))
                self.updateCurrent()
                return

    def __onCurrentTabChanged(self, index):
        """Triggered when the current tab is changed"""
        del index   # :nused argument
        self.updateCurrent()

    def __onTextEditorTabAdded(self, index):
        """Triggered when a new text editor window was added"""
        widget = self.em.widget(index)
        if widget.getType() == MainWindowTabWidgetBase.PlainTextEditor:
            self.__registerWidget(widget)
        self.updateCurrent()

    def __onFileTypeChanged(self, fname, uuid, mime):
        """Triggered when a file type is changed"""
        for index in range(self.__widgets.count()):
            if self.__widgets.widget(index).objectName() == uuid:
                self.updateCurrent()
                return

    def __onBufferSavedAs(self, fname, uuid):
        """Triggered when the file was saved under another name"""
        for index in range(self.__widgets.count()):
            if self.__widgets.widget(index).objectName() == uuid:
                self.updateCurrent()
                return

    def __onFileUpdated(self, fname, uuid):
        """Triggered when the file is overwritten"""
        for index in range(self.__widgets.count()):
            if self.__widgets.widget(index).objectName() == uuid:
                self.updateCurrent()
                return

    def updateCurrent(self):
        """Updates the window title and switches to the proper widget"""
        widget = self.em.widget(self.em.currentIndex())
        if widget is None:
            # May happened when there are no widgets in the em
            return

        widgetType = widget.getType()
        if widgetType == MainWindowTabWidgetBase.PlainTextEditor:
            editor = widget.getEditor()
            isPython = editor.isPythonBuffer()
            isMarkdown = editor.isMarkdownBuffer()
            if isPython or isMarkdown:
                title = 'Floating renderer: '
                if isPython:
                    title += 'python buffer ('
                else:
                    title += 'markdown buffer ('
                title += widget.getShortName() + ')'
                self.setWindowTitle(title)

                uuid = widget.getUUID()
                for index in range(self.__widgets.count()):
                    if self.__widgets.widget(index).objectName() == uuid:
                        self.__widgets.setCurrentIndex(index)
                        break
                return

        # Not python, not markdown, i.e. no renderer
        self.__widgets.setCurrentIndex(0)
        self.setWindowTitle('Floating renderer: no renderer for the current tab')
