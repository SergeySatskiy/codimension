#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Provides a dictionary of values from the codimension latest version file "

import urllib, sys

def getLatestVersionFile():
    " Reads the latest version file from the web site "

    try:
        url = "http://satsky.spb.ru/codimension/LatestVersion.txt"
        response = urllib.urlopen( url )
        content = response.read()

        result = {}
        for line in content.split( '\n' ):
            line = line.strip()
            if line == "" or line.startswith( '#' ):
                continue

            parts = line.split( ':' )
            if len( parts ) < 2:
                # Unknown line format
                continue

            value = ':'.join( parts[ 1: ] ).strip()
            result[ parts[ 0 ].strip() ] = value.replace( '\\n', '\n' )

        # LatestVersion key must be there
        if not result.has_key( 'LatestVersion' ):
            return False, {}

        # All is fine
        return True, result

    except:

        # Does not matter what the problem was
        return False, {}



# The script execution entry point
if __name__ == "__main__":
    success, values = getLatestVersionFile()

    if not success:
        print >> sys.stderr, "Error getting the codimension latest version"
        sys.exit( 1 )

    for key in values:
        print key + ": " + values[ key ]
    sys.exit( 0 )

