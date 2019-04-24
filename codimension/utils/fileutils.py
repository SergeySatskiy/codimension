# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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


"""file related utils"""

import os
from os.path import (islink, exists, split, join, sep, basename, realpath,
                     normpath, isabs, dirname)
import logging
import json
import magic
import tempfile
from errno import EACCES, ENOENT
from ui.qt import QImageReader

# Qutepart has a few maps which halp to map a file to a syntax.
from qutepart import Qutepart

from .pixmapcache import getIcon
from .config import DEFAULT_ENCODING


__QTSupportedImageFormats = [fmt.data().decode(DEFAULT_ENCODING) for fmt in
                             QImageReader.supportedImageFormats()]
VIEWABLE_IMAGE_MIMES = ['image/' + ext for ext in __QTSupportedImageFormats]


# NOTES
# The standard set of mime types does not cover all the required cases.
# In particular:
# - makefiles are not reliably distinguished
# - code and header files are detected as the same type but the icon needs to
#   be different
# - broken symbolic links are not distinguished


def __getXmlSyntaxFile(fName):
    """Checks the Qutepart mapping of a file extension to a syntax file.

    Returns: None if not found or a syntax file name
    """
    # Special cases: codimension project files
    #                makefiles
    if fName.endswith('.cdm'):
        return 'ini.xml'
    if fName.endswith('.cdm3'):
        return 'json.xml'
    if fName.endswith('.ts'):
        return 'xml.xml'
    if 'makefile' in fName.lower():
        return "makefile.xml"

    for regExp, xmlFileName in \
                Qutepart._globalSyntaxManager._extensionToXmlFileName.items():
        if regExp.match(fName):
            return xmlFileName
    return None


def __getMimeByXmlSyntaxFile(xmlSyntaxFile):
    """Checks the Qutepart mapping of a mime type to a syntax file.

    Returns a mime type or None
    """
    candidates = []
    for mime, xmlFileName in \
                Qutepart._globalSyntaxManager._mimeTypeToXmlFileName.items():
        if xmlFileName == xmlSyntaxFile:
            candidates.append(mime)
    if not candidates:
        # The qutepart syntax DB misses a markdown mime
        if xmlSyntaxFile == 'markdown.xml':
            return 'text/x-markdown'
        # ... and mako mime
        elif xmlSyntaxFile == 'mako.xml':
            return 'text/x-mako'
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Prefer the text candidate
    for item in candidates:
        if item.startswith('text'):
            return item
    return candidates[0]


def getXmlSyntaxFileByMime(mime):
    """Checks the Qutepart mapping of a mime type to a syntax file.

    Returns an xml syntax file or None
    """
    try:
        return Qutepart._globalSyntaxManager._mimeTypeToXmlFileName[mime]
    except KeyError:
        if mime == 'text/x-c++':
            return 'cpp.xml'
        return None


__magic = magic.Magic(mime=True)


def isFileSearchable(fName, checkForBrokenLink=True):
    """Returns True if it makes sense to search for text in that file"""
    mime, _, syntaxFile = getFileProperties(fName, checkForBrokenLink,
                                            skipCache=False)
    if syntaxFile is not None:
        # The files like libQt5Widgets.so.5 are mistakenly detected
        # as a man doc files (mandoc.xml)
        if mime:
            if mime.endswith('x-sharedlib'):
                return False
        return True
    if mime is None:
        return False
    return mime.startswith('text/')


def isImageViewable(mime):
    """True if QT can show the image"""
    if mime is None:
        return False
    return mime in VIEWABLE_IMAGE_MIMES


def isImageFile(fName):
    """True is the file is a viewable image"""
    mime, _, _ = getFileProperties(fName, checkForBrokenLink=True,
                                   skipCache=False)
    return isImageViewable(mime)


def isFileOpenable(fName):
    """True if codimension can open the file"""
    mime, _, syntaxFile = getFileProperties(fName, True, False)
    if syntaxFile is not None:
        return True
    return isImageViewable(mime)


__syntaxToIcon = None


def __initSyntaxToIcon():
    """Prevents calling getIcon before QApplication is created"""
    global __syntaxToIcon
    __syntaxToIcon = {
        'stata.xml': getIcon('filemisc.png'),
        'sisu.xml': getIcon('filemisc.png'),
        'mandoc.xml': getIcon('fileman.png'),
        'fgl-4gl.xml': getIcon('filemisc.png'),
        'ansforth94.xml': getIcon('filemisc.png'),
        'abap.xml': getIcon('filemisc.png'),
        'abc.xml': getIcon('filemisc.png'),
        'asm-avr.xml': getIcon('filemisc.png'),
        'freebasic.xml': getIcon('filemisc.png'),
        'wml.xml': getIcon('filemisc.png'),
        'd.xml': getIcon('filed.png'),
        'sql-oracle.xml': getIcon('filemisc.png'),
        'maxima.xml': getIcon('filemisc.png'),
        'fortran.xml': getIcon('filemisc.png'),
        'gdl.xml': getIcon('filemisc.png'),
        'haxe.xml': getIcon('filemisc.png'),
        'asm-m68k.xml': getIcon('filemisc.png'),
        'j.xml': getIcon('filemisc.png'),
        'lilypond.xml': getIcon('filemisc.png'),
        'asm-dsp56k.xml': getIcon('filemisc.png'),
        'jsp.xml': getIcon('filemisc.png'),
        'objectivecpp.xml': getIcon('filemisc.png'),
        'mab.xml': getIcon('filemisc.png'),
        'fgl-per.xml': getIcon('filemisc.png'),
        'pgn.xml': getIcon('filemisc.png'),
        'picsrc.xml': getIcon('filemisc.png'),
        'perl.xml': getIcon('fileperl.png'),
        'xharbour.xml': getIcon('filemisc.png'),
        'r.xml': getIcon('filemisc.png'),
        'rmarkdown.xml': getIcon('filemisc.png'),
        'relaxng.xml': getIcon('filemisc.png'),
        'verilog.xml': getIcon('filemisc.png'),
        'ada.xml': getIcon('fileada.png'),
        'hunspell-aff.xml': getIcon('filemisc.png'),
        'agda.xml': getIcon('filemisc.png'),
        'ahdl.xml': getIcon('filemisc.png'),
        'ahk.xml': getIcon('filemisc.png'),
        'postscript.xml': getIcon('filepostscript.png'),
        'ample.xml': getIcon('filemisc.png'),
        'ansys.xml': getIcon('filemisc.png'),
        'actionscript.xml': getIcon('filemisc.png'),
        'asn1.xml': getIcon('filemisc.png'),
        'asp.xml': getIcon('filemisc.png'),
        'awk.xml': getIcon('fileawk.png'),
        'bash.xml': getIcon('fileshell.png'),
        'dosbat.xml': getIcon('filemisc.png'),
        'latex.xml': getIcon('filetex.png'),
        'bibtex.xml': getIcon('filetex.png'),
        'boo.xml': getIcon('filemisc.png'),
        'component-pascal.xml': getIcon('filepascal.png'),
        'gdb.xml': getIcon('filemisc.png'),
        '4dos.xml': getIcon('filemisc.png'),
        'c.xml': getIcon('filec.png'),
        'ccss.xml': getIcon('filecss.png'),
        'coldfusion.xml': getIcon('filemisc.png'),
        'nagios.xml': getIcon('filemisc.png'),
        'cg.xml': getIcon('filemisc.png'),
        'cgis.xml': getIcon('filemisc.png'),
        'chicken.xml': getIcon('filemisc.png'),
        'haskell.xml': getIcon('filemisc.png'),
        'cisco.xml': getIcon('filemisc.png'),
        'opencl.xml': getIcon('filemisc.png'),
        'clojure.xml': getIcon('filemisc.png'),
        'cmake.xml': getIcon('filemake.png'),
        'coffee.xml': getIcon('filemisc.png'),
        'logtalk.xml': getIcon('filemisc.png'),
        'crk.xml': getIcon('filemisc.png'),
        'cs.xml': getIcon('filemisc.png'),
        'tcsh.xml': getIcon('fileshell.png'),
        'css.xml': getIcon('filecss.png'),
        'context.xml': getIcon('filemisc.png'),
        'cue.xml': getIcon('filemisc.png'),
        'curry.xml': getIcon('filemisc.png'),
        'xml.xml': getIcon('filexml.png'),
        'hunspell-dat.xml': getIcon('filemisc.png'),
        'prolog.xml': getIcon('filemisc.png'),
        'modula-2.xml': getIcon('filemisc.png'),
        'desktop.xml': getIcon('filemisc.png'),
        'hunspell-dic.xml': getIcon('filemisc.png'),
        'diff.xml': getIcon('filediff.png'),
        'dot.xml': getIcon('filemisc.png'),
        'doxygen.xml': getIcon('filemisc.png'),
        'dtd.xml': getIcon('filemisc.png'),
        'euphoria.xml': getIcon('filemisc.png'),
        'email.xml': getIcon('fileemail.png'),
        'erlang.xml': getIcon('filemisc.png'),
        'fasm.xml': getIcon('filemisc.png'),
        'ferite.xml': getIcon('filemisc.png'),
        'lex.xml': getIcon('filemisc.png'),
        'glsl.xml': getIcon('filemisc.png'),
        'fsharp.xml': getIcon('filemisc.png'),
        'ftl.xml': getIcon('filemisc.png'),
        'grammar.xml': getIcon('filemisc.png'),
        'gap.xml': getIcon('filemisc.png'),
        'glosstex.xml': getIcon('filetex.png'),
        'ruby.xml': getIcon('filemisc.png'),
        'gnuplot.xml': getIcon('filemisc.png'),
        'go.xml': getIcon('filemisc.png'),
        'groovy.xml': getIcon('filemisc.png'),
        'scheme.xml': getIcon('filemisc.png'),
        'haml.xml': getIcon('filemisc.png'),
        'hamlet.xml': getIcon('filemisc.png'),
        'spice.xml': getIcon('filemisc.png'),
        'html.xml': getIcon('filehtml.png'),
        'rhtml.xml': getIcon('filemisc.png'),
        'progress.xml': getIcon('filemisc.png'),
        'vcard.xml': getIcon('filevcard.png'),
        'idl.xml': getIcon('fileidl.png'),
        'hunspell-idx.xml': getIcon('filemisc.png'),
        'bmethod.xml': getIcon('filemisc.png'),
        'opal.xml': getIcon('filemisc.png'),
        'html-php.xml': getIcon('filemisc.png'),
        'inform.xml': getIcon('filemisc.png'),
        'ini.xml': getIcon('fileprops.png'),
        'jam.xml': getIcon('filemisc.png'),
        'java.xml': getIcon('filejava.png'),
        'jira.xml': getIcon('filemisc.png'),
        'julia.xml': getIcon('filemisc.png'),
        'javascript.xml': getIcon('filejs.png'),
        'json.xml': getIcon('filemisc.png'),
        'k.xml': getIcon('filemisc.png'),
        'kbasic.xml': getIcon('filemisc.png'),
        'literate-curry.xml': getIcon('filemisc.png'),
        'ld.xml': getIcon('filemisc.png'),
        'ldif.xml': getIcon('filemisc.png'),
        'less.xml': getIcon('filemisc.png'),
        'literate-haskell.xml': getIcon('filemisc.png'),
        'commonlisp.xml': getIcon('filemisc.png'),
        'lsl.xml': getIcon('filemisc.png'),
        'lua.xml': getIcon('filemisc.png'),
        'octave.xml': getIcon('filemisc.png'),
        'm3u.xml': getIcon('filemisc.png'),
        'm4.xml': getIcon('filemisc.png'),
        'mako.xml': getIcon('filemisc.png'),
        'markdown.xml': getIcon('filemisc.png'),
        'mediawiki.xml': getIcon('filemisc.png'),
        'mel.xml': getIcon('filemisc.png'),
        'metafont.xml': getIcon('filemisc.png'),
        'makefile.xml': getIcon('filemake.png'),
        'ocaml.xml': getIcon('filemisc.png'),
        'ocamllex.xml': getIcon('filemisc.png'),
        'ocamlyacc.xml': getIcon('filemisc.png'),
        'modelica.xml': getIcon('filemisc.png'),
        'carto-css.xml': getIcon('filecss.png'),
        'mergetagtext.xml': getIcon('filemisc.png'),
        'mup.xml': getIcon('filemisc.png'),
        'nemerle.xml': getIcon('filemisc.png'),
        'mathematica.xml': getIcon('filemisc.png'),
        'nesc.xml': getIcon('filemisc.png'),
        'nsis.xml': getIcon('filemisc.png'),
        'noweb.xml': getIcon('filemisc.png'),
        'lpc.xml': getIcon('filemisc.png'),
        'oors.xml': getIcon('filemisc.png'),
        'pascal.xml': getIcon('filepascal.png'),
        'purebasic.xml': getIcon('filemisc.png'),
        'pig.xml': getIcon('filemisc.png'),
        'pike.xml': getIcon('filemisc.png'),
        'pli.xml': getIcon('filemisc.png'),
        'gettext.xml': getIcon('filemisc.png'),
        'povray.xml': getIcon('filemisc.png'),
        'puppet.xml': getIcon('filemisc.png'),
        'ppd.xml': getIcon('filemisc.png'),
        'qmake.xml': getIcon('filemake.png'),
        'protobuf.xml': getIcon('filemisc.png'),
        'python.xml': getIcon('filepython.png'),
        'qml.xml': getIcon('filemisc.png'),
        'winehq.xml': getIcon('filemisc.png'),
        'replicode.xml': getIcon('filemisc.png'),
        'rexx.xml': getIcon('filemisc.png'),
        'rib.xml': getIcon('filemisc.png'),
        'relaxngcompact.xml': getIcon('filemisc.png'),
        'rapidq.xml': getIcon('filemisc.png'),
        'rust.xml': getIcon('filemisc.png'),
        'rest.xml': getIcon('filemisc.png'),
        'rtf.xml': getIcon('filertf.png'),
        'sather.xml': getIcon('filemisc.png'),
        'scala.xml': getIcon('filemisc.png'),
        'sci.xml': getIcon('filemisc.png'),
        'scss.xml': getIcon('filecss.png'),
        'sed.xml': getIcon('filemisc.png'),
        'sgml.xml': getIcon('filemisc.png'),
        'zsh.xml': getIcon('fileshell.png'),
        'sieve.xml': getIcon('filemisc.png'),
        'sml.xml': getIcon('filemisc.png'),
        'rpmspec.xml': getIcon('filemisc.png'),
        'valgrind-suppression.xml': getIcon('filemisc.png'),
        'systemverilog.xml': getIcon('filemisc.png'),
        'tads3.xml': getIcon('filemisc.png'),
        'txt2tags.xml': getIcon('filemisc.png'),
        'tcl.xml': getIcon('filetcl.png'),
        'texinfo.xml': getIcon('filetex.png'),
        'textile.xml': getIcon('filemisc.png'),
        'taskjuggler.xml': getIcon('filemisc.png'),
        'toml.xml': getIcon('filemisc.png'),
        'template-toolkit.xml': getIcon('filemisc.png'),
        'uscript.xml': getIcon('filemisc.png'),
        'vala.xml': getIcon('filemisc.png'),
        'monobasic.xml': getIcon('filemisc.png'),
        'varnishcc4.xml': getIcon('filemisc.png'),
        'varnish4.xml': getIcon('filemisc.png'),
        'vhdl.xml': getIcon('filemisc.png'),
        'velocity.xml': getIcon('filemisc.png'),
        'vera.xml': getIcon('filemisc.png'),
        'varnishtest4.xml': getIcon('filemisc.png'),
        'vrml.xml': getIcon('filemisc.png'),
        'xslt.xml': getIcon('filexml.png'),
        'xul.xml': getIcon('filemisc.png'),
        'yaml.xml': getIcon('filemisc.png'),
        'yacas.xml': getIcon('filemisc.png'),
        'yacc.xml': getIcon('filemisc.png'),
        'zonnon.xml': getIcon('filemisc.png'),
        'asterisk.xml': getIcon('filemisc.png'),
        'git-ignore.xml': getIcon('filemisc.png'),
        'kdesrc-buildrc.xml': getIcon('filemisc.png'),
        'changelog.xml': getIcon('filemisc.png'),
        'dockerfile.xml': getIcon('filemisc.png'),
        'kconfig.xml': getIcon('filemisc.png'),
        'ilerpg.xml': getIcon('filemisc.png'),
        'apache.xml': getIcon('filemisc.png'),
        'debiancontrol.xml': getIcon('filemisc.png'),
        'fstab.xml': getIcon('filemisc.png'),
        'git-rebase.xml': getIcon('filemisc.png'),
        'gitolite.xml': getIcon('filemisc.png'),
        'meson.xml': getIcon('filemisc.png'),
        'xorg.xml': getIcon('filemisc.png'),
        'markdown.xml': getIcon('filemarkdown.png')}


# Some specific cases for various binaries to be mapped to a certain icon
__mimeToIcon = None


def __initMimeToIcon():
    """Prevents calling getIcon() before QApplication is created"""
    global __mimeToIcon
    __mimeToIcon = {
        'application/x-executable': getIcon('filebinary.png'),
        'application/x-sharedlib': getIcon('fileso.png'),
        'application/x-coredump': getIcon('filemisc.png'),
        'application/pdf': getIcon('filepdf.png'),
        'application/x-bzip2': getIcon('filearchive.png'),
        'application/x-gzip': getIcon('filearchive.png'),
        'application/zip': getIcon('filearchive.png'),
        'application/x-xz': getIcon('filearchive.png'),
        'application/x-rar': getIcon('filearchive.png'),
        'application/x-tar': getIcon('filetar.png'),
        'application/x-object': getIcon('fileso.png')}


def __getIcon(xmlSyntaxFile, mime, fBaseName):
    """Provides an icon for a file"""
    fileExtension = fBaseName.split('.')[-1].lower()

    if xmlSyntaxFile is not None:
        # There are a few special cases:
        # - svg is detected as xml.xml
        # - c/c++/h/h++ are detected as cpp.xml
        # - cdm project is detected as ini.xml
        if xmlSyntaxFile == 'ini.xml':
            if fileExtension == 'cdm':
                return getIcon('fileproject.png')
        if xmlSyntaxFile == 'json.xml':
            if fileExtension == 'cdm3':
                return getIcon('fileproject.png')
        if xmlSyntaxFile == 'cpp.xml':
            if 'h' in fileExtension:
                if fBaseName.endswith('.ui.h'):
                    return getIcon('filedesigner.png')
                if fBaseName.endswith('.h'):    # Capital H is for C++
                    return getIcon('filecheader.png')
                return getIcon('filecppheader.png')
            return getIcon('filecpp.png')
        if xmlSyntaxFile == 'xml.xml':
            if fileExtension == 'svg':
                return getIcon('filesvg.png')
            if fileExtension == "ui":
                return getIcon('filedesigner.png')
            if fileExtension in ['ts', 'qm']:
                return getIcon('filelinguist2.png')
            if fileExtension == 'qrc':
                return getIcon('fileresource.png')

        try:
            if __syntaxToIcon is None:
                __initSyntaxToIcon()
            return __syntaxToIcon[xmlSyntaxFile]
        except KeyError:
            return getIcon('filemisc.png')

    # Here: no luck with a syntax file
    # This could be an image or compiled python or binary of some sort...
    # Or a text which does not need a syntax highlight

    if fileExtension in __QTSupportedImageFormats:
        return getIcon('filepixmap.png')

    try:
        if mime is not None:
            if __mimeToIcon is None:
                __initMimeToIcon()
            return __mimeToIcon[mime]
    except KeyError:
        pass

    if fileExtension in ['pyc', 'pyo']:
        return getIcon('filepythoncompiled.png')

    if mime is not None:
        if mime == 'application/x-executable':
            return getIcon('filebinary.png')
        if mime.startswith('text/'):
            return getIcon('filetext.png')
    return getIcon('filemisc.png')


def __getMagicMime(fName):
    """Uses the magic module to retrieve the file mime.

    The mime could be None if e.g. the file does not exist.
    The second bool tells if it was a permission denied case.
    """
    try:
        # E.g.: 'text/x-shellscript'
        output = __magic.from_file(realpath(fName))
        return output, False
    except OSError as exc:
        if exc.errno == EACCES:
            return None, True
        if exc.errno == ENOENT:
            return None, False
        logging.error(str(exc))
        return None, False
    except Exception as exc:
        # Most probably the file does not exist
        logging.error(str(exc))
        return None, False


def getMagicMimeFromBuffer(txt):
    """Guesses the buffer text mime type"""
    try:
        return __magic.from_buffer(txt)
    except:
        return None


# Cache is initialized with:
# - an unknown file type properties: ''
# - a directory: '/'
# - broken symlink: '.'
__filePropertiesCache = None


def __initFilePropertiesCache():
    """Prevents calling getIcon before a QApplication is created"""
    global __filePropertiesCache
    __filePropertiesCache = {
        '': [None, getIcon('filemisc.png'), None],
        '/': ['inode/directory', getIcon('dirclosed.png'), None],
        '.': ['inode/broken-symlink', getIcon('filebrokenlink.png'), None]}


def getFileProperties(fName, checkForBrokenLink=True, skipCache=False):
    """Provides the following properties:

    - mime type (could be None)
    - icon
    - syntax file name (could be None)

    Works for non-existing files too.
    Special cases:
    - fName ends with os.path.sep => directory
    - fName is empy or None => unknown file type
    """
    if __filePropertiesCache is None:
        __initFilePropertiesCache()

    if not fName:
        return __filePropertiesCache['']

    if fName.endswith(sep):
        return __filePropertiesCache['/']

    if checkForBrokenLink and islink(fName):
        if not exists(fName):
            return __filePropertiesCache['.']

    if not skipCache and fName in __filePropertiesCache:
        value = __filePropertiesCache[fName]
        if value[0] is None:
            mime, _ = __getMagicMime(fName)
            if mime is not None:
                value[0] = mime
                __filePropertiesCache[fName] = value
        return value

    # The function should work both for existing and non-existing files
    try:
        # If a file exists then it could be a symbolic link to
        # a different name file
        fBaseName = basename(realpath(fName))
    except:
        # File may not exist
        fBaseName = basename(fName)

    fileExtension = fBaseName.split('.')[-1].lower()

    syntaxFile = __getXmlSyntaxFile(fBaseName)
    if syntaxFile is None:
        denied = False
        # Special case: this could be a QT supported image
        if fileExtension in __QTSupportedImageFormats:
            mime = 'image/' + fileExtension
        elif 'readme' in fBaseName.lower():
            mime = 'text/plain'
        else:
            mime, denied = __getMagicMime(fName)
            if mime is not None:
                syntaxFile = getXmlSyntaxFileByMime(mime)

        cacheValue = [mime,
                      getIcon('filedenied.png') if denied else
                      __getIcon(syntaxFile, mime, fBaseName),
                      syntaxFile]
        __filePropertiesCache[fName] = cacheValue
        return cacheValue

    # syntax file was successfully identified.
    # Detect the mime type by a syntax file
    if fileExtension == 'cdm':
        mime = 'text/x-codimension'
    elif fileExtension == 'cdm3':
        mime = 'text/x-codimension3'
    else:
        mime = __getMimeByXmlSyntaxFile(syntaxFile)
        if mime is None:
            mime, _ = __getMagicMime(fName)

    if fileExtension == 'o' and syntaxFile == 'lpc.xml':
        # lpc.xml is bound to .o extension i.e. exactly object files!
        if 'object' in mime:
            syntaxFile = None
    if fileExtension == 'a' and syntaxFile == 'ada.xml':
        tryMime, _ = __getMagicMime(fName)
        if 'x-archive' in tryMime:
            mime = tryMime
            syntaxFile = None
    if fileExtension == 'ttf' and syntaxFile == 'template-toolkit.xml':
        tryMime, _ = __getMagicMime(fName)
        if 'font' in tryMime:
            mime = tryMime
            syntaxFile = None
    if fileExtension == 'dat' and syntaxFile == 'hunspell-dat.xml':
        tryMime, _ = __getMagicMime(fName)
        if 'octet-stream' in tryMime:
            mime = tryMime
            syntaxFile = None

    cacheValue = [mime, __getIcon(syntaxFile, mime, fBaseName), syntaxFile]
    __filePropertiesCache[fName] = cacheValue
    return cacheValue


def compactPath(path, width, measure=len):
    """Provides a compacted path fitting inside the given width.

    measure - ref to a function used to get the length of the string
    """
    if measure(path) <= width:
        return path

    dots = '...'

    head, tail = split(path)
    mid = len(head) // 2
    head1 = head[:mid]
    head2 = head[mid:]

    while head1:
        path = join("%s%s%s" % (head1, dots, head2), tail)
        if measure(path) <= width:
            return path
        head1 = head1[:-1]
        head2 = head2[1:]

    path = join(dots, tail)
    if measure(path) <= width:
        return path

    while tail:
        path = "%s%s" % (dots, tail)
        if measure(path) <= width:
            return path
        tail = tail[1:]
    return ''


def isPythonFile(fName):
    """True if it is a python file"""
    mime, _, _ = getFileProperties(fName)
    if mime is None:
        return False
    return 'python' in mime


def isPythonMime(mime):
    """True if it is a python mime"""
    if mime is None:
        return False
    return 'python' in mime


def isMarkdownMime(mime):
    """True if it is a markdown mime"""
    if mime:
        return 'markdown' in mime
    return False


def isPythonCompiledFile(fName):
    """True if it is a python compiled file"""
    mime, _, _ = getFileProperties(fName)
    if mime is None:
        return False
    if 'octet-stream' in mime:
        if fName.endswith('.pyc') or fName.endswith('.pyo'):
            return True
    return False


def isCDMProjectMime(mime):
    """True if it is a codimension project mime"""
    if mime is None:
        return False
    return 'x-codimension3' in mime


def isCDMProjectFile(fName):
    """True if it is a codimension project file"""
    mime, _, _ = getFileProperties(fName)
    if mime is None:
        return False
    return 'x-codimension3' in mime


# Utility functions to save/load generic JSON
def loadJSON(fileName, errorWhat, defaultValue):
    """Generic JSON loading"""
    try:
        with open(fileName, 'r', encoding=DEFAULT_ENCODING) as diskfile:
            return json.load(diskfile)
    except Exception as exc:
        logging.error('Error loading ' + errorWhat +
                      ' (from ' + fileName + '): ' + str(exc))
        return defaultValue


def saveJSON(fileName, values, errorWhat):
    """Generic JSON saving"""
    try:
        with open(fileName, 'w', encoding=DEFAULT_ENCODING) as diskfile:
            json.dump(values, diskfile, indent=4)
    except Exception as exc:
        logging.error('Error saving ' + errorWhat +
                      ' (to ' + fileName + '): ' + str(exc))
        return False
    return True


def getFileContent(fileName, allowException=True, enc=DEFAULT_ENCODING):
    """Provides the file content"""
    try:
        with open(fileName, 'r', encoding=enc) as diskfile:
            content = diskfile.read()
        return content
    except Exception as exc:
        if allowException:
            raise
        logging.error('Error reading from file ' + fileName + ': ' +
                      str(exc))
        return None


def saveToFile(fileName, content, allowException=True, enc=DEFAULT_ENCODING):
    """Overwrites the file content"""
    try:
        with open(fileName, 'w', encoding=enc) as diskfile:
            diskfile.write(content)
        return True
    except Exception as exc:
        if allowException:
            raise
        logging.error('Error writing to file ' + fileName + ': ' +
                      str(exc))
    return False


def saveBinaryToFile(fileName, content, allowException=True):
    """Overwrites the file content"""
    try:
        with open(fileName, 'wb') as diskfile:
            diskfile.write(content)
        return True
    except Exception as exc:
        if allowException:
            raise
        logging.error('Error writing to file ' + fileName + ': ' +
                      str(exc))
    return False


def makeTempFile(prefix='cdm_', suffix=None):
    """Creates a temporary file"""
    fileHandle, fileName = tempfile.mkstemp(suffix, prefix)
    os.close(fileHandle)
    return fileName


def resolveLink(path):
    """Resolves links and detects loops"""
    paths_seen = []
    while islink(path):
        if path in paths_seen:
            # Already seen this path, so we must have a symlink loop
            return path, True
        paths_seen.append(path)
        # Resolve where the link points to
        resolved = os.readlink(path)
        if not isabs(resolved):
            dir_name = dirname(path)
            path = normpath(dir_name + sep + resolved)
        else:
            path = normpath(resolved)
    return path, False
