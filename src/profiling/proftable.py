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

from PyQt4.QtCore import SIGNAL, QStringList
from PyQt4.QtGui import QTreeWidgetItem, QTreeWidget
from ui.itemdelegates import NoOutlineHeightDelegate


FLOAT_FORMAT = "%8.6f"


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
            return int( txt ) < int( otherTxt )
        except:
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

        self.setAlternatingRowColors( True )
        self.setRootIsDecorated( False )
        self.setItemsExpandable( False )
        self.setSortingEnabled( True )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.setUniformRowHeights( True )
        headerLabels = QStringList()

        headerLabels << "# of calls" << "Total time" << "Total time per call"
        headerLabels << "Cumulative time" << "Cumulative time per call"
        headerLabels << "File name/line" << "Function" << "# of callers"
        self.setHeaderLabels( headerLabels )
        self.connect( self, SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__activated )

        self.__populate( dataFile )
        return


    def __activated( self, item, column ):
        " Triggered when the item is activated "

        print "Item activated"
        return

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
            values << funcFileName + ":" + str( funcLine )
        else:
            values << funcFileName

        values << funcName
        values << str( len( callers ) )
        self.addTopLevelItem( ProfilingTableItem( values ) )
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



