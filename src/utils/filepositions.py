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

"""Provides the storage for the last position in a file"""

import os.path
from .fileutils import loadJSON, saveJSON


class FilePositions:

    """Loads/stores/saves the last position in files"""

    def __init__(self):
        # file name -> (line, pos, first visible, horizontalPos, verticalPos)
        self.__filePos = {}
        self.__fpFileName = None

    def reset(self):
        """Un-binds from the file system"""
        self.__filePos = {}
        self.__fpFileName = None

    def setup(self, dirName):
        """Binds the parameters to a disk file"""
        # Just in case - flush the previous data if they were bound
        FilePositions.save(self)

        dirName = os.path.realpath(dirName)
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep
        if not os.path.isdir(dirName):
            raise Exception('Directory name is expected for files '
                            'positions. The given ' + dirName + ' is not.')

        self.__fpFileName = dirName + 'lastpositions.json'
        if os.path.exists(self.__fpFileName):
            FilePositions.load(self)

    def load(self):
        """Loads the saved positions file"""
        if self.__fpFileName:
            self.__filePos = loadJSON(self.__fpFileName,
                                      'file editing positions', {})

    def save(self):
        """Saves the positions into a file"""
        if self.__fpFileName:
            saveJSON(self.__fpFileName, self.__filePos,
                     'file editing positions')

    def getFilePosition(self, fileName):
        """Provides the position or (-1,-1,-1,-1,-1) if not found"""
        return self.__filePos.get(fileName, (-1, -1, -1, -1, -1))

    def updateFilePosition(self, fileName, line, pos, firstLine,
                           horizontalPos, verticalPos):
        """Updates the position for the file"""
        self.__filePos[fileName] = (line, pos, firstLine,
                                    horizontalPos, verticalPos)
        FilePositions.save(self)
