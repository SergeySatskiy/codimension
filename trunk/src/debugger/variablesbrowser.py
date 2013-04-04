#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011  Sergey Satskiy <sergey.satskiy@gmail.com>
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

""" The debugger namespace viewer implementation """


from PyQt4.QtCore import Qt, SIGNAL, QRegExp, QString, QStringList
from PyQt4.QtGui import QAbstractItemView, QHeaderView, QTreeWidget
from ui.itemdelegates  import NoOutlineHeightDelegate
from utils.encoding import toUnicode
from variableitems import ( VariableItem, SpecialVariableItem,
                            ArrayElementVariableItem,
                            SpecialArrayElementVariableItem )


NONPRINTABLE = QRegExp( r"""(\\x\d\d)+""" )
VARNAME_CLASS_1 = QRegExp( r'<.*(instance|object) at 0x.*>(\[\]|\{\}|\(\))' )
VARNAME_CLASS_2 = QRegExp( r'<class .* at 0x.*>(\[\]|\{\}|\(\))' )
VARTYPE_CLASS = QRegExp( 'class .*' )
VARVALUE_CLASS_1 = QRegExp( '<.*(instance|object) at 0x.*>' )
VARVALUE_CLASS_2 = QRegExp( '<class .* at 0x.*>' )
VARNAME_SPECIAL_ARRAY_ELEMENT = QRegExp( r'^\d+(\[\]|\{\}|\(\))$' )
VARNAME_ARRAY_ELEMENT = QRegExp( r'^\d+$' )


VARIABLE_DISPLAY_TYPE = {
    '__':                           'Hidden Attributes',
    'nonetype':                     'None',
    'type':                         'Type',
    'bool':                         'Boolean',
    'int':                          'Integer',
    'long':                         'Long Integer',
    'float':                        'Float',
    'complex':                      'Complex',
    'str':                          'String',
    'unicode':                      'Unicode String',
    'tuple':                        'Tuple',
    'list':                         'List/Array',
    'dict':                         'Dictionary/Hash/Map',
    'dict-proxy':                   'Dictionary Proxy',
    'set':                          'Set',
    'file':                         'File',
    'xrange':                       'X Range',
    'slice':                        'Slice',
    'buffer':                       'Buffer',
    'class':                        'Class',
    'instance':                     'Class Instance',
    'classobj':                     'Class Instance',
    'instance method':              'Class Method',
    'property':                     'Class Property',
    'generator':                    'Generator',
    'function':                     'Function',
    'builtin_function_or_method':   'Builtin Function',
    'code':                         'Code',
    'module':                       'Module',
    'ellipsis':                     'Ellipsis',
    'traceback':                    'Traceback',
    'frame':                        'Frame',
    'other':                        'Other' }



class VariablesBrowser( QTreeWidget ):
    " Variables browser implementation "

    def __init__( self, parent = None ):
        QTreeWidget.__init__( self, parent )

        self.setRootIsDecorated( True )
        self.setAlternatingRowColors( True )
        self.setUniformRowHeights( True )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        self.setSelectionBehavior( QAbstractItemView.SelectRows )

        self.setHeaderLabels( QStringList() << "Name" << "Value" << "Type" )
        header = self.header()
        header.setSortIndicator( 0, Qt.AscendingOrder )
        header.setSortIndicatorShown( True )
        header.setClickable( True )
        header.setStretchLastSection( True )

        self.connect( self, SIGNAL( "itemExpanded(QTreeWidgetItem*)"), self.__expandItemSignal )
        self.connect( self, SIGNAL( "itemCollapsed(QTreeWidgetItem*)"), self.collapseItem )

        self.resortEnabled = True
        self.openItems = []
        self.framenr = 0
        return

    def __findItem( self, slist, column, node = None ):
        """
        Searches for an item.

        It is used to find a specific item in column,
        that is a child of node. If node is None, a child of the
        QTreeWidget is searched.

        @param slist searchlist (list of strings or QStrings)
        @param column index of column to search in (int)
        @param node start point of the search
        @return the found item or None
        """
        if node is None:
            count = self.topLevelItemCount()
        else:
            count = node.childCount()

        for index in xrange( count ):
            if node is None:
                item = self.topLevelItem( index )
            else:
                item = node.child( index )

            if QString.compare( item.text( column ), slist[ 0 ] ) == 0:
                if len( slist ) > 1:
                    item = self.__findItem( slist[ 1 : ], column, item )
                return item

        return None

    def __clearScopeVariables( self, areGlobals ):
        " Removes those variables which belong to the specified frame "
        count = self.topLevelItemCount()
        for index in xrange( count - 1, -1, -1 ):
            item = self.topLevelItem( index )
            if item.isGlobal() == areGlobals:
                self.takeTopLevelItem( index )
        return

    def showVariables( self, areGlobals, vlist, frmnr ):
        """
        Shows variables list.

        @param vlist the list of variables to be displayed. Each
                listentry is a tuple of three values.
                <ul>
                <li>the variable name (string)</li>
                <li>the variables type (string)</li>
                <li>the variables value (string)</li>
                </ul
        @param frmnr frame number (0 is the current frame) (int)
        """
        self.current = self.currentItem()
        if self.current:
            self.curpathlist = self.__buildTreePath( self.current )
        self.__clearScopeVariables( areGlobals )
        self.__scrollToItem = None
        self.framenr = frmnr

        if len( vlist ):
            self.resortEnabled = False
            for ( var, vtype, value ) in vlist:
                self.__addItem( None, areGlobals, vtype, var, value )

            # reexpand tree
            openItems = self.openItems[ : ]
            openItems.sort()
            self.openItems = []
            for itemPath in openItems:
                itm = self.__findItem( itemPath, 0 )
                if itm is not None:
                    self.expandItem( itm )
                else:
                    self.openItems.append( itemPath )

            if self.current:
                citm = self.__findItem( self.curpathlist, 0 )
                if citm:
                    self.setCurrentItem( citm )
                    self.setItemSelected( citm, True )
                    self.scrollToItem( citm, QAbstractItemView.PositionAtTop )
                    self.current = None

            self.__resizeSections()

            self.resortEnabled = True
            self.__resort()
        return

    def __resizeSections( self ):
        " Resizes the variable sections "
        if self.topLevelItemCount() == 0:
            return

        header = self.header()
        nameSectionSize = header.sectionSize( 0 )
        header.resizeSections( QHeaderView.ResizeToContents )
        if header.sectionSize( 0 ) < nameSectionSize:
            header.resizeSection( 0, nameSectionSize )
        return

    def showVariable( self, isGlobal, vlist ):
        " Shows variables in a list "

        # vlist the list of subitems to be displayed. The first element gives
        # the path of the parent variable. Each other listentry is a tuple of
        # three values:
        #   the variable name (string)
        #   the variables type (string)
        #   the variables value (string)

        resortEnabled = self.resortEnabled
        self.resortEnabled = False
        if self.current is None:
            self.current = self.currentItem()
            if self.current:
                self.curpathlist = self.__buildTreePath( self.current )

        subelementsAdded = False
        if vlist:
            item = self.__findItem( vlist[ 0 ], 0 )
            for var, vtype, value in vlist[ 1 : ]:
                self.__addItem( item, isGlobal, vtype, var, value )
            subelementsAdded = True

        # reexpand tree
        openItems = self.openItems[ : ]
        openItems.sort()
        self.openItems = []
        for itemPath in openItems:
            item = self.__findItem( itemPath, 0 )
            if item is not None and not item.isExpanded():
                if item.populated:
                    self.blockSignals( True )
                    item.setExpanded( True )
                    self.blockSignals( False )
                else:
                    self.expandItem( item )
        self.openItems = openItems[ : ]

        if self.current:
            citm = self.__findItem( self.curpathlist, 0 )
            if citm:
                self.setCurrentItem( citm )
                self.setItemSelected( citm, True )
                if self.__scrollToItem:
                    self.scrollToItem( self.__scrollToItem,
                                       QAbstractItemView.PositionAtTop )
                else:
                    self.scrollToItem( citm, QAbstractItemView.PositionAtTop )
                self.current = None
        elif self.__scrollToItem:
            self.scrollToItem( self.__scrollToItem,
                               QAbstractItemView.PositionAtTop )

        self.__resizeSections()

        self.resortEnabled = resortEnabled
        self.__resort()
        return

    def __generateItem( self, parentItem, isGlobal,
                              varName, varValue, varType, isSpecial = False ):
        " Generates an appropriate variable item "
        if isSpecial:
            if VARNAME_CLASS_1.exactMatch( varName ) or \
               VARNAME_CLASS_2.exactMatch( varName ):
                isSpecial = False

        if VARTYPE_CLASS.exactMatch( varType ):
            return SpecialVariableItem( parentItem, isGlobal,
                                        varName, varValue, varType[ 7 : -1 ],
                                        self.framenr )

        elif varType != "void *" and \
            ( VARVALUE_CLASS_1.exactMatch( varValue ) or \
               VARVALUE_CLASS_2.exactMatch( varValue ) or \
               isSpecial ):
            if VARNAME_SPECIAL_ARRAY_ELEMENT.exactMatch( varName ):
                return SpecialArrayElementVariableItem( parentItem, isGlobal,
                                                        varName, varValue, varType,
                                                        self.framenr )
            return SpecialVariableItem( parentItem, isGlobal,
                                        varName, varValue, varType,
                                        self.framenr )
        else:
            if isinstance( varValue, str ):
                varValue = QString.fromLocal8Bit( varValue )
            if VARNAME_ARRAY_ELEMENT.exactMatch( varName ):
                return ArrayElementVariableItem( parentItem, isGlobal,
                                                 varName, varValue, varType )
            return VariableItem( parentItem, isGlobal,
                                 varName, varValue, varType )

        print "WARNING: Reached the end without forming a variable!"

    def __unicode( self, value ):
        " Converts a string to unicode "
        if type( value ) is type( u"" ):
            return value

        try:
            return unicode( value, "utf-8" )
        except TypeError:
            return str( value )
        except UnicodeError:
            return toUnicode( value )

    def __getDisplayType( self, varType ):
        " Provides a variable type for display purpose "
        key = varType.lower()
        if key in VARIABLE_DISPLAY_TYPE:
            return VARIABLE_DISPLAY_TYPE[ key ]
        return varType

    def __addItem( self, parentItem, isGlobal, varType, varName, varValue ):
        " Adds a new item to the children of the parentItem "
        if parentItem is None:
            parentItem = self

        displayType = self.__getDisplayType( varType )
        if varType in [ 'list', 'Array', 'tuple', 'dict', 'Hash' ]:
            return self.__generateItem( parentItem, isGlobal,
                                        varName, str( varValue ) + " item(s)",
                                        displayType,
                                        True )
        if varType in [ 'unicode', 'str' ]:
            if NONPRINTABLE.indexIn( varValue ) != -1:
                stringValue = varValue
            else:
                try:
                    stringValue = eval( varValue )
                except:
                    stringValue = varValue
            return self.__generateItem( parentItem, isGlobal,
                                        varName, self.__unicode( stringValue ),
                                        displayType )

        return self.__generateItem( parentItem, isGlobal,
                                    varName, varValue, displayType )

    def mouseDoubleClickEvent( self, mouseEvent ):
        item = self.itemAt( mouseEvent.pos() )
        print "Double click detected"
        return

    def __buildTreePath( self, item ):
        " Builds up a path from the top to the given item "
        name = unicode( item.text( 0 ) )
        pathList = [ name ]

        parent = item.parent()
        # build up a path from the top to the item
        while parent is not None:
            parentVariableName = unicode( parent.text( 0 ) )
            pathList.insert( 0, parentVariableName )
            parent = parent.parent()

        return pathList[ : ]

    def __expandItemSignal( self, parentItem ):
        " Handles the expanded signal "
        self.expandItem( parentItem )
        self.__scrollToItem = parentItem
        return

    def expandItem( self, parentItem ):
        " Handles the expanded signal "
        pathList = self.__buildTreePath( parentItem )
        self.openItems.append( pathList )
        if parentItem.populated:
            return

        try:
            parentItem.expand()
            self.__resort()
        except AttributeError:
            QTreeWidget.expandItem( self, parentItem )
        return

    def collapseItem( self, parentItem ):
        " Handles the collapsed signal "
        pathList = self.__buildTreePath( parentItem )
        self.openItems.remove( pathList )

        try:
            parentItem.collapse()
        except AttributeError:
            QTreeWidget.collapseItem( self, parentItem )
        return

    def __resort( self ):
        " Resorts the tree "
        if self.resortEnabled:
            self.sortItems( self.sortColumn(),
                            self.header().sortIndicatorOrder() )
        return

