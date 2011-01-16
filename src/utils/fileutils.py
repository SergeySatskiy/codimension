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

""" file related utils """

import os.path
from PyQt4.QtGui        import QImageReader
from globals            import GlobalData
from utils.pixmapcache  import PixmapCache


UnknownFileType             = -1
PythonFileType              = 0
PythonCompiledFileType      = 1
Python3FileType             = 2
RubyFileType                = 3
DesignerFileType            = 4
DesignerHeaderFileType      = 5
LinguistFileType            = 6
QTResourceFileType          = 7
CodimensionProjectFileType  = 8
IDLFileType                 = 9
PixmapFileType              = 10
SVGFileType                 = 11
DFileType                   = 12
CFileType                   = 13
CHeaderFileType             = 14
CPPFileType                 = 15
CPPHeaderFileType           = 16
ELFFileType                 = 17
SOFileType                  = 18
PDFFileType                 = 19
HTMLFileType                = 20
CSSFileType                 = 21
XMLFileType                 = 22
MakefileType                = 23

BrokenSymlinkFileType       = 50


_fileTypes = { \
    UnknownFileType            : [ PixmapCache().getIcon( 'filemisc.png' ), 'Unknown' ],
    PythonFileType             : [ PixmapCache().getIcon( 'filepython.png' ), 'Python' ],
    PythonCompiledFileType     : [ PixmapCache().getIcon( 'filepythoncompiled.png' ), 'Binary' ],
    Python3FileType            : [ PixmapCache().getIcon( 'filepython.png' ), 'Python' ],
    RubyFileType               : [ PixmapCache().getIcon( 'fileruby.png' ), 'Ruby' ],
    DesignerFileType           : [ PixmapCache().getIcon( 'filedesigner.png' ), 'XML' ],
    DesignerHeaderFileType     : [ PixmapCache().getIcon( 'filedesigner.png' ), 'C++' ],
    LinguistFileType           : [ PixmapCache().getIcon( 'filelinguist2.png' ), 'XML' ],
    QTResourceFileType         : [ PixmapCache().getIcon( 'fileresource.png' ), 'XML' ],
    CodimensionProjectFileType : [ PixmapCache().getIcon( 'fileproject.png' ), 'Properties' ],
    IDLFileType                : [ PixmapCache().getIcon( 'fileidl.png' ), 'IDL' ],
    PixmapFileType             : [ PixmapCache().getIcon( 'filepixmap.png' ), 'Pixmap' ],
    SVGFileType                : [ PixmapCache().getIcon( 'filesvg.png' ), 'XML' ],
    DFileType                  : [ PixmapCache().getIcon( 'filed.png' ), 'D' ],
    CFileType                  : [ PixmapCache().getIcon( 'filec.png' ), 'C' ],
    CHeaderFileType            : [ PixmapCache().getIcon( 'filecheader.png' ), 'C' ],
    CPPFileType                : [ PixmapCache().getIcon( 'filecpp.png' ), 'C++' ],
    CPPHeaderFileType          : [ PixmapCache().getIcon( 'filecppheader.png' ), 'C++' ],
    ELFFileType                : [ PixmapCache().getIcon( 'filebinary.png' ), 'Binary' ],
    SOFileType                 : [ PixmapCache().getIcon( 'fileso.png' ), 'Binary' ],
    PDFFileType                : [ PixmapCache().getIcon( 'filepdf.png' ), 'PDF' ],
    HTMLFileType               : [ PixmapCache().getIcon( 'filehtml.png' ), 'HTML' ],
    CSSFileType                : [ PixmapCache().getIcon( 'filecss.png' ), 'CSS' ],
    XMLFileType                : [ PixmapCache().getIcon( 'filexml.png' ), 'XML' ],
    MakefileType               : [ PixmapCache().getIcon( 'filemake.png' ), 'Makefile' ],
    BrokenSymlinkFileType      : [ PixmapCache().getIcon( 'filebrokenlink.png' ), 'Unknown' ]
}



def detectFileType( path ):
    " Detects file type - must work for both existed and not existed files "

    absPath = os.path.abspath( str( path ) )
    if os.path.islink( absPath ):
        if not os.path.exists( absPath ):
            return BrokenSymlinkFileType

    # Must work for not existed files, e.g. new file request will also use it
    #    if not os.path.exists( absPath ):
    #        raise Exception( "Cannot find file: " + path )

    if path.lower().endswith( '.ui.h' ):
        fileExtension = 'ui.h'
    else:
        fileExtension = os.path.splitext( path )[ 1 ].lower()[ 1: ]

    if fileExtension in [ 'py', 'pyw', 'ptl' ]:
        return PythonFileType
    if fileExtension == 'pyc':
        return PythonCompiledFileType
    if fileExtension in [ 'py3', 'pyw3' ]:
        return Python3FileType
    if fileExtension == 'rb':
        return RubyFileType
    if fileExtension == 'ui':
        return DesignerFileType
    if fileExtension == 'ui.h':
        return DesignerHeaderFileType
    if fileExtension in [ 'ts', 'qm' ]:
        return LinguistFileType
    if fileExtension == 'qrc':
        return QTResourceFileType
    if fileExtension == 'cdm':
        return CodimensionProjectFileType
    if fileExtension == 'idl':
        return IDLFileType
    if fileExtension in QImageReader.supportedImageFormats():
        return PixmapFileType
    if fileExtension == 'svg':
        return SVGFileType
    if fileExtension in [ 'd', 'di' ]:
        return DFileType
    if fileExtension == 'c':
        return CFileType
    if fileExtension == 'h':
        return CHeaderFileType
    if fileExtension in [ 'cpp', 'cxx' ]:
        return CPPFileType
    if fileExtension in [ 'hpp', 'hxx' ]:
        return CPPHeaderFileType
    if fileExtension == 'pdf':
        return PDFFileType
    if fileExtension in [ 'htm', 'html' ]:
        return HTMLFileType
    if fileExtension == 'css':
        return CSSFileType
    if fileExtension == 'xml':
        return XMLFileType
    if fileExtension == 'so':
        return SOFileType

    if 'makefile' in path.lower():
        return MakefileType

    if os.path.exists( path ):
        if GlobalData().fileAvailable:
            try:
                output = os.popen( 'file -b ' + path ).read().lower()
                if 'elf ' in output and 'executable' in output:
                    return ELFFileType
                if 'elf ' in output and 'shared object' in output:
                    return SOFileType
            except:
                pass

    return UnknownFileType


def getFileIcon( fileType ):
    " Provides the file icon for a certain type "
    try:
        return _fileTypes[ fileType ][ 0 ]
    except:
        return PixmapCache().getIcon( 'empty.png' )


def getFileLanguage( fileType ):
    " Provides the file language "
    try:
        return _fileTypes[ fileType ][ 1 ]
    except:
        return 'Unknown'


def compactPath( path, width, measure = len ):
    """ Provides a compacted path fitting inside the given width.
        measure - ref to a function used to get the length of the string """

    if measure( path ) <= width:
        return path

    ellipsis = '...'

    head, tail = os.path.split( path )
    while head:
        path = os.path.join( "%s%s" % ( head, ellipsis ), tail )
        if measure( path ) <= width:
            return path
        head = head[ :-1 ]

    path = os.path.join( ellipsis, tail )
    if measure( path ) <= width:
        return path

    while tail:
        path = "%s%s" % (ellipsis, tail)
        if measure( path ) <= width:
            return path
        tail = tail[ 1: ]

    return ""
