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


import sys, os, os.path, getpass, commands, logging
from runparams import RunParameters


TERM_REDIRECT = -1
TERM_AUTO     = 0
TERM_KONSOLE  = 1
TERM_GNOME    = 2
TERM_XTERM    = 3


CMD_TYPE_RUN     = 0
CMD_TYPE_PROFILE = 1
CMD_TYPE_DEBUG   = 2



def getUserShell():
    " Provides the user shell on unix systems "

    try:
        s = os.getenv( 'SHELL' )
        if s is not None:
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
                      "'cd %(wdir)s; %(exec)s %(options)s; CDM_RES=$?; %(exit_if_ok)s %(shell)s' &",
    'Terminal'      : "Terminal --disable-server -x %(shell)s -c " \
                      "'cd %(wdir)s; %(exec)s %(options)s; CDM_RES=$?; %(exit_if_ok)s %(shell)s' &",
    'gnome-terminal': "gnome-terminal --disable-factory -x %(shell)s -c " \
                      "'cd %(wdir)s; %(exec)s %(options)s; CDM_RES=$?; %(exit_if_ok)s %(shell)s' &",
    'redirect'      : "%(exec)s %(runclient)s %(runopt)s -- %(options)s"
            }

# The profiling needs to waiting for the child process to finish
# Unfortunately Popen-ed process finishes immediately, I guess because of &
# So the child process PID is signalled over UDP - see the $PPID part
__osSpawnForProfile = {
    'posix'         : "%(term)s -e %(shell)s -c " \
                      "'%(exec)s %(fb)s %(port)d $PPID; cd %(wdir)s; " \
                      "%(exec)s -m cProfile -o %(out)s %(options)s; CDM_RES=$?; " \
                      "%(exec)s %(fb)s %(port)d $CDM_RES; %(exit_if_ok)s %(shell)s' &",
    'Terminal'      : "Terminal --disable-server -x %(shell)s -c " \
                      "'%(exec)s %(fb)s %(port)d $PPID; cd %(wdir)s; " \
                      "%(exec)s -m cProfile -o %(out)s %(options)s; CDM_RES=$?; " \
                      "%(exec)s %(fb)s %(port)d $CDM_RES; %(exit_if_ok)s %(shell)s' &",
    'gnome-terminal': "gnome-terminal --disable-factory -x %(shell)s -c " \
                      "'%(exec)s %(fb)s %(port)d $PPID; cd %(wdir)s; " \
                      "%(exec)s -m cProfile -o %(out)s %(options)s; CDM_RES=$?; " \
                      "%(exec)s %(fb)s %(port)d $CDM_RES; %(exit_if_ok)s %(shell)s' &",
                      }

# Unfortunately, the debugger does not use the debuggee exit code as its exit
# code. So it is impossible to detect in a bash part whether the console should
# be closed.
__osSpawnForDebug = {
    'posix'         : "%(term)s -e %(shell)s -c "
                      "'%(exec)s %(fb)s %(fbport)d $PPID; cd %(wdir)s; "
                      "%(exec)s %(dbgclient)s %(dbgopt)s -- %(app)s; echo; echo -e \"Script finished\"; "
                      "%(shell)s' &",
    'Terminal'      : "Terminal --disable-server -x %(shell)s -c "
                      "'%(exec)s %(fb)s %(fbport)d $PPID; cd %(wdir)s; "
                      "%(exec)s %(dbgclient)s %(dbgopt)s -- %(app)s; echo; echo -e \"Script finished\"; "
                      "%(shell)s' &",
    'gnome-terminal': "gnome-terminal --disable-factory -x %(shell)s -c "
                      "'%(exec)s %(fb)s %(fbport)d $PPID; cd %(wdir)s; "
                      "%(exec)s %(dbgclient)s %(dbgopt)s -- %(app)s; echo; echo -e \"Script finished\"; "
                      "%(shell)s' &",
    'redirect'      : "%(shell)s -c "
                      "'%(exec)s %(fb)s %(fbport)d $PPID; cd %(wdir)s; "
                      "%(exec)s %(dbgclient)s %(dbgopt)s -- %(app)s'",
                    }



EXIT_IF_OK = 'test "_$CDM_RES" == "_0" && exit;'



def getTerminalCommandToRun( fileName, workingDir, arguments,
                             terminalType, closeTerminal, tcpServerPort = None,
                             procID = None ):
    " Provides a command to run a separate shell terminal "

    if os.name != 'posix':
        raise Exception( "Cannot guess terminal command." )

    pythonExec = sys.executable
    shell = getUserShell()

    if terminalType == TERM_REDIRECT:
        terminalStartCmd = "redirect"
        runClient = os.path.sep.join( [ os.path.dirname( sys.argv[ 0 ] ),
                                        "debugger", "client",
                                        "client_cdm_run.py" ] )
        runOptions = "-h localhost -p " + str( tcpServerPort ) + \
                     " -w " + workingDir + " -i " + str( procID )
    else:
        terminalStartCmd = getStartTerminalCommand( terminalType )
        runClient = ""
        runOptions = ""

    args = ""
    for index in xrange( len( arguments ) ):
        args += ' "$CDM_ARG' + str( index ) + '"'

    if closeTerminal:
        exit_if_ok = EXIT_IF_OK
    else:
        exit_if_ok = ""

    if terminalStartCmd in __osSpawn:
        return __osSpawn[ terminalStartCmd ] % { 'shell':      shell,
                                                 'wdir':       workingDir,
                                                 'exec':       pythonExec,
                                                 'options':    fileName + args,
                                                 'exit_if_ok': exit_if_ok,
                                                 'runclient':  runClient,
                                                 'runopt':     runOptions }

    return __osSpawn[ os.name ] % { 'term':       terminalStartCmd,
                                    'shell':      shell,
                                    'wdir':       workingDir,
                                    'exec':       pythonExec,
                                    'options':    fileName + args,
                                    'exit_if_ok': exit_if_ok }



def getTerminalCommandToProfile( fileName, workingDir, arguments,
                                 terminalType, closeTerminal, port ):
    " Provides a command to run a separate shell terminal "

    if os.name != 'posix':
        raise Exception( "Cannot guess terminal command." )

    pythonExec = sys.executable
    shell = getUserShell()

    if terminalType == TERM_REDIRECT:
        logging.warning( "Profiling with redirected IO to IDE has not been "
                         "implemented yet. Falling back to xterm..." )
        terminalStartCmd = getStartTerminalCommand( TERM_XTERM )
    else:
        terminalStartCmd = getStartTerminalCommand( terminalType )

    args = ""
    for index in xrange( len( arguments ) ):
        args += ' "$CDM_ARG' + str( index ) + '"'

    if closeTerminal:
        exit_if_ok = EXIT_IF_OK
    else:
        exit_if_ok = ""

    # Calculate the procfeedback.py path.
    procfeedbackPath = os.path.sep.join( [ os.path.dirname( sys.argv[ 0 ] ),
                                         "utils", "procfeedback.py" ] )

    # Decide where to store the profiling output
    from globals import GlobalData
    outputPath = GlobalData().getProfileOutputPath()

    if terminalStartCmd in __osSpawnForProfile:
        return __osSpawnForProfile[ terminalStartCmd ] % { 'shell':      shell,
                                                           'wdir':       workingDir,
                                                           'exec':       pythonExec,
                                                           'options':    fileName + args,
                                                           'out':        outputPath,
                                                           'fb':         procfeedbackPath,
                                                           'port':       port,
                                                           'exit_if_ok': exit_if_ok }
    return __osSpawnForProfile[ os.name ] % { 'term':       terminalStartCmd,
                                              'shell':      shell,
                                              'wdir':       workingDir,
                                              'exec':       pythonExec,
                                              'options':    fileName + args,
                                              'out':        outputPath,
                                              'fb':         procfeedbackPath,
                                              'port':       port,
                                              'exit_if_ok': exit_if_ok }

def getTerminalCommandToDebug( fileName, workingDir, arguments,
                               terminalType, closeTerminal,
                               procFeedbackPort, tcpServerPort ):
    " Provides a command line to debug in a separate shell terminal "

    if os.name != 'posix':
        raise Exception( "Cannot guess terminal command." )

    # TODO: change it later to a selectable python interpreter
    pythonExec = sys.executable
    shell = getUserShell()

    args = ""
    for index in xrange( len( arguments ) ):
        args += ' "$CDM_ARG' + str( index ) + '"'

    if closeTerminal:
        exit_if_ok = EXIT_IF_OK
    else:
        exit_if_ok = ""

    # Calculate the procfeedback.py path.
    procfeedbackPath = os.path.sep.join( [ os.path.dirname( sys.argv[ 0 ] ),
                                           "utils", "procfeedback.py" ] )

    # Calculate the debug client path.
    debugClientPath = os.path.sep.join( [ os.path.dirname( sys.argv[ 0 ] ),
                                          "debugger", "client", "client_cdm_dbg.py" ] )

    # Get the debugging specific parameters
    from settings import Settings
    debugSettings = Settings().getDebuggerSettings()

    # Form the debug client options
    dbgopt = "-h localhost -p " + str( tcpServerPort ) + " -w " + workingDir
    if not debugSettings.reportExceptions:
        dbgopt += " -e"
    if debugSettings.traceInterpreter:
        dbgopt += " -t"
    if debugSettings.autofork:
        if debugSettings.followChild:
            dbgopt += " --fork-child"
        else:
            dbgopt += " --fork-parent"
    if terminalType != TERM_REDIRECT:
        dbgopt += " -n"

    if terminalType == TERM_REDIRECT:
        terminalStartCmd = "redirect"
    else:
        terminalStartCmd = getStartTerminalCommand( terminalType )


    # Here: all the parameters are prepared, need to combine the command line
    if terminalStartCmd in __osSpawnForDebug:
        return __osSpawnForDebug[ terminalStartCmd ] % { 'shell':      shell,
                                                         'wdir':       workingDir,
                                                         'exec':       pythonExec,
                                                         'app':        fileName + args,
                                                         'fb':         procfeedbackPath,
                                                         'fbport':     procFeedbackPort,
                                                         'tcpport':    tcpServerPort,
                                                         'dbgclient':  debugClientPath,
                                                         'dbgopt':     dbgopt }
    return __osSpawnForDebug[ os.name ] % { 'term':       terminalStartCmd,
                                            'shell':      shell,
                                            'wdir':       workingDir,
                                            'exec':       pythonExec,
                                            'app':        fileName + args,
                                            'fb':         procfeedbackPath,
                                            'fbport':     procFeedbackPort,
                                            'tcpport':    tcpServerPort,
                                            'dbgclient':  debugClientPath,
                                            'dbgopt':     dbgopt }


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


def getCwdCmdEnv( cmdType, path, params, terminalType,
                  procFeedbackPort = None, tcpServerPort = None,
                  procID = None ):
    """ Provides the working directory, command line and environment
        for running/debugging a script """

    workingDir = getWorkingDir( path, params )

    # The arguments parsing is going to pass OK because it
    # was checked in the run parameters dialogue
    arguments = parseCommandLineArguments( params.arguments )
    if cmdType == CMD_TYPE_RUN:
        cmd = getTerminalCommandToRun( path, workingDir, arguments,
                                       terminalType, params.closeTerminal,
                                       tcpServerPort, procID )
    elif cmdType == CMD_TYPE_PROFILE:
        cmd = getTerminalCommandToProfile( path, workingDir, arguments,
                                           terminalType, params.closeTerminal,
                                           procFeedbackPort )
    elif cmdType == CMD_TYPE_DEBUG:
        cmd = getTerminalCommandToDebug( path, workingDir, arguments,
                                         terminalType, params.closeTerminal,
                                         procFeedbackPort, tcpServerPort )
    else:
        raise Exception( "Unknown command requested. "
                         "Supported command types are: run, profile, debug." )

    environment = getNoArgsEnvironment( params )
    for index in xrange( len( arguments ) ):
        environment[ 'CDM_ARG' + str( index ) ] = arguments[ index ]

    return workingDir, cmd, environment


def getWorkingDir( path, params ):
    " Provides the working directory "
    if params.useScriptLocation:
        return os.path.dirname( path )
    return params.specificDir

def getNoArgsEnvironment( params ):
    " Provides a copy of the environment "
    if params.envType == params.InheritParentEnv:
        # 'None' does not work here: popen stores last env somewhere and
        # uses it inappropriately
        return os.environ.copy()
    if params.envType == params.InheritParentEnvPlus:
        environment = os.environ.copy()
        environment.update( params.additionToParentEnv )
        return environment
    return params.specificEnv.copy()


if __name__ == '__main__':
    print "Current working dir: " + os.getcwd()
    print "Environment: " + str( os.environ )
    print "Arguments: " + str( sys.argv )

