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


""" project line counter dialog """


import os, os.path
from PyQt4.QtCore       import Qt, SIGNAL, QTimer
from PyQt4.QtGui        import QDialog, QTextEdit, QDialogButtonBox, \
                               QVBoxLayout, QSizePolicy, \
                               QProgressBar, QApplication, QFontMetrics, \
                               QFont
from fitlabel           import FitPathLabel
from utils.linescounter import LinesCounter
from utils.globals      import GlobalData
from utils.misc         import splitThousands



class LineCounterDialog( QDialog, object ):
    """ line counter dialog implementation """

    def __init__( self, parent = None ):

        QDialog.__init__( self, parent )

        self.__cancelRequest = False
        self.__inProgress = False
        self.__createLayout()
        self.setWindowTitle( "Line counter" )
        self.show()
        QTimer.singleShot( 0, self.__process )
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 450, 220 )
        self.setSizeGripEnabled( True )

        self.verticalLayout = QVBoxLayout( self )

        # Info label
        self.infoLabel = FitPathLabel( self )
        #sizePolicy = QSizePolicy( QSizePolicy.Expanding,
        #                          QSizePolicy.Preferred )
        sizePolicy = QSizePolicy( QSizePolicy.Minimum,
                                  QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                    self.infoLabel.sizePolicy().hasHeightForWidth() )
        self.infoLabel.setSizePolicy( sizePolicy )
        self.verticalLayout.addWidget( self.infoLabel )

        # Progress bar
        self.progressBar = QProgressBar( self )
        self.progressBar.setValue( 0 )
        self.progressBar.setOrientation( Qt.Horizontal )
        self.verticalLayout.addWidget( self.progressBar )

        # Result window
        font = QFont( "Monospace", 12 )
        self.resultEdit = QTextEdit( self )
        self.resultEdit.setTabChangesFocus( False )
        self.resultEdit.setAcceptRichText( False )
        self.resultEdit.setReadOnly( True )
        self.resultEdit.setFont( font )

        # Calculate the vertical size
        fontMetrics = QFontMetrics( font )
        rect = fontMetrics.boundingRect( "W" )
        # 6 lines, 5 line spacings, 2 frames
        self.resultEdit.setMinimumHeight( rect.height() * 6 + 4 * 5 + \
                                          self.resultEdit.frameWidth() * 2 )
        self.verticalLayout.addWidget( self.resultEdit )

        # Buttons
        self.buttonBox = QDialogButtonBox( self )
        self.buttonBox.setOrientation( Qt.Horizontal )
        self.buttonBox.setStandardButtons( QDialogButtonBox.Close )
        self.verticalLayout.addWidget( self.buttonBox )

        self.connect( self.buttonBox, SIGNAL( "rejected()" ), self.__onClose )
        return

    def __onClose( self ):
        " triggered when the close button is clicked "

        self.__cancelRequest = True
        if not self.__inProgress:
            self.close()
        return

    def __process( self ):
        " Accumulation process "

        self.__inProgress = True
        files = GlobalData().project.filesList
        self.progressBar.setRange( 0, len( files ) )

        accumulator = LinesCounter()
        current = LinesCounter()

        index = 1
        for fileName in files:

            if self.__cancelRequest:
                self.__inProgress = False
                self.close()
                return

            self.infoLabel.setPath( 'Processing: ' + fileName )

            if (fileName.endswith( '.py' ) or fileName.endswith( '.py3' )) and \
               os.path.exists( fileName ):
                current.getLines( fileName )
                accumulator.files += current.files
                accumulator.filesSize += current.filesSize
                accumulator.codeLines += current.codeLines
                accumulator.emptyLines += current.emptyLines
                accumulator.commentLines += current.commentLines

            self.progressBar.setValue( index )
            index += 1

            QApplication.processEvents()

        self.infoLabel.setPath( 'Done' )
        self.__inProgress = False

        # Update text in the text window
        files = splitThousands( str( accumulator.files ) )
        filesSize = splitThousands( str( accumulator.filesSize ) )
        codeLines = splitThousands( str( accumulator.codeLines ) )
        emptyLines = splitThousands( str( accumulator.emptyLines ) )
        commentLines = splitThousands( str( accumulator.commentLines ) )
        totalLines = splitThousands( str( accumulator.codeLines +
                                          accumulator.emptyLines +
                                          accumulator.commentLines ) )
        self.resultEdit.setText( \
                "Python files in project: " + files + "\n" \
                "Total files size:        " + filesSize + " bytes\n" \
                "Code lines:              " + codeLines + "\n" \
                "Empty lines:             " + emptyLines + "\n" \
                "Comment lines:           " + commentLines + "\n" \
                "Total lines:             " + totalLines )
        return

