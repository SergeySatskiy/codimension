#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Running/debugging session parameters "


from copy import deepcopy

class RunParameters:
    " Stores the script run parameters "

    InheritParentEnv = 0
    InheritParentEnvPlus = 1
    SpecificEnvironment = 2

    def __init__(self):
        self.__dict__['__params'] = deepcopy(DEFAULT_RUN_PARAMETERS)
        return

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        if name in self.__dict__['__params']:
            return self.__dict__['__params'][name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self.__dict__['__params'][name] = value
        return

    def isDefault(self):
        " Returns True if all the values are default "
        for key in DEFAULT_RUN_PARAMETERS:
            if self.__dict__['__params'][key] != DEFAULT_RUN_PARAMETERS[key]:
                return False
        return True

    def toJSON(self):
        " Converts the instance to a serializable structure "
        return {'__class__': 'RunParameters',
                '__values__': self.__dict__['__params']}

    def fromJSON(self, jsonObj):
        " Populates the values from the json object "
        self.__dict__['__params'] = jsonObj['__values__']
        return


# Default parameters
DEFAULT_RUN_PARAMETERS = {
    # Cmd line arguments
    'arguments': "",

    # Working dir part
    'useScriptLocation': True,
    'specificDir': "",

    # Environment
    'envType': RunParameters.InheritParentEnv,
    'additionToParentEnv': {},
    'specificEnv': {},

    # Close terminal
    'closeTerminal': False}


# JSON serialization/deserialization support
# implementation idea is taken from here:
# http://www.diveintopython3.net/serializing.html
def toJSON(pythonObj):
    " Custom serialization "
    if isinstance(pythonObj, RunParameters):
        return pythonObj.toJSON()
    raise TypeError(repr(pythonObj) + ' is not JSON serializable')

def fromJSON(jsonObj):
    " Custom deserialization "
    if '__class__' in jsonObj:
        if jsonObj['__class__'] == 'RunParameters':
            params = RunParameters()
            params.fromJSON(jsonObj)
            return params
    return jsonObj
