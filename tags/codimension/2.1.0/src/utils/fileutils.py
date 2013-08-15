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
# $Id: fileutils.py 1503 2013-06-10 13:58:31Z sergey.satskiy@gmail.com $
#

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

""" file related utils """

from os.path import islink, exists, split, join, sep, basename
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
ShellFileType               = 24
JavascriptFileType          = 25
DiffFileType                = 26
JavaFileType                = 27
PascalFileType              = 28
PerlFileType                = 29
TCLFileType                 = 30
PropsFileType               = 31
TexFileType                 = 32
UnknownELFFileType          = 33
UTF8TextFile                = 34
ASCIITextFile               = 35
ObjectFileType              = 36
ArchiveFileType             = 37
TarFileType                 = 38

BrokenSymlinkFileType       = 50
DirectoryFileType           = 51


_fileTypes = {
    UnknownFileType:
        [ PixmapCache().getIcon( 'filemisc.png' ), 'Unknown' ],
    PythonFileType:
        [ PixmapCache().getIcon( 'filepython.png' ), 'Python' ],
    PythonCompiledFileType:
        [ PixmapCache().getIcon( 'filepythoncompiled.png' ), 'Binary' ],
    Python3FileType:
        [ PixmapCache().getIcon( 'filepython.png' ), 'Python' ],
    RubyFileType:
        [ PixmapCache().getIcon( 'fileruby.png' ), 'Ruby' ],
    DesignerFileType:
        [ PixmapCache().getIcon( 'filedesigner.png' ), 'XML' ],
    DesignerHeaderFileType:
        [ PixmapCache().getIcon( 'filedesigner.png' ), 'C++' ],
    LinguistFileType:
        [ PixmapCache().getIcon( 'filelinguist2.png' ), 'XML' ],
    QTResourceFileType:
        [ PixmapCache().getIcon( 'fileresource.png' ), 'XML' ],
    CodimensionProjectFileType :
        [ PixmapCache().getIcon( 'fileproject.png' ), 'Properties' ],
    IDLFileType:
        [ PixmapCache().getIcon( 'fileidl.png' ), 'IDL' ],
    PixmapFileType:
        [ PixmapCache().getIcon( 'filepixmap.png' ), 'Pixmap' ],
    SVGFileType:
        [ PixmapCache().getIcon( 'filesvg.png' ), 'XML' ],
    DFileType:
        [ PixmapCache().getIcon( 'filed.png' ), 'D' ],
    CFileType:
        [ PixmapCache().getIcon( 'filec.png' ), 'C' ],
    CHeaderFileType:
        [ PixmapCache().getIcon( 'filecheader.png' ), 'C' ],
    CPPFileType:
        [ PixmapCache().getIcon( 'filecpp.png' ), 'C++' ],
    CPPHeaderFileType:
        [ PixmapCache().getIcon( 'filecppheader.png' ), 'C++' ],
    ELFFileType:
        [ PixmapCache().getIcon( 'filebinary.png' ), 'Binary' ],
    SOFileType:
        [ PixmapCache().getIcon( 'fileso.png' ), 'Binary' ],
    ObjectFileType:
        [ PixmapCache().getIcon( 'fileso.png' ), 'Binary' ],
    PDFFileType:
        [ PixmapCache().getIcon( 'filepdf.png' ), 'PDF' ],
    HTMLFileType:
        [ PixmapCache().getIcon( 'filehtml.png' ), 'HTML' ],
    CSSFileType:
        [ PixmapCache().getIcon( 'filecss.png' ), 'CSS' ],
    XMLFileType:
        [ PixmapCache().getIcon( 'filexml.png' ), 'XML' ],
    MakefileType:
        [ PixmapCache().getIcon( 'filemake.png' ), 'Makefile' ],
    BrokenSymlinkFileType:
        [ PixmapCache().getIcon( 'filebrokenlink.png' ), 'Unknown' ],
    ShellFileType:
        [ PixmapCache().getIcon( 'fileshell.png' ), 'Shell' ],
    JavascriptFileType:
        [ PixmapCache().getIcon( 'filejs.png' ), 'Javascript' ],
    DiffFileType:
        [ PixmapCache().getIcon( 'filediff.png' ), 'Diff' ],
    JavaFileType:
        [ PixmapCache().getIcon( 'filejava.png' ), 'Java' ],
    PascalFileType:
        [ PixmapCache().getIcon( 'filepascal.png' ), 'Pascal' ],
    PerlFileType:
        [ PixmapCache().getIcon( 'fileperl.png' ), 'Perl' ],
    TCLFileType:
        [ PixmapCache().getIcon( 'filetcl.png' ), 'TCL' ],
    PropsFileType:
        [ PixmapCache().getIcon( 'fileprops.png' ), 'Properties' ],
    TexFileType:
        [ PixmapCache().getIcon( 'filetex.png' ), 'TeX' ],
    UnknownELFFileType:
        [ PixmapCache().getIcon( 'filemisc.png' ), 'Unknown' ],
    UTF8TextFile:
        [ PixmapCache().getIcon( 'filetext.png' ), 'Text' ],
    ASCIITextFile:
        [ PixmapCache().getIcon( 'filetext.png' ), 'Text' ],
    DirectoryFileType:
        [ PixmapCache().getIcon( 'dirclosed.png' ), '' ],
    ArchiveFileType:
        [ PixmapCache().getIcon( 'filearchive.png' ), 'Archive' ],
    TarFileType:
        [ PixmapCache().getIcon( 'filetar.png' ), 'Tar' ],
}


_extType = {
    'py'    :   PythonFileType,
    'pyw'   :   PythonFileType,
    'ptl'   :   PythonFileType,
    'pyc'   :   PythonCompiledFileType,
    'pyo'   :   PythonCompiledFileType,
    'py3'   :   Python3FileType,
    'pyw3'  :   Python3FileType,
    'rb'    :   RubyFileType,
    'ui'    :   DesignerFileType,
    'ts'    :   LinguistFileType,
    'qm'    :   LinguistFileType,
    'qrc'   :   QTResourceFileType,
    'cdm'   :   CodimensionProjectFileType,
    'idl'   :   IDLFileType,
    'svg'   :   SVGFileType,
    'd'     :   DFileType,
    'di'    :   DFileType,
    'c'     :   CFileType,
    'cpp'   :   CPPFileType,
    'cc'    :   CPPFileType,
    'cxx'   :   CPPFileType,
    'c++'   :   CPPFileType,
    'hpp'   :   CPPHeaderFileType,
    'hxx'   :   CPPHeaderFileType,
    'h++'   :   CPPHeaderFileType,
    'hh'    :   CPPHeaderFileType,
    'pdf'   :   PDFFileType,
    'htm'   :   HTMLFileType,
    'html'  :   HTMLFileType,
    'css'   :   CSSFileType,
    'xml'   :   XMLFileType,
    'xsl'   :   XMLFileType,
    'xslt'  :   XMLFileType,
    'so'    :   SOFileType,
    'o'     :   ObjectFileType,
    'bash'  :   ShellFileType,
    'sh'    :   ShellFileType,
    'js'    :   JavascriptFileType,
    'diff'  :   DiffFileType,
    'patch' :   DiffFileType,
    'java'  :   JavaFileType,
    'dfm'   :   PascalFileType,
    'dpk'   :   PascalFileType,
    'dpr'   :   PascalFileType,
    'inc'   :   PascalFileType,
    'pas'   :   PascalFileType,
    'pp'    :   PascalFileType,
    'ph'    :   PerlFileType,
    'pl'    :   PerlFileType,
    'pm'    :   PerlFileType,
    'tcl'   :   TCLFileType,
    'tk'    :   TCLFileType,
    'cfg'   :   PropsFileType,
    'cnf'   :   PropsFileType,
    'inf'   :   PropsFileType,
    'ini'   :   PropsFileType,
    'rc'    :   PropsFileType,
    'reg'   :   PropsFileType,
    'aux'   :   TexFileType,
    'idx'   :   TexFileType,
    'sty'   :   TexFileType,
    'tex'   :   TexFileType,
    'toc'   :   TexFileType,
    'txt'   :   UTF8TextFile,
    'tar'   :   TarFileType,
    'gz'    :   ArchiveFileType,
    'bz2'   :   ArchiveFileType,
    'gzip'  :   ArchiveFileType,
    'zip'   :   ArchiveFileType,
    'xz'    :   ArchiveFileType,
    'tgz'   :   ArchiveFileType,
    'properties':   PropsFileType,
}


__cachedFileTypes = {}
__magicModule = None
__QTSupportedImageFormats = [ str( fmt ) for fmt in
                              QImageReader.supportedImageFormats() ]

# Cached value to avoid unnecessary searches for a name
magicAvailable = GlobalData().magicAvailable

 

def detectFileType( path, checkForBrokenLink = True, skipCache = False ):
    " Detects file type - must work for both existed and not existed files "

    global __cachedFileTypes
    global __magicModule

    if not path:
        return UnknownFileType

    if path.endswith( sep ):
        __cachedFileTypes[ path ] = DirectoryFileType
        return DirectoryFileType

    if checkForBrokenLink and islink( path ):
        if not exists( path ):
            return BrokenSymlinkFileType

    if not skipCache and path in __cachedFileTypes:
        return __cachedFileTypes[ path ]

    # Must work for not existed files, e.g. new file request will also use it
    #    if not exists( absPath ):
    #        raise Exception( "Cannot find file: " + path )

    fileExtension = path.split( '.' )[ -1 ].lower()

    if fileExtension in _extType:
        fType = _extType[ fileExtension ]
        __cachedFileTypes[ path ] = fType
        return fType

    if fileExtension == 'h':
        if path.lower().endswith( '.ui.h' ):
            __cachedFileTypes[ path ] = DesignerHeaderFileType
            return DesignerHeaderFileType
        __cachedFileTypes[ path ] = CHeaderFileType
        return CHeaderFileType
    if fileExtension in __QTSupportedImageFormats:
        __cachedFileTypes[ path ] = PixmapFileType
        return PixmapFileType

    if 'makefile' in basename( path ).lower():
        __cachedFileTypes[ path ] = MakefileType
        return MakefileType

    if magicAvailable:
        try:
            if __magicModule is None:
                import magic
                __magicModule = magic.Magic()

            output = __magicModule.id_filename( path ).lower()
            if 'elf ' in output:
                if 'executable' in output:
                    __cachedFileTypes[ path ] = ELFFileType
                    return ELFFileType
                if 'shared object' in output:
                    __cachedFileTypes[ path ] = SOFileType
                    return SOFileType
                # Could be a core dump
                __cachedFileTypes[ path ] = UnknownELFFileType
                return UnknownELFFileType
            elif 'python ' in output:
                __cachedFileTypes[ path ] = PythonFileType
                return PythonFileType
            elif ' shell' in output:
                __cachedFileTypes[ path ] = ShellFileType
                return ShellFileType
            elif 'text' in output:
                if 'utf-8 ' in output:
                    __cachedFileTypes[ path ] = UTF8TextFile
                    return UTF8TextFile
                if 'ascii ' in output:
                    __cachedFileTypes[ path ] = ASCIITextFile
                    return ASCIITextFile
                if 'xml ' in output:
                    __cachedFileTypes[ path ] = XMLFileType
                    return XMLFileType
                __cachedFileTypes[ path ] = UTF8TextFile
                return UTF8TextFile
        except:
            pass

    __cachedFileTypes[ path ] = UnknownFileType
    return UnknownFileType


def closeMagicLibrary():
    global __magicModule
    if __magicModule is not None:
        __magicModule.close()
        __magicModule = None
    return

def isFileSearchable( fileName, checkForBrokenLink = True ):
    " Returns True if it makes sense to search for text in that file "
    return isFileTypeSearchable( detectFileType( fileName,
                                                 checkForBrokenLink ) )

def isFileTypeSearchable( fileType ):
    " Returns True if it makes sense to search for text in that file "
    return fileType not in [ PythonCompiledFileType, PixmapFileType,
                             ELFFileType, SOFileType, PDFFileType,
                             UnknownELFFileType, ObjectFileType,
                             BrokenSymlinkFileType, DirectoryFileType,
                             TarFileType, ArchiveFileType ]


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

    head, tail = split( path )
    while head:
        path = join( "%s%s" % ( head, ellipsis ), tail )
        if measure( path ) <= width:
            return path
        head = head[ :-1 ]

    path = join( ellipsis, tail )
    if measure( path ) <= width:
        return path

    while tail:
        path = "%s%s" % (ellipsis, tail)
        if measure( path ) <= width:
            return path
        tail = tail[ 1: ]

    return ""

