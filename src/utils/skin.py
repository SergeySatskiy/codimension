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

"""Skins support"""

import logging
import os
import json
from copy import deepcopy
from ui.qt import QColor, QFont
from .colorfont import buildFont, toJSON, fromJSON
from .fileutils import saveToFile, getFileContent
from .config import DEFAULT_ENCODING


_DEFAULT_SKIN_SETTINGS = {
    'name': 'default',
    'marginPaper': QColor(228, 228, 228, 255),
    'marginPaperDebug': QColor(255, 228, 228, 255),
    'marginColor': QColor(128, 128, 128, 255),
    'marginColorDebug': QColor(128, 128, 128, 255),
    'revisionMarginPaper': QColor(228, 228, 228, 255),
    'revisionMarginColor': QColor(0, 128, 0, 255),
    'revisionAlterPaper': QColor(238, 240, 241, 255),
    'lineNumFont': buildFont('Monospace,12,-1,5,50,0,0,0,0,0'),
    'searchMarkColor': QColor(0, 255, 0, 255),
    'searchMarkPaper': QColor(255, 0, 255, 255),
    'matchMarkColor': QColor(0, 0, 255, 255),
    'matchMarkPaper': QColor(255, 255, 0, 255),
    'spellingMarkColor': QColor(139, 0, 0, 255),
    'nolexerPaper': QColor(255, 255, 230, 255),
    'nolexerColor': QColor(0, 0, 0, 255),
    'nolexerFont': buildFont('Monospace,12,-1,5,50,0,0,0,0,0'),
    'currentLinePaper': QColor(232, 232, 255, 255),
    'edgeColor': QColor(127, 127, 127, 128),
    'matchedBracePaper': QColor(132, 117, 245, 255),
    'matchedBraceColor': QColor(255, 255, 255, 255),
    'unmatchedBracePaper': QColor(250, 89, 68, 255),
    'unmatchedBraceColor': QColor(0, 0, 255, 255),
    'indentGuidePaper': QColor(230, 230, 230, 255),
    'indentGuideColor': QColor(127, 127, 127, 255),
    'debugCurrentLineMarkerPaper': QColor(255, 255, 127, 255),
    'debugCurrentLineMarkerColor': QColor(0, 0, 255, 255),
    'debugExcptLineMarkerPaper': QColor(255, 64, 64, 255),
    'debugExcptLineMarkerColor': QColor(255, 255, 127, 255),
    'calltipPaper': QColor(220, 255, 220, 255),
    'calltipColor': QColor(0, 0, 0, 255),
    'calltipHighColor': QColor(250, 89, 68, 255),
    'outdatedOutlineColor': QColor(255, 154, 154, 255),
    'baseMonoFontFace': 'Monospace',

    'diffchanged2Color': QColor(0, 0, 0, 255),
    'diffchanged2Paper': QColor(247, 254, 0, 255),
    'diffponctColor': QColor(166, 72, 72, 255),
    'difflineColor': QColor(102, 102, 102, 255),
    'diffthColor': QColor(255, 255, 255, 255),
    'diffthPaper': QColor(102, 102, 102, 255),
    'diffaddedPaper': QColor(197, 250, 175, 255),
    'diffchangedColor': QColor(102, 102, 102, 255),
    'diffchangedPaper': QColor(244, 255, 221, 255),
    'diffdeletedPaper': QColor(255, 204, 204, 255),
    'diffhunkinfoColor': QColor(166, 72, 72, 255),
    'diffhunkinfoPaper': QColor(255, 255, 255, 255),
    'diffunmodifiedColor': QColor(102, 102, 102, 255),
    'diffunmodifiedPaper': QColor(238, 238, 238, 255),

    'ioconsolePaper': QColor(255, 255, 230, 255),
    'ioconsoleColor': QColor(0, 0, 0, 255),
    'ioconsoleStdoutPaper': QColor(255, 255, 230, 255),
    'ioconsoleStdoutColor': QColor(0, 0, 0, 255),
    'ioconsoleStdoutBold': False,
    'ioconsoleStdoutItalic': False,
    'ioconsoleStdinPaper': QColor(255, 255, 230, 255),
    'ioconsoleStdinColor': QColor(0, 0, 0, 255),
    'ioconsoleStdinBold': False,
    'ioconsoleStdinItalic': False,
    'ioconsoleStderrPaper': QColor(255, 228, 228, 255),
    'ioconsoleStderrColor': QColor(0, 0, 0, 255),
    'ioconsoleStderrBold': False,
    'ioconsoleStderrItalic': False,
    'ioconsoleIDEMsgPaper': QColor(228, 228, 228, 255),
    'ioconsoleIDEMsgColor': QColor(0, 0, 255, 255),
    'ioconsolemarginPaper': QColor(228, 228, 228, 255),
    'ioconsolemarginColor': QColor(128, 128, 128, 255),
    'ioconsolemarginFont': buildFont('Monospace,12,-1,5,50,0,0,0,0,0')}


_DEFAULT_APP_CSS = """
QStatusBar::item
{ border: 0px solid black }
QToolTip
{ font-size: 11px;
  border: 1px solid gray;
  border-radius: 3px;
  background: QLinearGradient(x1: 0, y1: 0,
                              x2: 0, y2: 1,
                              stop: 0 #eef, stop: 1 #ccf);
}
QTreeView
{ alternate-background-color: #eef0f1;
  background-color: #ffffe6; }
QLineEdit
{ background-color: #ffffe6; }
QComboBox
{ background-color: #ffffe6; color: black; }
QComboBox QAbstractItemView
{ outline: 0px; }
QTextEdit
{ background-color: #ffffe6; }
QListView
{ background-color: #ffffe6; }"""


class Skin:

    """Holds the definitions for a skin"""

    def __init__(self):
        # That's a trick to be able to implement getattr/setattr
        self.__dirName = None
        self.__appCSS = None
        self.__values = {}
        self.__reset()

    def __reset(self):
        """Resets all the values to the default"""
        self.__values = deepcopy(_DEFAULT_SKIN_SETTINGS)
        for key, value in self.__values.items():
            # deepcopy() does not work properly for QFont: the underlied C++
            # wrapper is not initialized in this case. So...
            if isinstance(value, QFont):
                self.__values[key] = QFont(_DEFAULT_SKIN_SETTINGS[key])
        self.__appCSS = deepcopy(_DEFAULT_APP_CSS)

    def __getitem__(self, key):
        if key == 'appCSS':
            return self.__appCSS
        return self.__values[key]

    def __setitem__(self, key, value):
        if key == 'name':
            raise Exception('Cannot change the skin name. It must match '
                            'the name of the skin directory.')
        if key == 'appCSS':
            self.__appCSS = value
            self.flushCSS()
        else:
            self.__values[key] = value
            self.flush()

    def flush(self):
        """Saves the values to the disk"""
        if self.__dirName:
            fName = self.__dirName + 'skin.json'
            try:
                with open(fName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
                    json.dump(self.__values, diskfile, indent=4,
                              default=toJSON)
            except Exception as exc:
                logging.error('Error saving skin settings (to ' +
                              fName + '): ' + str(exc))

    def flushCSS(self):
        """Saves the CSS to the disk"""
        if self.__dirName:
            # Note: comments and includes are lost here if they were in the
            # original css
            saveToFile(self.__dirName + 'app.css', self.__appCSS,
                       allowException=False)

    def load(self, dirName):
        """Loads the skin description from the given directory"""
        dName = os.path.realpath(dirName)
        if not os.path.isdir(dName):
            logging.error('Cannot load a skin from ' + dName + '. A directory '
                          'name is expected.')
            return False

        self.__dirName = dName + os.path.sep

        appFile = self.__dirName + 'app.css'
        if not os.path.exists(appFile):
            logging.error('Cannot load a skin from ' + dName +
                          '. The application css file ' + appFile +
                          ' is not found.')
            return False

        skinFile = self.__dirName + 'skin.json'
        if not os.path.exists(skinFile):
            logging.error('Cannot load a skin from ' + dName +
                          '. The skin settings file ' + skinFile +
                          ' is not found.')
            return False

        # All the files are in place. Load them
        if not self.__loadAppCSS(appFile):
            self.flushCSS()
        if not self.__loadSkin(skinFile):
            self.flush()
        return True

    def __loadAppCSS(self, fName):
        """Loads the application CSS file"""
        try:
            self.__appCSS = getFileContent(fName)
        except Exception as exc:
            logging.error('Cannot read an application CSS from ' + fName +
                          ': ' + str(exc) +
                          '\nThe file will be updated with a default CSS')
            return False
        return True

    def __loadSkin(self, fName):
        """Loads the general settings file"""
        try:
            with open(fName, 'r', encoding=DEFAULT_ENCODING) as diskfile:
                self.__values = json.load(diskfile, object_hook=fromJSON)
        except Exception as exc:
            logging.error('Cannot read skin settings from ' + fName +
                          ': ' + str(exc) +
                          '\nThe file will be updated with '
                          'default skin settings')
            return False
        return True
