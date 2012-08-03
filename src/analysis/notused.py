#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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


""" not used globals, functions, classes analysis """


import os, os.path, logging
from PyQt4.QtCore                import Qt, SIGNAL, QTimer
from PyQt4.QtGui                 import QDialog, QDialogButtonBox, \
                                        QVBoxLayout, QLabel, \
                                        QProgressBar, QApplication, QCursor
from autocomplete.completelists  import getOccurrences
from utils.globals               import GlobalData
from ui.findinfiles              import ItemToSearchIn, getSearchItemIndex


class NotUsedAnalysisProgress( QDialog ):
    " Progress of the not used analysis "

    Functions = 0
    Classes   = 1
    Globals   = 2

    def __init__( self, what, sourceModel, parent = None ):
        QDialog.__init__( self, parent )

        if what not in [ self.Functions, self.Classes, self.Globals ]:
            raise Exception( "Unsupported not used analysis type: " + \
                             str( what ) )

        self.__cancelRequest = False
        self.__inProgress = False

        self.__what = what              # what is in source model
        self.__srcModel = sourceModel   # source model of globals or
                                        # functions or classes

        # Avoid pylint complains
        self.__progressBar = None
        self.__infoLabel = None
        self.__foundLabel = None
        self.__found = 0        # Number of found

        self.__createLayout()
        self.setWindowTitle( self.__formTitle() )
        QTimer.singleShot( 0, self.__process )
        return

    def __formTitle( self ):
        " Forms the progress dialog title "
        title = "Not used "
        if self.__what == self.Functions:
            title += 'functions'
        elif self.__what == self.Classes:
            title += 'classes'
        else:
            title += 'globlal variables'
        return title + " analysis"

    def __formInfoLabel( self, name ):
        " Forms the info label "
        if self.__what == self.Functions:
            return 'Function: ' + name
        if self.__what == self.Classes:
            return 'Class: ' + name
        return 'Globlal variable: ' + name

    def __whatAsString( self ):
        " Provides 'what' as string "
        if self.__what == self.Functions:
            return 'function'
        if self.__what == self.Classes:
            return 'class'
        return 'global variable'

    def __updateFoundLabel( self ):
        " Updates the found label "
        text = "Found: " + str( self.__found ) + " candidate"
        if self.__found != 1:
            text += "s"
        self.__foundLabel.setText( text )
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 450, 20 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )

        # Note label
        noteLabel = QLabel( "<b>Note</b>: the analysis is " \
                            "suggestive and not precise. " \
                            "Use the results with caution.\n", self )
        verticalLayout.addWidget( noteLabel )

        # Info label
        self.__infoLabel = QLabel( self )
        verticalLayout.addWidget( self.__infoLabel )

        # Progress bar
        self.__progressBar = QProgressBar( self )
        self.__progressBar.setValue( 0 )
        self.__progressBar.setOrientation( Qt.Horizontal )
        verticalLayout.addWidget( self.__progressBar )

        # Found label
        self.__foundLabel = QLabel( self )
        verticalLayout.addWidget( self.__foundLabel )

        # Buttons
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Close )
        verticalLayout.addWidget( buttonBox )

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.__onClose )
        return

    def __onClose( self ):
        " triggered when the close button is clicked "

        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()
        return

    def __process( self ):
        " Analysis process "

        self.__inProgress = True

        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        modified = editorsManager.getModifiedList( True ) # True - only project files
        if len( modified ) > 0:
            modNames = [ modItem[ 0 ] for modItem in modified ]
            label = "File"
            if len( modified ) >= 2:
                label += "s"
            label += ": "
            logging.warning( "The analisys is performed for the content of saved files. " \
                             "The unsaved modifications will not be taken into account. " \
                             + label + ", ".join( modNames ) )

        self.__updateFoundLabel()
        self.__progressBar.setRange( 0,
                                   len( self.__srcModel.rootItem.childItems ) )
        QApplication.processEvents()
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )

        count = 0
        candidates = []
        for treeItem in self.__srcModel.rootItem.childItems:
            if self.__cancelRequest:
                break

            name = str( treeItem.data( 0 ) ).split( '(' )[ 0 ]
            path = os.path.realpath( treeItem.getPath() )
            lineNumber = int( treeItem.data( 2 ) )
            absPosition = treeItem.sourceObj.absPosition

            count += 1
            self.__progressBar.setValue( count )
            self.__infoLabel.setText( self.__formInfoLabel( name ) )
            QApplication.processEvents()

            # Analyze the name
            found = False
            try:
                # True is for throwing exceptions
                locations = getOccurrences( path, absPosition, True )

                if len( locations ) == 1 and \
                   locations[ 0 ][ 1 ] == lineNumber:
                    found = True
                    index = getSearchItemIndex( candidates, path )
                    if index < 0:
                        widget = mainWindow.getWidgetForFileName( path )
                        if widget is None:
                            uuid = ""
                        else:
                            uuid = widget.getUUID()
                        newItem = ItemToSearchIn( path, uuid )
                        candidates.append( newItem )
                        index = len( candidates ) - 1
                    candidates[ index ].addMatch( name, lineNumber )

            except Exception, exc:
                # There is nothing interesting with exceptions here.
                # It seems to me that rope throws them in case if the same item
                # is declared multiple times in a file. I also suspect that
                # exceptions may come up in case of syntactic errors.
                # So I just suppress them.
                pass

                #logging.warning( "Error detected while analysing " + \
                #                 self.__whatAsString() + " '" + name + \
                #                 "'. Message: " + str( exc ) )

            if found:
                self.__found += 1
                self.__updateFoundLabel()
            QApplication.processEvents()

        if self.__found == 0:
            logging.info( "No not used candidates found" )
        else:
            mainWindow.displayFindInFiles( "", candidates )

        QApplication.restoreOverrideCursor()
        self.__infoLabel.setText( 'Done' )
        self.__inProgress = False

        self.accept()
        return

