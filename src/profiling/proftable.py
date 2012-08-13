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
from PyQt4.QtGui import QTreeWidgetItem, QTreeWidget, QColor, QBrush
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.globals import GlobalData


FLOAT_FORMAT = "%8.6f"
NON_PROJECT_BACKGROUND = QColor( 255, 227, 227 )


class ProfilingTableItem( QTreeWidgetItem ):
    " Profiling table row "

    def __init__( self, items ):
        QTreeWidgetItem.__init__( self, items )

    @staticmethod
    def __getActualCalls( txt ):
        # Returns the actual number of calls as integer
        return int( str( txt ).split( '/' )[ 0 ] )

    def __lt__( self, other ):
        " Integer or string sorting "
        sortColumn = self.treeWidget().sortColumn()
        txt = self.text( sortColumn )
        otherTxt = other.text( sortColumn )

        # The first column may have two value
        if sortColumn == 0:
            return self.__getActualCalls( txt ) < self.__getActualCalls( otherTxt )

        # Try first numeric comparison
        try:
            return float( txt ) < float( otherTxt )
        except:
            pass
        # Fallback to string comparison
        return txt < otherTxt


class ProfileTableViewer( QTreeWidget ):
    " Profiling results table viewer "

    def __init__( self, scriptName, dataFile, parent = None ):
        QTreeWidget.__init__( self, parent )

        self.__script = scriptName
        project = GlobalData().project
        if project.isLoaded():
            self.__projectPrefix = os.path.dirname( project.fileName )
        else:
            self.__projectPrefix = os.path.dirname( scriptName )
        if not self.__projectPrefix.endswith( os.path.sep ):
            self.__projectPrefix += os.path.sep

        self.setAlternatingRowColors( True )
        self.setRootIsDecorated( False )
        self.setItemsExpandable( False )
        self.setSortingEnabled( True )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.setUniformRowHeights( True )
        headerLabels = QStringList()

        headerLabels << "# of calls" << "Total time" << "Per call"
        headerLabels << "Cum. time" << "Per call"
        headerLabels << "File name/line" << "Function" << "# of callers"

        headerItem = QTreeWidgetItem( headerLabels )
        headerItem.setToolTip( 0, "Actual calls/primitive call " \
                                  "(not induced via recursion)" )
        headerItem.setToolTip( 1, "Total time spent in function " \
                                  "(excluding time made in calls " \
                                  "to sub-functions)" )
        headerItem.setToolTip( 2, "Total time divided by number " \
                                  "of actual calls" )
        headerItem.setToolTip( 3, "Total time spent in function and all " \
                                  "subfunctions (from invocation till exit)" )
        headerItem.setToolTip( 4, "Cumulative time divided by number " \
                                  "of promitive calls" )
        headerItem.setToolTip( 5, "Function location" )
        headerItem.setToolTip( 6, "Function name" )
        headerItem.setToolTip( 7, "Function callers" )

        self.setHeaderLabels( headerItem )
        self.connect( self, SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__activated )

        self.__populate( dataFile )
        return

    def __setItemBackground( self, item, fileName ):
        " Sets reddish background "
        if not fileName.startswith( self.__projectPrefix ):
            brush = QBrush( NON_PROJECT_BACKGROUND )
            item.setBackground( 0, brush )
            item.setBackground( 1, brush )
        return

    def __activated( self, item, column ):
        " Triggered when the item is activated "

        # Column with the function address
        address = item.text( 5 )
        if address == "" or ":" not in address:
            return

        try:
            parts = address.split( ':' )
            line = int( parts[ len( parts ) - 1 ] )
            fileName = ":".join( parts[ : -1 ] )
        except:
            logging.error( "Could not parse function location" )
            return

        print "Item activated. file name: '" + fileName + "' line: " + str( line )
        return

    def __getCallLine( self, func, props ):
        " Provides the formatted call line "
        print "Func: " + func
        print "Props: " + props
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
                    tootip += "\n"
                tooltip += self.__getCallLine( func, callers[ func ] )
            item.setToolTip( 7, tooltip )

        self.__setItemBackground( item, funcFileName )
        self.addTopLevelItem( item )
        return

    def __populate( self, dataFile ):
        " Populates the data "

        stats = pstats.Stats( dataFile )
        totalCalls = stats.total_calls
        totalPrimitiveCalls = stats.prim_calls  # The calls was not induced via recursion
        totalTime = stats.total_tt

        for func, ( primitiveCalls, actualCalls, totalTime,
                    cumulativeTime, callers) in stats.stats.items():

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
        return



