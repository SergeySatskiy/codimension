#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2014  Sergey Satskiy <sergey.satskiy@gmail.com>
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

""" Wrapper to run a script with redirected IO """


import sys, socket
from outredir_cdm_dbg import OutStreamRedirector


class RedirectedIORunWrapper():
    " Wrapper to run a script with redirected IO "

    def __init__( self ):
        self.__socket = None
        return

    def main( self ):
        " Run wrapper driver "
        if '--' not in sys.argv:
            print >> sys.stderr, "Unexpected arguments"
            return 1

        host, port, wdir, args = self.parseArgs()
        if host is None or port is None or wdir is None:
            print >> sys.stderr, "Not enough arguments"
            return 1

        remoteAddress = self.resolveHost( host )
        self.connect( remoteAddress, port )

        # Wait till 'start' command
        # Run the script
        # Send the return code back

        return 0

    def connect( self, remoteAddress, port ):
        " Establishes a connection with the IDE "
        if remoteAddress is None:                    # default: 127.0.0.1
            self.__socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
            self.__socket.connect( ( '127.0.0.1', port ) )
        else:
            if "@@i" in remoteAddress:
                remoteAddress, index = remoteAddress.split( "@@i" )
            else:
                index = 0
            if ":" in remoteAddress:                              # IPv6
                sockaddr = socket.getaddrinfo( remoteAddress, port, 0, 0,
                                               socket.SOL_TCP )[ 0 ][ -1 ]
                self.__socket = socket.socket( socket.AF_INET6,
                                               socket.SOCK_STREAM )
                sockaddr = sockaddr[ : -1 ] + ( int( index ), )
                self.__socket.connect( sockaddr )
            else:                                                   # IPv4
                self.__socket = socket.socket( socket.AF_INET,
                                               socket.SOCK_STREAM )
                self.__socket.connect( ( remoteAddress, port ) )

        sys.stdout = OutStreamRedirector( self.__socket, True )
        sys.stderr = OutStreamRedirector( self.__socket, False )
        return

    def close( self ):
        " Closes the connection if so "
        try:
            if self.__socket:
                self.__socket.close()
        except:
            pass
        return

    @staticmethod
    def resolveHost( host ):
        " Resolves a hostname to an IP address "
        try:
            host, version = host.split( "@@" )
            family = socket.AF_INET6
        except ValueError:
            # version = 'v4'
            family = socket.AF_INET
        return socket.getaddrinfo( host, None, family,
                                   socket.SOCK_STREAM )[ 0 ][ 4 ][ 0 ]

    @staticmethod
    def parseArgs():
        " Parses the arguments "
        host = None
        port = None
        wdir = None
        args = sys.argv[ 1 : ]

        while args[ 0 ]:
            if args[ 0 ] in [ '-h', '--host' ]:
                host = args[ 1 ]
                del args[ 0 ]
                del args[ 0 ]
            elif args[ 0 ] in [ '-p', '--port' ]:
                port = int( args[ 1 ] )
                del args[ 0 ]
                del args[ 0 ]
            elif args[ 0 ] in [ '-w', '--workdir' ]:
                wdir = args[ 1 ]
                del args[ 0 ]
                del args[ 0 ]
            elif args[ 0 ] == '--':
                del args[ 0 ]
                break

        return host, port, wdir, args


if __name__ == "__main__":
    runWrapper = RedirectedIORunWrapper()
    sys.exit( runWrapper.main() )

