# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# The file was taken from eric 6 and adopted for codimension.
# Original copyright:
# Copyright (c) 2016 - 2017 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Module implementing classes and functions to dump variable contents"""

#
# This code was inspired by pydevd.
#

MAX_ITEMS_TO_HANDLE = 300
TOO_LARGE_MESSAGE = ("Too large to show contents. Max items to show: " +
                     str(MAX_ITEMS_TO_HANDLE))
TOO_LARGE_ATTRIBUTE = "Too large to be handled"


#
# Classes implementing resolvers for various compund types
#


class BaseResolver(object):

    """Base class of the resolver class tree"""

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        raise NotImplementedError

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        raise NotImplementedError


#
# Default Resolver
#
class DefaultResolver(BaseResolver):

    """Class used to resolve the default way"""

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        return getattr(var, attribute, None)

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        names = dir(var)
        if not names and hasattr(var, "__members__"):
            names = var.__members__

        retVal = {}
        for name in names:
            try:
                attribute = getattr(var, name)
                retVal[name] = attribute
            except Exception:
                pass    # if we can't get it, simply ignore it
        return retVal


#
# Resolver for Dictionaries
#
class DictResolver(BaseResolver):

    """Class used to resolve from a dictionary"""

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        if attribute in ('___len___', TOO_LARGE_ATTRIBUTE):
            return None

        if "(ID:" not in attribute:
            try:
                return var[attribute]
            except Exception:
                return getattr(var, attribute, None)

        expectedID = int(attribute.split("(ID:")[-1][:-1])
        for key, value in var.items():
            if id(key) == expectedID:
                return value

        return None

    @staticmethod
    def keyToStr(key):
        """Provides a string representation for a key"""
        if isinstance(key, str):
            return repr(key)
        return key

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        retVal = {}
        count = 0
        for key, value in var.items():
            count += 1
            key = "{0} (ID:{1})".format(self.keyToStr(key), id(key))
            retVal[key] = value
            if count > MAX_ITEMS_TO_HANDLE:
                retVal[TOO_LARGE_ATTRIBUTE] = TOO_LARGE_MESSAGE
                break

        retVal["___len___"] = len(var)

        # in case it has additional fields
        additionals = defaultResolver.getDictionary(var)
        retVal.update(additionals)
        return retVal


#
# Resolver for Lists and Tuples
#
class ListResolver(BaseResolver):

    """Class used to resolve from a tuple or list"""

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        if attribute in ('___len___', TOO_LARGE_ATTRIBUTE):
            return None

        try:
            return var[int(attribute)]
        except Exception:
            return getattr(var, attribute, None)

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        retVal = {}
        count = 0
        for value in var:
            retVal[str(count)] = value
            count += 1
            if count > MAX_ITEMS_TO_HANDLE:
                retVal[TOO_LARGE_ATTRIBUTE] = TOO_LARGE_MESSAGE
                break

        retVal["___len___"] = len(var)

        # in case it has additional fields
        additionals = defaultResolver.getDictionary(var)
        retVal.update(additionals)
        return retVal


#
# Resolver for Sets and Frozensets
#
class SetResolver(BaseResolver):

    """Class used to resolve from a set or frozenset"""

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        if attribute in ('___len___', TOO_LARGE_ATTRIBUTE):
            return None

        if attribute.startswith("ID: "):
            attribute = attribute.split(None, 1)[1]
        try:
            attribute = int(attribute)
        except Exception:
            return getattr(var, attribute, None)

        for varAttr in var:
            if id(varAttr) == attribute:
                return varAttr
        return None

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        retVal = {}
        count = 0
        for value in var:
            count += 1
            retVal["ID: " + str(id(value))] = value
            if count > MAX_ITEMS_TO_HANDLE:
                retVal[TOO_LARGE_ATTRIBUTE] = TOO_LARGE_MESSAGE
                break

        retVal["___len___"] = len(var)

        # in case it has additional fields
        additionals = defaultResolver.getDictionary(var)
        retVal.update(additionals)
        return retVal


#
# Resolver for Numpy Arrays
#
class NdArrayResolver(BaseResolver):

    """Class used to resolve from numpy ndarray including some meta data"""

    @staticmethod
    def __isNumeric(arr):
        """Checks if an array is of a numeric type"""
        try:
            return arr.dtype.kind in 'biufc'
        except AttributeError:
            return False

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        if attribute == '__internals__':
            return defaultResolver.getDictionary(var)

        if attribute == 'min':
            if self.__isNumeric(var):
                return var.min()
            return None

        if attribute == 'max':
            if self.__isNumeric(var):
                return var.max()
            return None

        if attribute == 'mean':
            if self.__isNumeric(var):
                return var.mean()
            return None

        if attribute == 'shape':
            return var.shape

        if attribute == 'dtype':
            return var.dtype

        if attribute == 'size':
            return var.size

        if attribute.startswith('['):
            container = NdArrayItemsContainer()
            count = 0
            for element in var:
                setattr(container, str(count), element)
                count += 1
                if count > MAX_ITEMS_TO_HANDLE:
                    setattr(container, TOO_LARGE_ATTRIBUTE, TOO_LARGE_MESSAGE)
                    break
            return container
        return None

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        retVal = {}
        retVal['__internals__'] = defaultResolver.getDictionary(var)
        if var.size > 1024 * 1024:
            retVal['min'] = 'ndarray too big, calculating min would ' \
                            'slow down debugging'
            retVal['max'] = 'ndarray too big, calculating max would ' \
                            'slow down debugging'
        else:
            if self.__isNumeric(var):
                retVal['min'] = var.min()
                retVal['max'] = var.max()
                retVal['mean'] = var.mean()
            else:
                retVal['min'] = 'not a numeric object'
                retVal['max'] = 'not a numeric object'
                retVal['mean'] = 'not a numeric object'
        retVal['shape'] = var.shape
        retVal['dtype'] = var.dtype
        retVal['size'] = var.size
        retVal['[0:{0}]'.format(
            len(var) - 1)] = list(var[0:MAX_ITEMS_TO_HANDLE])
        return retVal


class NdArrayItemsContainer:

    """Class to store ndarray items"""

    pass


#
# Resolver for Django Multi Value Dictionaries
#
class MultiValueDictResolver(DictResolver):

    """Class used to resolve from Django multi value dictionaries"""

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        if attribute in ('___len___', TOO_LARGE_ATTRIBUTE):
            return None

        if "(ID:" not in attribute:
            try:
                return var[attribute]
            except Exception:
                return getattr(var, attribute, None)

        expectedID = int(attribute.split("(ID:")[-1][:-1])
        for key in var.keys():
            if id(key) == expectedID:
                value = var.getlist(key)
                return value
        return None

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        retVal = {}
        count = 0
        for key in var.keys():
            count += 1
            value = var.getlist(key)
            key = "{0} (ID:{1})".format(self.keyToStr(key), id(key))
            retVal[key] = value
            if count > MAX_ITEMS_TO_HANDLE:
                retVal[TOO_LARGE_ATTRIBUTE] = TOO_LARGE_MESSAGE
                break

        retVal["___len___"] = len(var)
        return retVal


#
# Resolver for array.array
#
class ArrayResolver(BaseResolver):

    """Class used to resolve from array.array including some meta data"""

    TypeCodeMap = {
        "b": "int (signed char)",
        "B": "int (unsigned char)",
        "u": "Unicode character (Py_UNICODE)",
        "h": "int (signed short)",
        "H": "int (unsigned short)",
        "i": "int (signed int)",
        "I": "int (unsigned int)",
        "l": "int (signed long)",
        "L": "int (unsigned long)",
        "q": "int (signed long long)",
        "Q": "int (unsigned long long)",
        "f": "float (float)",
        "d": "float (double)",
    }

    def resolve(self, var, attribute):
        """Provides an attribute from a variable"""
        if attribute == 'itemsize':
            return var.itemsize

        if attribute == 'typecode':
            return var.typecode

        if attribute == 'type':
            if var.typecode in ArrayResolver.TypeCodeMap:
                return ArrayResolver.TypeCodeMap[var.typecode]
            return 'illegal type'

        if attribute.startswith('['):
            container = ArrayItemsContainer()
            count = 0
            for element in var:
                setattr(container, str(count), element)
                count += 1
                if count > MAX_ITEMS_TO_HANDLE:
                    setattr(container, TOO_LARGE_ATTRIBUTE, TOO_LARGE_MESSAGE)
                    break
            return container
        return None

    def getDictionary(self, var):
        """Provides the attributes of a variable as a dictionary"""
        retVal = {}
        retVal['typecode'] = var.typecode
        if var.typecode in ArrayResolver.TypeCodeMap:
            retVal['type'] = ArrayResolver.TypeCodeMap[var.typecode]
        else:
            retVal['type'] = 'illegal type'
        retVal['itemsize'] = var.itemsize
        retVal['[0:{0}]'.format(
            len(var) - 1)] = var.tolist()[0:MAX_ITEMS_TO_HANDLE]
        return retVal


class ArrayItemsContainer:

    """Class to store array.array items"""

    pass


defaultResolver = DefaultResolver()
dictResolver = DictResolver()
listResolver = ListResolver()
setResolver = SetResolver()
ndarrayResolver = NdArrayResolver()
multiValueDictResolver = MultiValueDictResolver()
arrayResolver = ArrayResolver()


#
# Methods to determine the type of a variable and the
# resolver class to use
#

_TypeMap = None


def _initTypeMap():
    """Initializes the type map"""
    global _TypeMap

    _TypeMap = [
        (type(None), None),
        (int, None),
        (float, None),
        (complex, None),
        (str, None),
        (tuple, listResolver),
        (list, listResolver),
        (dict, dictResolver)]

    try:
        _TypeMap.append((long, None))               # pylint: disable=E0602
    except Exception:
        pass    # not available on all python versions

    try:
        _TypeMap.append((unicode, None))            # pylint: disable=E0602
    except Exception:
        pass    # not available on all python versions

    try:
        _TypeMap.append((set, setResolver))         # pylint: disable=E0602
    except Exception:
        pass    # not available on all python versions

    try:
        _TypeMap.append((frozenset, setResolver))   # pylint: disable=E0602
    except Exception:
        pass    # not available on all python versions

    try:
        import array
        _TypeMap.append((array.array, arrayResolver))
    except ImportError:
        pass  # array.array may not be available

    try:
        import numpy
        _TypeMap.append((numpy.ndarray, ndarrayResolver))
    except ImportError:
        pass  # numpy may not be installed

    try:
        from django.utils.datastructures import MultiValueDict
        _TypeMap.insert(0, (MultiValueDict, multiValueDictResolver))
        # it should go before dict
    except ImportError:
        pass  # django may not be installed


def getType(obj):
    """Provides the type information for an object"""
    typeObject = type(obj)
    typeName = typeObject.__name__
    typeStr = str(typeObject)[8:-2]

    if typeStr.startswith(("PyQt5.", "PyQt4.")):
        resolver = None
    else:
        if _TypeMap is None:
            _initTypeMap()

        for typeData in _TypeMap:
            if isinstance(obj, typeData[0]):
                resolver = typeData[1]
                break
        else:
            resolver = defaultResolver
    return typeObject, typeName, typeStr, resolver
