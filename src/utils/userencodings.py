# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Provides the storage for the user assigned file encoding"""

import os.path
from .fileutils import loadJSON, saveJSON


class FileEncodings:

    """Loads/stores/saves the file encodingss"""

    def __init__(self):
        # file name -> encoding
        self.__encodings = {}
        self.__encFileName = None

    def reset(self):
        """Un-binds from the file system"""
        self.__encodings = {}
        self.__encFileName = None

    def setup(self, dirName):
        """Binds the parameters to a disk file"""
        # Just in case - flush the previous data if they were bound
        FileEncodings.save(self)

        dirName = os.path.realpath(dirName)
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep
        if not os.path.isdir(dirName):
            raise Exception('Directory name is expected for file '
                            'encodings. The given ' + dirName + ' is not.')

        self.__encFileName = dirName + 'encodings.json'
        if os.path.exists(self.__encFileName):
            FileEncodings.load(self)

    def load(self):
        """Loads the saved encodings file"""
        if self.__encFileName:
            self.__encodings = loadJSON(self.__encFileName,
                                        'file encodings', {})

    def save(self):
        """Saves the encodings into a file"""
        if self.__encFileName:
            saveJSON(self.__encFileName, self.__encodings, 'file encodings')

    def getFileEncoding(self, fileName):
        """Provides None if not found"""
        return self.__encodings.get(fileName, None)

    def setFileEncoding(self, fileName, encoding):
        """Sets the encoding for the file"""
        if encoding:
            self.__encodings[fileName] = encoding
            FileEncodings.save(self)
        else:
            if self.__encodings.pop(fileName, None):
                FileEncodings.save(self)
