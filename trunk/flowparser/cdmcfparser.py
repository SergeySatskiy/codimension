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

""" The file holds types and a glue code between python and C python
    code parser """

from _cdmcfparser import version, getControlFlowFromMemory as getCFlow
from cfiface import ControlFlowParserIFace
from flow import ControlFlow



def getControlFlowFromMemory( content ):
    " Builds the control flow info from memory "

    controlFlow = ControlFlow()
    callbacks = ControlFlowParserIFace( controlFlow )
    getCFlow( callbacks, content )
    return controlFlow


def getControlFlowFromFile( fileName ):
    """ Builds the control flow info from file.
        Always returns serialized object. """

    f = open( fileName )
    content = f.read()
    f.close()

    controlFlow = getControlFlowFromMemory( content )
    controlFlow.serialize( content )
    return controlFlow


def getVersion():
    " Provides the control flow parser version "
    return version

