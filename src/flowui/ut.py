#!/bin/env python
#
# File:   ut.py
#
# Author: Sergey Satskiy, copyright (c) 2015
#
# Date:   May 15, 2015
#
# Permission to copy, use, modify, sell and distribute this software
# is granted provided this copyright notice appears in all copies.
# This software is provided "as is" without express or implied
# warranty, and with no claim as to its suitability for any purpose.
#


"""
Unit test for the control flow drawing
"""

import sys, os, os.path, tempfile
from PyQt4      import QtGui, QtCore
from optparse   import OptionParser
from subprocess import Popen, PIPE



def safeRun( commandArgs ):
    """ Runs the given command and reads the output """

    errTmp = tempfile.mkstemp()
    errStream = os.fdopen( errTmp[0] )
    process = Popen( commandArgs, stdin = PIPE,
                     stdout = PIPE, stderr = errStream )
    process.stdin.close()
    processStdout = process.stdout.read()
    process.stdout.close()
    errStream.seek( 0 )
    err = errStream.read()
    errStream.close()
    os.unlink( errTmp[1] )
    process.wait()
    if process.returncode != 0:
        raise Exception( "Error in '%s' invocation: %s" % \
                         (commandArgs[0], err) )
    return processStdout


def isPythonFile( fName ):
    try:
        output = safeRun( ['file', '-i', '-b', fName] )
        if 'text/x-python' not in output:
            return "The file " + fName + " is not a python one"
    except:
        return "Error running the 'file' utility for " + fName
    return None


def main():
    """ The CF graphics driver """

    parser = OptionParser(
    """
    %prog [options] [fileName]
    Unit test for the control flow drawing
    """ )

    parser.add_option( "-v", "--verbose",
                       action="store_true", dest="verbose", default=False,
                       help="be verbose (default: False)" )

    options, args = parser.parse_args()
    if not len( args ) in [ 0, 1 ]:
        sys.stdout = sys.stderr
        parser.print_help()
        return 1

    fName = None
    warning = None
    if len( args ) == 1:
        fName = os.path.abspath( args[0] )
        if not os.path.exists( fName ):
            warning = "Cannot find the specified file: " + args[0]
            fName = None
        else:
            warning = isPythonFile( args[0] )
            if warning is not None:
                fName = None

    # Run the QT application
    app = QtGui.QApplication( sys.argv )
    mainWindow = MainWindow( options.verbose, fName, warning )
    mainWindow.show()
    return app.exec_()



class CFGraphicsView( QtGui.QGraphicsView ):
    """ Central widget """

    def __init__( self, parent = None ):
        super( CFGraphicsView, self ).__init__( parent )
        self.setRenderHint( QtGui.QPainter.Antialiasing )
        self.setRenderHint( QtGui.QPainter.TextAntialiasing )
        return

    def wheelEvent( self, event ):
        """ Mouse wheel event """
        factor = 1.41 ** ( -event.delta() / 240.0 )
        self.scale( factor, factor )
        return

    def zoomIn( self ):
        """ Zoom when a button clicked """
        factor = 1.41 ** (120.0/240.0)
        self.scale( factor, factor )
        return

    def zoomOut( self ):
        """ Zoom when a button clicked """
        factor = 1.41 ** (-120.0/240.0)
        self.scale( factor, factor )
        return



class MainWindow( QtGui.QMainWindow ):
    """ Main application window """

    def createToolbar( self ):
        """
        There are the following buttons on the main window:
        open, reload, zoom out, zoom in, debug, clear log
        """

        openButton = QtGui.QAction( QtGui.QIcon( 'icons/open.png' ),
                                    'Open (Ctrl+O)', self )
        openButton.setShortcut( 'Ctrl+O' )
        openButton.setStatusTip( 'Open python file' )
        self.connect( openButton, QtCore.SIGNAL( 'triggered()' ),
                      self.openButtonClicked )

        reloadButton = QtGui.QAction( QtGui.QIcon( 'icons/reload.png' ),
                                      'Reload (F5)', self )
        reloadButton.setShortcut( 'F5' )
        reloadButton.setStatusTip( 'Reload python file' )
        self.connect( reloadButton, QtCore.SIGNAL( 'triggered()' ),
                      self.reloadButtonClicked )

        zoomoutButton = QtGui.QAction( QtGui.QIcon( 'icons/zoomOut.png' ),
                                       'Zoom Out (Ctrl+-)', self )
        zoomoutButton.setShortcut( 'Ctrl+-' )
        zoomoutButton.setStatusTip( 'Zoom Out' )
        self.connect( zoomoutButton, QtCore.SIGNAL( 'triggered()' ),
                      self.zoomOut )

        zoominButton = QtGui.QAction( QtGui.QIcon( 'icons/zoomIn.png' ),
                                      'Zoom In (Ctrl++)', self )
        zoominButton.setShortcut( 'Ctrl++' )
        zoominButton.setStatusTip( 'Zoom In' )
        self.connect( zoominButton, QtCore.SIGNAL( 'triggered()' ),
                      self.zoomIn )

        clearLogButton = QtGui.QAction( QtGui.QIcon( 'icons/clear.png' ),
                                        'Clear log (Ctrl+R)', self )
        clearLogButton.setShortcut( 'Ctrl+R' )
        clearLogButton.setStatusTip( 'Clear log' )
        self.connect( clearLogButton, QtCore.SIGNAL( 'triggered()' ),
                      self.clearButtonClicked )


        # A few separators
        separator = QtGui.QAction( self )
        separator.setSeparator( True )
        separator1 = QtGui.QAction( self )
        separator1.setSeparator( True )

        toolbar = self.addToolBar( 'Toolbar' )
        toolbar.setIconSize( QtCore.QSize( 48, 48 ) )
        toolbar.addAction( openButton )
        toolbar.addAction( reloadButton )
        toolbar.addAction( separator )
        toolbar.addAction( zoomoutButton )
        toolbar.addAction( zoominButton )
        toolbar.addAction( separator1 )
        toolbar.addAction( clearLogButton )
        return

    def createLogWindow( self ):
        """ Creates a dockable RO editor for logging """

        self.logWidget = QtGui.QTextEdit()
        self.logWidget.setReadOnly( True )
        self.logWidget.setFontFamily( "Courier" )
        self.logWidget.setFontPointSize( 12.0 )

        logDockWidget = QtGui.QDockWidget( "Log", self )
        logDockWidget.setObjectName( "LogDockWidget" )
        logDockWidget.setAllowedAreas( QtCore.Qt.BottomDockWidgetArea )
        logDockWidget.setWidget( self.logWidget )

        self.addDockWidget( QtCore.Qt.BottomDockWidgetArea, logDockWidget )
        return

    def zoomIn( self ):
        """ zoom in the main window """
        self.view.zoomIn()
        return

    def zoomOut( self ):
        """ zoom out the main window """
        self.view.zoomOut()
        return

    def reloadButtonClicked( self ):
        """ reload button has been clicked """
        return

    def clearButtonClicked( self ):
        """ Deletes all the messages from the log window """
        self.logWidget.clear()
        return

    def createGraphicsView( self ):
        """ Creates the central widget """

        self.scene = QtGui.QGraphicsScene( self )

        self.view = CFGraphicsView()
        self.view.setScene( self.scene )
        return


    def __init__( self, verbose, fName, warning ):
        QtGui.QMainWindow.__init__( self )

        self.logWidget = None
        self.view = None
        self.scene = None
        self.fName = fName

        self.resize( 800, 600 )

        self.updateWindowTitle()
        self.statusBar()
        self.createToolbar()
        self.createLogWindow()
        self.createGraphicsView()

        self.setCentralWidget( self.view )

        if warning:
            self.logMessage( warning )

        if fName:
            # To yeld the main message processing loop
            kickOffTimer = QtCore.QTimer()
            kickOffTimer.singleShot( 200, self.proceedWithFile )
        return

    def updateWindowTitle( self ):
        """ updates the main window title with the current so file """

        if self.fName:
            self.setWindowTitle( 'Control flow for: ' + self.fName )
        else:
            self.setWindowTitle( 'Control flow for: no file selected' )
        return

    def logMessage( self, message ):
        """ Makes a log message visible in the user interface """

        self.logWidget.append( message )
        self.logWidget.update()
        return

    def openButtonClicked( self ):
        """ Brings up an open dialogue """

        # By some unknown reasons the following simple way of getting a file is
        # not working:
        # fileName = QtGui.QFileDialog.getOpenFileName( self, 'Open file',
        #                                           QtCore.QDir.currentPath() )
        #
        # There is however a workaround. Here it is:
        dialog = QtGui.QFileDialog( self )
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return

        fileNames = dialog.selectedFiles()
        fileName = str( fileNames[0] )

        if not os.path.exists( fileName ):
            QtGui.QMessageBox.critical( self, 'Error',
                                        'The selected file (' + fileName +
                                        ') does not exist' )
            return

        # Check that the file is a python one
        warning = isPythonFile( fileName )
        if warning is not None:
            QtGui.QMessageBox.critical( self, 'Error', warning )
            return

        # set the new file name
        self.fName = fileName
        self.updateWindowTitle()

        # initiate the process
        self.proceedWithFile()
        return

    def proceedWithFile( self ):
        """ Taks the file from settings and processes it """

        # Get the Graph objects and draw them
        self.pathGateGraph,     \
        self.pathNoGateGraph,   \
        self.noPathNoGateGraph, \
        self.noPathGateGraph = buildGraphs( self.settings.soFileName, self )

        self.drawScene()
        return


    def drawScene( self ):
        """ Redraws the scene using the given graph object """

        self.scene.clear()

        graph = None
        if self.settings.showGateSO:
            if self.settings.showPath:
                graph = self.pathGateGraph
            else:
                graph = self.noPathGateGraph
        else:
            if self.settings.showPath:
                graph = self.pathNoGateGraph
            else:
                graph = self.noPathNoGateGraph

        self.scene.setSceneRect( 0, 0, graph.width, graph.height )

        for edge in graph.edges:
            self.scene.addItem( GraphicsEdge( edge, self ) )

        for node in graph.nodes:
            self.scene.addItem( GraphicsNode( node, self ) )

        return

# The script execution entry point
if __name__ == "__main__":
    returnCode = 0
    try:
        returnCode = main()
    except Exception, exc:
        print >> sys.stderr, str( exc )
        returnCode = 1
    except:
        print >> sys.stderr, "Unknown exception"
        returnCode = 2
    sys.exit( returnCode )

