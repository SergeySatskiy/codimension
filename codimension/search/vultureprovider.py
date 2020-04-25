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

"""Vulture search result providers"""

import logging
from .resultprovideriface import SearchResultProviderIFace


class VultureSearchProvider(SearchResultProviderIFace):

    """vulture search results provider"""

    def __init__(self):
        SearchResultProviderIFace.__init__(self)

    @staticmethod
    def serialize(parameters):
        """Provides a string which serializes the search parameters"""
        return [('Path', parameters['path'])]

    @staticmethod
    def searchAgain(searchId, parameters, resultsViewer):
        """Repeats the search"""
        from analysis.notused import NotUsedAnalysisProgress
        try:
            dlg = NotUsedAnalysisProgress(parameters['path'],
                                          newSearch=False)
            dlg.exec_()
            resultsViewer.showReport(VultureSearchProvider.getName(),
                                     dlg.candidates,
                                     parameters, searchId)
        except Exception as exc:
            logging.error(str(exc))

    @staticmethod
    def getName():
        """Provides the display name"""
        return 'Dead code'

