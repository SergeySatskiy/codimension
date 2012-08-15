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

" Profiling results as a table "


import pstats
import logging
import os.path

from PyQt4.QtCore import Qt, SIGNAL, QStringList
from PyQt4.QtGui import QTreeWidgetItem, QTreeWidget, QColor, QBrush, QLabel, \
                        QWidget, QVBoxLayout, QFrame, QPalette, QHeaderView
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.globals import GlobalData


FLOAT_FORMAT = "%8.6f"


class ProfilingTableItem( QTreeWidgetItem ):
    " Profiling table row "

    def __init__( self, items, isOutside, path, line ):
        QTreeWidgetItem.__init__( self, items )

        self.fileName = path
        self.line = line
        self.isOutside = isOutside

        if isOutside:
            self.setIcon( 0, PixmapCache().getIcon( 'nonprojectentry.png' ) )
            self.setToolTip( 0, 'Record of an outside function' )
        else:
            self.setIcon( 0, PixmapCache().getIcon( 'empty.png' ) )
            self.setToolTip( 0, '' )
        return

    @staticmethod
    def __getActualCalls( txt ):
        # Returns the actual number of calls as integer
        return int( str( txt ).split( '/', 1 )[ 0 ] )

    @staticmethod
    def __getFloatValue( txt ):
        # Returns a float value from a column
        return float( str( txt ).split( ' ', 1 )[ 0 ] )

    def __lt__( self, other ):
        " Integer or string sorting "
        sortColumn = self.treeWidget().sortColumn()

        if sortColumn == 0:
            return self.isOutside < other.isOutside

        txt = self.text( sortColumn )
        otherTxt = other.text( sortColumn )
        if sortColumn == 1:
            return self.__getActualCalls( txt ) < self.__getActualCalls( otherTxt )

        if sortColumn in [ 2, 3, 4, 5 ]:
            return self.__getFloatValue( txt ) < self.__getFloatValue( otherTxt )

        if sortColumn == 6:
            # Function location
            if self.fileName == other.fileName:
                return self.line < other.line
            return self.fileName < other.fileName

        if sortColumn == 7:
            # Function name
            return txt < otherTxt

        if sortColumn in [ 8, 9 ]:
            # Number of callers/collees
            return int( txt ) < int( otherTxt )

        # Fallback to string comparison
        return txt < otherTxt


class ProfileTableViewer( QWidget ):
    " Profiling results table viewer "

    def __init__( self, scriptName, params, reportTime, dataFile, parent = None ):
        QWidget.__init__( self, parent )

        self.__table = QTreeWidget( self )

        self.__script = scriptName
        project = GlobalData().project
        if project.isLoaded():
            self.__projectPrefix = os.path.dirname( project.fileName )
        else:
            self.__projectPrefix = os.path.dirname( scriptName )
        if not self.__projectPrefix.endswith( os.path.sep ):
            self.__projectPrefix += os.path.sep

        self.__table.setAlternatingRowColors( True )
        self.__table.setRootIsDecorated( False )
        self.__table.setItemsExpandable( False )
        self.__table.setSortingEnabled( True )
        self.__table.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__table.setUniformRowHeights( True )
        headerLabels = QStringList()

        headerLabels << "" << "Calls" << "Total time" << "Per call"
        headerLabels << "Cum. time" << "Per call"
        headerLabels << "File name/line" << "Function" << "Callers" << "Callees"
        self.__table.setHeaderLabels( headerLabels )

        headerItem = self.__table.headerItem()
        headerItem.setToolTip( 0, "Indication if it is an outside function" )
        headerItem.setToolTip( 1, "Actual number of calls/primitive calls " \
                                  "(not induced via recursion)" )
        headerItem.setToolTip( 2, "Total time spent in function " \
                                  "(excluding time made in calls " \
                                  "to sub-functions)" )
        headerItem.setToolTip( 3, "Total time divided by number " \
                                  "of actual calls" )
        headerItem.setToolTip( 4, "Total time spent in function and all " \
                                  "subfunctions (from invocation till exit)" )
        headerItem.setToolTip( 5, "Cumulative time divided by number " \
                                  "of primitive calls" )
        headerItem.setToolTip( 6, "Function location" )
        headerItem.setToolTip( 7, "Function name" )
        headerItem.setToolTip( 8, "Function callers" )
        headerItem.setToolTip( 9, "Function callees" )

        self.connect( self.__table, SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__activated )

        self.__stats = pstats.Stats( dataFile )
        totalCalls = self.__stats.total_calls
        totalPrimitiveCalls = self.__stats.prim_calls  # The calls was not induced via recursion
        totalTime = self.__stats.total_tt

        summary = QLabel( "<b>Script:</b> " + self.__script + " " + params.arguments + "<br>" \
                          "<b>Run at:</b> " + reportTime + "<br>" + \
                          str( totalCalls ) + " function calls (" + \
                          str( totalPrimitiveCalls ) + " primitive calls) in " + \
                          FLOAT_FORMAT % totalTime + " CPU seconds" )
        summary.setFrameStyle( QFrame.StyledPanel )
        summary.setAutoFillBackground( True )
        summaryPalette = summary.palette()
        summaryBackground = summaryPalette.color( QPalette.Background )
        summaryBackground.setRgb( min( summaryBackground.red() + 30, 255 ),
                                  min( summaryBackground.green() + 30, 255 ),
                                  min( summaryBackground.blue() + 30, 255 ) )
        summaryPalette.setColor( QPalette.Background, summaryBackground )
        summary.setPalette( summaryPalette )

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins( 0, 0, 0, 0 )
        vLayout.setSpacing( 0 )
        vLayout.addWidget( summary )
        vLayout.addWidget( self.__table )

        self.setLayout( vLayout )

        self.__populate()
        return

    def __resize( self ):
        " Resizes columns to the content "
        self.__table.header().resizeSections( QHeaderView.ResizeToContents )
        self.__table.header().setStretchLastSection( True )
        return

    def setFocus( self ):
        " Set focus to the proper widget "
        self.__table.setFocus()
        return

    def __isOutsideItem( self, fileName ):
        " Detects if the record should be shown as an outside one "
        return not fileName.startswith( self.__projectPrefix )

    def __activated( self, item, column ):
        " Triggered when the item is activated "

        try:
            if item.line == 0 or item.fileName is None or \
               not os.path.abspath( item.fileName ):
                return
            GlobalData().mainWindow.openFile( item.fileName, item.line )
        except:
            logging.error( "Could not jump to function location" )
        return

    def __getCallLine( self, func, props ):
        " Provides the formatted call line "
        calls = str( props[ 1 ] )
        if props[ 0 ] != props[ 1 ]:
            calls += "/" + str( props[ 0 ] )
        
        return func[ 0 ] + ":" + str( func[ 1 ] ) + "(" + func[ 2 ] + ") " + calls
        print "Func: " + str( func )
        print "Props: " + str( props )
        return "dumb"

    def __createItem( self, funcFileName, funcLine, funcName,
                            primitiveCalls, actualCalls, totalTime,
                            cumulativeTime, timePerCall, cumulativeTimePerCall,
                            callers ):
        " Creates an item to display "
        values = QStringList()
        if primitiveCalls == actualCalls:
            values << str( actualCalls )
        else:
            values << str( actualCalls ) + "/" + str( primitiveCalls )

        values << FLOAT_FORMAT % totalTime
        values << FLOAT_FORMAT % timePerCall
        values << FLOAT_FORMAT % cumulativeTime
        values << FLOAT_FORMAT % cumulativeTimePerCall

        if funcLine is not None and funcLine != 0:
            funcLocation = funcFileName + ":" + str( funcLine )
        else:
            funcLocation = funcFileName
        values << funcLocation

        values << funcName

        callersCount = len( callers )
        values << str( callersCount )

        item = ProfilingTableItem( values )
        for column in [ 0, 1, 2, 3, 4 ]:
            item.setTextAlignment( column, Qt.AlignRight )

        if funcLocation is not None and funcLocation != "":
            item.setToolTip( 5, funcLocation )

        if callersCount != 0:
            tooltip = ""
            for func in callers:
                if tooltip != "":
                    tooltip += "\n"
                tooltip += self.__getCallLine( func, callers[ func ] )
            item.setToolTip( 7, tooltip )

        self.__setItemBackground( item, funcFileName )
        self.__table.addTopLevelItem( item )
        return

    def __populate( self ):
        " Populates the data "

        for func, ( primitiveCalls, actualCalls, totalTime,
                    cumulativeTime, callers) in self.__stats.stats.items():

            # Calc time per call
            if actualCalls == 0:
                timePerCall = 0.0
            else:
                timePerCall = totalTime / actualCalls

            # Calc time per cummulative call
            if primitiveCalls == 0:
                cumulativeTimePerCall = 0.0
            else:
                cumulativeTimePerCall = cumulativeTime / primitiveCalls

            self.__createItem( func[ 0 ], func[ 1 ], func[ 2 ],
                               primitiveCalls, actualCalls, totalTime,
                               cumulativeTime, timePerCall, cumulativeTimePerCall,
                               callers )
        self.__resize()
        self.__table.header().setSortIndicator( 2, Qt.DescendingOrder )
        self.__table.sortItems( 2,
                                self.__table.header().sortIndicatorOrder() )
        return

    def togglePath( self, state ):
        " Switches between showing full paths or file names in locations "
        print "State: " + bool( state )
        return

