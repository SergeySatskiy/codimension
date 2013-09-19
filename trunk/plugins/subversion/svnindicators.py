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

IND_ADDED = 0
IND_DELETED = 1
IND_IGNORED = 2
IND_MERGED = 3

IND_ERROR = 100


IND_DESCRIPTION = (
( IND_ADDED, "A", "0,0,0,255", "255,255,255,255", "Scheduled to add" ),


( IND_ERROR, "E", "0,0,0,255", "220,0,0,255", "Generic error" ),
)

