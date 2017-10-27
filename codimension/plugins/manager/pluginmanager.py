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

"""Codimension plugin manager"""

import logging
import os.path
import sys
from ui.qt import QObject, pyqtSignal
from yapsy.PluginManager import PluginManager
from utils.settings import SETTINGS_DIR, Settings
from distutils.version import StrictVersion


# List of the supported plugin categories, i.e. base class names
CATEGORIES = ["VersionControlSystemInterface",
              "WizardInterface"]

VENV_PLUGINS_PATH = os.path.normpath(
    os.path.dirname(sys.argv[0]) + '/../cdmplugins')


class CDMPluginManager(PluginManager, QObject):

    """Implements the codimension plugin manager"""

    sigPluginActivated = pyqtSignal(object)
    sigPluginDeactivated = pyqtSignal(object)

    NO_CONFLICT = 0
    # Same name plugin in system and user locations
    SYSTEM_USER_CONFLICT = 1
    # Plugin required incompatible version
    INCOMPATIBLE_IDE_VERSION_CONFLICT = 2
    # Newer version of the same name plugin
    VERSION_CONFLICT = 3
    # Does not derive from any of the supported interface
    BAD_BASE_CLASS = 4
    # The plugin raised exception during activation
    BAD_ACTIVATION = 5
    # Exception on basic methods
    BAD_INTERFACE = 6
    USER_DISABLED = 7

    def __init__(self):
        QObject.__init__(self)
        PluginManager.__init__(self, None,
                               [SETTINGS_DIR + "plugins",
                                "/usr/share/codimension3-plugins",
                                VENV_PLUGINS_PATH], "cdmp")

        self.inactivePlugins = {}   # Categorized inactive plugins
        self.activePlugins = {}     # Categorized active plugins
        self.unknownPlugins = []    # Unknown plugins

    def load(self):
        """Loads the found plugins"""
        # Now, let's check the plugins. They must be of known category.
        collectedPlugins = self.__collect()
        self.__applyDisabledPlugins(collectedPlugins)

        self.__checkIDECompatibility(collectedPlugins)
        self.__sysVsUserConflicts(collectedPlugins)
        self.__categoryConflicts(collectedPlugins)
        self.__activatePlugins(collectedPlugins)

        self.saveDisabledPlugins()

    def __collect(self):
        """Checks that the plugins belong to what is known"""
        self.collectPlugins()

        collectedPlugins = {}
        for plugin in self.getAllPlugins():
            recognised = False
            baseClasses = getBaseClassNames(plugin.plugin_object)
            for category in CATEGORIES:
                if category in baseClasses:
                    # OK, this plugin base has been recognised
                    recognised = True
                    newPlugin = CDMPluginInfo(plugin)
                    newPlugin.categoryName = category
                    if category in collectedPlugins:
                        collectedPlugins[category].append(newPlugin)
                    else:
                        collectedPlugins[category] = [newPlugin]
                    break

            if not recognised:
                logging.warning("Plugin of an unknown category is found at: " +
                                plugin.path + ". The plugin is disabled.")
                newPlugin = CDMPluginInfo(plugin)
                newPlugin.conflictType = CDMPluginManager.BAD_BASE_CLASS
                newPlugin.conflictMessage = "The plugin does not derive any " \
                                            "known plugin category interface"
                self.unknownPlugins.append(newPlugin)

        return collectedPlugins

    def __activatePlugins(self, collectedPlugins):
        """Activating the plugins"""
        from utils.globals import GlobalData

        for category in collectedPlugins:
            for plugin in collectedPlugins[category]:
                try:
                    plugin.getObject().activate(Settings(), GlobalData())
                    if category in self.activePlugins:
                        self.activePlugins[category].append(plugin)
                    else:
                        self.activePlugins[category] = [plugin]
                    self.sendPluginActivated(plugin)
                except Exception as excpt:
                    logging.error("Error activating plugin at " +
                                  plugin.getPath() +
                                  ". The plugin disabled. Error message: \n" +
                                  str(excpt))
                    plugin.conflictType = CDMPluginManager.BAD_ACTIVATION
                    plugin.conflictMessage = "Error activating the plugin"
                    if category in self.inactivePlugins:
                        self.inactivePlugins[category].append(plugin)
                    else:
                        self.inactivePlugins[category] = [plugin]

    def __checkIDECompatibility(self, collectedPlugins):
        """Checks that the plugins can be used with the current IDE"""
        from utils.globals import GlobalData

        toBeRemoved = []
        for category in collectedPlugins:
            for plugin in collectedPlugins[category]:
                try:
                    ideVer = GlobalData().version
                    if not plugin.getObject().isIDEVersionCompatible(ideVer):
                        # The plugin is incompatible. Disable it
                        logging.warning("Plugin of an incompatible version "
                                        "is found at: " + plugin.getPath() +
                                        ". The plugin is disabled.")
                        plugin.conflictType = \
                            CDMPluginManager.INCOMPATIBLE_IDE_VERSION_CONFLICT
                        plugin.conflictMessage = "The IDE version does not " \
                            "meet the plugin requirements."
                        self.unknownPlugins.append(plugin)
                        toBeRemoved.append(plugin.getPath())
                except Exception as excpt:
                    # Could not successfully call the interface method
                    logging.error("Error checking IDE version compatibility "
                                  "of plugin at " + plugin.getPath() +
                                  ". The plugin disabled. Error message: \n" +
                                  str(excpt))
                    plugin.conflictType = CDMPluginManager.BAD_INTERFACE
                    plugin.conflictMessage = "Error checking IDE version " \
                                             "compatibility"
                    if category in self.inactivePlugins:
                        self.inactivePlugins[category].append(plugin)
                    else:
                        self.inactivePlugins[category] = [plugin]
                    toBeRemoved.append(plugin.getPath())

        for path in toBeRemoved:
            for category in collectedPlugins:
                for plugin in collectedPlugins[category]:
                    if plugin.getPath() == path:
                        collectedPlugins.remove(plugin)
                        break

    def __applyDisabledPlugins(self, collectedPlugins):
        """Marks the disabled plugins in accordance to settings"""
        for disabledPlugin in Settings()['disabledPlugins']:
            # Parse the record
            try:
                conflictType, path, conflictMessage = \
                    CDMPluginInfo.parseDisabledLine(disabledPlugin)
            except Exception as excpt:
                logging.warning(str(excpt))
                continue

            found = False
            for category in collectedPlugins:
                for plugin in collectedPlugins[category]:
                    if plugin.getPath() == path:
                        found = True
                        plugin.conflictType = conflictType
                        plugin.conflictMessage = conflictMessage
                        if category in self.inactivePlugins:
                            self.inactivePlugins[category].append(plugin)
                        else:
                            self.inactivePlugins[category] = [plugin]
                        collectedPlugins[category].remove(plugin)
                        break
                if found:
                    break

            if not found:
                # Second try - search through the unknown plugins
                for plugin in self.unknownPlugins:
                    if plugin.getPath() == path:
                        found = True
                        plugin.conflictType = conflictType
                        plugin.conflictMessage = conflictMessage
                        break

            if not found:
                logging.warning("The disabled plugin at " + path +
                                " has not been found. The information that"
                                " the plugin is disabled will be deleted.")

    def __sysVsUserConflicts(self, collectedPlugins):
        """Checks for the system vs user plugin conflicts"""
        for category in collectedPlugins:
            self.__sysVsUserCategoryConflicts(category,
                                              collectedPlugins[category])

    def __sysVsUserCategoryConflicts(self, category, plugins):
        """Checks for the system vs user conflicts within one category"""
        def findIndexesByName(plugins, name):
            """Provides the plugin index by name"""
            result = []
            for index in range(len(plugins)):
                if plugins[index].getName() == name:
                    result.append(index)
            return result

        def hasUserPlugin(plugins, indexes):
            """True if has user plugins"""
            for index in indexes:
                if plugins[index].isUser():
                    return True
            return False

        index = 0
        while index < len(plugins):
            name = plugins[index].getName()
            sameNamePluginIndexes = findIndexesByName(plugins, name)
            if hasUserPlugin(plugins, sameNamePluginIndexes):
                # There is at least one user plugin
                # Disable all system plugins
                sameNamePluginIndexes.reverse()
                for checkIndex in sameNamePluginIndexes:
                    if not plugins[checkIndex].isUser():
                        logging.warning("The system wide plugin '" + name +
                                        "' at " +
                                        plugins[checkIndex].getPath() +
                                        " conflicts with a user plugin with "
                                        "the same name. The system wide "
                                        "plugin is automatically disabled.")
                        plugins[checkIndex].conflictType = \
                            CDMPluginManager.SYSTEM_USER_CONFLICT
                        plugins[checkIndex].conflictMessage = \
                            "It conflicts with a user plugin of the same name"
                        if category in self.inactivePlugins:
                            self.inactivePlugins[category].append(
                                plugins[checkIndex])
                        else:
                            self.inactivePlugins[category] = \
                                [plugins[checkIndex]]
                        del plugins[checkIndex]
                if plugins[index].getName() == name:
                    index += 1
            else:
                index += 1

    def __categoryConflicts(self, collectedPlugins):
        """Checks for version conflicts within the category"""
        for category in collectedPlugins:
            self.__singleCategoryConflicts(category,
                                           collectedPlugins[category])

    def __singleCategoryConflicts(self, category, plugins):
        """Checks a single category for name conflicts"""
        def findIndexesByName(plugins, name):
            """Provides the plugin index by name"""
            result = []
            for index in range(len(plugins)):
                if plugins[index].getName() == name:
                    result.append(index)
            return result

        index = 0
        while index < len(plugins):
            name = plugins[index].getName()
            sameNamePluginIndexes = findIndexesByName(plugins, name)
            if len(sameNamePluginIndexes) == 1:
                # The only plugin of the type. Keep it.
                index += 1
            else:
                # There are many. Check the versions and decide which to remove
                self.__resolveConflictByVersion(category, plugins,
                                                sameNamePluginIndexes)

    def __resolveConflictByVersion(self, category, plugins, indexes):
        """Resolves a single version conflict"""
        indexVersion = []
        for index in indexes:
            indexVersion.append((index,
                                 StrictVersion(plugins[index].getVersion())))

        # Sort basing on version
        indexVersion.sort(key=lambda indexVer: indexVer[1])

        # Disable everything except the last
        highVersion = indexVersion[-1][1]
        toBeDisabled = []
        for index in range(len(indexVersion) - 1):
            pluginIndex = indexVersion[index][0]
            logging.warning("The plugin '" + plugins[pluginIndex].getName() +
                            "' v." + plugins[pluginIndex].getVersion() +
                            " at " +
                            os.path.normpath(plugins[pluginIndex].getPath()) +
                            " conflicts with another plugin of the same name "
                            "and version " + str(highVersion) +
                            ". The former is disabled automatically.")
            toBeDisabled.append(pluginIndex)

        # Move the disabled to the inactive list
        toBeDisabled.sort()
        toBeDisabled.reverse()
        for index in toBeDisabled:
            plugins[index].conflictType = CDMPluginManager.VERSION_CONFLICT
            plugins[index].conflictMessage = \
                "It conflicts with another plugin of the same name"
            if category in self.inactivePlugins:
                self.inactivePlugins[category].append(plugins[index])
            else:
                self.inactivePlugins[category] = [plugins[index]]
            del plugins[index]

    def saveDisabledPlugins(self):
        """Saves the disabled plugins info into the settings"""
        value = []
        for category in self.inactivePlugins:
            for plugin in self.inactivePlugins[category]:
                line = plugin.getDisabledLine()
                if line is not None:
                    value.append(line)
        for plugin in self.unknownPlugins:
            line = plugin.getDisabledLine()
            if line is not None:
                value.append(line)
        Settings()['disabledPlugins'] = value

    def checkConflict(self, cdmPlugin):
        """Checks for the conflict and returns a message if so.

        If there is no conflict then returns None
        """
        # First, check the base class
        baseClasses = getBaseClassNames(cdmPlugin.getObject())
        category = None
        for registeredCategory in CATEGORIES:
            if registeredCategory in baseClasses:
                category = registeredCategory
                break
        if category is None:
            return "Plugin category is not recognised"

        # Second, IDE version compatibility
        from utils.globals import GlobalData
        try:
            ideVer = GlobalData().version
            if not cdmPlugin.getObject().isIDEVersionCompatible(ideVer):
                return "Plugin requires the other IDE version"
        except:
            # Could not successfully call the interface method
            return "Error checking IDE version compatibility"

        # Third, the other plugin with the same name is active
        if category in self.activePlugins:
            for plugin in self.activePlugins[category]:
                if plugin.getName() == cdmPlugin.getName():
                    return "Another plugin of the same name is active"

        return None

    def sendPluginActivated(self, plugin):
        """Emits the signal with the corresponding plugin"""
        self.sigPluginActivated.emit(plugin)
        plugin.getObject().pluginLogMessage.connect(self.__onPluginLogMessage)

    def sendPluginDeactivated(self, plugin):
        """Emits the signal with the corresponding plugin"""
        plugin.getObject().pluginLogMessage.disconnect(
            self.__onPluginLogMessage)
        self.sigPluginDeactivated.emit(plugin)

    @staticmethod
    def __onPluginLogMessage(logLevel, message):
        """Triggered when a plugin message is received"""
        logging.log(logLevel, str(message))


class CDMPluginInfo:

    """Holds info about a single plugin"""

    def __init__(self, pluginInfo):
        """The pluginInfo comes from yapsy"""
        # yapsy.PluginInfo
        self.__info = pluginInfo
        self.__isUser = self.__isUserPlugin()
        self.isEnabled = False
        # See CDMPluginManager constants
        self.conflictType = CDMPluginManager.NO_CONFLICT
        # One line message for UI/log
        self.conflictMessage = ""
        self.categoryName = None

    def isUser(self):
        """True if it is a user plugin"""
        return self.__isUser

    def __isUserPlugin(self):
        """True if it is a user plugin"""
        return self.getPath().startswith(SETTINGS_DIR)

    def getDisabledLine(self):
        """Used for the setting file"""
        if self.isEnabled is None or self.isEnabled:
            return None
        return str(self.conflictType) + ":::" + \
            self.__info.path + ":::" + \
            self.conflictMessage

    @staticmethod
    def parseDisabledLine(configLine):
        """Parser the config line and returns a tuple"""
        parts = configLine.split(":::", 2)
        if len(parts) != 3:
            raise ValueError("Incorrect disabled plugin description: " +
                             configLine)
        # (conflictType, path, conflictMessage)
        return (int(parts[0]), parts[1], parts[2])

    def getObject(self):
        """Provides a reference to the plugin object"""
        return self.__info.plugin_object

    def getPath(self):
        """Provides the plugin path"""
        return str(self.__info.path)

    def getName(self):
        """Provides the plugin name"""
        return str(self.__info.name)

    def getVersion(self):
        """Provides the plugin version"""
        return self.__info.details.get("Documentation", "Version")

    def getAuthor(self):
        """Provides the author name"""
        return self.__info.details.get("Documentation", "Author")

    def getDescription(self):
        """Provides the description"""
        return self.__info.details.get("Documentation", "Description")

    def getWebsite(self):
        """Provides the website"""
        return self.__info.details.get("Documentation", "Website")

    def getCopyright(self):
        """Provides the copyright"""
        return self.__info.details.get("Documentation", "Copyright")

    def getDetails(self):
        """Provides additional values from from the description section"""
        result = {}
        for name, value in self.__info.details.items("Documentation"):
            if name.lower() in ["version", "author", "description",
                                "website", "copyright"]:
                continue
            result[name] = value
        return result

    def disable(self, conflictType=CDMPluginManager.USER_DISABLED,
                conflictMessage=""):
        """Disables the plugin"""
        self.isEnabled = False
        self.conflictType = conflictType
        self.conflictMessage = conflictMessage

        if self.getObject().is_activated:
            if self.categoryName == "VersionControlSystemInterface":
                from utils.globals import GlobalData
                GlobalData().mainWindow.dismissVCSPlugin(self)
            self.getObject().deactivate()

    def enable(self):
        """Enables the plugin"""
        if not self.getObject().is_activated:
            from utils.globals import GlobalData
            self.getObject().activate(Settings(), GlobalData())

        self.isEnabled = True
        self.conflictType = CDMPluginManager.NO_CONFLICT
        self.conflictMessage = ""


def getBaseClassNames(inst):
    """Provides a list of base class names for the given instance"""
    baseNames = []

    def baseClassNames(inst, names):
        """Recursive retriever"""
        if hasattr(inst, "__bases__"):
            container = inst.__bases__
        else:
            container = inst.__class__.__bases__
        for base in container:
            names.append(base.__name__)
            if base.__name__ != "object":
                baseClassNames(base, names)
        return

    baseClassNames(inst, baseNames)
    return baseNames
