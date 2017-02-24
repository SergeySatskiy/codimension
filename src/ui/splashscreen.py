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


#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Splash screen implementation"""

from utils.pixmapcache import getPixmap
from .qt import (Qt, QColor, QApplication, QSplashScreen)


class SplashScreen(QSplashScreen):

    """Splash screen class"""

    def __init__(self):
        self.labelAlignment = Qt.Alignment(Qt.AlignBottom |
                                           Qt.AlignRight |
                                           Qt.AlignAbsolute)

        # The window flags are needed for some X Servers. E.g. Xwin-32
        # on windows draws a normal window outline if the flags are not here
        QSplashScreen.__init__(self, None, getPixmap('splash.png'),
                               Qt.SplashScreen |
                               Qt.WindowStaysOnTopHint |
                               Qt.X11BypassWindowManagerHint)

        self.show()
        QApplication.flush()

    def showMessage(self, msg):
        """Show the message in the bottom part of the splashscreen"""
        QSplashScreen.showMessage(self, msg,
                                  self.labelAlignment, QColor(Qt.black))
        QApplication.processEvents()

    def clearMessage(self):
        """Clear the splash screen message"""
        QSplashScreen.clearMessage(self)
        QApplication.processEvents()
