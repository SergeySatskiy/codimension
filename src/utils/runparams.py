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

"""Running/debugging session parameters"""

from copy import deepcopy


# These constants are used throughout the code to identify the type of run
RUN = 0
PROFILE = 1
DEBUG = 2


class RunParameters:

    """Stores the script run parameters"""

    InheritParentEnv = 0
    InheritParentEnvPlus = 1
    SpecificEnvironment = 2

    def __init__(self):
        self.__params = deepcopy(DEFAULT_RUN_PARAMETERS)

    def __getitem__(self, key):
        return self.__params[key]

    def __setitem__(self, key, value):
        self.__params[key] = value

    def isDefault(self):
        """Returns True if all the values are default"""
        return self.__params == DEFAULT_RUN_PARAMETERS

    def toJSON(self):
        """Converts the instance to a serializable structure"""
        return {'__class__': 'RunParameters',
                '__values__': self.__params}

    def fromJSON(self, jsonObj):
        """Populates the values from the json object"""
        self.__params = jsonObj['__values__']


# Default parameters
DEFAULT_RUN_PARAMETERS = {
    # Cmd line arguments
    'arguments': '',

    # Working dir part
    'useScriptLocation': True,
    'specificDir': '',

    # Environment
    'envType': RunParameters.InheritParentEnv,
    'additionToParentEnv': {},
    'specificEnv': {},

    # Path to python
    'useInherited': True,
    'customInterpreter': '',

    # Way to run
    'redirected': True,
    'customTerminal': ''}


# JSON serialization/deserialization support
# implementation idea is taken from here:
# http://www.diveintopython3.net/serializing.html
def toJSON(pythonObj):
    """Custom serialization"""
    if isinstance(pythonObj, RunParameters):
        return pythonObj.toJSON()
    raise TypeError(repr(pythonObj) + ' is not JSON serializable')


def fromJSON(jsonObj):
    """Custom deserialization"""
    if '__class__' in jsonObj:
        if jsonObj['__class__'] == 'RunParameters':
            params = RunParameters()
            params.fromJSON(jsonObj)
            return params
    return jsonObj
