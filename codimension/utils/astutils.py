# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2020  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""ast related utils"""

import sys
import ast

def parseSourceToAST(source, filename):
    """Parses the source code to an ast tree"""

    # type_comments parameter was introduced in python 3.8
    if sys.version_info >= (3, 8):
        return ast.parse(source, filename, mode='exec', type_comments=True)
    return ast.parse(source, filename, mode='exec')

