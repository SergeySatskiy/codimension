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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Collection of items which may appear in various tree views:
- project view
- filesystem view
- classes view
- functions view
"""

import os, os.path

from PyQt4.QtCore           import Qt
from utils.pixmapcache      import PixmapCache
from utils.fileutils        import detectFileType, getFileIcon, \
                                   PythonFileType, Python3FileType, \
                                   LinguistFileType, \
                                   CodimensionProjectFileType, \
                                   BrokenSymlinkFileType
from utils.project          import getProjectProperties

NoItemType                  = -1

DirectoryItemType           = 1
SysPathItemType             = 2
FileItemType                = 3
GlobalsItemType             = 4
ImportsItemType             = 5
FunctionsItemType           = 6
ClassesItemType             = 7
StaticAttributesItemType    = 8
InstanceAttributesItemType  = 9

CodingItemType              = 20
ImportItemType              = 21
ImportWhatItemType          = 22
FunctionItemType            = 23
ClassItemType               = 24
DecoratorItemType           = 25
AttributeItemType           = 26
GlobalItemType              = 27



class TreeViewItem( object ):
    " Common data structures for tree views items "

    def __init__( self, parent, data ):

        self.childItems = []
        self.childItemsSize = 0

        if type( data ) == list:
            self.itemData = data
        else:
            self.itemData = [ data ]
        self.itemDataSize = len( self.itemData )

        self.parentItem = parent
        self.itemType = NoItemType
        self.icon = PixmapCache().getIcon( 'empty.png' )
        self.populated = True
        self.lazyPopulation = False
        self.toolTip = ""
        return

    def isRoot( self ):
        " True if it is the root item "
        return self.parentItem == None

    def appendData( self, data ):
        " Adds more data to the item "

        if type( data ) == list:
            self.itemData += data
        else:
            self.itemData.append( data )
        self.itemDataSize = len( self.itemData )
        return

    def appendChild( self, child ):
        " Adds a child to the item "
        self.childItems.append( child )
        self.childItemsSize += 1
        self.populated = True
        return

    def removeChild( self, child ):
        " Removes the child "
        self.childItems.remove( child )
        self.childItemsSize -= 1
        return

    def removeChildren( self ):
        " Removes all children "
        self.childItems = []
        self.childItemsSize = 0
        return

    def child( self, row ):
        " Provides the child "
        return self.childItems[ row ]

    def children( self ):
        " Provides all the child items "
        return self.childItems[ : ]

    def childCount( self ):
        " Provides the number of child items "
        # Optimization against len( self.childItems )
        return self.childItemsSize

    def columnCount( self ):
        " Provides the number of available data items "
        # Optimization against len( self.itemData )
        return self.itemDataSize

    def data( self, column ):
        " Provides item data "
        try:
            return self.itemData[ column ]
        except IndexError:
            return ""

    def setData( self, column, value ):
        " Sets the new data "
        try:
            self.itemData[ column ] = value
        except:
            return

    def parent( self ):
        " Provides the reference to the parent item "
        return self.parentItem

    def row( self ):
        " Provides the row number of this item "
        return self.parentItem.childItems.index( self )

    def type( self ):
        " Provides the item type "
        return self.itemType

    def getIcon( self ):
        " Provides the items icon "
        return self.icon

    def lessThan( self, other, column, order ):
        " Check, if the item is less than another "
        try:
            return self.itemData[ column ] < other.itemData[ column ]
        except IndexError:
            return False

    def getPath( self ):
        " Provides the file name or dir name depending on the item type "

        if self.itemType in [ SysPathItemType, NoItemType ]:
            return ""

        current = self

        # The item could be used for G/F/C viewers where the file name is
        # available in the second column
        if len( self.itemData ) >= 2:
            return self.itemData[ 1 ]

        # Memorize if it is a directory item
        isDir = current.itemType == DirectoryItemType

        # skip till file or directory items
        while True:
            if current.itemType == NoItemType:
                raise Exception( "Internal error of getting tree view " \
                                 "item path. Please inform the developers." )
            if current.itemType in [ FileItemType, DirectoryItemType,
                                     SysPathItemType ]:
                break
            current = current.parentItem

        path = current.data( 0 )
        while current.parentItem.itemType != NoItemType and \
              current.parentItem.itemType != SysPathItemType:
            current = current.parentItem
            path = os.path.sep + path
            if current.data( 0 ) != os.path.sep:    # root item
                path = current.data( 0 ) + path

        path = os.path.normpath( path )
        if isDir:
            if not path.endswith( os.path.sep ):
                path += os.path.sep

        return path

    def getRowPath( self ):
        " Provides the row path "
        rowPath = []
        child = self
        current = self.parentItem
        while not current is None:
            for index in range( 0, len( current.childItems ) ):
                if current.childItems[ index ] == child:
                    rowPath = [ index ] + rowPath
                    child = current
                    current = child.parentItem
                    break
        return rowPath



class TreeViewDirectoryItem( TreeViewItem ):
    """ Directory item """

    def __init__( self, parent, dinfo, full = True ):

        self._dirName = os.path.abspath( str( dinfo ) )

        if full:
            dname = self._dirName
        else:
            dname = os.path.basename( self._dirName )

        TreeViewItem.__init__( self, parent, dname )

        self.itemType = DirectoryItemType

        self.icon = None
        self.populated = False
        self.lazyPopulation = True
        self.isLink = False
        self.updateStatus()
        return

    def updateStatus( self ):
        " Updates internal fields "
        if os.path.exists( self._dirName ):
            self.icon = PixmapCache().getIcon( 'dirclosed.png' )
            self.populated = False
            self.lazyPopulation = True

            if os.path.islink( self._dirName ):
                self.isLink = True
                linkTo = os.readlink( self._dirName )
                realpath = os.path.realpath( self._dirName )
                self.toolTip = "-> " + linkTo + "  (" + realpath + ")"
                self.icon = PixmapCache().getIcon( 'dirlink.png' )
        else:
            self.icon = PixmapCache().getIcon( 'dirbroken.png' )
            self.populated = True
            self.lazyPopulation = False

            self.childItems = []
            self.childItemsSize = 0
        return

    def lessThan( self, other, column, order ):
        """ Checks if the item is less than another """

        if other.itemType == FileItemType:
            return order == Qt.AscendingOrder

        return TreeViewItem.lessThan( self, other, column, order )



class TreeViewSysPathItem( TreeViewItem ):
    """ sys.path files item """

    def __init__( self, parent ):

        TreeViewItem.__init__( self, parent, "sys.path" )

        self.itemType = SysPathItemType
        self.icon = PixmapCache().getIcon( 'filepython.png' )
        self.populated = False
        self.lazyPopulation = True
        self.isLink = False
        return



class TreeViewFileItem( TreeViewItem ):
    """ file item """

    def __init__( self, parent, path ):

        path = str( path )
        TreeViewItem.__init__( self, parent, os.path.basename( path ) )
        self.itemType = FileItemType
        self.parsingErrors = False  # Used for python files only
        self.isLink = False

        self.fileType = detectFileType( path )
        self.icon = getFileIcon( self.fileType )

        if self.fileType == BrokenSymlinkFileType:
            self.isLink = True
            self.toolTip = self.__brokenLinkTooltip( path )
            return

        if os.path.islink( path ):
            self.isLink = True
            self.toolTip = self.__linkTooltip( path )
            self.icon = PixmapCache().getIcon( 'filelink.png' )
            self.fileType = detectFileType( os.path.realpath( path ) )
            return

        # Fine corrections for some file types
        if self.fileType in [ PythonFileType, Python3FileType ]:
            self.populated = False
            self.lazyPopulation = True
            return

        if self.fileType == LinguistFileType:
            if path.endswith( '.ts' ):
                self.icon = PixmapCache().getIcon( 'filelinguist.png' )
            return

        if self.fileType == CodimensionProjectFileType:
            # Get the project properties
            try:
                creationDate, author, lic, \
                copy_right, description, \
                version, email = getProjectProperties( path )
                self.toolTip = "Version: " + version + "\n" \
                               "Description: " + description + "\n" \
                               "Author: " + author + "\n" \
                               "e-mail: " + email + "\n" \
                               "Copyright: " + copy_right + "\n" \
                               "License: " + lic + "\n" \
                               "Creation date: " + creationDate
            except:
                # cannot get project properties
                self.toolTip = 'Broken project file'
            return

        return

    def lessThan( self, other, column, order ):
        """ Checks if the item is less than another """

        if other.itemType != FileItemType:
            return order == Qt.DescendingOrder

        sinit = self.data( 0 ).startswith( '__init__.py' )
        oinit = other.data( 0 ).startswith( '__init__.py' )
        if sinit and not oinit:
            return order == Qt.AscendingOrder
        if not sinit and oinit:
            return order == Qt.DescendingOrder

        return TreeViewItem.lessThan( self, other, column, order )

    def updateLinkStatus( self, path ):
        " Called to update the status to/from broken link "
        if not self.isLink:
            return

        self.fileType = detectFileType( path )
        self.icon = getFileIcon( self.fileType )
        if self.fileType == BrokenSymlinkFileType:
            self.toolTip = self.__brokenLinkTooltip( path )
            return

        self.toolTip = self.__linkTooltip( path )
        self.icon = PixmapCache().getIcon( 'filelink.png' )
        self.fileType = detectFileType( os.path.realpath( path ) )
        return

    @staticmethod
    def __brokenLinkTooltip( path ):
        " Provides the broken link tooltip "
        linkTo = os.readlink( path )
        realpath = os.path.realpath( path )
        return "Broken symlink -> " + linkTo + " (" + realpath + ")"

    @staticmethod
    def __linkTooltip( path ):
        " Provides the link tooltip "
        linkTo = os.readlink( path )
        realpath = os.path.realpath( path )
        return "-> " + linkTo + "  (" + realpath + ")"


class TreeViewGlobalsItem( TreeViewItem ):
    " Globals item "

    def __init__( self, parent, infoObj ):

        TreeViewItem.__init__( self, parent, "Globals" )

        self.sourceObj = infoObj
        self.itemType = GlobalsItemType
        self.icon = PixmapCache().getIcon( 'globalvar.png' )
        self.populated = False
        self.lazyPopulation = True
        return


class TreeViewImportsItem( TreeViewItem ):
    " Imports item "

    def __init__( self, parent, infoObj ):

        TreeViewItem.__init__( self, parent, "Imports" )

        self.sourceObj = infoObj
        self.itemType = ImportsItemType
        self.icon = PixmapCache().getIcon( 'imports.png' )
        self.populated = False
        self.lazyPopulation = True
        return


class TreeViewFunctionsItem( TreeViewItem ):
    " Functions item "

    def __init__( self, parent, infoObj ):

        TreeViewItem.__init__( self, parent, "Functions" )

        self.sourceObj = infoObj
        self.itemType = FunctionsItemType
        self.icon = PixmapCache().getIcon( 'method.png' )
        self.populated = False
        self.lazyPopulation = True
        return


class TreeViewClassesItem( TreeViewItem ):
    " Classes item "

    def __init__( self, parent, infoObj ):

        TreeViewItem.__init__( self, parent, "Classes" )

        self.sourceObj = infoObj
        self.itemType = ClassesItemType
        self.icon = PixmapCache().getIcon( 'class.png' )
        self.populated = False
        self.lazyPopulation = True
        return


class TreeViewStaticAttributesItem( TreeViewItem ):
    " Static attributes item "

    def __init__( self, parent ):

        TreeViewItem.__init__( self, parent, "Static attributes" )

        self.itemType = StaticAttributesItemType
        self.icon = PixmapCache().getIcon( 'attributes.png' )
        self.populated = False
        self.lazyPopulation = True
        return


class TreeViewInstanceAttributesItem( TreeViewItem ):
    " Instance attributes item "

    def __init__( self, parent ):

        TreeViewItem.__init__( self, parent, "Instance attributes" )

        self.itemType = InstanceAttributesItemType
        self.icon = PixmapCache().getIcon( 'attributes.png' )
        self.populated = False
        self.lazyPopulation = True
        return


class TreeViewCodingItem( TreeViewItem ):
    """ coding item """

    def __init__( self, parent, encodingObj ):

        TreeViewItem.__init__( self, parent, encodingObj.name )

        self.sourceObj = encodingObj
        self.itemType = CodingItemType
        self.icon = PixmapCache().getIcon( 'textencoding.png' )
        return


class TreeViewImportItem( TreeViewItem ):
    " Single import item "

    def __init__( self, parent, importObj ):

        TreeViewItem.__init__( self, parent, importObj.name )

        self.sourceObj = importObj
        self.itemType = ImportItemType
        self.icon = PixmapCache().getIcon( 'imports.png' )

        if len( importObj.what ) > 0:
            self.populated = False
            self.lazyPopulation = True
        return

class TreeViewWhatItem( TreeViewItem ):
    " Single what imported item "

    def __init__( self, parent, whatObj ):

        if whatObj.alias == "":
            TreeViewItem.__init__( self, parent, whatObj.name )
        else:
            TreeViewItem.__init__( self, parent, whatObj.name + \
                                   " as " + whatObj.alias )

        self.sourceObj = whatObj
        self.itemType = ImportWhatItemType
        self.icon = PixmapCache().getIcon( 'importwhat.png' )
        return

class TreeViewFunctionItem( TreeViewItem ):
    " Single function / class  method item "

    def __init__( self, parent, functionObj ):

        displayName = functionObj.name + "("
        if len( functionObj.arguments ) > 0:
            displayName += " " + ", ".join( functionObj.arguments ) + " "
        displayName += ")"

        TreeViewItem.__init__( self, parent, displayName )

        self.sourceObj = functionObj
        self.itemType = FunctionItemType
        self.toolTip = functionObj.docstring

        if functionObj.isPrivate():
            self.icon = PixmapCache().getIcon( 'method_private.png' )
        elif functionObj.isProtected():
            self.icon = PixmapCache().getIcon( 'method_protected.png' )
        else:
            self.icon = PixmapCache().getIcon( 'method.png' )

        # Decide if it should be expandable
        if len( functionObj.decorators ) > 0 or \
           len( functionObj.functions ) > 0 or \
           len( functionObj.classes ) > 0:
            self.populated = False
            self.lazyPopulation = True
        return


class TreeViewClassItem( TreeViewItem ):
    " Single class item "

    def __init__( self, parent, classObj ):

        displayName = classObj.name
        if len( classObj.base ) > 0:
            displayName += "( " + ", ".join( classObj.base ) + " )"

        TreeViewItem.__init__( self, parent, displayName )

        self.sourceObj = classObj
        self.itemType = ClassItemType
        self.toolTip = classObj.docstring

        if classObj.isPrivate():
            self.icon = PixmapCache().getIcon( 'class_private.png' )
        elif classObj.isProtected():
            self.icon = PixmapCache().getIcon( 'class_protected.png' )
        else:
            self.icon = PixmapCache().getIcon( 'class.png' )

        # Decide if it should be expandable
        if len( classObj.decorators ) > 0 or \
           len( classObj.functions ) > 0 or \
           len( classObj.classes ) > 0 or \
           len( classObj.classAttributes ) > 0 or \
           len( classObj.instanceAttributes ) > 0:
            self.populated = False
            self.lazyPopulation = True
        return


class TreeViewDecoratorItem( TreeViewItem ):
    " Single decorator item "

    def __init__( self, parent, decoratorObj ):

        displayName = decoratorObj.name
        if len( decoratorObj.arguments ) > 0:
            displayName += "( " + ", ".join( decoratorObj.arguments ) + " )"
        TreeViewItem.__init__( self, parent, displayName )

        self.sourceObj = decoratorObj
        self.itemType = DecoratorItemType
        self.icon = PixmapCache().getIcon( 'decorator.png' )
        return


class TreeViewAttributeItem( TreeViewItem ):
    " Single attribute item "

    def __init__( self, parent, attributeObj ):

        TreeViewItem.__init__( self, parent, attributeObj.name )

        self.sourceObj = attributeObj
        self.itemType = AttributeItemType

        if attributeObj.isPrivate():
            self.icon = PixmapCache().getIcon( 'attribute_private.png' )
        elif attributeObj.isProtected():
            self.icon = PixmapCache().getIcon( 'attribute_protected.png' )
        else:
            self.icon = PixmapCache().getIcon( 'attribute.png' )
        return


class TreeViewGlobalItem( TreeViewItem ):
    " Single global var item "

    def __init__( self, parent, globalObj ):

        TreeViewItem.__init__( self, parent, globalObj.name )

        self.sourceObj = globalObj
        self.itemType = GlobalItemType

        if globalObj.isPrivate():
            self.icon = PixmapCache().getIcon( 'attribute_private.png' )
        elif globalObj.isProtected():
            self.icon = PixmapCache().getIcon( 'attribute_protected.png' )
        else:
            self.icon = PixmapCache().getIcon( 'attribute.png' )
        return

