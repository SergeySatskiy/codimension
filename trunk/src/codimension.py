#!/bin/env python
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

"""
codimension main Python script.
It performs necessery initialization and starts the Qt main loop.
"""

__version__ = "0.0.2"

import sys, os.path, traceback, logging
from PyQt4        import QtGui
from optparse     import OptionParser
from PyQt4.QtCore import SIGNAL, SLOT, QTimer

# Make it possible to import from the subdirectories
srcDir = os.path.dirname( os.path.abspath( sys.argv[0] ) )
if not srcDir in sys.path:
    sys.path.append( srcDir )

from utils.settings         import Settings
from utils.globals          import GlobalData
from ui.application         import CodimensionApplication
from ui.splashscreen        import SplashScreen
from utils.pixmapcache      import PixmapCache
from utils.project          import CodimensionProject


# Saving the root logging handlers
__rootLoggingHandlers = []


def codimensionMain():
    """ The codimension driver """


    # Parse command line arguments
    parser = OptionParser(
    """
    %prog [options] [project file | python files]
    Runs codimension UI
    """,
    version = "%prog " + __version__ )

    parser.add_option( "--no-debug",
                       action="store_false", dest="debug", default=True,
                       help="switch off debug and info messages (default: On)" )

    options, args = parser.parse_args()

    # Configure logging
    setupLogging( options.debug )

    # The default exception handler can be replaced
    sys.excepthook = exceptionHook

    # Create global data singleton.
    # It's unlikely to throw any exceptions.
    globalData = GlobalData()
    globalData.version = __version__

    # Create pixmap cache singleton
    pixmapCache = PixmapCache()

    # Create QT application
    codimensionApp = CodimensionApplication( sys.argv )
    globalData.application = codimensionApp

    logging.debug( "Starting codimension v." + __version__ )

    # Process command line arguments
    if not len( args ) in [ 0, 1 ]:
        logging.error( "Unexpected number of arguments." )
        parser.print_help()
        return 1

    projectFile = ""
    if len( args ) == 1:
        projectFile = args[ 0 ]
        if not os.path.exists( projectFile ):
            logging.error( "Cannot find specified project file: " + \
                           projectFile )
            return 1
        if not projectFile.endswith( '.cdm' ):
            logging.error( "Error loading project: codimension " \
                           "project must have .cdm extension" )
            return 1


    # Show splash screen
    splash = SplashScreen()
    globalData.splash = splash

    # Load settings
    splash.showMessage( "Loading settings..." )
    settings = Settings()

    screenSize = codimensionApp.desktop().screenGeometry()
    globalData.screenWidth = screenSize.width()
    globalData.screenHeight = screenSize.height()

    splash.showMessage( "Importing packages..." )
    from ui.mainwindow import CodimensionMainWindow

    splash.showMessage( "Generating main window..." )
    mainWindow = CodimensionMainWindow( splash, settings )
    globalData.mainWindow = mainWindow
    codimensionApp.connect( codimensionApp, SIGNAL( "lastWindowClosed()" ),
                            codimensionApp, SLOT( "quit()" ) )
    mainWindow.connect( globalData.project, SIGNAL( 'projectChanged' ),
                        mainWindow.onProjectChanged )

    # Loading project if given or the recent one
    if projectFile != "":
        splash.showMessage( "Loading project..." )
        globalData.project.loadProject( projectFile )
    elif settings.projectLoaded and len( settings.recentProjects ) > 0:
        splash.showMessage( " Loading recent project..." )
        if os.path.exists( settings.recentProjects[ -1 ] ):
            globalData.project.loadProject( settings.recentProjects[ -1 ] )
        else:
            logging.warning( "Cannot open the most recent project: " + \
                             settings.recentProjects[ -1 ] + \
                             ". Ignore and continue." )
            # Fake signal for triggering browsers layout
            globalData.project.emit( SIGNAL( 'projectChanged' ),
                                     CodimensionProject.CompleteProject )
    else:
        # Fake signal for triggering browsers layout
        globalData.project.emit( SIGNAL( 'projectChanged' ),
                                 CodimensionProject.CompleteProject )

    mainWindow.show()

    # Launch the user interface
    QTimer.singleShot( 0, launchUserInterface )

    # Run the application main cycle
    retVal = codimensionApp.exec_()
    return retVal


def launchUserInterface():
    """ UI launch pad """

    globalData = GlobalData()
    if not globalData.splash is None:
        globalData.splash.finish( globalData.mainWindow )
        splashScreen = globalData.splash
        globalData.splash = None
        del splashScreen

    # Additional checks may come here

    return


def setupLogging( debug ):
    """ Configures the logging module """

    global __rootLoggingHandlers

    if debug:
        logLevel = logging.DEBUG
    else:
        logLevel = logging.WARNING

    # Default output stream is stderr
    logging.basicConfig( level = logLevel,
                         format = "%(levelname) -10s %(asctime)s %(message)s" )

    # Memorize the root logging handlers
    __rootLoggingHandlers = logging.root.handlers
    return


def exceptionHook( excType, excValue, tracebackObj ):
    """ Catches unhandled exceptions """

    globalData = GlobalData()

    # Keyboard interrupt is a special case
    if issubclass( excType, KeyboardInterrupt ):
        if not globalData.application is None:
            globalData.application.quit()
        return

    filename, line, dummy, dummy = traceback.extract_tb( tracebackObj ).pop()
    filename = os.path.basename( filename )
    error    = "%s: %s" % ( excType.__name__, excValue )
    stackTraceString = "".join( traceback.format_exception( excType, excValue,
                                                            tracebackObj ) )

    # Write a message to a log file
    logging.error( "Unhandled exception is caught\n" + stackTraceString )

    # Display the message as a QT modal dialog box if the application
    # has started
    if not globalData.application is None:
        QtGui.QMessageBox.critical( None, "Error: " + error,
                                    "<html>Unhandled exception is caught." \
                                    "<pre>" + stackTraceString + "</pre>" \
                                    "</html>" )
        globalData.application.exit( 1 )
    return


if __name__ == '__main__':
    retCode = codimensionMain()

    # restore root logging handlers
    if len( __rootLoggingHandlers ) != 0:
        logging.root.handlers = __rootLoggingHandlers

    logging.debug( "Exiting codimension" )
    sys.exit( retCode )

