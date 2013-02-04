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

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2013 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing the debug server
"""

from PyQt4.QtCore import SIGNAL, QModelIndex, QString
from PyQt4.QtNetwork import QTcpServer, QHostAddress, QHostInfo

from breakpointmodel import BreakPointModel
from watchpointmodel import WatchPointModel
from interface import DebuggerInterfacePython


class DebugServer( QTcpServer ):
    """
    Class implementing the debug server embedded within the IDE.

    @signal clientProcessStdout emitted after the client has sent some output
            via stdout
    @signal clientProcessStderr emitted after the client has sent some output
            via stderr
    @signal clientOutput emitted after the client has sent some output
    @signal clientRawInputSent emitted after the data was sent to
            the debug client
    @signal clientLine(filename, lineno, forStack) emitted after
            the debug client has executed a line of code
    @signal clientStack(stack) emitted after the debug client has executed a
            line of code
    @signal clientThreadList(currentId, threadList) emitted after a thread list
            has been received
    @signal clientThreadSet emitted after the client has acknowledged the change
            of the current thread
    @signal clientVariables(scope, variables) emitted after a variables dump has
            been received
    @signal clientVariable(scope, variables) emitted after a dump for one class
            variable has been received
    @signal clientStatement(boolean) emitted after an interactive command has
            been executed. The parameter is 0 to indicate that the command is
            complete and 1 if it needs more input.
    @signal clientException(exception) emitted after an exception occured on the
            client side
    @signal clientSyntaxError(exception) emitted after a syntax error
            has been detected on the client side
    @signal clientExit(int) emitted with the exit status after
            the client has exited
    @signal clientClearBreak(filename, lineno) emitted after the debug client
            has decided to clear a temporary breakpoint
    @signal clientBreakConditionError(fn, lineno) emitted after the client has
            signaled a syntax error in a breakpoint condition
    @signal clientClearWatch(condition) emitted after the debug client
            has decided to clear a temporary watch expression
    @signal clientWatchConditionError(condition) emitted after the client has
            signaled a syntax error in a watch expression
    @signal clientRawInput(prompt, echo) emitted after a raw input
            request was received
    @signal clientBanner(banner) emitted after the client banner was received
    @signal clientCapabilities(int capabilities, QString cltype) emitted after
            the clients capabilities were received
    @signal clientCompletionList(completionList, text) emitted after the client
            the commandline completion list and the reworked searchstring was
            received from the client
    @signal passiveDebugStarted emitted after the debug client has connected in
            passive debug mode
    @signal clientGone emitted if the client went away (planned or unplanned)
    """

    def __init__( self ):
        QTcpServer.__init__( self )

        # create our models
        self.breakpointModel = BreakPointModel( self )
        self.watchpointModel = WatchPointModel( self )
        self.watchSpecialCreated = "created"
        self.watchSpecialChanged = "changed"

        hostAddress = QHostAddress( QHostAddress.Any )
        self.listen( hostAddress )

        self.debuggerInterface = DebuggerInterfacePython( self )
        self.debugging = False
        self.running = False
        self.clientProcess = None
        self.bannerReceived = False

        self.connect( self, SIGNAL( "clientClearBreak" ),
                      self.__clientClearBreakPoint )
        self.connect( self, SIGNAL( "clientClearWatch" ),
                      self.__clientClearWatchPoint )
        self.connect( self, SIGNAL( "newConnection()" ),
                      self.__newConnection )

        self.connect( self.breakpointModel,
            SIGNAL( "rowsAboutToBeRemoved(const QModelIndex &, int, int)" ),
            self.__deleteBreakPoints )
        self.connect( self.breakpointModel,
            SIGNAL( "dataAboutToBeChanged(const QModelIndex &, const QModelIndex &)" ),
            self.__breakPointDataAboutToBeChanged )
        self.connect( self.breakpointModel,
            SIGNAL( "dataChanged(const QModelIndex &, const QModelIndex &)" ),
            self.__changeBreakPoints )
        self.connect( self.breakpointModel,
            SIGNAL( "rowsInserted(const QModelIndex &, int, int)" ),
            self.__addBreakPoints )

        self.connect( self.watchpointModel,
            SIGNAL( "rowsAboutToBeRemoved(const QModelIndex &, int, int)" ),
            self.__deleteWatchPoints )
        self.connect( self.watchpointModel,
            SIGNAL( "dataAboutToBeChanged(const QModelIndex &, const QModelIndex &)" ),
            self.__watchPointDataAboutToBeChanged )
        self.connect( self.watchpointModel,
            SIGNAL( "dataChanged(const QModelIndex &, const QModelIndex &)" ),
            self.__changeWatchPoints )
        self.connect( self.watchpointModel,
            SIGNAL( "rowsInserted(const QModelIndex &, int, int)" ),
            self.__addWatchPoints )

        self.__registerDebuggerInterfaces()
        return

    @staticmethod
    def getHostAddress( localhost ):
        """ Provides the IP address or hostname the debug server is listening.

        @param localhost flag indicating to return the
               address for localhost (boolean)
        @return IP address or hostname (string)
        """
        if localhost:
            return "127.0.0.1"
        return "%s@@v4" % QHostInfo.localHostName()

    def preferencesChanged( self ):
        " Handles the preferencesChanged signal "
        self.__registerDebuggerInterfaces()
        return

    def __registerDebuggerInterfaces( self ):
        " Registers the available debugger interface modules "
        self.__clientCapabilities = {}
        self.__clientAssociations = {}

        for interface in DebuggerInterfaces:
            modName = "Debugger.%s" % interface
            mod = __import__(modName)
            components = modName.split('.')
            for comp in components[1:]:
                mod = getattr(mod, comp)

            clientLanguage, clientCapabilities, clientExtensions = \
                mod.getRegistryData()
            if clientLanguage:
                self.__clientCapabilities[clientLanguage] = clientCapabilities
                for extension in clientExtensions:
                    if extension not in self.__clientAssociations:
                        self.__clientAssociations[extension] = clientLanguage
        return

    def getSupportedLanguages( self, shellOnly = False ):
        """
        Public slot to return the supported programming languages.

        @param shellOnly flag indicating only languages supporting an
            interactive shell should be returned
        @return list of supported languages (list of strings)
        """
        languages = self.__clientCapabilities.keys()
        try:
            del languages[ languages.index( "None" ) ]
        except ValueError:
            pass    # it is not in the list

        if shellOnly:
            languages = \
                [ lang for lang in languages 
                  if self.__clientCapabilities[ lang ] &
                     DebugClientCapabilities.HasShell ]

        return languages[ : ]

    def getExtensions( self, language ):
        """
        Public slot to get the extensions associated with the given language.

        @param language language to get extensions for (string)
        @return tuple of extensions associated with
                the language (tuple of strings)
        """
        extensions = []
        for ext, lang in self.__clientAssociations.items():
            if lang == language:
                extensions.append( ext )

        return tuple( extensions )

    def startClient( self, unplanned = True, forProject = False,
                     runInConsole = False ):
        """
        Public method to start a debug client.

        @keyparam unplanned flag indicating that the client has died (boolean)
        @keyparam clType type of client to be started (string)
        @keyparam forProject flag indicating a project related action (boolean)
        @keyparam runInConsole flag indicating to start the debugger in a
            console window (boolean)
        """
        self.running = False
        if self.debuggerInterface and self.debuggerInterface.isConnected():
            self.shutdownServer()
            self.emit( SIGNAL( 'clientGone' ),
                       unplanned & self.debugging )

        if self.clientProcess:
            self.disconnect( self.clientProcess,
                             SIGNAL( "readyReadStandardError()" ),
                             self.__clientProcessError )
            self.disconnect( self.clientProcess,
                             SIGNAL( "readyReadStandardOutput()" ),
                             self.__clientProcessOutput )
            self.clientProcess.close()
            self.clientProcess.kill()
            self.clientProcess.waitForFinished( 10000 )
            self.clientProcess = None

        if forProject:
            project = e4App().getObject( "Project" )
            if not project.isDebugPropertiesLoaded():
                self.clientProcess, isNetworked = \
                    self.debuggerInterface.startRemote( self.serverPort(),
                                                        runInConsole )
            else:
                self.clientProcess, isNetworked = \
                    self.debuggerInterface.startRemoteForProject(
                                                        self.serverPort(),
                                                        runInConsole )
        else:
            self.clientProcess, isNetworked = \
                self.debuggerInterface.startRemote( self.serverPort(),
                                                    runInConsole )

        if self.clientProcess:
            self.connect( self.clientProcess,
                          SIGNAL( "readyReadStandardError()" ),
                          self.__clientProcessError )
            self.connect( self.clientProcess,
                          SIGNAL( "readyReadStandardOutput()" ),
                          self.__clientProcessOutput )

            if not isNetworked:
                # the client is connected through stdin and stdout
                # Perform actions necessary, if client type has changed
                if self.bannerReceived == False:
                    self.bannerReceived = True
                    self.remoteBanner()

                self.debuggerInterface.flush()
        return

    def __clientProcessOutput( self ):
        " Processes client output received via stdout "
        output = QString( self.clientProcess.readAllStandardOutput() )
        self.emit( SIGNAL( "clientProcessStdout" ), output )
        return

    def __clientProcessError( self ):
        " Processes client output received via stderr "
        error = QString( self.clientProcess.readAllStandardError() )
        self.emit( SIGNAL( "clientProcessStderr" ), error )
        return

    def __clientClearBreakPoint( self, fname, lineno ):
        """
        Private slot to handle the clientClearBreak signal.

        @param fn filename of breakpoint to clear (string or QString)
        @param lineno line number of breakpoint to clear (integer)
        """
        if self.debugging:
            index = self.breakpointModel.getBreakPointIndex( fname, lineno )
            self.breakpointModel.deleteBreakPointByIndex( index )
        return

    def __deleteBreakPoints( self, parentIndex, start, end ):
        """
        Private slot to delete breakpoints.

        @param parentIndex index of parent item (QModelIndex)
        @param start start row (integer)
        @param end end row (integer)
        """
        if self.debugging:
            for row in xrange( start, end + 1 ):
                index = self.breakpointModel.index( row, 0, parentIndex )
                fname, lineno = \
                    self.breakpointModel.getBreakPointByIndex( index )[ 0 : 2 ]
                self.remoteBreakpoint( fname, lineno, False )
        return

    def __changeBreakPoints( self, startIndex, endIndex ):
        """
        Private slot to set changed breakpoints.

        @param indexes indexes of changed breakpoints.
        """
        if self.debugging:
            self.__addBreakPoints( QModelIndex(),
                                   startIndex.row(), endIndex.row() )
        return

    def __breakPointDataAboutToBeChanged( self, startIndex, endIndex ):
        """
        Handles the dataAboutToBeChanged signal of the breakpoint model.

        @param startIndex start index of the rows to be changed (QModelIndex)
        @param endIndex end index of the rows to be changed (QModelIndex)
        """
        if self.debugging:
            self.__deleteBreakPoints( QModelIndex(),
                                      startIndex.row(), endIndex.row() )
        return

    def __addBreakPoints( self, parentIndex, start, end ):
        """
        Private slot to add breakpoints.

        @param parentIndex index of parent item (QModelIndex)
        @param start start row (integer)
        @param end end row (integer)
        """
        if self.debugging:
            for row in xrange( start, end + 1 ):
                index = self.breakpointModel.index( row, 0, parentIndex )
                fname, line, cond, temp, enabled, ignorecount = \
                    self.breakpointModel.getBreakPointByIndex( index )[ : 6 ]
                self.remoteBreakpoint( fname, line, True, cond, temp )
                if not enabled:
                    self.__remoteBreakpointEnable( fname, line, False )
                if ignorecount:
                    self.__remoteBreakpointIgnore( fname, line, ignorecount )
        return

    def __makeWatchCondition( self, cond, special ):
        """
        Private method to construct the condition string.

        @param cond condition (string or QString)
        @param special special condition (string or QString)
        @return condition string (QString)
        """
        special = unicode( special )
        if special == "":
            _cond = unicode( cond )
        else:
            if special == unicode( self.watchSpecialCreated ):
                _cond = "%s ??created??" % cond
            elif special == unicode( self.watchSpecialChanged ):
                _cond = "%s ??changed??" % cond
        return _cond

    def __splitWatchCondition( self, cond ):
        """
        Private method to split a remote watch expression.

        @param cond remote expression (string or QString)
        @return tuple of local expression (string) and special
                condition (string)
        """
        cond = unicode( cond )
        if cond.endswith( " ??created??" ):
            cond, special = cond.split()
            special = unicode( self.watchSpecialCreated )
        elif cond.endswith( " ??changed??" ):
            cond, special = cond.split()
            special = unicode( self.watchSpecialChanged )
        else:
            cond = cond
            special = ""

        return cond, special

    def __clientClearWatchPoint( self, condition ):
        """
        Private slot to handle the clientClearWatch signal.

        @param condition expression of watch expression
               to clear (string or QString)
        """
        if self.debugging:
            cond, special = self.__splitWatchCondition( condition )
            index = self.watchpointModel.getWatchPointIndex( cond, special )
            self.watchpointModel.deleteWatchPointByIndex( index )
        return

    def __deleteWatchPoints( self, parentIndex, start, end ):
        """
        Private slot to delete watch expressions.

        @param parentIndex index of parent item (QModelIndex)
        @param start start row (integer)
        @param end end row (integer)
        """
        if self.debugging:
            for row in xrange( start, end + 1 ):
                index = self.watchpointModel.index( row, 0, parentIndex )
                cond, special = \
                    self.watchpointModel.getWatchPointByIndex( index )[ 0 : 2 ]
                cond = self.__makeWatchCondition( cond, special )
                self.__remoteWatchpoint( cond, False )
        return

    def __watchPointDataAboutToBeChanged( self, startIndex, endIndex ):
        """
        Private slot to handle the dataAboutToBeChanged signal of the
        watch expression model.

        @param startIndex start index of the rows to be changed (QModelIndex)
        @param endIndex end index of the rows to be changed (QModelIndex)
        """
        if self.debugging:
            self.__deleteWatchPoints( QModelIndex(),
                                      startIndex.row(), endIndex.row() )
        return

    def __addWatchPoints( self, parentIndex, start, end ):
        """
        Private slot to set a watch expression.

        @param parentIndex index of parent item (QModelIndex)
        @param start start row (integer)
        @param end end row (integer)
        """
        if self.debugging:
            for row in xrange( start, end + 1 ):
                index = self.watchpointModel.index( row, 0, parentIndex )
                cond, special, temp, enabled, ignorecount = \
                    self.watchpointModel.getWatchPointByIndex( index )[ : 5 ]
                cond = self.__makeWatchCondition( cond, special )
                self.__remoteWatchpoint( cond, True, temp )
                if not enabled:
                    self.__remoteWatchpointEnable( cond, False )
                if ignorecount:
                    self.__remoteWatchpointIgnore( cond, ignorecount )
        return

    def __changeWatchPoints( self, startIndex, endIndex ):
        """
        Private slot to set changed watch expressions.

        @param startIndex start index of the rows to be changed (QModelIndex)
        @param endIndex end index of the rows to be changed (QModelIndex)
        """
        if self.debugging:
            self.__addWatchPoints( QModelIndex(),
                                   startIndex.row(), endIndex.row() )
        return

    def getClientCapabilities( self, cType ):
        """
        Public method to retrieve the debug clients capabilities.

        @param type debug client type (string)
        @return debug client capabilities (integer)
        """
        try:
            return self.__clientCapabilities[ cType ]
        except KeyError:
            return 0    # no capabilities

    def __newConnection( self ):
        """
        Private slot to handle a new connection.
        """
        sock = self.nextPendingConnection()
        accepted = self.debuggerInterface.newConnection( sock )
        if accepted:
            # Perform actions necessary, if client type has changed
            if self.bannerReceived == False:
                self.bannerReceived = True
                self.remoteBanner()

            self.debuggerInterface.flush()
        return

    def shutdownServer( self ):
        """
        Public method to cleanly shut down.

        It closes our socket and shuts down
        the debug client. (Needed on Win OS)
        """
        if self.debuggerInterface is not None:
            self.debuggerInterface.shutdown()
        return

    def remoteEnvironment( self, env ):
        """
        Public method to set the environment for a program to debug, run, ...

        @param env environment settings (string)
        """
        envlist = Utilities.parseEnvironmentString(env)
        envdict = {}
        for item in envlist:
            try:
                key, value = item.split( '=', 1 )
                if value.startswith( '"' ) or value.startswith( "'" ):
                    value = value[ 1 : -1 ]
                envdict[ unicode( key ) ] = unicode( value )
            except:
                pass
        self.debuggerInterface.remoteEnvironment( envdict )
        return

    def remoteLoad( self, fname, argv, wdir, env,
                    tracePython = False, autoContinue = True,
                    forProject = False, runInConsole = False, autoFork = False,
                    forkChild = False ):
        """
        Public method to load a new program to debug.

        @param fname the filename to debug (string)
        @param argv the commandline arguments to pass to the program
               (string or QString)
        @param wdir the working directory for the program (string)
        @param env environment settings (string)
        @keyparam autoClearShell flag indicating, that the interpreter window
                  should be cleared (boolean)
        @keyparam tracePython flag indicating if the Python library should be
                  traced as well (boolean)
        @keyparam autoContinue flag indicating, that the debugger should not
                  stop at the first executable line (boolean)
        @keyparam forProject flag indicating a project related action (boolean)
        @keyparam runInConsole flag indicating to start the debugger in a
            console window (boolean)
        @keyparam autoFork flag indicating the automatic fork mode (boolean)
        @keyparam forkChild flag indicating to debug the child
                  after forking (boolean)
        """

        # Restart the client
        self.startClient( False, forProject = forProject,
                          runInConsole = runInConsole )

        self.remoteEnvironment(env)

        self.debuggerInterface.remoteLoad( fname, argv, wdir, tracePython,
                                           autoContinue, autoFork, forkChild )
        self.debugging = True
        self.running = True
        self.__restoreBreakpoints()
        self.__restoreWatchpoints()
        return

    def remoteRun(self, fname, argv, wdir, env,
                  forProject = False, runInConsole = False,
                  autoFork = False, forkChild = False):
        """
        Public method to load a new program to run.

        @param fn the filename to run (string)
        @param argv the commandline arguments to pass
               to the program (string or QString)
        @param wd the working directory for the program (string)
        @param env environment settings (string)
        @keyparam autoClearShell flag indicating, that the interpreter
                  window should be cleared (boolean)
        @keyparam forProject flag indicating a project related action (boolean)
        @keyparam runInConsole flag indicating to start the debugger in a
            console window (boolean)
        @keyparam autoFork flag indicating the automatic fork mode (boolean)
        @keyparam forkChild flag indicating to debug the child
                  after forking (boolean)
        """
        # Restart the client
        self.startClient( False, forProject = forProject,
                          runInConsole = runInConsole )

        self.remoteEnvironment( env )

        self.debuggerInterface.remoteRun( fname, argv, wdir,
                                          autoFork, forkChild )
        self.debugging = False
        self.running = True
        return

    def remoteStatement( self, stmt ):
        """
        Public method to execute a Python statement.

        @param stmt the Python statement to execute (string). It
              should not have a trailing newline.
        """
        self.debuggerInterface.remoteStatement( stmt )
        return

    def remoteStep( self ):
        " Single step the debugged program "
        self.debuggerInterface.remoteStep()
        return

    def remoteStepOver( self ):
        " Steps over the debugged program "
        self.debuggerInterface.remoteStepOver()
        return

    def remoteStepOut( self ):
        " Steps out the debugged program "
        self.debuggerInterface.remoteStepOut()
        return

    def remoteStepQuit( self ):
        " Stops the debugged program "
        self.debuggerInterface.remoteStepQuit()
        return

    def remoteContinue( self, special = False ):
        """
        Public method to continue the debugged program.

        @param special flag indicating a special continue operation
        """
        self.debuggerInterface.remoteContinue( special )
        return

    def remoteBreakpoint( self, fname, line, shouldSet,
                          cond = None, temp = False ):
        """
        Public method to set or clear a breakpoint.

        @param fname filename the breakpoint belongs to (string)
        @param line linenumber of the breakpoint (int)
        @param set flag indicating setting or resetting a breakpoint (boolean)
        @param cond condition of the breakpoint (string)
        @param temp flag indicating a temporary breakpoint (boolean)
        """
        self.debuggerInterface.remoteBreakpoint( fname, line, shouldSet,
                                                 cond, temp )
        return

    def __remoteBreakpointEnable( self, fname, line, enable ):
        """
        Private method to enable or disable a breakpoint.

        @param fname filename the breakpoint belongs to (string)
        @param line linenumber of the breakpoint (int)
        @param enable flag indicating enabling or
               disabling a breakpoint (boolean)
        """
        self.debuggerInterface.remoteBreakpointEnable( fname, line, enable )
        return

    def __remoteBreakpointIgnore( self, fname, line, count ):
        """
        Private method to ignore a breakpoint the next couple of occurrences.

        @param fname filename the breakpoint belongs to (string)
        @param line linenumber of the breakpoint (int)
        @param count number of occurrences to ignore (int)
        """
        self.debuggerInterface.remoteBreakpointIgnore( fname, line, count )
        return

    def __remoteWatchpoint( self, cond, shouldSet, temp = False ):
        """
        Private method to set or clear a watch expression.

        @param cond expression of the watch expression (string)
        @param set flag indicating setting or
               resetting a watch expression (boolean)
        @param temp flag indicating a temporary watch expression (boolean)
        """
        # cond is combination of cond and special (s. watch expression viewer)
        self.debuggerInterface.remoteWatchpoint( cond, shouldSet, temp )
        return

    def __remoteWatchpointEnable( self, cond, enable ):
        """
        Private method to enable or disable a watch expression.

        @param cond expression of the watch expression (string)
        @param enable flag indicating enabling or
               disabling a watch expression (boolean)
        """
        # cond is combination of cond and special (s. watch expression viewer)
        self.debuggerInterface.remoteWatchpointEnable( cond, enable )
        return

    def __remoteWatchpointIgnore( self, cond, count ):
        """
        Private method to ignore a watch expression
        the next couple of occurrences.

        @param cond expression of the watch expression (string)
        @param count number of occurrences to ignore (int)
        """
        # cond is combination of cond and special (s. watch expression viewer)
        self.debuggerInterface.remoteWatchpointIgnore( cond, count )
        return

    def remoteRawInput( self, inputString ):
        """
        Public method to send the raw input to the debugged program.

        @param inputString the raw input (string)
        """
        self.debuggerInterface.remoteRawInput( inputString )
        self.emit( SIGNAL( 'clientRawInputSent' ) )
        return

    def remoteThreadList( self ):
        " Requests the list of threads from the client "
        self.debuggerInterface.remoteThreadList()
        return

    def remoteSetThread( self, tid ):
        """
        Public method to request to set the given thread as current thread.

        @param tid id of the thread (integer)
        """
        self.debuggerInterface.remoteSetThread( tid )
        return

    def remoteClientVariables( self, scope, filterRegexp, framenr = 0 ):
        """
        Public method to request the variables of the debugged program.

        @param scope the scope of the variables (0 = local, 1 = global)
        @param filter list of variable types to filter out (list of int)
        @param framenr framenumber of the variables to retrieve (int)
        """
        self.debuggerInterface.remoteClientVariables( scope, filterRegexp,
                                                      framenr )
        return

    def remoteClientVariable( self, scope, filterRegexp, var, framenr = 0 ):
        """
        Public method to request the variables of the debugged program.

        @param scope the scope of the variables (0 = local, 1 = global)
        @param filter list of variable types to filter out (list of int)
        @param var list encoded name of variable to retrieve (string)
        @param framenr framenumber of the variables to retrieve (int)
        """
        self.debuggerInterface.remoteClientVariable( scope, filterRegexp,
                                                     var, framenr )
        return

    def remoteClientSetFilter( self, scope, filterRegexp ):
        """
        Public method to set a variables filter list.

        @param scope the scope of the variables (0 = local, 1 = global)
        @param filter regexp string for variable names to filter out (string)
        """
        self.debuggerInterface.remoteClientSetFilter( scope, filterRegexp )
        return

    def remoteEval( self, arg ):
        """
        Public method to evaluate arg in the current context
        of the debugged program.

        @param arg the arguments to evaluate (string)
        """
        self.debuggerInterface.remoteEval( arg )
        return

    def remoteExec( self, stmt ):
        """
        Public method to execute stmt in the current context
        of the debugged program.

        @param stmt statement to execute (string)
        """
        self.debuggerInterface.remoteExec( stmt )
        return

    def remoteBanner( self ):
        " Gets the banner info of the remote client "
        self.debuggerInterface.remoteBanner()
        return

    def remoteCapabilities( self ):
        """
        Public slot to get the debug clients capabilities.
        """
        self.debuggerInterface.remoteCapabilities()
        return

    def remoteCompletion( self, text ):
        """
        Public slot to get the a list of possible commandline completions
        from the remote client.

        @param text the text to be completed (string or QString)
        """
        self.debuggerInterface.remoteCompletion( text )
        return

    def clientOutput( self, line ):
        """
        Public method to process a line of client output.

        @param line client output (string)
        """
        self.emit( SIGNAL( 'clientOutput' ), line )
        return

    def clientLine( self, filename, lineno, forStack = False ):
        """
        Public method to process client position feedback.

        @param filename name of the file currently being executed (string)
        @param lineno line of code currently being executed (integer)
        @param forStack flag indicating this is for a stack dump (boolean)
        """
        self.emit( SIGNAL( 'clientLine' ), filename, lineno, forStack )
        return

    def clientStack( self, stack ):
        """
        Public method to process a client's stack information.

        @param stack list of stack entries. Each entry is a tuple of three
            values giving the filename, linenumber and method
            (list of lists of (string, integer, string))
        """
        self.emit( SIGNAL( 'clientStack' ), stack )
        return

    def clientThreadList( self, currentId, threadList ):
        """
        Public method to process the client thread list info.

        @param currentID id of the current thread (integer)
        @param threadList list of dictionaries containing the thread data
        """
        self.emit( SIGNAL( 'clientThreadList' ), currentId, threadList )
        return

    def clientThreadSet( self ):
        """
        Public method to handle the change of the client thread.
        """
        self.emit( SIGNAL( 'clientThreadSet' ) )
        return

    def clientVariables( self, scope, variables ):
        """
        Public method to process the client variables info.

        @param scope scope of the variables
               (-1 = empty global, 1 = global, 0 = local)
        @param variables the list of variables from the client
        """
        self.emit( SIGNAL( 'clientVariables' ), scope, variables )
        return

    def clientVariable( self, scope, variables ):
        """
        Public method to process the client variable info.

        @param scope scope of the variables
               (-1 = empty global, 1 = global, 0 = local)
        @param variables the list of members of a classvariable from the client
        """
        self.emit( SIGNAL( 'clientVariable' ), scope, variables )
        return

    def clientStatement( self, more ):
        """
        Public method to process the input response from the client.

        @param more flag indicating that more user input is required
        """
        self.emit( SIGNAL( 'clientStatement' ), more )
        return

    def clientException( self, exceptionType, exceptionMessage, stackTrace ):
        """
        Public method to process the exception info from the client.

        @param exceptionType type of exception raised (string)
        @param exceptionMessage message given by the exception (string)
        @param stackTrace list of stack entries with the exception position
               first. Each stack entry is a list giving the
               filename and the linenumber.
        """
        if self.running:
            self.emit( SIGNAL( 'clientException' ),
                       exceptionType, exceptionMessage, stackTrace )
        return

    def clientSyntaxError( self, message, filename, lineNo, characterNo ):
        """
        Public method to process the syntax error info from the client.

        @param message message of the syntax error (string)
        @param filename translated filename of the
               syntax error position (string)
        @param lineNo line number of the syntax error position (integer)
        @param characterNo character number of the
               syntax error position (integer)
        """
        if self.running:
            self.emit( SIGNAL( 'clientSyntaxError' ), message,
                       filename, lineNo, characterNo )
        return

    def clientExit( self, status ):
        """
        Public method to process the client exit status.

        @param status exit code as a string (string)
        """
        self.emit( SIGNAL( 'clientExit(int)' ), int( status ) )
        if Preferences.getDebugger("AutomaticReset"):
            self.startClient( False )
        self.running = False
        return

    def clientClearBreak( self, filename, lineno ):
        """
        Public method to process the client clear breakpoint command.

        @param filename filename of the breakpoint (string)
        @param lineno line umber of the breakpoint (integer)
        """
        self.emit( SIGNAL( 'clientClearBreak' ), filename, lineno )
        return

    def clientBreakConditionError( self, filename, lineno ):
        """
        Public method to process the client breakpoint condition error info.

        @param filename filename of the breakpoint (string)
        @param lineno line umber of the breakpoint (integer)
        """
        self.emit( SIGNAL( 'clientBreakConditionError' ), filename, lineno )
        return

    def clientClearWatch( self, condition ):
        """
        Public slot to handle the clientClearWatch signal.

        @param condition expression of watch expression
               to clear (string or QString)
        """
        self.emit( SIGNAL( 'clientClearWatch' ), condition )
        return

    def clientWatchConditionError( self, condition ):
        """
        Public method to process the client watch expression error info.

        @param condition expression of watch expression
               to clear (string or QString)
        """
        self.emit( SIGNAL( 'clientWatchConditionError' ), condition )
        return

    def clientRawInput( self, prompt, echo ):
        """
        Public method to process the client raw input command.

        @param prompt the input prompt (string)
        @param echo flag indicating an echoing of the input (boolean)
        """
        self.emit( SIGNAL( 'clientRawInput' ), prompt, echo )
        return

    def clientBanner( self, version, platform, debugClient ):
        """
        Public method to process the client banner info.

        @param version interpreter version info (string)
        @param platform hostname of the client (string)
        @param debugClient additional debugger type info (string)
        """
        self.emit( SIGNAL( 'clientBanner' ), version, platform, debugClient )
        return

    def clientCapabilities( self, capabilities, clientType ):
        """
        Public method to process the client capabilities info.

        @param capabilities bitmaks with the client capabilities (integer)
        @param clientType type of the debug client (string)
        """
        self.__clientCapabilities[ clientType ] = capabilities
        self.emit( SIGNAL( 'clientCapabilities' ), capabilities, clientType )
        return

    def clientCompletionList( self, completionList, text ):
        """
        Public method to process the client auto completion info.

        @param completionList list of possible completions (list of strings)
        @param text the text to be completed (string)
        """
        self.emit( SIGNAL( 'clientCompletionList' ), completionList, text )
        return

    def passiveStartUp( self, fname, exc ):
        """
        Public method to handle a passive debug connection.

        @param fname filename of the debugged script (string)
        @param exc flag to enable exception reporting of the IDE (boolean)
        """
        print "Passive debug connection received"
        self.debugging = True
        self.running = True
        self.__restoreBreakpoints()
        self.__restoreWatchpoints()
        self.emit( SIGNAL( 'passiveDebugStarted' ), fname, exc )
        return

    def __restoreBreakpoints( self ):
        " Restore the breakpoints after a restart "
        if self.debugging:
            self.__addBreakPoints( QModelIndex(), 0,
                                   self.breakpointModel.rowCount() - 1 )
        return

    def __restoreWatchpoints( self ):
        " Restores the watch expressions after a restart "
        if self.debugging:
            self.__addWatchPoints( QModelIndex(), 0,
                                   self.watchpointModel.rowCount() - 1 )
        return

    def getBreakPointModel( self ):
        " Provides a reference to the breakpoint model object "
        return self.breakpointModel

    def getWatchPointModel( self ):
        " Provides a reference to the watch expression model object "
        return self.watchpointModel

    def isConnected( self ):
        " Tests if the debug server is connected to a backend "
        return self.debuggerInterface and self.debuggerInterface.isConnected()
