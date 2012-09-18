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

""" todo viewer implementation """

from PyQt4.QtCore           import Qt, SIGNAL, QStringList
from PyQt4.QtGui            import QProgressDialog, QTreeWidget, \
                                   QTreeWidgetItem, QHeaderView, QDialog, \
                                   QAbstractItemView, QApplication

from todoproperties         import TodoPropertiesDialog
from utils.pixmapcache      import PixmapCache
from utils.globals          import GlobalData
from todoitem               import TodoItem
import os.path


class TodoViewer( QTreeWidget ):
    """ todo viewer implementation """

    def __init__( self, parent = None ):
        QTreeWidget.__init__( self, parent )

        self.setRootIsDecorated( False )
        self.setItemsExpandable( False )
        self.setSortingEnabled( True )

        self.__headerItem = QTreeWidgetItem(
            QStringList() << "" \
                          << "File name" \
                          << "Line" \
                          << "Description" )

        self.__headerItem.setIcon( 0,
                                   PixmapCache().getIcon("todocompleted.png") )
        self.setHeaderItem( self.__headerItem )

        self.header().setSortIndicator( 1, Qt.AscendingOrder )
        self.__resizeColumns()

        self.todoItems = []

        self.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__showContextMenu )
        self.connect( self,
                      SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__todoItemActivated )
        return


    def __sort( self ):
        """ Sort the items """

        self.sortItems( self.sortColumn(), self.header().sortIndicatorOrder() )
        return

    def __resizeColumns(self):
        """ Resize the list columns """

        self.header().resizeSections( QHeaderView.ResizeToContents )
        self.header().setStretchLastSection( True )
        return

    def __refresh( self ):
        """ refresh the list """

        for item in self.todoItems:
            index = self.indexOfTopLevelItem( item )
            if index == -1:
                self.addTopLevelItem( item )
        self.__sort()
        self.__resizeColumns()
        return

    def __todoItemActivated( self, item, column ):
        """ Handles the double click on the item """

        filename = item.getFilename()
        if filename != "":
            self.emit( SIGNAL( "displayFile" ), filename, item.getLineNumber() )
        else:
            self.__editTodoProperties()
        return

    def __showContextMenu( self, point ):
        """ Show the context menu """

        item = self.itemAt( point )
        point = self.mapToGlobal( point )
        #if item is None:
        #    self.backRegenerateProjectTasksItem.setEnabled( self.projectOpen )
        #    if self.copyTask:
        #        self.backPasteItem.setEnabled(True)
        #    else:
        #        self.backPasteItem.setEnabled(False)
        #    self.__backMenu.popup(point)
        #else:
        #    self.regenerateProjectTasksItem.setEnabled(self.projectOpen)
        #    if itm.getFilename():
        #        self.gotoItem.setEnabled(True)
        #        self.deleteItem.setEnabled(True)
        #        self.markCompletedItem.setEnabled(False)
        #        self.copyItem.setEnabled(False)
        #    else:
        #        self.gotoItem.setEnabled(False)
        #        self.deleteItem.setEnabled(True)
        #        self.markCompletedItem.setEnabled(True)
        #        self.copyItem.setEnabled(True)
        #    if self.copyTask:
        #        self.pasteItem.setEnabled(True)
        #    else:
        #        self.pasteItem.setEnabled(False)

        #    self.__menu.popup(point)
        return

    def addTodoItem( self, description, filename, linenumber,
                     completed, isFixme ):
        """ Adds a new todo """

        newItem = TodoItem( description, filename, linenumber,
                            completed, isFixme )
        self.__addTodo( newItem )
        return

    def addFileTodoItem( self, description, filename, lineno ):
        """ Decides if it is a bug fix item and adds a new todo item """

        isFixme = "FIXME" in description

        # The todo is always not completed as soon as it comes from the file.
        # I guess it must be deleted from the file if it is completed.
        self.addTodoItem( description, filename, lineno,
                          False, isFixme )
        return

    def __addTodo( self, item ):
        """ Adds the constructed item """

        self.todoItems.append( item )
        self.addTopLevelItem( item )
        self.__sort()
        self.__resizeColumns()
        return

    def clearAll( self ):
        """ Clear all the todo items """

        self.todoItems = []
        self.clear()
        return

    def __editTodoProperties( self ):
        """ Item "Properties" context menu entry """

        todo = self.currentItem()
        dialog = TodoPropertiesDialog( todo, self )

        readOnly = todo.getFilename() != ""
        if readOnly:
            dialog.setReadOnly()

        if dialog.exec_() == QDialog.Accepted and not readOnly:
            data = dialog.getData()
            todo.setDescription( data[0] )
            todo.setCompleted( data[1] )
        return

    def __newTodo(self):
        """ The "New item" context menu handler """

        dialog = TodoPropertiesDialog( None, self )
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.getData()
            self.addTodoItem( data[0], "", 0, data[1], "FIXME" in data[0] )
        return

    def __markCompleted( self ):
        """ The "Mark Completed" context menu handler """

        todo = self.currentItem()
        if todo.getFilename() != "":
            todo.setCompleted( True )
        return

    def __deleteCompleted(self):
        """ The "Delete Completed" context menu handler """

        for item in self.todoItems:
            if item.getFilename() != "":
                # No way to mark completed the item from the source code anyway
                continue
            if item.isCompleted():
                index = self.indexOfTopLevelItem( item )
                self.takeTopLevelItem( index )
                self.todoItems.remove( item )
                del item

        currentItem = self.currentItem()
        if currentItem:
            index = self.indexFromItem( currentItem, self.currentColumn() )
            self.scrollTo( index, QAbstractItemView.PositionAtCenter )
        return

    def __deleteTodo( self ):
        """ Delete the current todo item """

        item = self.currentItem()
        index = self.indexOfTopLevelItem( item )
        self.takeTopLevelItem( index )
        self.todoItems.remove( item )
        del item

        currentItem = self.currentItem()
        if currentItem:
            index = self.indexFromItem( currentItem, self.currentColumn() )
            self.scrollTo( index, QAbstractItemView.PositionAtCenter )
        return

    def regenerateProjectTodos( self ):
        """ Collects TODO and FIXME items from the project files """

        if GlobalData().project.fileName == "":
            return

        self.clearAll()
        files = GlobalData().project.filesList

        # now process them
        progress = QProgressDialog( "Extracting project todo items...",
                                    "Abort", 0, len( files ) )
        progress.setMinimumDuration( 0 )

        count = 0
        for fileName in files:
            progress.setLabelText( "Extracting project todos...\n" + \
                                   fileName )
            progress.setValue( count )
            QApplication.processEvents()
            if progress.wasCanceled():
                break

            # Do nothing for the directories
            if fileName.endswith( os.path.sep ):
                count += 1
                continue

            # read the file and split it into textlines
            try:
                f = open( fileName, 'r' )
                text = f.read()
                lines = text.splitlines()
                f.close()
            except IOError:
                count += 1
                self.progress.setValue( count )
                continue

            # now look for todo items
            lineIndex = 0
            for line in lines:
                lineIndex += 1
                if not line.strip().startswith( '#' ):
                    continue

                index = line.find( "TODO" )
                if index >= 0:
                    description = line[ index: ]
                    self.addFileTodoItem( description, fileName, lineIndex )
                    continue

                index = line.find( "FIXME" )
                if index >= 0:
                    description = line[ index: ]
                    self.addFileTodoItem( description, fileName, lineIndex )

            count += 1

        progress.setValue( len(files) )
        return

