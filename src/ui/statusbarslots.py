#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

""" Status bar message slots support """

from datetime import datetime, timedelta


class SlotMessage:
    " Holds a single slot message "

    def __init__( self, msg, duration ):
        self.msg = msg
        if duration is None:
            self.till = None
        else:
            self.till = datetime.now() + timedelta( milliseconds = duration )
        return

    def expired( self ):
        " returns True if the message is expired "
        if self.till is None:
            return True
        return datetime.now() > self.till


class StatusBarSlots:
    " Wraps logical slots for the status bar "

    def __init__( self, statusBar ):
        self.__statusBar = statusBar
        self.__slots = []   # SlotMessage
        return

    def showMessage( self, msg, slot, timeout = 10000 ):
        " Shows the message "
        if not msg:
            self.clearMessage( slot )
            return

        while len( self.__slots ) < slot + 1:
            newMsg = SlotMessage( None, None )
            self.__slots.append( newMsg )

        self.__slots[ slot ].msg = SlotMessage( msg, timeout )
        self.__display()
        return

    def clearMessage( self, slot ):
        " Clears the message in the given slot "
        if slot >= len( self.__slots ):
            return
        self.__slots[ slot ].msg = None
        self.__slots[ slot ].till = None
        self.__display()
        return

    def __display( self ):
        " Displays the combined message "
        self.__reduce()
        msg, timeout = self.__getMessageAndTimeout()
        if msg is None or timeout is None:
            self.__statusBar.clearMessage()
        else:
            self.__statusBar.showMessage( msg, timeout )
        return

    def __getMessageAndTimeout( self ):
        " Provides a complete message with a timeout in milliseconds "
        message = ""
        till = None
        for item in self.__slots:
            if message != "":
                message += " "
            message += item.msg
            if till is None:
                till = item.till
            else:
                if item.till > till:
                    till = item.till
        if not message or till is None:
            return None, None

        delta = till - datetime.now()
        delta = int(delta.microseconds / 1000)
        if delta <= 0:
            return None, None
        return message, delta

    def __reduce( self ):
        " Removes the expired messages "
        count = len( self.__slots )
        for index in xrange( count - 1, -1, -1 ):
            if not self.__slots[ index ].msg or self.__slots[ index ].expired():
                if index - 1 == len( self.__slots ):
                    # The last one
                    del self.__slots[ index ]
                else:
                    # Just nullify it
                    self.__slots[ index ].msg = None
                    self.__slots[ index ].till = None
        return

