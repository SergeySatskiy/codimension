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


def nodeKindToString( kind ):
    " Converts node kind into a string"
    if kind == pysvn.node_kind.file:
        return "file"
    if kind == pysvn.node_kind.dir:
        return "directory"
    if kind == pysvn.node_kind.none:
        return "absent"
    return "unknown"


def scheduleToString( schedule ):
    " Converts schedule to string "
    if schedule == pysvn.wc_schedule.normal:
        return "normal"
    if schedule == pysvn.wc_schedule.add:
        return "add"
    if schedule == pysvn.wc_schedule.delete:
        return "delete"
    if schedule == pysvn.wc_schedule.replace:
        return "replace"
    return "unknown"


def statusToString( status ):
    " Converts status to string "
    if status == IND_ADDED:
        return "added"
    if status == IND_DELETED:
        return "deleted"
    if status == IND_IGNORED:
        return "ignored"
    if status == IND_MERGED:
        return "merged"
    if status == IND_MODIFIED_LR:
        return "modified locally and in repository"
    if status == IND_MODIFIED_L:
        return "modified locally"
    if status == IND_MODIFIED_R:
        return "modified in repository"
    if status == IND_UPTODATE:
        return "up to date"
    if status == IND_REPLACED:
        return "replaced"
    if status == IND_CONFLICTED:
        return "conflicted"
    if status == IND_EXTERNAL:
        return "external"
    if status == IND_INCOMPLETE:
        return "incomplete entries list"
    if status == IND_MISSING:
        return "missing"
    if status == IND_OBSTRUCTED:
        return "obstructed"
    if status == IND_UNKNOWN:
        return "unknown"
    if status == IND_ERROR:
        return "error getting status"
    if status == VersionControlSystemInterface.NOT_UNDER_VCS:
        return "not under SVN control"

    return "unknown"


def timestampToString( value ):
    """ Converts a pysvn time value (float) into a human readable.
        Fraction of seconds is ommitted """

    timestamp = datetime.fromtimestamp( int( value ) )
    return timestamp.strftime( "%Y-%m-%d %H:%M:%S" )

