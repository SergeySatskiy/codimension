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

import _cdmpyparser
from sys import maxint



def trim_docstring( docstring ):
    " Taken from http://www.python.org/dev/peps/pep-0257/ "

    if not docstring:
        return ''

    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()

    # Determine minimum indentation (first line doesn't count):
    indent = maxint
    for line in lines[ 1: ]:
        stripped = line.lstrip()
        if stripped:
            indent = min( indent, len( line ) - len( stripped ) )

    # Remove indentation (first line is special):
    lines[ 0 ] = lines[ 0 ].strip()
    if indent < maxint:
        index = 1
        for line in lines[ 1: ]:
            lines[ index ] = line[ indent: ].rstrip()
            index += 1

    # Strip off trailing and leading blank lines:
    while lines and not lines[ -1 ]:
        del lines[ -1 ]
    while lines and not lines[ 0 ]:
        del lines[ 0 ]

    # Return a single string:
    return '\n'.join( lines )



class ModuleInfoBase():
    " Common part for the module information "

    def __init__( self, name, line, pos, absPosition ):
        self.name = name        # Item identifier
        self.line = line        # Line number where item is found (1-based)
        self.pos  = pos         # Item position in the line (1-based)

        self.absPosition = absPosition    # Absolute position of the first item
                                          # identifier character starting from
                                          # the beginning of the input stream
                                          # (0-based)
        return

    def isPrivate( self ):
        " True if it is private "
        return self.name.startswith( '__' )

    def isProtected( self ):
        " True if it is protected "
        return not self.isPrivate() and self.name.startswith( '_' )

    def _getLPA( self ):
        " Provides line, pos and absPosition line as string "
        return str( self.line ) + ":" + \
               str( self.pos ) + ":" + \
               str( self.absPosition )

    def getDisplayName( self ):
        """ Provides a name for display purpose.
            It is going to be overriden in deriving classes """
        return self.name


class Encoding( ModuleInfoBase ):
    " Holds information about encoding string "

    def __init__( self, encName, line, pos, absPosition ):
        ModuleInfoBase.__init__( self, encName, line, pos, absPosition )
        return

    def __str__( self ):
        return "Encoding[" + self._getLPA() + "]: '" + self.name + "'"


class ImportWhat( ModuleInfoBase ):
    " Holds information about a single imported item "

    def __init__( self, whatName, line, pos, absPosition ):
        ModuleInfoBase.__init__( self, whatName, line, pos, absPosition )
        self.alias = ""
        return

    def __str__( self ):
        if self.alias == "":
            return self.name + "[" + self._getLPA() + "]"
        return self.name + "[" + self._getLPA() + "] as " + self.alias

    def getDisplayName( self ):
        " Provides a name for display purpose respecting the alias "
        if self.alias == "":
            return self.name
        return self.name + " as " + self.alias


class Import( ModuleInfoBase ):
    " Holds information about a single import name "

    def __init__( self, importName, line, pos, absPosition ):
        ModuleInfoBase.__init__( self, importName, line, pos, absPosition )
        self.alias = ""
        self.what = []
        return

    def __str__( self ):
        out = "Import[" + self._getLPA() + "]: '" + self.name + "'"
        if self.alias != "":
            out += " as '" + self.alias + "'"
        whatPart = ""
        for item in self.what:
            whatPart += "\n    " + str( item )
        return out + whatPart

    def getDisplayName( self ):
        " Provides a name for display purpose respecting the alias "
        if self.alias == "":
            return self.name
        return self.name + " as " + self.alias


class Global( ModuleInfoBase ):
    " Holds information about a single global variable "

    def __init__( self, globalName, line, pos, absPosition ):
        ModuleInfoBase.__init__( self, globalName, line, pos, absPosition )
        return

    def __str__( self ):
        return "Global[" + self._getLPA() + "]: '" + self.name + "'"


class ClassAttribute( ModuleInfoBase ):
    " Holds information about a class attribute "

    def __init__( self, attrName, line, pos, absPosition ):
        ModuleInfoBase.__init__( self, attrName, line, pos, absPosition )
        return

    def __str__( self ):
        return "Class attribute[" + self._getLPA() + "]: '" + self.name + "'"


class InstanceAttribute( ModuleInfoBase ):
    " Holds information about a class instance attribute "

    def __init__( self, attrName, line, pos, absPosition ):
        ModuleInfoBase.__init__( self, attrName, line, pos, absPosition )
        return

    def __str__( self ):
        return "Instance attribute[" + self._getLPA() + "]: '" + self.name + "'"


class Decorator( ModuleInfoBase ):
    " Holds information about a class/function decorator "

    def __init__( self, decorName, line, pos, absPosition ):
        ModuleInfoBase.__init__( self, decorName, line, pos, absPosition )
        self.arguments = []
        return

    def __str__( self ):
        val = "Decorator[" + self._getLPA() + "]: '" + self.name
        if self.arguments:
            val += "( "
            first = True
            for item in self.arguments:
                if first:
                    val += item
                    first = False
                else:
                    val += ", " + item
            val += " )'"
        return val

    def getDisplayName( self ):
        " Provides a name for display purpose "
        displayName = self.name
        if self.arguments:
            displayName += "( " + ", ".join( self.arguments ) + " )"
        return displayName


class Docstring():
    " Holds a docstring information "

    def __init__( self, text, line ):
        self.line = line
        self.text = text
        return

    def __str__( self ):
        return "Docstring[" + str( self.line ) + "]: '" + self.text + "'"


class Function( ModuleInfoBase ):
    " Holds information about a single function"

    def __init__( self, funcName, line, pos, absPosition,
                        keywordLine, keywordPos,
                        colonLine, colonPos ):
        ModuleInfoBase.__init__( self, funcName, line, pos, absPosition )

        self.keywordLine = keywordLine  # line where 'def' keyword
                                        # starts (1-based).
        self.keywordPos = keywordPos    # pos where 'def' keyword
                                        # starts (1-based).
        self.colonLine = colonLine      # line where ':' char starts (1-based)
        self.colonPos = colonPos        # pos where ':' char starts (1-based)

        self.docstring = None
        self.arguments = []
        self.decorators = []
        self.functions = []     # nested functions
        self.classes = []       # nested classes
        return

    def isStaticMethod( self ):
        " Returns True if it is a static method "
        for item in self.decorators:
            if item.name == 'staticmethod':
                return True
        return False

    def niceStringify( self, level ):
        " Returns a string representation with new lines and shifts "

        out = level * "    " + "Function[" + str(self.keywordLine) + \
                                       ":" + str(self.keywordPos) + \
                                       ":" + self._getLPA() + \
                                       ":" + str(self.colonLine) + \
                                       ":" + str(self.colonPos) + \
                                       "]: '" + self.name + "'"
        for item in self.arguments:
            out += '\n' + level * "    " + "Argument: '" + item + "'"
        for item in self.decorators:
            out += '\n' + level * "    " + str( item )
        if self.docstring is not None:
            out += '\n' + level * "    " + str( self.docstring )
        for item in self.functions:
            out += '\n' + item.niceStringify( level + 1 )
        for item in self.classes:
            out += '\n' + item.niceStringify( level + 1 )
        return out

    def getDisplayName( self ):
        " Provides a name for display purpose "
        displayName = self.name + "("
        if self.arguments:
            displayName += " " + ", ".join( self.arguments ) + " "
        displayName += ")"
        return displayName


class Class( ModuleInfoBase ):
    " Holds information about a single class"

    def __init__( self, className, line, pos, absPosition,
                        keywordLine, keywordPos,
                        colonLine, colonPos ):
        ModuleInfoBase.__init__( self, className, line, pos, absPosition )

        self.keywordLine = keywordLine  # line where 'def' keyword
                                        # starts (1-based).
        self.keywordPos = keywordPos    # pos where 'def' keyword
                                        # starts (1-based).
        self.colonLine = colonLine      # line where ':' char starts (1-based)
        self.colonPos = colonPos        # pos where ':' char starts (1-based)

        self.docstring = None
        self.base = []
        self.decorators = []
        self.classAttributes = []
        self.instanceAttributes = []
        self.functions = []             # member functions
        self.classes = []               # nested classes
        return

    def niceStringify( self, level ):
        " Returns a string representation with new lines and shifts "

        out = level * "    " + "Class[" + str(self.keywordLine) + \
                                    ":" + str(self.keywordPos) + \
                                    ":" + self._getLPA() + \
                                    ":" + str(self.colonLine) + \
                                    ":" + str(self.colonPos) + \
                                    "]: '" + self.name + "'"
        for item in self.base:
            out += '\n' + level * "    " + "Base class: '" + item + "'"
        for item in self.decorators:
            out += '\n' + level * "    " + str( item )
        if self.docstring is not None:
            out += '\n' + level * "    " + str( self.docstring )
        for item in self.classAttributes:
            out += '\n' + level * "    " + str(item)
        for item in self.instanceAttributes:
            out += '\n' + level * "    " + str(item)
        for item in self.functions:
            out += '\n' + item.niceStringify( level + 1 )
        for item in self.classes:
            out += '\n' + item.niceStringify( level + 1 )
        return out

    def getDisplayName( self ):
        " Provides a name for display purpose "
        displayName = self.name
        if self.base:
            displayName += "( " + ", ".join( self.base ) + " )"
        return displayName


class BriefModuleInfo():
    " Holds a single module content information "

    def __init__( self ):
        self.isOK = True

        self.docstring = None
        self.encoding = None
        self.imports = []
        self.globals = []
        self.functions = []
        self.classes = []
        self.errors = []
        self.lexerErrors = []

        self.objectsStack = []
        self.__lastImport = None
        return

    def niceStringify( self ):
        " Returns a string representation with new lines and shifts "

        out = ""
        if self.docstring is not None:
            out += str( self.docstring )
        if not self.encoding is None:
            if out != "":
                out += '\n'
            out += str( self.encoding )
        for item in self.imports:
            if out != "":
                out += '\n'
            out += str( item )
        for item in self.globals:
            if out != "":
                out += '\n'
            out += str( item )
        for item in self.functions:
            if out != "":
                out += '\n'
            out += item.niceStringify( 0 )
        for item in self.classes:
            if out != "":
                out += '\n'
            out += item.niceStringify( 0 )
        return out


    def flush( self ):
        " Flushes the collected information "
        self.__flushLevel( 0 )
        if self.__lastImport is not None:
            self.imports.append( self.__lastImport )
        return

    def __flushLevel( self, level ):
        " Merge the found objects to the required level "

        objectsCount = len( self.objectsStack )

        while objectsCount > level:
            lastIndex = objectsCount - 1
            if lastIndex == 0:
                # We have exactly one element in the stack
                if self.objectsStack[ 0 ].__class__.__name__ == "Class":
                    self.classes.append( self.objectsStack[ 0 ] )
                else:
                    self.functions.append( self.objectsStack[ 0 ] )
                self.objectsStack = []
                break

            # Append to the previous level
            if self.objectsStack[ lastIndex ].__class__.__name__ == "Class":
                self.objectsStack[ lastIndex - 1 ].classes. \
                        append( self.objectsStack[ lastIndex ] )
            else:
                self.objectsStack[ lastIndex - 1 ].functions. \
                        append( self.objectsStack[ lastIndex ] )

            del self.objectsStack[ lastIndex ]
            objectsCount -= 1

        return

    def _onEncoding( self, encString, line, pos, absPosition ):
        " Memorizes module encoding "
        self.encoding = Encoding( encString, line, pos, absPosition )
        return

    def _onGlobal( self, name, line, pos, absPosition, level ):
        " Memorizes a global variable "

        # level is ignored
        for item in self.globals:
            if item.name == name:
                return
        self.globals.append( Global( name, line, pos, absPosition ) )
        return

    def _onClass( self, name, line, pos, absPosition,
                        keywordLine, keywordPos,
                        colonLine, colonPos, level ):
        " Memorizes a class "
        self.__flushLevel( level )
        self.objectsStack.append( Class( name, line, pos, absPosition,
                                         keywordLine, keywordPos,
                                         colonLine, colonPos ) )
        return

    def _onFunction( self, name, line, pos, absPosition,
                           keywordLine, keywordPos,
                           colonLine, colonPos, level ):
        " Memorizes a function "
        self.__flushLevel( level )
        self.objectsStack.append( Function( name, line, pos, absPosition,
                                            keywordLine, keywordPos,
                                            colonLine, colonPos ) )
        return

    def _onImport( self, name, line, pos, absPosition ):
        " Memorizes an import "
        if self.__lastImport is not None:
            self.imports.append( self.__lastImport )
        self.__lastImport = Import( name, line, pos, absPosition )
        return

    def _onAs( self, name ):
        " Memorizes an alias for an import or an imported item "
        if self.__lastImport.what:
            self.__lastImport.what[ -1 ].alias = name
        else:
            self.__lastImport.alias = name
        return

    def _onWhat( self, name, line, pos, absPosition ):
        " Memorizes an imported item "
        self.__lastImport.what.append( ImportWhat( name, line, pos,
                                                         absPosition ) )
        return

    def _onClassAttribute( self, name, line, pos, absPosition, level ):
        " Memorizes a class attribute "
        # A class must be on the top of the stack
        attributes = self.objectsStack[ level ].classAttributes
        for item in attributes:
            if item.name == name:
                return
        attributes.append( ClassAttribute( name, line, pos, absPosition ) )
        return

    def _onInstanceAttribute( self, name, line, pos, absPosition, level ):
        " Memorizes a class instance attribute "
        # Instance attributes may appear in member functions only so we already
        # have a function on the stack of objects. To get the class object one
        # more step is required so we -1 here.
        attributes = self.objectsStack[ level - 1 ].instanceAttributes
        for item in attributes:
            if item.name == name:
                return
        attributes.append( InstanceAttribute( name, line, pos, absPosition ) )
        return

    def _onDecorator( self, name, line, pos, absPosition ):
        " Memorizes a function or a class decorator "
        # A class or a function must be on the top of the stack
        self.objectsStack[ -1 ].decorators.append( \
                                            Decorator( name, line, pos,
                                                       absPosition ) )
        return

    def _onDecoratorArgument( self, name ):
        " Memorizes a decorator argument "
        self.objectsStack[ -1 ].decorators[ -1 ].arguments.append( name )
        return

    def _onDocstring( self, docstr, line ):
        " Memorizes a function/class/module docstring "
        if self.objectsStack:
            self.objectsStack[ -1 ].docstring = \
                                 Docstring( trim_docstring( docstr ), line )
            return

        self.docstring = Docstring( trim_docstring( docstr ), line )
        return

    def _onArgument( self, name ):
        " Memorizes a function argument "
        self.objectsStack[ -1 ].arguments.append( name )
        return

    def _onBaseClass( self, name ):
        " Memorizes a class base class "
        # A class must be on the top of the stack
        self.objectsStack[ -1 ].base.append( name )
        return

    def _onError( self, message ):
        " Memorizies a parser error message "
        self.isOK = False
        if message.strip() != "":
            self.errors.append( message )
        return

    def _onLexerError( self, message ):
        " Memorizes a lexer error message "
        self.isOK = False
        if message.strip() != "":
            self.lexerErrors.append( message )
        return


def getBriefModuleInfoFromFile( fileName ):
    " Builds the brief module info from file "

    modInfo = BriefModuleInfo()
    _cdmpyparser.getBriefModuleInfoFromFile( modInfo, fileName )
    modInfo.flush()
    return modInfo


def getBriefModuleInfoFromMemory( content ):
    " Builds the brief module info from memory "

    modInfo = BriefModuleInfo()
    _cdmpyparser.getBriefModuleInfoFromMemory( modInfo, content )
    modInfo.flush()
    return modInfo

def getVersion():
    " Provides the parser version "
    return _cdmpyparser.version

