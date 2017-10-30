# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Helper redirector class"""

from .qt import QObject, pyqtSignal


class Redirector(QObject):

    """Helper class used to redirect stdout and stderr to the log window"""

    appendToStdout = pyqtSignal(str)
    appendToStderr = pyqtSignal(str)

    def __init__(self, isStdout):
        QObject.__init__(self)
        self.__isStdout = isStdout

    def flush(self):
        """Flushes the buffered data - to conform the interface"""
        pass

    def write(self, message):
        """Writes the given data"""
        message = message.rstrip('\n')
        if self.__isStdout:
            self.appendToStdout.emit(message)
        else:
            self.appendToStderr.emit(message)
