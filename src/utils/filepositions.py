#
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

" Provides the storage for the last position in a file "

import os.path
import logging
import json


class FilesPositions:
    " Loads/stores/saves the last position in files "

    def __init__(self, dirName):

        # file name -> (line, pos, first visible, horizontalPos, verticalPos)
        self.__filePos = {}

        dirName = os.path.realpath(dirName)
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep
        if not os.path.isdir(dirName):
            raise Exception("Directory name is expected for files "
                            "positions. The given " + dirName + " is not.")

        self.__fileName = dirName + "lastpositions.json"
        if os.path.exists(self.__fileName):
            self.__load()
        return

    def __load(self):
        " Loads the saved positions file "
        try:
            with open(self.__fileName, mode='r', encoding='utf-8') as f:
                self.__filePos = json.load(f)
        except Exception as exc:
            logging.warning("Cannot load file editing positions from " +
                            self.__fileName + ". Message: " +
                            str(exc))
        return

    def save(self):
        " Saves the positions into a file "
        try:
            with open(self.__fileName, mode='w', encoding='utf-8') as f:
                json.dump(self.__filePos, f)
        except Exception as exc:
            logging.warning("Cannot save file editing positions to " +
                            self.__fileName + ". Message: " + str(exc))
        return

    def getPosition(self, fileName):
        " Provides the position or (-1,-1,-1,-1,-1) if not found "
        try:
            return self.__filePos[fileName]
        except KeyError:
            return (-1, -1, -1, -1, -1)

    def updatePosition(self, fileName, line, pos, firstLine,
                       horizontalPos, verticalPos):
        " Updates the position for the file "
        self.__filePos[fileName] = (line, pos, firstLine,
                                    horizontalPos, verticalPos)
        return
