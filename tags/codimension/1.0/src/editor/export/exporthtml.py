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


""" export to HTML """

# This code is a port of the C++ code found in SciTE 1.74
# Original code: Copyright 1998-2006 by Neil Hodgson <neilh@scintilla.org>


import os

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QCursor, QApplication, QFont, QFontInfo
from PyQt4.Qsci import QsciScintilla

from exportbase import ExportBase
from utils.encoding import html_encode


class HTMLExport( ExportBase ):
    " Export to HTML implementation "

    def __init__( self, editor, parent = None ):

        ExportBase.__init__( self, editor, parent )
        return

    def exportSource( self, srcFileName, saveToFileName ):
        """ Performs exporting """

        if saveToFileName == "":
            raise Exception( "File name to export to is not provided" )

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        QApplication.processEvents()

        try:
            self.editor.recolor( 0, -1 )

            tabSize = 4

            # TODO: this might come from settings
            wysiwyg = True
            folding = True
            onlyStylesUsed = False
            titleFullPath = False
            tabs = False

            lengthDoc = self.editor.length()
            styleIsUsed = {}
            if onlyStylesUsed:
                for index in range( QsciScintilla.STYLE_MAX + 1 ):
                    styleIsUsed[ index ] = False
                # check the used styles
                pos = 0
                while pos < lengthDoc:
                    styleIsUsed[ self.editor.styleAt( pos ) & 0x7F ] = True
                    pos += 1
            else:
                for index in range( QsciScintilla.STYLE_MAX + 1 ):
                    styleIsUsed[ index ] = True
            styleIsUsed[ QsciScintilla.STYLE_DEFAULT ] = True

            f = open( saveToFileName, "wb" )

            f.write( '<!DOCTYPE html PUBLIC "-//W3C//DTD'
                     ' XHTML 1.0 Transitional//EN"\n'
                     ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
                     '<html xmlns="http://www.w3.org/1999/xhtml">\n'
                     '<head>\n' )
            if titleFullPath:
                f.write( '<title>%s</title>\n' % srcFileName )
            else:
                f.write( '<title>%s</title>\n' % \
                         os.path.basename( srcFileName ) )
            f.write( '<meta name="Generator" content="codimension" />\n' )
            f.write( '<meta http-equiv="Content-Type" '
                     'content="text/html; charset=utf-8" />\n' )
            if folding:
                f.write( \
                    "<script language='JavaScript' type='text/javascript'>\n"
                    "<!--\n"
                    "function symbol(id, sym) {\n"
                    "  if (id.textContent == undefined) {\n"
                    "    id.innerText = sym;\n"
                    "  } else {\n"
                    "    id.textContent = sym;\n"
                    "  }\n"
                    "}\n"
                    "function toggle(id) {\n"
                    "  var thislayer = document.getElementById('ln' + id);\n"
                    "  id -= 1;\n"
                    "  var togline = document.getElementById('hd' + id);\n"
                    "  var togsym = document.getElementById('bt' + id);\n"
                    "  if (thislayer.style.display == 'none') {\n"
                    "    thislayer.style.display = 'block';\n"
                    "    togline.style.textDecoration = 'none';\n"
                    "    symbol(togsym, '- ');\n"
                    "  } else {\n"
                    "    thislayer.style.display = 'none';\n"
                    "    togline.style.textDecoration = 'underline';\n"
                    "    symbol(togsym, '+ ');\n"
                    "  }\n"
                    "}\n"
                    "//-->\n"
                    "</script>\n" )

            lex = self.editor.lexer_
            if lex:
                bgColour = lex.paper( QsciScintilla.STYLE_DEFAULT ).name()
            else:
                bgColour = self.editor.paper().name()

            f.write( '<style type="text/css">\n' )
            if lex:
                istyle = 0
                while istyle <= QsciScintilla.STYLE_MAX:
                    if ( istyle <= QsciScintilla.STYLE_DEFAULT or \
                         istyle > QsciScintilla.STYLE_LASTPREDEFINED ) and \
                         styleIsUsed[ istyle ]:
                        if not lex.description( istyle ).isEmpty() or \
                           istyle == QsciScintilla.STYLE_DEFAULT:
                            font = lex.font( istyle )
                            colour = lex.color( istyle )
                            paper = lex.paper( istyle )
                            if istyle == QsciScintilla.STYLE_DEFAULT:
                                f.write( 'span {\n' )
                            else:
                                f.write( '.S%d {\n' % istyle )
                            if font.italic():
                                f.write( '    font-style: italic;\n' )
                            if font.bold():
                                f.write( '    font-weight: bold;\n' )
                            if wysiwyg:
                                f.write( "    font-family: '%s';\n" % font.family() )
                            f.write( '    color: %s;\n' % colour.name() )
                            if istyle != QsciScintilla.STYLE_DEFAULT and \
                               bgColour != paper.name():
                                f.write( '    background: %s;\n' % paper.name() )
                                f.write( '    text-decoration: inherit;\n' )
                            if wysiwyg:
                                f.write( '    font-size: %dpt;\n' % \
                                         QFontInfo( font ).pointSize() )
                            f.write( '}\n' )
                        else:
                            styleIsUsed[ istyle ] = False
                    istyle += 1
            else:
                colour = self.editor.color()
                paper = self.editor.paper()

                # TODO: this may come from settings
                font = QFont()
                font.fromString( "Courier,10,-1,5,50,0,0,0,0,0" )

                f.write( '.S0 {\n' )
                if font.italic():
                    f.write( '    font-style: italic;\n' )
                if font.bold():
                    f.write( '    font-weight: bold;\n' )
                if wysiwyg:
                    f.write( "    font-family: '%s';\n" % font.family() )
                f.write( '    color: %s;\n' % colour.name() )
                if bgColour != paper.name():
                    f.write( '    background: %s;\n' % paper.name() )
                    f.write( '    text-decoration: inherit;\n' )
                if wysiwyg:
                    f.write( '    font-size: %dpt;\n' % \
                             QFontInfo( font ).pointSize() )
                f.write( '}\n' )
            f.write( '</style>\n'
                     '</head>\n' )

            f.write( '<body bgcolor="%s">\n' % bgColour )
            line = self.editor.lineAt( 0 )
            level = self.editor.foldLevelAt( line ) - \
                    QsciScintilla.SC_FOLDLEVELBASE
            levelStack = [ level ]
            styleCurrent = self.editor.styleAt( 0 )
            inStyleSpan = False
            inFoldSpan = False
            # Global span for default attributes
            if wysiwyg:
                f.write( '<span>' )
            else:
                f.write( '<pre>' )

            if folding:
                if self.editor.foldFlagsAt( line ) & \
                   QsciScintilla.SC_FOLDLEVELHEADERFLAG:
                    f.write( '''<span id="hd%d" ''' \
                             '''onclick="toggle('%d')">''' % \
                             (line, line + 1) )
                    f.write( '<span id="bt%d">- </span>' % line )
                    inFoldSpan = True
                else:
                    f.write( '&nbsp; ' )

            if styleIsUsed[ styleCurrent ]:
                f.write( '<span class="S%0d">' % styleCurrent )
                inStyleSpan = True

            column = 0
            pos = 0
            utf8 = self.editor.isUtf8()
            utf8Ch = ""
            utf8Len = 0

            while pos < lengthDoc:
                ch = self.editor.rawCharAt( pos )
                style = self.editor.styleAt( pos )
                if style != styleCurrent:
                    if inStyleSpan:
                        f.write( '</span>' )
                        inStyleSpan = False
                    if ch not in ['\r', '\n']:
                        # no need of a span for the EOL
                        if styleIsUsed[ style ]:
                            f.write( '<span class="S%d">' % style )
                            inStyleSpan = True
                        styleCurrent = style

                if ch == ' ':
                    if wysiwyg:
                        prevCh = ''
                        if column == 0:
                            # at start of line, must put a &nbsp;
                            # because regular space will be collapsed
                            prevCh = ' '
                        while pos < lengthDoc and \
                              self.editor.rawCharAt( pos ) == ' ':
                            if prevCh != ' ':
                                f.write( ' ' )
                            else:
                                f.write( '&nbsp;' )
                            prevCh = self.editor.rawCharAt( pos )
                            pos += 1
                            column += 1
                        pos -= 1
                        # the last incrementation will be done
                        # by the outer loop
                    else:
                        f.write( ' ' )
                        column += 1
                elif ch == '\t':
                    ts = tabSize - ( column % tabSize )
                    if wysiwyg:
                        f.write( '&nbsp;' * ts )
                        column += ts
                    else:
                        if tabs:
                            f.write( ch )
                            column += 1
                        else:
                            f.write( ' ' * ts )
                            column += ts
                elif ch in [ '\r', '\n' ]:
                    if inStyleSpan:
                        f.write( '</span>' )
                        inStyleSpan = False
                    if inFoldSpan:
                        f.write( '</span>' )
                        inFoldSpan = False
                    if ch == '\r' and \
                       self.editor.rawCharAt( pos + 1 ) == '\n':
                        pos += 1 # CR+LF line ending,
                                 # skip the "extra" EOL char
                    column = 0
                    if wysiwyg:
                        f.write( '<br />' )

                    styleCurrent = self.editor.styleAt( pos + 1 )
                    if folding:
                        line = self.editor.lineAt( pos + 1 )
                        newLevel = self.editor.foldLevelAt( line )

                        if newLevel < level:
                            while levelStack[ -1 ] > newLevel:
                                f.write( '</span>' )
                                levelStack.pop()
                        f.write( '\n' ) # here to get clean code
                        if newLevel > level:
                            f.write( '<span id="ln%d">' % line )
                            levelStack.append( newLevel )
                        if self.editor.foldFlagsAt( line ) & \
                           QsciScintilla.SC_FOLDLEVELHEADERFLAG:
                            f.write( '''<span id="hd%d" ''' \
                                     '''onclick="toggle('%d')">''' % \
                                     (line, line + 1) )
                            f.write( '<span id="bt%d">- </span>' % line )
                            inFoldSpan = True
                        else:
                            f.write( '&nbsp; ' )
                        level = newLevel
                    else:
                        f.write( '\n' )

                    if styleIsUsed[ styleCurrent ] and \
                       self.editor.rawCharAt( pos + 1 ) not in ['\r', '\n']:
                        # We know it's the correct next style,
                        # but no (empty) span for an empty line
                        f.write( '<span class="S%0d">' % styleCurrent )
                        inStyleSpan = True
                else:
                    if ch == '<':
                        f.write( '&lt;' )
                    elif ch == '>':
                        f.write( '&gt' )
                    elif ch == '&':
                        f.write( '&amp;' )
                    else:
                        if ord( ch ) > 127 and utf8:
                            utf8Ch += ch
                            if utf8Len == 0:
                                if ( ord( utf8Ch[ 0 ] ) & 0xF0 ) == 0xF0:
                                    utf8Len = 4
                                elif ( ord( utf8Ch[ 0 ] ) & 0xE0 ) == 0xE0:
                                    utf8Len = 3
                                elif ( ord( utf8Ch[ 0 ] ) & 0xC0 ) == 0xC0:
                                    utf8Len = 2
                                # will be incremented again later
                                column -= 1
                            elif len( utf8Ch ) == utf8Len:
                                char = utf8Ch.decode( 'utf8' )
                                f.write( html_encode( char ) )
                                utf8Ch = ""
                                utf8Len = 0
                            else:
                                # will be incremented again later
                                column -= 1
                        else:
                            f.write( ch )
                    column += 1

                pos += 1

            if inStyleSpan:
                f.write( '</span>' )

            if folding:
                while levelStack:
                    f.write( '</span>' )
                    levelStack.pop()

            if wysiwyg:
                f.write( '</span>' )
            else:
                f.write( '</pre>' )

            f.write( '</body>\n</html>\n' )
            f.close()

        except:
            QApplication.restoreOverrideCursor()
            raise

        QApplication.restoreOverrideCursor()
        return

