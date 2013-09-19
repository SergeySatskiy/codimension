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

" Subversion plugin indicators "

IND_ADDED       = 0
IND_DELETED     = 1
IND_IGNORED     = 2
IND_MERGED      = 3
IND_MODIFIED_LR = 4     # Local and repository
IND_MODIFIED_L  = 5     # Local only
IND_MODIFIED_R  = 6     # Repository only
IND_UPTODATE    = 7
IND_REPLACED    = 8
IND_CONFLICTED  = 9
IND_EXTERNAL    = 10
IND_INCOMPLETE  = 11
IND_MISSING     = 12
IND_OBSTRUCTED  = 13
IND_UNKNOWN     = 14

IND_ERROR       = 100


IND_DESCRIPTION = (
( IND_ADDED,       "A",  "0,0,0,255", "255,255,255,255", "Added" ),
( IND_DELETED,     "D",  "0,0,0,255", "255,255,255,255", "Deleted" ),
( IND_IGNORED,     "I",  "0,0,0,255", "255,255,255,255", "Ignored" ),
( IND_MERGED,      "G",  "0,0,0,255", "255,255,255,255", "Local modifications received repository modifications" ),
( IND_MODIFIED_LR, "M*", "0,0,0,255", "255,255,255,255", "Modified locally and in repository" ),
( IND_MODIFIED_L,  "M",  "0,0,0,255", "255,255,255,255", "Modified locally" ),
( IND_MODIFIED_R,  "*",  "0,0,0,255", "255,255,255,255", "Repository version updated" ),
( IND_UPTODATE,    "OK", "0,0,0,255", "255,255,255,255", "Up to date" ),
( IND_REPLACED,    "R",  "0,0,0,255", "255,255,255,255", "Deleted and then re-added" ),
( IND_CONFLICTED,  "C",  "0,0,0,255", "255,255,255,255", "Conflicted" ),
( IND_EXTERNAL,    "X",  "0,0,0,255", "255,255,255,255", "External" ),
( IND_INCOMPLETE,  "P",  "0,0,0,255", "255,255,255,255", "Directory does not contain a complete entries list" ),
( IND_MISSING,     "!",  "0,0,0,255", "255,255,255,255", "Missing" ),
( IND_OBSTRUCTED,  "~",  "0,0,0,255", "255,255,255,255", "Versioned item obstructed by some item of a different kind" ),
( IND_UNKNOWN,     "U",  "0,0,0,255", "255,255,255,255", "Unknown status" ),

( IND_ERROR,       "E",  "0,0,0,255", "220,0,0,255",     "Generic error" ),
)

