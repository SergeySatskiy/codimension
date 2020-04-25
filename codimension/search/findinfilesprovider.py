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

"""Find in files search result providers"""

import logging
from .resultprovideriface import SearchResultProviderIFace
from .findinfilesdialog import FindInFilesDialog


class FindInFilesSearchProvider(SearchResultProviderIFace):

    """Find in files search results provider"""

    def __init__(self):
        SearchResultProviderIFace.__init__(self)

    @staticmethod
    def serialize(parameters):
        """Provides a string which serializes the search parameters"""
        # Parameters dictionary:
        # { 'term': <string>,
        #   'case': <bool>,
        #   'whole': <bool>,
        #   'regexp': <bool>,
        #   'in-project': <bool>
        #   'in-opened': <bool>
        #   'in-dir': <string>
        #   'file-filter': <string> }
        ret = [('Text', parameters['term']),
               ('Case', str(parameters['case'])),
               ('Whole word', str(parameters['whole'])),
               ('Regular expression', str(parameters['regexp']))]

        if parameters['in-project']:
            ret.append(('In', 'Project'))
        elif parameters['in-opened']:
            ret.append(('In', 'Opened files'))
        else:
            ret.append(('In', parameters['in-dir']))

        if parameters['file-filter']:
            ret.append(('File filter', parameters['file-filter']))
        else:
            ret.append(('File filter', 'None'))

        return ret

    @staticmethod
    def searchAgain(searchId, parameters, resultsViewer):
        """Repeats the search"""
        try:
            dlg = FindInFilesDialog(params=parameters)
            dlg.exec_()
            resultsViewer.showReport(FindInFilesSearchProvider.getName(),
                                     dlg.searchResults,
                                     parameters, searchId)
        except Exception as exc:
            logging.error(str(exc))

    @staticmethod
    def getName():
        """Provides the display name"""
        return 'Find in files'

