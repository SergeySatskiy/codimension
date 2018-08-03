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

import sys
import logging
import os
import os.path
import json
from copy import deepcopy
from ui.qt import QColor, QFont
from .colorfont import buildFont, toJSON, fromJSON
from .fileutils import saveToFile, getFileContent
from .config import DEFAULT_ENCODING


isMac = sys.platform.lower() == 'darwin'

_DEFAULT_SKIN_SETTINGS = {
    'name': 'default',
    'marginPaper': QColor(228, 228, 228, 255),
    'marginPaperDebug': QColor(255, 228, 228, 255),
    'marginColor': QColor(128, 128, 128, 255),
    'marginColorDebug': QColor(128, 128, 128, 255),

    'flakesMarginPaper': QColor(208, 208, 208, 255),
    'flakesMarginPaperDebug':  QColor(255, 228, 228, 255),

    'bpointsMarginPaper': QColor(192, 192, 192, 255),

    'findNoMatchPaper': QColor(255, 193, 204, 100),
    'findMatchPaper': QColor(164, 198, 57, 100),
    'findInvalidPaper': QColor(228, 208, 10, 100),

    'revisionMarginPaper': QColor(228, 228, 228, 255),
    'revisionMarginColor': QColor(0, 128, 0, 255),
    'revisionAlterPaper': QColor(238, 240, 241, 255),
    'lineNumFont': buildFont('Courier,12,-1,5,50,0,0,0,0,0') if isMac else
                   buildFont('Monospace,12,-1,5,50,0,0,0,0,0'),
    'searchMarkColor': QColor(0, 255, 0, 255),
    'searchMarkPaper': QColor(255, 0, 255, 255),
    'matchMarkColor': QColor(0, 0, 255, 255),
    'matchMarkPaper': QColor(255, 255, 0, 255),
    'spellingMarkColor': QColor(139, 0, 0, 255),
    'nolexerPaper': QColor(255, 255, 255, 255),
    'nolexerColor': QColor(0, 0, 0, 255),
    'monoFont': buildFont('Courier,12,-1,5,50,0,0,0,0,0') if isMac else
                buildFont('Monospace,12,-1,5,50,0,0,0,0,0'),
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

    'ioconsolePaper': QColor(255, 255, 255, 255),
    'ioconsoleColor': QColor(0, 0, 0, 255),
    'ioconsoleMarginStdoutColor': QColor(0, 0, 0, 255),
    'ioconsoleMarginStdinColor': QColor(51, 102, 255, 255),
    'ioconsoleMarginStderrColor': QColor(204, 51, 0, 255),
    'ioconsoleMarginIDEMsgColor': QColor(128, 128, 128, 255)}


_DEFAULT_APP_CSS = """
QStatusBar::item
{ border: 0px solid black }
QToolTip
{ color: black;
  font-size: 11px;
  border: 1px solid gray;
  background-color: #fff;
  padding: 2px;
}
QTreeView
{ alternate-background-color: #eef0f1;
  background-color: #fff; }
QLineEdit
{ background-color: #fff; }
QComboBox
{ background-color: #fff;
  color: black; }
QComboBox QAbstractItemView
{ outline: 0px; }
QTextEdit
{ background-color: #fff; }
QPlainTextEdit
{ background-color: #fff; }
QListView
{ background-color: #fff; }"""


_DEFAULT_CFLOW_SETTINGS = {
    'debug': False,
    'cfMonoFont': buildFont('Courier,12,-1,5,50,0,0,0,0,0') if isMac else
                  buildFont('Monospace,12,-1,5,50,0,0,0,0,0'),
    'badgeFont': buildFont('Courier,9,-1,5,50,0,0,0,0,0') if isMac else
                 buildFont('Monospace,9,-1,5,50,0,0,0,0,0'),

    'hCellPadding': 8,      # in pixels (left and right)
    'vCellPadding': 8,      # in pixels (top and bottom)
    'hTextPadding': 5,      # in pixels (left and right)
    'vTextPadding': 5,      # in pixels (top and bottom)

    # E.g. comments could be hidden so they need to become smaller
    'vHiddenTextPadding': 0,
    'hHiddenTextPadding': 2,

    # Scope header (file, decor, loops etc) paddings
    'hHeaderPadding': 5,
    'vHeaderPadding': 5,

    'vSpacer': 10,

    # Rounded rectangles radius for the scopes
    'rectRadius': 6,

    # Rounded rectangles radius for the return-like statements
    'returnRectRadius': 16,
    'minWidth': 100,
    'ifWidth': 10,           # One if wing width
    'commentCorner': 6,      # Top right comment corner

    'lineWidth': 1,          # used for connections and box edges
    'lineColor': QColor(16, 16, 16, 255),

    # Selection
    'selectColor': QColor(63, 81, 181, 255),
    'selectPenWidth': 3,

    # Code blocks and other statements
    'boxBGColor': QColor(250, 250, 250, 255),
    'boxFGColor': QColor(0, 0, 0, 255),

    # Badges
    'badgeBGColor': QColor(230, 230, 230, 255),
    'badgeFGColor': QColor(0, 0, 0, 255),
    'badgeLineWidth': 1,
    'badgeLineColor': QColor(180, 180, 180, 255),

    # Labels
    'labelBGColor': QColor(230, 230, 230, 255),
    'labelFGColor': QColor(0, 0, 0, 255),
    'labelLineWidth': 1,
    'labelLineColor': QColor(0, 0, 0, 255),

    # Comments: leading, side & independent
    'commentBGColor': QColor(255, 255, 153, 255),
    'commentFGColor': QColor(0, 0, 0, 255),
    'commentLineColor': QColor(102, 102, 61, 255),
    'commentLineWidth': 1,
    'mainLine': 25,

    'fileScopeBGColor': QColor(255, 255, 230, 255),
    'funcScopeBGColor': QColor(230, 230, 255, 255),
    'decorScopeBGColor': QColor(230, 255, 255, 255),
    'classScopeBGColor': QColor(230, 255, 230, 255),
    'forScopeBGColor': QColor(187, 222, 251, 255),
    'whileScopeBGColor': QColor(187, 222, 251, 255),
    'elseScopeBGColor': QColor(209, 196, 233, 255),
    'withScopeBGColor': QColor(255, 255, 255, 255),
    'tryScopeBGColor': QColor(255, 255, 255, 255),
    'exceptScopeBGColor': QColor(255, 255, 255, 255),
    'finallyScopeBGColor': QColor(192, 192, 192, 255),
    'breakBGColor': QColor(249, 160, 160, 255),
    'continueBGColor': QColor(144, 202, 249, 255),
    'ifBGColor': QColor(255, 229, 127, 255),

    'hiddenCommentText': 'c',
    'hiddenExceptText': 'e',

    # Groups
    'collapsedOutlineWidth': 5,
    'openGroupVSpacer': 3,
    'openGroupHSpacer': 3,
    'groupBGColor': QColor(228, 255, 186, 255),
    'groupFGColor': QColor(0, 0, 0, 255),
    'groupBorderColor': QColor(0, 0, 0, 255),
    'groupControlBGColor': QColor(197, 217, 249),
    'groupControlBorderColor': QColor(140, 179, 242),

    # Rubber band selection
    'rubberBandBorderColor': QColor(63, 81, 181, 255),
    'rubberBandFGColor': QColor(182, 182, 182, 64)}



class Skin:

    """Holds the definitions for a skin"""

    def __init__(self):
        # That's a trick to be able to implement getattr/setattr
        self.__dirName = None
        self.__appCSS = None
        self.__values = {}
        self.__cfValues = {}
        self.minTextZoom = None
        self.minCFlowZoom = None
        self.__reset()

    def __reset(self):
        """Resets all the values to the default"""
        # Note: python 3.5 and 3.6 deepcopy() behaves different. The 3.6
        # fails to copy QFont at all while 3.5 copies it improperly.
        # So to be 100% sure it works, here is a manual copying...
        self.__values = {}
        for key, value in _DEFAULT_SKIN_SETTINGS.items():
            if isinstance(value, QFont):
                self.__values[key] = QFont(_DEFAULT_SKIN_SETTINGS[key])
            else:
                self.__values[key] = value

        self.__cfValues = {}
        for key, value in _DEFAULT_CFLOW_SETTINGS.items():
            if isinstance(value, QFont):
                self.__cfValues[key] = QFont(_DEFAULT_CFLOW_SETTINGS[key])
            else:
                self.__cfValues[key] = value

        self.__appCSS = deepcopy(_DEFAULT_APP_CSS)

        self.minTextZoom = self.__calculateMinTextZoom()
        self.minCFlowZoom = self.__calculateMinCFlowZoom()

    def __getitem__(self, key):
        if key == 'appCSS':
            return self.__appCSS
        if key in self.__cfValues:
            return self.__cfValues[key]
        return self.__values[key]

    def __setitem__(self, key, value):
        if key == 'name':
            raise Exception('Cannot change the skin name. It must match '
                            'the name of the skin directory.')
        if key == 'appCSS':
            self.__appCSS = value
            self.flushCSS()
        elif key in self.__cfValues:
            self.__cfValues[key] = value
            self.flushCFlow()
        else:
            self.__values[key] = value
            self.flush()

    @property
    def cflowSettings(self):
        """Provides the cflow settings dictionary"""
        return self.__cfValues

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

    def flushCFlow(self):
        """Saves the cflow settings to the disk"""
        if self.__dirName:
            fName = self.__dirName + 'cflow.json'
            try:
                with open(fName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
                    json.dump(self.__cfValues, diskfile, indent=4,
                              default=toJSON)
            except Exception as exc:
                logging.error('Error saving control flow settings (to ' +
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

        cflowFile = self.__dirName + 'cflow.json'
        if not os.path.exists(cflowFile):
            logging.error('Cannot load a skin from ' + dName +
                          '. The control flow settings file ' + cflowFile +
                          ' is not found.')
            return False

        # All the files are in place. Load them
        if not self.__loadAppCSS(appFile):
            self.flushCSS()
        if not self.__loadSkin(skinFile):
            self.flush()
        if not self.__loadCFlow(cflowFile):
            self.flushCFlow()
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
            origLength = len(self.__values)
            with open(fName, 'r', encoding=DEFAULT_ENCODING) as diskfile:
                self.__values.update(json.load(diskfile, object_hook=fromJSON))
            if origLength != len(self.__values):
                self.flush()
        except Exception as exc:
            logging.error('Cannot read skin settings from ' + fName +
                          ': ' + str(exc) +
                          '\nThe file will be updated with '
                          'default skin settings')
            return False

        self.minTextZoom = self.__calculateMinTextZoom()
        return True

    def __loadCFlow(self, fName):
        """Loads control flow settings file"""
        try:
            origLength = len(self.__cfValues)
            with open(fName, 'r', encoding=DEFAULT_ENCODING) as diskfile:
                self.__cfValues.update(json.load(diskfile,
                                                 object_hook=fromJSON))
            if origLength != len(self.__cfValues):
                self.flushCFlow()
        except Exception as exc:
            logging.error('Cannot read control flow settings from ' + fName +
                          ': ' + str(exc) +
                          '\nThe file will be updated with '
                          'default control flow settings')
            return False

        self.minCFlowZoom = self.__calculateMinCFlowZoom()
        return True

    def __calculateMinTextZoom(self):
        """Calculates the minimum text zoom"""
        marginPointSize = self.__values['lineNumFont'].pointSize()
        mainAreaPointSize = self.__values['monoFont'].pointSize()
        return (min(marginPointSize, mainAreaPointSize) - 1) * -1

    def __calculateMinCFlowZoom(self):
        """Calculates the minimum control flow zoom"""
        badgePointSize = self.__cfValues['badgeFont'].pointSize()
        monoPointSize = self.__cfValues['cfMonoFont'].pointSize()
        return (min(badgePointSize, monoPointSize) - 1) * -1

    def setTextMonoFontFamily(self, fontFamily):
        """Sets the new mono font family"""
        self.__values['monoFont'].setFamily(fontFamily)
        self.flush()

    def setMarginFontFamily(self, fontFamily):
        """Sets the new mono font family"""
        self.__values['lineNumFont'].setFamily(fontFamily)
        self.flush()

    def setFlowMonoFontFamily(self, fontFamily):
        """Sets the new flow font family"""
        self.__cfValues['cfMonoFont'].setFamily(fontFamily)
        self.flushCFlow()

    def setFlowBadgeFontFamily(self, fontFamily):
        """Sets the new flow badge font"""
        self.__cfValues['badgeFont'].setFamily(fontFamily)
        self.flushCFlow()


def getThemesList(localSkinsDir):
    """Builds a list of themes - system wide and the user local"""
    def isSkinDir(dName):
        """True if all the required files are there"""
        for fName in ['app.css', 'skin.json', 'cflow.json']:
            if not os.path.exists(dName + fName):
                return False
        return True

    def getSkinName(dName):
        """Provides the skin name or None"""
        try:
            fName = dName + 'skin.json'
            with open(fName, 'r',
                      encoding=DEFAULT_ENCODING) as diskfile:
                values = json.load(diskfile, object_hook=fromJSON)
                return values['name']
        except:
            return None

    result = []
    for item in os.listdir(localSkinsDir):
        dName = localSkinsDir + item + os.path.sep
        if os.path.isdir(dName):
            # Seems to be a skin dir
            if isSkinDir(dName):
                # Get the theme display name
                name = getSkinName(dName)
                if name:
                    result.append([item, name])

    # Add the installed names unless the same dirs have been already copied
    # to the user local dir
    srcDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    skinsDir = srcDir + os.path.sep + "skins" + os.path.sep

    if os.path.exists(skinsDir):
        for item in os.listdir(skinsDir):
            dName = skinsDir + item + os.path.sep
            if os.path.isdir(dName):
                # Seems to be a skin dir
                if isSkinDir(dName):
                    # Check if this name alrady added
                    for theme in result:
                        if theme[0] == item:
                            break
                    else:
                        # Get the theme display name
                        name = getSkinName(dName)
                        result.append([item, name])
    return result
