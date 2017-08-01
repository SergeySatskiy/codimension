# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Codimension SVN plugin implementation"""

from ui.qt import QMutex, QDialog, pyqtSignal
from copy import deepcopy
import svn
import os.path
from plugins.categories.vcsiface import VersionControlSystemInterface
from .svnmenus import SVNMenuMixin
from .svnconfigdlg import (SVNPluginConfigDialog, saveSVNSettings, getSettings,
                           AUTH_PASSWD, STATUS_LOCAL_ONLY)
from .svnindicators import (IND_ADDED, IND_ERROR, IND_DELETED, IND_IGNORED,
                            IND_MERGED, IND_MODIFIED_LR, IND_MODIFIED_L,
                            IND_MODIFIED_R, IND_UPTODATE, IND_REPLACED,
                            IND_CONFLICTED, IND_EXTERNAL, IND_INCOMPLETE,
                            IND_MISSING, IND_OBSTRUCTED, IND_UNKNOWN,
                            IND_DESCRIPTION)
from .svninfo import SVNInfoMixin
from .svnupdate import SVNUpdateMixin
from .svnannotate import SVNAnnotateMixin
from .svncommit import SVNCommitMixin
from .svnadd import SVNAddMixin
from .svnstatus import SVNStatusMixin
from .svndelete import SVNDeleteMixin
from .svndiff import SVNDiffMixin
from .svnrevert import SVNRevertMixin
from .svnlog import SVNLogMixin
from .svnprops import SVNPropsMixin


class SubversionPlugin(SVNMenuMixin, SVNInfoMixin, SVNAddMixin, SVNCommitMixin,
                       SVNDeleteMixin, SVNDiffMixin, SVNRevertMixin,
                       SVNUpdateMixin, SVNAnnotateMixin, SVNStatusMixin,
                       SVNLogMixin, SVNPropsMixin,
                       VersionControlSystemInterface):

    """Codimension subversion plugin"""

    PathChanged = pyqtSignal(str)

    def __init__(self):
        VersionControlSystemInterface.__init__(self)
        SVNInfoMixin.__init__(self)
        SVNAddMixin.__init__(self)
        SVNCommitMixin.__init__(self)
        SVNDeleteMixin.__init__(self)
        SVNDiffMixin.__init__(self)
        SVNRevertMixin.__init__(self)
        SVNUpdateMixin.__init__(self)
        SVNAnnotateMixin.__init__(self)
        SVNStatusMixin.__init__(self)
        SVNLogMixin.__init__(self)
        SVNPropsMixin.__init__(self)
        SVNMenuMixin.__init__(self)

        self.projectSettings = None
        self.ideWideSettings = None
        self.__settingsLock = QMutex()

        self.fileParentMenu = None
        self.dirParentMenu = None

    @staticmethod
    def isIDEVersionCompatible(ideVersion):
        """SVN Plugin is compatible with any IDE version"""
        return True

    @staticmethod
    def getVCSName():
        """Should provide the specific version control name, e.g. SVN"""
        return "SVN"

    def activate(self, ideSettings, ideGlobalData):
        """Called when the plugin is activated"""
        VersionControlSystemInterface.activate(self, ideSettings,
                                               ideGlobalData)

        # Read the settings
        self.ideWideSettings = getSettings(self.__getIDEConfigFile())
        if self.ide.project.isLoaded():
            self.projectSettings = getSettings(self.__getProjectConfigFile())
        self.ide.project.sigProjectChanged.connect(self.__onProjectChanged)

    def deactivate(self):
        """Called when the plugin is deactivated"""
        self.ide.project.sigProjectChanged.disconnect(self.__onProjectChanged)

        self.projectSettings = None
        self.ideWideSettings = None

        VersionControlSystemInterface.deactivate(self)

    def getConfigFunction(self):
        """SVN plugin requires configuring"""
        return self.configure

    def __getIDEConfigFile(self):
        """Provides a name of the IDE wide config file"""
        return self.ide.settingsDir + "svn.plugin.conf"

    def __getProjectConfigFile(self):
        """Provides a name of the project config file"""
        return self.ide.projectSettingsDir + "svn.plugin.conf"

    def configure(self):
        " Configures the SVN plugin "
        dlg = SVNPluginConfigDialog(self.ideWideSettings,
                                    self.projectSettings)
        if dlg.exec_() == QDialog.Accepted:
            # Save the settings if they have changed
            self.__settingsLock.lock()
            if self.ideWideSettings != dlg.ideWideSettings:
                self.ideWideSettings = dlg.ideWideSettings
                saveSVNSettings(self.ideWideSettings,
                                self.__getIDEConfigFile())
            if self.projectSettings is not None:
                if self.projectSettings != dlg.projectSettings:
                    self.projectSettings = dlg.projectSettings
                    saveSVNSettings(self.projectSettings,
                                    self.__getProjectConfigFile())
            self.__settingsLock.unlock()

    def notifyPathChanged(self, path):
        """Sends notifications to the IDE that a path was changed"""
        self.PathChanged.emit(path)

    def __onProjectChanged(self, what):
        """Triggers when a project has changed"""
        if what != self.ide.project.CompleteProject:
            return

        if self.ide.project.isLoaded():
            self.__settingsLock.lock()
            self.projectSettings = getSettings(self.__getProjectConfigFile())
            self.__settingsLock.unlock()
        else:
            self.__settingsLock.lock()
            self.projectSettings = None
            self.__settingsLock.unlock()

    def getCustomIndicators(self):
        """Provides custom indicators if needed"""
        return IND_DESCRIPTION

    def getSettings(self):
        """Thread safe settings copy"""
        if self.ide.project.isLoaded():
            self.__settingsLock.lock()
            settings = deepcopy(self.projectSettings)
            self.__settingsLock.unlock()
            return settings

        self.__settingsLock.lock()
        settings = deepcopy(self.ideWideSettings)
        self.__settingsLock.unlock()
        return settings

    def getSVNClient(self, settings):
        """Creates the SVN client object"""
        client = pysvn.Client()
        client.exception_style = 1   # In order to get error codes
        client.callback_get_login = self._getLoginCallback
        return client

    def _getLoginCallback(self, realm, username, may_save):
        """SVN client calls it when authorization is requested"""
        settings = self.getSettings()
        if settings.authKind == AUTH_PASSWD:
            return (True, settings.userName, settings.password, False)
        return (False, "", "", False)

    def convertSVNStatus(self, status):
        """Converts the status between the SVN and
           the plugin supported values"""
        if status.text_status == pysvn.wc_status_kind.added:
            return IND_ADDED
        if status.text_status == pysvn.wc_status_kind.deleted:
            return IND_DELETED
        if status.text_status == pysvn.wc_status_kind.ignored:
            return IND_IGNORED
        if status.text_status == pysvn.wc_status_kind.merged:
            return IND_MERGED
        if status.text_status == pysvn.wc_status_kind.modified:
            if status.repos_text_status == pysvn.wc_status_kind.modified or \
               status.repos_prop_status == pysvn.wc_status_kind.modified:
                return IND_MODIFIED_LR
            return IND_MODIFIED_L
        if status.text_status == pysvn.wc_status_kind.normal:
            if status.repos_text_status == pysvn.wc_status_kind.modified or \
               status.repos_prop_status == pysvn.wc_status_kind.modified:
                return IND_MODIFIED_R
            if status.prop_status == pysvn.wc_status_kind.modified:
                return IND_MODIFIED_L
            return IND_UPTODATE
        if status.text_status == pysvn.wc_status_kind.replaced:
            return IND_REPLACED
        if status.text_status == pysvn.wc_status_kind.conflicted:
            return IND_CONFLICTED
        if status.text_status == pysvn.wc_status_kind.external:
            return IND_EXTERNAL
        if status.text_status == pysvn.wc_status_kind.incomplete:
            return IND_INCOMPLETE
        if status.text_status == pysvn.wc_status_kind.missing:
            return IND_MISSING
        if status.text_status == pysvn.wc_status_kind.none:
            return self.NOT_UNDER_VCS
        if status.text_status == pysvn.wc_status_kind.obstructed:
            return IND_OBSTRUCTED
        if status.text_status == pysvn.wc_status_kind.unversioned:
            return self.NOT_UNDER_VCS

        return IND_UNKNOWN

    def getStatus(self, path, flag):
        """Provides VCS statuses for the path"""
        settings = self.getSettings()
        client = self.getSVNClient(settings)

        clientUpdate = settings.statusKind != STATUS_LOCAL_ONLY

        if flag == self.REQUEST_RECURSIVE:
            clientDepth = pysvn.depth.infinity
        elif flag == self.REQUEST_ITEM_ONLY:
            # Heck! By some reasons if depth empty AND update is True
            # the request returns nothing
            if path.endswith(os.path.sep):
                clientDepth = pysvn.depth.empty
            else:
                clientDepth = pysvn.depth.unknown
        else:
            clientDepth = pysvn.depth.files

        try:
            statusList = client.status(path, update=clientUpdate,
                                       depth=clientDepth)
            # Another heck! If a directory is not under VCS and the depth is
            # not empty then the result set is empty! I have no ideas why.
            if not statusList:
                # Try again, may be it is because the depth
                statusList = client.status(path, update=clientUpdate,
                                           depth=pysvn.depth.empty)
            # And another heck! If a directory is not under VCS even empty
            # depth may not help. Sometimes an empty list is returned because
            # update is set to True. Try without update as the last resort.
            if not statusList and clientUpdate:
                statusList = client.status(path, update=False,
                                           depth=pysvn.depth.empty)

            result = []
            for status in statusList:
                reportPath = status.path
                if not status.path.endswith(os.path.sep):
                    if status.entry is None:
                        if os.path.isdir(status.path):
                            reportPath += os.path.sep
                    elif status.entry.kind == pysvn.node_kind.dir:
                        reportPath += os.path.sep

                result.append((reportPath.replace(path, ""),
                               self.convertSVNStatus(status), None))
            return result
        except pysvn.ClientError as exc:
            errorCode = exc.args[1][0][1]
            if errorCode == pysvn.svn_err.wc_not_working_copy:
                return (("", self.NOT_UNDER_VCS, None),)
            message = exc.args[0]
            return (("", IND_ERROR, message),)
        except Exception as exc:
            return (("", IND_ERROR, "Error: " + str(exc)),)
        except:
            return (("", IND_ERROR, "Unknown error"),)

    def getLocalStatus(self, path, pDepth=None):
        """Provides quick local SVN status for the item itself"""
        client = self.getSVNClient(self.getSettings())
        try:
            statusList = client.status(path, update=False, depth=pDepth)
            if pDepth != pysvn.depth.empty and len(statusList) == 0:
                statusList = client.status(path, update=False,
                                           depth=pysvn.depth.empty)
            statusCount = len(statusList)
            if pDepth == pysvn.depth.empty and statusCount != 1:
                return IND_ERROR
            if statusCount == 1:
                return self.convertSVNStatus(statusList[0])
            # It is a list of statuses
            res = []
            for status in statusList:
                res.append((status.path, self.convertSVNStatus(status)))
            return res
        except pysvn.ClientError as exc:
            errorCode = exc.args[1][0][1]
            if errorCode == pysvn.svn_err.wc_not_working_copy:
                return self.NOT_UNDER_VCS
            # message = exc.args[0]
            return IND_ERROR
        except Exception as exc:
            return IND_ERROR
        except:
            return IND_ERROR
