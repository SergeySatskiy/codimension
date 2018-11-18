#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2018  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Codimension main Python script.

It performs necessery initialization and starts the Qt main loop.
"""

import sys
import os
import os.path
import gc
import traceback
import logging
import shutil
import datetime
import json
from optparse import OptionParser

# Workaround if link is used
sys.argv[0] = os.path.realpath(__file__)

# Make it possible to import from the subdirectories
srcDir = os.path.dirname(sys.argv[0])
if srcDir not in sys.path:
    sys.path.insert(0, srcDir)

from ui.qt import QTimer, QDir, QMessageBox
from ui.application import CodimensionApplication
from ui.splashscreen import SplashScreen
from utils.project import CodimensionProject
from utils.skin import (Skin, _DEFAULT_SKIN_SETTINGS, _DEFAULT_CFLOW_SETTINGS,
                        _DEFAULT_APP_CSS)
from utils.config import CONFIG_DIR
from utils.config import DEFAULT_ENCODING
from utils.settings import Settings, SETTINGS_DIR
from utils.globals import GlobalData
from utils.colorfont import toJSON


try:
    import cdmverspec
    VER = cdmverspec.version
except:
    VER = '0.0.0'


class CodimensionUILauncher:

    """Wrapper class to launch Codimension"""

    def __init__(self):
        self.rootLoggingHandlers = []

        # In case of windows XServers (at least X-Win32) early usage of
        # redirected logging.something(...) leads to a silent crash. It does
        # not happen in a pure Linux environment though. So some warning
        # messages are delayed till the main application loop has started.
        self.__delayedWarnings = []

        self.__args = []
        self.__options = None
        self.__projectFile = None
        self.__splash = None

    def setupLogging(self):
        """Configures the logging module"""
        if self.__options.debug:
            logLevel = logging.DEBUG
        else:
            logLevel = logging.INFO

        # Default output stream is stderr
        logging.basicConfig(level=logLevel,
                            format='%(levelname) -10s %(asctime)s %(message)s')

        # Memorize the root logging handlers
        self.rootLoggingHandlers = logging.root.handlers

    def isOpenable(self, fName):
        """Checks that the file can be opened"""
        # I cannot import it at the top because the fileutils want
        # to use the pixmap cache which needs the application to be
        # created, so the import is deferred
        from utils.fileutils import isFileOpenable

        if not os.path.exists(fName):
            self.__delayedWarnings.append('File does not exist: ' + fName)
            return False
        if not os.path.isfile(fName):
            self.__delayedWarnings.append('The ' + fName + ' is not a file')
            return False
        if not isFileOpenable(fName):
            self.__delayedWarnings.append('The file ' + fName +
                                          ' could not be opened in Codimension')
            return False
        return True

    def processCommandLineArgs(self):
        """Checks what is in the command line"""
        # I cannot import it at the top because the fileutils want
        # to use the pixmap cache which needs the application to be
        # created, so the import is deferred
        from utils.fileutils import getFileProperties, isCDMProjectMime

        if self.__args:
            totalArgs = len(self.__args)
            goodArgs = []
            for fName in self.__args:
                if self.isOpenable(fName):
                    goodArgs.append(fName)
            self.__args = goodArgs

            if totalArgs == 1 and len(self.__args) == 1:
                mime, _, _ = getFileProperties(self.__args[0])
                if isCDMProjectMime(mime):
                    return self.__args[0]

            # Check that the is no project file because it can only come alone
            for fName in self.__args:
                mime, _, _ = getFileProperties(fName)
                if isCDMProjectMime(mime):
                    raise Exception('A Codimension project file (' +
                                    fName + ') must not come '
                                    'together with other files')
        return None

    def main(self):
        """The codimension driver"""
        usageMessage = 'Usage: %prog [options] [project file | python files]'
        parser = OptionParser(usage=usageMessage, version='%prog ' + VER)

        parser.add_option(
            '--debug', action='store_true', dest='debug',
            default=False,
            help='switch on debug and info messages (default: Off)')
        parser.add_option(
            '--clean-start', action='store_true', dest='cleanStart',
            default=False,
            help='do not restore previous IDE state (default: Off)')

        self.__options, self.__args = parser.parse_args()
        self.setupLogging()

        # The default exception handler can be replaced
        sys.excepthook = exceptionHook

        # Create global data singleton.
        # It's unlikely to throw any exceptions.
        globalData = GlobalData()
        globalData.version = VER

        # Loading settings - they have to be loaded before the application is
        # created. This is because the skin name is saved there.
        settings = Settings()
        self.copySkin()

        # Load the skin
        globalData.skin = Skin()
        globalData.skin.load(SETTINGS_DIR + 'skins' +
                             os.path.sep + settings['skin'])

        self.__delayedWarnings += settings.validateZoom(
            globalData.skin.minTextZoom, globalData.skin.minCFlowZoom)

        # QT on UBUNTU has a bug - the main menu bar does not generate the
        # 'aboutToHide' signal (though 'aboutToShow' is generated properly. This
        # prevents codimension working properly so this hack below disables the
        # global menu bar for codimension and makes it working properly.
        os.environ['QT_X11_NO_NATIVE_MENUBAR'] = '1'
    
        # Create QT application
        codimensionApp = CodimensionApplication(sys.argv, settings['style'])
        globalData.application = codimensionApp

        logging.debug('Starting codimension v.%s', VER)

        try:
            # Process command line arguments
            self.__projectFile = self.processCommandLineArgs()
        except Exception as exc:
            logging.error(str(exc))
            parser.print_help()
            return 1

        # Show splash screen
        self.__splash = SplashScreen()

        screenSize = codimensionApp.desktop().screenGeometry()
        globalData.screenWidth = screenSize.width()
        globalData.screenHeight = screenSize.height()

        self.__splash.showMessage('Importing packages...')
        from ui.mainwindow import CodimensionMainWindow

        self.__splash.showMessage('Generating main window...')
        mainWindow = CodimensionMainWindow(self.__splash, settings)
        codimensionApp.setMainWindow(mainWindow)
        globalData.mainWindow = mainWindow
        codimensionApp.lastWindowClosed.connect(codimensionApp.quit)

        mainWindow.show()
        mainWindow.restoreWindowPosition()
        mainWindow.restoreSplitterSizes()

        # Launch the user interface
        QTimer.singleShot(1, self.launchUserInterface)

        # Run the application main cycle
        retVal = codimensionApp.exec_()
        return retVal

    def launchUserInterface(self):
        """UI launchpad"""
        globalData = GlobalData()

        self.__splash.showMessage('Loading plugins...')
        globalData.pluginManager.load()

        settings = Settings()
        mainWindow = globalData.mainWindow
        mainWindow.getToolbar().setVisible(settings['showMainToolBar'])

        needSignal = True
        if self.__options.cleanStart:
            # Codimension will not load anything.
            pass
        elif self.__projectFile:
            self.__splash.showMessage('Loading project...')
            globalData.project.loadProject(self.__projectFile)
            needSignal = False
        elif self.__args:
            # There are arguments and they are python files
            # The project should not be loaded but the files should
            # be opened
            for fName in self.__args:
                mainWindow.openFile(os.path.abspath(fName), -1)
        elif settings['projectLoaded']:
            if not settings['recentProjects']:
                # Some project was loaded but now it is not available.
                pass
            else:
                self.__splash.showMessage('Loading project...')
                if os.path.exists(settings['recentProjects'][0]):
                    globalData.project.loadProject(settings['recentProjects'][0])
                    needSignal = False
                else:
                    self.__delayedWarnings.append(
                        'Cannot open the most recent project: ' +
                        settings['recentProjects'][0] + '. Ignore and continue.')
        else:
            mainWindow.em.restoreTabs(settings.tabStatus)

        # Signal for triggering browsers layout
        if needSignal:
            globalData.project.sigProjectChanged.emit(
                CodimensionProject.CompleteProject)

        # The editors positions can be restored properly only when the editors have
        # actually been drawn. Otherwise the first visible line is unknown.
        # So, I load the project first and let object browsers initialize
        # themselves and then manually call the main window handler to restore the
        # editors. The last step is to connect the signal.
        mainWindow.onProjectChanged(CodimensionProject.CompleteProject)
        globalData.project.sigProjectChanged.connect(mainWindow.onProjectChanged)

        self.__splash.finish(globalData.mainWindow)
        self.__splash = None
        del self.__splash

        for message in self.__delayedWarnings:
            logging.warning(message)

        # Some startup time objects could be collected here. In my test runs
        # there were around 700 objects.
        gc.collect()

    def copySkin(self):
        """Copies the new system-wide skins to the user settings dir.

        Also tests if the configured skin is in place. Sets the default if not.
        """
        # I cannot import it at the top because the fileutils want
        # to use the pixmap cache which needs the application to be
        # created, so the import is deferred
        from utils.fileutils import saveToFile

        systemWideSkinsDir = srcDir + os.path.sep + 'skins' + os.path.sep
        userSkinsDir = os.path.normpath(QDir.homePath()) + \
            os.path.sep + CONFIG_DIR + os.path.sep + 'skins' + os.path.sep

        skinFiles = ['app.css', 'skin.json', 'cflow.json']
        platformSuffix = '.' + sys.platform.lower()

        if os.path.exists(systemWideSkinsDir):
            for item in os.listdir(systemWideSkinsDir):
                candidate = systemWideSkinsDir + item
                if os.path.isdir(candidate):
                    userCandidate = userSkinsDir + item
                    if not os.path.exists(userCandidate):
                        try:
                            os.makedirs(userCandidate, exist_ok=True)
                            filesToCopy = []
                            for fName in skinFiles:
                                generalFile = candidate + os.path.sep + fName
                                platformSpecificFile = generalFile + platformSuffix
                                userFile = userCandidate + os.path.sep + fName
                                if os.path.exists(platformSpecificFile):
                                    filesToCopy.append([platformSpecificFile,
                                                        userFile])
                                elif os.path.exists(generalFile):
                                    filesToCopy.append([generalFile, userFile])
                                else:
                                    raise Exception('The skin file ' + fName +
                                                    ' is not found in the '
                                                    'installation package')
                            for srcDst in filesToCopy:
                                shutil.copyfile(srcDst[0], srcDst[1])
                        except Exception as exc:
                            logging.error('Could not copy system wide skin from '
                                          '%s to  the user skin to %s. '
                                          'Continue without copying skin.',
                                          candidate, userCandidate)
                            logging.error(str(exc))

        # Deal with the default settings
        defaultSkinDir = userSkinsDir + 'default'
        defaultSkinDirOK = True
        if not os.path.exists(defaultSkinDir):
            # Create the default skin dir
            try:
                os.makedirs(defaultSkinDir, exist_ok=True)
            except Exception as exc:
                defaultSkinDirOK = False
                logging.error('Error creating a default skin directory: %s',
                              defaultSkinDir)
                logging.error(str(exc))
    
        if defaultSkinDirOK:
            defaultCSS = defaultSkinDir + os.path.sep + 'app.css'
            if not os.path.exists(defaultCSS):
                try:
                    saveToFile(defaultCSS, _DEFAULT_APP_CSS)
                except Exception as exc:
                    logging.error('Error creating default skin app.css file at %s',
                                  defaultCSS)
                    logging.error(str(exc))
            defaultCommonSkin = defaultSkinDir + os.path.sep + 'skin.json'
            if not os.path.exists(defaultCommonSkin):
                try:
                    with open(defaultCommonSkin, 'w',
                              encoding=DEFAULT_ENCODING) as diskfile:
                        json.dump(_DEFAULT_SKIN_SETTINGS, diskfile, indent=4,
                                  default=toJSON)
                except Exception as exc:
                    logging.error('Error creating default skin skin.json '
                                  'file at %s', defaultCommonSkin)
                    logging.error(str(exc))
            defaultCFlowSkin  = defaultSkinDir + os.path.sep + 'cflow.json'
            if not os.path.exists(defaultCFlowSkin):
                try:
                    with open(defaultCFlowSkin, 'w',
                              encoding=DEFAULT_ENCODING) as diskfile:
                        json.dump(_DEFAULT_CFLOW_SETTINGS, diskfile, indent=4,
                                  default=toJSON)
                except Exception as exc:
                    logging.error('Error creating default skin cflow.json '
                                  'file at %s', defaultCFlowSkin)
                    logging.error(str(exc))

        # Check that the configured skin is in place
        userSkinDir = userSkinsDir + Settings()['skin']
        if os.path.exists(userSkinDir) and os.path.isdir(userSkinDir):
            # That's just fine
            return

        # Here: the configured skin is not found in the user dir.
        # Try to set the default.
        if os.path.exists(defaultSkinDir):
            if os.path.isdir(defaultSkinDir):
                logging.warning("The configured skin '%s' has not been found. "
                                "Fallback to the 'default' skin.",
                                Settings()['skin'])
                Settings()['skin'] = 'default'
                return

        # Default is not there. Try to pick any.
        anySkinName = None
        for item in os.listdir(userSkinsDir):
            if os.path.isdir(userSkinsDir + item):
                anySkinName = item
                break

        if anySkinName is None:
            # Really bad situation. No system wide skins, no local skins.
            logging.error('Cannot find the any Codimension skin. '
                          'Please check Codimension installation.')
            return

        # Here: last resort - fallback to the first found skin
        logging.warning("The configured skin '%s' has not been found. "
                        "Fallback to the '%s' skin.",
                        Settings()['skin'], anySkinName)
        Settings()['skin'] = anySkinName


def exceptionHook(excType, excValue, tracebackObj):
    """Catches unhandled exceptions"""
    globalData = GlobalData()

    # Keyboard interrupt is a special case
    if issubclass(excType, KeyboardInterrupt):
        if globalData.application is not None:
            globalData.application.quit()
        return

    error = '%s: %s' % (excType.__name__, excValue)
    stackTraceString = ''.join(traceback.format_exception(excType, excValue,
                                                          tracebackObj))

    # Save the traceback to a file explicitly together with a log window
    # content.
    excptFileName = SETTINGS_DIR + 'unhandledexceptions.log'
    try:
        savedOK = True
        with open(excptFileName, 'a',
                  encoding=DEFAULT_ENCODING) as diskfile:
            diskfile.write('------ Unhandled exception report at ' +
                           str(datetime.datetime.now()) + '\n')
            diskfile.write('Traceback:\n')
            diskfile.write(stackTraceString)

            diskfile.write('Log window:\n')
            if globalData.mainWindow is not None:
                # i.e. the log window is available, save its content too
                logWindowContent = globalData.mainWindow.getLogViewerContent()
                logWindowContent = logWindowContent.strip()
                if logWindowContent:
                    diskfile.write(logWindowContent)
                    diskfile.write('\n')
                else:
                    diskfile.write('Nothing is there\n')
            else:
                diskfile.write('Has not been created yet\n')
            diskfile.write('------\n\n')
    except:
        savedOK = False

    # This output will be to a console if the application has not started yet
    # or to a log window otherwise.
    logging.error('Unhandled exception is caught\n%s', stackTraceString)

    # Display the message as a QT modal dialog box if the application
    # has started
    if globalData.application is not None:
        message = "<html><body>"
        if savedOK:
            message += "Stack trace and log window content saved in " + \
                       excptFileName + ".<br>"
        else:
            message += "Failed to save stack trace and log window " \
                       "content in " + excptFileName + ".<br>"

        lines = stackTraceString.split('\n')
        if len(lines) > 32:
            message += "First 32 lines of the stack trace " \
                       "(the rest is truncated):" \
                       "<pre>" + "\n".join(lines[:32]) + "<pre>"
        else:
            message += "Stack trace:" + \
                       "<pre>" + stackTraceString + "</pre>"
        message += "</body></html>"
        QMessageBox.critical(None, "Unhandled exception: " + error, message)
        globalData.application.exit(1)


def main():
    """The main entry point"""
    launcher = CodimensionUILauncher()
    retCode = launcher.main()

    # restore root logging handlers
    if launcher.rootLoggingHandlers:
        logging.root.handlers = launcher.rootLoggingHandlers

    logging.debug('Exiting codimension')
    sys.exit(retCode)


if __name__ == '__main__':
    main()
