#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

" Text editor implementation "


import os.path, logging, urllib2, socket
from subprocess import Popen
import lexer
from PyQt4.Qsci import QsciLexerPython
from scintillawrap import ScintillaWrapper
from PyQt4.QtCore import ( Qt, QFileInfo, SIGNAL, QSize, QUrl, QTimer,
                           QVariant, QRect, QEvent, QPoint, QModelIndex )
from PyQt4.QtGui import ( QApplication, QCursor, QFontMetrics, QToolBar,
                          QActionGroup, QHBoxLayout, QWidget, QAction, QMenu,
                          QSizePolicy, QToolButton, QDialog, QToolTip,
                          QDesktopServices, QFont )
from PyQt4.Qsci import QsciScintilla
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.fileutils import ( detectFileType, DesignerFileType,
                              LinguistFileType, MakefileType, getFileLanguage,
                              UnknownFileType, PythonFileType, Python3FileType )
from utils.encoding import decode, encode, CodingError, supportedCodecs
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.settings import Settings
from utils.misc import getLocaleDateTime
from ui.pylintviewer import PylintViewer
from ui.pymetricsviewer import PymetricsViewer
from diagram.importsdgm import ( ImportsDiagramDialog, ImportDiagramOptions,
                                 ImportsDiagramProgress )
from utils.importutils import ( getImportsList, getImportsInLine, resolveImport,
                                getImportedNameDefinitionLine, resolveImports )
from ui.importlist import ImportListWidget
from ui.outsidechanges import OutsideChangeWidget
from autocomplete.bufferutils import ( getContext, getPrefixAndObject,
                                       getEditorTags, isImportLine,
                                       isStringLiteral, getCallPosition,
                                       getCommaCount )
from autocomplete.completelists import ( getCompletionList, getCalltipAndDoc,
                                         getDefinitionLocation, getOccurrences )
from cdmbriefparser import getBriefModuleInfoFromMemory
from ui.completer import CodeCompleter
from ui.runparams import RunDialog
from utils.run import getCwdCmdEnv, CMD_TYPE_RUN
from ui.findinfiles import ItemToSearchIn, getSearchItemIndex
from debugger.modifiedunsaved import ModifiedUnsavedDialog
from ui.linecounter import LineCounterDialog
from pythontidy.tidy import ( getPythonTidySetting, PythonTidyDriver,
                              getPythonTidySettingFileName )
from pythontidy.tidysettingsdlg import TidySettingsDialog
from profiling.profui import ProfilingProgressDialog
from debugger.bputils import getBreakpointLines
from debugger.breakpoint import Breakpoint
from ui.calltip import Calltip


class TextEditor( ScintillaWrapper ):
    " Text editor implementation "

    matchIndicator    = ScintillaWrapper.INDIC_CONTAINER
    searchIndicator   = ScintillaWrapper.INDIC_CONTAINER + 1
    spellingIndicator = ScintillaWrapper.INDIC_CONTAINER + 2

    textToIterate = ""

    LINENUM_MARGIN = 0
    BPOINT_MARGIN = 1
    FOLDING_MARGIN = 2
    MESSAGES_MARGIN = 3

    def __init__( self, parent, debugger ):

        ScintillaWrapper.__init__( self, parent )

        self.__debugger = debugger

        self.__initMargins()
        self.__initIndicators()
        self.__alterKeyBinding()
        self.__initContextMenu()
        self.__initDebuggerMarkers()

        self.connect( self, SIGNAL( 'SCN_DOUBLECLICK(int,int,int)' ),
                      self.__onDoubleClick )
        self.connect( self, SIGNAL( 'cursorPositionChanged(int,int)' ),
                      self.__onCursorPositionChanged )

        self.connect( self, SIGNAL( 'SCN_DWELLSTART(int,int,int)' ),
                      self._onDwellStart )
        self.connect( self, SIGNAL( 'SCN_DWELLEND(int,int,int)' ),
                      self._onDwellEnd )

        self.connect( self, SIGNAL( 'SCN_MODIFIED(int,int,const char*,int,int,int,int,int,int,int)' ),
                      self.__onSceneModified )
        self.__skipChangeCursor = False

        skin = GlobalData().skin
        self.__openedLine = -1

        self.encoding = 'utf-8'     # default
        self.lexer_ = None

        self.__pyflakesMessages = {}    # marker handle -> error message
        self.ignoreBufferChangedSignal = False  # Changing margin icons also
                                                # generates BufferChanged
                                                # signal which is extra
        self.__pyflakesTooltipShown = False

        self.__breakpoints = {}         # marker handle -> Breakpoint

        self.setPaper( skin.nolexerPaper )
        self.setColor( skin.nolexerColor )
        self.monospacedStyles( skin.nolexerFont )

        self.setAttribute( Qt.WA_DeleteOnClose )
        self.setAttribute( Qt.WA_KeyCompression )
        self.setUtf8( True )
        self.setFocusPolicy( Qt.StrongFocus )
        self.setIndentationWidth( 4 )
        self.setTabWidth( 4 )
        self.setEdgeColumn( Settings().editorEdge )

        self.setMatchedBraceBackgroundColor( skin.matchedBracePaper )
        self.setMatchedBraceForegroundColor( skin.matchedBraceColor )
        self.setUnmatchedBraceBackgroundColor( skin.unmatchedBracePaper )
        self.setUnmatchedBraceForegroundColor( skin.unmatchedBraceColor )
        self.setIndentationGuidesBackgroundColor( skin.indentGuidePaper )
        self.setIndentationGuidesForegroundColor( skin.indentGuideColor )

        self.updateSettings()

        # Completion support
        self.__completionObject = ""
        self.__completionPrefix = ""
        self.__completionLine = -1
        self.__completionPos = -1
        self.__completer = CodeCompleter( self )
        self.__inCompletion = False
        self.connect( self.__completer, SIGNAL( "activated(const QString &)" ),
                      self.insertCompletion )

        self.connect( self,
                      SIGNAL( 'marginClicked(int, int, Qt::KeyboardModifiers)' ),
                      self._marginClicked )

        # Calltip support
        self.__calltip = None
        self.__callPosition = None
        self.__calltipTimer = QTimer( self )
        self.__calltipTimer.setSingleShot( True )
        self.connect( self.__calltipTimer, SIGNAL( 'timeout()' ), self.__onCalltipTimer )

        # Breakpoint support
        self.__inLinesChanged = False
        if self.__debugger:
            bpointModel = self.__debugger.getBreakPointModel()
            self.connect( bpointModel,
                          SIGNAL( "rowsAboutToBeRemoved(const QModelIndex &, int, int)" ),
                          self.__deleteBreakPoints )
            self.connect( bpointModel,
                          SIGNAL( "dataAboutToBeChanged(const QModelIndex &, const QModelIndex &)" ),
                          self.__breakPointDataAboutToBeChanged )
            self.connect( bpointModel,
                          SIGNAL( "dataChanged(const QModelIndex &, const QModelIndex &)" ),
                          self.__changeBreakPoints )
            self.connect( bpointModel,
                          SIGNAL( "rowsInserted(const QModelIndex &, int, int)" ),
                          self.__addBreakPoints )

        self.installEventFilter( self )
        return

    def eventFilter( self, obj, event ):
        " Event filter to catch shortcuts on UBUNTU "
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if modifiers == Qt.ShiftModifier | Qt.ControlModifier:
                if key == Qt.Key_F1:
                    return self.onCallHelp()
                if key == Qt.Key_T:
                    return self.onJumpToTop()
                if key == Qt.Key_M:
                    return self.onJumpToMiddle()
                if key == Qt.Key_B:
                    return self.onJumpToBottom()
                if key == Qt.Key_Up:
                    return self.__onCtrlShiftUp()
                if key == Qt.Key_Down:
                    return self.__onCtrlShiftDown()
            if modifiers == Qt.ShiftModifier:
                if key == Qt.Key_Delete:
                    return self.onShiftDel()
                if key == Qt.Key_Tab or key == Qt.Key_Backtab:
                    return self.__onDedent()
                if key == Qt.Key_End:
                    return self.__onShiftEnd()
                if key == Qt.Key_Home:
                    return self.__onShiftHome()
            if modifiers == Qt.ControlModifier:
                if key == Qt.Key_X:
                    return self.onShiftDel()
                if key in [ Qt.Key_C, Qt.Key_Insert ]:
                    return self.onCtrlC()
                if key == ord( "'" ):               # Ctrl + '
                    return self.__onHighlight()
                if key == Qt.Key_Period:
                    return self.__onNextHighlight() # Ctrl + .
                if key == Qt.Key_Comma:
                    return self.__onPrevHighlight() # Ctrl + ,
                if key == Qt.Key_M:
                    return self.onCommentUncomment()
                if key == Qt.Key_Space:
                    return self.onAutoComplete()
                if key == Qt.Key_F1:
                    return self.onTagHelp()
                if key == Qt.Key_Backslash:
                    return self.onGotoDefinition()
                if key == Qt.Key_BracketRight:
                    return self.onOccurences()
                if key == Qt.Key_Slash:
                    return self.onShowCalltip()
                if key == Qt.Key_Minus:
                    return self.parent().onZoomOut()
                if key == Qt.Key_Equal:
                    return self.parent().onZoomIn()
                if key == Qt.Key_0:
                    return self.parent().onZoomReset()
                if key == Qt.Key_L:
                    return self.parent().onPylint()
                if key == Qt.Key_K:
                    return self.parent().onPymetrics()
                if key == Qt.Key_I:
                    return self.parent().onOpenImport()
                if key == Qt.Key_Home:
                    return self.onFirstChar()
                if key == Qt.Key_End:
                    return self.onLastChar()
            if modifiers == Qt.AltModifier:
                if key == Qt.Key_Left:
                    return self.__onWordPartLeft()
                if key == Qt.Key_Right:
                    return self.__onWordPartRight()
                if key == Qt.Key_Up:
                    return self.__onParagraphUp()
                if key == Qt.Key_Down:
                    return self.__onParagraphDown()
                if key == Qt.Key_U:
                    return self.onScopeBegin()
            if modifiers == Qt.KeypadModifier | Qt.ControlModifier:
                if key == Qt.Key_Minus:
                    return self.parent().onZoomOut()
                if key == Qt.Key_Plus:
                    return self.parent().onZoomIn()
                if key == Qt.Key_0:
                    return self.parent().onZoomReset()
            if key == Qt.Key_Home and modifiers == Qt.NoModifier:
                return self.__onHome()
            if key == Qt.Key_End and modifiers == Qt.NoModifier:
                return self.__onEnd()

        return ScintillaWrapper.eventFilter( self, obj, event )

    def wheelEvent( self, event ):
        " Mouse wheel event "
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if event.delta() > 0:
                self.parent().onZoomIn()
            else:
                self.parent().onZoomOut()
        else:
            ScintillaWrapper.wheelEvent( self, event )
        return

    def __initContextMenu( self ):
        " Initializes the context menu "
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager

        self.__menu = QMenu( self )
        self.__menuUndo = self.__menu.addAction(
                                    PixmapCache().getIcon( 'undo.png' ),
                                    '&Undo', self.onUndo, "Ctrl+Z" )
        self.__menuRedo = self.__menu.addAction(
                                    PixmapCache().getIcon( 'redo.png' ),
                                    '&Redo', self.onRedo, "Ctrl+Shift+Z" )
        self.__menu.addSeparator()
        self.__menuCut = self.__menu.addAction(
                                    PixmapCache().getIcon( 'cutmenu.png' ),
                                    'Cu&t', self.onShiftDel, "Ctrl+X" )
        self.__menuCopy = self.__menu.addAction(
                                    PixmapCache().getIcon( 'copymenu.png' ),
                                    '&Copy', self.onCtrlC, "Ctrl+C" )
        self.__menuPaste = self.__menu.addAction(
                                    PixmapCache().getIcon( 'pastemenu.png' ),
                                    '&Paste', self.paste, "Ctrl+V" )
        self.__menuSelectAll = self.__menu.addAction(
                                PixmapCache().getIcon( 'selectallmenu.png' ),
                                'Select &all', self.selectAll, "Ctrl+A" )
        self.__menu.addSeparator()
        menu = self.__menu.addMenu( self.__initEncodingMenu() )
        menu.setIcon( PixmapCache().getIcon( 'textencoding.png' ) )
        self.__menu.addSeparator()
        menu = self.__menu.addMenu( self.__initToolsMenu() )
        menu.setIcon( PixmapCache().getIcon( 'toolsmenu.png' ) )
        self.__menu.addSeparator()
        menu = self.__menu.addMenu( self.__initDiagramsMenu() )
        menu.setIcon( PixmapCache().getIcon( 'diagramsmenu.png' ) )
        self.__menu.addSeparator()
        self.__menuOpenAsFile = self.__menu.addAction(
                                PixmapCache().getIcon( 'filemenu.png' ),
                                'O&pen as file', self.openAsFile )
        self.__menuDownloadAndShow = self.__menu.addAction(
                                PixmapCache().getIcon( 'filemenu.png' ),
                                'Do&wnload and show', self.downloadAndShow )
        self.__menuOpenInBrowser = self.__menu.addAction(
                                PixmapCache().getIcon( 'homepagemenu.png' ),
                                'Open in browser', self.openInBrowser )
        self.__menu.addSeparator()
        self.__menuHighlightInPrj = self.__menu.addAction(
                                PixmapCache().getIcon( "highlightmenu.png" ),
                                "&Highlight in project browser",
                                editorsManager.onHighlightInPrj )
        self.__menuHighlightInFS = self.__menu.addAction(
                                PixmapCache().getIcon( "highlightmenu.png" ),
                                "H&ighlight in file system browser",
                                editorsManager.onHighlightInFS )
        self.__menuHighlightInOutline = self.__menu.addAction(
                                PixmapCache().getIcon( "highlightmenu.png" ),
                                "Highlight in &outline browser",
                                self.highlightInOutline )

        self.connect( self.__menu, SIGNAL( "aboutToShow()" ),
                      self.__contextMenuAboutToShow )

        # Plugins support
        self.__pluginMenuSeparator = self.__menu.addSeparator()
        editorsManager = self.parent().parent()
        registeredMenus = editorsManager.getPluginMenus()
        if registeredMenus:
            for path in registeredMenus:
                self.__menu.addMenu( registeredMenus[ path ] )
        else:
            self.__pluginMenuSeparator.setVisible( False )

        self.connect( editorsManager, SIGNAL( 'PluginContextMenuAdded' ),
                      self.__onPluginMenuAdded )
        self.connect( editorsManager, SIGNAL( 'PluginContextMenuRemoved' ),
                      self.__onPluginMenuRemoved )
        return

    def __onPluginMenuAdded( self, menu, count ):
        " Triggered when a new menu was added "
        self.__menu.addMenu( menu )
        self.__pluginMenuSeparator.setVisible( True )
        return

    def __onPluginMenuRemoved( self, menu, count ):
        " Triggered when a menu was deleted "
        self.__menu.removeAction( menu.menuAction() )
        self.__pluginMenuSeparator.setVisible( count != 0 )
        return

    def _marginNumber( self, xPos ):
        " Calculates the margin number based on a x position "
        width = 0
        for margin in xrange( 5 ):
            width += self.marginWidth( margin )
            if xPos <= width:
                return margin
        return None

    def _marginClicked( self, margin, line, modifiers ):
        " Triggered when a margin is clicked "
        if margin == self.BPOINT_MARGIN:
            self.__breakpointMarginClicked( line + 1 )
        return

    def __initEncodingMenu( self ):
        " Creates the encoding menu "
        self.supportedEncodings = {}
        self.encodingMenu = QMenu( "&Encoding" )
        self.encodingsActGrp = QActionGroup( self )
        for encoding in sorted( supportedCodecs ):
            act = self.encodingMenu.addAction( encoding )
            act.setCheckable( True )
            act.setData( QVariant( encoding ) )
            self.supportedEncodings[ encoding ] = act
            self.encodingsActGrp.addAction( act )
        self.connect( self.encodingMenu, SIGNAL( 'triggered(QAction *)' ),
                      self.__encodingsMenuTriggered )
        return self.encodingMenu

    def __encodingsMenuTriggered( self, act ):
        " Triggered when encoding is selected "
        encoding = unicode( act.data().toString() )
        self.setEncoding( encoding + "-selected" )
        return

    @staticmethod
    def __normalizeEncoding( enc ):
        " Strips display purpose suffix "
        return enc.replace( "-default", "" ) \
                  .replace( "-guessed", "" ) \
                  .replace( "-selected", "" )

    def __initToolsMenu( self ):
        " Creates the tools menu "
        self.toolsMenu = QMenu( "Too&ls" )
        self.pylintAct = self.toolsMenu.addAction(
                            PixmapCache().getIcon( 'pylint.png' ),
                            'pylint', self.parent().onPylint, "Ctrl+L" )
        self.pylintAct.setEnabled( False )
        self.pymetricsAct = self.toolsMenu.addAction(
                            PixmapCache().getIcon( 'metrics.png' ),
                            'pymetrics', self.parent().onPymetrics, "Ctrl+K" )
        self.toolsMenu.addSeparator()
        self.runAct = self.toolsMenu.addAction(
                            PixmapCache().getIcon( 'run.png' ),
                            'Run script', self.parent().onRunScript )
        self.runParamAct = self.toolsMenu.addAction(
                            PixmapCache().getIcon( 'paramsmenu.png' ),
                            'Set parameters and run',
                            self.parent().onRunScriptSettings )
        self.toolsMenu.addSeparator()
        self.profileAct = self.toolsMenu.addAction(
                            PixmapCache().getIcon( 'profile.png' ),
                            'Profile script', self.parent().onProfileScript )
        self.profileParamAct = self.toolsMenu.addAction(
                            PixmapCache().getIcon( 'paramsmenu.png' ),
                            'Set parameters and profile',
                            self.parent().onProfileScriptSettings )
        return self.toolsMenu

    def __initDiagramsMenu( self ):
        " Creates the diagrams menu "
        self.diagramsMenu = QMenu( "&Diagrams" )
        self.importsDgmAct = self.diagramsMenu.addAction(
                                PixmapCache().getIcon( 'importsdiagram.png' ),
                                'Imports diagram',
                                self.parent().onImportDgm )
        self.importsDgmParamAct = self.diagramsMenu.addAction(
                                PixmapCache().getIcon( 'paramsmenu.png' ),
                                'Fine tuned imports diagram',
                                self.parent().onImportDgmTuned )
        return self.diagramsMenu

    def contextMenuEvent( self, event ):
        " Called just before showing a context menu "
        event.accept()
        if self._marginNumber( event.x() ) is None:
            self.__menuUndo.setEnabled( self.isUndoAvailable() )
            self.__menuRedo.setEnabled( self.isRedoAvailable() )
            self.__menuPaste.setEnabled( QApplication.clipboard().text() != "" )

            # Check the proper encoding in the menu
            fileType = self.parent().getFileType()
            fileName = self.parent().getFileName()
            if fileType in [ DesignerFileType, LinguistFileType ]:
                self.encodingMenu.setEnabled( False )
            else:
                self.encodingMenu.setEnabled( True )
                encoding = self.__normalizeEncoding( self.encoding )
                if encoding in self.supportedEncodings:
                    self.supportedEncodings[ encoding ].setChecked( True )

            self.__menuOpenAsFile.setEnabled( self.openAsFileAvailable() )
            self.__menuDownloadAndShow.setEnabled(
                                        self.downloadAndShowAvailable() )
            self.__menuOpenInBrowser.setEnabled(
                                        self.downloadAndShowAvailable() )
            self.__menuHighlightInPrj.setEnabled(
                        os.path.isabs( fileName ) and
                        GlobalData().project.isLoaded() and
                        GlobalData().project.isProjectFile( fileName ) )
            self.__menuHighlightInFS.setEnabled( os.path.isabs( fileName ) )
            self.__menu.popup( event.globalPos() )
        else:
            # Menu for a margin
            pass
        return

    def openAsFileAvailable( self ):
        " True if there is something to try to open as a file "
        importLine, line = isImportLine( self )
        if importLine:
            return False
        selectedText = str( self.selectedText() ).strip()
        if selectedText:
            return '\n' not in selectedText and \
                   '\r' not in selectedText

        currentWord = str( self.getCurrentWord() ).strip()
        return currentWord != ""

    def downloadAndShowAvailable( self ):
        " True if download and show available "
        importLine, line = isImportLine( self )
        if importLine:
            return False
        selectedText = str( self.selectedText() ).strip()
        if not selectedText:
            return False

        if '\n' in selectedText or '\r' in selectedText:
            # Not a single line selection
            return False

        return selectedText.startswith( 'http://' ) or \
               selectedText.startswith( 'www.' )


    def focusInEvent( self, event ):
        " Enable Shift+Tab when the focus is received "
        if not self.parent().shouldAcceptFocus():
            self.parent().setFocus()
            return
        return ScintillaWrapper.focusInEvent( self, event )

    def focusOutEvent( self, event ):
        " Disable Shift+Tab when the focus is lost "
        self.__completer.hide()
        if not self.__inCompletion:
            self.__resetCalltip()
        return ScintillaWrapper.focusOutEvent( self, event )

    def updateSettings( self ):
        " Updates the editor settings "
        settings = Settings()

        if settings.verticalEdge:
            self.setEdgeMode( QsciScintilla.EdgeLine )
            self.setEdgeColor( GlobalData().skin.edgeColor )
        else:
            self.setEdgeMode( QsciScintilla.EdgeNone )

        if settings.showSpaces:
            self.setWhitespaceVisibility( QsciScintilla.WsVisible )
        else:
            self.setWhitespaceVisibility( QsciScintilla.WsInvisible )

        if settings.lineWrap:
            self.setWrapMode( QsciScintilla.WrapWord )
        else:
            self.setWrapMode( QsciScintilla.WrapNone )

        # Moving the cursor and letting messages be processed allows the
        # bracing highlight be switched on/off properly even if the cursor is
        # currently on the highlighted position
        oldLine, oldPos = self.getCursorPosition()
        self.setCursorPosition( oldLine, 0 )
        QApplication.processEvents()
        if settings.showBraceMatch:
            self.setBraceMatching( QsciScintilla.StrictBraceMatch )
        else:
            self.setBraceMatching( QsciScintilla.NoBraceMatch )
        QApplication.processEvents()
        self.setCursorPosition( oldLine, oldPos )

        self.setEolVisibility( settings.showEOL )
        self.setAutoIndent( settings.autoIndent )
        self.setBackspaceUnindents( settings.backspaceUnindent )
        self.setTabIndents( settings.tabIndents )
        self.setIndentationGuides( settings.indentationGuides )
        self.setCurrentLineHighlight( settings.currentLineVisible,
                                      GlobalData().skin.currentLinePaper )
        return

    def detectLineNumMarginWidth( self ):
        """ Caculates the margin width depending on
            the margin font and the current zoom """
        skin = GlobalData().skin
        font = QFont( skin.lineNumFont )
        font.setPointSize( font.pointSize() + self.zoom )
        # The second parameter of the QFontMetrics is essential!
        # If it is not there then the width is not calculated properly.
        fontMetrics = QFontMetrics( font, self )
        return fontMetrics.width( '8888' ) + 5

    def setLineNumMarginWidth( self ):
        " Called when zooming is done to keep the width enough for 4 digits "
        self.setMarginWidth( self.LINENUM_MARGIN,
                             self.detectLineNumMarginWidth() )
        return

    def __initMargins( self ):
        " Initializes the editor margins "

        # The supported margins: line numbers (4 digits), bookmarks, folding

        # reset standard margins settings
        for margin in xrange( 5 ):
            self.setMarginLineNumbers( margin, False )
            self.setMarginMarkerMask( margin, 0 )
            self.setMarginWidth( margin, 0 )
            self.setMarginSensitivity( margin, False )

        skin = GlobalData().skin
        self.setMarginsBackgroundColor( skin.marginPaper )
        self.setMarginsForegroundColor( skin.marginColor )

        # Set margin 0 for line numbers
        self.setMarginsFont( skin.lineNumFont )
        self.setMarginLineNumbers( self.LINENUM_MARGIN, True )

        # Setup break point margin
        self.setMarginWidth( self.BPOINT_MARGIN, 16 )

        # Setup messages margin
        self.setMarginWidth( self.MESSAGES_MARGIN, 16 )

        # Setup folding margin
        self.setMarginWidth( self.FOLDING_MARGIN, 16 )
        self.setFolding( QsciScintilla.PlainFoldStyle, self.FOLDING_MARGIN )
        self.setFoldMarginColors( skin.foldingColor,
                                  skin.foldingPaper )

        # Setup margin markers
        self.__pyflakesMsgMarker = self.markerDefine(
                    PixmapCache().getPixmap( 'pyflakesmsgmarker.png' ) )
        self.__dbgMarker = self.markerDefine(
                    PixmapCache().getPixmap( 'dbgcurrentmarker.png' ) )
        self.__excptMarker = self.markerDefine(
                    PixmapCache().getPixmap( 'dbgexcptmarker.png' ) )
        self.__bpointMarker = self.markerDefine(
                    PixmapCache().getPixmap( 'dbgbpointmarker.png' ) )
        self.__tempbpointMarker = self.markerDefine(
                    PixmapCache().getPixmap( 'dbgtmpbpointmarker.png' ) )
        self.__disbpointMarker = self.markerDefine(
                    PixmapCache().getPixmap( 'dbgdisbpointmarker.png' ) )

        marginMask = ( 1 << self.__pyflakesMsgMarker |
                       1 << self.__dbgMarker |
                       1 << self.__excptMarker )
        self.setMarginMarkerMask( self.MESSAGES_MARGIN, marginMask )
        self.setMarginSensitivity( self.MESSAGES_MARGIN, True )

        self.__bpointMarginMask = ( 1 << self.__bpointMarker |
                                    1 << self.__tempbpointMarker |
                                    1 << self.__disbpointMarker )
        self.setMarginMarkerMask( self.BPOINT_MARGIN, self.__bpointMarginMask )
        self.setMarginSensitivity( self.BPOINT_MARGIN, True )
        return

    def __initDebuggerMarkers( self ):
        " Initializes debugger related markers "
        skin = GlobalData().skin
        self.__currentDebuggerLineMarker = self.markerDefine(
                                                    QsciScintilla.Background )
        self.setMarkerForegroundColor( skin.debugCurrentLineMarkerColor,
                                       self.__currentDebuggerLineMarker )
        self.setMarkerBackgroundColor( skin.debugCurrentLineMarkerPaper,
                                       self.__currentDebuggerLineMarker )

        self.__exceptionLineMarker = self.markerDefine(
                                                    QsciScintilla.Background )
        self.setMarkerForegroundColor( skin.debugExcptLineMarkerColor,
                                       self.__exceptionLineMarker )
        self.setMarkerBackgroundColor( skin.debugExcptLineMarkerPaper,
                                       self.__exceptionLineMarker )
        return

    def highlightCurrentDebuggerLine( self, line, asException ):
        " Highlights the current debugger line "
        if asException:
            self.markerAdd( line - 1, self.__exceptionLineMarker )
            self.markerAdd( line - 1, self.__excptMarker )
        else:
            self.markerAdd( line - 1, self.__currentDebuggerLineMarker )
            self.markerAdd( line - 1, self.__dbgMarker )
        return

    def clearCurrentDebuggerLine( self ):
        " Removes the current debugger line marker "
        self.markerDeleteAll( self.__currentDebuggerLineMarker )
        self.markerDeleteAll( self.__exceptionLineMarker )
        self.markerDeleteAll( self.__dbgMarker )
        self.markerDeleteAll( self.__excptMarker )
        return

    def __convertIndicator( self, value ):
        " Converts an indicator style from a config file to the scintilla constant "
        indicatorStyles = { 0:  self.INDIC_PLAIN,
                            1:  self.INDIC_SQUIGGLE,
                            2:  self.INDIC_TT,
                            3:  self.INDIC_DIAGONAL,
                            4:  self.INDIC_STRIKE,
                            5:  self.INDIC_HIDDEN,
                            6:  self.INDIC_BOX,
                            7:  self.INDIC_ROUNDBOX }
        # Sick! Some scintilla versions are so old that they don't have the
        # indicators below...
        if hasattr( self, "INDIC_STRAIGHTBOX" ):
            indicatorStyles[ 8 ] = self.INDIC_STRAIGHTBOX
        if hasattr( self, "INDIC_DASH" ):
            indicatorStyles[ 9 ] = self.INDIC_DASH
        if hasattr( self, "INDIC_DOTS" ):
            indicatorStyles[ 10 ] = self.INDIC_DOTS
        if hasattr( self, "INDIC_SQUIGGLELOW" ):
            indicatorStyles[ 11 ] = self.INDIC_SQUIGGLELOW
        if hasattr( self, "INDIC_DOTBOX" ):
            indicatorStyles[ 12 ] = self.INDIC_DOTBOX
        if hasattr( self, "INDIC_SQUIGGLEPIXMAP" ):
            indicatorStyles[ 13 ] = self.INDIC_SQUIGGLEPIXMAP
        if hasattr( self, "INDIC_COMPOSITIONTHICK" ):
            indicatorStyles[ 14 ] = self.INDIC_COMPOSITIONTHICK

        if value in indicatorStyles:
            return indicatorStyles[ value ]
        return self.INDIC_ROUNDBOX

    def __initIndicators( self ):
        " Initialises indicators "
        skin = GlobalData().skin

        # Search indicator
        self.SendScintilla( self.SCI_INDICSETSTYLE, self.searchIndicator,
                            self.__convertIndicator( skin.searchMarkStyle ) )
        self.SendScintilla( self.SCI_INDICSETALPHA, self.searchIndicator,
                            skin.searchMarkAlpha )
        if hasattr( self, "SCI_INDICSETOUTLINEALPHA" ):
            self.SendScintilla( self.SCI_INDICSETOUTLINEALPHA, self.searchIndicator,
                                skin.searchMarkOutlineAlpha )
        self.SendScintilla( self.SCI_INDICSETUNDER, self.searchIndicator,
                            True )
        self.SendScintilla( self.SCI_INDICSETFORE, self.searchIndicator,
                            skin.searchMarkColor )

        self.SendScintilla( self.SCI_INDICSETSTYLE, self.matchIndicator,
                            self.__convertIndicator( skin.matchMarkStyle ) )
        self.SendScintilla( self.SCI_INDICSETALPHA, self.matchIndicator,
                            skin.matchMarkAlpha )
        if hasattr( self, "SCI_INDICSETOUTLINEALPHA" ):
            self.SendScintilla( self.SCI_INDICSETOUTLINEALPHA, self.matchIndicator,
                                skin.matchMarkOutlineAlpha )
        self.SendScintilla( self.SCI_INDICSETUNDER, self.matchIndicator,
                            True )
        self.SendScintilla( self.SCI_INDICSETFORE, self.matchIndicator,
                            skin.matchMarkColor )

        # Spelling indicator
        self.SendScintilla( self.SCI_INDICSETSTYLE, self.spellingIndicator,
                            self.INDIC_SQUIGGLE )
        self.SendScintilla( self.SCI_INDICSETALPHA, self.spellingIndicator,
                            skin.spellingMarkAlpha )
        self.SendScintilla( self.SCI_INDICSETUNDER, self.spellingIndicator,
                            True )
        self.SendScintilla( self.SCI_INDICSETFORE, self.spellingIndicator,
                            skin.spellingMarkColor )
        return

    def __alterKeyBinding( self ):
        " Disable some unwanted key bindings "
        ctrl  = self.SCMOD_CTRL << 16
        shift = self.SCMOD_SHIFT << 16
        alt = self.SCMOD_ALT << 16

        # Disable default Ctrl+L (line deletion)
        self.SendScintilla( self.SCI_CLEARCMDKEY, ord( 'L' ) + ctrl )
        # Set Alt+Shift+HOME to select till position 0
        altshift = alt + shift
        self.SendScintilla( self.SCI_ASSIGNCMDKEY,
                            self.SCK_HOME  + altshift, self.SCI_HOMERECTEXTEND )
        return

    def bindLexer( self, fileName, fileType ):
        " Sets the correct lexer depending on language "

        if self.lexer_ is not None and \
           (self.lexer_.lexer() == "container" or self.lexer_.lexer() is None):
            self.disconnect( self, SIGNAL( "SCN_STYLENEEDED(int)" ),
                             self.__styleNeeded )

        self.lexer_ = lexer.getLexerByType( fileType, fileName, self )
        skin = GlobalData().skin
        if self.lexer_ is not None:
            self.lexer_.setDefaultPaper( skin.nolexerPaper )
            self.lexer_.setDefaultColor( skin.nolexerColor )
            self.lexer_.setDefaultFont( skin.nolexerFont )
            self.setLexer( self.lexer_ )

            if self.lexer_.lexer() == "container" or \
               self.lexer_.lexer() is None:
                self.setStyleBits( self.lexer_.styleBitsNeeded() )
                self.connect( self, SIGNAL( "SCN_STYLENEEDED(int)" ),
                              self.__styleNeeded )

            # now set the lexer properties
            self.lexer_.initProperties()

            # initialize the auto indent style of the lexer
            ais = self.lexer_.autoIndentStyle()

        self.setIndentationsUseTabs( fileType == MakefileType )

        # Scintilla bug? workaround
        # If a lexer is switched to text-only, the font on margin is lost
        # Set it again
        self.setMarginsBackgroundColor( skin.marginPaper )
        self.setMarginsForegroundColor( skin.marginColor )
        self.setMarginsFont( skin.lineNumFont )
        return

    def __styleNeeded( self, position ):
        " Handles the need for more styling "
        self.lexer_.styleText( self.getEndStyled(), position )
        return

    def setEncoding( self, newEncoding ):
        " Sets the required encoding for the buffer "
        if newEncoding == self.encoding:
            return

        encoding = self.__normalizeEncoding( newEncoding )
        if encoding not in supportedCodecs:
            logging.warning( "Cannot change encoding to '" +
                             newEncoding + "'. "
                             "Supported encodings are: " +
                             ", ".join( sorted( supportedCodecs ) ) )
            return

        self.encoding = newEncoding
        GlobalData().mainWindow.sbEncoding.setText( newEncoding )
        return

    def readFile( self, fileName ):
        " Reads the text from a file "

        fileName = unicode( fileName )
        try:
            f = open( fileName, 'rb' )
        except IOError:
            raise Exception( "Cannot open file " + fileName )

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        fileType = detectFileType( fileName )
        if fileType in [ DesignerFileType, LinguistFileType ]:
            # special treatment for Qt-Linguist and Qt-Designer files
            txt = f.read()
            self.encoding = 'latin-1'
        else:
            content = f.read()
            txt, self.encoding = decode( content )

        f.close()
        self.detectEolString( txt )

        # Hack to avoid breakpoints reset when a file is reload
        self.__breakpoints = {}
        self.setText( txt )

        # perform automatic eol conversion
        self.convertEols( self.eolMode() )
        self.setModified( False )

        # self.extractTasks()
        # self.extractBookmarks()

        QApplication.restoreOverrideCursor()
        return

    def getFileEncoding( self, fileName, fileType ):
        " Provides the file encoding. "
        if fileType in [ DesignerFileType, LinguistFileType ]:
            # special treatment for Qt-Linguist and Qt-Designer files
            return 'latin-1'

        try:
            f = open( unicode( fileName ), 'rb' )
            fewLines = f.read( 512 )
            f.close()
        except IOError:
            raise Exception( "Cannot read file " + fileName +
                             " to detect its encoding")

        txt, encoding = decode( fewLines )
        return encoding

    def writeFile( self, fileName ):
        " Writes the text to a file "

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        if Settings().removeTrailingOnSave:
            self.removeTrailingWhitespaces()
        txt = unicode( self.text() )

        # work around glitch in scintilla: always make sure,
        # that the last line is terminated properly
        eol = self.getLineSeparator()
        if eol:
            if len( txt ) >= len( eol ):
                if txt[ -len( eol ) : ] != eol:
                    txt += eol
            else:
                txt += eol
        try:
            # For liguist and designer file types the latin-1 is enforced
            fileType = detectFileType( fileName, True, True )
            txt, newEncoding = encode( txt, self.encoding,
                                       fileType in [ DesignerFileType,
                                                     LinguistFileType ] )
        except CodingError, exc:
            QApplication.restoreOverrideCursor()
            logging.critical( "Cannot save " + fileName +
                              ". Reason: " + str( exc ) )
            return False

        # Now write text to the file
        fileName = unicode( fileName )
        try:
            f = open( fileName, 'wb' )
            f.write( txt )
            f.close()
        except IOError, why:
            QApplication.restoreOverrideCursor()
            logging.critical( "Cannot save " + fileName +
                              ". Reason: " + str( why ) )
            return False

        self.setEncoding( self.getFileEncoding( fileName, fileType ) )
        self.parent().updateModificationTime( fileName )
        self.parent().setReloadDialogShown( False )
        QApplication.restoreOverrideCursor()
        return True

    def clearSearchIndicators( self ):
        " Hides the search indicator "
        self.clearAllIndicators( self.searchIndicator )
        self.clearAllIndicators( self.matchIndicator )
        return

    def setSearchIndicator( self, startPos, indicLength ):
        " Sets a single search indicator "
        self.setIndicatorRange( self.searchIndicator, startPos, indicLength )
        return

    def markOccurrences( self, indicator, txt,
                         selectionOnly, isRegexp, caseSensitive, wholeWord ):
        " Marks all occurrences of the text with the given indicator "
        lineFrom = 0
        indexFrom = 0
        lineTo = -1
        indexTo = -1

        if selectionOnly:
            lineFrom, indexFrom, lineTo, indexTo = self.getSelection()

        self.clearAllIndicators( indicator )
        found = self.findFirstTarget( txt, isRegexp, caseSensitive, wholeWord,
                                      lineFrom, indexFrom, lineTo, indexTo )
        foundTargets = []
        while found:
            tgtPos, tgtLen = self.getFoundTarget()
            line, pos = self.lineIndexFromPosition( tgtPos )
            foundTargets.append( [ line, pos, tgtLen ] )
            self.setIndicatorRange( indicator, tgtPos, tgtLen )
            found = self.findNextTarget()
        return foundTargets

    def getTargets( self, txt,
                    isRegexp, caseSensitive, wholeWord,
                    lineFrom, indexFrom, lineTo, indexTo ):
        " Provides a list of the targets start points and the target length "
        found = self.findFirstTarget( txt, isRegexp, caseSensitive, wholeWord,
                                      lineFrom, indexFrom, lineTo, indexTo )
        foundTargets = []
        while found:
            tgtPos, tgtLen = self.getFoundTarget()
            line, pos = self.lineIndexFromPosition( tgtPos )
            foundTargets.append( [ line, pos, tgtLen ] )
            found = self.findNextTarget()
        return foundTargets

    def highlightMatch( self, text,
                        originLine, originPos,
                        isRegexp, caseSensitive, wholeWord,
                        respectSelection = False, highlightFirst = True ):
        """ - Highlight all the matches
            - The first one is highlighted special way if requested
            - Provides the found target position if so """
        self.clearSearchIndicators()

        status = self.hasSelectedText() and respectSelection
        if status:
            line1, index1, line2, index2 = self.getSelection()
            if line1 == line2:
                status = False
        if status:
            # Search within the selection
            targets = self.markOccurrences( self.searchIndicator,
                                            text, True,
                                            isRegexp, caseSensitive, wholeWord )
            if len( targets ) == 0:
                return [-1, -1, -1]

            # Highlight the first target in a special way
            if highlightFirst:
                tgtPos = self.positionFromLineIndex( targets[ 0 ][ 0 ],
                                                     targets[ 0 ][ 1 ] )
                self.clearIndicatorRange( self.searchIndicator,
                                          tgtPos, targets[ 0 ][ 2 ] )
                self.setIndicatorRange( self.matchIndicator, tgtPos,
                                        targets[ 0 ][ 2 ] )
            return [targets[ 0 ][ 0 ], targets[ 0 ][ 1 ], targets[ 0 ][ 2 ]]

        # There is no selected text, deal with the whole document
        targets = self.markOccurrences( self.searchIndicator,
                                        text, False,
                                        isRegexp, caseSensitive, wholeWord )
        if len( targets ) == 0:
            return [-1, -1, -1]

        # Now, check if the origin pos within a target
        for item in targets:
            if originLine == item[ 0 ]:
                if originPos >= item[ 1 ] and \
                   originPos <= item[ 1 ] + item[ 2 ]:
                    # This is the target to highlight - cursor within the
                    # target
                    if highlightFirst:
                        tgtPos = self.positionFromLineIndex( item[ 0 ],
                                                             item[ 1 ] )
                        self.clearIndicatorRange( self.searchIndicator,
                                                  tgtPos, item[ 2 ] )
                        self.setIndicatorRange( self.matchIndicator, tgtPos,
                                                item[ 2 ] )
                    return [item[ 0 ], item[ 1 ], item[ 2 ]]
                if originPos < item[ 1 ]:
                    # This is the target to highlight - cursor is before the
                    # target
                    if highlightFirst:
                        tgtPos = self.positionFromLineIndex( item[ 0 ],
                                                             item[ 1 ] )
                        self.clearIndicatorRange( self.searchIndicator,
                                                  tgtPos, item[ 2 ] )
                        self.setIndicatorRange( self.matchIndicator, tgtPos,
                                                item[ 2 ] )
                    return [item[ 0 ], item[ 1 ], item[ 2 ]]
            if originLine < item[ 0 ]:
                if highlightFirst:
                    tgtPos = self.positionFromLineIndex( item[ 0 ], item[ 1 ] )
                    self.clearIndicatorRange( self.searchIndicator,
                                              tgtPos, item[ 2 ] )
                    self.setIndicatorRange( self.matchIndicator, tgtPos,
                                            item[ 2 ] )
                return [item[ 0 ], item[ 1 ], item[ 2 ]]

        # Here - nothing is found till the end of the document
        # Take the first from the beginning
        if highlightFirst:
            tgtPos = self.positionFromLineIndex( targets[ 0 ][ 0 ],
                                                 targets[ 0 ][ 1 ] )
            self.setIndicatorRange( self.matchIndicator, tgtPos,
                                    targets[ 0 ][ 2 ] )
            self.setIndicatorRange( self.matchIndicator, tgtPos,
                                    targets[ 0 ][ 2 ] )
        return [targets[ 0 ][ 0 ], targets[ 0 ][ 1 ], targets[ 0 ][ 2 ]]

    def keyPressEvent( self, event ):
        """ Handles the key press events """

        self.__skipChangeCursor = True
        key = event.key()
        if self.__completer.isVisible():
            self.__skipChangeCursor = False
            if key == Qt.Key_Escape:
                self.__completer.hide()
                self.setFocus()
                return
            # There could be backspace or printed characters only
            ScintillaWrapper.keyPressEvent( self, event )
            QApplication.processEvents()
            if key == Qt.Key_Backspace:
                if self.__completionPrefix == "":
                    self.__completer.hide()
                    self.setFocus()
                else:
                    self.__completionPrefix = self.__completionPrefix[ : -1 ]
                    self.__completer.setPrefix( self.__completionPrefix )
            else:
                self.__completionPrefix += event.text()
                self.__completer.setPrefix( self.__completionPrefix )
                if self.__completer.completionCount() == 0:
                    self.__completer.hide()
                    self.setFocus()
        elif key in [ Qt.Key_Enter, Qt.Key_Return ]:
            QApplication.processEvents()
            line, pos = self.getCursorPosition()

            self.beginUndoAction()
            ScintillaWrapper.keyPressEvent( self, event )
            QApplication.processEvents()

            if line == self.__openedLine:
                self.__removeLine( line )
            self.endUndoAction()

            # If the new line has one or more spaces then it is a candidate for
            # automatic trimming
            line, pos = self.getCursorPosition()
            text = self.text( line )
            self.__openedLine = -1
            if len( text ) > 0 and len( text.trimmed() ) == 0:
                self.__openedLine = line

        elif key in [ Qt.Key_Up, Qt.Key_PageUp,
                      Qt.Key_Down, Qt.Key_PageDown ]:
            line, pos = self.getCursorPosition()
            lineToTrim = -1
            if line == self.__openedLine:
                lineToTrim = line

            self.beginUndoAction()
            ScintillaWrapper.keyPressEvent( self, event )
            QApplication.processEvents()

            if lineToTrim != -1:
                line, pos = self.getCursorPosition()
                if line != lineToTrim:
                    # The cursor was really moved to another line
                    self.__removeLine( lineToTrim )
            self.endUndoAction()
            self.__openedLine = -1

        elif key == Qt.Key_Escape:
            self.__resetCalltip()
            self.emit( SIGNAL('ESCPressed') )
            event.accept()

        elif key == Qt.Key_Tab:
            line, pos = self.getCursorPosition()
            if pos != 0:
                previousCharPos = self.positionFromLineIndex( line, pos - 1 )
                char = self.charAt( previousCharPos )
                if char.isalnum() or char in [ '_', '.' ]:
                    self.onAutoComplete()
                    event.accept()
                else:
                    ScintillaWrapper.keyPressEvent( self, event )
            else:
                ScintillaWrapper.keyPressEvent( self, event )
        elif key == Qt.Key_Z and \
            int( event.modifiers() ) == (Qt.ControlModifier + Qt.ShiftModifier):
            event.accept()

        elif key == Qt.Key_ParenLeft:
            if Settings().editorCalltips:
                ScintillaWrapper.keyPressEvent( self, event )
                self.onShowCalltip( False, False )
            else:
                ScintillaWrapper.keyPressEvent( self, event )
        else:
            # Special keyboard keys are delivered as 0 values
            if key != 0:
                self.__openedLine = -1
                ScintillaWrapper.keyPressEvent( self, event )

        self.__skipChangeCursor = False
        return

    def __onCursorPositionChanged( self, line, pos ):
        " Triggered when the cursor changed the position "
        if self.__calltip:
            if self.__calltipTimer.isActive():
                self.__calltipTimer.stop()
            self.__calltipTimer.start( 500 )

        if self.__skipChangeCursor:
            return

        if line == self.__openedLine:
            self.__openedLine = -1
            return

        self.__skipChangeCursor = True
        self.beginUndoAction()
        self.__removeLine( self.__openedLine )
        self.endUndoAction()
        self.__skipChangeCursor = False
        self.__openedLine = -1
        return

    def __removeLine( self, line ):
        " Removes characters from the given line "
        if line < 0:
            return

        currentLine, currentPos = self.getCursorPosition()
        self.setCursorPosition( line, 0 )
        self.deleteLineRight()
        self.setCursorPosition( currentLine, currentPos )
        QApplication.processEvents()
        return

    def getLanguage( self ):
        " Provides the lexer language if it is set "
        if self.lexer_ is not None:
            return self.lexer_.language()
        return "Unknown"

    def getCurrentPosFont( self ):
        " Provides the font of the current character "
        if self.lexer_ is not None:
            font = self.lexer_.font( self.styleAt( self.currentPosition() ) )
        else:
            font = self.font()
        font.setPointSize( font.pointSize() + self.getZoom() )
        return font

    def __onDoubleClick( self, position, line, modifier ):
        " Triggered when the user double clicks in the editor "
        text = self.getCurrentWord()
        if text == "" or text.contains( '\r' ) or text.contains( '\n' ):
            TextEditor.textToIterate = ""
        else:
            TextEditor.textToIterate = text
        self.highlightWord( text )
        return

    def _onDwellStart( self, position, x, y ):
        " Triggered when mouse started to dwell "
        if not self.underMouse():
            return
        marginNumber = self._marginNumber( x )
        if marginNumber != self.MESSAGES_MARGIN:
            return
        if not self.__pyflakesMessages:
            return

        # Calculate the line
        pos = self.SendScintilla( self.SCI_POSITIONFROMPOINT, x, y )
        line, posInLine = self.lineIndexFromPosition( pos )

        if self.markersAtLine( line ) & (1 << self.__pyflakesMsgMarker) == 0:
            return

        handle = self.__markerHandleByLine( line )
        if handle == -1:
            return

        message = self.__pyflakesMessages[ handle ]
        QToolTip.showText( self.mapToGlobal( QPoint( x, y ) ), message )
        self.__pyflakesTooltipShown = True
        return

    def __markerHandleByLine( self, line ):
        for handle in self.__pyflakesMessages.keys():
            if self.SendScintilla( self.SCI_MARKERLINEFROMHANDLE,
                                   handle ) == line:
                return handle
        return -1

    def _onDwellEnd( self, position, x, y ):
        " Triggered when mouse ended to dwell "
        if self.__pyflakesTooltipShown:
            self.__pyflakesTooltipShown = False
            QToolTip.hideText()
        return

    def onFirstChar( self ):
        " Jump to the first character in the buffer "
        self.setCursorPosition( 0, 0 )
        self.ensureLineVisible( 0 )
        self.setHScrollOffset( 0 )
        return True

    def onLastChar( self ):
        " Jump to the last char "
        line = self.lines()
        if line != 0:
            line -= 1
        pos = self.lineLength( line )
        if pos != 0:
            pos -= 1
        self.setCursorPosition( line, pos )
        self.ensureLineVisible( line )
        self.setHScrollOffset( 0 )
        return True

    def highlightWord( self, text ):
        " Highlights the given word with the searchIndicator "
        self.clearAllIndicators( self.matchIndicator )
        self.clearAllIndicators( self.searchIndicator )

        if text == "" or text.contains( '\r' ) or text.contains( '\n' ):
            return

        self.markOccurrences( self.searchIndicator, text,
                              False, False, False, True )
        return

    def __onHighlight( self ):
        " Triggered when Ctrl+' is clicked "
        text = self.getCurrentWord()
        if text == "" or text.contains( '\r' ) or text.contains( '\n' ):
            TextEditor.textToIterate = ""
        else:
            if str( TextEditor.textToIterate ).lower() == str( text ).lower():
                return self.__onNextHighlight()
            TextEditor.textToIterate = text
        self.highlightWord( text )
        return True

    def __onNextHighlight( self ):
        " Triggered when Ctrl+. is clicked "
        if TextEditor.textToIterate == "":
            return self.__onHighlight()

        targets = self.markOccurrences( self.searchIndicator,
                                        TextEditor.textToIterate,
                                        False, False, False, True )
        foundCount = len( targets )
        if foundCount == 0:
            return True

        line, index = self.getCursorPosition()
        if foundCount == 1:
            if line == targets[ 0 ][ 0 ] and \
               index >= targets[ 0 ][ 1 ] and \
               index <= targets[ 0 ][ 1 ] + targets[ 0 ][ 2 ]:
                # The only match and we are within it
                return True

        for target in targets:
            if target[ 0 ] < line:
                continue
            if target[ 0 ] == line:
                lastPos = target[ 1 ] + target[ 2 ]
                if index > lastPos:
                    continue
                if index >= target[ 1 ] and index <= lastPos:
                    # Cursor within this target, we need the next one
                    continue
            # Move the cursor to the target
            self.setCursorPosition( target[ 0 ], target[ 1 ] )
            self.ensureLineVisible( target[ 0 ] )
            return True

        self.setCursorPosition( targets[ 0 ][ 0 ], targets[ 0 ][ 1 ] )
        self.ensureLineVisible( targets[ 0 ][ 0 ] )
        return True

    def __onPrevHighlight( self ):
        " Triggered when Ctrl+, is clicked "
        if TextEditor.textToIterate == "":
            return self.__onHighlight()

        targets = self.markOccurrences( self.searchIndicator,
                                        TextEditor.textToIterate,
                                        False, False, False, True )
        foundCount = len( targets )
        if foundCount == 0:
            return True

        line, index = self.getCursorPosition()
        if foundCount == 1:
            if line == targets[ 0 ][ 0 ] and \
               index >= targets[ 0 ][ 1 ] and \
               index <= targets[ 0 ][ 1 ] + targets[ 0 ][ 2 ]:
                # The only match and we are within it
                return True

        for idx in xrange( foundCount - 1, -1, -1 ):
            target = targets[ idx ]
            if target[ 0 ] > line:
                continue
            if target[ 0 ] == line:
                if index < target[ 1 ]:
                    continue
                if index >= target[ 1 ] and index <= target[ 1 ] + target[ 2 ]:
                    # Cursor within this target, we need the previous one
                    continue
            # Move the cursor to the target
            self.setCursorPosition( target[ 0 ], target[ 1 ] )
            self.ensureLineVisible( target[ 0 ] )
            return True

        last = foundCount - 1
        self.setCursorPosition( targets[ last ][ 0 ], targets[ last ][ 1 ] )
        self.ensureLineVisible( targets[ last ][ 0 ] )
        return True

    def __onDedent( self ):
        " Triggered when Shift+Tab is clicked "
        self.SendScintilla( QsciScintilla.SCI_BACKTAB )
        return True

    def onCommentUncomment( self ):
        " Triggered when Ctrl+M is received "
        if self.isReadOnly():
            return True
        if self.lexer_ is None or not self.lexer_.canBlockComment():
            return True

        commentStr = self.lexer_.commentStr()

        self.beginUndoAction()
        if self.hasSelectedText():
            lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
            if indexTo == 0:
                endLine = lineTo - 1
            else:
                endLine = lineTo

            if self.text( lineFrom ).startsWith( commentStr ):
                # need to uncomment
                for line in xrange( lineFrom, endLine + 1 ):
                    if not self.text( line ).startsWith( commentStr ):
                        continue
                    self.setSelection( line, 0, line, commentStr.length() )
                    self.removeSelectedText()
                self.setSelection( lineFrom, 0, endLine + 1, 0 )
            else:
                # need to comment
                for line in xrange( lineFrom, endLine + 1 ):
                    self.insertAt( commentStr, line, 0 )
                self.setSelection( lineFrom, 0, endLine + 1, 0 )
        else:
            # Detect what we need - comment or uncomment
            line, index = self.getCursorPosition()
            if self.text( line ).startsWith( commentStr ):
                # need to uncomment
                self.setSelection( line, 0, line, commentStr.length() )
                self.removeSelectedText()
            else:
                # need to comment
                self.insertAt( commentStr, line, 0 )
            # Jump to the beginning of the next line
            if self.lines() != line + 1:
                line += 1
            self.setCursorPosition( line, 0 )
            self.ensureLineVisible( line )
        self.endUndoAction()
        return True

    def __onWordPartLeft( self ):
        " Triggered when Alt+Left is received "
        self.SendScintilla( QsciScintilla.SCI_WORDPARTLEFT )
        return True

    def __onWordPartRight( self ):
        " Triggered when Alt+Right is received "
        self.SendScintilla( QsciScintilla.SCI_WORDPARTRIGHT )
        return True

    def __onParagraphUp( self ):
        " Triggered when Alt+Up is received "
        self.SendScintilla( QsciScintilla.SCI_PARAUP )
        return True

    def __onParagraphDown( self ):
        " Triggered when Alt+Down is received "
        self.SendScintilla( QsciScintilla.SCI_PARADOWN )
        return True

    def __onCtrlShiftUp( self ):
        " Triggered when Ctrl+Shift+Up is received "
        self.SendScintilla( QsciScintilla.SCI_PARAUPEXTEND )
        return True

    def __onCtrlShiftDown( self ):
        " Triggered when Ctrl+Shift+Down is received "
        self.SendScintilla( QsciScintilla.SCI_PARADOWNEXTEND )
        return True

    def __onHome( self ):
        " Triggered when HOME is received "
        if Settings().jumpToFirstNonSpace:
            self.SendScintilla( QsciScintilla.SCI_VCHOME )
        else:
            self.SendScintilla( QsciScintilla.SCI_HOMEDISPLAY )
        return True

    def __onShiftHome( self ):
        " Triggered when Shift+HOME is received "
        if Settings().jumpToFirstNonSpace:
            self.SendScintilla( QsciScintilla.SCI_VCHOMEEXTEND )
        else:
            self.SendScintilla( QsciScintilla.SCI_HOMEDISPLAYEXTEND )
        return True

    def __onEnd( self ):
        " Triggered when END is received "
        self.SendScintilla( QsciScintilla.SCI_LINEENDDISPLAY )
        return True

    def __onShiftEnd( self ):
        " Triggered when END is received "
        self.SendScintilla( QsciScintilla.SCI_LINEENDDISPLAYEXTEND )
        return True

    def onShiftDel( self ):
        " Triggered when Shift+Del is received "
        if self.hasSelectedText():
            self.cut()
        else:
            self.SendScintilla( QsciScintilla.SCI_LINECOPY )
            self.SendScintilla( QsciScintilla.SCI_LINEDELETE )
        return True

    def onCtrlC( self ):
        " Triggered when Ctrl+C / Ctrl+Insert is receved "
        if self.hasSelectedText():
            self.copy()
        else:
            self.SendScintilla( QsciScintilla.SCI_LINECOPY )
        return True

    def __detectLineHeight( self ):
        " Sets the self._lineHeight "
        firstVisible = self.firstVisibleLine()
        lastVisible = firstVisible + self.linesOnScreen()
        line, pos = self.getCursorPosition()
        xPos, yPos = self.getCurrentPixelPosition()
        if line > 0 and (line - 1) >= firstVisible \
                    and (line - 1) <= lastVisible:
            self.setCursorPosition( line - 1, 0 )
            xPos1, yPos1 = self.getCurrentPixelPosition()
            self._lineHeight = yPos - yPos1
        else:
            if self.lines() > line + 1 and (line + 1) >= firstVisible \
                                       and (line + 1) <= lastVisible:
                self.setCursorPosition( line + 1, 0 )
                xPos1, yPos1 = self.getCurrentPixelPosition()
                self._lineHeight = yPos1 -yPos
            else:
                # This is the last resort, it provides wrong values
                currentPosFont = self.getCurrentPosFont()
                metric = QFontMetrics( currentPosFont )
                self._lineHeight = metric.lineSpacing()
        self.setCursorPosition( line, pos )
        return

    def __detectCharWidth( self ):
        " Sets the self._charWidth "
        line, pos = self.getCursorPosition()
        xPos, yPos = self.getCurrentPixelPosition()
        if pos > 0:
            self.setCursorPosition( line, pos - 1 )
            xPos1, yPos1 = self.getCurrentPixelPosition()
            self._charWidth = xPos - xPos1
        else:
            if len( self.text( line ) ) > 1:
                self.setCursorPosition( line, pos + 1 )
                xPos1, yPos1 = self.getCurrentPixelPosition()
                self._charWidth = xPos1 - xPos
            else:
                # This is the last resort, it provides wrong values
                currentPosFont = self.getCurrentPosFont()
                metric = QFontMetrics( currentPosFont )
                self._charWidth = metric.boundingRect( "W" ).width()
        self.setCursorPosition( line, pos )
        return

    def onAutoComplete( self ):
        " Triggered when ctrl+space or TAB is clicked "
        if self.isReadOnly():
            return True

        self.__inCompletion = True
        self.__completionObject, \
        self.__completionPrefix = getPrefixAndObject( self )

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            words = list( getEditorTags( self, self.__completionPrefix ) )
            isModName = False
        else:
            text = str( self.text() )
            info = getBriefModuleInfoFromMemory( text )
            context = getContext( self, info )

            words, isModName = getCompletionList( self.parent().getFileName(),
                                                  context,
                                                  self.__completionObject,
                                                  self.__completionPrefix,
                                                  self, text, info )
        QApplication.restoreOverrideCursor()

        if len( words ) == 0:
            self.setFocus()
            self.__inCompletion = False
            return True

        line, pos = self.getCursorPosition()
        if isModName:
            # The prefix should be re-taken because a module name may have '.'
            # in it.
            self.__completionPrefix = str( self.getWord( line, pos,
                                                         1, True, "." ) )

        currentPosFont = self.getCurrentPosFont()
        self.__completer.setWordsList( words, currentPosFont )
        self.__completer.setPrefix( self.__completionPrefix )

        count = self.__completer.completionCount()
        if count == 0:
            self.setFocus()
            self.__inCompletion = False
            return True

        # Make sure the line is visible
        self.ensureLineVisible( line )
        xPos, yPos = self.getCurrentPixelPosition()
        if self.hasSelectedText():
            # Remove the selection as it could be interpreted not as expected
            self.setSelection( line, pos, line, pos )

        if count == 1:
            self.insertCompletion( self.__completer.currentCompletion() )
            self.__inCompletion = False
            return True

        if self._charWidth <= 0:
            self.__detectCharWidth()
        if self._lineHeight <= 0:
            self.__detectLineHeight()

        # All the X Servers I tried have a problem with the line height, so I
        # have some spare points in the height
        cursorRectangle = QRect( xPos, yPos - 2,
                                 self._charWidth, self._lineHeight + 8 )
        self.__completer.complete( cursorRectangle )
        self.__inCompletion = False
        return True

    def onTagHelp( self ):
        " Provides help for an item if available "
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        calltip, docstring = getCalltipAndDoc( self.parent().getFileName(),
                                               self )
        if calltip is None and docstring is None:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage( "Doc is not found" )
            return True

        QApplication.restoreOverrideCursor()
        GlobalData().mainWindow.showTagHelp( calltip, docstring )
        return True

    def onCallHelp( self ):
        " Provides help for the current call "
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        callPosition = getCallPosition( self )
        if callPosition is None:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage( "Not a function call" )
            return True

        calltip, docstring = getCalltipAndDoc( self.parent().getFileName(),
                                               self, callPosition )
        if calltip is None and docstring is None:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage( "Doc is not found" )
            return True

        QApplication.restoreOverrideCursor()
        GlobalData().mainWindow.showTagHelp( calltip, docstring )
        return True

    def onJumpToTop( self ):
        " Jumps to the first position of the first visible line "
        self.setCursorPosition( self.firstVisibleLine(), 0 )
        return True

    def onJumpToMiddle( self ):
        " Jumps to the first position of the line in a middle of the editing area "
        # Count the number of the visible line
        count = 0
        firstVisible = self.firstVisibleLine()
        lastVisible = self.lastVisibleLine()
        candidate = firstVisible
        while candidate <= lastVisible:
            if self.isLineVisible( candidate ):
                count += 1
            candidate += 1

        shift = int( count / 2 )
        jumpTo = firstVisible
        while shift > 0:
            if self.isLineVisible( jumpTo ):
                shift -= 1
            jumpTo += 1
        self.setCursorPosition( jumpTo, 0 )
        return True

    def onJumpToBottom( self ):
        " Jumps to the first position of the last line "
        currentFirstVisible = self.firstVisibleLine()
        self.setCursorPosition( self.lastVisibleLine(), 0 )
        safeLastVisible = self.lastVisibleLine()

        while self.firstVisibleLine() != currentFirstVisible:
            # Here: a partially visible last line caused scrolling. So the cursor
            # needs to be set to the previous visible line
            self.setCursorPosition( currentFirstVisible, 0 )
            safeLastVisible -= 1
            while not self.isLineVisible( safeLastVisible ):
                safeLastVisible -= 1
            self.setCursorPosition( safeLastVisible, 0 )
        return True

    def onGotoDefinition( self ):
        " The user requested a jump to definition "
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return True

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        location = getDefinitionLocation( self.parent().getFileName(),
                                          self )
        QApplication.restoreOverrideCursor()
        if location is None:
            GlobalData().mainWindow.showStatusBarMessage(
                                            "Definition is not found" )
        else:
            if location.resource is None:
                # That was an unsaved yet buffer, but something has been found
                GlobalData().mainWindow.jumpToLine( location.lineno )
            else:
                path = os.path.realpath( location.resource.real_path )
                GlobalData().mainWindow.openFile( path, location.lineno )
        return True

    def onScopeBegin( self ):
        " The user requested jumping to the current scope begin "
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return True

        text = str( self.text() )
        info = getBriefModuleInfoFromMemory( text )
        context = getContext( self, info, True )
        if context.getScope() != context.GlobalScope:
            GlobalData().mainWindow.jumpToLine( context.getLastScopeLine() )
        return True

    def onShowCalltip( self, showMessage = True, showKeyword = True ):
        " The user requested show calltip "
        if self.__calltip is not None:
            self.__resetCalltip()
            return True
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return True

        if self.styleAt( self.currentPosition() ) in [
                                QsciLexerPython.TripleDoubleQuotedString,
                                QsciLexerPython.TripleSingleQuotedString,
                                QsciLexerPython.DoubleQuotedString,
                                QsciLexerPython.SingleQuotedString,
                                QsciLexerPython.UnclosedString ]:
            return True

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        callPosition = getCallPosition( self )
        if callPosition is None:
            QApplication.restoreOverrideCursor()
            self.__resetCalltip()
            if showMessage:
                GlobalData().mainWindow.showStatusBarMessage( "Not a function call" )
            return True

        if not showKeyword and \
           self.styleAt( callPosition ) == QsciLexerPython.Keyword:
            QApplication.restoreOverrideCursor()
            self.__resetCalltip()
            return True

        calltip, docstring = getCalltipAndDoc( self.parent().getFileName(),
                                               self, callPosition, True )
        if calltip is None:
            QApplication.restoreOverrideCursor()
            self.__resetCalltip()
            if showMessage:
                GlobalData().mainWindow.showStatusBarMessage( "Calltip is not found" )
            return True

        currentPos = self.currentPosition()
        commas = getCommaCount( self, callPosition, currentPos )
        self.__calltip = Calltip( self )
        self.__calltip.showCalltip( str( calltip ), commas )
        QApplication.restoreOverrideCursor()

        # Memorize how the tooltip was shown
        self.__callPosition = callPosition
        return True

    def __resetCalltip( self ):
        " Hides the calltip and resets how it was shown "
        self.__calltipTimer.stop()
        if self.__calltip is not None:
            self.__calltip.hide()
            self.__calltip = None
        self.__callPosition = None
        return

    def resizeCalltip( self ):
        " Resizes the calltip if so "
        if self.__calltip:
            self.__calltip.resize()
        return

    def __onCalltipTimer( self ):
        " Handles the calltip update timer "
        if self.__calltip:
            currentPos = self.currentPosition()
            if currentPos < self.__callPosition:
                self.__resetCalltip()
                return
            QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
            callPosition = getCallPosition( self, currentPos )
            if callPosition != self.__callPosition:
                self.__resetCalltip()
            else:
                # It is still the same call, check the commas
                commas = getCommaCount( self, callPosition, currentPos )
                self.__calltip.highlightParameter( commas )
            QApplication.restoreOverrideCursor()
        return

    def onOccurences( self ):
        " The user requested a list of occurences "
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return True
        if self.parent().getType() in [ MainWindowTabWidgetBase.VCSAnnotateViewer ]:
            return True
        if not os.path.isabs( self.parent().getFileName() ):
            GlobalData().mainWindow.showStatusBarMessage(
                                            "Save the buffer first" )
            return True
        if self.isModified():
            # Check that the directory is writable for a temporary file
            dirName = os.path.dirname( self.parent().getFileName() )
            if not os.access( dirName, os.W_OK ):
                GlobalData().mainWindow.showStatusBarMessage(
                                "File directory is not writable. "
                                "Cannot run rope." )
                return True

        # Prerequisites were checked, run the rope library
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        name, locations = getOccurrences( self.parent().getFileName(), self )
        if len( locations ) == 0:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage(
                                        "No occurences of " + name + " found" )
            return True

        # There are found items
        result = []
        for loc in locations:
            index = getSearchItemIndex( result, loc[ 0 ] )
            if index < 0:
                widget = GlobalData().mainWindow.getWidgetForFileName( loc[0] )
                if widget is None:
                    uuid = ""
                else:
                    uuid = widget.getUUID()
                newItem = ItemToSearchIn( loc[ 0 ], uuid )
                result.append( newItem )
                index = len( result ) - 1
            result[ index ].addMatch( name, loc[ 1 ] )

        QApplication.restoreOverrideCursor()

        GlobalData().mainWindow.displayFindInFiles( "", result )
        return True

    def insertCompletion( self, text ):
        " Triggered when a completion is selected "
        if text:
            currentWord = str( self.getCurrentWord() )
            prefixLength = len( str( self.__completionPrefix ).decode( 'utf-8' ) )
            # wordLength = len( currentWord.decode( 'utf-8' ) )
            line, pos = self.getCursorPosition()

            if text == currentWord:
                # No changes, just possible cursor position change
                self.setCursorPosition( line, pos + len( text ) - prefixLength )
            else:
                oldBuffer = QApplication.clipboard().text()
                self.beginUndoAction()
                self.setSelection( line, pos - prefixLength,
                                   line, pos )
                self.removeSelectedText()
                self.insert( text )
                self.setCursorPosition( line, pos + len( text ) - prefixLength )
                self.endUndoAction()
                QApplication.clipboard().setText( oldBuffer )

            self.__completionPrefix = ""
            self.__completionObject = ""
            self.__completer.hide()
        return

    @staticmethod
    def utf8len( txt ):
        " Calculates lenght in bytes "
        return len( str( txt ).encode( 'utf-8' ) )

    def hideCompleter( self ):
        " Hides the completer if visible "
        self.__completer.hide()
        return

    def onUndo( self ):
        " Triggered when undo button is clicked "
        if self.isUndoAvailable():
            self.undo()
            self.parent().modificationChanged()
        return

    def onRedo( self ):
        " Triggered when redo button is clicked "
        if self.isRedoAvailable():
            self.redo()
            self.parent().modificationChanged()
        return

    def openAsFile( self ):
        """ Triggered when a selection or a current tag is
            requested to be opened as a file """
        selectedText = str( self.selectedText() ).strip()
        singleSelection = selectedText != "" and \
                          '\n' not in selectedText and \
                          '\r' not in selectedText
        currentWord = ""
        if selectedText == "":
            currentWord = str( self.getCurrentWord() ).strip()

        path = currentWord
        if singleSelection:
            path = selectedText

        # Now the processing
        if os.path.isabs( path ):
            GlobalData().mainWindow.detectTypeAndOpenFile( path )
            return
        # This is not an absolute path but could be a relative path for the
        # current buffer file. Let's try it.
        fileName = self.parent().getFileName()
        if fileName != "":
            # There is a file name
            fName = os.path.dirname( fileName ) + os.path.sep + path
            fName = os.path.abspath( os.path.realpath( fName ) )
            if os.path.exists( fName ):
                GlobalData().mainWindow.detectTypeAndOpenFile( fName )
                return
        if GlobalData().project.isLoaded():
            # Try it as a relative path to the project
            prjFile = GlobalData().project.fileName
            fName = os.path.dirname( prjFile ) + os.path.sep + path
            fName = os.path.abspath( os.path.realpath( fName ) )
            if os.path.exists( fName ):
                GlobalData().mainWindow.detectTypeAndOpenFile( fName )
                return
        # The last hope - open as is
        if os.path.exists( path ):
            path = os.path.abspath( os.path.realpath( path ) )
            GlobalData().mainWindow.detectTypeAndOpenFile( path )
            return

        logging.error( "Cannot find '" + path + "' to open" )
        return

    def clearPyflakesMessages( self ):
        " Clears all the pyflakes markers "
        self.ignoreBufferChangedSignal = True
        self.markerDeleteAll( self.__pyflakesMsgMarker )
        self.__pyflakesMessages = {}
        self.ignoreBufferChangedSignal = False
        self._updateDwellingTime()
        return

    def addPyflakesMessage( self, line, message ):
        " Shows up a pyflakes message "
        self.ignoreBufferChangedSignal = True
        if line <= 0:
            line = 1    # Sometimes line is reported as 0

        handle = self.markerAdd( line - 1, self.__pyflakesMsgMarker )
        self.__pyflakesMessages[ handle ] = message
        self.ignoreBufferChangedSignal = False
        self._updateDwellingTime()
        return

    def downloadAndShow( self ):
        " Triggered when the user wants to download and see the file "
        url = str( self.selectedText() ).strip()
        if url.startswith( "www." ):
            url = "http://" + url

        oldTimeout = socket.getdefaulttimeout()
        newTimeout = 5      # Otherwise the pause is too long
        socket.setdefaulttimeout( newTimeout )
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        try:
            response = urllib2.urlopen( url )
            content = response.read()

            # The content has been read sucessfully
            mainWindow = GlobalData().mainWindow
            editorsManager = mainWindow.editorsManagerWidget.editorsManager
            editorsManager.newTabClicked( content, os.path.basename( url ) )
        except Exception, exc:
            logging.error( "Error downloading '" + url + "'\n" + str( exc ) )

        QApplication.restoreOverrideCursor()
        socket.setdefaulttimeout( oldTimeout )
        return

    def openInBrowser( self ):
        " Triggered when a selected URL should be opened in a browser "
        url = str( self.selectedText() ).strip()
        if url.startswith( "www." ):
            url = "http://" + url
        QDesktopServices.openUrl( QUrl( url ) )
        return

    def __contextMenuAboutToShow( self ):
        " Context menu is about to show "
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            self.__menuHighlightInOutline.setEnabled( False )
        else:
            self.__menuHighlightInOutline.setEnabled( True )
        return

    def highlightInOutline( self ):
        " Triggered when highlight in outline browser is requested "
        text = str( self.text() )
        info = getBriefModuleInfoFromMemory( text )
        context = getContext( self, info, True, False )
        line, pos = self.getCursorPosition()
        GlobalData().mainWindow.highlightInOutline( context, int( line ) + 1 )
        return

    def _updateDwellingTime( self ):
        " Updates the dwelling time as necessary "
        if self.__pyflakesMessages:
            self.SendScintilla( self.SCI_SETMOUSEDWELLTIME, 250 )
        else:
            self.SendScintilla( self.SCI_SETMOUSEDWELLTIME,
                                self.SC_TIME_FOREVER )
        return

    def gotoLine( self, line, pos = None, firstVisible = None ):
        """ Jumps to the given position and scrolls if needed.
            line and pos and firstVisible are 1-based. """
        # Normalize editor line and pos
        editorLine = line - 1
        if editorLine < 0:
            editorLine = 0
        if pos is None or pos <= 0:
            editorPos = 0
        else:
            editorPos = pos - 1

        if self.isLineOnScreen( editorLine ):
            if firstVisible is None:
                self.setCursorPosition( editorLine, editorPos )
                return

        # The line could be in a collapsed block
        self.ensureLineVisible( editorLine )

        # Otherwise we would deal with scrolling any way, so normalize
        # the first visible line
        if firstVisible is None:
            editorFirstVisible = editorLine - 1
        else:
            editorFirstVisible = firstVisible - 1
        if editorFirstVisible < 0:
            editorFirstVisible = 0

        self.setCursorPosition( editorLine, editorPos )
        self.setHScrollOffset( 0 ) # avoid unwanted scrolling

        # The loop below is required because in line wrap mode a line could
        # occupy a few lines while the scroll is done in formal lines.
        # In practice the desirable scroll is done in up to 5 iterations or so!
        currentFirstVisible = self.firstVisibleLine()
        while currentFirstVisible != editorFirstVisible:
            self.scrollVertical( editorFirstVisible - currentFirstVisible )
            newFirstVisible = self.firstVisibleLine()
            if newFirstVisible == currentFirstVisible:
                # Scintilla refuses to scroll any further, e.g.
                # The memorized position was below the current file size (file
                # was reduced outside of codimension)
                break
            currentFirstVisible = newFirstVisible
        return


    ## Break points support

    def __breakpointMarginClicked( self, line ):
        " Margin has been clicked. Line is 1 - based "
        for handle, bpoint in self.__breakpoints.items():
            if self.markerLine( handle ) == line - 1:
                # Breakpoint marker is set for this line already
                self.__toggleBreakpoint( line )
                return

        # Check if it is a python file
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return

        fileName = self.parent().getFileName()
        if fileName is None or fileName == "" or not os.path.isabs( fileName ):
            logging.warning( "The buffer has to be saved "
                             "before breakpoints could be set." )
            return


        breakableLines = getBreakpointLines( "", str( self.text() ),
                                             True, False )
        if breakableLines is None:
            logging.warning( "The breakable lines could not be identified "
                             "due to the file compilation errors. Fix the code "
                             "first and try again." )
            return

        breakableLines = list( breakableLines )
        breakableLines.sort()
        if not breakableLines:
            # There are no breakable lines
            return

        if line in breakableLines:
            self.__toggleBreakpoint( line )
            return

        # There are breakable lines however the user requested a line which
        # is not breakable
        candidateLine = breakableLines[ 0 ]
        if line < breakableLines[ 0 ]:
            candidateLine = breakableLines[ 0 ]
        elif line > breakableLines[ -1 ]:
            candidateLine = breakableLines[ -1 ]
        else:
            direction = 0
            if isStringLiteral( self,
                                self.positionFromLineIndex( line - 1, 0 ) ):
                direction = 1
            elif self.isLineEmpty( line ):
                direction = 1
            else:
                direction = -1

            for breakableLine in breakableLines[ 1 : ]:
                if direction > 0:
                    if breakableLine > line:
                        candidateLine = breakableLine
                        break
                else:
                    if breakableLine < line:
                        candidateLine = breakableLine
                    else:
                        break

        if not self.isLineOnScreen( candidateLine - 1 ):
            # The redirected breakpoint line is not on the screen, scroll it
            self.ensureLineVisible( candidateLine - 1 )
            currentFirstVisible = self.firstVisibleLine()
            requiredVisible = candidateLine - 2
            if requiredVisible < 0:
                requiredVisible = 0
            self.scrollVertical( requiredVisible - currentFirstVisible )
        self.__toggleBreakpoint( candidateLine )
        return


    def __toggleBreakpoint( self, line, temporary = False ):
        " Toggles the line breakpoint "
        fileName = self.parent().getFileName()
        model = self.__debugger.getBreakPointModel()
        for handle, bpoint in self.__breakpoints.items():
            if self.markerLine( handle ) == line - 1:
                index = model.getBreakPointIndex( fileName, line )
                if not model.isBreakPointTemporaryByIndex( index ):
                    model.deleteBreakPointByIndex( index )
                    self.__addBreakpoint( line, True )
                else:
                    model.deleteBreakPointByIndex( index )
                return
        self.__addBreakpoint( line, temporary )
        return

    def __addBreakpoint( self, line, temporary ):
        " Adds a new breakpoint "
        # The prerequisites:
        # - it is saved buffer
        # - it is a python buffer
        # - it is a breakable line
        # are checked in the function
        if not self.parent().isLineBreakable( line, True, True ):
            return

        bpoint = Breakpoint( self.parent().getFileName(),
                             line, "", temporary, True, 0 )
        self.__debugger.getBreakPointModel().addBreakpoint( bpoint )
        return

    def __deleteBreakPoints( self, parentIndex, start, end ):
        " Deletes breakpoints "
        bpointModel = self.__debugger.getBreakPointModel()
        for row in xrange( start, end + 1 ):
            index = bpointModel.index( row, 0, parentIndex )
            bpoint = bpointModel.getBreakPointByIndex( index )
            fileName = bpoint.getAbsoluteFileName()

            if fileName == self.parent().getFileName():
                self.clearBreakpoint( bpoint.getLineNumber() )
        return

    def clearBreakpoint( self, line ):
        " Clears a breakpoint "
        if self.__inLinesChanged:
            return

        for handle, bpoint in self.__breakpoints.items():
            if self.markerLine( handle ) == line - 1:
                del self.__breakpoints[ handle ]
                self.ignoreBufferChangedSignal = True
                self.markerDeleteHandle( handle )
                self.ignoreBufferChangedSignal = False
                return
        # Ignore the request if not found
        return

    def __breakPointDataAboutToBeChanged( self, startIndex, endIndex ):
        " Handles the dataAboutToBeChanged signal of the breakpoint model "
        self.__deleteBreakPoints( QModelIndex(),
                                  startIndex.row(), endIndex.row() )
        return

    def __changeBreakPoints( self, startIndex, endIndex ):
        " Sets changed breakpoints "
        self.__addBreakPoints( QModelIndex(),
                               startIndex.row(), endIndex.row() )
        return

    def __addBreakPoints( self, parentIndex, start, end ):
        " Adds breakpoints "
        bpointModel = self.__debugger.getBreakPointModel()
        for row in xrange( start, end + 1 ):
            index = bpointModel.index( row, 0, parentIndex )
            bpoint = bpointModel.getBreakPointByIndex( index )
            fileName = bpoint.getAbsoluteFileName()

            if fileName == self.parent().getFileName():
                self.newBreakpointWithProperties( bpoint )
        return

    def newBreakpointWithProperties( self, bpoint ):
        " Sets a new breakpoint and its properties "
        if not bpoint.isEnabled():
            marker = self.__disbpointMarker
        elif bpoint.isTemporary():
            marker = self.__tempbpointMarker
        else:
            marker = self.__bpointMarker

        line = bpoint.getLineNumber()
        if self.markersAtLine( line - 1 ) & self.__bpointMarginMask == 0:
            self.ignoreBufferChangedSignal = True
            handle = self.markerAdd( line - 1, marker )
            self.ignoreBufferChangedSignal = False
            self.__breakpoints[ handle ] = bpoint
        return

    def isLineEmpty( self, line ):
        " Returns True if the line is empty. Line is 1 based. "
        return self.text( line - 1 ).trimmed() == ""

    def restoreBreakpoints( self ):
        " Restores the breakpoints "
        self.ignoreBufferChangedSignal = True
        self.markerDeleteAll( self.__bpointMarker )
        self.markerDeleteAll( self.__tempbpointMarker )
        self.markerDeleteAll( self.__disbpointMarker )
        self.ignoreBufferChangedSignal = False
        self.__addBreakPoints( QModelIndex(), 0,
                               self.__debugger.getBreakPointModel().rowCount() - 1 )
        return

    def __onSceneModified( self, position, modificationType, text,
                                 length, linesAdded, line, foldLevelNow,
                                 foldLevelPrev, token, annotationLinesAdded ):
        if not self.__breakpoints:
            return

        opLine, opIndex = self.lineIndexFromPosition( position )

        if linesAdded == 0:
            if self.isLineEmpty( opLine + 1 ):
                self.__deleteBreakPointsInLineRange( opLine + 1, 1 )
            return

        # We are interested in inserted or deleted lines
        if linesAdded < 0:
            # Some lines were deleted
            linesDeleted = abs( linesAdded )
            if opIndex != 0:
                linesDeleted -= 1
                if self.isLineEmpty( opLine + 1 ):
                    self.__deleteBreakPointsInLineRange( opLine + 1, 1 )
                if linesDeleted == 0:
                    self.__onLinesChanged( opLine + 1 )
                    return
                opLine += 1

            # Some lines were fully deleted
            self.__deleteBreakPointsInLineRange( opLine + 1, linesDeleted )
            self.__onLinesChanged( opLine + 1 )
        else:
            # Some lines were added
            self.__onLinesChanged( opLine + 1 )
        return

    def __deleteBreakPointsInLineRange( self, startFrom, count ):
        " Deletes breakpoints which fall into the given lines range "
        toBeDeleted = []
        limit = startFrom + count - 1
        for handle, bpoint in self.__breakpoints.items():
            bpointLine = bpoint.getLineNumber()
            if bpointLine >= startFrom and bpointLine <= limit:
                toBeDeleted.append( bpointLine )

        if toBeDeleted:
            model = self.__debugger.getBreakPointModel()
            fileName = self.parent().getFileName()
            for line in toBeDeleted:
                index = model.getBreakPointIndex( fileName, line )
                model.deleteBreakPointByIndex( index )
        return

    def deleteAllBreakpoints( self ):
        " Deletes all the breakpoints in the buffer "
        self.__deleteBreakPointsInLineRange( 1, self.lines() )
        return

    def validateBreakpoints( self ):
        " Checks breakpoints and deletes those which are invalid "
        if not self.__breakpoints:
            return

        fileName = self.parent().getFileName()
        breakableLines = getBreakpointLines( fileName, str( self.text() ),
                                             True, False )

        toBeDeleted = []
        for handle, bpoint in self.__breakpoints.items():
            bpointLine = bpoint.getLineNumber()
            if breakableLines is None or bpointLine not in breakableLines:
                toBeDeleted.append( bpointLine )

        if toBeDeleted:
            model = self.__debugger.getBreakPointModel()
            for line in toBeDeleted:
                if breakableLines is None:
                    logging.warning( "Breakpoint at " + fileName + ":" +
                                     str( line ) + " does not point to a "
                                     "breakable line (file is not compilable). "
                                     "The breakpoint is deleted." )
                else:
                    logging.warning( "Breakpoint at " + fileName + ":" +
                                     str( line ) + " does not point to a breakable "
                                     "line anymore. The breakpoint is deleted." )
                index = model.getBreakPointIndex( fileName, line )
                model.deleteBreakPointByIndex( index )
        return

    def __onLinesChanged( self, startFrom ):
        " Tracks breakpoints when some lines were inserted. startFrom is 1 based. "
        if self.__breakpoints:
            self.ignoreBufferChangedSignal = True

            bpointModel = self.__debugger.getBreakPointModel()
            bps = []    # list of breakpoints
            for handle, bpoint in self.__breakpoints.items():
                line = self.markerLine( handle ) + 1
                if line < startFrom:
                    continue

                self.markerDeleteHandle( handle )
                bps.append( ( bpoint, line, handle ) )

            self.__inLinesChanged = True
            for bp, newLineNumber, oldHandle in bps:
                del self.__breakpoints[ oldHandle ]

                index = bpointModel.getBreakPointIndex( bp.getAbsoluteFileName(),
                                                        bp.getLineNumber() )
                bpointModel.updateLineNumberByIndex( index, newLineNumber )
            self.__inLinesChanged = False
            self.ignoreBufferChangedSignal = False
        return




class TextEditorTabWidget( QWidget, MainWindowTabWidgetBase ):
    " Plain text editor tab widget "

    def __init__( self, parent, debugger ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        self.__editor = TextEditor( self, debugger )
        self.__fileName = ""
        self.__shortName = ""
        self.__fileType = UnknownFileType

        self.__createLayout()
        self.__editor.zoomTo( Settings().zoom )

        self.connect( self.__editor, SIGNAL( 'modificationChanged(bool)' ),
                      self.modificationChanged )

        self.__diskModTime = None
        self.__diskSize = None
        self.__reloadDlgShown = False

        self.__debugMode = False
        self.__breakableLines = None

        self.__vcsStatus = None
        return

    def shouldAcceptFocus( self ):
        return self.__outsideChangesBar.isHidden()

    def readFile( self, fileName ):
        " Reads the text from a file "
        self.__editor.readFile( fileName )
        self.setFileName( fileName )
        self.__editor.restoreBreakpoints()

        # Memorize the modification date
        path = os.path.realpath( fileName )
        self.__diskModTime = os.path.getmtime( path )
        self.__diskSize = os.path.getsize( path )
        return

    def writeFile( self, fileName ):
        " Writes the text to a file "
        if self.__editor.writeFile( fileName ):
            # Memorize the modification date
            path = os.path.realpath( fileName )
            self.__diskModTime = os.path.getmtime( path )
            self.__diskSize = os.path.getsize( path )
            self.setFileName( fileName )
            self.__editor.restoreBreakpoints()
            return True
        return False

    def __createLayout( self ):
        " Creates the toolbar and layout "

        # Buttons
        printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                               'Print', self )
        self.connect( printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )
        printButton.setEnabled( False )
        printButton.setVisible( False )

        printPreviewButton = QAction(
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        self.connect( printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )
        printPreviewButton.setEnabled( False )
        printPreviewButton.setVisible( False )

        self.pylintButton = QAction(
            PixmapCache().getIcon( 'pylint.png' ),
            'Analyse the file (Ctrl+L)', self )
        self.connect( self.pylintButton, SIGNAL( 'triggered()' ),
                      self.onPylint )
        self.pylintButton.setEnabled( False )

        self.pymetricsButton = QAction(
            PixmapCache().getIcon( 'metrics.png' ),
            'Calculate the file metrics (Ctrl+K)', self )
        self.connect( self.pymetricsButton, SIGNAL( 'triggered()' ),
                      self.onPymetrics )
        self.pymetricsButton.setEnabled( False )

        # Imports diagram and its menu
        importsMenu = QMenu( self )
        importsDlgAct = importsMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Fine tuned imports diagram' )
        self.connect( importsDlgAct, SIGNAL( 'triggered()' ),
                      self.onImportDgmTuned )
        self.importsDiagramButton = QToolButton( self )
        self.importsDiagramButton.setIcon(
                            PixmapCache().getIcon( 'importsdiagram.png' ) )
        self.importsDiagramButton.setToolTip( 'Generate imports diagram' )
        self.importsDiagramButton.setPopupMode( QToolButton.DelayedPopup )
        self.importsDiagramButton.setMenu( importsMenu )
        self.importsDiagramButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.importsDiagramButton, SIGNAL( 'clicked(bool)' ),
                      self.onImportDgm )
        self.importsDiagramButton.setEnabled( False )

        # Run script and its menu
        runScriptMenu = QMenu( self )
        runScriptDlgAct = runScriptMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set run/debug parameters' )
        self.connect( runScriptDlgAct, SIGNAL( 'triggered()' ),
                      self.onRunScriptSettings )
        self.runScriptButton = QToolButton( self )
        self.runScriptButton.setIcon(
                            PixmapCache().getIcon( 'run.png' ) )
        self.runScriptButton.setToolTip( 'Run script' )
        self.runScriptButton.setPopupMode( QToolButton.DelayedPopup )
        self.runScriptButton.setMenu( runScriptMenu )
        self.runScriptButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.runScriptButton, SIGNAL( 'clicked(bool)' ),
                      self.onRunScript )
        self.runScriptButton.setEnabled( False )

        # Profile script and its menu
        profileScriptMenu = QMenu( self )
        profileScriptDlgAct = profileScriptMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set profile parameters' )
        self.connect( profileScriptDlgAct, SIGNAL( 'triggered()' ),
                      self.onProfileScriptSettings )
        self.profileScriptButton = QToolButton( self )
        self.profileScriptButton.setIcon(
                            PixmapCache().getIcon( 'profile.png' ) )
        self.profileScriptButton.setToolTip( 'Profile script' )
        self.profileScriptButton.setPopupMode( QToolButton.DelayedPopup )
        self.profileScriptButton.setMenu( profileScriptMenu )
        self.profileScriptButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.profileScriptButton, SIGNAL( 'clicked(bool)' ),
                      self.onProfileScript )
        self.profileScriptButton.setEnabled( False )

        # Debug script and its menu
        debugScriptMenu = QMenu( self )
        debugScriptDlgAct = debugScriptMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set run/debug parameters' )
        self.connect( debugScriptDlgAct, SIGNAL( 'triggered()' ),
                      self.onDebugScriptSettings )
        self.debugScriptButton = QToolButton( self )
        self.debugScriptButton.setIcon(
                            PixmapCache().getIcon( 'debugger.png' ) )
        self.debugScriptButton.setToolTip( 'Debug script' )
        self.debugScriptButton.setPopupMode( QToolButton.DelayedPopup )
        self.debugScriptButton.setMenu( debugScriptMenu )
        self.debugScriptButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.debugScriptButton, SIGNAL( 'clicked(bool)' ),
                      self.onDebugScript )
        self.debugScriptButton.setEnabled( False )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.__undoButton = QAction(
            PixmapCache().getIcon( 'undo.png' ), 'Undo (Ctrl+Z)', self )
        self.__undoButton.setShortcut( 'Ctrl+Z' )
        self.connect( self.__undoButton, SIGNAL( 'triggered()' ),
                      self.__editor.onUndo )
        self.__undoButton.setEnabled( False )

        self.__redoButton = QAction(
            PixmapCache().getIcon( 'redo.png' ), 'Redo (Ctrl+Shift+Z)', self )
        self.__redoButton.setShortcut( 'Ctrl+Shift+Z' )
        self.connect( self.__redoButton, SIGNAL( 'triggered()' ),
                      self.__editor.onRedo )
        self.__redoButton.setEnabled( False )

        # Python tidy script button and its menu
        pythonTidyMenu = QMenu( self )
        pythonTidyDlgAct = pythonTidyMenu.addAction(
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set python tidy parameters' )
        self.connect( pythonTidyDlgAct, SIGNAL( 'triggered()' ),
                      self.onPythonTidySettings )
        self.pythonTidyButton = QToolButton( self )
        self.pythonTidyButton.setIcon(
                      PixmapCache().getIcon( 'pythontidy.png' ) )
        self.pythonTidyButton.setToolTip( 'Python tidy (code must be '
                                          'syntactically valid)' )
        self.pythonTidyButton.setPopupMode( QToolButton.DelayedPopup )
        self.pythonTidyButton.setMenu( pythonTidyMenu )
        self.pythonTidyButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.pythonTidyButton, SIGNAL( 'clicked(bool)' ),
                      self.onPythonTidy )
        self.pythonTidyButton.setEnabled( False )

        self.lineCounterButton = QAction(
            PixmapCache().getIcon( 'linecounter.png' ),
            'Line counter', self )
        self.connect( self.lineCounterButton, SIGNAL( 'triggered()' ),
                      self.onLineCounter )

        self.removeTrailingSpacesButton = QAction(
            PixmapCache().getIcon( 'trailingws.png' ),
            'Remove trailing spaces', self )
        self.connect( self.removeTrailingSpacesButton, SIGNAL( 'triggered()' ),
                      self.onRemoveTrailingWS )
        self.expandTabsButton = QAction(
            PixmapCache().getIcon( 'expandtabs.png' ),
            'Expand tabs (4 spaces)', self )
        self.connect( self.expandTabsButton, SIGNAL( 'triggered()' ),
                      self.onExpandTabs )

        # Zoom buttons
        # It was decided that it is wrong to have these buttons here
        #zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
        #                        'Zoom in (Ctrl+=)', self )
        #self.connect( zoomInButton, SIGNAL( 'triggered()' ), self.onZoomIn )

        #zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
        #                        'Zoom out (Ctrl+-)', self )
        #self.connect( zoomOutButton, SIGNAL( 'triggered()' ), self.onZoomOut )

        #zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
        #                           'Zoom reset (Ctrl+0)', self )
        #self.connect( zoomResetButton, SIGNAL( 'triggered()' ),
        #              self.onZoomReset )

        #fixedSpacer = QWidget()
        #fixedSpacer.setFixedHeight( 16 )

        # The toolbar
        toolbar = QToolBar( self )
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.RightToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )

        toolbar.addAction( printPreviewButton )
        toolbar.addAction( printButton )
        toolbar.addAction( self.pylintButton )
        toolbar.addAction( self.pymetricsButton )
        toolbar.addWidget( self.importsDiagramButton )
        toolbar.addWidget( self.runScriptButton )
        toolbar.addWidget( self.profileScriptButton )
        toolbar.addWidget( self.debugScriptButton )
        toolbar.addAction( self.__undoButton )
        toolbar.addAction( self.__redoButton )
        toolbar.addWidget( spacer )
        #toolbar.addAction( zoomInButton )
        #toolbar.addAction( zoomOutButton )
        #toolbar.addAction( zoomResetButton )
        #toolbar.addWidget( fixedSpacer )
        toolbar.addWidget( self.pythonTidyButton )
        toolbar.addAction( self.lineCounterButton )
        toolbar.addAction( self.removeTrailingSpacesButton )
        toolbar.addAction( self.expandTabsButton )


        self.__importsBar = ImportListWidget( self.__editor )
        self.__importsBar.hide()

        self.__outsideChangesBar = OutsideChangeWidget( self.__editor )
        self.connect( self.__outsideChangesBar, SIGNAL( 'ReloadRequest' ),
                      self.__onReload )
        self.connect( self.__outsideChangesBar,
                      SIGNAL( 'ReloadAllNonModifiedRequest' ),
                      self.reloadAllNonModified )
        self.__outsideChangesBar.hide()

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )
        hLayout.addWidget( self.__editor )
        hLayout.addWidget( toolbar )

        self.setLayout( hLayout )
        return

    def updateStatus( self ):
        " Updates the toolbar buttons status "
        if self.__fileType == UnknownFileType:
            self.__fileType = self.getFileType()
        isPythonFile = self.__fileType in [ PythonFileType, Python3FileType ]
        self.pylintButton.setEnabled( isPythonFile and
                                      GlobalData().pylintAvailable )
        self.__editor.pylintAct.setEnabled( self.pylintButton.isEnabled() )
        self.pymetricsButton.setEnabled( isPythonFile )
        self.__editor.pymetricsAct.setEnabled(
                            self.pymetricsButton.isEnabled() )
        self.importsDiagramButton.setEnabled( isPythonFile and
                            GlobalData().graphvizAvailable )
        self.__editor.importsDgmAct.setEnabled(
                                    self.importsDiagramButton.isEnabled() )
        self.__editor.importsDgmParamAct.setEnabled(
                                    self.importsDiagramButton.isEnabled() )
        self.__editor.runAct.setEnabled( self.runScriptButton.isEnabled() )
        self.__editor.runParamAct.setEnabled( self.runScriptButton.isEnabled() )
        self.__editor.profileAct.setEnabled( self.runScriptButton.isEnabled() )
        self.__editor.profileParamAct.setEnabled(
                                    self.runScriptButton.isEnabled() )
        self.pythonTidyButton.setEnabled( isPythonFile )
        self.lineCounterButton.setEnabled( isPythonFile )
        self.__updateRunDebugButtons()
        return

    def onPylint( self ):
        " Triggers when pylint should be used "

        if self.__fileType == UnknownFileType:
            self.__fileType = self.getFileType()
        if self.__fileType not in [ PythonFileType, Python3FileType ]:
            return True

        if self.__fileName:
            reportFile = self.__fileName
        else:
            reportFile = self.__shortName

        if self.isModified() or self.__fileName == "":
            # Need to parse the buffer
            GlobalData().mainWindow.showPylintReport(
                            PylintViewer.SingleBuffer, self.__editor.text(),
                            reportFile, self.getUUID(), self.__fileName )
        else:
            # Need to parse the file
            GlobalData().mainWindow.showPylintReport(
                            PylintViewer.SingleFile, self.__fileName,
                            reportFile, self.getUUID(), self.__fileName )
        return True

    def onPymetrics( self ):
        " Triggers when pymetrics should be used "

        if self.__fileType == UnknownFileType:
            self.__fileType = self.getFileType()
        if self.__fileType not in [ PythonFileType, Python3FileType ]:
            return True

        if self.__fileName:
            reportFile = self.__fileName
        else:
            reportFile = self.__shortName

        if self.isModified() or self.__fileName == "":
            # Need to parse the buffer
            GlobalData().mainWindow.showPymetricsReport(
                            PymetricsViewer.SingleBuffer, self.__editor.text(),
                            reportFile, self.getUUID() )
        else:
            # Need to parse the file
            GlobalData().mainWindow.showPymetricsReport(
                            PymetricsViewer.SingleFile, self.__fileName,
                            reportFile, self.getUUID() )
        return True

    def onZoomReset( self ):
        " Triggered when the zoom reset button is pressed "
        if self.__editor.zoom != 0:
            self.emit( SIGNAL( 'TextEditorZoom' ), 0 )
        return True

    def onZoomIn( self ):
        " Triggered when the zoom in button is pressed "
        if self.__editor.zoom < 20:
            self.emit( SIGNAL( 'TextEditorZoom' ), self.__editor.zoom + 1 )
        return True

    def onZoomOut( self ):
        " Triggered when the zoom out button is pressed "
        if self.__editor.zoom > -10:
            self.emit( SIGNAL( 'TextEditorZoom' ), self.__editor.zoom - 1 )
        return True

    def __onPrint( self ):
        " Triggered when the print button is pressed "
        pass

    def __onPrintPreview( self ):
        " triggered when the print preview button is pressed "
        pass

    def modificationChanged( self, modified = False ):
        " Triggered when the content is changed "
        self.__undoButton.setEnabled( self.__editor.isUndoAvailable() )
        self.__redoButton.setEnabled( self.__editor.isRedoAvailable() )
        self.__updateRunDebugButtons()
        return

    def __updateRunDebugButtons( self ):
        " Enables/disables the run and debug buttons as required "
        enable = self.__fileType == PythonFileType and \
                 self.isModified() == False and \
                 self.__debugMode == False and \
                 os.path.isabs( self.__fileName )

        if enable == self.runScriptButton.isEnabled():
            # No change
            return

        self.runScriptButton.setEnabled( enable )
        self.profileScriptButton.setEnabled( enable )
        self.debugScriptButton.setEnabled( enable )
        self.emit( SIGNAL( "TabRunChanged" ), enable )
        return

    def isTabRunEnabled( self ):
        " Tells the status of run-like buttons "
        return self.runScriptButton.isEnabled()

    def onPythonTidy( self ):
        " Triggered when python tidy should be called "
        text = str( self.__editor.text() )
        info = getBriefModuleInfoFromMemory( text )
        if info.isOK == False:
            logging.warning( "The python code is syntactically incorrect. "
                             "Fix it first and then run PythonTidy." )
            return

        tidy = PythonTidyDriver()
        try:
            QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
            result = tidy.run( text, getPythonTidySetting() )
            QApplication.restoreOverrideCursor()
        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            return

        diff = tidy.getDiff()
        if diff is None:
            GlobalData().mainWindow.showStatusBarMessage(
                    "PythonTidy did no changes." )
            return

        # There are changes, so replace the text and tell about the changes
        self.replaceAll( result )
        timestamp = getLocaleDateTime()
        diffAsText = '\n'.join( list( diff ) )
        diffAsText = diffAsText.replace( "--- ",
                                         "--- " + self.getShortName(), 1 )
        diffAsText = diffAsText.replace( "+++ ",
                                         "+++ generated at " + timestamp, 1 )
        GlobalData().mainWindow.showDiff( diffAsText,
                                          "PythonTidy diff for " +
                                          self.getShortName() +
                                          " generated at " + timestamp )
        return

    def onPythonTidySettings( self ):
        " Triggered when a python tidy settings are requested "
        text = str( self.__editor.text() )
        info = getBriefModuleInfoFromMemory( text )
        if info.isOK == False:
            logging.warning( "The python code is syntactically incorrect. "
                             "Fix it first and then run PythonTidy." )
            return

        tidySettings = getPythonTidySetting()
        settingsFile = getPythonTidySettingFileName()
        dlg = TidySettingsDialog( tidySettings, settingsFile, self )
        if dlg.exec_() != QDialog.Accepted:
            return

        tidy = PythonTidyDriver()
        try:
            QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
            result = tidy.run( str( self.__editor.text() ),
                               tidySettings )
            QApplication.restoreOverrideCursor()
        except Exception, exc:
            QApplication.restoreOverrideCursor()
            logging.error( str( exc ) )
            return

        diff = tidy.getDiff()
        if diff is None:
            GlobalData().mainWindow.showStatusBarMessage(
                    "PythonTidy did no changes." )
            return

        # There are changes, so replace the text and tell about the changes
        self.replaceAll( result )
        timestamp = getLocaleDateTime()
        diffAsText = '\n'.join( list( diff ) )
        diffAsText = diffAsText.replace( "--- ",
                                         "--- " + self.getShortName(), 1 )
        diffAsText = diffAsText.replace( "+++ ",
                                         "+++ generated at " + timestamp, 1 )
        GlobalData().mainWindow.showDiff( diffAsText,
                                          "PythonTidy diff for " +
                                          self.getShortName() +
                                          " generated at " + timestamp )
        return

    def replaceAll( self, newText ):
        " Replaces the current buffer content with a new text "
        # Unfortunately, the setText() clears the undo history so it cannot be
        # used. The selectAll() and replacing selected text do not suite
        # because after undo the cursor does not jump to the previous position.
        # So, there is an ugly select -> replace manipulation below...
        self.__editor.beginUndoAction()

        origLine, origPos = self.__editor.getCursorPosition()
        self.__editor.setSelection( 0, 0, origLine, origPos )
        self.__editor.removeSelectedText()
        self.__editor.insert( newText )
        self.__editor.setCurrentPosition( len( newText ) )
        line, pos = self.__editor.getCursorPosition()
        lastLine = self.__editor.lines()
        self.__editor.setSelection( line, pos,
                                    lastLine - 1,
                                    len( self.__editor.text( lastLine - 1 ) ) )
        self.__editor.removeSelectedText()
        self.__editor.setCursorPosition( origLine, origPos )

        # These two for the proper cursor positioning after redo
        self.__editor.insert( "s" )
        self.__editor.setCursorPosition( origLine, origPos + 1 )
        self.__editor.deleteBack()
        self.__editor.setCursorPosition( origLine, origPos )

        self.__editor.endUndoAction()
        return

    def onLineCounter( self ):
        " Triggered when line counter button is clicked "
        LineCounterDialog( None, self.__editor ).exec_()
        return

    def onRemoveTrailingWS( self ):
        " Triggers when the trailing spaces should be wiped out "
        self.__editor.removeTrailingWhitespaces()
        return

    def onExpandTabs( self ):
        " Expands tabs if there are any "
        self.__editor.expandTabs( 4 )
        return

    def setFocus( self ):
        " Overridden setFocus "
        if self.__outsideChangesBar.isHidden():
            self.__editor.setFocus()
        else:
            self.__outsideChangesBar.setFocus()
        return

    def onImportDgmTuned( self ):
        " Runs the settings dialog first "
        if self.__editor.isModified():
            what = ImportsDiagramDialog.SingleBuffer
            if not os.path.isabs( self.getFileName() ):
                logging.warning( "Imports diagram can only be generated for "
                                 "a file. Save the editor buffer "
                                 "and try again." )
                return
        else:
            what = ImportsDiagramDialog.SingleFile
        dlg = ImportsDiagramDialog( what, self.getFileName() )
        if dlg.exec_() == QDialog.Accepted:
            # Should proceed with the diagram generation
            self.__generateImportDiagram( what, dlg.options )
        return

    def onImportDgm( self, action = None ):
        " Runs the generation process with default options "
        if self.__editor.isModified():
            what = ImportsDiagramDialog.SingleBuffer
            if not os.path.isabs( self.getFileName() ):
                logging.warning( "Imports diagram can only be generated for "
                                 "a file. Save the editor buffer "
                                 "and try again." )
                return
        else:
            what = ImportsDiagramDialog.SingleFile
        self.__generateImportDiagram( what, ImportDiagramOptions() )
        return

    def __generateImportDiagram( self, what, options ):
        " Show the generation progress and display the diagram "
        if self.__editor.isModified():
            progressDlg = ImportsDiagramProgress( what, options,
                                                  self.getFileName(),
                                                  self.__editor.text() )
            tooltip = "Generated for modified buffer (" + \
                      self.getFileName() + ")"
        else:
            progressDlg = ImportsDiagramProgress( what, options,
                                                  self.getFileName() )
            tooltip = "Generated for file " + self.getFileName()
        if progressDlg.exec_() == QDialog.Accepted:
            GlobalData().mainWindow.openDiagram( progressDlg.scene,
                                                 tooltip )
        return

    def onOpenImport( self ):
        " Triggered when Ctrl+I is received "
        if self.__fileType not in [ PythonFileType, Python3FileType ]:
            return True

        # Python file, we may continue
        importLine, lineNo = isImportLine( self.__editor )
        basePath = os.path.dirname( self.__fileName )

        if importLine:
            lineImports, importWhat = getImportsInLine( self.__editor.text(),
                                                        lineNo + 1 )
            currentWord = str( self.__editor.getCurrentWord( "." ) )
            if currentWord in lineImports:
                # The cursor is on some import
                path = resolveImport( basePath, currentWord )
                if path != '':
                    GlobalData().mainWindow.openFile( path, -1 )
                    return True
                GlobalData().mainWindow.showStatusBarMessage(
                        "The import '" + currentWord + "' is not resolved." )
                return True
            # We are not on a certain import.
            # Check if it is a line with exactly one import
            if len( lineImports ) == 1:
                path = resolveImport( basePath, lineImports[ 0 ] )
                if path == '':
                    GlobalData().mainWindow.showStatusBarMessage(
                        "The import '" + lineImports[ 0 ] +
                        "' is not resolved." )
                    return True
                # The import is resolved. Check where we are.
                if currentWord in importWhat:
                    # We are on a certain imported name in a resolved import
                    # So, jump to the definition line
                    line = getImportedNameDefinitionLine( path, currentWord )
                    GlobalData().mainWindow.openFile( path, line )
                    return True
                GlobalData().mainWindow.openFile( path, -1 )
                return True

            # Take all the imports in the line and resolve them.
            self.__onImportList( basePath, lineImports )
            return True

        # Here: the cursor is not on the import line. Take all the file imports
        # and resolve them
        fileImports = getImportsList( self.__editor.text() )
        if not fileImports:
            GlobalData().mainWindow.showStatusBarMessage(
                                            "There are no imports" )
            return True
        if len( fileImports ) == 1:
            path = resolveImport( basePath, fileImports[ 0 ] )
            if path == '':
                GlobalData().mainWindow.showStatusBarMessage(
                    "The import '" + fileImports[ 0 ] + "' is not resolved." )
                return True
            GlobalData().mainWindow.openFile( path, -1 )
            return True

        self.__onImportList( basePath, fileImports )
        return True

    def __onImportList( self, basePath, imports ):
        " Works with a list of imports "

        # It has already been checked that the file is a Python one
        resolvedList = resolveImports( basePath, imports )
        if not resolvedList:
            GlobalData().mainWindow.showStatusBarMessage(
                                            "No imports are resolved" )
            return

        # Display the import selection widget
        self.__importsBar.showResolvedList( resolvedList )
        return

    def resizeEvent( self, event ):
        " Resizes the import selection dialogue if necessary "
        self.__editor.hideCompleter()
        QWidget.resizeEvent( self, event )
        self.resizeBars()
        return

    def resizeBars( self ):
        " Resize the bars if they are shown "
        if not self.__importsBar.isHidden():
            self.__importsBar.resize()
        if not self.__outsideChangesBar.isHidden():
            self.__outsideChangesBar.resize()
        self.__editor.resizeCalltip()
        return

    def showOutsideChangesBar( self, allEnabled ):
        " Shows the bar for the editor for the user to choose the action "
        self.setReloadDialogShown( True )
        self.__outsideChangesBar.showChoice( self.isModified(),
                                             allEnabled )
        return

    def __onReload( self ):
        " Triggered when a request to reload the file is received "
        self.emit( SIGNAL( 'ReloadRequest' ) )
        return

    def reload( self ):
        " Called (from the editors manager) to reload the file "

        # Re-read the file with updating the file timestamp
        self.readFile( self.__fileName )

        # Hide the bars, just in case both of them
        if not self.__importsBar.isHidden():
            self.__importsBar.hide()
        if not self.__outsideChangesBar.isHidden():
            self.__outsideChangesBar.hide()

        # Set the shown flag
        self.setReloadDialogShown( False )
        return

    def reloadAllNonModified( self ):
        """ Triggered when a request to reload all the
            non-modified files is received """
        self.emit( SIGNAL( 'ReloadAllNonModifiedRequest' ) )
        return

    def onRunScriptSettings( self ):
        " Shows the run parameters dialogue "
        fileName = self.getFileName()
        params = GlobalData().getRunParameters( fileName )
        termType = Settings().terminalType
        profilerParams = Settings().getProfilerSettings()
        debuggerParams = Settings().getDebuggerSettings()
        dlg = RunDialog( fileName, params, termType,
                         profilerParams, debuggerParams, "Run" )
        if dlg.exec_() == QDialog.Accepted:
            GlobalData().addRunParams( fileName, dlg.runParams )
            if dlg.termType != termType:
                Settings().terminalType = dlg.termType
            self.onRunScript()
        return

    def onProfileScriptSettings( self ):
        " Shows the profile parameters dialogue "
        fileName = self.getFileName()
        params = GlobalData().getRunParameters( fileName )
        termType = Settings().terminalType
        profilerParams = Settings().getProfilerSettings()
        debuggerParams = Settings().getDebuggerSettings()
        dlg = RunDialog( fileName, params, termType,
                         profilerParams, debuggerParams, "Profile" )
        if dlg.exec_() == QDialog.Accepted:
            GlobalData().addRunParams( fileName, dlg.runParams )
            if dlg.termType != termType:
                Settings().terminalType = dlg.termType
            if dlg.profilerParams != profilerParams:
                Settings().setProfilerSettings( dlg.profilerParams )
            self.onProfileScript()
        return

    def onRunScript( self, action = False ):
        " Runs the script "
        fileName = self.getFileName()
        params = GlobalData().getRunParameters( fileName )
        workingDir, cmd, environment = getCwdCmdEnv( CMD_TYPE_RUN,
                                                     fileName, params,
                                                     Settings().terminalType )

        try:
            Popen( cmd, shell = True,
                   cwd = workingDir, env = environment )
        except Exception, exc:
            logging.error( str( exc ) )
        return

    def onProfileScript( self, action = False ):
        " Profiles the script "
        try:
            ProfilingProgressDialog( self.getFileName(), self ).exec_()
        except Exception, exc:
            logging.error( str( exc ) )
        return

    def onDebugScriptSettings( self ):
        " Shows the debug parameters dialogue "
        if self.__checkDebugPrerequisites() == False:
            return

        fileName = self.getFileName()
        params = GlobalData().getRunParameters( fileName )
        termType = Settings().terminalType
        profilerParams = Settings().getProfilerSettings()
        debuggerParams = Settings().getDebuggerSettings()
        dlg = RunDialog( fileName, params, termType,
                         profilerParams, debuggerParams, "Debug" )
        if dlg.exec_() == QDialog.Accepted:
            GlobalData().addRunParams( fileName, dlg.runParams )
            if dlg.termType != termType:
                Settings().terminalType = dlg.termType
            if dlg.debuggerParams != debuggerParams:
                Settings().setDebuggerSettings( dlg.debuggerParams )
            self.onDebugScript()
        return

    def onDebugScript( self ):
        " Starts debugging "
        if self.__checkDebugPrerequisites() == False:
            return

        GlobalData().mainWindow.debugScript( self.getFileName() )
        return

    def __checkDebugPrerequisites( self ):
        " Returns True if should continue "
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        modifiedFiles = editorsManager.getModifiedList( True )
        if not modifiedFiles:
            return True

        dlg = ModifiedUnsavedDialog( modifiedFiles, "Save and debug" )
        if dlg.exec_() != QDialog.Accepted:
            # Selected to cancel
            return False

        # Need to save the modified project files
        return editorsManager.saveModified( True )

    # Mandatory interface part is below

    def getEditor( self ):
        " Provides the editor widget "
        return self.__editor

    def isModified( self ):
        " Tells if the file is modified "
        return self.__editor.isModified()

    def getRWMode( self ):
        " Tells if the file is read only "
        if not os.path.exists( self.__fileName ):
            return "N/A"
        if QFileInfo( self.__fileName ).isWritable():
            return "RW"
        return "RO"

    def getFileType( self ):
        " Provides the file type "
        if self.__fileType == UnknownFileType:
            if self.__fileName:
                self.__fileType = detectFileType( self.__fileName )
            elif self.__shortName:
                self.__fileType = detectFileType( self.__shortName )
        return self.__fileType

    def setFileType( self, typeToSet ):
        """ Sets the file type explicitly.
            It needs e.g. for .cgi files which can change its type """
        self.__fileType = typeToSet
        return

    def getType( self ):
        " Tells the widget type "
        return MainWindowTabWidgetBase.PlainTextEditor

    def getLanguage( self ):
        " Tells the content language "
        if self.__fileType == UnknownFileType:
            self.__fileType = self.getFileType()
        if self.__fileType != UnknownFileType:
            return getFileLanguage( self.__fileType )
        return self.__editor.getLanguage()

    def getFileName( self ):
        " Tells what file name of the widget content "
        return self.__fileName

    def setFileName( self, name ):
        " Sets the file name "
        self.__fileName = name
        self.__shortName = os.path.basename( name )
        self.__fileType = detectFileType( name )
        return

    def getEol( self ):
        " Tells the EOL style "
        return self.__editor.getEolIndicator()

    def getLine( self ):
        " Tells the cursor line "
        line, pos = self.__editor.getCursorPosition()
        return int( line )

    def getPos( self ):
        " Tells the cursor column "
        line, pos = self.__editor.getCursorPosition()
        return int( pos )

    def getEncoding( self ):
        " Tells the content encoding "
        return self.__editor.encoding

    def setEncoding( self, newEncoding ):
        " Sets the new editor encoding "
        self.__editor.setEncoding( newEncoding )
        return

    def getShortName( self ):
        " Tells the display name "
        return self.__shortName

    def setShortName( self, name ):
        " Sets the display name "
        self.__shortName = name
        self.__fileType = detectFileType( name )
        return

    def isDiskFileModified( self ):
        " Return True if the loaded file is modified "
        if not os.path.isabs( self.__fileName ):
            return False
        if not os.path.exists( self.__fileName ):
            return True
        path = os.path.realpath( self.__fileName )
        return self.__diskModTime != os.path.getmtime( path ) or \
               self.__diskSize != os.path.getsize( path )

    def doesFileExist( self ):
        " Returns True if the loaded file still exists "
        return os.path.exists( self.__fileName )

    def setReloadDialogShown( self, value = True ):
        """ Sets the new value of the flag which tells if the reloading
            dialogue has already been displayed """
        self.__reloadDlgShown = value
        return

    def getReloadDialogShown( self ):
        " Tells if the reload dialog has already been shown "
        return self.__reloadDlgShown and not self.__outsideChangesBar.isVisible()

    def updateModificationTime( self, fileName ):
        " Updates the modification time "
        path = os.path.realpath( fileName )
        self.__diskModTime = os.path.getmtime( path )
        self.__diskSize = os.path.getsize( path )
        return

    def setDebugMode( self, mode, disableEditing ):
        " Called to switch debug/development "
        skin = GlobalData().skin
        self.__debugMode = mode
        self.__breakableLines = None

        if mode == True:
            if disableEditing:
                self.__editor.setMarginsBackgroundColor( skin.marginPaperDebug )
                self.__editor.setMarginsForegroundColor( skin.marginColorDebug )
                self.__editor.setReadOnly( True )

                # Undo/redo
                self.__undoButton.setEnabled( False )
                self.__redoButton.setEnabled( False )

                # Spaces/tabs/line
                self.removeTrailingSpacesButton.setEnabled( False )
                self.expandTabsButton.setEnabled( False )
                self.pythonTidyButton.setEnabled( False )
        else:
            self.__editor.setMarginsBackgroundColor( skin.marginPaper )
            self.__editor.setMarginsForegroundColor( skin.marginColor )
            self.__editor.setReadOnly( False )

            # Undo/redo
            self.__undoButton.setEnabled( self.__editor.isUndoAvailable() )
            self.__redoButton.setEnabled( self.__editor.isRedoAvailable() )

            # Spaces/tabs
            self.removeTrailingSpacesButton.setEnabled( True )
            self.expandTabsButton.setEnabled( True )
            self.pythonTidyButton.setEnabled( True )

        # Run/debug buttons
        self.__updateRunDebugButtons()
        return

    def isLineBreakable( self, line = None,
                               enforceRecalc = False,
                               enforceSure = False ):
        " Returns True if a breakpoint could be placed on the current line "
        if self.__fileName is None or \
           self.__fileName == "" or \
           os.path.isabs( self.__fileName ) == False:
            return False
        if not self.getFileType() in [ PythonFileType,
                                       Python3FileType ]:
            return False

        if line is None:
            line = self.getLine() + 1
        if self.__breakableLines is not None and enforceRecalc == False:
            return line in self.__breakableLines

        self.__breakableLines = getBreakpointLines( self.getFileName(),
                                                    str( self.__editor.text() ),
                                                    enforceRecalc )

        if self.__breakableLines is None :
            if enforceSure == False:
                # Be on the safe side - if there is a problem of
                # getting the breakable lines, let the user decide
                return True
            return False

        return line in self.__breakableLines

    def getVCSStatus( self ):
        " Provides the VCS status "
        return self.__vcsStatus

    def setVCSStatus( self, newStatus ):
        " Sets the new VCS status "
        self.__vcsStatus = newStatus
        return
