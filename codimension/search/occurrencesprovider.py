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

"""Occurrences search result providers"""

import logging
from .resultprovideriface import SearchResultProviderIFace
from autocomplete.completelists import getOccurrences


class OccurrencesSearchProvider(SearchResultProviderIFace):

    """vulture search results provider"""

    def __init__(self):
        SearchResultProviderIFace.__init__(self)

    @staticmethod
    def serialize(parameters):
        """Provides a string which serializes the search parameters"""
        # parameters -> {'name': <string>,
        #                'filename': <string>,
        #                'line': <int>
        #                'column': <int>}
        return [('Name', parameters['name']),
                ('File name', parameters['filename']),
                ('Line', str(parameters['line'])),
                ('Column', str(parameters['column']))]

    @staticmethod
    def searchAgain(searchId, parameters, resultsViewer):
        """Repeats the search"""
        try:
            pass
        except Exception as exc:
            logging.error(str(exc))

    @staticmethod
    def getName():
        """Provides the display name"""
        return 'Occurrences'

