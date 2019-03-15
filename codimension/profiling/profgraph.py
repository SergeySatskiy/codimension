# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Profiling results as a graph"""

from subprocess import PIPE, Popen
import os
import os.path
import math
import io
import gprof2dot
from ui.qt import (Qt, QPointF, pyqtSignal, QFont, QPen, QColor,
                   QFontMetrics, QPainterPath, QPainter, QWidget, QLabel,
                   QVBoxLayout, QGraphicsScene, QGraphicsPathItem,
                   QStyle, QGraphicsTextItem, QStyleOptionGraphicsItem,
                   QGraphicsItem, QGraphicsRectItem, QSizePolicy)
from utils.settings import Settings
from utils.globals import GlobalData
from utils.pixmapcache import getPixmap
from utils.colorfont import getLabelStyle
from diagram.plaindotparser import getGraphFromPlainDotData
from diagram.importsdgmgraphics import DiagramWidget
from .proftable import FLOAT_FORMAT


DEFAULT_FONT = QFont("Arial", 10)

class FuncConnectionLabel(QGraphicsTextItem):

    """Connector label"""

    def __init__(self, edge, edgeFont):
        text = edge.label.replace('\\n', '\n')
        QGraphicsTextItem.__init__(self, text)

        if edgeFont:
            self.setFont(edgeFont)
        else:
            self.setFont(DEFAULT_FONT)

        metric = QFontMetrics(self.font())
        rec = metric.boundingRect(0, 0, 10000, 10000, Qt.AlignCenter, text)

        self.setPos(edge.labelX - rec.width() / 2,
                    edge.labelY - rec.height() / 2)

        # To make double click not delivered
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    def paint(self, painter, option, widget):
        """ Draws the edge text """
        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem(option)
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected

        QGraphicsTextItem.paint(self, painter, itemOption, widget)


class FuncConnection(QGraphicsPathItem):

    """Connection between functions"""

    def __init__(self, edge):
        QGraphicsPathItem.__init__(self)
        self.__edge = edge

        startPoint = QPointF(edge.points[0][0], edge.points[0][1])
        painterPath = QPainterPath(startPoint)

        index = 1
        while index + 3 <= len(edge.points):
            painterPath.cubicTo(
                edge.points[index][0], edge.points[index][1],
                edge.points[index + 1][0], edge.points[index + 1][1],
                edge.points[index + 2][0], edge.points[index + 2][1])
            index = index + 3
        if index + 2 <= len(edge.points):
            painterPath.quadTo(
                edge.points[index + 1][0], edge.points[index + 1][1],
                edge.points[index + 2][0], edge.points[index + 2][1])
            index = index + 2

        if index + 1 <= len(edge.points):
            painterPath.lineTo(edge.points[index + 1][0],
                               edge.points[index + 1][1])

        if edge.head != edge.tail:
            lastIndex = len(edge.points) - 1
            self.addArrow(painterPath,
                          edge.points[lastIndex - 1][0],
                          edge.points[lastIndex - 1][1],
                          edge.points[lastIndex][0],
                          edge.points[lastIndex][1])
        self.setPath(painterPath)

    def addArrow(self, painterPath, startX, startY, endX, endY):
        """Add arrows to the edges
           http://kapo-cpp.blogspot.com/2008/10/drawing-arrows-with-cairo.html
        """
        arrowLength = 12.0
        arrowDegrees = 0.15      # Radian

        angle = math.atan2(endY - startY, endX - startX) + math.pi
        arrowX1 = endX + arrowLength * math.cos(angle - arrowDegrees)
        arrowY1 = endY + arrowLength * math.sin(angle - arrowDegrees)
        arrowX2 = endX + arrowLength * math.cos(angle + arrowDegrees)
        arrowY2 = endY + arrowLength * math.sin(angle + arrowDegrees)

        painterPath.moveTo(endX, endY)
        painterPath.lineTo(arrowX1, arrowY1)
        painterPath.moveTo(endX, endY)
        painterPath.lineTo(arrowX2, arrowY2)

    def paint(self, painter, option, widget):
        """Draws a curve and then adds an arrow"""
        pen = QPen(QColor(0, 0, 0))
        pen.setWidth(2)
        self.setPen(pen)

        painter.setRenderHint(QPainter.Antialiasing, True)
        QGraphicsPathItem.paint(self, painter, option, widget)


class Function(QGraphicsRectItem):

    """Rectangle for a function"""

    def __init__(self, node, fileName, lineNumber, outside, nodeFont):
        QGraphicsRectItem.__init__(self)
        self.__node = node
        self.__fileName = fileName
        self.__lineNumber = lineNumber
        self.__outside = outside

        self.__font = DEFAULT_FONT
        if nodeFont:
            self.__font = nodeFont

        posX = node.posX - node.width / 2.0
        posY = node.posY - node.height / 2.0
        QGraphicsRectItem.__init__(self, posX, posY,
                                   node.width, node.height)

        self.setRectanglePen()

        # node.color is like "#fe0400"
        if node.color.startswith("#"):
            color = QColor(int(node.color[1:3], 16),
                           int(node.color[3:5], 16),
                           int(node.color[5:], 16))
        else:
            color = QColor(220, 255, 220)
        self.setBrush(color)

        # To make item selectable
        self.setFlag(QGraphicsItem.ItemIsSelectable,
                     os.path.isabs(self.__fileName) and
                     self.__lineNumber > 0)

        # Set tooltip as a function docstring
        if fileName != "" and lineNumber != 0:
            self.setToolTip(
                GlobalData().getFileLineDocstring(fileName, lineNumber))

    def setRectanglePen(self):
        """Sets the diagram pen"""
        pen = QPen(QColor(0, 0, 0))
        pen.setWidth(2)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)

    def paint(self, painter, option, widget):
        """Draws a filled rectangle and then adds a title"""
        # Hide the dotted outline
        itemOption = QStyleOptionGraphicsItem(option)
        if itemOption.state & QStyle.State_Selected != 0:
            itemOption.state = itemOption.state & ~QStyle.State_Selected

        # Draw the rectangle
        pen = painter.pen()
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        QGraphicsRectItem.paint(self, painter, itemOption, widget)

        # Draw text over the rectangle
        painter.setFont(self.__font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(self.__node.posX - self.__node.width / 2.0,
                         self.__node.posY - self.__node.height / 2.0,
                         self.__node.width, self.__node.height,
                         Qt.AlignCenter,
                         self.__node.label.replace('\\n', '\n'))

        if self.__outside:
            pixmap = getPixmap("nonprojectentrydgm.png")
            pixmapPosX = self.__node.posX - self.__node.width / 2.0 + 2
            pixmapPosY = self.__node.posY + self.__node.height / 2.0 - \
                pixmap.height() - 2
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(pixmapPosX, pixmapPosY, pixmap)

    def mouseDoubleClickEvent(self, _):
        """Open the clicked file if it could be opened"""
        if self.__lineNumber == 0:
            return
        if not os.path.isabs(self.__fileName):
            return

        GlobalData().mainWindow.openFile(self.__fileName,
                                         self.__lineNumber)


class ProfileGraphViewer(QWidget):

    """Profiling results as a graph"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, scriptName, params, reportTime,
                 dataFile, stats, parent=None):
        QWidget.__init__(self, parent)

        self.__dataFile = dataFile
        self.__script = scriptName
        self.__reportTime = reportTime
        self.__params = params
        self.__stats = stats

        project = GlobalData().project
        if project.isLoaded():
            self.__projectPrefix = os.path.dirname(project.fileName)
        else:
            self.__projectPrefix = os.path.dirname(scriptName)
        if not self.__projectPrefix.endswith(os.path.sep):
            self.__projectPrefix += os.path.sep

        self.__createLayout()
        self.__getDiagramLayout()

        self.__viewer.setScene(self.__scene)

    def setFocus(self):
        """Sets the focus properly"""
        self.__viewer.setFocus()

    def __isOutsideItem(self, fileName):
        """Detects if the record should be shown as an outside one"""
        return not fileName.startswith(self.__projectPrefix)

    def __createLayout(self):
        """Creates the widget layout"""
        totalCalls = self.__stats.total_calls
        # The calls were not induced via recursion
        totalPrimitiveCalls = self.__stats.prim_calls
        totalTime = self.__stats.total_tt

        txt = "<b>Script:</b> " + self.__script + " " + \
              self.__params['arguments'] + "<br/>" \
              "<b>Run at:</b> " + self.__reportTime + "<br/>" + \
              str(totalCalls) + " function calls (" + \
              str(totalPrimitiveCalls) + " primitive calls) in " + \
              FLOAT_FORMAT % totalTime + " CPU seconds"
        summary = QLabel(txt)
        summary.setToolTip(txt)
        summary.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        summary.setStyleSheet('QLabel {' + getLabelStyle(self) + '}')

        self.__scene = QGraphicsScene()
        self.__viewer = DiagramWidget()
        self.__viewer.sigEscapePressed.connect(self.__onESC)

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(summary)
        vLayout.addWidget(self.__viewer)

        self.setLayout(vLayout)

    @staticmethod
    def __getDotFont(parts):
        """Provides a QFont object if a font spec is found"""
        for part in parts:
            if 'fontname=' in part:
                fontName = part.replace('fontname=', '')
                fontName = fontName.replace('[', '')
                fontName = fontName.replace(']', '')
                fontName = fontName.replace(',', '')
                return QFont(fontName)
        return None

    def __postprocessFullDotSpec(self, dotSpec):
        """Removes the arrow size, extracts tooltips, extracts font info"""
        nodeFont = None
        edgeFont = None
        tooltips = {}
        processed = []

        for line in dotSpec.splitlines():
            parts = line.split()
            lineModified = False
            if parts:
                if parts[0] == 'node':
                    # need to extract the fontname
                    nodeFont = self.__getDotFont(parts)
                elif parts[0] == 'edge':
                    # need to extract the fontname
                    edgeFont = self.__getDotFont(parts)
                elif parts[0].isdigit():
                    if parts[1] == '->':
                        # certain edge spec: replace arrowsize and font size
                        for index, part in enumerate(parts):
                            if part.startswith('[arrowsize='):
                                modified = parts[:]
                                modified[index] = '[arrowsize="0.0",'
                                processed.append(' '.join(modified))
                            elif part.startswith('fontsize='):
                                size = float(part.split('"')[1])
                                if edgeFont:
                                    edgeFont.setPointSize(size)
                        lineModified = True
                    elif parts[1].startswith('['):
                        # certain node spec: pick the tooltip and font size
                        lineno = None
                        for part in parts:
                            if part.startswith('tooltip='):
                                nodePath = part.split('"')[1]
                                pathLine = nodePath + ':' + str(lineno)
                                tooltips[int(parts[0])] = pathLine
                            elif part.startswith('fontsize='):
                                size = float(part.split('"')[1])
                                if nodeFont:
                                    nodeFont.setPointSize(size)
                            elif part.startswith('label='):
                                try:
                                    lineno = int(part.split(':')[1])
                                except:
                                    pass
            if not lineModified:
                processed.append(line)

        return '\n'.join(processed), tooltips, nodeFont, edgeFont


    def __rungprof2dot(self):
        """Runs gprof2dot which produces a full dot spec"""
        nodeLimit = Settings().getProfilerSettings().nodeLimit
        edgeLimit = Settings().getProfilerSettings().edgeLimit
        with io.StringIO() as buf:
            gprofParser = gprof2dot.PstatsParser(self.__dataFile)
            profileData = gprofParser.parse()
            profileData.prune(nodeLimit / 100.0, edgeLimit / 100.0, False, False)

            dot = gprof2dot.DotWriter(buf)
            dot.strip = False
            dot.wrap = False
            dot.graph(profileData, gprof2dot.TEMPERATURE_COLORMAP)

            output = buf.getvalue()
        return self.__postprocessFullDotSpec(output)

    def __getDiagramLayout(self):
        """Runs external tools to get the diagram layout"""
        fullDotSpec, tooltips, nodeFont, edgeFont = self.__rungprof2dot()

        dotProc = Popen(["dot", "-Tplain"],
                        stdin=PIPE, stdout=PIPE, bufsize=1)
        graphDescr = dotProc.communicate(
            fullDotSpec.encode('utf-8'))[0].decode('utf-8')

        graph = getGraphFromPlainDotData(graphDescr)
        graph.normalize(self.physicalDpiX(), self.physicalDpiY())

        self.__scene.clear()
        self.__scene.setSceneRect(0, 0, graph.width, graph.height)

        for edge in graph.edges:
            self.__scene.addItem(FuncConnection(edge))
            if edge.label != "":
                self.__scene.addItem(FuncConnectionLabel(edge, edgeFont))

        for node in graph.nodes:
            fileName = ""
            lineNumber = 0

            try:
                nodeNameAsInt = int(node.name)
                if nodeNameAsInt in tooltips:
                    parts = tooltips[nodeNameAsInt].rsplit(':', 1)
                    fileName = parts[0]
                    if parts[1].isdigit():
                        lineNumber = int(parts[1])
            except:
                pass

            self.__scene.addItem(Function(node, fileName, lineNumber,
                                          self.__isOutsideItem(fileName),
                                          nodeFont))

    def __onESC(self):
        """Triggered when ESC is clicked"""
        self.sigEscapePressed.emit()

    def onCopy(self):
        """Copies the diagram to the exchange buffer"""
        self.__viewer.onCopy()

    def onSaveAs(self, fileName):
        """Saves the diagram to a file"""
        self.__viewer.onSaveAs(fileName)

    def zoomIn(self):
        """Triggered on the 'zoom in' button"""
        self.__viewer.zoomIn()

    def zoomOut(self):
        """Triggered on the 'zoom out' button"""
        self.__viewer.zoomOut()

    def resetZoom(self):
        """Triggered on the 'zoom reset' button"""
        self.__viewer.resetZoom()
