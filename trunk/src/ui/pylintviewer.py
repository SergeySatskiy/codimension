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

" Pylint viewer implementation "

import os.path, logging
from PyQt4.QtCore import Qt, SIGNAL, QSize, QStringList
from PyQt4.QtGui import ( QColor, QToolBar, QHBoxLayout, QWidget, QAction,
                          QPalette, QVBoxLayout, QLabel, QScrollArea,
                          QSizePolicy, QFrame, QLayout, QTreeWidget,
                          QTreeWidgetItem, QHeaderView, QApplication )
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from itemdelegates import NoOutlineHeightDelegate



class ErrorTableItem( QTreeWidgetItem ):
    " Error table row derivation to allow integer sorting "

    def __init__( self, items, intColumn ):
        QTreeWidgetItem.__init__( self, items )
        self.__intColumn = intColumn
        return

    def __lt__( self, other ):
        " Integer or string custom sorting "
        sortColumn = self.treeWidget().sortColumn()
        if sortColumn == self.__intColumn:
            selfLine, selfPos = self.getLinePos( self.text( sortColumn ) )
            otherLine, otherPos = self.getLinePos( other.text( sortColumn ) )
            if selfLine < otherLine:
                return True
            if otherLine < selfLine:
                return False
            return selfPos < otherPos
        return self.text( sortColumn ) < other.text( sortColumn )

    @staticmethod
    def getLinePos( value ):
        " Returns line and pos to compare "
        value = str( value )
        if ":" in value:
            parts = value.split( ":" )
            return int( parts[ 0 ] ), int( parts[ 1 ] )
        return int( value ), 0




class PylintViewer( QWidget ):
    " Pylint tab widget "

    # Limits to colorize the final score
    BadLimit = 8.5
    GoodLimit = 9.5

    # Options of providing a report
    SingleFile     = 0
    DirectoryFiles = 1
    ProjectFiles   = 2
    SingleBuffer   = 3

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__reportUUID = ""
        self.__reportFileName = ""
        self.__reportOption = -1
        self.__reportShown = False
        self.__report = None

        self.__widgets = []

        # Prepare members for reuse
        if GlobalData().pylintAvailable:
            self.__noneLabel = QLabel( "\nNo results available" )
        else:
            self.__noneLabel = QLabel( "\nPylint is not available" )
        self.__noneLabel.setAutoFillBackground( True )
        noneLabelPalette = self.__noneLabel.palette()
        noneLabelPalette.setColor( QPalette.Background,
                                   GlobalData().skin.nolexerPaper )
        self.__noneLabel.setPalette( noneLabelPalette )

        self.__noneLabel.setFrameShape( QFrame.StyledPanel )
        self.__noneLabel.setAlignment( Qt.AlignHCenter )
        self.__headerFont = self.__noneLabel.font()
        self.__headerFont.setPointSize( self.__headerFont.pointSize() + 4 )
        self.__noneLabel.setFont( self.__headerFont )

        self.__createLayout( parent )

        self.__updateButtonsStatus()
        self.resizeEvent()
        return

    def __createLayout( self, parent ):
        " Creates the toolbar and layout "

        # Buttons
        self.printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                                    'Print', self )
        #printButton.setShortcut( 'Ctrl+' )
        self.connect( self.printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )
        self.printButton.setVisible( False )

        self.printPreviewButton = QAction(
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        #printPreviewButton.setShortcut( 'Ctrl+' )
        self.connect( self.printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )
        self.printPreviewButton.setVisible( False )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.clearButton = QAction(
            PixmapCache().getIcon( 'trash.png' ),
            'Clear', self )
        self.connect( self.clearButton, SIGNAL( 'triggered()' ),
                      self.__clear )

        # The toolbar
        self.toolbar = QToolBar( self )
        self.toolbar.setOrientation( Qt.Vertical )
        self.toolbar.setMovable( False )
        self.toolbar.setAllowedAreas( Qt.RightToolBarArea )
        self.toolbar.setIconSize( QSize( 16, 16 ) )
        self.toolbar.setFixedWidth( 28 )
        self.toolbar.setContentsMargins( 0, 0, 0, 0 )

        self.toolbar.addAction( self.printPreviewButton )
        self.toolbar.addAction( self.printButton )
        self.toolbar.addWidget( spacer )
        self.toolbar.addAction( self.clearButton )

        self.__vLayout = QVBoxLayout()
        self.__vLayout.setContentsMargins( 5, 5, 5, 5 )
        self.__vLayout.setSpacing( 0 )
        self.__vLayout.setSizeConstraint( QLayout.SetFixedSize )

        self.__bodyFrame = QFrame( self )
#        self.__bodyFrame.setFrameShape( QFrame.StyledPanel )
        self.__bodyFrame.setFrameShape( QFrame.NoFrame )

#        self.__bodyFrame.setSizePolicy( QSizePolicy.Maximum,
#                                        QSizePolicy.Expanding )
        self.__bodyFrame.setLayout( self.__vLayout )
        self.bodyWidget = QScrollArea( self )
        self.bodyWidget.setFocusPolicy( Qt.NoFocus )
        self.bodyWidget.setWidget( self.__bodyFrame )
        self.bodyWidget.hide()

        self.__hLayout = QHBoxLayout()
        self.__hLayout.setContentsMargins( 0, 0, 0, 0 )
        self.__hLayout.setSpacing( 0 )
        self.__hLayout.addWidget( self.toolbar )
        self.__hLayout.addWidget( self.__noneLabel )
        self.__hLayout.addWidget( self.bodyWidget )

        self.setLayout( self.__hLayout )
        return

    def __updateButtonsStatus( self ):
        " Updates the buttons status "
        self.printButton.setEnabled( self.__reportShown )
        self.printPreviewButton.setEnabled( self.__reportShown )
        self.clearButton.setEnabled( self.__reportShown )
        return

    def __onPrint( self ):
        " Triggered when the print button is pressed "
        pass

    def __onPrintPreview( self ):
        " triggered when the print preview button is pressed "
        pass

    def setFocus( self ):
        " Overridden setFocus "
        self.__vLayout.setFocus()
        return

    def __clear( self ):
        " Clears the content of the vertical layout "
        if not self.__reportShown:
            return

        self.__removeAll()
        self.bodyWidget.hide()
        self.__noneLabel.show()

        self.__report = None
        self.__reportShown = False
        self.__updateButtonsStatus()
        self.resizeEvent()

        self.__updateTooltip()
        return

    def __removeAll( self ):
        " Removes all the items from the report "
        for item in self.__widgets:
            item.hide()
            self.__vLayout.removeWidget( item )
            del item

        self.__widgets = []
        return

    def __createScoreLabel( self, score, previousScore,
                            showFileName, fileName ):
        " Creates the score label "

        txt = "Score: " + str( score )
        if previousScore != "":
            txt += " / Previous score: " + str( previousScore )
        if not showFileName:
            txt += " for " + os.path.basename( fileName )

        scoreLabel = QLabel( txt )
        scoreLabel.setFrameShape( QFrame.StyledPanel )
        scoreLabel.setFont( self.__headerFont )
        scoreLabel.setAutoFillBackground( True )
        palette = scoreLabel.palette()

        if score < self.BadLimit:
            palette.setColor( QPalette.Background, QColor( 255, 127, 127 ) )
            palette.setColor( QPalette.Foreground, QColor( 0, 0, 0 ) )
        elif score > self.GoodLimit:
            palette.setColor( QPalette.Background, QColor( 220, 255, 220 ) )
            palette.setColor( QPalette.Foreground, QColor( 0, 0, 0 ) )
        else:
            palette.setColor( QPalette.Background, QColor( 255, 255, 127 ) )
            palette.setColor( QPalette.Foreground, QColor( 0, 0, 0 ) )

        scoreLabel.setPalette( palette )
        return scoreLabel

    @staticmethod
    def __setTableHeight( table ):
        " Auxiliary function to set the table height "

        # Height - it is ugly and approximate however I am tired of
        # calculating the proper height. Why is this so hard, huh?
        lastRowHeight = table.itemDelegate().lastHeight
        height = lastRowHeight * ( table.topLevelItemCount() + 1 ) + 10
        table.setFixedHeight( height )
        return

    @staticmethod
    def __shouldShowFileName( messages ):
        " Decides if the file name column should be supressed "
        if len( messages ) == 0:
            return False
        firstName = messages[ 0 ].fileName
        for index in range( 1, len( messages ) ):
            if firstName != messages[ index ].fileName:
                return True
        return False

    def __addErrorsTable( self, messages, showFileName ):
        " Creates the messages table "

        errTable = QTreeWidget( self.bodyWidget )
        errTable.setAlternatingRowColors( True )
        errTable.setRootIsDecorated( False )
        errTable.setItemsExpandable( False )
        errTable.setSortingEnabled( True )
        errTable.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        errTable.setUniformRowHeights( True )
        self.connect( errTable,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__errorActivated )

        headerLabels = QStringList() << "File name" << "Line" \
                                     << "Message ID" << "Object" << "Message"
        errTable.setHeaderLabels( headerLabels )

        for item in messages:
            if item.position is None:
                lineNumber = str( item.lineNumber )
            else:
                lineNumber = str( item.lineNumber ) + ":" + str( item.position )
            values = QStringList() << item.fileName \
                                   << item.lineNumber << item.messageID \
                                   << item.objectName << item.message
            errTable.addTopLevelItem( ErrorTableItem( values, 1 ) )

        # Hide the file name column if required
        if not showFileName:
            errTable.setColumnHidden( 0, True )

        # Resizing
        errTable.header().resizeSections( QHeaderView.ResizeToContents )
        errTable.header().setStretchLastSection( True )

        # Sort indicator
        if showFileName:
            sortIndex = 0   # By file names
        else:
            sortIndex = 1   # By line number because this is from the same file
        errTable.header().setSortIndicator( sortIndex, Qt.AscendingOrder )
        errTable.sortItems( sortIndex, errTable.header().sortIndicatorOrder() )

        # Height
        self.__setTableHeight( errTable )

        self.__vLayout.addWidget( errTable )
        self.__widgets.append( errTable )
        return

    def __addSimilarity( self, similarity, titleText ):
        " Adds a similarity "

        # Label
        title = QLabel( titleText )
        title.setFont( self.__headerFont )

        self.__vLayout.addWidget( title )
        self.__widgets.append( title )

        # List of files
        simTable = QTreeWidget( self.bodyWidget )
        simTable.setAlternatingRowColors( True )
        simTable.setRootIsDecorated( False )
        simTable.setItemsExpandable( False )
        simTable.setSortingEnabled( False )
        simTable.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        simTable.setUniformRowHeights( True )
        self.connect( simTable,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__similarityActivated )

        headerLabels = QStringList() << "File name" << "Line"
        simTable.setHeaderLabels( headerLabels )

        for item in similarity.files:
            values = QStringList() << item[ 0 ] << str( item[ 1 ] )
            simTable.addTopLevelItem( QTreeWidgetItem( values )  )

        # Resizing
        simTable.header().resizeSections( QHeaderView.ResizeToContents )
        simTable.header().setStretchLastSection( True )

        # Height
        self.__setTableHeight( simTable )

        self.__vLayout.addWidget( simTable )
        self.__widgets.append( simTable )

        # The fragment itself
        if len( similarity.fragment ) > 10:
            # Take first 9 lines
            text = "\n".join( similarity.fragment[ : 9 ] ) + "\n ..."
            toolTip = "\n".join( similarity.fragment )
        else:
            text = "\n".join( similarity.fragment )
            toolTip = ""
        fragmentLabel = QLabel( "<pre>" + self.__htmlEncode( text ) + "</pre>" )
        if toolTip != "":
            fragmentLabel.setToolTip( "<pre>" + self.__htmlEncode( toolTip ) +
                                      "</pre>" )
        palette = fragmentLabel.palette()
        palette.setColor( QPalette.Background, QColor( 250, 250, 175 ) )
        palette.setColor( QPalette.Foreground, QColor( 0, 0, 0 ) )
        fragmentLabel.setPalette( palette )
        fragmentLabel.setFrameShape( QFrame.StyledPanel )
        fragmentLabel.setAutoFillBackground( True )

        labelFont = fragmentLabel.font()
        labelFont.setFamily( GlobalData().skin.baseMonoFontFace )
        fragmentLabel.setFont( labelFont )

        self.__vLayout.addWidget( fragmentLabel )
        self.__widgets.append( fragmentLabel )
        return

    @staticmethod
    def __htmlEncode( string ):
        " Encodes HTML "
        return string.replace( "&", "&amp;" ) \
                     .replace( ">", "&gt;" ) \
                     .replace( "<", "&lt;" )

    def __addSectionSpacer( self ):
        " Adds a fixed height spacer to the VBox layout "
        spacer = QWidget()
        spacer.setFixedHeight( 10 )
        self.__vLayout.addWidget( spacer )
        self.__widgets.append( spacer )
        return

    def __addGenericTable( self, table ):
        " Adds a generic table to the report "

        theTable = QTreeWidget( self.bodyWidget )
        theTable.setAlternatingRowColors( True )
        theTable.setRootIsDecorated( False )
        theTable.setItemsExpandable( False )
        theTable.setSortingEnabled( False )
        theTable.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        theTable.setUniformRowHeights( True )

        headerLabels = QStringList()
        for index in range( 0, len( table.header ) ):
            headerLabels << table.header[ index ]
        theTable.setHeaderLabels( headerLabels )

        for item in table.body:
            row = QStringList()
            for index in range( 0, len( table.header ) ):
                row << item[ index ]
            theTable.addTopLevelItem( QTreeWidgetItem( row ) )

        theTable.setFocusPolicy( Qt.NoFocus )

        # Resizing
        theTable.header().resizeSections( QHeaderView.ResizeToContents )
        theTable.header().setStretchLastSection( True )

        # Height
        self.__setTableHeight( theTable )

        self.__vLayout.addWidget( theTable )
        self.__widgets.append( theTable )
        return

    def __addGenericTableTitle( self, table ):
        " Adds a generic table title "
        tableTitle = QLabel( table.title )
        tableTitle.setFont( self.__headerFont )

        self.__vLayout.addWidget( tableTitle )
        self.__widgets.append( tableTitle )
        return

    def __updateTooltip( self ):
        " Generates a signal with appropriate string message "
        if not self.__reportShown:
            tooltip = "No results available"
        elif self.__reportOption == self.DirectoryFiles:
            tooltip = "Report generated for directory: " + \
                      self.__reportFileName
        elif self.__reportOption == self.ProjectFiles:
            tooltip = "Report generated for the whole project"
        elif self.__reportOption == self.SingleFile:
            tooltip = "Report generated for file: " + self.__reportFileName
        elif self.__reportOption == self.SingleBuffer:
            tooltip = "Report generated for unsaved file: " + \
                      self.__reportFileName
        else:
            tooltip = ""
        self.emit( SIGNAL( 'updatePylintTooltip' ), tooltip )
        return

    def showReport( self, lint, reportOption, fileName, uuid ):
        " Shows the pylint results "
        self.__removeAll()
        self.__noneLabel.hide()

        self.__report = lint
        self.__reportUUID = uuid
        self.__reportFileName = fileName
        self.__reportOption = reportOption

        showFileName = self.__shouldShowFileName( lint.errorMessages )

        scoreLabel = self.__createScoreLabel( lint.score, lint.previousScore,
                                              showFileName, fileName )
        self.__vLayout.addWidget( scoreLabel )
        self.__widgets.append( scoreLabel )

        if len( lint.errorMessages ) > 0:
            self.__addSectionSpacer()
            self.__addErrorsTable( lint.errorMessages, showFileName )

        index = 0
        for similarity in lint.similarities:
            self.__addSectionSpacer()
            self.__addSimilarity( similarity, "Similarity #" + str( index ) )
            index += 1

        for table in lint.tables:
            self.__addSectionSpacer()
            self.__addGenericTableTitle( table )
            self.__addGenericTable( table )

        self.bodyWidget.show()
        self.bodyWidget.ensureVisible( 0, 0, 0, 0 )
        self.__reportShown = True
        self.__updateButtonsStatus()
        self.__updateTooltip()

        # It helps, but why do I have flickering?
        QApplication.processEvents()
        self.__resizeBodyFrame()
        return

    def __errorActivated( self, item, column ):
        " Handles the double click (or Enter) on the item "

        linePos = str( item.text( 1 ) )
        if ":" in linePos:
            parts = linePos.split( ":" )
            lineNumber = int( parts[ 0 ] )
            pos = int( parts[ 1 ] )
        else:
            lineNumber = int( linePos )
            pos = 0

        if self.__reportOption in [ self.SingleFile, self.DirectoryFiles,
                                    self.ProjectFiles ]:
            fileName = str( item.text( 0 ) )
        else:
            # SingleBuffer
            if self.__reportFileName != "":
                if os.path.isabs( self.__reportFileName ):
                    fileName = self.__reportFileName
                else:
                    # Could be unsaved buffer, so try to search by the
                    mainWindow = GlobalData().mainWindow
                    widget = mainWindow.getWidgetByUUID( self.__reportUUID )
                    if widget is None:
                        logging.error( "The unsaved buffer has been closed" )
                        return
                    # The widget was found, so jump to the required
                    editor = widget.getEditor()
                    editor.gotoLine( lineNumber, pos )
                    editor.setFocus()
                    return

        GlobalData().mainWindow.openFile( fileName, lineNumber )
        return

    def __resizeBodyFrame( self ):
        " Resizing the frame to occupy all available width "
        size = self.bodyWidget.maximumViewportSize()
        self.__bodyFrame.setMinimumWidth( size.width() - 16 )
        self.__bodyFrame.setMinimumHeight( size.height() )
        return

    def showEvent( self, showEv = None ):
        " Called when the widget is shown "
        self.__resizeBodyFrame()
        return

    def resizeEvent( self, resizeEv = None ):
        " Called when the main window gets resized "
        self.__resizeBodyFrame()
        return

    def onFileUpdated( self, fileName, uuid ):
        " Called when a buffer is saved or saved as "

        if not self.__reportShown:
            return
        if self.__reportUUID != uuid:
            return

        # Currently shown report is for the saved buffer
        # File name is expected being absolute
        self.__reportFileName = fileName
        self.emit( SIGNAL( 'updatePylintTooltip' ),
                   "Report generated for buffer saved as " + fileName )
        return

    def __similarityActivated( self, item, column ):
        " Triggered when a similarity is activated "
        fileName = str( item.text( 0 ) )
        lineNumber = int( item.text( 1 ) )
        GlobalData().mainWindow.openFile( fileName, lineNumber )
        return

