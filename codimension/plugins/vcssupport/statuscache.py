#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy sergey.satskiy@gmail.com
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

"""VCS plugin support: status cache"""

import datetime


class VCSStatus:

    """Holds the VCS file status"""

    def __init__(self):
        self.pluginID = None        # integer
        self.indicatorID = None     # integer
        self.message = None         # string or None
        self.lastUpdate = None      # time

    def __str__(self):
        return "Plugin ID: " + str(self.pluginID) + \
            " Indicator ID: " + str(self.indicatorID) + \
            " Message: " + str(self.message) + \
            " Last update: " + str(self.lastUpdate)

    def __eq__(self, other):
        if other is None:
            return False
        return self.pluginID == other.pluginID and \
            self.indicatorID == other.indicatorID and \
            self.message == other.message

    def __ne__(self, other):
        if other is None:
            return True
        return self.pluginID != other.pluginID or \
            self.indicatorID != other.indicatorID or \
            self.message != other.message


class VCSStatusCache:

    """Caches the file statuses which came from various plugins"""

    def __init__(self):
        self.cache = {}   # path -> VCSStatus

    def getStatus(self, path):
        """Provides the status if it is in the cache"""
        if path in self.cache:
            return self.cache[path]
        return None

    def updateStatus(self, path, pluginID, indicatorID, message, callback):
        """Updates the status in the cache"""
        if path in self.cache:
            item = self.cache[path]
            item.lastUpdate = datetime.datetime.now()
            if item.pluginID != pluginID or \
               item.indicatorID != indicatorID or \
               item.message != message:
                item.pluginID = pluginID
                item.indicatorID = indicatorID
                item.message = message
                if callback:
                    callback(path, item)
            return

        item = VCSStatus()
        item.pluginID = pluginID
        item.indicatorID = indicatorID
        item.message = message
        item.lastUpdate = datetime.datetime.now()
        self.cache[path] = item

        if callback:
            callback(path, item)

    def clear(self):
        """Purges the cache"""
        self.cache = {}

    def dismissPlugin(self, pluginID, callback):
        " Removes all the certain plugin entries from the cache "
        for path, status in self.cache.items():
            if status.pluginID == pluginID:
                status.lastUpdate = None
                status.pluginID = None
                status.message = None
                oldIndicator = status.indicatorID
                status.indicatorID = None
                if oldIndicator:
                    callback(path, status)
