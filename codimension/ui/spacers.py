# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2020  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Spacers to be used on the toolbars"""


from .qt import QWidget, QSizePolicy


class ToolBarHSpacer(QWidget):

    """Horizontal toolbar spacer"""

    def __init__(self, parent, width, name=None):
        QWidget.__init__(self, parent)
        self.setFixedWidth(width)
        if name is not None:
            self.setObjectName(name)
        self.setStyleSheet('background: transparent')


class ToolBarVSpacer(QWidget):

    """Vertical toolbar spacer"""

    def __init__(self, parent, height, name=None):
        QWidget.__init__(self, parent)
        self.setFixedHeight(height)
        if name is not None:
            self.setObjectName(name)
        self.setStyleSheet('background: transparent')


class ToolBarExpandingSpacer(QWidget):

    """Expanding toolbar spacer"""

    def __init__(self, parent, name=None):
        QWidget.__init__(self, parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if name is not None:
            self.setObjectName(name)
        self.setStyleSheet('background: transparent')

