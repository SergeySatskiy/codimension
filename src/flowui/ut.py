#!/usr/bin/env python
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

import sys, os, os.path, tempfile, datetime
from PyQt4      import QtGui, QtCore
from optparse   import OptionParser
from subprocess import Popen, PIPE
from cdmcf      import getControlFlowFromFile, VERSION
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication

import vcanvas
import cflowsettings


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
    if not fName.endswith( ".py" ):
        try:
            output = safeRun( ['file', '-i', '-b', fName] )
            if 'text/x-python' not in output:
                return "The file " + fName + " is not a python one"
        except:
            return "Error running the 'file' utility for " + fName
    return None


def formatFlow( s ):
    " Reformats the control flow output "
    result = ""
    shifts = []     # positions of opening '<'
    pos = 0         # symbol position in a line
    nextIsList = False

    def IsNextList( index, maxIndex, buf ):
        if index == maxIndex:
            return False
        if buf[ index + 1 ] == '<':
            return True
        if index < maxIndex - 1:
            if buf[ index + 1 ] == '\n' and buf[ index + 2 ] == '<':
                return True
        return False

    maxIndex = len( s ) - 1
    for index in xrange( len( s ) ):
        sym = s[ index ]
        if sym == "\n":
            lastShift = shifts[ -1 ]
            result += sym + lastShift * " "
            pos = lastShift
            if index < maxIndex:
                if s[ index + 1 ] not in "<>":
                    result += " "
                    pos += 1
            continue
        if sym == "<":
            if nextIsList == False:
                shifts.append( pos )
            else:
                nextIsList = False
            pos += 1
            result += sym
            continue
        if sym == ">":
            shift = shifts[ -1 ]
            result += '\n'
            result += shift * " "
            pos = shift
            result += sym
            pos += 1
            if IsNextList( index, maxIndex, s ):
                nextIsList = True
            else:
                del shifts[ -1 ]
                nextIsList = False
            continue
        result += sym
        pos += 1
    return result


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
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            factor = 1.41 ** ( -event.delta() / 240.0 )
            self.scale( factor, factor )
        else:
            QtGui.QGraphicsView.wheelEvent( self, event )
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
        self.proceedWithFile()
        return

    def clearButtonClicked( self ):
        """ Deletes all the messages from the log window """
        self.logWidget.clear()
        return

    def createGraphicsView( self ):
        """ Creates the central widget """

        self.scene = QtGui.QGraphicsScene( self )

        self.view = CFGraphicsView( self )
        self.view.setScene( self.scene )
        return


    def __init__( self, verbose, fName, warning ):
        QtGui.QMainWindow.__init__( self )

        self.logWidget = None
        self.view = None
        self.scene = None
        self.fName = fName
        self.verbose = verbose
        self.cf = None

        self.resize( 1400, 800 )

        self.updateWindowTitle()
        self.statusBar()
        self.createToolbar()
        self.createLogWindow()
        self.createGraphicsView()

        self.setCentralWidget( self.view )

        if verbose:
            self.logMessage( "Using cdmcf version " + VERSION )

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
        timestamp = datetime.datetime.now().strftime( '%m-%d-%y %H:%M:%S.%f' )
        self.logWidget.append( timestamp + " " + message )
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

    def proceedWithFile( self, needToParse = True ):
        """ Taks the file from settings and processes it """

        if needToParse:
            if self.verbose:
                self.logMessage( "Parsing file " + self.fName )
            self.cf = getControlFlowFromFile( self.fName )
            if self.verbose:
                self.logMessage( "Parsed file:" )
                self.logMessage( formatFlow( str( self.cf ) ) )

            if len( self.cf.errors ) != 0:
                self.logMessage( "No drawing due to parsing errors" )
                return

            if len( self.cf.warnings ) != 0:
                self.logMessage( "Parser warnings: " )
                for warn in self.cf.warnings:
                    self.logMessage( str( warn[0] ) + ": " + warn[1] )
        else:
            if self.cf is None:
                self.logMessage( "No control flow object" )
                return
            if len( self.cf.errors ) != 0:
                self.logMessage( "No drawing due to parsing errors" )
                return

        self.scene.clear()

        if self.verbose:
            self.logMessage( "Layouting ..." )
        try:
            # To pick up possibly changed settings
            reload( cflowsettings )
            cflowSettings = cflowsettings.getDefaultCflowSettings( self )

            # Top level canvas has no adress and no parent canvas
            canvas = vcanvas.VirtualCanvas( cflowSettings, None, None, None )
            canvas.layout( self.cf )
            if self.verbose:
                self.logMessage( "Layout is done:" )
                self.logMessage( str( canvas ) )
                self.logMessage( "Rendering ..." )

            width, height = canvas.render()
            if self.verbose:
                self.logMessage( "Rendering is done. Scene size: " +
                                 str( width ) + "x" + str( height ) +
                                 ". Drawing ..." )

            self.scene.setSceneRect( 0, 0, width, height )
            canvas.draw( self.scene, 0, 0 )
        except Exception, exc:
            self.logMessage( "Exception:\n" + str( exc ) )
            raise

        if self.verbose:
            self.logMessage( "Drawing is done." )
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

