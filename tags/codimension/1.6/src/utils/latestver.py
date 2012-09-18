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

import socket, urllib2, sys

def getLatestVersionFile():
    " Reads the latest version file from the web site "

    success = True
    values  = {}

    oldTimeout = socket.getdefaulttimeout()
    newTimeout = 2
    socket.setdefaulttimeout( newTimeout )

    try:
        url = "http://satsky.spb.ru/codimension/LatestVersion.php"
        response = urllib2.urlopen( url )
        content = response.read().split( '\n' )

        result = {}

        lastIndex = len( content ) - 1
        index = 0

        while index <= lastIndex:
            # Start of a new chunk
            line = content[ index ].strip()
            if line == "" or line.startswith( '#' ):
                index += 1
                continue

            parts = line.split( ':' )
            if len( parts ) < 2:
                # Unknown line format
                index += 1
                continue

            key = parts[ 0 ].strip()

            # The line could continue on the next
            if line.endswith( '\\' ):
                # Many lines value
                line = line[ : -1 ]
                parts = line.split( ':' )
                value = ':'.join( parts[ 1: ] ).strip()

                index += 1
                while index <= lastIndex:
                    nextLine = content[ index ].strip()
                    if nextLine == "" or nextLine.startswith( '#' ):
                        break
                    if not nextLine.endswith( '\\' ):
                        value += content[ index ].rstrip()
                        index += 1
                        break

                    value += content[ index ].rstrip()[ :-1 ]
                    index += 1

            else:
                # Single line value, just use it
                value = ':'.join( parts[ 1: ] ).strip()
                index += 1

            result[ key ] = value.replace( '\\n', '\n' )

        # LatestVersion key must be there
        if not result.has_key( 'LatestVersion' ):
            success = False
            values  = {}
        else:
            # All is fine
            success = True
            values = result

    except:
        # Does not matter what the problem was
        success = False
        values  = {}

    socket.setdefaulttimeout( oldTimeout )
    return success, values


# The script execution entry point
if __name__ == "__main__":
    success, values = getLatestVersionFile()

    if not success:
        print >> sys.stderr, "Error getting the codimension latest version"
        sys.exit( 1 )

    for key in values:
        print key + ": " + values[ key ]
    sys.exit( 0 )

