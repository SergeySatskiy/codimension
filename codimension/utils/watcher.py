# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""
The watcher cares of the given directories structures.
If somethig has been changed then it emits a signal.
It accepts a set of exclude filters and a set of dirs to watch.
The watcher will ignore the directories which do not exist.
"""

import os
import os.path
import re
from ui.qt import QObject, QFileSystemWatcher, pyqtSignal


class Watcher(QObject):

    """Filesystem watcher implementation"""

    sigFSChanged = pyqtSignal(list)

    def __init__(self, excludeFilters, dirToWatch):
        QObject.__init__(self)
        self.__dirWatcher = QFileSystemWatcher(self)

        # data members
        self.__excludeFilter = []       # Files exclude filter
        self.__srcDirsToWatch = set()   # Came from the user

        self.__fsTopLevelSnapshot = {}  # Current snapshot
        self.__fsSnapshot = {}          # Current snapshot

        # Sets of dirs which are currently watched
        self.__dirsToWatch = set()
        self.__topLevelDirsToWatch = set()      # Generated till root

        # precompile filters
        for flt in excludeFilters:
            self.__excludeFilter.append(re.compile(flt))

        # Initialise the list of dirs to watch
        self.__srcDirsToWatch.add(dirToWatch)

        self.__topLevelDirsToWatch = self.__buildTopDirsList(
                                        self.__srcDirsToWatch)
        self.__fsTopLevelSnapshot = self.__buildTopLevelSnapshot(
                                        self.__topLevelDirsToWatch,
                                        self.__srcDirsToWatch)
        self.__dirsToWatch = self.__buildSnapshot()

        # Here __dirsToWatch and __topLevelDirsToWatch have a complete
        # set of what should be watched

        # Add the dirs to the watcher
        dirs = []
        for path in self.__dirsToWatch | self.__topLevelDirsToWatch:
            dirs.append(path)
        self.__dirWatcher.addPaths(dirs)
        self.__dirWatcher.directoryChanged.connect(self.__onDirChanged)

        # self.debug()
        return

    @staticmethod
    def __buildTopDirsList(srcDirs):
        """Takes a list of dirs to be watched and builds top dirs set"""
        topDirsList = set()
        for path in srcDirs:
            parts = path.split(os.path.sep)
            for index in range(1, len(parts) - 1):
                candidate = os.path.sep.join(parts[0:index]) + os.path.sep
                if os.path.exists(candidate):
                    if os.access(candidate, os.R_OK):
                        topDirsList.add(candidate)
        return topDirsList

    @staticmethod
    def __buildTopLevelSnapshot(topLevelDirs, srcDirs):
        """Takes top level dirs and builds their snapshot"""
        snapshot = {}
        for path in topLevelDirs:
            itemsSet = set()
            # search for all the dirs to be watched
            for candidate in topLevelDirs | srcDirs:
                if len(candidate) <= len(path):
                    continue
                if candidate.startswith(path):
                    candidate = candidate[len(path):]
                    slashIndex = candidate.find(os.path.sep) + 1
                    item = candidate[:slashIndex]
                    if os.path.exists(path + item):
                        itemsSet.add(item)
            snapshot[path] = itemsSet
        return snapshot

    def __buildSnapshot(self):
        """Builds the filesystem snapshot"""
        snapshotDirs = set()
        for path in self.__srcDirsToWatch:
            self.__addSnapshotPath(path, snapshotDirs)
        return snapshotDirs

    def __addSnapshotPath(self, path, snapshotDirs, itemsToReport=None):
        """Adds one path to the FS snapshot"""
        if not os.path.exists(path):
            return

        snapshotDirs.add(path)
        dirItems = set()
        for item in os.listdir(path):
            if self.__shouldExclude(item):
                continue
            if os.path.isdir(path + item):
                dirName = path + item + os.path.sep
                dirItems.add(item + os.path.sep)
                if itemsToReport is not None:
                    itemsToReport.append("+" + dirName)
                self.__addSnapshotPath(dirName, snapshotDirs, itemsToReport)
                continue
            dirItems.add(item)
            if itemsToReport is not None:
                itemsToReport.append("+" + path + item)
        self.__fsSnapshot[path] = dirItems
        return

    def __onDirChanged(self, path):
        """Triggered when the dir is changed"""
        if not path.endswith(os.path.sep):
            path = path + os.path.sep

        # Check if it is a top level dir
        try:
            oldSet = self.__fsTopLevelSnapshot[path]

            # Build a new set of what is in that top level dir
            newSet = set()
            for item in os.listdir(path):
                if not os.path.isdir(path + item):
                    continue    # Only dirs are of interest for the top level
                item = item + os.path.sep
                if item in oldSet:
                    newSet.add(item)
            # Now we have an old set and a new one with those from the old
            # which actually exist
            diff = oldSet - newSet

            # diff are those which disappeared. We need to do the following:
            # - build a list of all the items in the fs snapshot which start
            #   from this dir
            # - build a list of dirs which should be deregistered from the
            #   watcher. This list includes both top level and project level
            # - deregister dirs from the watcher
            # - emit a signal of what disappeared
            if not diff:
                return  # no changes

            self.__fsTopLevelSnapshot[path] = newSet

            dirsToBeRemoved = []
            itemsToReport = []

            for item in diff:
                self.__processRemoveTopDir(path + item, dirsToBeRemoved,
                                           itemsToReport)

            # Here: it is possible that the last dir to watch disappeared
            if not newSet:
                # There is nothing to watch here anymore
                dirsToBeRemoved.append(path)
                del self.__fsTopLevelSnapshot[path]

                parts = path[1:-1].split(os.path.sep)
                for index in range(len(parts) - 2, 0, -1):
                    candidate = os.path.sep + \
                                os.path.sep.join(parts[0:index]) + \
                                os.path.sep
                    dirSet = self.__fsTopLevelSnapshot[candidate]
                    dirSet.remove(parts[index + 1] + os.path.sep)
                    if not dirSet:
                        dirsToBeRemoved.append(candidate)
                        del self.__fsTopLevelSnapshot[candidate]
                        continue
                    break   # it is not the last item in the set

            # Update the watcher
            if dirsToBeRemoved:
                self.__dirWatcher.removePaths(dirsToBeRemoved)

            # Report
            if itemsToReport:
                self.sigFSChanged.emit(itemsToReport)
            return
        except:
            # it is not a top level dir - no key
            pass

        # Here: the change is in the project level dir
        try:
            oldSet = self.__fsSnapshot[path]

            # Build a new set of what is in that top level dir
            newSet = set()
            for item in os.listdir(path):
                if self.__shouldExclude(item):
                    continue
                if os.path.isdir(path + item):
                    newSet.add(item + os.path.sep)
                else:
                    newSet.add(item)

            # Here: we have a new and old snapshots
            # Lets calculate the difference
            deletedItems = oldSet - newSet
            addedItems = newSet - oldSet

            if not deletedItems and not addedItems:
                return  # No changes

            # Update the changed dir set
            self.__fsSnapshot[path] = newSet

            # We need to build some lists:
            # - list of files which were added
            # - list of dirs which were added
            # - list of files which were deleted
            # - list of dirs which were deleted
            # The deleted dirs must be unregistered in the watcher
            # The added dirs must be registered
            itemsToReport = []
            dirsToBeAdded = []
            dirsToBeRemoved = []

            for item in addedItems:
                if item.endswith(os.path.sep):
                    # directory was added
                    self.__processAddedDir(path + item,
                                           dirsToBeAdded, itemsToReport)
                else:
                    itemsToReport.append("+" + path + item)

            for item in deletedItems:
                if item.endswith(os.path.sep):
                    # directory was deleted
                    self.__processRemovedDir(path + item,
                                             dirsToBeRemoved, itemsToReport)
                else:
                    itemsToReport.append("-" + path + item)

            # Update the watcher
            if dirsToBeRemoved:
                self.__dirWatcher.removePaths(dirsToBeRemoved)
            if dirsToBeAdded:
                self.__dirWatcher.addPaths(dirsToBeAdded)

            # Report
            self.sigFSChanged.emit(itemsToReport)
        except:
            # It could be a queued signal about what was already reported
            pass

        # self.debug()
        return

    def __shouldExclude(self, name):
        """Tests if a file must be excluded"""
        for excl in self.__excludeFilter:
            if excl.match(name):
                return True
        return False

    def __processAddedDir(self, path, dirsToBeAdded, itemsToReport):
        """called for an appeared dir in the project tree"""
        dirsToBeAdded.append(path)
        itemsToReport.append("+" + path)

        # it should add dirs recursively into the snapshot and care
        # of the items to report
        dirItems = set()
        for item in os.listdir(path):
            if self.__shouldExclude(item):
                continue
            if os.path.isdir(path + item):
                dirName = path + item + os.path.sep
                dirItems.add(item + os.path.sep)
                self.__processAddedDir(dirName, dirsToBeAdded, itemsToReport)
                continue
            itemsToReport.append("+" + path + item)
            dirItems.add(item)
        self.__fsSnapshot[path] = dirItems
        return

    def __processRemovedDir(self, path, dirsToBeRemoved, itemsToReport):
        """called for a disappeared dir in the project tree"""
        # it should remove the dirs recursively from the fs snapshot
        # and care of items to report
        dirsToBeRemoved.append(path)
        itemsToReport.append("-" + path)

        oldSet = self.__fsSnapshot[path]
        for item in oldSet:
            if item.endswith(os.path.sep):
                # Nested dir
                self.__processRemovedDir(path + item, dirsToBeRemoved,
                                         itemsToReport)
            else:
                # a file
                itemsToReport.append("-" + path + item)
        del self.__fsSnapshot[path]
        return

    def __processRemoveTopDir(self, path, dirsToBeRemoved, itemsToReport):
        """Called for a disappeared top level dir"""
        if path in self.__fsTopLevelSnapshot:
            # It is still a top level dir
            dirsToBeRemoved.append(path)
            for item in self.__fsTopLevelSnapshot[path]:
                self.__processRemoveTopDir(path + item, dirsToBeRemoved,
                                           itemsToReport)
            del self.__fsTopLevelSnapshot[path]
        else:
            # This is a project level dir
            self.__processRemovedDir(path, dirsToBeRemoved,
                                     itemsToReport)
        return

    def reset(self):
        """Resets the watcher (it does not report any changes)"""
        self.__dirWatcher.removePaths(self.__dirWatcher.directories())

        self.__srcDirsToWatch = set()

        self.__fsTopLevelSnapshot = {}
        self.__fsSnapshot = {}

        self.__dirsToWatch = set()
        self.__topLevelDirsToWatch = set()

    def registerDir(self, path):
        """Adds a directory to the list of watched ones"""
        if not path.endswith(os.path.sep):
            path = path + os.path.sep

        if path in self.__srcDirsToWatch:
            return  # It is there already

        # It is necessary to do the following:
        # - add the dir to the fs snapshot
        # - collect dirs to add to the watcher
        # - collect items to report
        self.__srcDirsToWatch.add(path)

        dirsToWatch = set()
        itemsToReport = []
        self.__registerDir(path, dirsToWatch, itemsToReport)

        # It might be that top level dirs should be updated too
        newTopLevelDirsToWatch = self.__buildTopDirsList(self.__srcDirsToWatch)
        addedDirs = newTopLevelDirsToWatch - self.__topLevelDirsToWatch

        for item in addedDirs:
            dirsToWatch.add(item)

            # Identify items to be watched by this dir
            dirItems = set()
            for candidate in newTopLevelDirsToWatch | self.__srcDirsToWatch:
                if len(candidate) <= len(item):
                    continue
                if candidate.startswith(item):
                    candidate = candidate[len(item):]
                    slashIndex = candidate.find(os.path.sep) + 1
                    dirName = candidate[:slashIndex]
                    if os.path.exists(item + dirName):
                        dirItems.add(dirName)
            # Update the top level dirs snapshot
            self.__fsTopLevelSnapshot[item] = dirItems

        # Update the top level snapshot with the added dir
        upperDir = os.path.dirname(path[:-1]) + os.path.sep
        dirName = path.replace(upperDir, '')
        self.__fsTopLevelSnapshot[upperDir].add(dirName)

        # Update the list of top level dirs to watch
        self.__topLevelDirsToWatch = newTopLevelDirsToWatch

        # Update the watcher
        if dirsToWatch:
            dirs = []
            for item in dirsToWatch:
                dirs.append(item)
            self.__dirWatcher.addPaths(dirs)

        # Report the changes
        if itemsToReport:
            self.sigFSChanged.emit(itemsToReport)

        # self.debug()
        return

    def __registerDir(self, path, dirsToWatch, itemsToReport):
        """Adds one path to the FS snapshot"""
        if not os.path.exists(path):
            return

        dirsToWatch.add(path)
        itemsToReport.append("+" + path)

        dirItems = set()
        for item in os.listdir(path):
            if self.__shouldExclude(item):
                continue
            if os.path.isdir(path + item):
                dirName = path + item + os.path.sep
                dirItems.add(item + os.path.sep)
                itemsToReport.append("+" + path + item + os.path.sep)
                self.__addSnapshotPath(dirName, dirsToWatch, itemsToReport)
                continue
            dirItems.add(item)
            itemsToReport.append("+" + path + item)
        self.__fsSnapshot[path] = dirItems

    def deregisterDir(self, path):
        """Removes the directory from the list of the watched ones"""
        if not path.endswith(os.path.sep):
            path = path + os.path.sep

        if path not in self.__srcDirsToWatch:
            return  # It is not there already
        self.__srcDirsToWatch.remove(path)

        # It is necessary to do the following:
        # - remove the dir from the fs snapshot
        # - collect the dirs to be removed from watching
        # - collect item to report

        itemsToReport = []
        dirsToBeRemoved = []

        self.__deregisterDir(path, dirsToBeRemoved, itemsToReport)

        # It is possible that some of the top level watched dirs should be
        # removed as well
        newTopLevelDirsToWatch = self.__buildTopDirsList(self.__srcDirsToWatch)
        deletedDirs = self.__topLevelDirsToWatch - newTopLevelDirsToWatch

        for item in deletedDirs:
            dirsToBeRemoved.append(item)
            del self.__fsTopLevelSnapshot[item]

        # It might be the case that some of the items should be deleted in the
        # top level dirs sets
        for dirName in self.__fsTopLevelSnapshot:
            itemsSet = self.__fsTopLevelSnapshot[dirName]
            for item in itemsSet:
                candidate = dirName + item
                if candidate == path or candidate in deletedDirs:
                    itemsSet.remove(item)
                    self.__fsTopLevelSnapshot[dirName] = itemsSet
                    break

        # Update the list of dirs to be watched
        self.__topLevelDirsToWatch = newTopLevelDirsToWatch

        # Update the watcher
        if dirsToBeRemoved:
            self.__dirWatcher.removePaths(dirsToBeRemoved)

        # Report the changes
        if itemsToReport:
            self.sigFSChanged.emit(itemsToReport)

        # self.debug()

    def __deregisterDir(self, path, dirsToBeRemoved, itemsToReport):
        """Deregisters a directory recursively"""
        dirsToBeRemoved.append(path)
        itemsToReport.append("-" + path)
        if path in self.__fsTopLevelSnapshot:
            # This is a top level dir
            for item in self.__fsTopLevelSnapshot[path]:
                if item.endswith(os.path.sep):
                    # It's a dir
                    self.__deregisterDir(path + item, dirsToBeRemoved,
                                         itemsToReport)
                else:
                    # It's a file
                    itemsToReport.append("-" + path + item)
            del self.__fsTopLevelSnapshot[path]
            return

        # It is from an a project level snapshot
        if path in self.__fsSnapshot:
            for item in self.__fsSnapshot[path]:
                if item.endswith(os.path.sep):
                    # It's a dir
                    self.__deregisterDir(path + item, dirsToBeRemoved,
                                         itemsToReport)
                else:
                    # It's a file
                    itemsToReport.append("-" + path + item)
            del self.__fsSnapshot[path]
        return

    def debug(self):
        """Debugging printouts"""
        print("Top level dirs to watch: " + str(self.__topLevelDirsToWatch))
        print("Project dirs to watch: " + str(self.__dirsToWatch))

        print("Top level snapshot: " + str(self.__fsTopLevelSnapshot))
        print("Project snapshot: " + str(self.__fsSnapshot))
