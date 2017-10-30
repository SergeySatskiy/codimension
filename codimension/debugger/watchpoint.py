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

"""Debugger watchpoint"""


class Watchpoint:

    """Represents a single watchpoint"""

    def __init__(self, condition=None, special=False,
                 temporary=False, enabled=True, ignoreCount=0):
        self.__condition = condition
        self.__special = special
        self.__temporary = temporary
        self.__enabled = enabled
        self.__ignoreCount = 0

    def isValid(self):
        """True if the watchpoint is valid"""
        return self.__condition is not None

    def getSpecial(self):
        """Provides the special"""
        return self.__special

    def getCondition(self):
        """Provides the condition"""
        return self.__condition

    def isTemporary(self):
        """True if temporary"""
        return self.__temporary

    def isEnabled(self):
        """True if enabled"""
        return self.__enabled

    def getIgnoreCount(self):
        """Provides the ignore count"""
        return self.__ignoreCount

    def serialize(self):
        """Serializes the watchpoint to a string"""
        return {'condition': self.__condition,
                'special': self.__special,
                'temp': self.__temporary,
                'enabled': self.__enabled,
                'ignorecnt':self.__ignoreCount}

    def deserialize(self, source):
        """Deserializes the watchpoint"""
        self.__condition = source.get('condition', None)
        self.__special = source.get('special', False)
        self.__temporary = source.get('temp', False)
        self.__enabled = source.get('enabled', False)
        self.__ignoreCount = source.get('ignorecnt', 0)
        return self.isValid()
