#!/usr/bin/env python
#
# File:   ut.py
#
# Author: Sergey Satskiy, copyright (c) 2015-2016
#
# Date:   May 15, 2015
#
# Permission to copy, use, modify, sell and distribute this software
# is granted provided this copyright notice appears in all copies.
# This software is provided "as is" without express or implied
# warranty, and with no claim as to its suitability for any purpose.
#

"""Unit test for the control flow drawing"""


import sys
import os
import os.path
import tempfile
import datetime
import importlib
from optparse import OptionParser
from subprocess import Popen, PIPE
from cdmcfparser import getControlFlowFromFile, VERSION
from ui.qt import (Qt, QApplication, QGraphicsView, QMainWindow, QAction,
                   QTextEdit, QDockWidget, QGraphicsScene, QPainter, QTimer,
                   QIcon, QSize, QFileDialog, QDialog, QMessageBox)
from items import CellElement
import vcanvas
import cflowsettings


DEBUG = None

def safeRun(commandArgs):
    """Runs the given command and reads the output"""
    errTmp = tempfile.mkstemp()
    errStream = os.fdopen(errTmp[0])
    process = Popen(commandArgs, stdin=PIPE,
                    stdout=PIPE, stderr=errStream)
    process.stdin.close()
    processStdout = process.stdout.read()
    process.stdout.close()
    errStream.seek(0)
    err = errStream.read()
    errStream.close()
    os.unlink(errTmp[1])
    process.wait()
    if process.returncode != 0:
        raise Exception("Error in '%s' invocation: %s" %
                        (commandArgs[0], err))
    return processStdout


def isPythonFile(fName):
    """Checks if it is a python file"""
    if not fName.endswith(".py"):
        try:
            output = safeRun(['file', '-i', '-b', fName])
            if 'text/x-python' not in output:
                return "The file " + fName + " is not a python one"
        except:
            return "Error running the 'file' utility for " + fName
    return None


def formatFlow(src):
    """Reformats the control flow output"""
    result = ""
    shifts = []     # positions of opening '<'
    pos = 0         # symbol position in a line
    nextIsList = False

    def isNextList(index, maxIndex, buf):
        """True if it is a next list"""
        if index == maxIndex:
            return False
        if buf[index + 1] == '<':
            return True
        if index < maxIndex - 1:
            if buf[index + 1] == '\n' and buf[index + 2] == '<':
                return True
        return False

    maxIndex = len(src) - 1
    for index in range(len(src)):
        sym = src[index]
        if sym == "\n":
            lastShift = shifts[-1]
            result += sym + lastShift * " "
            pos = lastShift
            if index < maxIndex:
                if src[index + 1] not in "<>":
                    result += " "
                    pos += 1
            continue
        if sym == "<":
            if not nextIsList:
                shifts.append(pos)
            else:
                nextIsList = False
            pos += 1
            result += sym
            continue
        if sym == ">":
            shift = shifts[-1]
            result += '\n'
            result += shift * " "
            pos = shift
            result += sym
            pos += 1
            if isNextList(index, maxIndex, src):
                nextIsList = True
            else:
                del shifts[-1]
                nextIsList = False
            continue
        result += sym
        pos += 1
    return result


def main():
    """The CF graphics driver"""
    parser = OptionParser("""
    %prog [options] [fileName]
    Unit test for the control flow drawing
    """)

    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="be verbose (default: False)")
    parser.add_option("-g", "--debug",
                      action="store_true", dest="debug", default=None,
                      help="show debug (default: None)")

    options, args = parser.parse_args()
    if not len(args) in [0, 1]:
        sys.stdout = sys.stderr
        parser.print_help()
        return 1

    fName = None
    warning = None
    if len(args) == 1:
        fName = os.path.abspath(args[0])
        if not os.path.exists(fName):
            warning = "Cannot find the specified file: " + args[0]
            fName = None
        else:
            warning = isPythonFile(args[0])
            if warning is not None:
                fName = None

    if options.debug:
        global DEBUG
        DEBUG = True

    # Run the QT application
    app = QApplication(sys.argv)
    mainWindow = MainWindow(options.verbose, fName, warning)
    mainWindow.show()
    return app.exec_()


class CFGraphicsView(QGraphicsView):

    """Central widget"""

    def __init__(self, parent=None):
        super(CFGraphicsView, self).__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)

    def wheelEvent(self, event):
        """Mouse wheel event"""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            factor = 1.41 ** (-event.angleDelta() / 240.0)
            self.scale(factor, factor)
        else:
            QGraphicsView.wheelEvent(self, event)

    def zoomIn(self):
        """Zoom when a button clicked"""
        factor = 1.41 ** (120.0/240.0)
        self.scale(factor, factor)

    def zoomOut(self):
        """Zoom when a button clicked"""
        factor = 1.41 ** (-120.0/240.0)
        self.scale(factor, factor)


class MainWindow(QMainWindow):

    """Main application window"""

    def __init__(self, verbose, fName, warning):
        QMainWindow.__init__(self)

        self.logWidget = None
        self.view = None
        self.scene = None
        self.fName = fName
        self.verbose = verbose
        self.cFlow = None

        self.resize(1400, 800)

        self.updateWindowTitle()
        self.statusBar()
        self.createToolbar()
        self.createLogWindow()
        self.createGraphicsView()

        self.setCentralWidget(self.view)

        if verbose:
            self.logMessage("Using cdmcfparser version " + VERSION)

        if warning:
            self.logMessage(warning)

        if fName:
            # To yeld the main message processing loop
            kickOffTimer = QTimer()
            kickOffTimer.singleShot(200, self.proceedWithFile)

    def createToolbar(self):
        """There are a few buttons on the main window toolbar.

           They are: open, reload, zoom out, zoom in, debug, clear log
        """
        openButton = QAction(QIcon('icons/open.png'),
                             'Open (Ctrl+O)', self)
        openButton.setShortcut('Ctrl+O')
        openButton.setStatusTip('Open python file')
        openButton.triggered.connect(self.openButtonClicked)

        reloadButton = QAction(QIcon('icons/reload.png'),
                               'Reload (F5)', self)
        reloadButton.setShortcut('F5')
        reloadButton.setStatusTip('Reload python file')
        reloadButton.triggered.connect(self.reloadButtonClicked)

        zoomoutButton = QAction(QIcon('icons/zoomOut.png'),
                                'Zoom Out (Ctrl+-)', self)
        zoomoutButton.setShortcut('Ctrl+-')
        zoomoutButton.setStatusTip('Zoom Out')
        zoomoutButton.triggered.connect(self.zoomOut)

        zoominButton = QAction(QIcon('icons/zoomIn.png'),
                               'Zoom In (Ctrl++)', self)
        zoominButton.setShortcut('Ctrl++')
        zoominButton.setStatusTip('Zoom In')
        zoominButton.triggered.connect(self.zoomIn)

        clearLogButton = QAction(QIcon('icons/clear.png'),
                                 'Clear log (Ctrl+R)', self)
        clearLogButton.setShortcut('Ctrl+R')
        clearLogButton.setStatusTip('Clear log')
        clearLogButton.triggered.connect(self.clearButtonClicked)

        # A few separators
        separator = QAction(self)
        separator.setSeparator(True)
        separator1 = QAction(self)
        separator1.setSeparator(True)

        toolbar = self.addToolBar('Toolbar')
        toolbar.setIconSize(QSize(48, 48))
        toolbar.addAction(openButton)
        toolbar.addAction(reloadButton)
        toolbar.addAction(separator)
        toolbar.addAction(zoomoutButton)
        toolbar.addAction(zoominButton)
        toolbar.addAction(separator1)
        toolbar.addAction(clearLogButton)

    def createLogWindow(self):
        """Creates a dockable RO editor for logging"""
        self.logWidget = QTextEdit()
        self.logWidget.setReadOnly(True)
        self.logWidget.setFontFamily("Courier")
        self.logWidget.setFontPointSize(12.0)

        logDockWidget = QDockWidget("Log", self)
        logDockWidget.setObjectName("LogDockWidget")
        logDockWidget.setAllowedAreas(Qt.BottomDockWidgetArea)
        logDockWidget.setWidget(self.logWidget)

        self.addDockWidget(Qt.BottomDockWidgetArea, logDockWidget)

    def zoomIn(self):
        """zoom in the main window"""
        self.view.zoomIn()

    def zoomOut(self):
        """zoom out the main window"""
        self.view.zoomOut()

    def reloadButtonClicked(self):
        """reload button has been clicked"""
        self.proceedWithFile()

    def clearButtonClicked(self):
        """Deletes all the messages from the log window"""
        self.logWidget.clear()

    def createGraphicsView(self):
        """Creates the central widget"""
        self.scene = QGraphicsScene(self)

        self.view = CFGraphicsView(self)
        self.view.setScene(self.scene)

    def updateWindowTitle(self):
        """updates the main window title with the current so file"""
        if self.fName:
            self.setWindowTitle('Control flow for: ' + self.fName)
        else:
            self.setWindowTitle('Control flow for: no file selected')

    def logMessage(self, message):
        """Makes a log message visible in the user interface"""
        timestamp = datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S.%f')
        self.logWidget.append(timestamp + " " + message)
        self.logWidget.update()

    def openButtonClicked(self):
        """Brings up an open dialogue"""
        # By some unknown reasons the following simple way of getting a file is
        # not working:
        # fileName = QFileDialog.getOpenFileName(self, 'Open file',
        #                                        QDir.currentPath())
        #
        # There is however a workaround. Here it is:
        dialog = QFileDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        fileNames = dialog.selectedFiles()
        fileName = str(fileNames[0])

        if not os.path.exists(fileName):
            QMessageBox.critical(self, 'Error',
                                 'The selected file (' + fileName +
                                 ') does not exist')
            return

        # Check that the file is a python one
        warning = isPythonFile(fileName)
        if warning is not None:
            QMessageBox.critical(self, 'Error', warning)
            return

        # set the new file name
        self.fName = fileName
        self.updateWindowTitle()

        # initiate the process
        self.proceedWithFile()

    def proceedWithFile(self, needToParse=True):
        """Taks the file from settings and processes it"""
        if needToParse:
            if self.verbose:
                self.logMessage("Parsing file " + self.fName)
            self.cFlow = getControlFlowFromFile(self.fName)
            if self.verbose:
                self.logMessage("Parsed file:")
                self.logMessage(formatFlow(str(self.cFlow)))

            if len(self.cFlow.errors) != 0:
                self.logMessage("No drawing due to parsing errors")
                return

            if len(self.cFlow.warnings) != 0:
                self.logMessage("Parser warnings: ")
                for warn in self.cFlow.warnings:
                    self.logMessage(str(warn[0]) + ": " + warn[1])
        else:
            if self.cFlow is None:
                self.logMessage("No control flow object")
                return
            if len(self.cFlow.errors) != 0:
                self.logMessage("No drawing due to parsing errors")
                return

        self.scene.clear()

        if self.verbose:
            self.logMessage("Layouting ...")
        try:
            # To pick up possibly changed settings
            importlib.reload(cflowsettings)
            cflowSettings = cflowsettings.getDefaultCflowSettings(self)
            if DEBUG:
                cflowSettings.debug = True

            # Top level canvas has no adress and no parent canvas
            canvas = vcanvas.VirtualCanvas(cflowSettings, None, None, None)
            canvas.layout(self.cFlow, CellElement.FILE_SCOPE)
            if self.verbose:
                self.logMessage("Layout is done:")
                self.logMessage(str(canvas))
                self.logMessage("Rendering ...")

            width, height = canvas.render()
            if self.verbose:
                self.logMessage("Rendering is done. Scene size: " +
                                str(width) + "x" + str(height) +
                                ". Drawing ...")

            self.scene.setSceneRect(0, 0, width, height)
            canvas.draw(self.scene, 0, 0)
        except Exception as exc:
            self.logMessage("Exception:\n" + str(exc))
            raise

        if self.verbose:
            self.logMessage("Drawing is done.")


# The script execution entry point
if __name__ == "__main__":
    returnCode = 0
    try:
        returnCode = main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        returnCode = 1
    except:
        print("Unknown exception", file=sys.stderr)
        returnCode = 2
    sys.exit(returnCode)
