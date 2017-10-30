# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2004 - 2014 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""Module implementing utilities to get a password and/or the current user name

getpass(prompt) - prompt for a password, with echo turned off
getuser() - get the user name from the environment or password database

This module is a replacement for the one found in the Python distribution. It
is to provide a debugger compatible variant of the functions mentioned above.
"""

__all__ = ["getpass", "getuser"]


def getuser():
    """Function to get the username from the environment or password database.

    First try various environment variables, then the password
    database.  This works on Windows as long as USERNAME is set.
    """
    # this is copied from the oroginal getpass.py

    import os

    for name in ('LOGNAME', 'USER', 'LNAME', 'USERNAME'):
        user = os.environ.get(name)
        if user:
            return user

    # If this fails, the exception will "explain" why
    import pwd
    return pwd.getpwuid(os.getuid())[0]


def getpass(prompt='Password: '):
    """Function to prompt for a password, with echo turned off"""
    return input(prompt, False)


unix_getpass = getpass
win_getpass = getpass
default_getpass = getpass
