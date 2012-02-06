#
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
# The ideas and code samples are taken from the winpdb project.
# Credits: Nir Aides, Copyright (C) 2005-2009
#

" Utility functions to support running scripts "


import sys, os, getpass, commands


TERM_AUTO    = 0
TERM_KONSOLE = 1
TERM_GNOME   = 2
TERM_XTERM   = 3


class RunParameters:
    " Stores the script run parameters "

    InheritParentEnv = 0
    InheritParentEnvPlus = 1
    SpecificEnvironment = 2

    def __init__( self ):
        # Cmd line arguments
        self.arguments = ""

        # Working dir part
        self.useScriptLocation = True
        self.specificDir = ""

        # Environment
        self.envType = RunParameters.InheritParentEnv
        self.additionToParentEnv = {}
        self.specificEnv = {}
        return

    def isDefault( self ):
        " Returns True if all the values are default "
        return self.arguments == "" and \
               self.useScriptLocation == True and \
               self.specificDir == "" and \
               self.envType == RunParameters.InheritParentEnv and \
               len( self.additionToParentEnv ) == 0 and \
               len( self.specificEnv ) == 0



def getUserShell():
    " Provides the user shell on unix systems "

    try:
        s = os.getenv( 'SHELL' )
        if s != None:
            return s

        username = getpass.getuser()

        f = open( '/etc/passwd', 'r' )
        l = f.read()
        f.close()

        ll = l.split( '\n' )
        d = dict( [ (e.split(':', 1)[0], e.split(':')[-1]) for e in ll ] )

        return d[ username ]

    except:
        return 'sh'


def __isPrefixInEnviron( prefix ):
    " True if any of the environment variables starts with the given prefix "
    for name in os.environ.keys():
        if name.startswith( prefix ):
            return True
    return False


def __isFileInPath( name ):
    " True is the given name is in PATH "
    if name == '':
        return False

    try:
        envPath = os.environ[ 'PATH' ]
        for path in envPath.split( os.pathsep ):
            fName = os.path.join( path, name )
            abspath = os.path.abspath( fName )

            if os.path.isfile( abspath ):
                return True

        return False

    except:
        return False


__konsoleQuery = "kreadconfig --file kdeglobals --group General " \
                 "--key TerminalApplication --default konsole"


def getStartTerminalCommand( terminalType ):
    " Provides the UNIX command to start a new terminal, e.g.: xterm "

    if terminalType == TERM_KONSOLE:
        (s, term) = commands.getstatusoutput( __konsoleQuery )
        if (s == 0) and __isFileInPath( term ):
            return term
        raise Exception( 'default KDE konsole is not found' )
    elif terminalType == TERM_GNOME:
        if __isFileInPath( 'gnome-terminal' ):
            return 'gnome-terminal'
        raise Exception( 'gnome-terminal is not in PATH' )
    elif terminalType == TERM_XTERM:
        if __isFileInPath( 'xterm' ):
            return 'xterm'
        raise Exception( 'xterm is not in PATH' )

    # Autodetection is requested
    if 'COLORTERM' in os.environ:
        term = os.environ[ 'COLORTERM' ]
        if __isFileInPath( term ):
            return term

    if __isPrefixInEnviron( 'KDE' ):
        (s, term) = commands.getstatusoutput( __konsoleQuery )
        if (s == 0) and __isFileInPath( term ):
            return term

    elif __isPrefixInEnviron( 'GNOME' ):
        if __isFileInPath( 'gnome-terminal' ):
            return 'gnome-terminal'

    if __isFileInPath( 'xterm' ):
        return 'xterm'

    if __isFileInPath( 'rxvt' ):
        return 'rxvt'

    raise Exception( "Cannont detect terminal start command." )


__osSpawn = {
    'posix'         : "%(term)s -e %(shell)s -c " \
                      "'cd %(wdir)s; %(exec)s %(options)s; %(shell)s' &",
    'Terminal'      : "Terminal --disable-server -x %(shell)s -c " \
                      "'cd %(wdir)s; %(exec)s %(options)s; %(shell)s' &",
    'gnome-terminal': "gnome-terminal --disable-factory -x %(shell)s -c " \
                      "'cd %(wdir)s; %(exec)s %(options)s; %(shell)s' &",
            }


def getTerminalCommand( fileName, workingDir, arguments, terminalType ):
    " Provides a command to run a separate shell terminal "

    if os.name != 'posix':
        raise Exception( "Cannot guess terminal command." )

    pythonExec = sys.executable
    shell = getUserShell()
    terminalStartCmd = getStartTerminalCommand( terminalType )

    args = ""
    for index in xrange( len( arguments ) ):
        args += ' "$CDM_ARG' + str( index ) + '"'

    if terminalStartCmd in __osSpawn:
        command = __osSpawn[ terminalStartCmd ] % { 'shell':   shell,
                                                    'wdir':    workingDir,
                                                    'exec':    pythonExec,
                                                    'options': fileName + args }
    else:
        command = __osSpawn[ os.name ] % { 'term':    terminalStartCmd,
                                           'shell':   shell,
                                           'wdir':    workingDir,
                                           'exec':    pythonExec,
                                           'options': fileName + args }

    return command


def parseCommandLineArguments( cmdLine ):
    " Parses command line arguments provided by the user in the UI "

    result = []

    cmdLine = cmdLine.strip()
    expectQuote = False
    expectDblQuote = False
    lastIndex = len( cmdLine ) - 1
    argument = ""
    index = 0
    while index <= lastIndex:
        if expectQuote:
            if cmdLine[ index ] == "'":
                if cmdLine[ index - 1 ] != '\\':
                    if argument != "":
                        result.append( argument )
                        argument = ""
                    expectQuote = False
                else:
                    argument = argument[ : -1 ] + "'"
            else:
                argument += cmdLine[ index ]
            index += 1
            continue
        if expectDblQuote:
            if cmdLine[ index ] == '"':
                if cmdLine[ index - 1 ] != '\\':
                    if argument != "":
                        result.append( argument )
                        argument = ""
                    expectDblQuote = False
                else:
                    argument = argument[ : -1 ] + '"'
            else:
                argument += cmdLine[ index ]
            index += 1
            continue
        # Not in a string literal
        if cmdLine[ index ] == "'":
            if index == 0 or cmdLine[ index - 1 ] != '\\':
                expectQuote = True
                if argument != "":
                    result.append( argument )
                    argument = ""
            else:
                argument = argument[ : -1 ] + "'"
            index += 1
            continue
        if cmdLine[ index ] == '"':
            if index == 0 or cmdLine[ index - 1 ] != '\\':
                expectDblQuote = True
                if argument != "":
                    result.append( argument )
                    argument = ""
            else:
                argument = argument[ : -1 ] + '"'
            index += 1
            continue
        if cmdLine[ index ] in [ ' ', '\t' ]:
            if argument != "":
                result.append( argument )
                argument = ""
            index += 1
            continue
        argument += cmdLine[ index ]
        index += 1


    if argument != "":
        result.append( argument )

    if expectQuote or expectDblQuote:
        raise Exception( "No closing quotation" )
    return result


def getCwdCmdEnv( path, params, terminalType ):
    """ Provides the working directory, command line and environment
        for running/debugging a script """

    if params.useScriptLocation:
        workingDir = os.path.dirname( path )
    else:
        workingDir = params.specificDir

    # The arguments parsing is going to pass OK because it
    # was checked in the run parameters dialogue
    arguments = parseCommandLineArguments( params.arguments )
    cmd = getTerminalCommand( path, workingDir, arguments, terminalType )

    if params.envType == params.InheritParentEnv:
        # 'None' does not work here: popen stores last env somewhere and
        # uses it inappropriately
        environment = os.environ.copy()
    elif params.envType == params.InheritParentEnvPlus:
        environment = os.environ.copy()
        environment.update( params.additionToParentEnv )
    else:
        environment = params.specificEnv.copy()

    for index in xrange( len( arguments ) ):
        environment[ 'CDM_ARG' + str( index ) ] = arguments[ index ]

    return workingDir, cmd, environment




if __name__ == '__main__':
    print "Current working dir: " + os.getcwd()
    print "Environment: " + str( os.environ )
    print "Arguments: " + str( sys.argv )

