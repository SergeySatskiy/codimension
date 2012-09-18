#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" namespaces viewer "


from PyQt4.QtCore       import Qt, SIGNAL, QStringList
from PyQt4.QtGui        import QFrame, QVBoxLayout, QLabel, QWidget, \
                               QSizePolicy, QTabWidget, QSpacerItem, \
                               QHBoxLayout, QToolButton, QPalette
from namespace          import NamespaceViewer
from utils.pixmapcache  import PixmapCache


class NamespacesViewer( QWidget ):
    " Implements the stack viewer for a debugger "

    MinFilter = 0
    MedFilter = 1
    MaxFilter = 2

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__locals = NamespaceViewer()
        self.__globals = NamespaceViewer()
        self.__exceptions = NamespaceViewer()
        self.__filter = NamespacesViewer.MedFilter

        self.__namespacesBar = QTabWidget()
        self.__namespacesBar.addTab( self.__locals, "Local" )
        self.__namespacesBar.addTab( self.__globals,
                                     PixmapCache().getIcon( 'globalvar.png' ),
                                     "Global" )
        self.__namespacesBar.addTab( self.__exceptions, "Exception" )

        self.__createLayout()
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 0, 0, 0, 0 )
        verticalLayout.setSpacing( 0 )

        headerFrame = QFrame()
        headerFrame.setFrameStyle( QFrame.StyledPanel )
        headerFrame.setAutoFillBackground( True )
        headerPalette = headerFrame.palette()
        headerBackground = headerPalette.color( QPalette.Background )
        headerBackground.setRgb( min( headerBackground.red() + 30, 255 ),
                                 min( headerBackground.green() + 30, 255 ),
                                 min( headerBackground.blue() + 30, 255 ) )
        headerPalette.setColor( QPalette.Background, headerBackground )
        headerFrame.setPalette( headerPalette )
        headerFrame.setFixedHeight( 24 )

        label = QLabel( "Namespaces" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer = QSpacerItem( 3, 3 )

        self.__minFilterButton = QToolButton()
        self.__minFilterButton.setCheckable( True )
        self.__minFilterButton.setChecked( False )
        self.__minFilterButton.setIcon( PixmapCache().getIcon( 'maxitems.png' ) )
        self.__minFilterButton.setFixedSize( 20, 20 )
        self.__minFilterButton.setToolTip( "Filter: minimum" )
        self.__minFilterButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__minFilterButton, SIGNAL( 'clicked()' ),
                      self.__onMinFilter )

        self.__medFilterButton = QToolButton()
        self.__medFilterButton.setCheckable( True )
        self.__medFilterButton.setChecked( True )
        self.__medFilterButton.setIcon( PixmapCache().getIcon( 'meditems.png' ) )
        self.__medFilterButton.setFixedSize( 20, 20 )
        self.__medFilterButton.setToolTip( "Filter: medium" )
        self.__medFilterButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__medFilterButton, SIGNAL( 'clicked()' ),
                      self.__onMedFilter )

        self.__maxFilterButton = QToolButton()
        self.__maxFilterButton.setCheckable( True )
        self.__maxFilterButton.setChecked( False )
        self.__maxFilterButton.setIcon( PixmapCache().getIcon( 'minitems.png' ) )
        self.__maxFilterButton.setFixedSize( 20, 20 )
        self.__maxFilterButton.setToolTip( "Filter: maximum" )
        self.__maxFilterButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__maxFilterButton, SIGNAL( 'clicked()' ),
                      self.__onMaxFilter )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 0, 0, 0, 0 )
        headerLayout.setSpacing( 0 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( label )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__minFilterButton )
        headerLayout.addWidget( self.__medFilterButton )
        headerLayout.addWidget( self.__maxFilterButton )
        headerFrame.setLayout( headerLayout )

        verticalLayout.addWidget( headerFrame )
        verticalLayout.addWidget( self.__namespacesBar )
        return

    def __onMinFilter( self ):
        " Min filtering has been pressed "
        self.__minFilterButton.setChecked( True )
        self.__medFilterButton.setChecked( False )
        self.__maxFilterButton.setChecked( False )

        if self.__filter == NamespacesViewer.MinFilter:
            # No changes
            return

        self.__filter = NamespacesViewer.MinFilter
        return

    def __onMedFilter( self ):
        " Med filtering has been pressed "
        self.__minFilterButton.setChecked( False )
        self.__medFilterButton.setChecked( True )
        self.__maxFilterButton.setChecked( False )

        if self.__filter == NamespacesViewer.MedFilter:
            # No changes
            return

        self.__filter = NamespacesViewer.MedFilter
        return

    def __onMaxFilter( self ):
        " Max filtering has been pressed "
        self.__minFilterButton.setChecked( False )
        self.__medFilterButton.setChecked( False )
        self.__maxFilterButton.setChecked( True )

        if self.__filter == NamespacesViewer.MaxFilter:
            # No changes
            return

        self.__filter = NamespacesViewer.MaxFilter
        return


