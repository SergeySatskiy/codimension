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

# pylint: disable=C0305
# pylint: disable=W0603
# pylint: disable=W0702
# pylint: disable=W0703

import sys
import logging
import os.path
import json
from copy import deepcopy
from ui.qt import QColor, QFont
from .colorfont import (buildFont, buildColor,
                        colorFontToJSON, colorFontFromJSON)
from .fileutils import saveToFile, getFileContent
from .config import DEFAULT_ENCODING
from .settings import SETTINGS_DIR


PACKAGE_SKIN_DIR = os.path.dirname(os.path.realpath(sys.argv[0])) + \
                   os.path.sep + 'skins' + os.path.sep
USER_SKIN_DIR = SETTINGS_DIR + 'skins' + os.path.sep
OVERRIDE_FILE = 'override.json'
SAMPLE_SKIN = 'sample'

isMac = sys.platform.lower() == 'darwin'

_DEFAULT_SKIN_SETTINGS = {
    'name': 'default',
    'dark': False,
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

    # 'revisionMarginPaper': QColor(228, 228, 228, 255),
    # 'revisionMarginColor': QColor(0, 128, 0, 255),
    # 'revisionAlterPaper': QColor(238, 240, 241, 255),

    'lineNumFont': buildFont('Courier,12,-1,5,50,0,0,0,0,0') if isMac else
                   buildFont('Monospace,12,-1,5,50,0,0,0,0,0'),
    'searchMarkColor': QColor(0, 255, 0, 255),
    'searchMarkPaper': QColor(255, 0, 255, 255),
    'matchMarkColor': QColor(0, 0, 255, 255),
    'matchMarkPaper': QColor(255, 255, 0, 255),
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

    # 'diffchanged2Color': QColor(0, 0, 0, 255),
    # 'diffchanged2Paper': QColor(247, 254, 0, 255),
    # 'diffponctColor': QColor(166, 72, 72, 255),
    # 'difflineColor': QColor(102, 102, 102, 255),
    # 'diffthColor': QColor(255, 255, 255, 255),
    # 'diffthPaper': QColor(102, 102, 102, 255),
    # 'diffaddedPaper': QColor(197, 250, 175, 255),
    # 'diffchangedColor': QColor(102, 102, 102, 255),
    # 'diffchangedPaper': QColor(244, 255, 221, 255),
    # 'diffdeletedPaper': QColor(255, 204, 204, 255),
    # 'diffhunkinfoColor': QColor(166, 72, 72, 255),
    # 'diffhunkinfoPaper': QColor(255, 255, 255, 255),
    # 'diffunmodifiedColor': QColor(102, 102, 102, 255),
    # 'diffunmodifiedPaper': QColor(238, 238, 238, 255),

    'ioconsolePaper': QColor(255, 255, 255, 255),
    'ioconsoleColor': QColor(0, 0, 0, 255),
    'ioconsoleMarginStdoutColor': QColor(0, 0, 0, 255),
    'ioconsoleMarginStdinColor': QColor(51, 102, 255, 255),
    'ioconsoleMarginStderrColor': QColor(204, 51, 0, 255),
    'ioconsoleMarginIDEMsgColor': QColor(128, 128, 128, 255),

    'invalidInputPaper': QColor(255, 193, 204, 100),

    'headerLabelBGColor': QColor(255, 255, 255, 255),
    'headerLabelBorderColor': QColor(179, 175, 171, 255)}


_DEFAULT_APP_CSS = """
QStatusBar::item
{ border: 0px solid black }
QToolTip
{ color: black;
  font-size: 11px;
  border: 1px solid gray;
  background-color: #fff;
  padding: 2px; }
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
{ background-color: #fff; }

QStatusBar StatusBarFramedLabel
{ border-radius: 3px;
  padding: 4px;
  background-color: #fff;
  border: 1px solid #b3afab; }
QStatusBar StatusBarPixmapLabel
{ background: transparent; }
QStatusBar StatusBarPathLabel
{ border-radius: 3px;
  padding: 4px;
  background-color: #fff;
  border: 1px solid #b3afab; }
FramedLabel
{ border-radius: 3px;
  padding: 4px;
  background: transparent;
  border: 1px solid #b3afab; }
HeaderLabel
{ border-radius: 3px;
  padding: 4px;
  background-color: #fff;
  border: 1px solid #b3afab; }
FramedFitLabel
{ border-radius: 3px;
  padding: 4px;
  background: transparent;
  border: 1px solid #b3afab; }
HeaderFitLabel
{ border-radius: 3px;
  padding: 4px;
  background-color: #fff;
  border: 1px solid #b3afab; }
FramedFitPathLabel
{ border-radius: 3px;
  padding: 4px;
  background: transparent;
  border: 1px solid #b3afab; }
HeaderFitPathLabel
{ border-radius: 3px;
  padding: 4px;
  background-color: #fff;
  border: 1px solid #b3afab; }"""


_DEFAULT_CFLOW_SETTINGS = {
    'debug': False,
    'cfMonoFont': buildFont('Courier,12,-1,5,50,0,0,0,0,0') if isMac else
                  buildFont('Monospace,12,-1,5,50,0,0,0,0,0'),
    'badgeFont': buildFont('Courier,9,-1,5,50,0,0,0,0,0') if isMac else
                 buildFont('Monospace,9,-1,5,50,0,0,0,0,0'),

    'hCellPadding': 6,      # in pixels (left and right)
    'vCellPadding': 4,      # in pixels (top and bottom)
    'hTextPadding': 4,      # in pixels (left and right)
    'vTextPadding': 4,      # in pixels (top and bottom)

    # Scope header (file, decor, loops etc) paddings
    'hHeaderPadding': 4,
    'vHeaderPadding': 4,

    'vSpacer': 8,

    # Rounded rectangles radius for the return-like statements
    'minWidth': 100,

    'cfLineWidth': 1,       # Control flow line
    'boxLineWidth': 1,      # All boxes and their leads to CF
    'cfLineColor': QColor(132, 132, 132, 255),

    # Selection
    'selectColor': QColor(63, 81, 181, 255),
    'selectPenWidth': 3,

    # Code blocks and other statements
    'codeBlockBGColor': QColor(248, 248, 248, 255),
    'codeBlockFGColor': QColor(0, 0, 0, 255),
    'codeBlockBorderColor': QColor(150, 150, 150, 255),

    'breakBGColor': QColor(250, 227, 217, 255),
    'breakFGColor': QColor(0, 0, 0, 255),
    'breakBorderColor': QColor(150, 150, 150, 255),
    'breakHPadding': 4,
    'breakVPadding': 0,
    'breakRectRadius': 2,

    'continueBGColor': QColor(138, 198, 209, 255),
    'continueFGColor': QColor(0, 0, 0, 255),
    'continueBorderColor': QColor(150, 150, 150, 255),
    'continueHPadding': 4,
    'continueVPadding': 0,
    'continueRectRadius': 2,

    'returnBGColor': QColor(255, 247, 188, 255),
    'returnFGColor': QColor(0, 0, 0, 255),
    'returnBorderColor': QColor(150, 150, 150, 255),
    'returnRectRadius': 12,

    'raiseBGColor': QColor(219, 210, 210, 255),
    'raiseFGColor': QColor(0, 0, 0, 255),
    'raiseBorderColor': QColor(150, 150, 150, 255),

    'assertBGColor': QColor(210, 210, 210, 255),
    'assertFGColor': QColor(0, 0, 0, 255),
    'assertBorderColor': QColor(150, 150, 150, 255),

    'sysexitBGColor': QColor(255, 156, 156, 255),
    'sysexitFGColor': QColor(0, 0, 0, 255),
    'sysexitBorderColor': QColor(60, 60, 60, 255),

    'importBGColor': QColor(248, 248, 248, 255),
    'importFGColor': QColor(0, 0, 0, 255),
    'importBorderColor': QColor(150, 150, 150, 255),

    'ifBGColor': QColor(255, 247, 188, 255),
    'ifFGColor': QColor(0, 0, 0, 255),
    'ifBorderColor': QColor(150, 150, 150, 255),
    'ifYBranchTextColor': QColor(132, 132, 132, 255),
    'ifNBranchTextColor': QColor(132, 132, 132, 255),
    'ifWidth': 10,           # One if wing width

    'decorRectRadius': 2,

    # Badges
    'badgeBGColor': QColor(230, 230, 230, 255),
    'badgeFGColor': QColor(0, 0, 0, 255),
    'badgeLineWidth': 1,
    'badgeBorderColor': QColor(150, 150, 150, 255),
    'badgeHSpacing': 2,
    'badgeVSpacing': 1,
    'badgeRadius': 2,
    'badgeToScopeVPadding': 3,
    'badgeToBadgeHSpacing': 4,
    'badgePixmapSpacing': 4,    # For square badges like comment, decorator etc
    'badgeGroupSpacing': 10,

    # Comments: leading, side & independent
    'commentBGColor': QColor(255, 255, 235, 255),
    'commentFGColor': QColor(90, 90, 90, 255),
    'commentBorderColor': QColor(150, 150, 150, 255),
    'commentCorner': 5,      # Top right comment corner
    'vHiddenCommentPadding': 3,
    'hHiddenCommentPadding': 3,
    'hiddenCommentBGColor': QColor(255, 255, 235, 255),
    'hiddenCommentBorderColor': QColor(150, 150, 150, 255),
    'hiddenCommentRectRadius': 2,
    'ifSideCommentVShift': 7,

    'mainLine': 25,
    'decorMainLine': 15,

    # docstring border cannot be changed; it is a property of the scope
    'docstringBGColor': QColor(255, 255, 235, 255),
    'docstringFGColor': QColor(90, 90, 90, 255),
    'docstringBorderColor': QColor(150, 150, 150, 255),

    'scopeRectRadius': 4,
    'loopHeaderPadding': 7,

    'fileScopeBGColor': QColor(255, 255, 255, 255),
    'fileScopeFGColor': QColor(0, 0, 0, 255),
    'fileScopeBorderColor': QColor(150, 150, 150, 255),

    'funcScopeBGColor': QColor(240, 240, 255, 255),
    'funcScopeFGColor': QColor(0, 0, 0, 255),
    'funcScopeBorderColor': QColor(150, 150, 150, 255),

    'classScopeBGColor': QColor(240, 255, 240, 255),
    'classScopeFGColor': QColor(0, 0, 0, 255),
    'classScopeBorderColor': QColor(150, 150, 150, 255),

    'forScopeBGColor': QColor(198, 219, 239, 255),
    'forScopeFGColor': QColor(0, 0, 0, 255),
    'forScopeBorderColor': QColor(150, 150, 150, 255),
    'forScopeHeaderBorderColor': QColor(150, 150, 150, 255),
    'forScopeHeaderBGColor': QColor(218, 239, 255, 255),
    'forScopeHeaderPenWidth': 2,

    'whileScopeBGColor': QColor(198, 219, 239, 255),
    'whileScopeFGColor': QColor(0, 0, 0, 255),
    'whileScopeBorderColor': QColor(150, 150, 150, 255),
    'whileScopeHeaderBorderColor': QColor(150, 150, 150, 255),
    'whileScopeHeaderBGColor': QColor(218, 239, 255, 255),
    'whileScopeHeaderPenWidth': 2,

    'tryScopeBGColor': QColor(248, 248, 248, 255),
    'tryScopeFGColor': QColor(0, 0, 0, 255),
    'tryScopeBorderColor': QColor(150, 150, 150, 255),

    'decorScopeBGColor': QColor(240, 240, 240, 255),
    'decorScopeFGColor': QColor(0, 0, 0, 255),
    'decorScopeBorderColor': QColor(150, 150, 150, 255),

    'withScopeBGColor': QColor(248, 248, 248, 255),
    'withScopeFGColor': QColor(0, 0, 0, 255),
    'withScopeBorderColor': QColor(150, 150, 150, 255),

    'exceptScopeBGColor': QColor(210, 210, 210, 255),
    'exceptScopeFGColor': QColor(0, 0, 0, 255),
    'exceptScopeBorderColor': QColor(150, 150, 150, 255),
    'hiddenExceptBGColor': QColor(240, 240, 240, 255),
    'hiddenExceptBorderColor': QColor(150, 150, 150, 255),
    'hHiddenExceptPadding': 3,
    'vHiddenExceptPadding': 3,
    'hiddenExceptRectRadius': 3,

    'finallyScopeBGColor': QColor(248, 248, 248, 255),
    'finallyScopeFGColor': QColor(0, 0, 0, 255),
    'finallyScopeBorderColor': QColor(150, 150, 150, 255),

    'forElseScopeBGColor': QColor(198, 219, 239, 255),
    'forElseScopeFGColor': QColor(0, 0, 0, 255),
    'forElseScopeBorderColor': QColor(150, 150, 150, 255),

    'whileElseScopeBGColor': QColor(198, 219, 239, 255),
    'whileElseScopeFGColor': QColor(0, 0, 0, 255),
    'whileElseScopeBorderColor': QColor(150, 150, 150, 255),

    'tryElseScopeBGColor': QColor(248, 248, 248, 255),
    'tryElseScopeFGColor': QColor(0, 0, 0, 255),
    'tryElseScopeBorderColor': QColor(150, 150, 150, 255),

    # Groups
    'openGroupVSpacer': 3,
    'openGroupHSpacer': 3,
    'openGroupBGColor': QColor(245, 255, 255, 255),
    'openGroupFGColor': QColor(0, 0, 0, 255),
    'openGroupBorderColor': QColor(32, 32, 32, 255),
    'openGroupControlBGColor': QColor(197, 217, 249, 255),
    'openGroupControlBorderColor': QColor(140, 179, 242, 255),
    'openGroupControlLineWidth': 1,

    'collapsedGroupBGColor': QColor(245, 255, 255, 255),
    'collapsedGroupFGColor': QColor(0, 0, 0, 255),
    'collapsedGroupBorderColor': QColor(150, 150, 150, 255),
    'collapsedGroupXShift': 4,
    'collapsedGroupYShift': 4,

    'emptyGroupBGColor': QColor(245, 255, 255, 255),
    'emptyGroupFGColor': QColor(0, 0, 0, 255),
    'emptyGroupBorderColor': QColor(150, 150, 150, 255),
    'emptyGroupXShift': 4,
    'emptyGroupYShift': 4,

    # Rubber band selection
    'rubberBandBorderColor': QColor(63, 81, 181, 255),
    'rubberBandFGColor': QColor(182, 182, 182, 64),

    # Doc links
    'hDocLinkPadding': 3,   # in pixels (left and right)
    'vDocLinkPadding': 3,   # in pixels (top and bottom)
    'docLinkBGColor': QColor(219, 230, 246, 255),
    'docLinkFGColor': QColor(0, 0, 0, 255),
    'docLinkBorderColor': QColor(150, 150, 150, 255)}


class Skin:

    """Holds the definitions for a skin"""

    def __init__(self):
        # That's a trick to be able to implement getattr/setattr
        self.__dirName = None
        self.__userDirName = None
        self.__appCSS = None
        self.__values = {}
        self.__overrides = {}
        self.minTextZoom = None
        self.minCFlowZoom = None
        self.__reset()

    def __reset(self):
        """Resets all the values to the default"""
        # Note: python 3.5 and 3.6 deepcopy() behaves different. The 3.6
        # fails to copy QFont at all while 3.5 copies it improperly.
        # So to be 100% sure it works, here is a manual copying...
        self.__dirName = None
        self.__overrides = {}
        self.__userDirName = USER_SKIN_DIR + \
                             _DEFAULT_SKIN_SETTINGS['name'] + os.path.sep
        if not os.path.exists(self.__userDirName):
            self.__userDirName = None
        elif not os.path.isdir(self.__userDirName):
            self.__userDirName = None

        self.__values = {}
        for key, value in _DEFAULT_SKIN_SETTINGS.items():
            if isinstance(value, QFont):
                self.__values[key] = QFont(_DEFAULT_SKIN_SETTINGS[key])
            else:
                self.__values[key] = value

        for key, value in _DEFAULT_CFLOW_SETTINGS.items():
            if isinstance(value, QFont):
                self.__values[key] = QFont(_DEFAULT_CFLOW_SETTINGS[key])
            else:
                self.__values[key] = value

        self.__appCSS = deepcopy(_DEFAULT_APP_CSS)
        self.__applyOverrides()

        self.minTextZoom = self.__calculateMinTextZoom()
        self.minCFlowZoom = self.__calculateMinCFlowZoom()

    def getDir(self):
        """Provides the directory where the skin is coming from"""
        # Can be None for the default skin and for the custom user skin
        return self.__dirName

    def getUserDir(self):
        """Provides the location of the user skin directory"""
        # Can be the same as self.__dirName for the custom user skin
        return self.__userDirName

    def __getitem__(self, key):
        if key == 'appCSS':
            return self.__appCSS
        return self.__values[key]

    def __setitem__(self, key, value):
        logging.error('The generic skin parameters are immutable')

    @property
    def cflowSettings(self):
        """Provides the cflow settings dictionary"""
        # It is more than needed. The minimum is what is in the CFOW dict
        return self.__values

    @staticmethod
    def flush(fName, values):
        """Saves the values to the disk"""
        try:
            with open(fName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
                json.dump(values, diskfile, indent=4, default=colorFontToJSON)
        except Exception as exc:
            logging.error('Error updating skin settings (to %s): %s',
                          fName, str(exc))

    @staticmethod
    def flushCFlow(fName, values):
        """Saves the cflow settings to the disk"""
        try:
            with open(fName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
                json.dump(values, diskfile, indent=4, default=colorFontToJSON)
        except Exception as exc:
            logging.error('Error updating control flow settings (to %s): %s',
                          fName, str(exc))

    def loadByName(self, skinName):
        """Loads the skin by name.

        Implemetation should be in sync with getSkinsList
        """
        if self.__values['name'] == skinName:
            return

        if skinName == _DEFAULT_SKIN_SETTINGS['name']:
            self.__reset()
            return

        # check if it is from an installation package
        skinsAndDirs = getSkinsWithDirs()
        if skinName not in skinsAndDirs:
            logging.error('Skin "%s" is not found', skinName)
            return

        skinDir = skinsAndDirs[skinName]

        # load 3 files
        newAppCSS = self.__loadAppCSS(skinDir + 'app.css')
        newValues = self.__loadSkin(skinDir + 'skin.json')
        newCflowValues = self.__loadCFlow(skinDir + 'cflow.json')
        if newAppCSS is None or newValues is None or newCflowValues is None:
            logging.error('The current skin ("%s") has not been replaced '
                          'with skin "%s"', self.__values['name'], skinName)
            return

        # Apply new values
        self.__appCSS = newAppCSS
        self.__values = newValues
        self.__values.update(newCflowValues)

        # Set the skin directories
        if skinDir.startswith(USER_SKIN_DIR):
            # Pure user dir, unknown for the package
            self.__dirName = None
            self.__userDirName = skinDir
        else:
            self.__dirName = skinDir
            self.__userDirName = USER_SKIN_DIR + \
                                 self.__values['name'] + os.path.sep
            if not os.path.exists(self.__userDirName):
                self.__userDirName = None
            elif not os.path.isdir(self.__userDirName):
                self.__userDirName = None

        self.__applyOverrides()
        self.__checkMissedValues()

        self.minTextZoom = self.__calculateMinTextZoom()
        self.minCFlowZoom = self.__calculateMinCFlowZoom()

    def __applyOverrides(self):
        """Applies the skin overrides"""
        if self.__userDirName is None:
            return
        fName = self.__userDirName + OVERRIDE_FILE
        if not os.path.exists(fName):
            return
        if not os.path.isfile(fName):
            return

        try:
            with open(fName, 'r', encoding=DEFAULT_ENCODING) as diskfile:
                diskContent = json.load(diskfile,
                                        object_hook=colorFontFromJSON)
                diskContent, _ = self.__postProcessValues(diskContent)
            self.__overrides = diskContent
            self.__values.update(diskContent)
        except Exception as exc:
            logging.error('Error applying overrides on the skin "%s" '
                          'from %s: %s',self.__values['name'], fName, str(exc))

    def __checkMissedValues(self):
        """Checks if some values are missed in the skin"""
        expectedValues = set(_DEFAULT_SKIN_SETTINGS.keys()) | \
                         set(_DEFAULT_CFLOW_SETTINGS.keys())
        presentValues = set(self.__values.keys())
        diff = expectedValues - presentValues
        for val in diff:
            logging.error('The skin "%s" misses value %s. The values will be '
                          'taken from the default settings.',
                          self.__values['name'], val)
            if val in _DEFAULT_SKIN_SETTINGS:
                defaultVal = {val: _DEFAULT_SKIN_SETTINGS[val]}
            else:
                defaultVal = {val: _DEFAULT_CFLOW_SETTINGS[val]}
            defaultVal, _ = self.__postProcessValues(defaultVal)
            self.__values.update(defaultVal)

    @staticmethod
    def __loadAppCSS(fName):
        """Loads the application CSS file"""
        try:
            return getFileContent(fName)
        except Exception as exc:
            logging.error('Cannot read an application CSS from %s: %s',
                          fName, str(exc))
        return None

    def __loadSkin(self, fName):
        """Loads the general settings file"""
        try:
            with open(fName, 'r', encoding=DEFAULT_ENCODING) as diskfile:
                diskContent = json.load(diskfile,
                                        object_hook=colorFontFromJSON)
                diskContent, oldFormat = self.__postProcessValues(diskContent)
            if oldFormat:
                try:
                    self.flush(fName, diskContent)
                except:
                    pass
            return diskContent
        except Exception as exc:
            logging.error('Cannot read skin settings from %s: %s',
                          fName, str(exc))
        return None

    def __loadCFlow(self, fName):
        """Loads control flow settings file"""
        try:
            with open(fName, 'r', encoding=DEFAULT_ENCODING) as diskfile:
                diskContent = json.load(diskfile,
                                        object_hook=colorFontFromJSON)
                diskContent, oldFormat = self.__postProcessValues(diskContent)
            if oldFormat:
                try:
                    self.flushCFlow(fName, diskContent)
                except:
                    pass
            return diskContent
        except Exception as exc:
            logging.error('Cannot read control flow settings from %s: %s',
                          fName, str(exc))
        return None

    def __calculateMinTextZoom(self):
        """Calculates the minimum text zoom"""
        marginPointSize = self.__values['lineNumFont'].pointSize()
        mainAreaPointSize = self.__values['monoFont'].pointSize()
        return (min(marginPointSize, mainAreaPointSize) - 1) * -1

    def __calculateMinCFlowZoom(self):
        """Calculates the minimum control flow zoom"""
        badgePointSize = self.__values['badgeFont'].pointSize()
        monoPointSize = self.__values['cfMonoFont'].pointSize()
        return (min(badgePointSize, monoPointSize) - 1) * -1

    @staticmethod
    def __postProcessValues(values):
        """Builds fonts and colors as needed"""
        # Detection is primitive: the name of the dictionary item
        oldFormat = False
        for name, value in values.items():
            lowerName = name.lower()
            if 'font' in lowerName:
                if isinstance(value, QFont):
                    # already built
                    oldFormat = True
                else:
                    values[name] = buildFont(value)
            elif 'color' in lowerName or 'paper' in lowerName:
                if isinstance(value, QColor):
                    # already built
                    oldFormat = True
                else:
                    values[name] = buildColor(value)
        return values, oldFormat

    def __createUserSkinDir(self):
        """Creates the user skin dir if necessary"""
        if not self.__userDirName:
            self.__userDirName = USER_SKIN_DIR + self.__values['name'] + \
                                 os.path.sep
            if os.path.exists(self.__userDirName):
                if not os.path.isdir(self.__userDirName):
                    logging.error('The skin needs to have the directory %s '
                                  'to be available but the name is taken by '
                                  'something else. No skin overrides '
                                  'possible.', self.__userDirName)
                    self.__userDirName = None
                    return False
            # Try to create the dir
            try:
                os.makedirs(self.__userDirName, exist_ok=True)
            except Exception as exc:
                logging.error('Error creating the skin overriding '
                              'directory %s: %s', self.__userDirName, str(exc))
                self.__userDirName = None
                return False
        return True

    def __flushOverrides(self):
        """Saves the overrides to the disk"""
        # The user directory must exist
        fName = self.__userDirName + OVERRIDE_FILE
        try:
            with open(fName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
                json.dump(self.__overrides, diskfile, indent=4,
                          default=colorFontToJSON)
        except Exception as exc:
            logging.error('Error updating overridden skin settings in %s: %s',
                          fName, str(exc))

    def setTextMonoFont(self, font):
        """Sets the new mono font family"""
        self.__values['monoFont'] = font
        self.__overrides['monoFont'] = font
        if self.__createUserSkinDir():
            self.__flushOverrides()

    def setMarginFont(self, font):
        """Sets the new mono font family"""
        self.__values['lineNumFont'] = font
        self.__overrides['lineNumFont'] = font
        if self.__createUserSkinDir():
            self.__flushOverrides()

    def setFlowMonoFont(self, font):
        """Sets the new flow font family"""
        self.__values['cfMonoFont'] = font
        self.__overrides['cfMonoFont'] = font
        if self.__createUserSkinDir():
            self.__flushOverrides()

    def setFlowBadgeFont(self, font):
        """Sets the new flow badge font"""
        self.__values['badgeFont'] = font
        self.__overrides['badgeFont'] = font
        if self.__createUserSkinDir():
            self.__flushOverrides()


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
            # Note: the load() method lacks the
            # object_hook=colorFontFromJSON parameter because the only
            # the skin name is read and no font/color conversion needed
            values = json.load(diskfile)
            return values['name']
    except:
        return None


# Dictionary { <skin name>: <directory> }
SKIN_LIST = None


def getSkinsList():
    """Provides just the skin names"""
    return getSkinsWithDirs().keys()


def getSkinsWithDirs():
    """Builds a list of skins - system wide and the user local"""
    global SKIN_LIST

    if SKIN_LIST is None:
        # default is coming from memory and always there
        SKIN_LIST = {'default': None}

        # First, walk the installation skin dirs
        for item in os.listdir(PACKAGE_SKIN_DIR):
            dName = PACKAGE_SKIN_DIR + item + os.path.sep
            if os.path.isdir(dName):
                if isSkinDir(dName):
                    name = getSkinName(dName)
                    if name and name not in SKIN_LIST:
                        SKIN_LIST[name] = dName

        for item in os.listdir(USER_SKIN_DIR):
            if item == SAMPLE_SKIN:
                continue
            if item in SKIN_LIST:
                # this is overriding of the IDE supplied skins
                continue
            dName = USER_SKIN_DIR + item + os.path.sep
            if os.path.isdir(dName):
                if isSkinDir(dName):
                    name = getSkinName(dName)
                    if name and name not in SKIN_LIST:
                        SKIN_LIST[name] = dName
    return SKIN_LIST


def populateSampleSkin():
    """Populates the sample skin in the user directory"""
    dName = USER_SKIN_DIR + SAMPLE_SKIN + os.path.sep
    if os.path.exists(dName):
        if not os.path.isdir(dName):
            logging.error('Error creating a sample skin at %s. '
                          'The file system entry is already occupied '
                          'by something else', dName)
            return

    # Try to create the dir
    try:
        os.makedirs(dName, exist_ok=True)
    except Exception as exc:
        logging.error('Error creating a sample skin at %s: %s',
                      dName, str(exc))

    fName = dName + 'app.css'
    try:
        saveToFile(fName, _DEFAULT_APP_CSS)
    except Exception as exc:
        logging.error('Error creating a sample skin at %s. '
                      'Cannot write app.css: %s', dName, str(exc))

    fName = dName + 'skin.json'
    try:
        values = {}
        for key, value in _DEFAULT_SKIN_SETTINGS.items():
            if isinstance(value, QFont):
                values[key] = QFont(_DEFAULT_SKIN_SETTINGS[key])
            else:
                values[key] = value
        values['name'] = SAMPLE_SKIN
        with open(fName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
            json.dump(values, diskfile, indent=4, default=colorFontToJSON)
    except Exception as exc:
        logging.error('Error creating a sample skin at %s. '
                      'Cannot write skin.json: %s', dName, str(exc))

    fName = dName + 'cflow.json'
    try:
        values = {}
        for key, value in _DEFAULT_CFLOW_SETTINGS.items():
            if isinstance(value, QFont):
                values[key] = QFont(_DEFAULT_CFLOW_SETTINGS[key])
            else:
                values[key] = value
        with open(fName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
            json.dump(values, diskfile, indent=4, default=colorFontToJSON)
    except Exception as exc:
        logging.error('Error creating a sample skin at %s. '
                      'Cannot write cflow.json: %s', dName, str(exc))

