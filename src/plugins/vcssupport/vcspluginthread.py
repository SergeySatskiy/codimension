# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""VCS plugin support: plugin thread"""

import time
from collections import deque
from ui.qt import QThread, QMutex, QWaitCondition, pyqtSignal
from plugins.categories.vcsiface import VersionControlSystemInterface


# Indicator used by IDE to display errors while retrieving item status
IND_VCS_ERROR = -2


class VCSPluginThread(QThread):

    """Wrapper for the plugin thread"""

    VCSStatus = pyqtSignal(str, int, str)

    def __init__(self, plugin, parent=None):
        QThread.__init__(self, parent)

        self.__plugin = plugin
        self.__requestQueue = deque()

        self.__stopRequest = False
        self.__lock = QMutex()
        self.__condition = QWaitCondition()

    def run(self):
        """Thread loop"""
        while not self.__stopRequest:
            self.__lock.lock()
            while self.__requestQueue:
                path, flag = self.__requestQueue.pop()
                self.__lock.unlock()
                time.sleep(0.01)
                self.__processRequest(path, flag)
                if self.__stopRequest:
                    break
                self.__lock.lock()
            if self.__stopRequest:
                self.__lock.unlock()
                break
            self.__condition.wait(self.__lock)
            self.__lock.unlock()

    def __processRequest(self, path, flag):
        """Processes a single request. It must be exception safe."""
        try:
            statuses = self.__plugin.getObject().getStatus(path, flag)
            for status in statuses:
                if len(status) == 3:
                    self.VCSStatus.emit(path + status[0], status[1], status[2])
                else:
                    self.VCSStatus.emit(
                        path, IND_VCS_ERROR,
                        "The " + self.__plugin.getName() + " plugin "
                        "does not follow the getStatus() interface agreement")
        except Exception as exc:
            self.VCSStatus.emit(
                path, IND_VCS_ERROR,
                "Exception in " + self.__plugin.getName() +
                " plugin while retrieving VCS status: " + str(exc))
        except:
            self.VCSStatus.emit(
                path, IND_VCS_ERROR,
                "Unknown exception in " + self.__plugin.getName() +
                " plugin while retrieving VCS status")

    def addRequest(self, path, flag, urgent=False):
        """Adds a request to the queue"""
        self.__lock.lock()
        if urgent:
            self.__requestQueue.append((path, flag))
        else:
            self.__requestQueue.appendleft((path, flag))
        self.__lock.unlock()
        self.__condition.wakeAll()

    def stop(self):
        """Delivers the stop request"""
        self.__stopRequest = True
        self.__condition.wakeAll()

    def clearRequestQueue(self):
        """Clears the thread request queue"""
        self.__lock.lock()
        self.__requestQueue.clear()
        self.__lock.unlock()

    def canInitiateStatusRequestLoop(self):
        """Returns true if the is no jam in the request queue"""
        # It is a very rough test which seems however good enough.
        # First it is checked that there are no more than 10 (picked arbitrary)
        # not served yet requests in the queue and then it is checked if there
        # is at least one directory status request from a previous iteration.
        self.__lock.lock()
        if len(self.__requestQueue) > 10:
            self.__lock.unlock()
            return False
        for item in self.__requestQueue:
            if item[1] == VersionControlSystemInterface.REQUEST_DIRECTORY:
                self.__lock.unlock()
                return False
        self.__lock.unlock()
        return True
