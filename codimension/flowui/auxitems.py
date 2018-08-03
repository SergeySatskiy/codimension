# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Auxiliary items on a canvas which do not derive from CellElement"""


from sys import maxsize
import os.path
from ui.qt import (QPen, QBrush, QPainterPath, Qt, QGraphicsSvgItem,
                   QGraphicsSimpleTextItem, QGraphicsRectItem, QLabel,
                   QGraphicsPathItem, QColor, QFrame,
                   QVBoxLayout, QPalette, QApplication)
from utils.globals import GlobalData


class SVGItem(QGraphicsSvgItem):

    """Wrapper for an SVG items on the control flow"""

    def __init__(self, fName, ref):
        self.__fName = fName
        QGraphicsSvgItem.__init__(self, self.__getPath(fName))
        self.__scale = 0
        self.ref = ref

    def __getPath(self, fName):
        """Tries to resolve the given file name"""
        try:
            from utils.pixmapcache import PIXMAP_CACHE
            path = PIXMAP_CACHE.getSearchPath() + fName
            if os.path.exists(path):
                return path
        except:
            pass

        if os.path.exists(fName):
            return fName
        return ''

    def setHeight(self, height):
        """Scales the svg item to the required height"""
        rectHeight = float(self.boundingRect().height())
        if rectHeight != 0.0:
            self.__scale = float(height) / rectHeight
            self.setScale(self.__scale)

    def setWidth(self, width):
        """Scales the svg item to the required width"""
        rectWidth = float(self.boundingRect().width())
        if rectWidth != 0.0:
            self.__scale = float(width) / rectWidth
            self.setScale(self.__scale)

    def height(self):
        """Provides the height"""
        return self.boundingRect().height() * self.__scale

    def width(self):
        """Provides the width"""
        return self.boundingRect().width() * self.__scale

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return "SVG item for " + self.__fName

    def isProxyItem(self):
        """True if it is a proxy item"""
        return True

    def getProxiedItem(self):
        """Provides the real item for the proxy one"""
        return self.ref

    def isComment(self):
        """True if it is a comment"""
        return False

    def scopedItem(self):
        """True if it is a scoped item"""
        return False


class BadgeItem(QGraphicsRectItem):

    """Serves the scope badges"""

    def __init__(self, ref, text):
        QGraphicsRectItem.__init__(self)
        self.ref = ref
        self.__text = text

        self.__textRect = ref.canvas.settings.badgeFontMetrics.boundingRect(
            0, 0,  maxsize, maxsize, 0, text)
        self.__hSpacing = 2
        self.__vSpacing = 1
        self.__radius = 2

        self.__width = self.__textRect.width() + 2 * self.__hSpacing
        self.__height = self.__textRect.height() + 2 * self.__vSpacing

        self.__bgColor = ref.canvas.settings.badgeBGColor
        self.__fgColor = ref.canvas.settings.badgeFGColor
        self.__frameColor = ref.canvas.settings.badgeLineColor
        self.__font = ref.canvas.settings.badgeFont
        self.__needRect = True

    def setBGColor(self, bgColor):
        """Sets the background color"""
        self.__bgColor = bgColor

    def setFGColor(self, fgColor):
        """Sets the foreground color"""
        self.__fgColor = fgColor

    def setFrameColor(self, frameColor):
        """Sets the frame color"""
        self.__frameColor = frameColor

    def setNeedRectangle(self, value):
        """Sets the need rectangle flag"""
        self.__needRect = value

    def setFont(self, font):
        """Sets the font"""
        self.__font = font

    def width(self):
        """Provides the width"""
        return self.__width

    def height(self):
        """Provides the height"""
        return self.__height

    def text(self):
        """Provides the text"""
        return self.__text

    def moveTo(self, x, y):
        """Moves to the specified position"""
        # This is a mistery. I do not understand why I need to divide by 2.0
        # however this works. I tried various combinations of initialization,
        # setting the position and mapping. Nothing works but ../2.0. Sick!
        self.setPos(float(x) / 2.0, float(y) / 2.0)
        self.setRect(float(x) / 2.0, float(y) / 2.0,
                     self.__width, self.__height)

    def withinHeader(self):
        """True if it is within a header"""
        if self.ref.kind in [self.ref.ELSE_SCOPE,
                             self.ref.FINALLY_SCOPE,
                             self.ref.TRY_SCOPE]:
            return True
        if self.ref.kind == self.ref.EXCEPT_SCOPE:
            return self.ref.ref.clause is None
        return False

    def paint(self, painter, option, widget):
        """Paints the badge item"""
        s = self.ref.canvas.settings

        if self.__needRect:
            pen = QPen(self.__frameColor)
            pen.setWidth(s.badgeLineWidth)
            painter.setPen(pen)
            brush = QBrush(self.__bgColor)
            painter.setBrush(brush)
            painter.drawRoundedRect(self.x(), self.y(),
                                    self.__width, self.__height,
                                    self.__radius, self.__radius)

        pen = QPen(self.__fgColor)
        painter.setPen(pen)
        painter.setFont(self.__font)
        painter.drawText(self.x() + self.__hSpacing,
                         self.y() + self.__vSpacing,
                         self.__textRect.width(),
                         self.__textRect.height(),
                         Qt.AlignLeft, self.__text)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return "Badge item '" + self.__text + "'"

    def isProxyItem(self):
        """True if it is a proxy item"""
        return True

    def getProxiedItem(self):
        """Provides the real item for a proxy one"""
        return self.ref

    def isComment(self):
        """True if it is a comment"""
        return False

    def scopedItem(self):
        """True if it is a scoped item"""
        return False



class Connector(QGraphicsPathItem):

    """Implementation of a connector item"""

    def __init__(self, settings, x1, y1, x2, y2):
        QGraphicsPathItem.__init__(self)
        self.__settings = settings

        path = QPainterPath()
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)
        self.setPath(path)

        self.penStyle = None
        self.penColor = None
        self.penWidth = None

    def paint(self, painter, option, widget):
        """Paints the connector"""
        color = self.__settings.lineColor
        if self.penColor:
            color = self.penColor
        width = self.__settings.lineWidth
        if self.penWidth:
            width = self.penWidth

        pen = QPen(color)
        pen.setWidth(width)
        pen.setCapStyle(Qt.FlatCap)
        pen.setJoinStyle(Qt.RoundJoin)
        if self.penStyle:
            pen.setStyle(self.penStyle)
        self.setPen(pen)
        QGraphicsPathItem.paint(self, painter, option, widget)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Connector item'

    def isProxyItem(self):
        """True if it is a proxy item"""
        return True

    def getProxiedItem(self):
        """Provides the real item for a proxy one"""
        return None

    def isComment(self):
        """True if it is a comment"""
        return False

    def scopedItem(self):
        """True if it is a scoped item"""
        return False



class RubberBandItem(QGraphicsRectItem):

    """Custom rubber band for selection"""

    def __init__(self, settings):
        QGraphicsRectItem.__init__(self)
        self.__settings = settings
        self.__x = None
        self.__y = None
        self.__width = None
        self.__height = None

    def setGeometry(self, rect):
        # This is a mistery. I do not understand why I need to divide by 2.0
        # however this works. I tried various combinations of initialization,
        # setting the position and mapping. Nothing works but ../2.0. Sick!
        self.__x = rect.x() / 2.0
        self.__y = rect.y() / 2.0
        self.__width = rect.width()
        self.__height = rect.height()

        self.setPos(self.__x, self.__y)
        self.setRect(self.__x, self.__y, self.__width, self.__height)

        self.update()

    def paint(self, painter, option, widget):
        """Paints the rubber band"""
        pen = QPen(self.__settings.rubberBandBorderColor)
        painter.setPen(pen)
        brush = QBrush(self.__settings.rubberBandFGColor)
        painter.setBrush(brush)
        painter.drawRect(self.__x, self.__y,
                         self.__width, self.__height)

    def isProxyItem(self):
        """True if it is a proxy item"""
        return True

    def getProxiedItem(self):
        """Provides the real item for a proxy one"""
        return None

    def isComment(self):
        """True if it is a comment"""
        return False

    def scopedItem(self):
        """True if it is a scoped item"""
        return False



class Text(QGraphicsSimpleTextItem):

    """Implementation of a text item"""

    def __init__(self, settings, text):
        QGraphicsSimpleTextItem.__init__(self)
        self.__settings = settings

        self.setFont(settings.badgeFont)
        self.setText(text)

        self.color = None

    def paint(self, painter, option, widget):
        """Paints the text item"""
        color = self.__settings.lineColor
        if self.color:
            color = self.color

        self.setBrush(QBrush(color))
        QGraphicsSimpleTextItem.paint(self, painter, option, widget)

    def getSelectTooltip(self):
        """Provides the tooltip"""
        return 'Text item'

    def isProxyItem(self):
        """True if it is a proxy item"""
        return True

    def getProxiedItem(self):
        """Provides the real item for a proxy one"""
        return None

    def isComment(self):
        """True if it is a comment"""
        return False

    def scopedItem(self):
        """True if it is a scoped item"""
        return False


class GroupCornerControl(QGraphicsRectItem):

    """Expanded group top left corner control"""

    def __init__(self, ref):
        QGraphicsRectItem.__init__(self)
        self.ref = ref

        settings = self.ref.canvas.settings
        self.__width = settings.openGroupHSpacer * 2 - 1
        self.__height = settings.openGroupVSpacer * 2 - 1

        self.setAcceptHoverEvents(True)

    def moveTo(self, xPos, yPos):
        """Moves to the specified position"""
        settings = self.ref.canvas.settings

        # This is a mistery. I do not understand why I need to divide by 2.0
        # however this works. I tried various combinations of initialization,
        # setting the position and mapping. Nothing works but ../2.0. Sick!
        self.setPos((float(xPos) + settings.openGroupHSpacer - 1) / 2.0,
                    (float(yPos) + settings.openGroupVSpacer - 1) / 2.0)
        self.setRect(self.x(), self.y(),
                     self.__width, self.__height)

    def paint(self, painter, option, widget):
        """Paints the control"""
        settings = self.ref.canvas.settings

        pen = QPen(settings.groupControlBorderColor)
        pen.setStyle(Qt.SolidLine)
        pen.setWidth(1)
        painter.setPen(pen)

        brush = QBrush(settings.groupControlBGColor)
        painter.setBrush(brush)

        painter.drawRoundedRect(self.x(), self.y(),
                                self.__width, self.__height,
                                1, 1)

    def hoverEnterEvent(self, event):
        """Handles the mouse in event"""
        del event
        self.ref.setHighlight(True)
        if self.ref.getTitle():
            groupTitlePopup.setTitleForGroup(self.ref)
            groupTitlePopup.show(self)

    def hoverLeaveEvent(self, event):
        """Handles the mouse out event"""
        del event
        self.ref.setHighlight(False)
        groupTitlePopup.hide()

    def isProxyItem(self):
        """True if it is a proxy item"""
        return True

    def getProxiedItem(self):
        """Provides the real item for a proxy one"""
        return self.ref

    def isComment(self):
        """True if it is a comment"""
        return False

    def scopedItem(self):
        """True if it is a scoped item"""
        return False



class GroupTitlePopup(QFrame):

    """Frameless panel to show the group title"""

    def __init__(self, parent):
        QFrame.__init__(self, parent)

        self.setWindowFlags(Qt.SplashScreen |
                            Qt.WindowStaysOnTopHint |
                            Qt.X11BypassWindowManagerHint)

        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)

        self.__titleLabel = None
        self.__createLayout()

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.__titleLabel = QLabel()
        self.__titleLabel.setAutoFillBackground(True)
        self.__titleLabel.setFrameShape(QFrame.StyledPanel)
        self.__titleLabel.setStyleSheet('padding: 2px')
        verticalLayout.addWidget(self.__titleLabel)

    def setTitleForGroup(self, group):
        """Sets the title of the group"""
        self.__titleLabel.setFont(group.canvas.settings.monoFont)
        self.__titleLabel.setText(group.getTitle())

    def resize(self, controlItem):
        """Moves the popup to the proper position"""
        # calculate the positions above the group
        # Taken from here:
        # https://stackoverflow.com/questions/9871749/find-screen-position-of-a-qgraphicsitem
        scene = controlItem.ref.scene()
        view = scene.views()[0]
        sceneP = controlItem.mapToScene(controlItem.boundingRect().topLeft())
        viewP = view.mapFromScene(sceneP)
        pos = view.viewport().mapToGlobal(viewP)

        self.move(pos.x(), pos.y() - self.height() - 2)
        QApplication.processEvents()

    def show(self, controlItem):
        """Shows the title above the group control"""
        # Use the palette from the group
        bgColor, fgColor, _ = controlItem.ref.colors()
        palette = self.__titleLabel.palette()
        palette.setColor(QPalette.Background, bgColor)
        palette.setColor(QPalette.Foreground, fgColor)
        self.__titleLabel.setPalette(palette)

        # That's a trick: resizing works correctly only if the item is shown
        # So move it outside of the screen, show it so it is invisible and then
        # resize and move to the proper position
        screenHeight = GlobalData().screenHeight
        self.move(0, screenHeight + 128)
        QFrame.show(self)
        QApplication.processEvents()
        self.resize(controlItem)

# One instance use for all
groupTitlePopup = GroupTitlePopup(None)
