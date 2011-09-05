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

""" export to PDF """

# This code is a port of the C++ code found in SciTE 1.74
# Original code: Copyright 1998-2006 by Neil Hodgson <neilh@scintilla.org>


from PyQt4.QtCore   import Qt
from PyQt4.QtGui    import QCursor, QApplication, QFont, QFontInfo
from PyQt4.Qsci     import QsciScintilla
from exportbase     import ExportBase


PDF_FONT_DEFAULT        = 1    # Helvetica
PDF_FONTSIZE_DEFAULT    = 10
PDF_SPACING_DEFAULT     = 1.2
PDF_MARGIN_DEFAULT      = 72    # 1.0"
PDF_ENCODING            = "WinAnsiEncoding"

PDFfontNames = [
    "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique",
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic"
]

PDFfontAscenders =  [629, 718, 699]
PDFfontDescenders = [157, 207, 217]
PDFfontWidths =     [600,   0,   0]

PDFpageSizes = {
    # name   : (height, width)
    "Letter" : (792, 612),
    "A4"     : (842, 595),
}

class PDFStyle( object ):
    """ Storage for the values of a PDF style """

    def __init__( self ):

        self.fore = ""
        self.font = 0
        return


class PDFObjectTracker( object ):
    """ Conveniently handles the tracking of PDF objects
        so that the cross-reference table can be built (PDF1.4Ref(p39))
        All writes to the file are passed through a PDFObjectTracker object.
    """

    def __init__( self, fileToWrite ):

        self.file = fileToWrite
        self.offsetList = []
        self.index = 1
        return

    def write( self, objectData ):
        """ Writes the data to the file """

        if type( objectData ) == type(1):
            self.file.write( "%d" % objectData )
        else:
            self.file.write( objectData )
        return

    def add( self, objectData ):
        """ Add a new object """

        self.offsetList.append( self.file.tell() )
        self.write( self.index )
        self.write( " 0 obj\n" )
        self.write( objectData )
        self.write( "endobj\n" )
        ind = self.index
        self.index += 1
        return ind

    def xref( self ):
        """ Builds the xref table """

        xrefStart = self.file.tell()
        self.write( "xref\n0 " )
        self.write( self.index )

        # a xref entry *must* be 20 bytes long (PDF1.4Ref(p64))
        # so extra space added; also the first entry is special
        self.write( "\n0000000000 65535 f \n" )
        ind = 0
        while ind < len( self.offsetList ):
            self.write( "%010d 00000 n \n" % self.offsetList[ ind ] )
            ind += 1
        return xrefStart


class PDFRender( object ):
    """ Manages line and page rendering
        Apart from startPDF, endPDF everything goes in via add() and nextLine()
        so that line formatting and pagination can be done properly.
    """

    def __init__( self ):

        self.pageStarted = False
        self.firstLine = False
        self.pageCount = 0
        self.pageData = ""
        self.style = {}
        self.segStyle = ""
        self.segment = ""
        self.pageMargins = {
            "left"   : 72,
            "right"  : 72,
            "top"    : 72,
            "bottom" : 72,
        }
        self.fontSize = 0
        self.fontSet = 0
        self.leading = 0.0
        self.pageWidth = 0
        self.pageHeight = 0
        self.pageContentStart = 0
        self.xPos = 0.0
        self.yPos = 0.0
        self.justWhiteSpace = False
        return

    def fontToPoints(self, thousandths):
        """ Converts the font size to points """

        return self.fontSize * thousandths / 1000.0

    def setStyle( self, style_ ):
        """ Sets the style """

        styleNext = style_
        if style_ == -1:
            styleNext = self.styleCurrent

        buf = ""
        if styleNext != self.styleCurrent or style_ == -1:
            if self.style[ self.styleCurrent ].font != self.style[ styleNext ].font or \
               style_ == -1:
                buf += "/F%d %d Tf " % ( self.style[ styleNext ].font + 1, self.fontSize )
            if self.style[ self.styleCurrent ].fore != self.style[ styleNext ].fore or \
               style_ == -1:
                buf += "%srg " % self.style[ styleNext ].fore
        return buf

    def startPDF( self ):
        """ Starts the PDF document """

        if self.fontSize <= 0:
            self.fontSize = PDF_FONTSIZE_DEFAULT

        # leading is the term for distance between lines
        self.leading = self.fontSize * PDF_SPACING_DEFAULT

        # sanity check for page size and margins
        pageWidthMin = int( self.leading ) + \
                       self.pageMargins[ "left" ] + self.pageMargins[ "right" ]
        if self.pageWidth < pageWidthMin:
            self.pageWidth = pageWidthMin
        pageHeightMin = int( self.leading ) + \
                       self.pageMargins[ "top" ] + self.pageMargins[ "bottom" ]
        if self.pageHeight < pageHeightMin:
            self.pageHeight = pageHeightMin

        # start to write PDF file here (PDF1.4Ref(p63))
        # ASCII>127 characters to indicate binary-possible stream
        self.oT.write( "%PDF-1.3\n%�쏢\n" )
        self.styleCurrent = QsciScintilla.STYLE_DEFAULT

        # build objects for font resources; note that font objects are
        # *expected* to start from index 1 since they are the first objects
        # to be inserted (PDF1.4Ref(p317))
        for i in range( 4 ):
            buf = \
                "<</Type/Font/Subtype/Type1/Name/F%d/BaseFont/%s/Encoding/%s>>\n" % \
                (i + 1, PDFfontNames[self.fontSet * 4 + i], PDF_ENCODING)
            self.oT.add( buf )

        self.pageContentStart = self.oT.index
        return

    def endPDF( self ):
        """ Ends the PDF document """

        if self.pageStarted:
            # flush buffers
            self.endPage()

        # refer to all used or unused fonts for simplicity
        resourceRef = self.oT.add(
            "<</ProcSet[/PDF/Text]\n/Font<</F1 1 0 R/F2 2 0 R/F3 3 0 R/F4 4 0 R>> >>\n" )

        # create all the page objects (PDF1.4Ref(p88))
        # forward reference pages object; calculate its object number
        pageObjectStart = self.oT.index
        pagesRef = pageObjectStart + self.pageCount
        for i in range( self.pageCount ):
            buf = "<</Type/Page/Parent %d 0 R\n" \
                  "/MediaBox[ 0 0 %d %d]\n" \
                  "/Contents %d 0 R\n" \
                  "/Resources %d 0 R\n>>\n" % \
                  (pagesRef, self.pageWidth, self.pageHeight,
                   self.pageContentStart + i, resourceRef)
            self.oT.add( buf )

        # create page tree object (PDF1.4Ref(p86))
        self.pageData = "<</Type/Pages/Kids[\n"
        for i in range( self.pageCount ):
            self.pageData += "%d 0 R\n" % ( pageObjectStart + i )
        self.pageData += "]/Count %d\n>>\n" % self.pageCount
        self.oT.add( self.pageData )

        # create catalog object (PDF1.4Ref(p83))
        buf = "<</Type/Catalog/Pages %d 0 R >>\n" % pagesRef
        catalogRef = self.oT.add( buf )

        # append the cross reference table (PDF1.4Ref(p64))
        xref = self.oT.xref()

        # end the file with the trailer (PDF1.4Ref(p67))
        buf = "trailer\n<< /Size %d /Root %d 0 R\n>>\nstartxref\n%d\n%%%%EOF\n" % \
                 ( self.oT.index, catalogRef, xref )
        self.oT.write( buf )
        return

    def add( self, ch, style_ ):
        """ Adds a character to the page """

        if not self.pageStarted:
            self.startPage()

        # get glyph width (TODO future non-monospace handling)
        glyphWidth = self.fontToPoints( PDFfontWidths[ self.fontSet ] )
        self.xPos += glyphWidth

        # if cannot fit into a line, flush, wrap to next line
        if self.xPos > self.pageWidth - self.pageMargins[ "right" ]:
            self.nextLine()
            self.xPos += glyphWidth

        # if different style, then change to style
        if style_ != self.styleCurrent:
            self.flushSegment()
            # output code (if needed) for new style
            self.segStyle = self.setStyle( style_ )
            self.stylePrev = self.styleCurrent
            self.styleCurrent = style_

        # escape these characters
        if ch == ')' or ch == '(' or ch == '\\':
            self.segment += '\\'
        if ch != ' ':
            self.justWhiteSpace = False
        self.segment += ch # add to segment data
        return

    def flushSegment( self ):
        """ Flushes a segment of data """

        if len(self.segment) > 0:
            if self.justWhiteSpace:     # optimise
                self.styleCurrent = self.stylePrev
            else:
                self.pageData += self.segStyle
            self.pageData += "(%s)Tj\n" % self.segment
            self.segment = ""
            self.segStyle = ""
            self.justWhiteSpace = True
        return

    def startPage( self ):
        """
        Public method to start a new page.
        """
        self.pageStarted = True
        self.firstLine = True
        self.pageCount += 1
        fontAscender = self.fontToPoints( PDFfontAscenders[ self.fontSet ] )
        self.yPos = self.pageHeight - self.pageMargins[ "top" ] - fontAscender

        # start a new page
        buf = "BT 1 0 0 1 %d %d Tm\n" % (self.pageMargins[ "left" ],
                                            int( self.yPos ))

        # force setting of initial font, colour
        self.segStyle = self.setStyle(-1)
        buf += self.segStyle
        self.pageData = buf
        self.xPos = self.pageMargins[ "left" ]
        self.segment = ""
        self.flushSegment()
        return

    def endPage( self ):
        """ End a page """

        self.pageStarted = False
        self.flushSegment()

        # build actual text object; +3 is for "ET\n"
        # PDF1.4Ref(p38) EOL marker preceding endstream not counted
        textObj = "<</Length %d>>\nstream\n%sET\nendstream\n" % \
                  (len(self.pageData) - 1 + 3, self.pageData)
        self.oT.add( textObj )
        return

    def nextLine( self ):
        """ Starts a new line """

        if not self.pageStarted:
            self.startPage()

        self.xPos = self.pageMargins[ "left" ]
        self.flushSegment()

        # PDF follows cartesian coords, subtract -> down
        self.yPos -= self.leading
        fontDescender = self.fontToPoints( PDFfontDescenders[ self.fontSet ] )
        if self.yPos < self.pageMargins[ "bottom" ] + fontDescender:
            self.endPage()
            self.startPage()
            return

        if self.firstLine:
            # avoid breakage due to locale setting
            f = int(self.leading * 10 + 0.5)
            buf = "0 -%d.%d TD\n" % (f / 10, f % 10)
            self.firstLine = False
        else:
            buf = "T*\n"
        self.pageData += buf
        return


class PDFExport( ExportBase ):
    """ PDF exporting """

    def __init__( self, editor, parent = None ):

        ExportBase.__init__( self, editor, parent )
        return

    def __getPDFRGB( self, color ):
        """ Converts a color object to the correct PDF color """

        pdfColor = ""
        for component in [color.red(), color.green(), color.blue()]:
            c = (component * 1000 + 127) / 255
            if c == 0 or c == 1000:
                pdfColor += "%d " % (c / 1000)
            else:
                pdfColor += "0.%03d " % c
        return pdfColor

    def exportSource( self, srcFileName, saveToFileName ):
        """ Performs the export """

        pr = PDFRender()

        if saveToFileName == "":
            raise Exception( "File name to export to is not provided" )

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        QApplication.processEvents()

        try:
            self.editor.recolor( 0, -1 )
            lex = self.editor.lexer_

            tabSize = 4

            # get magnification value to add to default screen font size
            # TODO: this may come from settings
            pr.fontSize = 0

            # set font family according to face name
            # TODO: this may come from settings
            fontName = unicode( "Courier" )
            pr.fontSet = PDF_FONT_DEFAULT
            if fontName == "Courier":
                pr.fontSet = 0
            elif fontName == "Helvetica":
                pr.fontSet = 1
            elif fontName == "Times":
                pr.fontSet = 2

            # page size: height, width,
            # TODO: this may come from settings
            pageSize = unicode( "Letter" )
            try:
                pageDimensions = PDFpageSizes[ pageSize ]
            except KeyError:
                pageDimensions = PDFpageSizes[ "A4" ]
            pr.pageHeight = pageDimensions[ 0 ]
            pr.pageWidth = pageDimensions[ 1 ]

            # page margins: left, right, top, bottom
            # < 0 to use PDF default values
            # TODO: this may come from settings
            val = 36
            if val < 0:
                pr.pageMargins[ "left" ] = PDF_MARGIN_DEFAULT
            else:
                pr.pageMargins[ "left" ] = val

            # TODO: this may come from settings
            val = 36
            if val < 0:
                pr.pageMargins[ "right" ] = PDF_MARGIN_DEFAULT
            else:
                pr.pageMargins[ "right" ] = val

            # TODO: this may come from settings
            val = 36
            if val < 0:
                pr.pageMargins[ "top" ] = PDF_MARGIN_DEFAULT
            else:
                pr.pageMargins[ "top" ] = val

            # TODO: this may come from settings
            val = 36
            if val < 0:
                pr.pageMargins[ "bottom" ] = PDF_MARGIN_DEFAULT
            else:
                pr.pageMargins[ "bottom" ] = val

            # collect all styles available for that 'language'
            # or the default style if no language is available...
            if lex:
                istyle = 0
                while istyle <= QsciScintilla.STYLE_MAX:
                    if (istyle <= QsciScintilla.STYLE_DEFAULT or \
                        istyle > QsciScintilla.STYLE_LASTPREDEFINED):
                        if not lex.description(istyle).isEmpty() or \
                           istyle == QsciScintilla.STYLE_DEFAULT:
                            style = PDFStyle()

                            font = lex.font(istyle)
                            if font.italic():
                                style.font |= 2
                            if font.bold():
                                style.font |= 1

                            colour = lex.color(istyle)
                            style.fore = self.__getPDFRGB(colour)
                            pr.style[istyle] = style

                        # grab font size from default style
                        if istyle == QsciScintilla.STYLE_DEFAULT:
                            fontSize = QFontInfo(font).pointSize()
                            if fontSize > 0:
                                pr.fontSize += fontSize
                            else:
                                pr.fontSize = PDF_FONTSIZE_DEFAULT

                    istyle += 1
            else:
                style = PDFStyle()

                # TODO: this may come from settings
                font = QFont()
                font.fromString( "Courier,10,-1,5,50,0,0,0,0,0" )
                if font.italic():
                    style.font |= 2
                if font.bold():
                    style.font |= 1

                colour = self.editor.color()
                style.fore = self.__getPDFRGB( colour )
                pr.style[ 0 ] = style
                pr.style[ QsciScintilla.STYLE_DEFAULT ] = style

                fontSize = QFontInfo( font ).pointSize()
                if fontSize > 0:
                    pr.fontSize += fontSize
                else:
                    pr.fontSize = PDF_FONTSIZE_DEFAULT

            f = open( saveToFileName, "wb" )

            # initialise PDF rendering
            ot = PDFObjectTracker(f)
            pr.oT = ot
            pr.startPDF()

            # do here all the writing
            lengthDoc = self.editor.length()

            if lengthDoc == 0:
                pr.nextLine() # enable zero length docs
            else:
                pos = 0
                column = 0
                utf8 = self.editor.isUtf8()
                utf8Ch = ""
                utf8Len = 0

                while pos < lengthDoc:
                    ch = self.editor.rawCharAt( pos )
                    style = self.editor.styleAt( pos )

                    if ch == '\t':
                        # expand tabs
                        ts = tabSize - (column % tabSize)
                        column += ts
                        pr.add( ' ' * ts, style )
                    elif ch == '\r' or ch == '\n':
                        if ch == '\r' and self.editor.rawCharAt(pos + 1) == '\n':
                            pos += 1
                        # close and begin a newline...
                        pr.nextLine()
                        column = 0
                    else:
                        # write the character normally...
                        if ord(ch) > 127 and utf8:
                            utf8Ch += ch
                            if utf8Len == 0:
                                if (ord(utf8Ch[0]) & 0xF0) == 0xF0:
                                    utf8Len = 4
                                elif (ord(utf8Ch[0]) & 0xE0) == 0xE0:
                                    utf8Len = 3
                                elif (ord(utf8Ch[0]) & 0xC0) == 0xC0:
                                    utf8Len = 2
                                # will be incremented again later
                                column -= 1
                            elif len( utf8Ch ) == utf8Len:
                                # convert utf-8 character to
                                # win ansi using cp1250
                                char = utf8Ch.decode( 'utf8' )\
                                           .encode( 'cp1250', 'replace' )
                                pr.add( char, style )
                                utf8Ch = ""
                                utf8Len = 0
                            else:
                                # will be incremented again later
                                column -= 1
                        else:
                            pr.add( ch, style )
                        column += 1

                    pos += 1

            # write required stuff and close the PDF file
            pr.endPDF()
            f.close()
        except:
            QApplication.restoreOverrideCursor()
            raise

        QApplication.restoreOverrideCursor()
        return

