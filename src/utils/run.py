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



def getStartTerminalCommand():
    " Provides the UNIX command to start a new terminal, e.g.: xterm "

    if 'COLORTERM' in os.environ:
        term = os.environ[ 'COLORTERM' ]
        if __isFileInPath( term ):
            return term

    if __isPrefixInEnviron( 'KDE' ):
        konsoleQuery = "kreadconfig --file kdeglobals --group General " \
                       "--key TerminalApplication --default konsole"
        (s, term) = commands.getstatusoutput( konsoleQuery )
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
    'posix'         : "%(term)s -e %(shell)s -c '%(exec)s %(options)s; %(shell)s' &",
    'Terminal'      : "Terminal --disable-server -x %(shell)s -c '%(exec)s %(options)s; %(shell)s' &",
    'gnome-terminal': "gnome-terminal --disable-factory -x %(shell)s -c '%(exec)s %(options)s; %(shell)s' &",
            }


def getTerminalCommand( fileName ):
    " Provides a command to run a separate shell terminal "

    if os.name != 'posix':
        raise Exception( "Cannot guess terminal command." )

    pythonExec = sys.executable
    shell = getUserShell()
    terminalStartCmd = getStartTerminalCommand()

    if terminalStartCmd in __osSpawn:
        command = __osSpawn[ terminalStartCmd ] % { 'shell':   shell,
                                                    'exec':    pythonExec,
                                                    'options': fileName }
    else:
        command = __osSpawn[ os.name ] % { 'term':    terminalStartCmd,
                                           'shell':   shell,
                                           'exec':    pythonExec,
                                           'options': fileName }

    return command


if __name__ == '__main__':
    print "Current working dir: " + os.getcwd()
    print "Environment: " + str( os.environ )
