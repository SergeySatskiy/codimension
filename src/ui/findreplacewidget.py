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
                                       QGridLayout, QWidget, QCheckBox
from utils.pixmapcache          import PixmapCache
from PyQt4.QtCore               import SIGNAL, Qt, QStringList
from mainwindowtabwidgetbase    import MainWindowTabWidgetBase
from utils.globals              import GlobalData
from utils.project              import CodimensionProject



class SearchAttr:
    " Stores search attributes for a single editor "

    def __init__( self ):
        self.line = -1
        self.pos = -1
        self.firstLine = -1
        self.match = [ -1, -1, -1 ]     # line, pos, length
        return


class SearchSupport:
    " Auxiliary class to support incremental search "

    def __init__( self ):
        self.editorSearchAttributes = {}
        return

    def add( self, uuid, searchAttr ):
        " Adds new editor search attributes "
        self.editorSearchAttributes[ uuid ] = searchAttr
        return

    def hasEditor( self, uuid ):
        " Checks if there was a search in the editor "
        return self.editorSearchAttributes.has_key( uuid )

    def get( self, uuid ):
        " Provides the search attributes "
        return self.editorSearchAttributes[ uuid ]

    def delete( self, uuid ):
        " Deletes the editor attributes from the storage "
        if self.hasEditor( uuid ):
            del self.editorSearchAttributes[ uuid ]
        return

    def clearStartPositions( self ):
        " Cleans up the memorised start positions "
        for key in self.editorSearchAttributes:
            attributes = self.editorSearchAttributes[ key ]
            attributes.line = -1
            attributes.pos = -1
            self.editorSearchAttributes[ key ] = attributes
        return


class FindReplaceBase( QWidget ):
    """ Base class for both find and replace widgets """

    maxHistory = 16

    def __init__( self, editorsManager, parent = None ):

        QWidget.__init__( self, parent )
        self.editorsManager = editorsManager
        self.findHistory = QStringList( GlobalData().project.findHistory )
        self._findBackward = False
        self._selection = None
        self.__skip = True

        # Incremental search support
        self._searchSupport = SearchSupport()
        self.connect( editorsManager, SIGNAL( "tabClosed" ),
                      self.__onTabClosed )

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
        self.connect( self.caseCheckBox, SIGNAL( 'stateChanged(int)' ),
                      self._onCheckBoxChange )

        self.wordCheckBox = QCheckBox( self )
        self.wordCheckBox.setText( "Whole word" )
        self.wordCheckBox.setFocusPolicy( Qt.NoFocus )
        self.wordCheckBox.setEnabled( False )
        self.connect( self.wordCheckBox, SIGNAL( 'stateChanged(int)' ),
                      self._onCheckBoxChange )

        self.regexpCheckBox = QCheckBox( self )
        self.regexpCheckBox.setText( "Regexp" )
        self.regexpCheckBox.setFocusPolicy( Qt.NoFocus )
        self.regexpCheckBox.setEnabled( False )
        self.connect( self.regexpCheckBox, SIGNAL( 'stateChanged(int)' ),
                      self._onCheckBoxChange )
        return

    def keyPressEvent( self, event ):
        " Handles the ESC key for the search bar "
        if event.key() == Qt.Key_Escape:
            self._searchSupport.clearStartPositions()
            event.accept()
            self.hide()
            activeWindow = self.editorsManager.currentWidget()
            if activeWindow:
                activeWindow.setFocus()
        return

    def __onTabClosed( self, uuid ):
        " Triggered when a tab is closed "
        self._searchSupport.delete( uuid )
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

        textAvailable = self.findtextCombo.currentText() != ""
        self.findPrevButton.setEnabled( status and textAvailable )
        self.findNextButton.setEnabled( status and textAvailable )

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
        self.caseCheckBox.setChecked( False )
        self.wordCheckBox.setChecked( False )
        self.regexpCheckBox.setChecked( False )
        self._findBackward = False
        self.__skip = False

        QWidget.show( self )
        self.activateWindow()

        self._performSearch( True )
        return

    def _onCheckBoxChange( self, newState ):
        " Triggered when a search check box state is changed "
        if self.__skip:
            return
        self._performSearch( False )
        return

    def _onEditTextChanged( self, text ):
        " Triggered when the search text has been changed "
        if self.__skip:
            return
        self._performSearch( False )
        return


    def _performSearch( self, fromScratch ):
        " Performs the incremental search "

        currentWidget = self.editorsManager.currentWidget()
        if currentWidget.getType() not in \
                    [ MainWindowTabWidgetBase.PlainTextEditor ]:
            return

        # Memorize the search arguments
        text = self.findtextCombo.currentText()
        isRegexp = self.regexpCheckBox.isChecked()
        isCase = self.caseCheckBox.isChecked()
        isWord = self.wordCheckBox.isChecked()


        status = text != ""
        self.findNextButton.setEnabled( status )
        self.findPrevButton.setEnabled( status )

        editor = currentWidget.getEditor()
        editorUUID = currentWidget.getUUID()

        if not fromScratch:
            # We've been searching here already
            searchAattributes = self._searchSupport.get( editorUUID )

            if text == "":
                # Remove the highlight and scroll back
                editor.clearAllIndicators( editor.searchIndicator )
                editor.clearAllIndicators( editor.matchIndicator )

                editor.setCursorPosition( searchAattributes.line,
                                          searchAattributes.pos )
                editor.ensureLineVisible( searchAattributes.firstLine )
                searchAattributes.match = [ -1, -1, -1 ]
                return

            matchTarget = editor.highlightMatch( text, searchAattributes.line,
                                                       searchAattributes.pos,
                                                 isRegexp, isCase, isWord )
            searchAattributes.match = matchTarget
            if matchTarget != [-1, -1, -1]:
                # Move the cursor to the match
                editor.setCursorPosition( matchTarget[ 0 ],
                                          matchTarget[ 1 ] )
                editor.ensureLineVisible( matchTarget[ 0 ] )
            else:
                # Nothing is found, so scroll back to the original
                editor.setCursorPosition( searchAattributes.line,
                                          searchAattributes.pos )
                editor.ensureLineVisible( searchAattributes.firstLine )

            return

        # Brand new editor to search in
        searchAattributes = SearchAttr()
        searchAattributes.line = currentWidget.getLine()
        searchAattributes.pos = currentWidget.getPos()
        searchAattributes.firstLine = editor.firstVisibleLine()

        if text == "":
            searchAattributes.match = [ -1, -1, -1 ]
            self._searchSupport.add( editorUUID, searchAattributes )
            return

        matchTarget = editor.highlightMatch( text, searchAattributes.line,
                                                   searchAattributes.pos,
                                             isRegexp, isCase, isWord )
        searchAattributes.match = matchTarget
        self._searchSupport.add( editorUUID, searchAattributes )

        if matchTarget != [-1, -1, -1]:
            # Move the cursor to the match
            editor.setCursorPosition( matchTarget[ 0 ],
                                      matchTarget[ 1 ] )
            editor.ensureLineVisible( matchTarget[ 0 ] )

        return


    def _advanceMatchIndicator( self, uuid, newLine, newPos, newLength ):
        " Advances the current match indicator for the given editor "

        if not self._searchSupport.hasEditor( uuid ):
            return

        searchAattributes = self._searchSupport.get( uuid )
        match = searchAattributes.match

        if newLine == match[ 0 ] and newPos == match[ 1 ] and \
           newLength == match[ 2 ]:
            # It is the same target - nothing to do
            return

        widget = self.editorsManager.getWidgetByUUID( uuid )
        if widget is None:
            return
        editor = widget.getEditor()

        # Replace the old highlight
        tgtPos = editor.positionFromLineIndex( match[ 0 ], match[ 1 ] )
        editor.clearIndicatorRange( editor.matchIndicator, tgtPos, match[ 2 ] )
        editor.setIndicatorRange( editor.searchIndicator, tgtPos, match[ 2 ] )

        # Memorise new target
        searchAattributes.match = [ newLine, newPos, newLength ]
        self._searchSupport.add( uuid, searchAattributes )

        # Update the new highlight
        tgtPos = editor.positionFromLineIndex( newLine, newPos )
        editor.clearIndicatorRange( editor.searchIndicator, tgtPos, newLength )
        editor.setIndicatorRange( editor.matchIndicator, tgtPos, newLength )

        # Move the cursor to the new match
        editor.setCursorPosition( newLine, newPos )
        editor.ensureLineVisible( newLine )
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
        if not self.__findNextPrev():
            GlobalData().mainWindow.showStatusBarMessage( \
                    "The '" + self.findtextCombo.currentText() + \
                    "' was not found" )
        return

    def onPrev( self ):
        " Triggered when the find prev is clicked "
        if not self.onPrevNext():
            return

        self._findBackward = True
        if not self.__findNextPrev():
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

    def __findNextPrev( self ):
        " Finds the next occurrence of the search text "

        currentWidget = self.editorsManager.currentWidget()
        editor = currentWidget.getEditor()
        editorUUID = currentWidget.getUUID()

        # Memorize the search arguments
        text = self.findtextCombo.currentText()
        isRegexp = self.regexpCheckBox.isChecked()
        isCase = self.caseCheckBox.isChecked()
        isWord = self.wordCheckBox.isChecked()

        # Identify the search start point
        startLine = currentWidget.getLine()
        startPos = currentWidget.getPos()

        if self._searchSupport.hasEditor( editorUUID ):
            searchAattributes = self._searchSupport.get( editorUUID )
            if startLine == searchAattributes.match[ 0 ] and \
               startPos == searchAattributes.match[ 1 ]:
                # The cursor is on the current match, i.e. the user did not
                # put the focus into the editor and did not move it
                if not self._findBackward:
                    startPos = startPos + searchAattributes.match[ 2 ]

            else:
                # The cursor is not at the same position as the last match,
                # i.e. the user moved it some way
                # Update the search attributes as if a new search is started
                searchAattributes.line = startLine
                searchAattributes.pos = startPos
                searchAattributes.firstLine = editor.firstVisibleLine()
                searchAattributes.match = [ -1, -1, -1 ]
                self._searchSupport.add( editorUUID, searchAattributes )

        else:
            # There were no search in this editor
            searchAattributes = SearchAttr()
            searchAattributes.line = startLine
            searchAattributes.pos = startPos
            searchAattributes.firstLine = editor.firstVisibleLine()
            searchAattributes.match = [ -1, -1, -1 ]
            self._searchSupport.add( editorUUID, searchAattributes )


        # Here: start point has been identified
        if not self._findBackward:
            # Search forward
            editor.highlightMatch( text, startLine, startPos,
                                   isRegexp, isCase, isWord, False, False )
            targets = editor.getTargets( text, isRegexp, isCase, isWord,
                                         startLine, startPos, -1, -1 )
            if len( targets ) == 0:
                GlobalData().mainWindow.showStatusBarMessage( \
                        "Reached the end of the document. " \
                        "Searching from the beginning..." )
                targets = editor.getTargets( text, isRegexp, isCase, isWord,
                                             0, 0, startLine, startPos )
                if len( targets ) == 0:
                    searchAattributes = self._searchSupport.get( editorUUID )
                    searchAattributes.match = [ -1, -1, -1 ]
                    self._searchSupport.add( editorUUID, searchAattributes )
                    return False    # Nothing has matched

            # Move the highlight and the cursor to the new match and
            # memorize a new match
            self._advanceMatchIndicator( editorUUID, targets[ 0 ][ 0 ],
                                                     targets[ 0 ][ 1 ],
                                                     targets[ 0 ][ 2 ] )
            return True

        # Search backward
        editor.highlightMatch( text, startLine, startPos,
                               isRegexp, isCase, isWord, False, False )
        targets = editor.getTargets( text, isRegexp, isCase, isWord,
                                     0, 0, startLine, startPos )
        if len( targets ) == 0:
            GlobalData().mainWindow.showStatusBarMessage( \
                    "Reached the beginning of the document. " \
                    "Searching from the end..." )
            targets = editor.getTargets( text, isRegexp, isCase, isWord,
                                         startLine, startPos, -1, -1 )
            if len( targets ) == 0:
                searchAattributes = self._searchSupport.get( editorUUID )
                searchAattributes.match = [ -1, -1, -1 ]
                self._searchSupport.add( editorUUID, searchAattributes )
                return False    # Nothing has matched

        # Move the highlight and the cursor to the new match and
        # memorize a new match
        index = len( targets ) - 1
        self._advanceMatchIndicator( editorUUID, targets[ index ][ 0 ],
                                                 targets[ index ][ 1 ],
                                                 targets[ index ][ 2 ] )
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

