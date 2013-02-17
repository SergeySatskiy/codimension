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


import os.path, logging
from subprocess import Popen
import lexer
from scintillawrap              import ScintillaWrapper
from PyQt4.QtCore               import Qt, QFileInfo, SIGNAL, QSize, \
                                       QVariant, QRect, QEvent, QPoint
from PyQt4.QtGui                import QApplication, QCursor, \
                                       QFontMetrics, QToolBar, QActionGroup, \
                                       QHBoxLayout, QWidget, QAction, QMenu, \
                                       QSizePolicy, QToolButton, QDialog, \
                                       QToolTip
from PyQt4.Qsci                 import QsciScintilla, QsciLexerPython
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.fileutils            import detectFileType, DesignerFileType, \
                                       LinguistFileType, MakefileType, \
                                       getFileLanguage, UnknownFileType, \
                                       PythonFileType, Python3FileType
from utils.encoding             import decode, encode, CodingError, \
                                       supportedCodecs
from utils.pixmapcache          import PixmapCache
from utils.globals              import GlobalData
from utils.settings             import Settings
from utils.misc                 import getLocaleDateTime
from ui.pylintviewer            import PylintViewer
from ui.pymetricsviewer         import PymetricsViewer
from diagram.importsdgm         import ImportsDiagramDialog, \
                                       ImportDiagramOptions, \
                                       ImportsDiagramProgress
from utils.importutils          import getImportsList, \
                                       getImportsInLine, resolveImport, \
                                       getImportedNameDefinitionLine, \
                                       resolveImports
from ui.importlist              import ImportListWidget
from ui.outsidechanges          import OutsideChangeWidget
from autocomplete.bufferutils   import getContext, getPrefixAndObject, \
                                       getEditorTags
from autocomplete.completelists import getCompletionList, getCalltipAndDoc, \
                                       getDefinitionLocation, getOccurrences
from cdmbriefparser             import getBriefModuleInfoFromMemory
from ui.completer               import CodeCompleter
from ui.runparams               import RunDialog
from utils.run                  import getCwdCmdEnv
from ui.findinfiles             import ItemToSearchIn, getSearchItemIndex
from debugger.modifiedunsaved   import ModifiedUnsavedDialog
from ui.linecounter             import LineCounterDialog
from pythontidy.tidy            import getPythonTidySetting, PythonTidyDriver, \
                                       getPythonTidySettingFileName
from pythontidy.tidysettingsdlg import TidySettingsDialog
from profiling.profui           import ProfilingProgressDialog


class TextEditor( ScintillaWrapper ):
    " Text editor implementation "

    matchIndicator    = ScintillaWrapper.INDIC_CONTAINER
    searchIndicator   = ScintillaWrapper.INDIC_CONTAINER + 1
    spellingIndicator = ScintillaWrapper.INDIC_CONTAINER + 2

    textToIterate = ""

    LINENUM_MARGIN = 0
    MESSAGES_MARGIN = 1
    FOLDING_MARGIN = 2

    def __init__( self, parent = None ):

        ScintillaWrapper.__init__( self, parent )
        self.__initMargins()
        self.__initIndicators()
        self.__disableKeyBinding()
        self.__initContextMenu()

        self.connect( self, SIGNAL( 'SCN_DOUBLECLICK(int,int,int)' ),
                      self.__onDoubleClick )
        self.connect( self, SIGNAL( 'cursorPositionChanged(int,int)' ),
                      self.__onCursorPositionChanged )

        self.SendScintilla( self.SCI_SETMOUSEDWELLTIME, 1000 )
        self.connect( self, SIGNAL( 'SCN_DWELLSTART(int,int,int)' ),
                      self.__onDwellStart )
        self.connect( self, SIGNAL( 'SCN_DWELLEND(int,int,int)' ),
                      self.__onDwellEnd )
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
        self.connect( self.__completer, SIGNAL( "activated(const QString &)" ),
                      self.insertCompletion )

        self.installEventFilter( self )
        return

    def eventFilter( self, obj, event ):
        " Event filter to catch shortcuts on UBUNTU "
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
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
            if modifiers == Qt.AltModifier | Qt.ShiftModifier:
                if key == Qt.Key_Up:
                    return self.__onAltShiftUp()
                if key == Qt.Key_Down:
                    return self.__onAltShiftDown()
                if key == Qt.Key_Left:
                    return self.__onAlShiftLeft()
                if key == Qt.Key_Right:
                    return self.__onAlShiftRight()
            if key == Qt.Key_Home:
                return self.__onHome()
            if key == Qt.Key_End:
                return self.__onEnd()

        return ScintillaWrapper.eventFilter( self, obj, event )

    def __initContextMenu( self ):
        " Initializes the context menu "
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager

        self.__menu = QMenu( self )
        self.__menuUndo = self.__menu.addAction( \
                                    PixmapCache().getIcon( 'undo.png' ),
                                    '&Undo', self.onUndo, "Ctrl+Z" )
        self.__menuRedo = self.__menu.addAction( \
                                    PixmapCache().getIcon( 'redo.png' ),
                                    '&Redo', self.onRedo, "Ctrl+Shift+Z" )
        self.__menu.addSeparator()
        self.__menuCut = self.__menu.addAction( \
                                    PixmapCache().getIcon( 'cutmenu.png' ),
                                    'Cu&t', self.onShiftDel, "Ctrl+X" )
        self.__menuCopy = self.__menu.addAction( \
                                    PixmapCache().getIcon( 'copymenu.png' ),
                                    '&Copy', self.onCtrlC, "Ctrl+C" )
        self.__menuPaste = self.__menu.addAction( \
                                    PixmapCache().getIcon( 'pastemenu.png' ),
                                    '&Paste', self.paste, "Ctrl+V" )
        self.__menuSelectAll = self.__menu.addAction( \
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
                                'Do&wnload and show',
                                self.downloadAndShow )
        self.__menu.addSeparator()
        self.__menuHighlightInPrj = self.__menu.addAction(
                                PixmapCache().getIcon( "highlightmenu.png" ),
                                "&Highlight in project browser",
                                editorsManager.onHighlightInPrj )
        self.__menuHighlightInFS = self.__menu.addAction(
                                PixmapCache().getIcon( "highlightmenu.png" ),
                                "H&ighlight in file system browser",
                                editorsManager.onHighlightInFS )
        return

    def __marginNumber( self, xPos ):
        " Calculates the margin number based on a x position "
        width = 0
        for margin in xrange( 5 ):
            width += self.marginWidth( margin )
            if xPos <= width:
                return margin
        return None

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
        self.pylintAct = self.toolsMenu.addAction( \
                            PixmapCache().getIcon( 'pylint.png' ),
                            'pylint', self.parent().onPylint, "Ctrl+L" )
        self.pylintAct.setEnabled( False )
        self.pymetricsAct = self.toolsMenu.addAction( \
                            PixmapCache().getIcon( 'metrics.png' ),
                            'pymetrics', self.parent().onPymetrics, "Ctrl+K" )
        self.toolsMenu.addSeparator()
        self.runAct = self.toolsMenu.addAction( \
                            PixmapCache().getIcon( 'run.png' ),
                            'Run script', self.parent().onRunScript )
        self.runParamAct = self.toolsMenu.addAction( \
                            PixmapCache().getIcon( 'paramsmenu.png' ),
                            'Set parameters and run',
                            self.parent().onRunScriptSettings )
        self.toolsMenu.addSeparator()
        self.profileAct = self.toolsMenu.addAction( \
                            PixmapCache().getIcon( 'profile.png' ),
                            'Profile script', self.parent().onProfileScript )
        self.profileParamAct = self.toolsMenu.addAction( \
                            PixmapCache().getIcon( 'paramsmenu.png' ),
                            'Set parameters and profile',
                            self.parent().onProfileScriptSettings )
        return self.toolsMenu

    def __initDiagramsMenu( self ):
        " Creates the diagrams menu "
        self.diagramsMenu = QMenu( "&Diagrams" )
        self.importsDgmAct = self.diagramsMenu.addAction( \
                                PixmapCache().getIcon( 'importsdiagram.png' ),
                                'Imports diagram',
                                self.parent().onImportDgm )
        self.importsDgmParamAct = self.diagramsMenu.addAction( \
                                PixmapCache().getIcon( 'paramsmenu.png' ),
                                'Fine tuned imports diagram',
                                self.parent().onImportDgmTuned )
        return self.diagramsMenu

    def contextMenuEvent( self, event ):
        " Called just before showing a context menu "
        event.accept()
        if self.__marginNumber( event.x() ) is None:
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
                self.supportedEncodings[ encoding ].setChecked( True )

            self.__menuOpenAsFile.setEnabled( self.openAsFileAvailable() )
            self.__menuDownloadAndShow.setEnabled(
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
        isImportLine, line = self.isImportLine()
        if isImportLine:
            return False
        selectedText = str( self.selectedText() ).strip()
        if selectedText:
            return '\n' not in selectedText and \
                   '\r' not in selectedText

        currentWord = str( self.getCurrentWord() ).strip()
        return currentWord != ""

    def downloadAndShowAvailable( self ):
        " True if download and show available "
        isImportLine, line = self.isImportLine()
        if isImportLine:
            return False
        selectedText = str( self.selectedText() ).strip()
        if not selectedText:
            return False

        if '\n' in selectedText or '\r' in selectedText:
            # Not a single line selection
            return False

        return selectedText.startswith( 'http:' ) or \
               selectedText.startswith( 'https:' ) or \
               ( selectedText.startswith( 'www.' ) and '/' in selectedText )


    def focusInEvent( self, event ):
        " Enable Shift+Tab when the focus is received "
        if not self.parent().shouldAcceptFocus():
            self.parent().setFocus()
            return
        return ScintillaWrapper.focusInEvent( self, event )

    def focusOutEvent( self, event ):
        " Disable Shift+Tab when the focus is lost "
        self.__completer.hide()
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
        fontMetrics = QFontMetrics( skin.lineNumFont )
        self.setMarginWidth( self.LINENUM_MARGIN,
                             fontMetrics.width( ' 8888' ) )

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
        pyflakesMarginMask = ( 1 << self.__pyflakesMsgMarker )
        self.setMarginMarkerMask( self.MESSAGES_MARGIN,
                                  pyflakesMarginMask )
        self.setMarginSensitivity( self.MESSAGES_MARGIN, True )

        return

    def __initIndicators( self ):
        " Initialises indicators "
        skin = GlobalData().skin

        # Search indicator
        self.SendScintilla( self.SCI_INDICSETSTYLE, self.searchIndicator,
                            self.INDIC_ROUNDBOX )
        self.SendScintilla( self.SCI_INDICSETALPHA, self.searchIndicator,
                            skin.searchMarkAlpha )
        self.SendScintilla( self.SCI_INDICSETUNDER, self.searchIndicator,
                            True )
        self.SendScintilla( self.SCI_INDICSETFORE, self.searchIndicator,
                            skin.searchMarkColor )

        self.SendScintilla( self.SCI_INDICSETSTYLE, self.matchIndicator,
                            self.INDIC_ROUNDBOX )
        self.SendScintilla( self.SCI_INDICSETALPHA, self.matchIndicator,
                            skin.matchMarkAlpha )
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

    def __disableKeyBinding( self ):
        " Disable some unwanted key bindings "
        ctrl  = self.SCMOD_CTRL << 16
        # shift = self.SCMOD_SHIFT << 16
        self.SendScintilla( self.SCI_CLEARCMDKEY, ord( 'L' ) + ctrl )
        return

    def gotoLine( self, lineNo ):
        " Jumps to the beginning of the line lineNo "
        self.setCursorPosition( lineNo - 1, 0 )
        self.ensureLineVisible( lineNo )
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
            logging.warning( "Cannot change encoding to '" + \
                             newEncoding + "'. " \
                             "Supported encodings are: " + \
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
        fileEol = self.detectEolString( txt )

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
            logging.critical( "Cannot save " + fileName + \
                              ". Reason: " + str( exc ) )
            return False

        # Now write text to the file
        fileName = unicode( fileName )
        try:
            f = open( fileName, 'wb' )
            f.write( txt )
            f.close()
        except IOError, why:
            logging.critical( "Cannot save " + fileName + \
                              ". Reason: " + str( why ) )
            return False

        self.setEncoding( self.getFileEncoding( fileName, fileType ) )
        self.parent().updateModificationTime( fileName )
        self.parent().setReloadDialogShown( False )
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
            line, pos = self.getCursorPosition()
            lineToTrim = -1
            if line == self.__openedLine:
                lineToTrim = line

            ScintillaWrapper.keyPressEvent( self, event )
            QApplication.processEvents()

            self.__removeLine( lineToTrim )

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

            ScintillaWrapper.keyPressEvent( self, event )
            QApplication.processEvents()

            if lineToTrim != -1:
                line, pos = self.getCursorPosition()
                if line != lineToTrim:
                    # The cursor was really moved to another line
                    self.__removeLine( lineToTrim )
            self.__openedLine = -1

        elif key == Qt.Key_Escape:
            self.emit( SIGNAL('ESCPressed') )
            event.accept()

        elif key == Qt.Key_Tab:
            line, pos = self.getCursorPosition()
            if pos != 0:
                char = self.charAt( self.currentPosition() - 1 )
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

        else:
            # Special keyboard keys are delivered as 0 values
            if key != 0:
                self.__openedLine = -1
                ScintillaWrapper.keyPressEvent( self, event )

        self.__skipChangeCursor = False
        return

    def __onCursorPositionChanged( self, line, pos ):
        " Triggered when the cursor changed the position "
        if self.__skipChangeCursor:
            return

        if line == self.__openedLine:
            self.__openedLine = -1
            return

        self.__skipChangeCursor = True
        self.__removeLine( self.__openedLine )
        self.__skipChangeCursor = False
        self.__openedLine = -1
        return

    def __removeLine( self, line ):
        " Removes characters from the given line "
        if line < 0:
            return

        currentLine, currentPos = self.getCursorPosition()
        oldBuffer = QApplication.clipboard().text()
        self.beginUndoAction()
        self.setCursorPosition( line, 0 )
        self.extendSelectionToEOL()
        self.removeSelectedText()
        self.setCursorPosition( currentLine, currentPos )
        self.endUndoAction()
        QApplication.clipboard().setText( oldBuffer )
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

    def __onDwellStart( self, position, x, y ):
        " Triggered when mouse started to dwell "
        if not self.underMouse():
            return
        marginNumber = self.__marginNumber( x )
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

    def __onDwellEnd( self, position, x, y ):
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
            if TextEditor.textToIterate == text:
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

    def __onAltShiftUp( self ):
        " Triggered when Alt+Shift+Up is received "
        self.SendScintilla( QsciScintilla.SCI_PARAUPEXTEND )
        return True

    def __onAltShiftDown( self ):
        " Triggered when Alt+Shift+Down is received "
        self.SendScintilla( QsciScintilla.SCI_PARADOWNEXTEND )
        return True

    def __onAlShiftLeft( self ):
        " Triggered when Alt+Shift+Left is received "
        self.SendScintilla( QsciScintilla.SCI_WORDPARTLEFTEXTEND )
        return True

    def __onAlShiftRight( self ):
        " Triggered when Alt+Shift+Right is received "
        self.SendScintilla( QsciScintilla.SCI_WORDPARTRIGHTEXTEND )
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
            return True

        line, pos = self.getCursorPosition()
        if isModName:
            # The prefix should be re-taken because a module name may have '.'
            # in it.
            self.__completionPrefix = self.getWord( line, pos, 1, True, "." )

        currentPosFont = self.getCurrentPosFont()
        self.__completer.setWordsList( words, currentPosFont )
        self.__completer.setPrefix( self.__completionPrefix )

        count = self.__completer.completionCount()
        if count == 0:
            self.setFocus()
            return True

        # Make sure the line is visible
        self.ensureLineVisible( line )
        xPos, yPos = self.getCurrentPixelPosition()
        if self.hasSelectedText():
            # Remove the selection as it could be interpreted not as expected
            self.setSelection( line, pos, line, pos )

        if count == 1:
            self.insertCompletion( self.__completer.currentCompletion() )
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
        return True

    def onTagHelp( self ):
        " Provides help for an item if available "
        calltip, docstring = getCalltipAndDoc( self.parent().getFileName(),
                                               self )
        GlobalData().mainWindow.showTagHelp( calltip, docstring )
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
            GlobalData().mainWindow.showStatusBarMessage( \
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

    def onOccurences( self ):
        " The user requested a list of occurances "
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return True
        if not os.path.isabs( self.parent().getFileName() ):
            GlobalData().mainWindow.showStatusBarMessage( \
                                            "Save the buffer first" )
            return True
        if self.isModified():
            # Check that the directory is writable for a temporary file
            dirName = os.path.dirname( self.parent().getFileName() )
            if not os.access( dirName, os.W_OK ):
                GlobalData().mainWindow.showStatusBarMessage( \
                                "File directory is not writable. " \
                                "Cannot run rope." )
                return True

        # Prerequisites were checked, run the rope library
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        name, locations = getOccurrences( self.parent().getFileName(), self )
        if len( locations ) == 0:
            QApplication.restoreOverrideCursor()
            GlobalData().mainWindow.showStatusBarMessage( \
                                        "No occurances of " + name + " found" )
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
        if text != "":
            oldBuffer = QApplication.clipboard().text()
            prefixLength = len( self.__completionPrefix )
            line, pos = self.getCursorPosition()
            self.beginUndoAction()
            self.setSelection( line, pos - prefixLength, line, pos )
            self.removeSelectedText()
            self.insert( text )
            self.setCursorPosition( line, pos + len( text ) - prefixLength )
            self.endUndoAction()
            self.__completionPrefix = ""
            self.__completionObject = ""
            self.__completer.hide()
            QApplication.clipboard().setText( oldBuffer )
        return

    def isImportLine( self ):
        " Returns True if the current line is a part of an import line "
        if self.isInStringLiteral():
            return False, -1

        line, pos = self.getCursorPosition()
        pos = pos   # Makes pylint happy

        # Find the beginning of the line
        while True:
            if line == 0:
                break
            prevLine = self.text( line - 1 ).trimmed()
            if not prevLine.endsWith( '\\' ):
                break
            line -= 1

        text = str( self.text( line ) ).lstrip()
        if text.startswith( "import " ) or text.startswith( "from " ) or \
           text.startswith( "import\\" ) or text.startswith( "from\\" ):
            if not self.isInStringLiteral( line, 0 ):
                return True, line

        return False, -1


    def isOnSomeImport( self ):
        """ Returns 3 values:
            bool   - this is an import line
            bool   - a list of modules should be provided
            string - module name from which an aobject is to imported
        """
        # There are two case:
        # import BLA1, BLA2 as WHATEVER2, BLA3
        # from BLA import X, Y as y, Z
        isImport, line = self.isImportLine()
        if isImport == False:
            return False, False, ""

        text = self.text( line ).trimmed()
        if text.startsWith( "import" ):
            currentWord = self.getCurrentWord()
            if currentWord in [ "import", "as" ]:
                # It is an import line, but no need to complete
                return True, False, ""
            # Search for the first non space character before the current word
            position = self.currentPosition() - 1
            while self.charAt(position) not in [ ' ', '\\', '\r', '\n', '\t' ]:
                position -= 1
            while self.charAt(position) in [ ' ', '\\', '\r', '\n', '\t' ]:
                position -= 1
            if self.charAt(position) == ',':
                # It's an import line and need to complete
                return True, True, ""

            line, pos = self.lineIndexFromPosition( position )
            previousWord = self.getWord( line, pos )
            if previousWord == "import":
                # It's an import line and need to complete
                return True, True, ""
            # It;s an import line but no need to complete
            return True, False, ""

        # Here: this is the from x import bla as ... statement
        currentWord = self.getCurrentWord()
        if currentWord in [ "from", "import", "as" ]:
            return True, False, ""
        # Search for the first non space character before the current word
        position = self.currentPosition() - 1
        while self.charAt( position ) not in [ ' ', '\\', '\r', '\n', '\t' ]:
            position -= 1
        while self.charAt( position ) in [ ' ', '\\', '\r', '\n', '\t' ]:
            position -= 1

        wordLine, pos = self.lineIndexFromPosition( position )
        previousWord = self.getWord( wordLine, pos )
        if previousWord == "as":
            # Nothing should be completed
            return True, False, ""
        if previousWord == "from":
            # Completing a module
            return True, True, ""
        if previousWord == "import" or self.charAt( position ) == ',':
            # Need to complete an imported object
            position = self.positionFromLineIndex( line, 0 )
            while self.charAt( position ) in [ ' ', '\t' ]:
                position += 1
            # Expected 'from' at this position
            wordLine, pos = self.lineIndexFromPosition( position )
            word = self.getWord( wordLine, pos )
            if word != 'from':
                return True, False, ""
            # Next is a module name
            position += len( 'from' )
            while self.charAt( position ) in [ ' ', '\\', '\r', '\n', '\t' ]:
                position += 1
            wordLine, pos = self.lineIndexFromPosition( position )
            moduleName = self.getWord( wordLine, pos, 0, True, "." )
            if moduleName == "":
                return True, False, ""
            # Sanity check - there is 'import' after that
            position += len( moduleName )
            while self.charAt( position ) in [ ' ', '\\', '\r', '\n', '\t' ]:
                position += 1
            wordLine, pos = self.lineIndexFromPosition( position )
            word = self.getWord( wordLine, pos )
            if word != 'import':
                return True, False, ""
            # Finally, this is a completion for an imported object
            return True, True, moduleName

        return True, False, ""


    def isRemarkLine( self, line = -1, pos = -1 ):
        " Returns true if the current line is a remark one "
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return False

        if line == -1 or pos == -1:
            cursorPosition = self.currentPosition()
        else:
            cursorPosition = self.positionFromLineIndex( line, pos )
        return self.styleAt( cursorPosition ) in \
                            [ QsciLexerPython.Comment,
                              QsciLexerPython.CommentBlock ]


    def isInStringLiteral( self, line = -1, pos = -1 ):
        " Returns True if the current cursor position is in a string literal "
        if self.parent().getFileType() not in [ PythonFileType,
                                                Python3FileType ]:
            return False

        if line == -1 or pos == -1:
            cursorPosition = self.currentPosition()
        else:
            cursorPosition = self.positionFromLineIndex( line, pos )
        return self.styleAt( cursorPosition ) in \
                            [ QsciLexerPython.TripleDoubleQuotedString,
                              QsciLexerPython.TripleSingleQuotedString,
                              QsciLexerPython.DoubleQuotedString,
                              QsciLexerPython.SingleQuotedString,
                              QsciLexerPython.UnclosedString ]


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
        return

    def addPyflakesMessage( self, line, message ):
        " Shows up a pyflakes message "
        self.ignoreBufferChangedSignal = True
        if line <= 0:
            line = 1    # Sometimes line is reported as 0

        handle = self.markerAdd( line - 1, self.__pyflakesMsgMarker )
        self.__pyflakesMessages[ handle ] = message
        self.ignoreBufferChangedSignal = False
        return

    def downloadAndShow( self ):
        " Triggered when the user wants to download and see the file "
        return


class TextEditorTabWidget( QWidget, MainWindowTabWidgetBase ):
    " Plain text editor tab widget "

    def __init__( self, parent = None ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        self.__editor = TextEditor( self )
        self.__fileName = ""
        self.__shortName = ""
        self.__fileType = UnknownFileType

        self.__createLayout()
        self.__editor.zoomTo( Settings().zoom )

        self.connect( self.__editor, SIGNAL( 'modificationChanged(bool)' ),
                      self.modificationChanged )

        self.__diskModTime = None
        self.__reloadDlgShown = False

        self.__debugMode = False
        return

    def shouldAcceptFocus( self ):
        return self.__outsideChangesBar.isHidden()

    def readFile( self, fileName ):
        " Reads the text from a file "
        self.__editor.readFile( fileName )

        # Memorize the modification date
        self.__diskModTime = os.path.getmtime( os.path.realpath( fileName ) )
        return

    def writeFile( self, fileName ):
        " Writes the text to a file "
        if self.__editor.writeFile( fileName ):
            # Memorize the modification date
            self.__diskModTime = os.path.getmtime( \
                                            os.path.realpath( fileName ) )
            return True
        return False

    def __createLayout( self ):
        " Creates the toolbar and layout "

        # Buttons
        printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                               'Print', self )
        printButton.setEnabled( False )
        self.connect( printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )

        printPreviewButton = QAction( \
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        printPreviewButton.setEnabled( False )
        self.connect( printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )

        self.pylintButton = QAction( \
            PixmapCache().getIcon( 'pylint.png' ),
            'Analyse the file (Ctrl+L)', self )
        self.connect( self.pylintButton, SIGNAL( 'triggered()' ),
                      self.onPylint )
        self.pylintButton.setEnabled( False )

        self.pymetricsButton = QAction( \
            PixmapCache().getIcon( 'metrics.png' ),
            'Calculate the file metrics (Ctrl+K)', self )
        self.connect( self.pymetricsButton, SIGNAL( 'triggered()' ),
                      self.onPymetrics )
        self.pymetricsButton.setEnabled( False )

        # Imports diagram and its menu
        importsMenu = QMenu( self )
        importsDlgAct = importsMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Fine tuned imports diagram' )
        self.connect( importsDlgAct, SIGNAL( 'triggered()' ),
                      self.onImportDgmTuned )
        self.importsDiagramButton = QToolButton( self )
        self.importsDiagramButton.setIcon( \
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
        runScriptDlgAct = runScriptMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set run/debug parameters' )
        self.connect( runScriptDlgAct, SIGNAL( 'triggered()' ),
                      self.onRunScriptSettings )
        self.runScriptButton = QToolButton( self )
        self.runScriptButton.setIcon( \
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
        profileScriptDlgAct = profileScriptMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set profile parameters' )
        self.connect( profileScriptDlgAct, SIGNAL( 'triggered()' ),
                      self.onProfileScriptSettings )
        self.profileScriptButton = QToolButton( self )
        self.profileScriptButton.setIcon( \
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
        debugScriptDlgAct = debugScriptMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set run/debug parameters' )
        self.connect( debugScriptDlgAct, SIGNAL( 'triggered()' ),
                      self.__onDebugScriptSettings )
        self.debugScriptButton = QToolButton( self )
        self.debugScriptButton.setIcon( \
                            PixmapCache().getIcon( 'debugger.png' ) )
        self.debugScriptButton.setToolTip( 'Debug script' )
        self.debugScriptButton.setPopupMode( QToolButton.DelayedPopup )
        self.debugScriptButton.setMenu( debugScriptMenu )
        self.debugScriptButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.debugScriptButton, SIGNAL( 'clicked(bool)' ),
                      self.__onDebugScript )
        self.debugScriptButton.setEnabled( False )
        self.debugScriptButton.setVisible( False )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.__undoButton = QAction( \
            PixmapCache().getIcon( 'undo.png' ), 'Undo (Ctrl+Z)', self )
        self.__undoButton.setShortcut( 'Ctrl+Z' )
        self.connect( self.__undoButton, SIGNAL( 'triggered()' ),
                      self.__editor.onUndo )
        self.__undoButton.setEnabled( False )

        self.__redoButton = QAction( \
            PixmapCache().getIcon( 'redo.png' ), 'Redo (Ctrl+Shift+Z)', self )
        self.__redoButton.setShortcut( 'Ctrl+Shift+Z' )
        self.connect( self.__redoButton, SIGNAL( 'triggered()' ),
                      self.__editor.onRedo )
        self.__redoButton.setEnabled( False )

        # Python tidy script button and its menu
        pythonTidyMenu = QMenu( self )
        pythonTidyDlgAct = pythonTidyMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Set python tidy parameters' )
        self.connect( pythonTidyDlgAct, SIGNAL( 'triggered()' ),
                      self.onPythonTidySettings )
        self.pythonTidyButton = QToolButton( self )
        self.pythonTidyButton.setIcon( \
                      PixmapCache().getIcon( 'pythontidy.png' ) )
        self.pythonTidyButton.setToolTip( 'Python tidy (code must be ' \
                                          'syntactically valid)' )
        self.pythonTidyButton.setPopupMode( QToolButton.DelayedPopup )
        self.pythonTidyButton.setMenu( pythonTidyMenu )
        self.pythonTidyButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.pythonTidyButton, SIGNAL( 'clicked(bool)' ),
                      self.onPythonTidy )
        self.pythonTidyButton.setEnabled( False )

        self.lineCounterButton = QAction( \
            PixmapCache().getIcon( 'linecounter.png' ),
            'Line counter', self )
        self.connect( self.lineCounterButton, SIGNAL( 'triggered()' ),
                      self.onLineCounter )

        self.removeTrailingSpacesButton = QAction( \
            PixmapCache().getIcon( 'trailingws.png' ),
            'Remove trailing spaces', self )
        self.connect( self.removeTrailingSpacesButton, SIGNAL( 'triggered()' ),
                      self.onRemoveTrailingWS )
        self.expandTabsButton = QAction( \
            PixmapCache().getIcon( 'expandtabs.png' ),
            'Expand tabs (4 spaces)', self )
        self.connect( self.expandTabsButton, SIGNAL( 'triggered()' ),
                      self.onExpandTabs )

        # Zoom buttons
        zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
                                'Zoom in (Ctrl+=)', self )
        self.connect( zoomInButton, SIGNAL( 'triggered()' ), self.onZoomIn )

        zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
                                'Zoom out (Ctrl+-)', self )
        self.connect( zoomOutButton, SIGNAL( 'triggered()' ), self.onZoomOut )

        zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
                                   'Zoom reset (Ctrl+0)', self )
        self.connect( zoomResetButton, SIGNAL( 'triggered()' ),
                      self.onZoomReset )

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight( 16 )

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
        toolbar.addAction( zoomInButton )
        toolbar.addAction( zoomOutButton )
        toolbar.addAction( zoomResetButton )
        toolbar.addWidget( fixedSpacer )
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
        self.runScriptButton.setEnabled( isPythonFile and
                                         self.isModified() == False and
                                         os.path.isabs( self.__fileName ) )
        self.profileScriptButton.setEnabled( self.runScriptButton.isEnabled() )
        self.__editor.runAct.setEnabled( self.runScriptButton.isEnabled() )
        self.__editor.runParamAct.setEnabled( self.runScriptButton.isEnabled() )
        self.__editor.profileAct.setEnabled( self.runScriptButton.isEnabled() )
        self.__editor.profileParamAct.setEnabled(
                                    self.runScriptButton.isEnabled() )
        self.debugScriptButton.setEnabled( isPythonFile and
                                    self.isModified() == False and
                                    os.path.isabs( self.__fileName ) )
        self.pythonTidyButton.setEnabled( isPythonFile )
        self.lineCounterButton.setEnabled( isPythonFile )
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
        self.runScriptButton.setEnabled( self.__fileType == PythonFileType and \
                                         self.isModified() == False and \
                                         self.__debugMode == False and \
                                         os.path.isabs( self.__fileName ) )
        self.profileScriptButton.setEnabled( self.runScriptButton.isEnabled() )
        self.debugScriptButton.setEnabled( self.runScriptButton.isEnabled() )
        return

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
        isImportLine, lineNo = self.__editor.isImportLine()
        basePath = os.path.dirname( self.__fileName )

        if isImportLine:
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
                    GlobalData().mainWindow.showStatusBarMessage( \
                        "The import '" + lineImports[ 0 ] + \
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
        workingDir, cmd, environment = getCwdCmdEnv( fileName, params,
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

    def __onDebugScriptSettings( self ):
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
            self.__onDebugScript()
        return

    def __onDebugScript( self ):
        " Starts debugging "
        if self.__checkDebugPrerequisites() == False:
            return

        fileName = self.getFileName()
        params = GlobalData().getRunParameters( fileName )
        workingDir, cmd, environment = getCwdCmdEnv( fileName, params,
                                                     Settings().terminalType )
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
        return self.__diskModTime != \
               os.path.getmtime( os.path.realpath( self.__fileName ) )

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
        return self.__reloadDlgShown

    def updateModificationTime( self, fileName ):
        " Updates the modification time "
        self.__diskModTime = \
                    os.path.getmtime( os.path.realpath( fileName ) )
        return

    def setDebugMode( self, mode, isProjectFile ):
        " Called to switch debug/development "
        skin = GlobalData().skin
        self.__debugMode = mode

        if mode == True:
            self.__editor.setMarginsBackgroundColor( skin.marginPaperDebug )
            self.__editor.setMarginsForegroundColor( skin.marginColorDebug )
            self.__editor.setReadOnly( isProjectFile )

            # Undo/redo
            if isProjectFile:
                self.__undoButton.setEnabled( False )
                self.__redoButton.setEnabled( False )

                # Spaces/tabs/line
                self.removeTrailingSpacesButton.setEnabled( False )
                self.expandTabsButton.setEnabled( False )
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

        # Run/debug buttons
        self.__updateRunDebugButtons()
        return
