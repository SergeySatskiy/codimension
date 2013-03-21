#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Debugger server "


from utils.globals import GlobalData
from utils.run import getCwdCmdEnv, CMD_TYPE_DEBUG
from utils.settings import Settings


class CodimensionDebugger():
    " Debugger server implementation "

    STATE_IDLE = 0
    STATE_PROLOGUE = 1
    STATE_DEBUGGING = 2
    STATE_FINISHING = 3

    def __init__( self, mainWindow ):

        # To control the user interface elements
        self.__mainWindow = mainWindow
        self.__state = self.STATE_IDLE

        self.__procFeedbackSocket = None
        self.__tcpServer = None
        self.__procWatchTimer = None
        self.__procPID = None

        return

    def startDebugging( self, fileName ):
        " Starts debugging a script "
        if self.__state != self.STATE_IDLE:
            return

        # Switch the UI and make debugging visually noticable
        self.__mainWindow.switchDebugMode( True )

        params = GlobalData().getRunParameters( fileName )
        workingDir, cmd, environment = getCwdCmdEnv( CMD_TYPE_DEBUG,
                                                     fileName, params,
                                                     Settings().terminalType )


        return


    def stopDebugging( self ):
        " Stops debugging "
        self.__mainWindow.switchDebugMode( False )
        return


