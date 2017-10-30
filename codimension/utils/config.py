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


"""A few constants which do not depend on other project files"""

# Default encoding for the cases when:
# - the encoding could not be detected
# - replaces ascii to be on the safe side
DEFAULT_ENCODING = 'utf-8'

# File encoding used for various settings and project files
SETTINGS_ENCODING = 'utf-8'

# Directory to store Codimension settings and projects
CONFIG_DIR = '.codimension3'
