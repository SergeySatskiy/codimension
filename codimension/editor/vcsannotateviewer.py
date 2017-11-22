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

"""Annotated VCS viewer implementation"""


import os.path
from ui.qt import (Qt, QSize, QPoint, pyqtSignal, QToolBar, QFont,
                   QFontMetrics, QHBoxLayout, QWidget, QAction, QSizePolicy,
                   QToolTip)
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.fileutils import getFileProperties, isPythonMime
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from utils.importutils import getImportsList, resolveImports
from ui.importlist import ImportListWidget
from .texteditor import TextEditor


class VCSAnnotateViewer(TextEditor):

    """VCS blame view"""

    LINENUM_MARGIN = 0      # Matches the text editor
    REVISION_MARGIN = 1     # Introduced here
    FOLDING_MARGIN = 2      # Matches the text editor
    MESSAGES_MARGIN = 3     # Matches the text editor

    def __init__(self, parent):
        self.__maxLength = None

        TextEditor.__init__(self, parent, None)
        self.__revisionTooltipShown = False
        self.__initAlterRevisionMarker()
        self._updateDwellingTime()

    def __initAlterRevisionMarker(self):
        skin = GlobalData().skin
        self.__alterMarker = self.markerDefine(QsciScintilla.Background)
        self.setMarkerBackgroundColor(skin.revisionAlterPaper,
                                      self.__alterMarker)

    def setAnnotatedContent(self, shortName, text, lineRevisions, revisionInfo):
        """Sets the content"""
        self.__lineRevisions = lineRevisions
        self.__revisionInfo = revisionInfo

        fileType = self._parent.getFileType()
        if fileType in [DesignerFileType, LinguistFileType]:
            # special treatment for Qt-Linguist and Qt-Designer files
            self.encoding = 'latin-1'
        else:
            text, self.encoding = decode(text)

        self.detectEolString(text)
        self.setText(text)
        self.bindLexer(shortName, fileType)

        self.setModified(False)
        self.setReadOnly(True)

        self.__initAnnotateMargins()
        self.__setRevisionText()

    def __setRevisionText(self):
        """Sets the revision margin text"""
        for revNumber in self.__revisionInfo:
            author = self.__revisionInfo[revNumber]['author']
            if '@' in author:
                # Most probably this is an e-mail address. Leave just name.
                self.__revisionInfo[revNumber]['shortAuthor'] = author.split('@')[0]
            else:
                self.__revisionInfo[revNumber]['shortAuthor'] = author

        skin = GlobalData().skin
        revisionMarginFont = QFont(skin.lineNumFont)
        revisionMarginFont.setItalic(True)
        style = QsciStyle(-1, "Revision margin style",
                          skin.revisionMarginColor,
                          skin.revisionMarginPaper, revisionMarginFont)

        lineNumber = 0
        self.__maxLength = -1

        # Altering line background support
        currentRevision = -1
        needMarker = True

        for lineRevision in self.__lineRevisions:
            if lineRevision in self.__revisionInfo:
                marginText = " " + ":".join([str(lineRevision),
                    self.__revisionInfo[lineRevision]['shortAuthor']])
            else:
                marginText = " " + str(lineRevision)
            textLength = len(marginText)
            if textLength > self.__maxLength:
                self.__maxLength = textLength
            self.setMarginText(lineNumber, marginText, style)

            # Set the line background if needed
            if lineRevision != currentRevision:
                currentRevision = lineRevision
                needMarker = not needMarker
            if needMarker:
                self.markerAdd(lineNumber, self.__alterMarker)

            lineNumber += 1

        self.setRevisionMarginWidth()

    def detectRevisionMarginWidth(self):
        """Caculates the margin width depending on
           the margin font and the current zoom"""
        skin = GlobalData().skin
        font = QFont(skin.lineNumFont)
        font.setPointSize(font.pointSize() + self.getZoom())
        fontMetrics = QFontMetrics(font, self)
        return fontMetrics.width('W' * self.__maxLength) + 3

    def setRevisionMarginWidth(self):
        """Called when zooming is done to keep the width wide enough"""
        if self.__maxLength:
            self.setMarginWidth(self.REVISION_MARGIN,
                                self.detectRevisionMarginWidth())
        else:
            self.setMarginWidth(self.REVISION_MARGIN, 0)

    def __initAnnotateMargins(self):
        """Initializes the editor margins"""
        self.setMarginType(self.REVISION_MARGIN, self.TextMargin)
        self.setMarginMarkerMask(self.REVISION_MARGIN, 0)

        # Together with overriding _marginClicked(...) this
        # prevents selecting a line when the margin is clicked.
        self.setMarginSensitivity(self.REVISION_MARGIN, True)

    def _marginClicked(self, margin, line, modifiers):
        """Handles a click on the margin"""
        return

    def __getRevisionMarginTooltip(self, lineNumber):
        """lineNumber is zero based"""
        revisionNumber = self.__lineRevisions[lineNumber]
        if not revisionNumber in self.__revisionInfo:
            return None

        tooltip = "Revision: " + \
            str(revisionNumber) + "\n" \
            "Author: " + \
            self.__revisionInfo[revisionNumber]['author'] + "\n" \
            "Date: " + \
            str(self.__revisionInfo[revisionNumber]['date'])
        comment = self.__revisionInfo[revisionNumber]['message']
        if comment:
            tooltip += "\nComment: " + comment
        return tooltip

    def _updateDwellingTime(self):
        """There is always something to show"""
        self.SendScintilla(self.SCI_SETMOUSEDWELLTIME, 250)

    def _onDwellStart(self, position, x, y):
        """Triggered when mouse started to dwell"""
        if not self.underMouse():
            return

        marginNumber = self._marginNumber(x)
        if marginNumber == self.REVISION_MARGIN:
            self.__showRevisionTooltip(position, x, y)
        else:
            TextEditor._onDwellStart(self, position, x, y)

    def __showRevisionTooltip(self, position, x, y):
        """Shows the tooltip"""
        # Calculate the line
        pos = self.SendScintilla(self.SCI_POSITIONFROMPOINT, x, y)
        line, posInLine = self.lineIndexFromPosition(pos)

        tooltip = self.__getRevisionMarginTooltip(line)
        if tooltip:
            QToolTip.showText(self.mapToGlobal(QPoint(x, y)), tooltip)
            self.__revisionTooltipShown = True

    def _onDwellEnd(self, position, x, y):
        """Triggered when mouse ended to dwell"""
        if self.__revisionTooltipShown:
            self.__revisionTooltipShown = False
            QToolTip.hideText()

    def setLineNumMarginWidth(self):
        """Sets the line number margin widht"""
        TextEditor.setLineNumMarginWidth(self)
        self.setRevisionMarginWidth()

    def _contextMenuAboutToShow(self):
        """Enables/disables the appropriate menu items"""
        self._menuHighlightInOutline.setEnabled(self.isPythonBuffer())

        self.encodingMenu.setEnabled(False)
        self.pylintAct.setEnabled(False)
        self.pymetricsAct.setEnabled(False)
        self.runAct.setEnabled(False)
        self.runParamAct.setEnabled(False)
        self.profileAct.setEnabled(False)
        self.profileParamAct.setEnabled(False)
        self.importsDgmAct.setEnabled(False)
        self.importsDgmParamAct.setEnabled(False)


class VCSAnnotateViewerTabWidget(QWidget, MainWindowTabWidgetBase):

    """VCS annotate viewer tab widget"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent):

        MainWindowTabWidgetBase.__init__(self)
        QWidget.__init__(self, parent)

        self.__viewer = VCSAnnotateViewer(self)
        self.__viewer.sigEscapePressed.connect(self.__onEsc)
        self.__fileName = ""
        self.__shortName = ""

        self.__createLayout()
        self.__viewer.zoomTo(Settings()['zoom'])

    def __onEsc(self):
        """Triggered when Esc is pressed"""
        self.sigEscapePressed.emit()

    def __createLayout(self):
        """Creates the toolbar and layout"""
        # Buttons
        printButton = QAction(getIcon('printer.png'), 'Print', self)
        printButton.triggered.connect(self.__onPrint)
        printButton.setEnabled(False)
        printButton.setVisible(False)

        printPreviewButton = QAction(
            getIcon('printpreview.png'), 'Print preview', self)
        printPreviewButton.triggered.connect(self.__onPrintPreview)
        printPreviewButton.setEnabled(False)
        printPreviewButton.setVisible(False)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # The toolbar
        toolbar = QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        toolbar.setMovable(False)
        toolbar.setAllowedAreas(Qt.RightToolBarArea)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setFixedWidth(28)
        toolbar.setContentsMargins(0, 0, 0, 0)

        toolbar.addAction(printPreviewButton)
        toolbar.addAction(printButton)
        toolbar.addWidget(spacer)

        self.__importsBar = ImportListWidget(self.__viewer)
        self.__importsBar.hide()

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addWidget(self.__viewer)
        hLayout.addWidget(toolbar)

        self.setLayout(hLayout)

    def updateStatus(self):
        """Updates the toolbar buttons status"""
        pass

    def __onPrint(self):
        """Triggered when the print button is pressed"""
        pass

    def __onPrintPreview(self):
        """triggered when the print preview button is pressed"""
        pass

    def setFocus(self):
        """Overridden setFocus"""
        self.__viewer.setFocus()

    def onOpenImport(self):
        """Triggered when Ctrl+I is received"""
        if isPythonMime(self.__editor.mime):
            # Take all the file imports and resolve them
            fileImports = getImportsList(self.__editor.text)
            if not fileImports:
                GlobalData().mainWindow.showStatusBarMessage(
                    "There are no imports")
            else:
                self.__onImportList(self.__fileName, fileImports)

    def __onImportList(self, fileName, imports):
        """Works with a list of imports"""
        # It has already been checked that the file is a Python one
        resolvedList, errors = resolveImports(fileName, imports)
        del errors  # errors are OK here
        if resolvedList:
            # Display the import selection widget
            self.__importsBar.showResolvedImports(resolvedList)
        else:
            GlobalData().mainWindow.showStatusBarMessage(
                "Could not resolve any imports")

    def resizeEvent(self, event):
        """Resizes the import selection dialogue if necessary"""
        QWidget.resizeEvent(self, event)
        self.resizeBars()

    def resizeBars(self):
        """Resize the bars if they are shown"""
        if not self.__importsBar.isHidden():
            self.__importsBar.resize()
        self.__viewer.resizeCalltip()

    def onRunScript(self, action=False):
        return True
    def onRunScriptSettings(self):
        return True
    def onProfileScript(self, action=False):
        return True
    def onProfileScriptSettings(self):
        return True
    def onImportDgm(self, action=None):
        return True
    def onImportDgmTuned(self):
        return True
    def shouldAcceptFocus(self):
        return True

    def setAnnotatedContent(self, shortName, text,
                            lineRevisions, revisionInfo):
        """Sets the content"""
        self.setShortName(shortName)
        self.__viewer.setAnnotatedContent(shortName, text,
                                          lineRevisions, revisionInfo)

    def writeFile(self, fileName):
        """Writes the text to a file"""
        return self.__viewer.writeFile(fileName)

    def updateModificationTime(self, fileName):
        """No need to implement"""
        return

    # Mandatory interface part is below

    def getEditor(self):
        """Provides the editor widget"""
        return self.__viewer

    def isModified(self):
        """Tells if the file is modified"""
        return False

    def getRWMode(self):
        """Tells if the file is read only"""
        return "RO"

    def getMime(self):
        """Provides the file type"""
        return self.__viewer.mime

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.VCSAnnotateViewer

    def getLanguage(self):
        """Tells the content language"""
        lang = self.__viewer.language()
        if lang:
            return lang
        return self.__viewer.mime if self.__viewer.mime else 'n/a'

    def setFileName(self, name):
        """Sets the file name"""
        raise Exception("Setting a file name for "
                        "annotate results is not applicable")

    def getEol(self):
        """Tells the EOL style"""
        return self.__viewer.getEolIndicator()

    def getLine(self):
        """Tells the cursor line"""
        line, _ = self.__viewer.cursorPosition
        return line

    def getPos(self):
        """Tells the cursor column"""
        _, pos = self.__viewer.cursorPosition
        return pos

    def getEncoding(self):
        """Tells the content encoding"""
        return self.__viewer.encoding

    def setEncoding(self, newEncoding):
        """Sets the new editor encoding"""
        self.__viewer.setEncoding(newEncoding)

    def getShortName(self):
        """Tells the display name"""
        return self.__shortName

    def setShortName(self, name):
        """Sets the display name"""
        self.__shortName = name
