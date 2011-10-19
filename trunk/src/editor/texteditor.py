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
import lexer
from scintillawrap              import ScintillaWrapper
from PyQt4.QtCore               import Qt, QFileInfo, SIGNAL, QSize, \
                                       QVariant, QDir, QUrl, QEvent
from PyQt4.QtGui                import QApplication, QCursor, \
                                       QFontMetrics, QToolBar, \
                                       QHBoxLayout, QWidget, QAction, QMenu, \
                                       QSizePolicy, QToolButton, QFileDialog, \
                                       QDialog, QMessageBox, QShortcut
from PyQt4.Qsci                 import QsciScintilla
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.fileutils            import detectFileType, DesignerFileType, \
                                       LinguistFileType, MakefileType, \
                                       getFileLanguage, UnknownFileType, \
                                       PythonFileType, Python3FileType
from utils.encoding             import decode, encode, CodingError
from utils.pixmapcache          import PixmapCache
from utils.globals              import GlobalData
from utils.settings             import Settings
from ui.pylintviewer            import PylintViewer
from ui.pymetricsviewer         import PymetricsViewer
from diagram.importsdgm         import ImportsDiagramDialog, \
                                       ImportDiagramOptions, \
                                       ImportsDiagramProgress
from utils.importutils          import getImportsList, \
                                       getImportsInLine, resolveImport, \
                                       getImportedNameDefinitionLine
from ui.importlist              import ImportListWidget
import export


class TextEditor( ScintillaWrapper ):
    " Text editor implementation "

    matchIndicator    = ScintillaWrapper.INDIC_CONTAINER
    searchIndicator   = ScintillaWrapper.INDIC_CONTAINER + 1
    spellingIndicator = ScintillaWrapper.INDIC_CONTAINER + 2

    def __init__( self, parent = None ):

        ScintillaWrapper.__init__( self, parent )
        self.__initMargins()
        self.__initIndicators()
        self.__disableKeyBinding()

        self.connect( self, SIGNAL( 'SCN_DOUBLECLICK(int,int,int)' ),
                      self.__onDoubleClick )

        skin = GlobalData().skin

        self.encoding = 'utf-8'     # default
        self.lexer_ = None

        self.setPaper( skin.nolexerPaper )
        self.setColor( skin.nolexerColor )
        self.monospacedStyles( skin.nolexerFont )

        self.setAttribute( Qt.WA_DeleteOnClose )
        self.setAttribute( Qt.WA_KeyCompression )
        self.setUtf8( True )
        self.setFocusPolicy( Qt.StrongFocus )
        self.setIndentationWidth( 4 )
        self.setTabWidth( 4 )
        self.setEdgeColumn( 80 )

        self.setMatchedBraceBackgroundColor( skin.matchedBracePaper )
        self.setMatchedBraceForegroundColor( skin.matchedBraceColor )
        self.setUnmatchedBraceBackgroundColor( skin.unmatchedBracePaper )
        self.setUnmatchedBraceForegroundColor( skin.unmatchedBraceColor )
        self.setIndentationGuidesBackgroundColor( skin.indentGuidePaper )
        self.setIndentationGuidesForegroundColor( skin.indentGuideColor )

        self.updateSettings()

        # Shift+Tab support
        self.shiftTab = QAction( self )
        self.shiftTab.setShortcut( 'Shift+Tab' )
        self.connect( self.shiftTab, SIGNAL( 'triggered()' ), self.__onDedent )
        self.addAction( self.shiftTab )
        return

    def focusInEvent( self, event ):
        " Enable Shift+Tab when the focus is received "
        self.shiftTab.setEnabled( True )
        return ScintillaWrapper.focusInEvent( self, event )

    def focusOutEvent( self, event ):
        " Disable Shift+Tab when the focus is lost "
        self.shiftTab.setEnabled( False )
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
        for margin in range( 5 ):
            self.setMarginLineNumbers( margin, False )
            self.setMarginMarkerMask( margin, 0 )
            self.setMarginWidth( margin, 0 )
            self.setMarginSensitivity( margin, False )

        skin = GlobalData().skin
        self.setMarginsBackgroundColor( skin.marginPaper )
        self.setMarginsForegroundColor( skin.marginColor )

        # Set margin 0 for line numbers
        self.setMarginsFont( skin.lineNumFont )
        self.setMarginLineNumbers( 0, True )
        fontMetrics = QFontMetrics( skin.lineNumFont )
        self.setMarginWidth( 0, fontMetrics.width( ' 8888' ) )

        # Setup bookmark margin
        self.setMarginWidth( 1, 16 )

        # Setup folding margin
        self.setMarginWidth( 2, 16 )
        self.setFolding( QsciScintilla.PlainFoldStyle, 2 )
        self.setFoldMarginColors( skin.foldingColor,
                                  skin.foldingPaper )
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
        shift = self.SCMOD_SHIFT << 16
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
        if self.lexer_ is not None:
            self.lexer_.setDefaultPaper( GlobalData().skin.nolexerPaper )
            self.lexer_.setDefaultColor( GlobalData().skin.nolexerColor )
            self.lexer_.setDefaultFont( GlobalData().skin.nolexerFont )
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
        return

    def __styleNeeded( self, position ):
        " Handles the need for more styling "
        self.lexer_.styleText( self.getEndStyled(), position )
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
            txt, self.encoding = decode( f.read() )
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

    def writeFile( self, fileName ):
        " Writes the text to a file "

        fileName = unicode( fileName )
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
            txt, self.encoding = encode( txt, self.encoding )
        except CodingError, exc:
            logging.critical( "Cannot save " + fileName + \
                              ". Reason: " + str( exc ) )
            return False

        # now write text to the file fn
        try:
            f = open( fileName, 'wb' )
            f.write( txt )
            f.close()
        except IOError, why:
            logging.critical( "Cannot save " + fileName + \
                              ". Reason: " + str( why ) )
            return False
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

        if event.key() == Qt.Key_Escape:
            self.emit( SIGNAL('ESCPressed') )
            event.accept()
        elif event.key() == Qt.Key_Home:
            ScintillaWrapper.keyPressEvent( self, event )
            line, pos = self.getCursorPosition()
            if pos != 0:
                # Process HOME once more to make the cursor jumping to the real
                # beginning of the line
                event.setAccepted( False )
                ScintillaWrapper.keyPressEvent( self, event )
        elif event.key() == Qt.Key_N and Qt.ControlModifier & event.modifiers():
            self.__onHighlight()
            event.accept()
        elif event.key() == Qt.Key_Backslash and Qt.ControlModifier & event.modifiers():
            self.__onCompleteFromDocument()
            event.accept()
        elif event.key() in [ Qt.Key_Left, Qt.Key_Right ] and \
             Qt.AltModifier & event.modifiers():
            event.accept()
        else:
            ScintillaWrapper.keyPressEvent( self, event )
        return

    def getLanguage( self ):
        " Provides the lexer language if it is set "
        if self.lexer_ is not None:
            return self.lexer_.language()
        return "Unknown"

    def __onDoubleClick( self, position, line, modifier ):
        " Triggered when the user double clicks in the editor "
        self.highlightWord( self.selectedText() )
        return

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
        " Triggered when Ctrl+N is clicked "
        self.highlightWord( self.getCurrentWord() )
        return

    def __onDedent( self ):
        " Triggered when Shift+Tab is clicked "
        self.SendScintilla( QsciScintilla.SCI_BACKTAB )
        return

    def __onCompleteFromDocument( self ):
        " Triggered when Ctrl+\\ is clicked "
        self.autoCompleteFromDocument()
        return

    def isImportLine( self ):
        " Returns True if the current line is a part of an import line "
        line, pos = self.getCursorPosition()

        text = self.text( line ).trimmed()
        while 1:
            if text.startsWith( "import" ) or text.startsWith( "from" ):
                return True, line

            # It could be continuation of the previous import line
            line -= 1
            if line < 0:
                break
            text = self.text( line ).trimmed()
            if not text.endsWith( '\\' ):
                break
        return False, -1


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
                      self.__modificationChanged )

        openImportAction = QShortcut( 'Ctrl+I', self )
        self.connect( openImportAction, SIGNAL( "activated()" ),
                      self.__onOpenImport )
        return

    def __createLayout( self ):
        " Creates the toolbar and layout "

        # Buttons
        printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                               'Print', self )
        printButton.setEnabled( False )
        #printButton.setShortcut( 'Ctrl+' )
        self.connect( printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )

        printPreviewButton = QAction( \
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        printPreviewButton.setEnabled( False )
        #printPreviewButton.setShortcut( 'Ctrl+' )
        self.connect( printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )

        self.pylintButton = QAction( \
            PixmapCache().getIcon( 'pylint.png' ),
            'Analyse the file (Ctrl+L)', self )
        self.pylintButton.setShortcut( 'Ctrl+L' )
        self.connect( self.pylintButton, SIGNAL( 'triggered()' ),
                      self.__onPylint )
        self.pylintButton.setEnabled( False )

        self.pymetricsButton = QAction( \
            PixmapCache().getIcon( 'metrics.png' ),
            'Calculate the file metrics (Ctrl+K)', self )
        self.pymetricsButton.setShortcut( 'Ctrl+K' )
        self.connect( self.pymetricsButton, SIGNAL( 'triggered()' ),
                      self.__onPymetrics )
        self.pymetricsButton.setEnabled( False )

        # Imports diagram and its menu
        importsMenu = QMenu( self )
        importsDlgAct = importsMenu.addAction( \
                                PixmapCache().getIcon( 'detailsdlg.png' ),
                                'Fine tuned imports diagram' )
        self.connect( importsDlgAct, SIGNAL( 'triggered()' ),
                      self.__onImportDgmTuned )
        self.importsDiagramButton = QToolButton( self )
        self.importsDiagramButton.setIcon( \
                            PixmapCache().getIcon( 'importsdiagram.png' ) )
        self.importsDiagramButton.setToolTip( 'Generate imports diagram' )
        self.importsDiagramButton.setPopupMode( QToolButton.DelayedPopup )
        self.importsDiagramButton.setMenu( importsMenu )
        self.importsDiagramButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.importsDiagramButton, SIGNAL( 'clicked(bool)' ),
                      self.__onImportDgm )
        self.importsDiagramButton.setEnabled( False )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        exportMenu = QMenu( self )
        self.connect( exportMenu, SIGNAL( "triggered(QAction*)" ),
                      self.__onExportRequest )
        exportMenu.addAction( PixmapCache().getIcon( 'filehtml.png' ),
                              'HTML' ).setData( QVariant( 0 ) )
        exportMenu.addAction( PixmapCache().getIcon( 'filepdf.png' ),
                              'PDF' ).setData( QVariant( 1 ) )
        exportMenu.addAction( PixmapCache().getIcon( 'filertf.png' ),
                              'RTF' ).setData( QVariant( 2 ) )
        exportMenu.addAction( PixmapCache().getIcon( 'filetex.png' ),
                              'TEX' ).setData( QVariant( 3 ) )

        exportButton = QToolButton( self )
        exportButton.setIcon( PixmapCache().getIcon( "export.png" ) )
        exportButton.setToolTip( "Export the content to..." )
        exportButton.setPopupMode( QToolButton.InstantPopup )
        exportButton.setMenu( exportMenu )
        exportButton.setEnabled( False )

        self.__undoButton = QAction( \
            PixmapCache().getIcon( 'undo.png' ), 'Undo (Ctrl+Z)', self )
        self.__undoButton.setShortcut( 'Ctrl+Z' )
        self.connect( self.__undoButton, SIGNAL( 'triggered()' ),
                      self.__onUndo )
        self.__undoButton.setEnabled( False )

        self.__redoButton = QAction( \
            PixmapCache().getIcon( 'redo.png' ), 'Redo (Ctrl+Shift+Z)', self )
        self.__redoButton.setShortcut( 'Ctrl+Shift+Z' )
        self.connect( self.__redoButton, SIGNAL( 'triggered()' ),
                      self.__onRedo )
        self.__redoButton.setEnabled( False )

        removeTrailingSpacesButton = QAction( \
            PixmapCache().getIcon( 'trailingws.png' ),
            'Remove trailing spaces', self )
        self.connect( removeTrailingSpacesButton, SIGNAL( 'triggered()' ),
                      self.__onRemoveTrailingWS )
        expandTabsButton = QAction( \
            PixmapCache().getIcon( 'expandtabs.png' ),
            'Expand tabs (4 spaces)', self )
        self.connect( expandTabsButton, SIGNAL( 'triggered()' ),
                      self.__onExpandTabs )

        # Zoom buttons
        zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
                                'Zoom in (Ctrl++)', self )
        zoomInButton.setShortcut( 'Ctrl++' )
        self.connect( zoomInButton, SIGNAL( 'triggered()' ), self.__onZoomIn )

        zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
                                'Zoom out (Ctrl+-)', self )
        zoomOutButton.setShortcut( 'Ctrl+-' )
        self.connect( zoomOutButton, SIGNAL( 'triggered()' ), self.__onZoomOut )

        zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
                                   'Zoom reset (Ctrl+0)', self )
        zoomResetButton.setShortcut( 'Ctrl+0' )
        self.connect( zoomResetButton, SIGNAL( 'triggered()' ),
                      self.__onZoomReset )

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
        toolbar.addAction( self.__undoButton )
        toolbar.addAction( self.__redoButton )
        toolbar.addWidget( spacer )
        toolbar.addAction( zoomInButton )
        toolbar.addAction( zoomOutButton )
        toolbar.addAction( zoomResetButton )
        toolbar.addWidget( fixedSpacer )
        toolbar.addWidget( exportButton )
        toolbar.addAction( removeTrailingSpacesButton )
        toolbar.addAction( expandTabsButton )


        self.__importsBar = ImportListWidget( self.__editor )
        self.__importsBar.hide()

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
            if self.__shortName != "":
                self.__fileType = detectFileType( self.__shortName )
        self.pylintButton.setEnabled( self.__fileType == PythonFileType and
                                      GlobalData().pylintAvailable )
        self.pymetricsButton.setEnabled( self.__fileType == PythonFileType )
        self.importsDiagramButton.setEnabled( \
                            self.__fileType == PythonFileType and
                            GlobalData().graphvizAvailable )
        return

    def __onPylint( self ):
        " Triggers when pylint should be used "

        if self.__fileType == UnknownFileType:
            if self.__shortName != "":
                self.__fileType = detectFileType( self.__shortName )
        if self.__fileType not in [ PythonFileType, Python3FileType ]:
            return

        if self.__fileName != "":
            reportFile = self.__fileName
        else:
            reportFile = self.__shortName

        if self.isModified() or self.__fileName == "":
            # Need to parse the buffer
            GlobalData().mainWindow.showPylintReport( \
                            PylintViewer.SingleBuffer, self.__editor.text(),
                            reportFile, self.getUUID() )
        else:
            # Need to parse the file
            GlobalData().mainWindow.showPylintReport( \
                            PylintViewer.SingleFile, self.__fileName,
                            reportFile, self.getUUID() )
        return

    def __onPymetrics( self ):
        " Triggers when pymetrics should be used "

        if self.__fileType == UnknownFileType:
            if self.__shortName != "":
                self.__fileType = detectFileType( self.__shortName )
        if self.__fileType not in [ PythonFileType, Python3FileType ]:
            return

        if self.__fileName != "":
            reportFile = self.__fileName
        else:
            reportFile = self.__shortName

        if self.isModified() or self.__fileName == "":
            # Need to parse the buffer
            GlobalData().mainWindow.showPymetricsReport( \
                            PymetricsViewer.SingleBuffer, self.__editor.text(),
                            reportFile, self.getUUID() )
        else:
            # Need to parse the file
            GlobalData().mainWindow.showPymetricsReport( \
                            PymetricsViewer.SingleFile, self.__fileName,
                            reportFile, self.getUUID() )
        return


    def __onExportRequest( self, act ):
        " Triggers when one of the export items is selected "

        index, isOK = act.data().toInt()
        if not isOK:
            return
        if index < 0 or index > 3:
            logging.error( "Invalid export format requested" )
            return

        if index == 0:
            title = "Export to HTML"
            ext = "html"
        elif index == 1:
            title = "Export to PDF"
            ext = "pdf"
        elif index == 2:
            title = "Export to RTF"
            ext = "rtf"
        else:
            title = "Export to TeX"
            ext = "tex"

        # select the file to save to
        dialog = QFileDialog( self, title )
        dialog.setFileMode( QFileDialog.AnyFile )
        dialog.setLabelText( QFileDialog.Accept, "Save" )
        projectFile = GlobalData().project.fileName
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )
        if projectFile != "":
            # Project is loaded
            dirs = GlobalData().project.getProjectDirs()
            for item in dirs:
                urls.append( QUrl.fromLocalFile( item ) )
        dialog.setSidebarUrls( urls )

        if self.__fileName != "":
            dialog.setDirectory( os.path.dirname( self.__fileName ) )
            dialog.selectFile( self.__fileName + "." + ext )
        else:
            dialog.setDirectory( QDir.currentPath() )
            dialog.selectFile( self.__shortName + "." + ext )

        dialog.setOption( QFileDialog.DontConfirmOverwrite, False )
        if dialog.exec_() != QDialog.Accepted:
            return False

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath( str( fileNames[ 0 ] ) )

        if os.path.isdir( fileName ):
            logging.error( "A file must be selected" )
            return False

        # Check permissions to write into the file or to a directory
        if os.path.exists( fileName ):
            # Check write permissions for the file
            if not os.access( fileName, os.W_OK ):
                logging.error( "There is no write permissions for " + fileName )
                return False
        else:
            # Check write permissions to the directory
            dirName = os.path.dirname( fileName )
            if not os.access( dirName, os.W_OK ):
                logging.error( "There is no write permissions for the " \
                               "directory " + dirName )
                return False

        if os.path.exists( fileName ):
            res = QMessageBox.warning( \
                self, "Save File",
                "<p>The file <b>" + fileName + "</b> already exists.</p>",
                QMessageBox.StandardButtons( QMessageBox.Abort | \
                                             QMessageBox.Save ),
                QMessageBox.Abort )
            if res == QMessageBox.Abort or res == QMessageBox.Cancel:
                return False

        # OK, the file name was properly selected
        try:
            exporter = export.getExporter( ext, self.__editor )
            if self.__fileName != "":
                exporter.exportSource( self.__fileName, fileName )
            else:
                exporter.exportSource( self.__shortName, fileName )
        except Exception, exc:
            logging.error( str( exc ) )
            return False
        return True

    def __onZoomReset( self ):
        " Triggered when the zoom reset button is pressed "
        if self.__editor.zoom != 0:
            self.emit( SIGNAL( 'TextEditorZoom' ), 0 )
        return

    def __onZoomIn( self ):
        " Triggered when the zoom in button is pressed "
        if self.__editor.zoom < 20:
            self.emit( SIGNAL( 'TextEditorZoom' ), self.__editor.zoom + 1 )
        return

    def __onZoomOut( self ):
        " Triggered when the zoom out button is pressed "
        if self.__editor.zoom > -10:
            self.emit( SIGNAL( 'TextEditorZoom' ), self.__editor.zoom - 1 )
        return

    def __onPrint( self ):
        " Triggered when the print button is pressed "
        pass

    def __onPrintPreview( self ):
        " triggered when the print preview button is pressed "
        pass

    def __modificationChanged( self, modified = False ):
        " Triggered when the content is changed "
        self.__undoButton.setEnabled( self.__editor.isUndoAvailable() )
        self.__redoButton.setEnabled( self.__editor.isRedoAvailable() )
        return

    def __onRedo( self ):
        " Triggered when redo button is clicked "
        if self.__editor.isRedoAvailable():
            self.__editor.redo()
            self.__modificationChanged()
        return

    def __onUndo( self ):
        " Triggered when undo button is clicked "
        if self.__editor.isUndoAvailable():
            self.__editor.undo()
            self.__modificationChanged()
        return

    def __onRemoveTrailingWS( self ):
        " Triggers when the trailing spaces should be wiped out "
        self.__editor.removeTrailingWhitespaces()
        return

    def __onExpandTabs( self ):
        " Expands tabs if there are any "
        self.__editor.expandTabs( 4 )
        return

    def setFocus( self ):
        " Overridden setFocus "
        self.__editor.setFocus()
        return

    def __onImportDgmTuned( self ):
        " Runs the settings dialog first "
        if self.__editor.isModified():
            what = ImportsDiagramDialog.SingleBuffer
            if not os.path.isabs( self.getFileName() ):
                logging.warning( "Imports diagram can only be generated for " \
                                 "a file. Save the editor buffer " \
                                 "and try again." )
                return
        else:
            what = ImportsDiagramDialog.SingleFile
        dlg = ImportsDiagramDialog( what, self.getFileName() )
        if dlg.exec_() == QDialog.Accepted:
            # Should proceed with the diagram generation
            self.__generateImportDiagram( what, dlg.options )
        return

    def __onImportDgm( self, action ):
        " Runs the generation process with default options "
        if self.__editor.isModified():
            what = ImportsDiagramDialog.SingleBuffer
            if not os.path.isabs( self.getFileName() ):
                logging.warning( "Imports diagram can only be generated for " \
                                 "a file. Save the editor buffer " \
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

    def __onOpenImport( self ):
        " Triggered when Ctrl+I is received "

        if self.__fileType not in [ PythonFileType, Python3FileType ]:
            return

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
                    return
                GlobalData().mainWindow.showStatusBarMessage( \
                        "The import '" + currentWord + "' is not resolved." )
                return
            # We are not on a certain import.
            # Check if it is a line with exactly one import
            if len( lineImports ) == 1:
                path = resolveImport( basePath, lineImports[ 0 ] )
                if path == '':
                    GlobalData().mainWindow.showStatusBarMessage( \
                        "The import '" + lineImports[ 0 ] + "' is not resolved." )
                    return
                # The import is resolved. Check where we are.
                if currentWord in importWhat:
                    # We are on a certain imported name in a resolved import
                    # So, jump to the definition line
                    line = getImportedNameDefinitionLine( path, currentWord )
                    GlobalData().mainWindow.openFile( path, line )
                    return
                GlobalData().mainWindow.openFile( path, -1 )
                return

            # Take all the imports in the line and resolve them.
            self.__onImportList( basePath, lineImports )
            return

        # Here: the cursor is not on the import line. Take all the file imports
        # and resolve them
        fileImports = getImportsList( self.__editor.text() )
        if len( fileImports ) == 0:
            GlobalData().mainWindow.showStatusBarMessage( \
                                            "There are no imports" )
            return
        if len( fileImports ) == 1:
            path = resolveImport( basePath, fileImports[ 0 ] )
            if path == '':
                GlobalData().mainWindow.showStatusBarMessage( \
                    "The import '" + fileImports[ 0 ] + "' is not resolved." )
                return
            GlobalData().mainWindow.openFile( path, -1 )
            return

        self.__onImportList( basePath, fileImports )
        return

    def __onImportList( self, basePath, imports ):
        " Works with a list of imports "
        resolvedList = []
        for item in imports:
            path = resolveImport( basePath, item )
            if path != '':
                resolvedList.append( [ item, path ] )
        if len( resolvedList ) == 0:
            GlobalData().mainWindow.showStatusBarMessage( \
                                            "No imports are resolved" )
            return

        # Display the import selection widget
        self.__importsBar.showResolvedList( resolvedList )
        return

    def resizeEvent( self, event ):
        " Resizes the import selection dialogue if necessary "
        QWidget.resizeEvent( self, event )
        if not self.__importsBar.isHidden():
            self.__importsBar.resize()
        return

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

    def getType( self ):
        " Tells the widget type "
        return MainWindowTabWidgetBase.PlainTextEditor

    def getLanguage( self ):
        " Tells the content language "
        if self.__fileType == UnknownFileType:
            if self.__shortName != "":
                self.__fileType = detectFileType( self.__shortName )
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
        return "Unknown"

    def getShortName( self ):
        " Tells the display name "
        return self.__shortName

    def setShortName( self, name ):
        " Sets the display name "
        self.__shortName = name
        self.__fileType = detectFileType( name )
        return

