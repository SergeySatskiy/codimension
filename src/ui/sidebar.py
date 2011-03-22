#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

""" sidebar implementation """

from PyQt4.QtCore import SIGNAL,  SLOT, QEvent, QSize, Qt
from PyQt4.QtGui  import QTabBar, QWidget, QStackedWidget, QBoxLayout


class SideBar( QWidget ):
    """ Sidebar with a widget area which is hidden or shown.
        On by clicking any tab, off by clicking the current tab.
    """

    North = 0
    East  = 1
    South = 2
    West  = 3

    def __init__( self, orientation = 2, parent = None ):
        QWidget.__init__( self, parent )

        self.__tabBar = QTabBar()
        self.__tabBar.setDrawBase( True )
        self.__tabBar.setShape( QTabBar.RoundedNorth )
        self.__tabBar.setFocusPolicy( Qt.NoFocus )
        self.__tabBar.setUsesScrollButtons( True )
        self.__tabBar.setElideMode( 1 )
        self.__stackedWidget = QStackedWidget( self )
        self.__stackedWidget.setContentsMargins( 0, 0, 0, 0 )
        self.barLayout = QBoxLayout( QBoxLayout.LeftToRight )
        self.barLayout.setMargin( 0 )
        self.layout = QBoxLayout( QBoxLayout.TopToBottom )
        self.layout.setMargin( 0 )
        self.layout.setSpacing( 0 )
        self.barLayout.addWidget( self.__tabBar )
        self.layout.addLayout( self.barLayout )
        self.layout.addWidget( self.__stackedWidget )
        self.setLayout( self.layout )

        self.__minimized = False
        self.__minSize = 0
        self.__maxSize = 0
        self.__bigSize = QSize()

        self.splitter = None
        self.splitterSizes = []

        self.__tabBar.installEventFilter( self )

        self.__orientation = orientation
        self.setOrientation( orientation )

        self.connect( self.__tabBar, SIGNAL( "currentChanged(int)" ),
                      self.__stackedWidget, SLOT( "setCurrentIndex(int)" ) )
        return

    def setSplitter( self, splitter ):
        """ Set the splitter managing the sidebar """

        self.splitter = splitter
        return

    def shrink( self ):
        """ Shrink the sidebar """
        if self.__minimized:
            return

        self.__minimized = True
        self.__bigSize = self.size()
        if self.__orientation in [ SideBar.North, SideBar.South ]:
            self.__minSize = self.minimumHeight()
            self.__maxSize = self.maximumHeight()
        else:
            self.__minSize = self.minimumWidth()
            self.__maxSize = self.maximumWidth()
        self.splitterSizes = self.splitter.sizes()

        self.__stackedWidget.hide()

        if self.__orientation in [ SideBar.North, SideBar.South ]:
            self.setFixedHeight( self.__tabBar.minimumSizeHint().height() )
        else:
            self.setFixedWidth( self.__tabBar.minimumSizeHint().width() )
        return

    def expand( self ):
        """ Expand the sidebar """
        if not self.__minimized:
            return

        self.__minimized = False
        self.__stackedWidget.show()
        self.resize( self.__bigSize )
        if self.__orientation in [ SideBar.North, SideBar.South ]:
            self.setMinimumHeight( self.__minSize )
            self.setMaximumHeight( self.__maxSize )
        else:
            self.setMinimumWidth( self.__minSize )
            self.setMaximumWidth( self.__maxSize )
        self.splitter.setSizes( self.splitterSizes )
        return

    def isMinimized( self ):
        """ Provides the minimized state """

        return self.__minimized

    def eventFilter( self, obj, evt ):
        """ Handle click events for the tabbar """

        if obj == self.__tabBar:
            if evt.type() == QEvent.MouseButtonPress:
                pos = evt.pos()

                index = self.__tabBar.count() - 1
                while index >= 0:
                    if self.__tabBar.tabRect( index ).contains( pos ):
                        break
                    index -= 1

                if index == self.__tabBar.currentIndex():
                    if self.isMinimized():
                        self.expand()
                    else:
                        self.shrink()
                    return True

                elif self.isMinimized():
                    self.expand()

        return QWidget.eventFilter( self, obj, evt )

    def addTab( self, widget, iconOrLabel, label = None ):
        """ Add a tab to the sidebar """

        if label:
            self.__tabBar.addTab( iconOrLabel, label )
        else:
            self.__tabBar.addTab( iconOrLabel )
        self.__stackedWidget.addWidget( widget )
        return

    def insertTab( self, index, widget, iconOrLabel, label = None ):
        """ Insert a tab into the sidebar """

        if label:
            self.__tabBar.insertTab( index, iconOrLabel, label )
        else:
            self.__tabBar.insertTab( index, iconOrLabel )
        self.__stackedWidget.insertWidget( index, widget )
        return

    def removeTab( self, index ):
        """ Remove a tab """

        self.__stackedWidget.removeWidget( self.__stackedWidget.widget( index ) )
        self.__tabBar.removeTab( index )
        return

    def clear( self ):
        """ Remove all tabs """

        while self.count() > 0:
            self.removeTab( 0 )
        return

    def prevTab( self ):
        """ Show the previous tab """

        index = self.currentIndex() - 1
        if index < 0:
            index = self.count() - 1

        self.setCurrentIndex( index )
        self.currentWidget().setFocus()
        return

    def nextTab( self ):
        """ Show the next tab """

        index = self.currentIndex() + 1
        if index >= self.count():
            index = 0

        self.setCurrentIndex( index )
        self.currentWidget().setFocus()
        return

    def count( self ):
        """ Provides the number of tabs """

        return self.__tabBar.count()

    def currentIndex( self ):
        """ Provides the index of the current tab """

        return self.__stackedWidget.currentIndex()

    def setCurrentIndex( self, index ):
        """ Switch to the certain tab """

        if index >= self.currentIndex():
            return

        self.__tabBar.setCurrentIndex( index )
        self.__stackedWidget.setCurrentIndex(index)
        if self.isMinimized():
            self.expand()
        return

    def currentWidget( self ):
        """ Provide a reference to the current widget """

        return self.__stackedWidget.currentWidget()

    def setCurrentWidget( self, widget ):
        """ Set the current widget """

        self.__stackedWidget.setCurrentWidget( widget )
        self.__tabBar.setCurrentIndex( self.__stackedWidget.currentIndex() )
        if self.isMinimized():
            self.expand()
        return

    def indexOf( self, widget ):
        """ Provides the index of the given widget """

        return self.__stackedWidget.indexOf( widget )

    def isTabEnabled( self, index ):
        """ Check if the tab is enabled """

        return self.__tabBar.isTabEnabled( index )

    def setTabEnabled( self, index, enabled ):
        """ Set the enabled state of the tab """

        self.__tabBar.setTabEnabled( index, enabled )
        return

    def orientation( self ):
        """ Provides the orientation of the sidebar """

        return self.__orientation

    def setOrientation( self, orient ):
        """ Set the orientation of the sidebar """

        if orient == SideBar.North:
            self.__tabBar.setShape( QTabBar.RoundedNorth )
            self.barLayout.setDirection( QBoxLayout.LeftToRight )
            self.layout.setDirection( QBoxLayout.TopToBottom )
            self.layout.setAlignment( self.barLayout, Qt.AlignLeft )
        elif orient == SideBar.East:
            self.__tabBar.setShape( QTabBar.RoundedEast )
            self.barLayout.setDirection( QBoxLayout.TopToBottom )
            self.layout.setDirection( QBoxLayout.RightToLeft )
            self.layout.setAlignment( self.barLayout, Qt.AlignTop )
        elif orient == SideBar.South:
            self.__tabBar.setShape( QTabBar.RoundedSouth )
            self.barLayout.setDirection( QBoxLayout.LeftToRight )
            self.layout.setDirection( QBoxLayout.BottomToTop )
            self.layout.setAlignment( self.barLayout, Qt.AlignLeft )
        else:
            # default
            orient = SideBar.West
            self.__tabBar.setShape( QTabBar.RoundedWest )
            self.barLayout.setDirection( QBoxLayout.TopToBottom )
            self.layout.setDirection( QBoxLayout.LeftToRight )
            self.layout.setAlignment( self.barLayout, Qt.AlignTop )
        self.__orientation = orient
        return

    def tabIcon( self, index ):
        """ Provide the icon of the tab """

        return self.__tabBar.tabIcon( index )

    def setTabIcon( self, index, icon ):
        """ Set the icon of the tab """

        self.__tabBar.setTabIcon( index, icon )
        return

    def tabText( self, index ):
        """ Provide the text of the tab """

        return self.__tabBar.tabText( index )

    def setTabText( self, index, text ):
        """ Set the text of the tab """

        self.__tabBar.setTabText( index, text )
        return

    def tabToolTip( self, index ):
        """ Provide the tooltip text of the tab """

        return self.__tabBar.tabToolTip( index )

    def setTabToolTip( self, index, tip ):
        """ Set the tooltip text of the tab """

        self.__tabBar.setTabToolTip( index, tip )
        return

    def tabWhatsThis( self, index ):
        """ Provide the WhatsThis text of the tab """

        return self.__tabBar.tabWhatsThis( index )

    def setTabWhatsThis( self, index, text ):
        """ Set the WhatsThis text for the tab """

        self.__tabBar.setTabWhatsThis( index, text )
        return

    def widget( self, index ):
        """ Provides the reference to the widget (QWidget) """

        return self.__stackedWidget.widget( index )

