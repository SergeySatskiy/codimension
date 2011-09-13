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
Module implementing an exporter for TeX.
"""

# This code is a port of the C++ code found in SciTE 1.74
# Original code: Copyright 1998-2006 by Neil Hodgson <neilh@scintilla.org>

import os

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QCursor, QApplication, QFont
from PyQt4.Qsci import QsciScintilla

from exportbase import ExportBase


class TEXExport( ExportBase ):
    """ Export to TeX implementation """

    CHARZ = ord('z') - ord('a') + 1

    def __init__( self, editor, parent = None ):

        ExportBase.__init__( self, editor, parent )
        return

    def __getTexRGB( self, color ):
        """ Converts a color object to a TeX color string """

        # texcolor[rgb]{0,0.5,0}{....}
        rf = color.red() / 256.0
        gf = color.green() / 256.0
        bf = color.blue() / 256.0

        # avoid breakage due to locale setting
        r = int(rf * 10 + 0.5)
        g = int(gf * 10 + 0.5)
        b = int(bf * 10 + 0.5)

        return "%d.%d, %d.%d, %d.%d" % (r / 10, r % 10, g / 10, g % 10, b / 10, b % 10)

    def __texStyle( self, style ):
        """ Calculates a style name string for a given style number """

        buf = ""
        if style == 0:
            buf = "a"
        else:
            while style > 0:
                buf += chr(ord('a') + (style % self.CHARZ))
                style /= self.CHARZ
        return buf

    def __defineTexStyle( self, font, color, paper, fileObj, istyle ):
        """ Define a new TeX style """

        closing_brackets = 3
        fileObj.write( "\\newcommand{\\eric%s}[1]{\\noindent{\\ttfamily{" % \
                    self.__texStyle( istyle ) )
        if font.italic():
            fileObj.write( "\\textit{" )
            closing_brackets += 1
        if font.bold():
            fileObj.write( "\\textbf{" )
            closing_brackets += 1
        if color != self.defaultColor:
            fileObj.write( "\\textcolor[rgb]{%s}{" % self.__getTexRGB( color ) )
            closing_brackets += 1
        if paper != self.defaultPaper:
            fileObj.write( "\\colorbox[rgb]{%s}{" % self.__getTexRGB( paper ) )
            closing_brackets += 1
        fileObj.write( "#1%s\n" % ('}' * closing_brackets) )
        return

    def exportSource( self, srcFileName, saveToFileName ):
        """ Performing the export """

        if saveToFileName == "":
            raise Exception( "File name to export to is not provided" )

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        QApplication.processEvents()

        try:
            self.editor.recolor( 0, -1 )

            tabSize = 4

            # TODO: this might come from settings
            onlyStylesUsed = False
            titleFullPath = False

            lex = self.editor.lexer_
            self.defaultPaper = lex and \
                                lex.paper( QsciScintilla.STYLE_DEFAULT ) or \
                                self.editor.paper().name()
            self.defaultColor = lex and \
                                lex.color( QsciScintilla.STYLE_DEFAULT ) or \
                                self.editor.color().name()
            # TODO: this may come from settings
            font = QFont()
            font.fromString( "Courier,10,-1,5,50,0,0,0,0,0" )
            self.defaultFont = lex and \
                               lex.color( QsciScintilla.STYLE_DEFAULT ) or \
                               font

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

            f.write( "\\documentclass[a4paper]{article}\n"
                     "\\usepackage[a4paper,margin=1.5cm]{geometry}\n"
                     "\\usepackage[T1]{fontenc}\n"
                     "\\usepackage{color}\n"
                     "\\usepackage{alltt}\n"
                     "\\usepackage{times}\n" )
            if self.editor.isUtf8():
                f.write( "\\usepackage[utf8]{inputenc}\n" )
            else:
                f.write( "\\usepackage[latin1]{inputenc}\n" )

            if lex:
                istyle = 0
                while istyle <= QsciScintilla.STYLE_MAX:
                    if (istyle <= QsciScintilla.STYLE_DEFAULT or \
                        istyle > QsciScintilla.STYLE_LASTPREDEFINED) and \
                       styleIsUsed[istyle]:
                        if not lex.description(istyle).isEmpty() or \
                           istyle == QsciScintilla.STYLE_DEFAULT:
                            font = lex.font( istyle )
                            colour = lex.color( istyle )
                            paper = lex.paper( istyle )

                            self.__defineTexStyle( font, colour, paper, f, istyle )
                    istyle += 1
            else:
                colour = self.editor.color()
                paper = self.editor.paper()
                # TODO: this may come from settings
                font = QFont()
                font.fromString( "Courier,10,-1,5,50,0,0,0,0,0" )

                self.__defineTexStyle( font, colour, paper, f, 0)
                self.__defineTexStyle( font, colour, paper, f,
                                       QsciScintilla.STYLE_DEFAULT )

            f.write( "\\begin{document}\n\n" )
            if titleFullPath:
                title = self.editor.getFileName()
            else:
                title = os.path.basename( self.editor.getFileName() )
            f.write( "Source File: %s\n\n\\noindent\n\\tiny{\n" % title )

            styleCurrent = self.editor.styleAt(0)
            f.write( "\\eric%s{" % self.__texStyle(styleCurrent) )

            lineIdx = 0
            pos = 0

            while pos < lengthDoc:
                ch = self.editor.rawCharAt( pos )
                style = self.editor.styleAt( pos )
                if style != styleCurrent:
                    # new style
                    f.write( "}\n\\eric%s{" % self.__texStyle(style) )
                    styleCurrent = style

                if ch == '\t':
                    ts = tabSize - (lineIdx % tabSize)
                    lineIdx += ts - 1
                    f.write( "\\hspace*{%dem}" % ts )
                elif ch == '\\':
                    f.write( "{\\textbackslash}" )
                elif ch in ['>', '<', '@']:
                    f.write( "$%c$" % ch )
                elif ch in ['{', '}', '^', '_', '&', '$', '#', '%', '~']:
                    f.write( "\\%c" % ch )
                elif ch in ['\r', '\n']:
                    lineIdx = -1    # because incremented below
                    if ch == '\r' and self.editor.rawCharAt(pos + 1) == '\n':
                        pos += 1    # skip the LF
                    styleCurrent = self.editor.styleAt(pos + 1)
                    f.write("} \\\\\n\\eric%s{" % self.__texStyle(styleCurrent))
                elif ch == ' ':
                    if self.editor.rawCharAt(pos + 1) == ' ':
                        f.write( "{\\hspace*{1em}}" )
                    else:
                        f.write( ' ' )
                else:
                    f.write( ch )
                lineIdx += 1
                pos += 1

            # close last empty style macros and document too
            f.write( "}\n} %end tiny\n\n\\end{document}\n" )
            f.close()

        except:
            QApplication.restoreOverrideCursor()
            raise

        QApplication.restoreOverrideCursor()
        return

