# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2019  Sergey V. Satskiy sergey.satskiy@tuta.io
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

"""Rendered plantuml diagram cache"""


import sys
import subprocess
import os.path
import logging
import datetime
import hashlib
from distutils.spawn import find_executable
from .fileutils import loadJSON, saveJSON, saveToFile
from ui.qt import QThread, pyqtSignal, QObject

CACHE_FILE_NAME = 'cachemap.json'


def getPlantUMLJarPath():
    """Provides the full path to the plantUML jar file"""
    if  find_executable('java') == None:
        return None
    exeDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    plantUMLPath = os.path.dirname(exeDir) + os.path.sep + 'plantuml' + os.path.sep
    for item in os.listdir(plantUMLPath):
        if item.startswith('plantuml.') and item.endswith('.jar'):
            return plantUMLPath + item
    return None
JAR_PATH = getPlantUMLJarPath()


def __removeEmptyForward(items, startIndex, length):
    toRemove = []
    for index in range(startIndex, length):
        if not items[index].strip():
            toRemove.append(index)
    for index in range(len(toRemove)):
        items.pop(toRemove[-(index + 1)])
    return items


def __removeEmptyBackward(items, endIndex):
    while not items[endIndex].strip():
        items.pop(endIndex)
        endIndex -= 1
    return items


def normalizePlantumlSource(source):
    """Normalizes the diagram source"""
    lines = source.strip().splitlines()
    length = len(lines)
    if length == 1:
        if lines[0].startswith('@start'):
            # end is missed
            return '\n'.join([lines[0], '@end' + lines[0][6:]])
        if lines[0].startswith('@end'):
            # start is missed
            return'\n'.join(['@start' + lines[0][4:], lines[0]])
        # missed both
        return '\n'.join(['@startuml', lines[0], '@enduml'])

    # More than one line
    startFound = lines[0].startswith('@start')
    endFound = lines[-1].lstrip().startswith('@end')

    if startFound and endFound:
        # both found
        # remove empty lines before and after
        __removeEmptyForward(lines, 1, length)
        __removeEmptyBackward(lines, len(lines) - 2)
        lines[0] = lines[0].strip()
        lines[-1] = lines[-1].strip()
    elif startFound:
        # start is here, end is missed
        __removeEmptyForward(lines, 1, length)
        lines[0] = lines[0].strip()
        lines.append('@end' + lines[0][6:])
    elif endFound:
        # start is missed, end is here
        __removeEmptyBackward(lines, length - 2)
        lines[-1] = lines[-1].strip()
        lines.insert(0, '@start' + lines[-1][4:])
    else:
        # both missed
        __removeEmptyForward(lines, 0, length)
        __removeEmptyBackward(lines, len(lines) - 1)
        lines.insert(0, '@startuml')
        lines.append('@enduml')

    return '\n'.join(lines)


class PlantUMLRenderer(QThread):

    """Runs plantuml"""

    sigFinishedOK = pyqtSignal(str, str, str)       # md5, uuid, file
    sigFinishedError = pyqtSignal(str, str)         # md5, file

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def get(self, source, md5, fName, uuid):
        self.__source = source
        self.__md5 = md5
        self.__uuid = uuid
        self.__fName = fName
        self.start()

    def safeUnlink(self, fName):
        try:
            os.unlink(fName)
        except:
            pass

    def run(self):
        srcFile = self.__fName[:-3] + 'txt'
        try:
            # Run plantUML
            saveToFile(srcFile, self.__source)
            retCode = subprocess.call(['java', '-jar', JAR_PATH,
                                       '-charset', 'utf-8', '-nometadata', srcFile],
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
            self.safeUnlink(srcFile)

            if retCode == 0:
                self.sigFinishedOK.emit(self.__md5, self.__uuid, self.__fName)
            else:
                self.sigFinishedError.emit(self.__md5, self.__fName)
        except Exception as exc:
            logging.error('Cannot render a plantUML diagram: ' + str(exc))
            self.safeUnlink(srcFile)
            self.sigFinishedError.emit(self.__md5, self.__fName)



class PlantUMLCache(QObject):

    """The plantUML render cache"""

    sigRenderReady = pyqtSignal(str, str)    # uuid, file

    def __init__(self, cacheDir):
        QObject.__init__(self)

        self.__md5ToFileName = {}
        self.__threads = {}
        self.__cacheDir = os.path.normpath(cacheDir) + os.path.sep

        if os.path.exists(self.__cacheDir):
            if os.path.isdir(self.__cacheDir):
                if os.access(self.__cacheDir, os.W_OK):
                    self.__loadCache()
                    self.__saveCache()
                else:
                    logging.error('The plantUML render cache directory (' +
                                  self.__cacheDir + ') does not '
                                  'have write permissions. There will be no '
                                  'plantUML rendering')
                    self.__cacheDir = None
            else:
                logging.error('The plantUML render cache directory path (' +
                              self.__cacheDir + ') exists and '
                              'is not a directory. There will be no pluntUML '
                              'rendering')
                self.__cacheDir = None
        else:
            # Try to create the dir
            try:
                os.mkdir(self.__cacheDir)
            except Exception as exc:
                logging.error('Error creating pluntUML render cache directory '
                              + self.__cacheDir + ': ' + str(exc) +
                              ' There will be no plantUML rendering')
                self.__cacheDir = None

    def __loadCache(self):
        """Loads the cache from the disk files"""
        if self.__cacheDir is None:
            return

        # Remove too old files
        now = datetime.datetime.now()
        limit = now - datetime.timedelta(days=1)
        limit = limit.timestamp()
        for item in os.listdir(self.__cacheDir):
            if item == CACHE_FILE_NAME:
                continue
            if os.path.isfile(self.__cacheDir + item):
                modtime = os.path.getmtime(self.__cacheDir + item)
                if modtime < limit:
                    try:
                        os.unlink(self.__cacheDir + item)
                    except Exception as exc:
                        logging.error('Error removing obsolete plantUML '
                                      'render file (' +
                                      self.__cacheDir + item + '): ' + str(exc))

        if os.path.exists(self.__cacheDir + CACHE_FILE_NAME):
            prevCache = loadJSON(self.__cacheDir + CACHE_FILE_NAME,
                                 'plantUML render cache map', None)
            for item in prevCache.items():
                if os.path.exists(item[1]):
                    self.__md5ToFileName[item[0]] = item[1]

    def __saveCache(self):
        """Saves the cache to the disk"""
        if self.__cacheDir is None:
            return
        dictToSave = {}
        for item in self.__md5ToFileName.items():
            if item[1] is not None:
                dictToSave[item[0]] = item[1]
        saveJSON(self.__cacheDir + CACHE_FILE_NAME, dictToSave,
                 'plantUML render cache map')

    def onRenderOK(self, md5, uuid, fName):
        """Render saved successfully"""
        self.__md5ToFileName[md5] = fName
        self.__onThreadFinish(fName)
        self.__saveCache()
        self.sigRenderReady.emit(uuid, fName)

    def onRenderError(self, md5, fName):
        """Error rendering"""
        self.__md5ToFileName[md5] = None
        self.__onThreadFinish(fName)

    def __onThreadFinish(self, fName):
        """Cleans up after a retrieval thread"""
        thread = self.__threads.get(fName, None)
        if thread is not None:
            self.__disconnectThread(thread)
            thread.wait()
            self.__threads.pop(fName)

    def __connectThread(self, thread):
        """Connects the thread signals"""
        thread.sigFinishedOK.connect(self.onRenderOK)
        thread.sigFinishedError.connect(self.onRenderError)

    def __disconnectThread(self, thread):
        """Connects the thread signals"""
        try:
            thread.sigFinishedOK.disconnect(self.onRenderOK)
            thread.sigFinishedError.disconnect(self.onRenderError)
        except:
            pass

    def getResource(self, source, uuid):
        """Provides the rendered file name

        If None => no rendering will be done
        Otherwise the ready-to-use file or where the pic is expected
        """
        if self.__cacheDir is None or JAR_PATH is None:
            return None

        normSource = normalizePlantumlSource(source)
        print('Normalized: ' + normSource)
        md5 = hashlib.md5(normSource.encode('utf-8')).hexdigest()
        if md5 in self.__md5ToFileName:
            return self.__md5ToFileName[md5]

        basename = md5 + '.png'
        fName = self.__cacheDir + basename
        if fName in self.__threads:
            # Reject double request
            return fName

        thread = PlantUMLRenderer()
        self.__threads[fName] = thread
        self.__connectThread(thread)
        thread.get(normSource, md5, fName, uuid)
        return fName
