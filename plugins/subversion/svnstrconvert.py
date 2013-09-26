#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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
# $Id$
#

" Subversion plugin string conversion facilities "

import pysvn
from datetime import datetime

from svnindicators import ( IND_ADDED, IND_DELETED, IND_IGNORED, IND_MERGED,
                            IND_MODIFIED_LR, IND_MODIFIED_L, IND_MODIFIED_R,
                            IND_UPTODATE, IND_REPLACED, IND_CONFLICTED,
                            IND_EXTERNAL, IND_INCOMPLETE, IND_MISSING,
                            IND_OBSTRUCTED, IND_UNKNOWN, IND_ERROR )
from plugins.categories.vcsiface import VersionControlSystemInterface


NODE_KIND = { pysvn.node_kind.file : "file",
              pysvn.node_kind.dir  : "directory",
              pysvn.node_kind.none : "absent" }

def nodeKindToString( kind ):
    " Converts node kind into a string"
    if kind in NODE_KIND:
        return NODE_KIND[ kind ]
    return "unknown"


SCHEDULE = { pysvn.wc_schedule.normal  : "normal",
             pysvn.wc_schedule.add     : "add",
             pysvn.wc_schedule.delete  : "delete",
             pysvn.wc_schedule.replace : "replace" }


def scheduleToString( schedule ):
    " Converts schedule to string "
    if schedule in SCHEDULE:
        return SCHEDULE[ schedule ]
    return "unknown"


STATUS = { IND_ADDED       : "added",
           IND_DELETED     : "deleted",
           IND_IGNORED     : "ignored",
           IND_MERGED      : "merged",
           IND_MODIFIED_LR : "modified locally and in repository",
           IND_MODIFIED_L  : "modified locally",
           IND_MODIFIED_R  : "modified in repository",
           IND_UPTODATE    : "up to date",
           IND_REPLACED    : "replaced",
           IND_CONFLICTED  : "conflicted",
           IND_EXTERNAL    : "external",
           IND_INCOMPLETE  : "incomplete entries list",
           IND_MISSING     : "missing",
           IND_UNKNOWN     : "unknown",
           IND_ERROR       : "error getting status",
           VersionControlSystemInterface.NOT_UNDER_VCS: "not under SVN control" }

def statusToString( status ):
    " Converts status to string "
    if status in STATUS:
        return STATUS[ status ]
    return "unknown"


def timestampToString( value ):
    """ Converts a pysvn time value (float) into a human readable.
        Fraction of seconds is ommitted """

    timestamp = datetime.fromtimestamp( int( value ) )
    return timestamp.strftime( "%Y-%m-%d %H:%M:%S" )


ACTION = { pysvn.wc_notify_action.add: "adding",
           pysvn.wc_notify_action.annotate_revision: "",
           pysvn.wc_notify_action.changelist_clear: "",
           pysvn.wc_notify_action.changelist_moved: "",
           pysvn.wc_notify_action.changelist_set: "",
           pysvn.wc_notify_action.commit_added: "",
           pysvn.wc_notify_action.commit_copied: "",
           pysvn.wc_notify_action.commit_copied_replaced: "",
           pysvn.wc_notify_action.commit_deleted: "",
           pysvn.wc_notify_action.commit_modified: "",
           pysvn.wc_notify_action.commit_postfix_txdelta: "",
           pysvn.wc_notify_action.commit_replaced: "",
           pysvn.wc_notify_action.copy: "",
           pysvn.wc_notify_action.delete: "",
           pysvn.wc_notify_action.exclude: "",
           pysvn.wc_notify_action.exists: "",
           pysvn.wc_notify_action.failed_conflict: "",
           pysvn.wc_notify_action.failed_external: "",
           pysvn.wc_notify_action.failed_lock: "",
           pysvn.wc_notify_action.failed_missing: "",
           pysvn.wc_notify_action.failed_no_parent: "",
           pysvn.wc_notify_action.failed_out_of_date: "",
           pysvn.wc_notify_action.failed_revert: "",
           pysvn.wc_notify_action.failed_unlock: "",
           pysvn.wc_notify_action.foreign_merge_begin: "",
           pysvn.wc_notify_action.locked: "",
           pysvn.wc_notify_action.merge_begin: "",
           pysvn.wc_notify_action.merge_completed: "",
           pysvn.wc_notify_action.merge_elide_info: "",
           pysvn.wc_notify_action.merge_record_info: "",
           pysvn.wc_notify_action.merge_record_info_begin: "",
           pysvn.wc_notify_action.patch: "",
           pysvn.wc_notify_action.patch_applied_hunk: "",
           pysvn.wc_notify_action.patch_hunk_already_applied: "",
           pysvn.wc_notify_action.patch_rejected_hunk: "",
           pysvn.wc_notify_action.path_nonexistent: "",
           pysvn.wc_notify_action.property_added: "",
           pysvn.wc_notify_action.property_deleted: "",
           pysvn.wc_notify_action.property_deleted_nonexistent: "",
           pysvn.wc_notify_action.property_modified: "",
           pysvn.wc_notify_action.resolved: "",
           pysvn.wc_notify_action.restore: "",
           pysvn.wc_notify_action.revert: "",
           pysvn.wc_notify_action.revprop_deleted: "",
           pysvn.wc_notify_action.revprop_set: "",
           pysvn.wc_notify_action.skip: "",
           pysvn.wc_notify_action.status_completed: "",
           pysvn.wc_notify_action.status_external: "",
           pysvn.wc_notify_action.tree_conflict: "",
           pysvn.wc_notify_action.unlocked: "",
           pysvn.wc_notify_action.update_add: "",
           pysvn.wc_notify_action.update_completed: "",
           pysvn.wc_notify_action.update_delete: "",
           pysvn.wc_notify_action.update_external: "",
           pysvn.wc_notify_action.update_external_removed: "",
           pysvn.wc_notify_action.update_replace: "",
           pysvn.wc_notify_action.update_shadowed_add: "",
           pysvn.wc_notify_action.update_shadowed_delete: "",
           pysvn.wc_notify_action.update_shadowed_update: "",
           pysvn.wc_notify_action.update_skip_obstruction: "",
           pysvn.wc_notify_action.update_skip_working_only: "",
           pysvn.wc_notify_action.update_started: "",
           pysvn.wc_notify_action.update_update: "",
           pysvn.wc_notify_action.upgraded_path: "",
           pysvn.wc_notify_action.url_redirect: "" }



def notifyActionToString( action ):
    " Converts the action to a string "
    if action in ACTION:
        return ACTION[ action ]
    return "unknown"

