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

import os.path
from PyQt4.QtGui import QPixmap, QColor


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


pluginHomeDir = os.path.dirname( os.path.abspath( __file__ ) ) + os.path.sep 

IND_DESCRIPTION = (
( IND_ADDED,
  QPixmap( pluginHomeDir + "status-added.png" ),
  QColor( 0, 0 , 0,255 ), QColor( 255, 255, 255, 255 ),
  "Added to SVN repository" ),
( IND_DELETED,
  QPixmap( pluginHomeDir + "status-deleted.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Deleted from SVN repository" ),
( IND_IGNORED,
  QPixmap( pluginHomeDir + "status-ignored.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Ignored" ),
( IND_MERGED,
  QPixmap( pluginHomeDir + "status-merged.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Local modifications received SVN repository modifications" ),
( IND_MODIFIED_LR,
  QPixmap( pluginHomeDir + "status-locally-repos-modified.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Modified locally and in SVN repository" ),
( IND_MODIFIED_L,
  QPixmap( pluginHomeDir + "status-locally-modified.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Modified locally" ),
( IND_MODIFIED_R,
  QPixmap( pluginHomeDir + "status-repos-modified.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "SVN repository version updated" ),
( IND_UPTODATE,
  QPixmap( pluginHomeDir + "status-uptodate.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Up to date" ),
( IND_REPLACED,
  QPixmap( pluginHomeDir + "status-replaced.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Deleted and then re-added" ),
( IND_CONFLICTED,
  QPixmap( pluginHomeDir + "status-conflict.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Conflicted" ),
( IND_EXTERNAL,
  QPixmap( pluginHomeDir + "status-external.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "External" ),
( IND_INCOMPLETE,
  QPixmap( pluginHomeDir + "status-incomplete.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Directory does not contain a complete entries list" ),
( IND_MISSING,
  QPixmap( pluginHomeDir + "status-missing.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Missing" ),
( IND_OBSTRUCTED,
  QPixmap( pluginHomeDir + "status-obstructed.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Versioned item obstructed by some item of a different kind" ),
( IND_UNKNOWN,
  QPixmap( pluginHomeDir + "status-unknown.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 255, 255, 255, 255 ),
  "Unknown status" ),

( IND_ERROR,
  QPixmap( pluginHomeDir + "status-error.png" ),
  QColor( 0, 0, 0, 255 ), QColor( 220, 0, 0, 255 ),
  "Generic error" ),
)
