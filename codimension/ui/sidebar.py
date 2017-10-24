# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Sidebar implementation"""

from .qt import (QEvent, QSize, Qt, QTabBar, QWidget, QStackedWidget,
                 QBoxLayout, pyqtSignal)


class SideBar(QWidget):

    """Sidebar with a widget area which is hidden or shown.

    On by clicking any tab, off by clicking the current tab.
    """

    North = 0
    East = 1
    South = 2
    West = 3

    sigTabCloseRequested = pyqtSignal(int)

    def __init__(self, orientation, parent=None):
        QWidget.__init__(self, parent)

        self.__tabBar = QTabBar()
        self.__tabBar.setDrawBase(True)
        self.__tabBar.setFocusPolicy(Qt.NoFocus)
        self.__tabBar.setUsesScrollButtons(True)
        self.__tabBar.setElideMode(1)
        self.__tabBar.tabCloseRequested.connect(self.__onCloseRequest)
        self.__stackedWidget = QStackedWidget(self)
        self.__stackedWidget.setContentsMargins(0, 0, 0, 0)
        self.barLayout = QBoxLayout(QBoxLayout.LeftToRight)
        self.barLayout.setContentsMargins(0, 0, 0, 0)
        self.layout = QBoxLayout(QBoxLayout.TopToBottom)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.barLayout.addWidget(self.__tabBar)
        self.layout.addLayout(self.barLayout)
        self.layout.addWidget(self.__stackedWidget)
        self.setLayout(self.layout)

        self.__minimized = False
        self.__minSize = 0
        self.__maxSize = 0
        self.__bigSize = QSize()

        self.splitter = None

        self.__tabBar.installEventFilter(self)

        self.__orientation = orientation
        self.setOrientation(orientation)

        self.__tabBar.currentChanged.connect(
            self.__stackedWidget.setCurrentIndex)

    def setSplitter(self, splitter):
        """Set the splitter managing the sidebar"""
        self.splitter = splitter

    def __getIndex(self):
        """Provides the widget index in splitters"""
        if self.__orientation == SideBar.West:
            return 0
        if self.__orientation == SideBar.East:
            return 2
        if self.__orientation == SideBar.South:
            return 1
        return 0

    def shrink(self):
        """Shrink the sidebar"""
        if self.__minimized:
            return

        self.__minimized = True
        self.__bigSize = self.size()
        if self.__orientation in [SideBar.North, SideBar.South]:
            self.__minSize = self.minimumHeight()
            self.__maxSize = self.maximumHeight()
        else:
            self.__minSize = self.minimumWidth()
            self.__maxSize = self.maximumWidth()

        self.__stackedWidget.hide()

        sizes = self.splitter.sizes()
        selfIndex = self.__getIndex()

        if self.__orientation in [SideBar.North, SideBar.South]:
            newHeight = self.__tabBar.minimumSizeHint().height()
            self.setFixedHeight(newHeight)

            diff = sizes[selfIndex] - newHeight
            sizes[selfIndex] = newHeight
        else:
            newWidth = self.__tabBar.minimumSizeHint().width()
            self.setFixedWidth(newWidth)

            diff = sizes[selfIndex] - newWidth
            sizes[selfIndex] = newWidth

        if selfIndex == 0:
            sizes[1] += diff
        else:
            sizes[selfIndex - 1] += diff

        self.splitter.setSizes(sizes)

    def expand(self):
        """Expand the sidebar"""
        if not self.__minimized:
            return

        self.__minimized = False
        self.__stackedWidget.show()
        self.resize(self.__bigSize)

        sizes = self.splitter.sizes()
        selfIndex = self.__getIndex()

        if self.__orientation in [SideBar.North, SideBar.South]:
            self.setMinimumHeight(self.__minSize)
            self.setMaximumHeight(self.__maxSize)

            diff = self.__bigSize.height() - sizes[selfIndex]
            sizes[selfIndex] = self.__bigSize.height()
        else:
            self.setMinimumWidth(self.__minSize)
            self.setMaximumWidth(self.__maxSize)

            diff = self.__bigSize.width() - sizes[selfIndex]
            sizes[selfIndex] = self.__bigSize.width()

        if selfIndex == 0:
            sizes[1] -= diff
        else:
            sizes[selfIndex - 1] -= diff

        self.splitter.setSizes(sizes)

    def isMinimized(self):
        """Provides the minimized state"""
        return self.__minimized

    def eventFilter(self, obj, evt):
        """Handle click events for the tabbar"""
        if obj == self.__tabBar:
            if evt.type() == QEvent.MouseButtonPress:
                pos = evt.pos()

                index = None
                for index in range(self.__tabBar.count()):
                    if self.__tabBar.tabRect(index).contains(pos):
                        break

                if index == self.__tabBar.currentIndex():
                    if self.isMinimized():
                        self.expand()
                    else:
                        self.shrink()
                    return True

                if self.isMinimized():
                    if self.isTabEnabled(index):
                        self.expand()

        return QWidget.eventFilter(self, obj, evt)

    @staticmethod
    def __toVariant(name, priority):
        """A tab stores its name and priority"""
        if priority is None:
            return ':' + name
        return str(priority) + ':' + name

    @staticmethod
    def __fromVariant(data):
        """A tab stores its name and priority"""
        val = data.split(':')
        if val[0] == '':
            return val[1], None
        return val[1], int(val[0])

    def __appendTab(self, widget, icon, label, name, priority):
        """Appends a new widget to the end"""
        self.__tabBar.addTab(icon, label)
        self.__stackedWidget.addWidget(widget)
        self.__tabBar.setTabData(self.count - 1,
                                 self.__toVariant(name, priority))

    def __pickInsertIndex(self, priority):
        """Picks the tab insert index in accordance to the priority"""
        for index in range(self.__tabBar.count()):
            data = self.__tabBar.tabData(index)
            _, tabPriority = self.__fromVariant(data)
            if tabPriority is None:
                return index
            if priority < tabPriority:
                return index
        return None

    def addTab(self, widget, icon, label, name, priority):
        """Add a tab to the sidebar"""
        if priority is None:
            # Appending to the end
            self.__appendTab(widget, icon, label, name, priority)
        else:
            # Pick the index in accordance to the priority
            index = self.__pickInsertIndex(priority)
            if index is None:
                self.__appendTab(widget, icon, label, name, priority)
            else:
                self.__tabBar.insertTab(index, icon, label)
                self.__stackedWidget.insertWidget(index, widget)
                self.__tabBar.setTabData(index,
                                         self.__toVariant(name, priority))

    def clear(self):
        """Remove all tabs"""
        while self.count > 0:
            self.removeTab(0)

    def prevTab(self):
        """Show the previous tab"""
        index = self.currentIndex() - 1
        if index < 0:
            index = self.count - 1

        self.setCurrentIndex(index)
        self.currentWidget().setFocus()

    def nextTab(self):
        """Show the next tab"""
        index = self.currentIndex() + 1
        if index >= self.count:
            index = 0

        self.setCurrentIndex(index)
        self.currentWidget().setFocus()

    @property
    def count(self):
        """Provides the number of tabs"""
        return self.__tabBar.count()

    def currentIndex(self):
        """Provides the index of the current tab"""
        return self.__stackedWidget.currentIndex()

    def currentWidget(self):
        """Provide a reference to the current widget"""
        return self.__stackedWidget.currentWidget()

    def currentTabName(self):
        """Provides the name of the current tab"""
        return self.getTabName(self.currentIndex())

    def __getWidgetIndex(self, indexOrNameOrWidget):
        """Provides the widget index via the provided index, name or widget"""
        if indexOrNameOrWidget is None:
            return None
        if isinstance(indexOrNameOrWidget, int):
            if indexOrNameOrWidget >= self.count:
                return None
            return indexOrNameOrWidget
        if isinstance(indexOrNameOrWidget, str):
            for index in range(self.__tabBar.count()):
                data = self.__tabBar.tabData(index)
                tabName, _ = self.__fromVariant(data)
                if tabName == indexOrNameOrWidget:
                    return index
            return None
        return self.__stackedWidget.indexOf(indexOrNameOrWidget)

    def getTabName(self, indexOrWidget):
        """Provides the tab name by index or widget"""
        index = self.__getWidgetIndex(indexOrWidget)
        if index is not None:
            data = self.__tabBar.tabData(index)
            tabName, _ = self.__fromVariant(data)
            return tabName
        return None

    def updateTabName(self, indexOrNameOrWidget, newName):
        """Updates the tab name"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            data = self.__tabBar.tabData(index)
            _, priority = self.__fromVariant(data)
            self.__tabBar.setTabData(index,
                                     self.__toVariant(newName, priority))

    def setCurrentTab(self, indexOrNameOrWidget):
        """Sets the current widget approprietly"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            self.__tabBar.setCurrentIndex(index)
            self.__stackedWidget.setCurrentIndex(index)
            if self.isMinimized():
                self.expand()

    def removeTab(self, indexOrNameOrWidget):
        """Remove a tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            self.__stackedWidget.removeWidget(
                self.__stackedWidget.widget(index))
            self.__tabBar.removeTab(index)

    def isTabEnabled(self, indexOrNameOrWidget):
        """Check if the tab is enabled"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            return self.__tabBar.isTabEnabled(index)
        return False

    def setTabEnabled(self, indexOrNameOrWidget, enabled):
        """Set the enabled state of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            self.__tabBar.setTabEnabled(index, enabled)

    def orientation(self):
        """Provides the orientation of the sidebar"""
        return self.__orientation

    def setOrientation(self, orient):
        """Set the orientation of the sidebar"""
        if orient == SideBar.North:
            self.__tabBar.setShape(QTabBar.RoundedNorth)
            self.barLayout.setDirection(QBoxLayout.LeftToRight)
            self.layout.setDirection(QBoxLayout.TopToBottom)
            self.layout.setAlignment(self.barLayout, Qt.AlignLeft)
        elif orient == SideBar.East:
            self.__tabBar.setShape(QTabBar.RoundedEast)
            self.barLayout.setDirection(QBoxLayout.TopToBottom)
            self.layout.setDirection(QBoxLayout.RightToLeft)
            self.layout.setAlignment(self.barLayout, Qt.AlignTop)
        elif orient == SideBar.South:
            self.__tabBar.setShape(QTabBar.RoundedSouth)
            self.barLayout.setDirection(QBoxLayout.LeftToRight)
            self.layout.setDirection(QBoxLayout.BottomToTop)
            self.layout.setAlignment(self.barLayout, Qt.AlignLeft)
        else:
            # default
            orient = SideBar.West
            self.__tabBar.setShape(QTabBar.RoundedWest)
            self.barLayout.setDirection(QBoxLayout.TopToBottom)
            self.layout.setDirection(QBoxLayout.LeftToRight)
            self.layout.setAlignment(self.barLayout, Qt.AlignTop)
        self.__orientation = orient

    def tabIcon(self, indexOrNameOrWidget):
        """Provide the icon of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            return self.__tabBar.tabIcon(index)
        return None

    def setTabIcon(self, indexOrNameOrWidget, icon):
        """Set the icon of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            self.__tabBar.setTabIcon(index, icon)

    def tabText(self, indexOrNameOrWidget):
        """Provide the text of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            return self.__tabBar.tabText(index)
        return None

    def tabButton(self, indexOrNameOrWidget, position):
        """Provide the button of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            return self.__tabBar.tabButton(index, position)
        return None

    def setTabText(self, indexOrNameOrWidget, text):
        """Set the text of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            self.__tabBar.setTabText(index, text)

    def tabToolTip(self, indexOrNameOrWidget):
        """Provide the tooltip text of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            return self.__tabBar.tabToolTip(index)
        return None

    def setTabToolTip(self, indexOrNameOrWidget, tip):
        """Set the tooltip text of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            self.__tabBar.setTabToolTip(index, tip)

    def tabWhatsThis(self, indexOrNameOrWidget):
        """Provide the WhatsThis text of the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            return self.__tabBar.tabWhatsThis(index)
        return None

    def setTabWhatsThis(self, indexOrNameOrWidget, text):
        """Set the WhatsThis text for the tab"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            self.__tabBar.setTabWhatsThis(index, text)

    def widget(self, indexOrNameOrWidget):
        """Provides the reference to the widget: QWidget or None"""
        index = self.__getWidgetIndex(indexOrNameOrWidget)
        if index is not None:
            return self.__stackedWidget.widget(index)
        return None

    def setTabsClosable(self, closable):
        """Sets the tabs closable"""
        self.__tabBar.setTabsClosable(closable)

    def __onCloseRequest(self, index):
        """Re-emits the close request signal"""
        self.sigTabCloseRequested.emit(index)
