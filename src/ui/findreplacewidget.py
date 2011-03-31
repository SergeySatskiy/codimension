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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#


""" Find and replace widgets implementation """

from PyQt4.QtGui                import QHBoxLayout, QToolButton, QLabel, \
                                       QSizePolicy, QComboBox, \
                                       QGridLayout, QWidget, QCheckBox, \
                                       QShortcut
from utils.pixmapcache          import PixmapCache
from PyQt4.QtCore               import SIGNAL, Qt, QStringList
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase
from utils.globals              import GlobalData
from utils.project              import CodimensionProject



class FindReplaceBase( QWidget ):
    """ Base class for both find and replace widgets """

    maxHistory = 16

    def __init__( self, editorsManager, parent = None ):

        QWidget.__init__( self, parent )
        self.editorsManager = editorsManager
        self.findHistory = QStringList( GlobalData().project.findHistory )
        self._findBackward = False
        self._selection = None

        # Incremental search support
        # If not None => the search started in this editor and has not been
        # finished
        self._originEditor = None
        self._originPosition = (-1, -1)     # line, pos
        self._originFirstLine = -1
        self._matchTarget = [-1, -1, -1]    # line, pos, length

        # Common graphics items
        self.closeButton = QToolButton( self )
        self.closeButton.setToolTip( "Close the dialog (ESC)" )
        self.closeButton.setIcon( PixmapCache().getIcon( "close.png" ) )
        self.connect( self.closeButton, SIGNAL( "clicked()" ), self.hide )

        self.findLabel = QLabel( self )
        self.findLabel.setText( "Find:" )

        self.findtextCombo = QComboBox( self )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                self.findtextCombo.sizePolicy().hasHeightForWidth() )
        self.findtextCombo.setSizePolicy( sizePolicy )
        self.findtextCombo.setEditable( True )
        self.findtextCombo.setInsertPolicy( QComboBox.InsertAtTop )
        self.findtextCombo.setAutoCompletion( False )
        self.findtextCombo.setDuplicatesEnabled( False )
        self.findtextCombo.setEnabled( False )
        self.connect( self.findtextCombo,
                      SIGNAL( 'editTextChanged(const QString&)' ),
                      self._onEditTextChanged )

        self.findPrevButton = QToolButton( self )
        self.findPrevButton.setToolTip( "Previous occurrence (Shift+F3)" )
        self.findPrevButton.setIcon( PixmapCache().getIcon( "1leftarrow.png" ) )
        self.findPrevButton.setFocusPolicy( Qt.NoFocus )
        self.findPrevButton.setEnabled( False )

        self.findNextButton = QToolButton( self )
        self.findNextButton.setToolTip( "Next occurrence (F3)" )
        self.findNextButton.setIcon( \
                    PixmapCache().getIcon( "1rightarrow.png" ) )
        self.findNextButton.setFocusPolicy( Qt.NoFocus )
        self.findNextButton.setEnabled( False )

        self.caseCheckBox = QCheckBox( self)
        self.caseCheckBox.setText( "Match case" )
        self.caseCheckBox.setFocusPolicy( Qt.NoFocus )
        self.caseCheckBox.setEnabled( False )

        self.wordCheckBox = QCheckBox( self )
        self.wordCheckBox.setText( "Whole word" )
        self.wordCheckBox.setFocusPolicy( Qt.NoFocus )
        self.wordCheckBox.setEnabled( False )

        self.regexpCheckBox = QCheckBox( self )
        self.regexpCheckBox.setText( "Regexp" )
        self.regexpCheckBox.setFocusPolicy( Qt.NoFocus )
        self.regexpCheckBox.setEnabled( False )
        return

    def _finalizeSearch( self ):
        " Finalizes search in an editor if so "
        if self._originEditor is None:
            return
        if self._matchTarget == [-1, -1, -1]:
            self._originEditor = None
            self._originPosition = (-1, -1)
            self._originFirstLine = -1
            return

        line, pos = self._originEditor.getCursorPosition()
        if self._originPosition[ 0 ] != line or \
            self._originPosition[ 1 ] != pos:
            # The cursor has been moved, so no jumps
            self._matchTarget = [-1, -1, -1]
            self._originEditor = None
            self._originPosition = (-1, -1)
            self._originFirstLine = -1
            return

        # Move the cursor
        self._originEditor.setCursorPosition( self._matchTarget[ 0 ],
                                              self._matchTarget[ 1 ] )
        self._originEditor.ensureLineVisible( self._matchTarget[ 0 ] )

        self._matchTarget = [-1, -1, -1]
        self._originEditor = None
        self._originPosition = (-1, -1)
        self._originFirstLine = -1
        return

    def keyPressEvent( self, event ):
        " Handles the key press events only when the focus is in the search bar "
        if event.key() == Qt.Key_Escape:
            self._finalizeSearch()
            activeWindow = self.editorsManager.currentWidget()
            if activeWindow:
                activeWindow.setFocus()
            event.accept()
            self.hide()
        return

    def setFocus( self ):
        " Overridded setFocus "
        self.findtextCombo.setFocus()
        return

    def updateStatus( self ):
        " Triggered when the current tab is changed "

        currentWidget = self.editorsManager.currentWidget()
        status = currentWidget.getType() in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]
        self.findtextCombo.setEnabled( status )
        self.findPrevButton.setEnabled( status and \
                                        self.findtextCombo.currentText() != "" )
        self.findNextButton.setEnabled( status and \
                                        self.findtextCombo.currentText() != "" )
        self.caseCheckBox.setEnabled( status )
        self.wordCheckBox.setEnabled( status )
        self.regexpCheckBox.setEnabled( status )

        self._updateSelection()
        return

    def copyAvailable( self, status ):
        " Triggered when the editor has changed the selection "
        self._updateSelection()
        return

    def _updateSelection( self ):
        " Updates the selection member "

        self._selection = None
        currentWidget = self.editorsManager.currentWidget()
        if currentWidget.getType() not in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return False
        if currentWidget.getEditor().hasSelectedText():
            line1, index1, line2, index2 = \
                currentWidget.getEditor().getSelection()
            if line1 != line2:
                self._selection = ( line1, index1, line2, index2 )
                return True
        return False

    def show( self, text = '' ):
        " Overridden show() method "
        self.__skip = True
        self.findtextCombo.clear()
        self.findtextCombo.addItems( self.findHistory )
        self.findtextCombo.setEditText( text )
        self.findtextCombo.lineEdit().selectAll()
        self.findtextCombo.setFocus()
        self.__skip = False
        self._onEditTextChanged( text )

        self.caseCheckBox.setChecked( False )
        self.wordCheckBox.setChecked( False )
        self.regexpCheckBox.setChecked( False )

        self._findBackward = False
        self._highlightOnly = True

        QWidget.show( self )
        self.activateWindow()
        return

    def _onEditTextChanged( self, text ):
        " Triggered when the search text has been changed "
        if self.__skip:
            return
        status = text != ""
        self.findNextButton.setEnabled( status )
        self.findPrevButton.setEnabled( status )

        currentWidget = self.editorsManager.currentWidget()
        if currentWidget.getType() not in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return
        editor = currentWidget.getEditor()


        # There are the following cases:
        # - start of the search with no text
        # - some text was replaced with nothing
        # - start of the search with some text
        # - some symbols have been changed

        if self._originEditor is None:
            # There were no started search before
            if text == "":
                # Start with no text - do nothing
                return

            # It is a start of a new search with some text
            # Memorize the current state
            self._originEditor = editor
            self._originPosition = editor.getCursorPosition()
            self._originFirstLine = editor.firstVisibleLine()

            self._matchTarget = editor.highlightMatch( text,
                                                       self._originPosition[ 0 ],
                                                       self._originPosition[ 1 ],
                                                       self.regexpCheckBox.isChecked(),
                                                       self.caseCheckBox.isChecked(),
                                                       self.wordCheckBox.isChecked() )
            if self._matchTarget != [-1, -1, -1]:
                # Scroll the editor if required
                editor.ensureLineVisible( self._matchTarget[ 0 ] )

        else:
            # This is continue of the started search
            if self._originEditor == editor:
                # This is still the same editor
                if text == "":
                    # Remove the highlight and scroll back
                    editor.clearAllIndicators( editor.searchIndicator )
                    editor.clearAllIndicators( editor.matchIndicator )
                    self._matchTarget = [-1, -1, -1]

                    editor.scrollVertical( self._originFirstLine - editor.firstVisibleLine() )
                    return

                # These are changes to what it was
                self._matchTarget = editor.highlightMatch( text,
                                                           self._originPosition[ 0 ],
                                                           self._originPosition[ 1 ],
                                                           self.regexpCheckBox.isChecked(),
                                                           self.caseCheckBox.isChecked(),
                                                           self.wordCheckBox.isChecked() )
                if self._matchTarget != [-1, -1, -1]:
                    # Scroll the editor if required
                    editor.ensureLineVisible( self._matchTarget[ 0 ] )
                else:
                    # Nothing is found, so scroll back to the original
                    editor.scrollVertical( self._originFirstLine - \
                                           editor.firstVisibleLine() )

            else:
                # The user switched to the other editor
                self._finalizeSearch()

                # Recursive call which will initiate a new search
                self._onEditTextChanged( self.findtextCombo.currentText() )

        return

    def _advanceMatchIndicator( self, newLine, newPos, newLength ):
        " Advances the current match indicator "

        if newLine == self._matchTarget[ 0 ] and \
           newPos == self._matchTarget[ 1 ] and \
           newLength == self._matchTarget[ 2 ]:
            # It is the same target - nothing to do
            return

        editor = self._originEditor

        # Replace the old highlight
        tgtPos = editor.positionFromLineIndex( self._matchTarget[ 0 ], self._matchTarget[ 1 ] )
        editor.clearIndicatorRange( editor.matchIndicator, tgtPos, self._matchTarget[ 2 ] )
        editor.setIndicatorRange( editor.searchIndicator, tgtPos, self._matchTarget[ 2 ] )

        # Memorise new target
        self._matchTarget = [newLine, newPos, newLength]

        # Update the new highlight
        tgtPos = editor.positionFromLineIndex( self._matchTarget[ 0 ], self._matchTarget[ 1 ] )
        editor.clearIndicatorRange( editor.searchIndicator, tgtPos, self._matchTarget[ 2 ] )
        editor.setIndicatorRange( editor.matchIndicator, tgtPos, self._matchTarget[ 2 ] )

        editor.ensureLineVisible( self._matchTarget[ 0 ] )

        if (not self.isVisible() or editor.hasFocus()) and not editor.hasSelectedText():
            self._originPosition = (self._matchTarget[ 0 ],
                                    self._matchTarget[ 1 ] )
            editor.setCursorPosition( self._matchTarget[ 0 ],
                                      self._matchTarget[ 1 ] )
        return


class FindWidget( FindReplaceBase ):
    """ Find in the current file widget """

    def __init__( self, editorsManager, parent = None ):

        FindReplaceBase.__init__( self, editorsManager, parent )

        self.horizontalLayout = QHBoxLayout( self )
        self.horizontalLayout.setMargin( 0 )

        self.horizontalLayout.addWidget( self.closeButton )
        self.horizontalLayout.addWidget( self.findLabel )
        self.horizontalLayout.addWidget( self.findtextCombo )
        self.horizontalLayout.addWidget( self.findPrevButton )
        self.horizontalLayout.addWidget( self.findNextButton )
        self.horizontalLayout.addWidget( self.caseCheckBox )
        self.horizontalLayout.addWidget( self.wordCheckBox )
        self.horizontalLayout.addWidget( self.regexpCheckBox )

        self.setTabOrder( self.findtextCombo, self.caseCheckBox )
        self.setTabOrder( self.caseCheckBox, self.wordCheckBox )
        self.setTabOrder( self.wordCheckBox, self.regexpCheckBox )
        self.setTabOrder( self.regexpCheckBox, self.findNextButton )
        self.setTabOrder( self.findNextButton, self.findPrevButton )
        self.setTabOrder( self.findPrevButton, self.closeButton )

        self.connect( self.findNextButton, SIGNAL( 'clicked()' ),
                      self.onNext )
        self.connect( self.findPrevButton, SIGNAL( 'clicked()' ),
                      self.onPrev )
        self.connect( self.findtextCombo.lineEdit(),
                      SIGNAL( "returnPressed()" ),
                      self.__findByReturnPressed )
        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def updateStatus( self ):
        " Triggered when the current tab is changed "
        FindReplaceBase.updateStatus( self )
        return

    def onNext( self ):
        " Triggered when the find next is clicked "
        if not self.onPrevNext():
            return

        self._findBackward = False
        if not self.__findNextPrev( self.findtextCombo.currentText() ):
            GlobalData().mainWindow.showStatusBarMessage( \
                    "The '" + self.findtextCombo.currentText() + \
                    "' was not found" )
        return

    def onPrev( self ):
        " Triggered when the find prev is clicked "
        if not self.onPrevNext():
            return

        self._findBackward = True
        if not self.__findNextPrev( self.findtextCombo.currentText() ):
            GlobalData().mainWindow.showStatusBarMessage( \
                    "The '" + self.findtextCombo.currentText() + \
                    "' was not found" )
        return

    def onPrevNext( self ):
        """ Checks prerequisites, saves the history and
            returns True if the search should be done """
        txt = self.findtextCombo.currentText()
        if txt == "":
            return False

        currentWidget = self.editorsManager.currentWidget()
        if currentWidget.getType() not in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return False

        return True

    def __findByReturnPressed( self ):
        " Triggered when 'Enter' or 'Return' is clicked "
        if self._findBackward:
            self.onPrev()
        else:
            self.onNext()
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "
        if what == CodimensionProject.CompleteProject:
            self.findHistory = QStringList( GlobalData().project.findHistory )
        return

    def __findNextPrev( self, txt ):
        " Finds the next occurrence of the search text "

        currentWidget = self.editorsManager.currentWidget()
        editor = currentWidget.getEditor()

        if editor == self._originEditor:
            # Still the same editor
            if not self._updateSelection():
                # In the whole document
                if self._matchTarget == [-1, -1, -1]:
                    return False        # Nothing is found
                if not self._findBackward:
                    # Search forward and we know for sure there is something
                    targets = editor.getTargets( txt,
                                                 self.regexpCheckBox.isChecked(),
                                                 self.caseCheckBox.isChecked(),
                                                 self.wordCheckBox.isChecked(),
                                                 self._matchTarget[ 0 ],
                                                 self._matchTarget[ 1 ] + self._matchTarget[ 2 ],
                                                 -1, -1 )
                    if len( targets ) == 0:
                        GlobalData().mainWindow.showStatusBarMessage( \
                                    "Reached the end of the document. " \
                                     "Searching from the beginning..." )
                        targets = editor.getTargets( txt,
                                                     self.regexpCheckBox.isChecked(),
                                                     self.caseCheckBox.isChecked(),
                                                     self.wordCheckBox.isChecked(),
                                                     0, 0,
                                                     self._matchTarget[ 0 ],
                                                     self._matchTarget[ 1 ] + self._matchTarget[ 2 ] )

                    # Take the very first target
                    self._advanceMatchIndicator( targets[ 0 ][ 0 ],
                                                 targets[ 0 ][ 1 ],
                                                 targets[ 0 ][ 2 ] )
                    return True
                else:
                    # Search backward
                    targets = editor.getTargets( txt,
                                                 self.regexpCheckBox.isChecked(),
                                                 self.caseCheckBox.isChecked(),
                                                 self.wordCheckBox.isChecked(),
                                                 0, 0,
                                                 self._matchTarget[ 0 ],
                                                 self._matchTarget[ 1 ] )
                    if len( targets ) == 0:
                        GlobalData().mainWindow.showStatusBarMessage( \
                                        "Reached the beginning of the document. " \
                                        "Searching from the end..." )
                        targets = editor.getTargets( txt,
                                                     self.regexpCheckBox.isChecked(),
                                                     self.caseCheckBox.isChecked(),
                                                     self.wordCheckBox.isChecked(),
                                                     self._matchTarget[ 0 ],
                                                     self._matchTarget[ 1 ],
                                                     -1, -1 )

                    # Take the last item
                    index = len( targets ) - 1
                    self._advanceMatchIndicator( targets[ index ][ 0 ],
                                                 targets[ index ][ 1 ],
                                                 targets[ index ][ 2 ] )
                    return True
            else:
                # Only in the selection
                if self._matchTarget == [-1, -1, -1]:
                    return False        # Nothing is found

                lineFrom, indexFrom, lineTo, indexTo = self._selection
                if not self._findBackward:
                    # Search forward
                    targets = editor.getTargets( txt,
                                                 self.regexpCheckBox.isChecked(),
                                                 self.caseCheckBox.isChecked(),
                                                 self.wordCheckBox.isChecked(),
                                                 self._matchTarget[ 0 ],
                                                 self._matchTarget[ 1 ] + self._matchTarget[ 2 ],
                                                 lineTo, indexTo )
                    if len( targets ) == 0:
                        GlobalData().mainWindow.showStatusBarMessage( \
                                        "Reached the end of the selection. " \
                                        "Searching from the beginning..." )
                        targets = editor.getTargets( txt,
                                                     self.regexpCheckBox.isChecked(),
                                                     self.caseCheckBox.isChecked(),
                                                     self.wordCheckBox.isChecked(),
                                                     lineFrom, indexFrom,
                                                     self._matchTarget[ 0 ],
                                                     self._matchTarget[ 1 ] + self._matchTarget[ 2 ] )

                    # Take the very first target
                    self._advanceMatchIndicator( targets[ 0 ][ 0 ],
                                                 targets[ 0 ][ 1 ],
                                                 targets[ 0 ][ 2 ] )
                    return True
                else:
                    # Search backward
                    targets = editor.getTargets( txt,
                                                 self.regexpCheckBox.isChecked(),
                                                 self.caseCheckBox.isChecked(),
                                                 self.wordCheckBox.isChecked(),
                                                 lineFrom, indexFrom,
                                                 self._matchTarget[ 0 ],
                                                 self._matchTarget[ 1 ] )
                    if len( targets ) == 0:
                        GlobalData().mainWindow.showStatusBarMessage( \
                                        "Reached the beginning of the selection. " \
                                        "Searching from the end..." )
                        targets = editor.getTargets( txt,
                                                     self.regexpCheckBox.isChecked(),
                                                     self.caseCheckBox.isChecked(),
                                                     self.wordCheckBox.isChecked(),
                                                     self._matchTarget[ 0 ],
                                                     self._matchTarget[ 1 ],
                                                     lineTo, indexTo )

                    # Take the last item
                    index = len( targets ) - 1
                    self._advanceMatchIndicator( targets[ index ][ 0 ],
                                                 targets[ index ][ 1 ],
                                                 targets[ index ][ 2 ] )
                    return True
        else:
            # Another editor
            self._finalizeSearch()

            # Call the textChanged() handler which will initiate a new search
            self._onEditTextChanged( txt )
            if self._matchTarget == [-1, -1, -1]:
                GlobalData().mainWindow.showStatusBarMessage( "The '" + txt + "' was not found" )

        return True



class ReplaceWidget( FindReplaceBase ):
    """ Find and replace in the current file widget """

    def __init__( self, editorsManager, parent = None ):

        FindReplaceBase.__init__( self, editorsManager, parent )
        prj = GlobalData().project
        self.findHistory = QStringList( prj.replaceWhatHistory )
        self.replaceHistory = QStringList( prj.replaceHistory )

        # Additional UI elements
        self.replaceLabel = QLabel( self )
        self.replaceLabel.setText( "Replace:" )

        self.replaceCombo = QComboBox( self )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                self.replaceCombo.sizePolicy().hasHeightForWidth() )
        self.replaceCombo.setSizePolicy( sizePolicy )
        self.replaceCombo.setEditable( True )
        self.replaceCombo.setInsertPolicy( QComboBox.InsertAtTop )
        self.replaceCombo.setAutoCompletion( False )
        self.replaceCombo.setDuplicatesEnabled( False )
        self.replaceCombo.setEnabled( False )

        self.replaceButton = QToolButton( self )
        self.replaceButton.setToolTip( "Replace current occurrence" )
        self.replaceButton.setIcon( PixmapCache().getIcon( "replace.png" ) )
        self.replaceButton.setEnabled( False )

        self.replaceAllButton = QToolButton( self )
        self.replaceAllButton.setToolTip( "Replace all occurrences" )
        self.replaceAllButton.setIcon( \
                PixmapCache().getIcon( "replaceall.png" ) )
        self.replaceAllButton.setEnabled( False )

        self.gridLayout = QGridLayout( self )
        self.gridLayout.setMargin( 0 )

        self.gridLayout.addWidget( self.closeButton, 0, 0, 1, 1 )
        self.gridLayout.addWidget( self.findLabel, 0, 1, 1, 1 )
        self.gridLayout.addWidget( self.findtextCombo, 0, 2, 1, 1 )
        self.gridLayout.addWidget( self.findPrevButton, 0, 3, 1, 1 )
        self.gridLayout.addWidget( self.findNextButton, 0, 4, 1, 1 )
        self.gridLayout.addWidget( self.caseCheckBox, 0, 5, 1, 1 )
        self.gridLayout.addWidget( self.wordCheckBox, 0, 6, 1, 1 )
        self.gridLayout.addWidget( self.regexpCheckBox, 0, 7, 1, 1 )

        self.gridLayout.addWidget( self.replaceLabel, 1, 1, 1, 1 )
        self.gridLayout.addWidget( self.replaceCombo, 1, 2, 1, 1 )
        self.gridLayout.addWidget( self.replaceButton, 1, 3, 1, 1 )
        self.gridLayout.addWidget( self.replaceAllButton, 1, 4, 1, 1 )


        self.setTabOrder( self.findtextCombo, self.replaceCombo )
        self.setTabOrder( self.replaceCombo, self.caseCheckBox )
        self.setTabOrder( self.caseCheckBox, self.wordCheckBox )
        self.setTabOrder( self.wordCheckBox, self.regexpCheckBox )
        self.setTabOrder( self.regexpCheckBox, self.findNextButton )
        self.setTabOrder( self.findNextButton, self.findPrevButton )
        self.setTabOrder( self.findPrevButton, self.replaceButton )
        self.setTabOrder( self.replaceButton, self.replaceAllButton )
        self.setTabOrder( self.replaceAllButton, self.closeButton )

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def updateStatus( self ):
        " Triggered when the current tab is changed "

        FindReplaceBase.updateStatus( self )

        currentWidget = self.editorsManager.currentWidget()
        status = currentWidget.getType() in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]
        self.replaceCombo.setEnabled( status )
        self.replaceButton.setEnabled( status )
        self.replaceAllButton.setEnabled( status )
        return

    def show( self, text = '' ):
        " Overridden show method "
        self.replaceCombo.clear()
        self.replaceCombo.addItems( self.replaceHistory )
        self.replaceCombo.setEditText( '' )

        FindReplaceBase.show( self, text )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "
        if what == CodimensionProject.CompleteProject:
            prj = GlobalData().project
            self.findHistory = QStringList( prj.replaceWhatHistory )
            self.replaceHistory = QStringList( prj.replaceHistory )
        return

