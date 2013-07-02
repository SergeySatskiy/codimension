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

" Profiling results as a graph "

import os, os.path, math
from PyQt4.QtCore import Qt, SIGNAL, QPointF
from PyQt4.QtGui import QWidget, QLabel, QFrame, QPalette, QVBoxLayout, \
                        QGraphicsScene, QGraphicsPathItem, QPainterPath, \
                        QPen, QColor, QPainter, QGraphicsTextItem, \
                        QFont, QFontMetrics, QStyleOptionGraphicsItem, \
                        QStyle, QGraphicsItem, QGraphicsRectItem
from utils.misc import safeRun
from utils.settings import Settings, thirdpartyDir
from utils.globals import GlobalData
from utils.pixmapcache import PixmapCache
from diagram.plaindotparser import getGraphFromPlainDotData
from diagram.importsdgmgraphics import DiagramWidget
from proftable import FLOAT_FORMAT


class FuncConnectionLabel( QGraphicsTextItem ):
    " Connector label "

    def __init__( self, edge ):
        text = edge.label.replace( '\\n', '\n' )
        QGraphicsTextItem.__init__( self, text )

        font = QFont( "Arial", 10 )
        self.setFont( font )

        metric = QFontMetrics( font )
        rec = metric.boundingRect( 0, 0, 10000, 10000, Qt.AlignCenter, text )

        self.setPos( edge.labelX - rec.width() / 2,
                     edge.labelY - rec.height() / 2 )

        # To make double click not delivered
        self.setFlag( QGraphicsItem.ItemIsSelectable, False )
        return

    def paint( self, painter, option, widget ):
        """ Draws the edge text """

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem( option )
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected

        QGraphicsTextItem.paint( self, painter, itemOption, widget )
        return


class FuncConnection( QGraphicsPathItem ):
    " Connection between functions "

    def __init__( self, edge ):
        QGraphicsPathItem.__init__( self )
        self.__edge = edge

        startPoint = QPointF( edge.points[ 0 ][ 0 ], edge.points[ 0 ][ 1 ] )
        painterPath = QPainterPath( startPoint )

        index = 1
        while index + 3 <= len( edge.points ):
            painterPath.cubicTo(edge.points[index][0],  edge.points[index][1],
                                edge.points[index+1][0],edge.points[index+1][1],
                                edge.points[index+2][0],edge.points[index+2][1])
            index = index + 3
        if index + 2 <= len( edge.points ):
            painterPath.quadTo(edge.points[index+1][0], edge.points[index+1][1],
                               edge.points[index+2][0], edge.points[index+2][1])
            index = index + 2

        if index + 1 <= len( edge.points ):
            painterPath.lineTo(edge.points[index+1][0], edge.points[index+1][1])

        if edge.head != edge.tail:
            lastIndex = len( edge.points ) - 1
            self.addArrow( painterPath,
                           edge.points[lastIndex-1][0],
                           edge.points[lastIndex-1][1],
                           edge.points[lastIndex][0],
                           edge.points[lastIndex][1] )

        self.setPath( painterPath )
        return

    def addArrow( self, painterPath, startX, startY, endX, endY ):
        """
        Add arrows to the edges
        http://kapo-cpp.blogspot.com/2008/10/drawing-arrows-with-cairo.html
        """

        arrowLength  = 12.0
        arrowDegrees = 0.15      # Radian

        angle = math.atan2( endY - startY, endX - startX ) + math.pi
        arrowX1 = endX + arrowLength * math.cos(angle - arrowDegrees)
        arrowY1 = endY + arrowLength * math.sin(angle - arrowDegrees)
        arrowX2 = endX + arrowLength * math.cos(angle + arrowDegrees)
        arrowY2 = endY + arrowLength * math.sin(angle + arrowDegrees)

        painterPath.moveTo( endX, endY )
        painterPath.lineTo( arrowX1, arrowY1 )
        painterPath.moveTo( endX, endY )
        painterPath.lineTo( arrowX2, arrowY2 )

        return

    def paint( self, painter, option, widget ):
        """ Draws a curve and then adds an arrow """

        pen = QPen( QColor( 0, 0, 0) )
        pen.setWidth( 2 )
        self.setPen( pen )

        painter.setRenderHint( QPainter.Antialiasing, True )
        QGraphicsPathItem.paint( self, painter, option, widget )
        return


class Function( QGraphicsRectItem ):
    " Rectangle for a function "

    def __init__( self, node, fileName, lineNumber, outside ):
        QGraphicsRectItem.__init__( self )
        self.__node = node
        self.__fileName = fileName
        self.__lineNumber = lineNumber
        self.__outside = outside

        posX = node.posX - node.width / 2.0
        posY = node.posY - node.height / 2.0
        QGraphicsRectItem.__init__( self, posX, posY,
                                    node.width, node.height )

        self.setRectanglePen()

        # node.color is like "#fe0400"
        if node.color.startswith( "#" ):
            color = QColor( int( node.color[ 1:3 ], 16 ),
                            int( node.color[ 3:5 ], 16 ),
                            int( node.color[ 5: ], 16 ) )
        else:
            color = QColor( 220, 255, 220 )
        self.setBrush( color )

        # To make item selectable
        self.setFlag( QGraphicsItem.ItemIsSelectable,
                      os.path.isabs( self.__fileName ) and \
                      self.__lineNumber > 0 )

        # Set tooltip as a function docstring
        if fileName != "" and lineNumber != 0:
            self.setToolTip( \
                    GlobalData().getFileLineDocstring( fileName, lineNumber ) )
        return

    def setRectanglePen( self ):
        " Sets the diagram pen "
        pen = QPen( QColor( 0, 0, 0) )
        pen.setWidth( 2 )
        pen.setJoinStyle( Qt.RoundJoin )
        self.setPen( pen )
        return

    def paint( self, painter, option, widget ):
        """ Draws a filled rectangle and then adds a title """

        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem( option )
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected

        # Draw the rectangle
        pen = painter.pen()
        pen.setJoinStyle( Qt.RoundJoin )
        painter.setPen( pen )
        QGraphicsRectItem.paint( self, painter, itemOption, widget )

        # Draw text over the rectangle
        font = QFont( "Arial", 10 )
        painter.setFont( font )
        painter.setPen( QPen( QColor( 255, 255, 255 ) ) )
        painter.drawText( self.__node.posX - self.__node.width / 2.0,
                          self.__node.posY - self.__node.height / 2.0,
                          self.__node.width, self.__node.height,
                          Qt.AlignCenter,
                          self.__node.label.replace( '\\n', '\n' ) )

        if self.__outside:
            pixmap = PixmapCache().getPixmap( "nonprojectentrydgm.png" )
            pixmapPosX = self.__node.posX - self.__node.width / 2.0 + 2
            pixmapPosY = self.__node.posY + self.__node.height / 2.0 - \
                         pixmap.height() - 2
            painter.setRenderHint( QPainter.SmoothPixmapTransform )
            painter.drawPixmap( pixmapPosX, pixmapPosY, pixmap )
        return

    def mouseDoubleClickEvent( self, event ):
        " Open the clicked file if it could be opened "
        if self.__lineNumber == 0:
            return
        if not os.path.isabs( self.__fileName ):
            return

        GlobalData().mainWindow.openFile( self.__fileName,
                                          self.__lineNumber )
        return


# The node label has attached nodeID to it as follows:
# <label>--id
def extractNodeID( label ):
    " Extracts the ID from the label "
    parts = label.split( "--" )
    length = len( parts )
    if length == 1:
        return -1, label
    try:
        node_id = int( parts[ length - 1 ] )
        return node_id, "--".join( parts[ :-1 ] )
    except:
        return -1, label



class ProfileGraphViewer( QWidget ):
    " Profiling results as a graph "

    def __init__( self, scriptName, params, reportTime,
                        dataFile, stats, parent = None ):
        QWidget.__init__( self, parent )

        self.__dataFile = dataFile
        self.__script = scriptName
        self.__reportTime = reportTime
        self.__params = params
        self.__stats = stats

        project = GlobalData().project
        if project.isLoaded():
            self.__projectPrefix = os.path.dirname( project.fileName )
        else:
            self.__projectPrefix = os.path.dirname( scriptName )
        if not self.__projectPrefix.endswith( os.path.sep ):
            self.__projectPrefix += os.path.sep

        self.__createLayout()
        self.__getDiagramLayout()

        self.__viewer.setScene( self.__scene )
        return

    def setFocus( self ):
        " Sets the focus properly "
        self.__viewer.setFocus()
        return

    def __isOutsideItem( self, fileName ):
        " Detects if the record should be shown as an outside one "
        return not fileName.startswith( self.__projectPrefix )

    def __createLayout( self ):
        " Creates the widget layout "
        totalCalls = self.__stats.total_calls
        totalPrimitiveCalls = self.__stats.prim_calls  # The calls were not induced via recursion
        totalTime = self.__stats.total_tt

        summary = QLabel( "<b>Script:</b> " + self.__script + " " + self.__params.arguments + "<br>" \
                          "<b>Run at:</b> " + self.__reportTime + "<br>" + \
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

        self.__scene = QGraphicsScene()
        self.__viewer = DiagramWidget()
        self.connect( self.__viewer, SIGNAL( 'ESCPressed' ), self.__onESC )

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins( 0, 0, 0, 0 )
        vLayout.setSpacing( 0 )
        vLayout.addWidget( summary )
        vLayout.addWidget( self.__viewer )

        self.setLayout( vLayout )
        return


    def __getDiagramLayout( self ):
        " Runs external tools to get the diagram layout "

        # Preparation: build a map of func ID -> fileName + line
        funcMap = {}
        index = 0
        for func, props in self.__stats.stats.items():
            funcMap[ index ] = ( func[ 0 ], func[ 1 ] )
            index += 1

        # First step is to run grpof2dot
        gprof2dot = thirdpartyDir + "gprof2dot" + os.path.sep + "gprof2dot.py"
        outputFile = self.__dataFile + ".dot"
        nodeLimit = Settings().profileNodeLimit
        edgeLimit = Settings().profileEdgeLimit
        dotSpec = safeRun( [ gprof2dot, '-n', str( nodeLimit ),
                             '-e', str( edgeLimit ),
                             '-f', 'pstats', '-o', outputFile,
                             self.__dataFile ] )
        graphDescr = safeRun( [ "dot", "-Tplain", outputFile ] )
        graph = getGraphFromPlainDotData( graphDescr )
        graph.normalize( self.physicalDpiX(), self.physicalDpiY() )

        self.__scene.clear()
        self.__scene.setSceneRect( 0, 0, graph.width, graph.height )

        for edge in graph.edges:
            self.__scene.addItem( FuncConnection( edge ) )
            if edge.label != "":
                self.__scene.addItem( FuncConnectionLabel( edge ) )

        for node in graph.nodes:
            fileName = ""
            lineNumber = 0
            isOutside = True
            nodeID, newLabel = extractNodeID( node.label )
            if nodeID != -1:
                node.label = newLabel

                # Now, detect the file name/line number and
                # if it belongs to the project
                ( fileName, lineNumber ) = funcMap[ nodeID ]
            self.__scene.addItem( Function( node, fileName, lineNumber,
                                            self.__isOutsideItem( fileName ) ) )

        return

    def __onESC( self ):
        " Triggered when ESC is clicked "
        self.emit( SIGNAL( 'ESCPressed' ) )
        return

    def onCopy( self ):
        " Copies the diagram to the exchange buffer "
        self.__viewer.onCopy()
        return

    def onSaveAs( self, fileName ):
        " Saves the diagram to a file "
        self.__viewer.onSaveAs( fileName )
        return

    def zoomIn( self ):
        " Triggered on the 'zoom in' button "
        self.__viewer.zoomIn()
        return

    def zoomOut( self ):
        " Triggered on the 'zoom out' button "
        self.__viewer.zoomOut()
        return

    def resetZoom( self ):
        " Triggered on the 'zoom reset' button "
        self.__viewer.resetZoom()
        return

