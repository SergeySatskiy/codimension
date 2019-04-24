# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2019  Sergey V. Satskiy sergey.satskiy@gmail.com
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

""" Resource cache for the markdown renderer """

# By default the text browser does not download the internet resource so
# this facility needs to be implemented separately

import os.path
import logging
import datetime
import hashlib
import urllib.request
from .fileutils import loadJSON, saveJSON, saveBinaryToFile
from ui.qt import QThread, pyqtSignal, QObject

TIMEOUT = 5   # timeout in seconds to do a request
CACHE_FILE_NAME = 'cachemap.json'


class ResourceRetriever(QThread):

    """Retrieves the item from the web"""

    sigRetrieveOK = pyqtSignal(str, str, str)       # url, uuid, file
    sigRetrieveError = pyqtSignal(str, str)         # url, file

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def get(self, url, fName, uuid):
        self.__url = url
        self.__uuid = uuid
        self.__fName = fName
        self.start()

    def run(self):
        try:
            req = urllib.request.urlopen(self.__url, timeout=TIMEOUT)
            saveBinaryToFile(self.__fName, req.read())
            self.sigRetrieveOK.emit(self.__url, self.__uuid, self.__fName)
        except Exception as exc:
            logging.error('Cannot retrieve ' + self.__url + ': ' + str(exc))
            self.sigRetrieveError.emit(self.__url, self.__fName)



class WebResourceCache(QObject):

    """ The we resources cache """

    sigResourceSaved = pyqtSignal(str, str, str)    # url, uuid, file

    def __init__(self, cacheDir):
        QObject.__init__(self)

        self.__urlToFileName = {}
        self.__threads = {}
        self.__cacheDir = os.path.normpath(cacheDir) + os.path.sep

        if os.path.exists(self.__cacheDir):
            if os.path.isdir(self.__cacheDir):
                if os.access(self.__cacheDir, os.W_OK):
                    self.__loadCache()
                    self.__saveCache()
                else:
                    logging.error('The web resource cache directory (' +
                                  self.__cacheDir + ') does not '
                                  'have write permissions. There will be no '
                                  'web resource downloading')
                    self.__cacheDir = None
            else:
                logging.error('The web resource cache directory path (' +
                              self.__cacheDir + ') exists and '
                              'is not a directory. There will be no web '
                              'resource downloading')
                self.__cacheDir = None
        else:
            # Try to create the dir
            try:
                os.mkdir(self.__cacheDir)
            except Exception as exc:
                logging.error('Error creating the web resource cache directory '
                              + self.__cacheDir + ': ' + str(exc) +
                              ' There will be no web resource downloading')
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
                        logging.error('Error removing obsolete web '
                                      'resource file (' +
                                      self.__cacheDir + item + '): ' + str(exc))

        if os.path.exists(self.__cacheDir + CACHE_FILE_NAME):
            prevCache = loadJSON(self.__cacheDir + CACHE_FILE_NAME,
                                 'web resources cache map', None)
            for item in prevCache.items():
                if os.path.exists(item[1]):
                    self.__urlToFileName[item[0]] = item[1]

    def __saveCache(self):
        """Saves the cache to the disk"""
        if self.__cacheDir is None:
            return
        dictToSave = {}
        for item in self.__urlToFileName.items():
            if item[1] is not None:
                dictToSave[item[0]] = item[1]
        saveJSON(self.__cacheDir + CACHE_FILE_NAME, dictToSave,
                 'web resources cache map')

    def onResourceSaved(self, url, uuid, fName):
        """Resource downloaded and saved"""
        self.__urlToFileName[url] = fName
        self.__onThreadFinish(fName)
        self.__saveCache()
        self.sigResourceSaved.emit(url, uuid, fName)

    def onResourceError(self, url, fName):
        """Error downloading the resource"""
        self.__urlToFileName[url] = None
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
        thread.sigRetrieveOK.connect(self.onResourceSaved)
        thread.sigRetrieveError.connect(self.onResourceError)

    def __disconnectThread(self, thread):
        """Connects the thread signals"""
        try:
            thread.sigRetrieveOK.disconnect(self.onResourceSaved)
            thread.sigRetrieveError.disconnect(self.onResourceError)
        except:
            pass

    def getResource(self, url, uuid):
        """Provides the resource"""
        if self.__cacheDir is None:
            return None

        fName = self.__cacheDir + hashlib.md5(url.encode('utf-8')).hexdigest()
        if url in self.__urlToFileName:
            return self.__urlToFileName[url]

        if fName in self.__threads:
            # Reject double request
            return None

        thread = ResourceRetriever()
        self.__threads[fName] = thread
        self.__connectThread(thread)
        thread.get(url, fName, uuid)
        return None
