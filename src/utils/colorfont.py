#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2016-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""QT color and font general utils"""

from PyQt5.QtGui import QColor, QFont, QFontComboBox


def checkColorRange(value):
    """Checks the color range"""
    if value < 0 or value > 255:
        raise Exception("Invalid color value")


def buildColor(color):
    """Four options are supported:
       #hhhhhh             hexadecimal rgb
       #hhhhhhhh           hexadecimal rgb and alpha
       ddd,ddd,ddd         decimal rgb
       ddd,ddd,ddd,ddd     decimal rgb and alpha"""
    if color.startswith('#'):
        color = color[1:]
        length = len(color)
        if length not in [6, 8]:
            raise Exception("Invalid hexadecimal color format: #" + color)

        try:
            # The most common case
            r = int(color[0:2], 16)
            checkColorRange(r)
            g = int(color[2:4], 16)
            checkColorRange(g)
            b = int(color[4:6], 16)
            checkColorRange(b)

            if length == 6:
                return QColor(r, g, b)
            a = int(color[6:8], 16)
            checkColorRange(a)
            return QColor(r, g, b, a)
        except:
            raise Exception("Invalid hexadecimal color format: #" + color)

    parts = color.split(',')
    length = len(parts)
    if length not in [3, 4]:
        raise Exception("Invalid decimal color format: " + color)

    try:
        r = int(parts[0].strip())
        checkColorRange(r)
        g = int(parts[1].strip())
        checkColorRange(g)
        b = int(parts[2].strip())
        checkColorRange(b)

        if length == 3:
            return QColor(r, g, b)
        a = int(parts[3].strip())
        checkColorRange(a)
        return QColor(r, g, b, a)
    except:
        raise Exception("Invalid decimal color format: " + color)


def colorAsString(color, hexadecimal=False):
    """Converts the given color to a string"""
    def toHex(value):
        """Converts the value to a double digit hex string"""
        asStr = hex(value)[2:]
        if len(asStr) == 1:
            return '0' + asStr
        return asStr

    if hexadecimal:
        return '#'.join([toHex(color.red()),
                         toHex(color.green()),
                         toHex(color.blue()),
                         toHex(color.alpha())])
    return ','.join([str(color.red()),
                     str(color.green()),
                     str(color.blue()),
                     str(color.alpha())])


def buildFont(fontAsStr):
    """Converts saved font into QFont object"""
    fontAsStr = fontAsStr.strip()
    font = QFont()
    font.fromString(fontAsStr)
    return font


def fontAsString(font):
    """Converts a font to a string"""
    return font.toString()


def getMonospaceFontList():
    """Provides a list of strings with the system installed monospace fonts"""
    result = []
    combo = QFontComboBox()
    combo.setFontFilters(QFontComboBox.MonospacedFonts)
    for index in range(combo.count()):
        face = str(combo.itemText(index))
        if face.lower() != "webdings":
            result.append(face)
    return result


def toJSON(pythonObj):
    """Custom serialization"""
    if isinstance(pythonObj, QColor):
        return {'__class__': 'QColor',
                '__value__': colorAsString(pythonObj)}
    if isinstance(pythonObj, QFont):
        return {'__Class__': 'QFont',
                '__value__': fontAsString(pythonObj)}
    raise TypeError(repr(pythonObj) + ' is not JSON serializable')


def fromJSON(jsonObj):
    """Custom deserialization"""
    if '__class__' in jsonObj:
        if jsonObj['__class__'] == 'QColor':
            return buildColor(jsonObj['__value__']
        if jsonObj['__class__'] == 'QFont':
            return buildFont(jsonObj['__value__']
    return jsonObj
