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
           IND_OBSTRUCTED  : "obstructed by another item",
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


ACTION = { pysvn.wc_notify_action.add: "add",
           pysvn.wc_notify_action.annotate_revision: "annotate revision",
           pysvn.wc_notify_action.changelist_clear: "changelist clear",
           pysvn.wc_notify_action.changelist_moved: "changelist moved",
           pysvn.wc_notify_action.changelist_set: "changelist set",
           pysvn.wc_notify_action.commit_added: "added",
           pysvn.wc_notify_action.commit_copied: "copied",
           pysvn.wc_notify_action.commit_copied_replaced: "copied replaced",
           pysvn.wc_notify_action.commit_deleted: "deleted",
           pysvn.wc_notify_action.commit_modified: "modified",
           pysvn.wc_notify_action.commit_postfix_txdelta: None,
           pysvn.wc_notify_action.commit_replaced: "repolaced",
           pysvn.wc_notify_action.copy: "copy",
           pysvn.wc_notify_action.delete: "delete",
           pysvn.wc_notify_action.exclude: "exclude",
           pysvn.wc_notify_action.exists: "exists",
           pysvn.wc_notify_action.failed_conflict: "failed conflict",
           pysvn.wc_notify_action.failed_external: "failed external",
           pysvn.wc_notify_action.failed_lock: "failed lock",
           pysvn.wc_notify_action.failed_missing: "failed missing",
           pysvn.wc_notify_action.failed_no_parent: "failed no parent",
           pysvn.wc_notify_action.failed_out_of_date: "failed out of date",
           pysvn.wc_notify_action.failed_revert: "failed revert",
           pysvn.wc_notify_action.failed_unlock: "failed unlock",
           pysvn.wc_notify_action.foreign_merge_begin: "foreign merge begin",
           pysvn.wc_notify_action.locked: "locked",
           pysvn.wc_notify_action.merge_begin: "merge begin",
           pysvn.wc_notify_action.merge_completed: "merge completed",
           pysvn.wc_notify_action.merge_elide_info: "merge elide info",
           pysvn.wc_notify_action.merge_record_info: "merge record info",
           pysvn.wc_notify_action.merge_record_info_begin: "merge record info begin",
           pysvn.wc_notify_action.patch: "patch",
           pysvn.wc_notify_action.patch_applied_hunk: "patch applied hunk",
           pysvn.wc_notify_action.patch_hunk_already_applied: "patch hunk already applied",
           pysvn.wc_notify_action.patch_rejected_hunk: "patch rejected hunk",
           pysvn.wc_notify_action.path_nonexistent: "path nonexistent",
           pysvn.wc_notify_action.property_added: "property added",
           pysvn.wc_notify_action.property_deleted: "property deleted",
           pysvn.wc_notify_action.property_deleted_nonexistent: "property deleted nonexistent",
           pysvn.wc_notify_action.property_modified: "property modified",
           pysvn.wc_notify_action.resolved: "resolved",
           pysvn.wc_notify_action.restore: "restore",
           pysvn.wc_notify_action.revert: "revert",
           pysvn.wc_notify_action.revprop_deleted: "revprop deleted",
           pysvn.wc_notify_action.revprop_set: "revprop set",
           pysvn.wc_notify_action.skip: "skip",
           pysvn.wc_notify_action.status_completed: "status completed",
           pysvn.wc_notify_action.status_external: "status external",
           pysvn.wc_notify_action.tree_conflict: "tree conflict",
           pysvn.wc_notify_action.unlocked: "unlocked",
           pysvn.wc_notify_action.update_add: "update add",
           pysvn.wc_notify_action.update_completed: "update completed",
           pysvn.wc_notify_action.update_delete: "update delete",
           pysvn.wc_notify_action.update_external: "update external",
           pysvn.wc_notify_action.update_external_removed: "update external removed",
           pysvn.wc_notify_action.update_replace: "update replace",
           pysvn.wc_notify_action.update_shadowed_add: "update shadowed add",
           pysvn.wc_notify_action.update_shadowed_delete: "update shadowed delete",
           pysvn.wc_notify_action.update_shadowed_update: "update shadowed update",
           pysvn.wc_notify_action.update_skip_obstruction: "update skip obstruction",
           pysvn.wc_notify_action.update_skip_working_only: "update skip working only",
           pysvn.wc_notify_action.update_started: "update started",
           pysvn.wc_notify_action.update_update: "update",
           pysvn.wc_notify_action.upgraded_path: "upgraded path",
           pysvn.wc_notify_action.url_redirect: "url redirect" }



def notifyActionToString( action ):
    " Converts the action to a string "
    if action in ACTION:
        return ACTION[ action ]
    return "unknown"

