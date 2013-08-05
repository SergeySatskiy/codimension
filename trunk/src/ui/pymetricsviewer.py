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

" Pymetrics viewer implementation "

import os.path, logging
from PyQt4.QtCore                       import Qt, SIGNAL, QSize, \
                                               QStringList
from PyQt4.QtGui                        import QToolBar, \
                                               QHBoxLayout, QWidget, QAction, \
                                               QSizePolicy, QLabel, \
                                               QSizePolicy, QFrame, \
                                               QTreeWidget, QApplication, \
                                               QTreeWidgetItem, QHeaderView
from utils.pixmapcache                  import PixmapCache
from utils.globals                      import GlobalData
from itemdelegates                      import NoOutlineHeightDelegate
from pymetricsparser.pymetricsparser    import BasicMetrics
from cdmbriefparser                     import getBriefModuleInfoFromFile, \
                                               getBriefModuleInfoFromMemory
from utils.misc                         import splitThousands


class McCabeTableItem( QTreeWidgetItem ):
    " McCabe complexity table row "

    def __init__( self, items ):
        QTreeWidgetItem.__init__( self, items )
        self.__intColumn = items.count() - 1

        complexityValue = int( items[ self.__intColumn ] )
        if complexityValue > PymetricsViewer.HighRiskLimit:
            self.setIcon( 0, PixmapCache().getIcon( 'highriskcmpx.png' ) )
            self.setToolTip( 0, 'Untestable, very high risk' )
        elif complexityValue > PymetricsViewer.ModerateRiskLimit:
            self.setIcon( 0, PixmapCache().getIcon( 'moderateriskcmpx.png' ) )
            self.setToolTip( 0, 'Moderate risk' )
        elif complexityValue > PymetricsViewer.LittleRiskLimit:
            self.setIcon( 0, PixmapCache().getIcon( 'littleriskcmpx.png' ) )
            self.setToolTip( 0, 'Little risk' )
        else:
            self.setIcon( 0, PixmapCache().getIcon( 'noriskcmpx.png' ) )
            self.setToolTip( 0, 'No risk' )
        return

    def __lt__( self, other ):
        " Integer or string custom sorting "
        sortColumn = self.treeWidget().sortColumn()
        if sortColumn == self.__intColumn:
            return int( self.text( sortColumn ) ) < \
                   int( other.text( sortColumn ) )
        return self.text( sortColumn ) < other.text( sortColumn )



class PymetricsViewer( QWidget ):
    " Pymetrics tab widget "

    # Limits to colorize the McCabe score
    LittleRiskLimit = 10
    ModerateRiskLimit = 20
    HighRiskLimit = 50

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

        # Prepare members for reuse
        self.__noneLabel = QLabel( "\nNo results available" )

        self.__noneLabel.setFrameShape( QFrame.StyledPanel )
        self.__noneLabel.setAlignment( Qt.AlignHCenter )
        self.__headerFont = self.__noneLabel.font()
        self.__headerFont.setPointSize( self.__headerFont.pointSize() + 4 )
        self.__noneLabel.setFont( self.__headerFont )

        self.__createLayout( parent )

        self.__updateButtonsStatus()
        return

    def __createLayout( self, parent ):
        " Creates the toolbar and layout "

        # Buttons
        self.__mcCabeButton = QAction( PixmapCache().getIcon( 'tableview.png' ),
                                       'Switch to McCabe only table view',
                                       self )
        self.__mcCabeButton.setCheckable( True )
        self.connect( self.__mcCabeButton, SIGNAL( 'toggled(bool)' ),
                      self.__onMcCabe )

        self.printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                                    'Print', self )
        #printButton.setShortcut( 'Ctrl+' )
        self.connect( self.printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )
        self.printButton.setVisible( False )

        self.printPreviewButton = QAction( \
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        #printPreviewButton.setShortcut( 'Ctrl+' )
        self.connect( self.printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )
        self.printPreviewButton.setVisible( False )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.clearButton = QAction( \
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

        self.toolbar.addAction( self.__mcCabeButton )
        self.toolbar.addAction( self.printPreviewButton )
        self.toolbar.addAction( self.printButton )
        self.toolbar.addWidget( spacer )
        self.toolbar.addAction( self.clearButton )

        self.__totalResultsTree = QTreeWidget()
        self.__totalResultsTree.setAlternatingRowColors( True )
        self.__totalResultsTree.setRootIsDecorated( True )
        self.__totalResultsTree.setItemsExpandable( True )
        self.__totalResultsTree.setUniformRowHeights( True )
        self.__totalResultsTree.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        headerLabels = QStringList() << "Path / name" << "Value" << ""
        self.__totalResultsTree.setHeaderLabels( headerLabels )
        self.connect( self.__totalResultsTree,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__allItemActivated )
        self.connect( self.__totalResultsTree,
                      SIGNAL( "itemExpanded(QTreeWidgetItem *)" ),
                      self.__onResultsExpanded )
        self.__totalResultsTree.setColumnHidden( 2, True )
        self.__totalResultsTree.hide()

        self.__mcCabeTable = QTreeWidget()
        self.__mcCabeTable.setAlternatingRowColors( True )
        self.__mcCabeTable.setRootIsDecorated( False )
        self.__mcCabeTable.setItemsExpandable( False )
        self.__mcCabeTable.setSortingEnabled( True )
        self.__mcCabeTable.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__mcCabeTable.setUniformRowHeights( True )
        headerLabels = QStringList() << "" << "File name" << "Object" \
                                     << "McCabe Complexity"
        self.__mcCabeTable.setHeaderLabels( headerLabels )
        self.connect( self.__mcCabeTable,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__mcCabeActivated )
        self.__mcCabeTable.hide()

        self.__hLayout = QHBoxLayout()
        self.__hLayout.setContentsMargins( 0, 0, 0, 0 )
        self.__hLayout.setSpacing( 0 )
        self.__hLayout.addWidget( self.toolbar )
        self.__hLayout.addWidget( self.__noneLabel )
        self.__hLayout.addWidget( self.__totalResultsTree )
        self.__hLayout.addWidget( self.__mcCabeTable )

        self.setLayout( self.__hLayout )
        return

    def getTotalResultsWidget( self ):
        " Provides a reference to the total results widget "
        return self.__totalResultsTree

    def getMcCabeResultsWidget( self ):
        " Provides a reference to the McCabe results widget "
        return self.__mcCabeTable

    def __updateButtonsStatus( self ):
        " Updates the buttons status "
        self.__mcCabeButton.setEnabled( self.__reportShown )
        self.printButton.setEnabled( self.__reportShown )
        self.printPreviewButton.setEnabled( self.__reportShown )
        self.clearButton.setEnabled( self.__reportShown )
        return

    def __onResultsExpanded( self, item ):
        " An item has been expanded, so the column width should be adjusted "
        self.__totalResultsTree.header().resizeSections( \
                                            QHeaderView.ResizeToContents )
        return

    def __onPrint( self ):
        " Triggered when the print button is pressed "
        pass

    def __onPrintPreview( self ):
        " triggered when the print preview button is pressed "
        pass

    def __onMcCabe( self, state ):
        " Triggered when the metrics view is switched "

        if not self.__reportShown:
            return

        if state:
            self.__totalResultsTree.hide()
            self.__mcCabeTable.show()
            self.__mcCabeButton.setIcon( \
                            PixmapCache().getIcon( 'treeview.png' ) )
            self.__mcCabeButton.setToolTip( "Switch to complete " \
                                            "results tree view" )
        else:
            self.__mcCabeTable.hide()
            self.__totalResultsTree.show()
            self.__mcCabeButton.setIcon( \
                            PixmapCache().getIcon( 'tableview.png' ) )
            self.__mcCabeButton.setToolTip( "Switch to McCabe only table view" )
        return

    def setFocus( self ):
        " Overridden setFocus "
        self.__hLayout.setFocus()
        return

    def __clear( self ):
        " Clears the content of the vertical layout "
        if not self.__reportShown:
            return

        self.__totalResultsTree.clear()
        self.__totalResultsTree.hide()
        self.__mcCabeTable.clear()
        self.__mcCabeTable.hide()
        self.__noneLabel.show()

        self.__report = None
        self.__reportShown = False
        self.__updateButtonsStatus()
#        self.resizeEvent()
        self.__mcCabeButton.setIcon( PixmapCache().getIcon( 'tableview.png' ) )
        self.__mcCabeButton.setToolTip( "Switch to McCabe only table view" )
        self.__mcCabeButton.setChecked( False )

        self.__updateTooltip()
        return

    def __updateTooltip( self ):
        " Generates a signal with appropriate string message "
        if not self.__reportShown:
            tooltip = "No metrics available"
        elif self.__reportOption == self.DirectoryFiles:
            tooltip = "Metrics generated for directory: " + \
                      self.__reportFileName
        elif self.__reportOption == self.ProjectFiles:
            tooltip = "Metrics generated for the whole project"
        elif self.__reportOption == self.SingleFile:
            tooltip = "Metrics generated for file: " + self.__reportFileName
        elif self.__reportOption == self.SingleBuffer:
            tooltip = "Metrics generated for unsaved file: " + \
                      self.__reportFileName
        else:
            tooltip = ""
        self.emit( SIGNAL( 'updatePymetricsTooltip' ), tooltip )
        return

    @staticmethod
    def __shouldShowFileName( table, column ):
        " Checks if the file name is the same "

        size = table.topLevelItemCount()
        if size == 0:
            return False

        index = size - 1
        firstName = table.topLevelItem( index ).text( column )
        index -= 1
        while index >= 0:
            if table.topLevelItem( index ).text( column ) != firstName:
                return True
            index -= 1
        return False

    def showReport( self, metrics, reportOption, fileName, uuid ):
        " Shows the pymetrics results "
        self.__clear()
        self.__noneLabel.hide()

        self.__report = metrics
        self.__reportUUID = uuid
        self.__reportFileName = fileName
        self.__reportOption = reportOption

        if len( metrics.report ) > 1:
            accumulatedBasic = self.__accumulateBasicMetrics()
            accItem = QTreeWidgetItem( QStringList() << "Cumulative basic metrics" )
            self.__totalResultsTree.addTopLevelItem( accItem )
            for key in accumulatedBasic:
                bmItem = QStringList() \
                            << BasicMetrics.metricsOfInterest[ key ] \
                            << splitThousands( str( accumulatedBasic[ key ] ) )
                basicMetric = QTreeWidgetItem( bmItem )
                accItem.addChild( basicMetric )

        # Add the complete information
        for fileName in metrics.report:
            if reportOption == self.SingleBuffer:
                fileItem = QTreeWidgetItem( QStringList() << "Editor buffer" )
            else:
                fileItem = QTreeWidgetItem( QStringList() << fileName )
                if GlobalData().project.isProjectFile( fileName ):
                    infoSrc = GlobalData().project.briefModinfoCache
                else:
                    infoSrc = GlobalData().briefModinfoCache
                info = infoSrc.get( fileName )
                if info.docstring is not None:
                    fileItem.setToolTip( 0, info.docstring.text )
                else:
                    fileItem.setToolTip( 0, "" )
            self.__totalResultsTree.addTopLevelItem( fileItem )

            # Messages part
            messages = metrics.report[ fileName ].messages
            if len( messages ) > 0:
                messagesItem = QTreeWidgetItem( QStringList() << "Messages" )
                fileItem.addChild( messagesItem )
                for message in messages:
                    mItem = QStringList() << message << "" << "E"
                    messagesItem.addChild( QTreeWidgetItem( mItem ) )

            # Basic metrics part
            basicItem = QTreeWidgetItem( QStringList() << "Basic metrics" )
            fileItem.addChild( basicItem )
            basic = metrics.report[ fileName ].basicMetrics
            for key in basic.metrics:
                bmItem = QStringList() \
                            << BasicMetrics.metricsOfInterest[ key ] \
                            << str( basic.metrics[ key ] )
                basicMetric = QTreeWidgetItem( bmItem )
                basicItem.addChild( basicMetric )

            # McCabe part
            mccabeItem = QTreeWidgetItem( QStringList() << "McCabe metrics" )
            fileItem.addChild( mccabeItem )
            mccabe = metrics.report[ fileName ].mcCabeMetrics.metrics
            for objName in mccabe:
                objItem = QStringList() << objName \
                                        << str( mccabe[ objName ] ) << "M"
                mccabeMetric = QTreeWidgetItem( objItem )
                mccabeItem.addChild( mccabeMetric )


            # COCOMO 2 part
            cocomo = QStringList() \
                     << "COCOMO 2" \
                     << str( metrics.report[ fileName ].cocomo2Metrics.value )
            cocomoItem = QTreeWidgetItem( cocomo )
            fileItem.addChild( cocomoItem )



        # Resizing the table
        self.__totalResultsTree.header().resizeSections( \
                                            QHeaderView.ResizeToContents )


        # Add McCabe complexity information
        for fileName in metrics.report:
            mccabe = metrics.report[ fileName ].mcCabeMetrics.metrics
            for objName in mccabe:
                values = QStringList() << "" << fileName << objName \
                                       << str( mccabe[ objName ] )
                self.__mcCabeTable.addTopLevelItem( McCabeTableItem( values ) )

        if not self.__shouldShowFileName( self.__mcCabeTable, 1 ):
            self.__mcCabeTable.setColumnHidden( 1, True )

        # Resizing and sorting the table
        self.__mcCabeTable.header().setSortIndicator( 3, Qt.DescendingOrder )
        self.__mcCabeTable.sortItems( 3,
                          self.__mcCabeTable.header().sortIndicatorOrder() )
        self.__mcCabeTable.header().resizeSections( \
                          QHeaderView.ResizeToContents )

        # Show the complete information
        self.__mcCabeTable.hide()
        self.__totalResultsTree.show()

        self.__reportShown = True
        self.__updateButtonsStatus()
        self.__updateTooltip()

        # It helps, but why do I have flickering?
        QApplication.processEvents()
        return

    def __accumulateBasicMetrics( self ):
        " Accumulates basic metrics for all the processed files "
        basic = {}
        for fileName in self.__report.report:
            singleBasic = self.__report.report[ fileName ].basicMetrics.metrics
            for key in singleBasic:
                if not key.startswith( 'num' ):
                    continue
                if key in basic:
                    basic[ key ] += int( singleBasic[ key ] )
                else:
                    basic[ key ] = int( singleBasic[ key ] )
        return basic

    def __mcCabeActivated( self, item, column ):
        " Handles the double click (or Enter) on the mccabe table item "

        objName = str( item.text( 2 ) )
        if self.__reportOption == self.SingleBuffer:
            if os.path.isabs( self.__reportFileName ):
                fileName = self.__reportFileName
            else:
                fileName = ""
        else:
            fileName = str( item.text( 1 ) )
        self.__onMcCabeObject( objName, fileName )
        return

    def __allItemActivated( self, item, column ):
        " Handles the double click (or Enter) in the total results tree "

        # We process only the error messages and McCabe items
        hiddenColumnText = str( item.text( 2 ) )
        if not hiddenColumnText in [ "M", "E" ]:
            return

        fileName = self.__getTreeItemFileName( item )
        lineNumber = 0
        if hiddenColumnText == "M":
            # This is McCabe item
            objName = str( item.text( 0 ) )
            self.__onMcCabeObject( objName, fileName )
            return
        elif hiddenColumnText == "E":
            # This is an error message
            message = str( item.text( 0 ) )
            pos = message.find( "at line" )
            if pos == -1:
                logging.error( "Unknown format of the message. " \
                               "Please inform the developers." )
                return
            parts = message[ pos: ].split()
            try:
                lineNumber = int( parts[ 2 ].replace( ',', '' ) )
            except:
                logging.error( "Unknown format of the message. " \
                               "Please inform the developers." )
                return

            if fileName == "":
                # This is an unsaved buffer, try to find the editor by UUID
                mainWindow = GlobalData().mainWindow
                widget = mainWindow.getWidgetByUUID( self.__reportUUID )
                if widget is None:
                    logging.error( "The unsaved buffer has been closed" )
                    return
                # The widget was found, so jump to the required
                editor = widget.getEditor()
                editor.gotoLine( lineNumber )
                editor.setFocus()
                return

        GlobalData().mainWindow.openFile( fileName, lineNumber )
        return

    def __getTreeItemFileName( self, item ):
        " Identifies the tree view item file name "
        if self.__reportOption == self.SingleBuffer:
            if os.path.isabs( self.__reportFileName ):
                return self.__reportFileName
            return ""

        # The file name is always two levels up
        fileItem = item.parent().parent()
        return str( fileItem.text( 0 ) )

    def __onMcCabeObject( self, objName, fileName ):
        " Called when the user activated McCabe item "

        info = None

        mainWindow = GlobalData().mainWindow
        widget = mainWindow.getWidgetByUUID( self.__reportUUID )
        if widget is None:
            if fileName == "":
                logging.error( "The unsaved buffer has been closed" )
                return
            # No widget, but we know the file name
            info = getBriefModuleInfoFromFile( fileName )
        else:
            # The widget was found
            editor = widget.getEditor()
            # The editor content has been modified, so re-parse the buffer
            info = getBriefModuleInfoFromMemory( str( editor.text() ) )

        parts = objName.split( '.' )
        currentIndex = 0
        functionsContainer = info.functions
        classesContainer = info.classes
        line = -1

        if objName == "__main__" and len( parts ) == 1:
            # Special case - global file scope
            line = 1
            currentIndex = 1

        while currentIndex < len( parts ):
            found = False
            for func in functionsContainer:
                if func.name == parts[ currentIndex ]:
                    if currentIndex == len( parts ) - 1:
                        # Found, jump to the line
                        line = func.line
                        break
                    functionsContainer = func.functions
                    classesContainer = func.classes
                    found = True
                    break
            if line != -1:
                break
            if found:
                currentIndex += 1
                continue
            for klass in classesContainer:
                if klass.name == parts[ currentIndex ]:
                    if currentIndex == len( parts ) - 1:
                        # Found, jump to the line
                        line = klass.line
                        break
                    functionsContainer = klass.functions
                    classesContainer = klass.classes
                    found = True
            if line != -1:
                break
            if found:
                currentIndex += 1
                continue

            # Not found
            logging.error( "Cannot find the " + objName )
            return

        # Here we have the line number
        if widget is None:
            GlobalData().mainWindow.openFile( fileName, line )
        else:
            editor = widget.getEditor()
            editor.gotoLine( line )
            editor.setFocus()
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
        self.emit( SIGNAL( 'updatePymetricsTooltip' ),
                   "Metrics generated for buffer saved as " + fileName )
        return

