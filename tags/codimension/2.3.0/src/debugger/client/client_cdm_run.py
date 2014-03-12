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


import sys, socket, time, traceback, os, imp
from outredir_cdm_dbg import OutStreamRedirector, MAX_TRIES
from protocol_cdm_dbg import ( RequestContinue, EOT, ResponseExit,
                               ResponseRaw, RequestExit, ResponseProcID )
from errno import EAGAIN


WAIT_CONTINUE_TIMEOUT = 10
WAIT_EXIT_COMMAND = 5
RUN_WRAPPER = None


def runClientRawInput( prompt = "", echo = 1 ):
    " Replacement for the standard raw_input builtin "
    if RUN_WRAPPER is None or RUN_WRAPPER.redirected() == False:
        return runClientOrigRawInput( prompt )
    return RUN_WRAPPER.raw_input( prompt, echo )

# Use our own raw_input().
try:
    runClientOrigRawInput = __builtins__.__dict__[ 'raw_input' ]
    __builtins__.__dict__[ 'raw_input' ] = runClientRawInput
except ( AttributeError, KeyError ):
    import __main__
    runClientOrigRawInput = __main__.__builtins__.__dict__[ 'raw_input' ]
    __main__.__builtins__.__dict__[ 'raw_input' ] = runClientRawInput


def runClientInput( prompt = "" ):
    " Replacement for the standard input builtin "
    if RUN_WRAPPER is None or RUN_WRAPPER.redirected() == False:
        return runClientOrigInput( prompt )
    return RUN_WRAPPER.input( prompt )

# Use our own input().
try:
    runClientOrigInput = __builtins__.__dict__[ 'input' ]
    __builtins__.__dict__[ 'input' ] = runClientInput
except ( AttributeError, KeyError ):
    import __main__
    runClientOrigInput = __main__.__builtins__.__dict__[ 'input' ]
    __main__.__builtins__.__dict__[ 'input' ] = runClientInput



class RedirectedIORunWrapper():
    " Wrapper to run a script with redirected IO "

    def __init__( self ):
        self.__socket = None
        self.__redirected = False
        return

    def redirected( self ):
        " True if streams are redirected "
        return self.__redirected

    def main( self ):
        " Run wrapper driver "
        if '--' not in sys.argv:
            print >> sys.stderr, "Unexpected arguments"
            return 1

        procid, host, port, wdir, args = self.parseArgs()
        if procid is None or host is None or port is None or wdir is None:
            print >> sys.stderr, "Not enough arguments"
            return 1

        remoteAddress = self.resolveHost( host )
        self.connect( remoteAddress, port )
        self.write( ResponseProcID + str( procid ) )

        try:
            self.__waitContinue()
        except Exception, exc:
            print >> sys.stderr, str( exc )
            return 1

        # Setup redirections
        stdoutOld = sys.stdout
        stderrOld = sys.stderr
        sys.stdout = OutStreamRedirector( self.__socket, True )
        sys.stderr = OutStreamRedirector( self.__socket, False )
        self.__redirected = True

        # Run the script
        retCode = 0
        try:
            self.__runScript( wdir, args )
        except SystemExit, exc:
            if exc.code is None:
                retCode = 0
            elif type( exc.code ) == int:
                retCode = exc.code
            else:
                retCode = 1
                print >> sys.stderr, str( exc.code )
        except KeyboardInterrupt, exc:
            retCode = 1
            print >> sys.stderr, traceback.format_exc()
        except Exception, exc:
            retCode = 1
            print >> sys.stderr, traceback.format_exc()
        except:
            retCode = 1
            print >> sys.stderr, traceback.format_exc()

        sys.stderr = stderrOld
        sys.stdout = stdoutOld
        self.__redirected = False

        # Send the return code back
        try:
            self.write( ResponseExit + str( retCode ) )
        except Exception, exc:
            print >> sys.stderr, str( exc )
            self.close()
            return 1

        self.close()
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
        return

    def __waitContinue( self ):
        " Waits the 'continue' command "
        startTime = time.time()
        while True:
            time.sleep( 0.01 )

            # Read from the socket
            try:
                data = self.__socket.recv( 1024, socket.MSG_DONTWAIT )
            except socket.error, exc:
                if exc[ 0 ] != EAGAIN:
                    raise
                data = None
            if not data:
                if time.time() - startTime > WAIT_CONTINUE_TIMEOUT:
                    raise Exception( "Continue command timeout" )
            else:
                if data == RequestContinue + EOT:
                    break
                raise Exception( "Unexpected command from IDE: " + data )
        return

    def __waitExit( self ):
        " Waits for the 'exit' command "
        startTime = time.time()
        while True:
            time.sleep( 0.01 )

            # Read from the socket
            try:
                data = self.__socket.recv( 1024, socket.MSG_DONTWAIT )
            except socket.error, exc:
                if exc[ 0 ] != EAGAIN:
                    raise
                data = None
            if data is None:
                if time.time() - startTime > WAIT_EXIT_COMMAND:
                    raise Exception( "Exit command timeout" )
            else:
                if data == RequestExit + EOT:
                    break
                raise Exception( "Unexpected command from IDE: " + data )
        return

    def write( self, data ):
        " Writes into the socket "
        tries = MAX_TRIES
        while tries > 0:
            try:
                if self.__socket:
                    self.__socket.sendall( data + EOT )
                return
            except socket.error:
                tries -= 1
                continue
        raise socket.error( "Too many attempts to send data" )

    def __runScript( self, workingDir, arguments ):
        " Runs the python script "

        try:
            # In Py 2.x, the builtins were in __builtin__
            builtins = sys.modules[ '__builtin__' ]
        except KeyError:
            # In Py 3.x, they're in builtins
            builtins = sys.modules[ 'builtins' ]

        fileName = arguments[ 0 ]

        oldMainMod = sys.modules[ '__main__' ]
        mainMod = imp.new_module( '__main__' )
        sys.modules[ '__main__' ] = mainMod
        mainMod.__file__ = fileName
        mainMod.__builtins__ = builtins

        # Set sys.argv properly.
        oldArgv = sys.argv
        sys.argv = arguments

        # Without this imports of what is located at the script directory do
        # not work
        sys.path.insert( 0, workingDir )

        os.chdir( workingDir )
        f = open( fileName, "rU" )
        source = f.read()
        f.close()

        # We have the source.  `compile` still needs the last line to be clean,
        # so make sure it is, then compile a code object from it.
        if not source or source[-1] != '\n':
            source += '\n'

        code = compile( source, fileName, "exec" )
        exec( code, mainMod.__dict__ )

        # Restore the old __main__
        sys.modules[ '__main__' ] = oldMainMod

        # Restore the old argv and path
        sys.argv = oldArgv
        return

    def close( self ):
        " Closes the connection if so "
        try:
            if self.__socket:
                # Wait exit needed because otherwise IDE may get socket
                # disconnected before it has a chance to read the script
                # exit code. Wait for the explicit command to exit guarantees
                # that all the data will be received.
                self.__waitExit()
                self.__socket.close()
        except:
            pass
        return

    def raw_input( self, prompt, echo ):
        " Implements raw_input() using the redirected input "
        # self.__flushSocketBuffer()
        self.write( "%s%s" % ( ResponseRaw, unicode( ( prompt, echo ) ) ) )
        return self.__waitInput()

    def __flushSocketBuffer( self ):
        " Debug purpose function which empties the socket buffer "
        try:
            data = self.__socket.recv( 1024, socket.MSG_DONTWAIT )
            if data is not None:
                if len( data ) > 0:
                    f = open( "clientsocket.txt", "a" )
                    f.write( "UNEXPECTED data in socket: " + repr( data ) + "\n" )
                    f.close()
        except:
            pass
        return

    def input( self, prompt ):
        " Implement input() using the redirected input "
        return self.raw_input( prompt, 1 )

    def __waitInput( self ):
        " Waits for the user input "
        buf = u""
        while True:
            try:
                data = self.__socket.recv( 4096 )
                if data is not None:
                    pos = data.find( '\n' )
                    if pos != -1:
                        buf += data[ 0 : pos ].decode( 'utf8' )
                        break

                    buf += data.decode( 'utf8' )
            except Exception, exc:
                f = open( "clientsocket.txt", "a" )
                f.write( "Wait input exception: " + str( exc ) + "\n" )
                f.close()
        return buf

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
        procid = None
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
            elif args[ 0 ] in [ '-i', '--procid' ]:
                procid = int( args[ 1 ] )
                del args[ 0 ]
                del args[ 0 ]
            elif args[ 0 ] == '--':
                del args[ 0 ]
                break

        return procid, host, port, wdir, args


if __name__ == "__main__":
    RUN_WRAPPER = RedirectedIORunWrapper()
    sys.exit( RUN_WRAPPER.main() )

