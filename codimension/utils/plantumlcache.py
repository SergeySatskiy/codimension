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


import os.path
import logging
import datetime
import hashlib
import urllib.request
from .fileutils import loadJSON, saveJSON, saveBinaryToFile
from ui.qt import QThread, pyqtSignal, QObject

CACHE_FILE_NAME = 'cachemap.json'


class PlantUMLRenderer(QThread):

    """Runs plantuml"""

    sigFinishedOK = pyqtSignal(str, str, str)       # md5, uuid, file
    sigFinishedError = pyqtSignal(str, str)         # md5, file

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def get(self, source, fName, uuid):
        self.__source = source
        self.__uuid = uuid
        self.__fName = fName
        self.start()

    def run(self):
        try:
            # Run plantUML


            saveBinaryToFile(self.__fName, req.read())
            self.sigRetrieveOK.emit(self.__url, self.__uuid, self.__fName)
        except Exception as exc:
            logging.error('Cannot retrieve ' + self.__url + ': ' + str(exc))
            self.sigRetrieveError.emit(self.__url, self.__fName)



class PlantUMLCache(QObject):

    """The plantUML render cache"""

    sigRenderReady = pyqtSignal(str, str, str)    # md5, uuid, file

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

    def onRenderOK(self, url, uuid, fName):
        """Resource downloaded and saved"""
        self.__md5ToFileName[url] = fName
        self.__onThreadFinish(fName)
        self.__saveCache()
        self.sigRenderReady.emit(url, uuid, fName)

    def onRenderError(self, url, fName):
        """Error downloading the resource"""
        self.__md5ToFileName[url] = None
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

    def __normalizeSource(source):
        """Normalizes the diagram source"""
        # For the time being it merely strips the source. Empty lines cannot be
        # voluntary removed because they may be meaningfull in e.g. multi line
        # captions. The same story is about leading and trailing spaces in
        # the source lines
        return source.strip()

    def getResource(self, source, uuid):
        """Provides the rendered file name

        If None => no rendering will be done
        Otherwise the ready-to-use file or where the pic is expected
        """
        if self.__cacheDir is None:
            return None

        normSource = self.__normalizeSource(source)
        md5 = hashlib.md5(normSource.encode('utf-8')).hexdigest()
        if md5 in self.__md5ToFileName:
            return self.__md5ToFileName[md5]

        basename = md5 + '.png'
        fName = self.__cacheDir + basename
        if fName in self.__threads:
            # Reject double request
            return fName

        thread = ResourceRetriever()
        self.__threads[fName] = thread
        self.__connectThread(thread)
        thread.get(normSource, fName, uuid)
        return fName
