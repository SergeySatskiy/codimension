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
from viewvariable import ViewVariableDialog


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
    'classobj':                     'Class',
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

    TYPE_INDICATORS = { 'list' : '[]', 'tuple' : '()', 'dict' : '{}',
                        'Array' : '[]', 'Hash' : '{}' }

    def __init__( self, debugger, parent = None ):
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

        self.connect( self, SIGNAL( "itemExpanded(QTreeWidgetItem*)"),
                      self.__expandItemSignal )
        self.connect( self, SIGNAL( "itemCollapsed(QTreeWidgetItem*)"),
                      self.collapseItem )

        self.resortEnabled = True
        self.openItems = []
        self.framenr = 0
        self.__debugger = debugger

        # Ugly filtering support
        self.__hideMCFFilter = False
        self.__scopeFilter = 0  # Global and local
        self.__filterIsSet = False
        self.__textFilters = []
        self.__textFiltersCount = 0

        self.setSortingEnabled( True )
        return

    def scrollTo( self, index, hint = QAbstractItemView.EnsureVisible ):
        """ Disables horizontal scrolling when a row is clicked.
            Found here: http://qt-project.org/faq/answer/how_can_i_disable_autoscroll_when_selecting_a_partially_displayed_column_in
        """
        oldValue = self.horizontalScrollBar().value()
        QTreeWidget.scrollTo( self, index, hint )
        self.horizontalScrollBar().setValue( oldValue )
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
            self.setSortingEnabled( False )
            for ( var, vtype, value ) in vlist:
                item = self.__addItem( None, areGlobals, vtype, var, value )
                item.setHidden( not self.__variableToShow( item.getName(),
                                                           item.isGlobal(),
                                                           item.getType() ) )

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
            self.setSortingEnabled( True )
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
        self.setSortingEnabled( False )

        if self.current is None:
            self.current = self.currentItem()
            if self.current:
                self.curpathlist = self.__buildTreePath( self.current )

        subelementsAdded = False
        if vlist:
            item = self.__findItem( vlist[ 0 ], 0 )
            for var, vtype, value in vlist[ 1 : ]:
                newItem = self.__addItem( item, isGlobal, vtype, var, value )
                newItem.setHidden( not self.__variableToShow( newItem.getName(),
                                                              newItem.isGlobal(),
                                                              newItem.getType() ) )
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
        if self.resortEnabled:
            self.setSortingEnabled( True )
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
            return SpecialVariableItem( parentItem, self.__debugger, isGlobal,
                                        varName, varValue, varType[ 7 : -1 ],
                                        self.framenr )

        elif varType != "void *" and \
            ( VARVALUE_CLASS_1.exactMatch( varValue ) or \
               VARVALUE_CLASS_2.exactMatch( varValue ) or \
               isSpecial ):
            if VARNAME_SPECIAL_ARRAY_ELEMENT.exactMatch( varName ):
                return SpecialArrayElementVariableItem( parentItem, self.__debugger, isGlobal,
                                                        varName, varValue, varType,
                                                        self.framenr )
            return SpecialVariableItem( parentItem, self.__debugger, isGlobal,
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

        # Decide what displayName will be
        if varType in self.TYPE_INDICATORS:
            varName += self.TYPE_INDICATORS[ varType ]

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
        if item is None:
            return

        childCount = item.childCount()
        if childCount == 0:
            # Show the dialog
            dlg = ViewVariableDialog( self.__getQualifiedName( item ),
                                      item.getType(), item.getValue(),
                                      item.isGlobal() )
            dlg.exec_()
            return

        QTreeWidget.mouseDoubleClickEvent( self, mouseEvent )
        return

    def __getQualifiedName( self, item ):
        " Provides a fully qualified name "
        name = item.getName()
        if name[ -2 : ] in [ '[]', '{}', '()' ]:
            name = name[ : -2 ]

        par = itm.parent()
        nlist = [ name ]
        # build up the fully qualified name
        while par is not None:
            pname = par.getName()
            if pname[ -2 : ] in [ '[]', '{}', '()' ]:
                if nlist[ 0 ].endswith( "." ):
                    nlist[ 0 ] = '[%s].' % nlist[ 0 ][ : -1 ]
                else:
                    nlist[ 0 ] = '[%s]' % nlist[ 0 ]
                nlist.insert( 0, pname[ : -2 ] )
            else:
                nlist.insert( 0, '%s.' % pname )
            par = par.parent()

        name = ''.join( nlist )
        return name

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

    def getShownAndTotalCounts( self ):
        " Provides the total number of variables and currently shown "
        total = self.topLevelItemCount()
        shownCount = 0
        for index in xrange( total ):
            if not self.topLevelItem( index ).isHidden():
                shownCount += 1
        return shownCount, total

    def clear( self ):
        " Resets everything "
        self.resortEnabled = True
        self.openItems = []
        self.framenr = 0

        QTreeWidget.clear( self )
        return

    def clearFilters( self ):
        " Clears the variable filters "
        self.__hideMCFFilter = False
        self.__scopeFilter = 0
        self.__textFilters = []
        self.__textFiltersCount = 0
        self.__filterIsSet = False
        return

    def setFilter( self, hideMCFFilter, scopeFilter, textFilter ):
        " Sets the new filter "
        self.__hideMCFFilter = hideMCFFilter
        self.__scopeFilter = scopeFilter

        self.__textFilters = []
        self.__textFiltersCount = 0
        for part in textFilter.split():
            regexp = QRegExp( part, Qt.CaseInsensitive, QRegExp.RegExp2 )
            self.__textFilters.append( regexp )
            self.__textFiltersCount += 1

        if self.__hideMCFFilter == False and \
           self.__scopeFilter == 0 and \
           self.__textFiltersCount == 0:
            self.__filterIsSet = False
        else:
            self.__filterIsSet = True
        self.__applyFilters()
        return

    def __applyFilters( self ):
        " Re-applies the filters to the list "
        resortEnabled = self.resortEnabled
        self.resortEnabled = False
        self.setSortingEnabled( False )

        for index in xrange( self.topLevelItemCount() ):
            item = self.topLevelItem( index )
            toShow = self.__variableToShow( item.getName(),
                                            item.isGlobal(),
                                            item.getType() )
            item.setHidden( not toShow )
            if toShow:
                self.__applyFiltersRecursively( item )

        self.__resizeSections()
        self.resortEnabled = resortEnabled
        if self.resortEnabled:
            self.setSortingEnabled( True )
        self.__resort()
        return

    def __applyFiltersRecursively( self, item ):
        " Applies the filter recursively to all the children of the given item "

        for index in xrange( item.childCount() ):
            childItem = item.child( index )
            if not hasattr( childItem, "getName" ):
                continue
            toShow = self.__variableToShow( childItem.getName(),
                                            childItem.isGlobal(),
                                            childItem.getType() )
            childItem.setHidden( not toShow )
            if toShow:
                self.__applyFiltersRecursively( childItem )
        return

    def __variableToShow( self, varName, isGlobal, varType ):
        " Checks if the given item should be shown "
        if not self.__filterIsSet:
            return True

        if self.__hideMCFFilter:
            if self.__isMCF( varType ):
                return False

        # Something is set so start checking
        varName = str( varName )
        if varName.endswith( "]" ) or \
           varName.endswith( "}" ) or \
           varName.endswith( ")" ):
            varName = varName[ : -2 ]   # Strip display purpose decor if so

        if self.__scopeFilter == 1:
            # Global only
            if not isGlobal:
                return False
        elif self.__scopeFilter == 2:
            # Local only
            if isGlobal:
                return False

        return True

    def __isMCF( self, varType ):
        " Returns True if it is a module, a function or a class "
        return varType in [ "Module", "Class", "Function", "Type" ]

