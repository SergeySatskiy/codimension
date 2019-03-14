# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Encoding related functions"""

import re
import encodings
import logging
import os.path
from codecs import BOM_UTF8, BOM_UTF16, BOM_UTF32
from cdmpyparser import getBriefModuleInfoFromMemory
from .diskvaluesrelay import getFileEncoding
from .fileutils import isPythonFile
from .globals import GlobalData
from .settings import Settings
from .config import DEFAULT_ENCODING


# There is no way to query a complete list of the supported codecs at run-time.
# So there is the list below.
# Note: aliases are not included into the list (could be retrieved at run-time)
# Note: there could be user registered codecs as well
# Note: the list is copied from the python documentation:
#       https://docs.python.org/3/library/codecs.html
# Note: instead of the '_' char in the list the '-' was used: it looks nicer
STANDARD_CODECS = ['ascii', 'big5', 'big5hkscs', 'cp037', 'cp273', 'cp424',
                   'cp437', 'cp500', 'cp720', 'cp737', 'cp775', 'cp850',
                   'cp852', 'cp855', 'cp856', 'cp857', 'cp858', 'cp860',
                   'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866',
                   'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950',
                   'cp1006', 'cp1026', 'cp1125', 'cp1140', 'cp1250',
                   'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255',
                   'cp1256', 'cp1257', 'cp1258', 'cp65001', 'euc_jp',
                   'euc-jis-2004', 'euc-jisx0213', 'euc-kr', 'gb2312',
                   'gbk', 'gb18030', 'hz', 'iso2022-jp', 'iso2022-jp-1',
                   'iso2022-jp-2', 'iso2022-jp-2004', 'iso2022-jp-3',
                   'iso2022_jp-ext', 'iso2022-kr', 'latin-1', 'iso8859-2',
                   'iso8859-3', 'iso8859-4', 'iso8859-5', 'iso8859-6',
                   'iso8859-7', 'iso8859-8', 'iso8859-9', 'iso8859-10',
                   'iso8859-11', 'iso8859-13', 'iso8859-14', 'iso8859-15',
                   'iso8859-16', 'johab', 'koi8-r', 'koi8-t', 'koi8-u',
                   'kz1048', 'mac-cyrillic', 'mac-greek', 'mac-iceland',
                   'mac-latin2', 'mac-roman', 'mac-turkish', 'ptcp154',
                   'shift-jis', 'shift-jis-2004', 'shift-jisx0213',
                   'utf-32', 'utf-32-be', 'utf-32-le',
                   'utf-16', 'utf-16-be', 'utf-16-le',
                   'utf-7', 'utf-8', 'utf-8-sig']

# These codecs were introduced to support BOM signatures without loosing
# them in the read->modify->write cycle
SYNTHETIC_CODECS = ['bom-utf-8', 'bom-utf-16', 'bom-utf-32']

SUPPORTED_CODECS = STANDARD_CODECS + SYNTHETIC_CODECS


CODING_FROM_BYTES = [
    (2, re.compile(br'''coding[:=]\s*([-\w_.]+)''')),
    (1, re.compile(br'''<\?xml.*\bencoding\s*=\s*['"]([-\w_.]+)['"]\?>'''))]


CODING_FROM_TEXT = [
    (2, re.compile(r'''coding[:=]\s*([-\w_.]+)''')),
    (1, re.compile(r'''<\?xml.*\bencoding\s*=\s*['"]([-\w_.]+)['"]\?>'''))]


def convertLineEnds(text, eol):
    """Converts the end of line characters in text to the given eol"""
    if eol == '\r\n':
        regexp = re.compile(r"(\r(?!\n)|(?<!\r)\n)")
        return regexp.sub(lambda m, eol='\r\n': eol, text)
    if eol == '\n':
        regexp = re.compile(r"(\r\n|\r)")
        return regexp.sub(lambda m, eol='\n': eol, text)
    if eol == '\r':
        regexp = re.compile(r"(\r\n|\n)")
        return regexp.sub(lambda m, eol='\r': eol, text)
    return text


def detectEolString(text):
    """Detects the eol string using the first split. It cannot detect a mix"""
    if len(text.split('\r\n', 1)) == 2:
        return '\r\n'
    if len(text.split('\r', 1)) == 2:
        return '\r'
    return '\n'


def isValidEncoding(enc):
    """Checks if it is a valid encoding"""
    norm_enc = encodings.normalize_encoding(enc).lower()
    if norm_enc in SUPPORTED_CODECS:
        return True
    if norm_enc in [encodings.normalize_encoding(supp_enc)
                    for supp_enc in SUPPORTED_CODECS]:
        return True

    # Check the aliases as well
    if norm_enc in encodings.aliases.aliases:
        return True
    return False


def getNormalizedEncoding(enc, validityCheck=True):
    """Returns a normalized encoding or throws an exception"""
    if validityCheck:
        if not isValidEncoding(enc):
            raise Exception('Unsupported encoding ' + enc)
    norm_enc = encodings.normalize_encoding(enc).lower()
    return encodings.aliases.aliases.get(norm_enc, norm_enc)


def areEncodingsEqual(enc_lhs, enc_rhs):
    """True if the encodings are essentially the same"""
    return getNormalizedEncoding(enc_lhs) == getNormalizedEncoding(enc_rhs)


def getCodingFromBytes(text):
    """Tries to find an encoding spec from a binary file content"""
    lines = text.splitlines()
    for cfb in CODING_FROM_BYTES:
        head = lines[:cfb[0]]
        regexp = cfb[1]
        for line in head:
            match = regexp.search(line)
            if match:
                return str(match.group(1), 'ascii')
    return None


def getCodingFromText(text):
    """Tries to find an encoding spec from a text file content"""
    lines = text.splitlines()
    for cft in CODING_FROM_TEXT:
        head = lines[:cft[0]]
        regexp = cft[1]
        for line in head:
            match = regexp.search(line)
            if match:
                return match.group(1)
    return None


def encodingSanityCheck(fName, decodedText, expectedEncoding):
    """Checks if the expected encoding matches the encing in the file"""
    try:
        modInfo = getBriefModuleInfoFromMemory(decodedText)
        modEncoding = modInfo.encoding
        if modEncoding:
            if not isValidEncoding(modEncoding.name):
                logging.warning("Invalid encoding " + modEncoding.name +
                                " found in the file " + fName)
                return False
            if not areEncodingsEqual(modEncoding.name, expectedEncoding):
                if expectedEncoding.startswith('bom-'):
                    noBomEncoding = expectedEncoding[4:]
                    if areEncodingsEqual(modEncoding.name, noBomEncoding):
                        return True
                logging.warning("The explicitly set encoding " +
                                expectedEncoding +
                                " does not match encoding " + modEncoding.name +
                                " found in the file " + fName)
                return False
    except:
        pass
    return True


def detectEncodingOnClearExplicit(fName, content):
    """Provides the reading encoding as a file would be read"""
    # The function is used in case the user reset the explicit encoding
    # so the current encoding needs to be set as if the file would be
    # read again
    try:
        with open(fName, 'rb') as diskfile:
            text = diskfile.read(1024)

        if text.startswith(BOM_UTF8):
            return 'bom-utf-8'
        if text.startswith(BOM_UTF16):
            return 'bom-utf-16'
        if text.startswith(BOM_UTF32):
            return 'bom-utf-32'

        # The function is called when an explicit encoding is reset so
        # there is no need to check for it

        encFromBuffer = getCodingFromText(content)
        if encFromBuffer:
            if isValidEncoding(encFromBuffer):
                return encFromBuffer

        project = GlobalData().project
        if project.isLoaded():
            projectEncoding = project.props['encoding']
            if projectEncoding:
                if isValidEncoding(projectEncoding):
                    return projectEncoding

        ideEncoding = Settings()['encoding']
        if ideEncoding:
            if isValidEncoding(ideEncoding):
                return ideEncoding

        return DEFAULT_ENCODING
    except Exception as exc:
        logging.warning("Error while guessing encoding for reading " +
                        fName + ": " + str(exc) + "\n"
                        "The default encoding " +
                        DEFAULT_ENCODING + " will be used.")
        return DEFAULT_ENCODING


def detectFileEncodingToRead(fName, text=None):
    """Detects the read encoding"""
    if text is None:
        with open(fName, 'rb') as diskfile:
            text = diskfile.read(1024)

    # Step 1: check for BOM
    if text.startswith(BOM_UTF8):
        return 'bom-utf-8'
    if text.startswith(BOM_UTF16):
        return 'bom-utf-16'
    if text.startswith(BOM_UTF32):
        return 'bom-utf-32'

    # Check if it was a user assigned encoding
    userAssignedEncoding = getFileEncoding(fName)
    if userAssignedEncoding:
        return userAssignedEncoding

    # Step 3: extract encoding from the file
    encFromFile = getCodingFromBytes(text)
    if encFromFile:
        return encFromFile

    # Step 4: check the project default encoding
    project = GlobalData().project
    if project.isLoaded():
        projectEncoding = project.props['encoding']
        if projectEncoding:
            return projectEncoding

    # Step 5: checks the IDE encoding
    ideEncoding = Settings()['encoding']
    if ideEncoding:
        return ideEncoding

    # Step 6: default
    return DEFAULT_ENCODING


def readEncodedFile(fName):
    """Reads the encoded file"""
    # Returns: text, used encoding
    with open(fName, 'rb') as diskfile:
        text = diskfile.read()

    isPython = isPythonFile(fName)
    triedEncodings = []
    # Step 1: check for BOM
    try:
        if text.startswith(BOM_UTF8):
            text = text[len(BOM_UTF8):]
            normEnc = encodings.normalize_encoding('utf-8')
            triedEncodings.append(normEnc)
            decodedText = str(text, normEnc)
            if isPython:
                encodingSanityCheck(fName, decodedText, 'bom-utf-8')
            return decodedText, 'bom-utf-8'
        if text.startswith(BOM_UTF16):
            text = text[len(BOM_UTF16):]
            normEnc = encodings.normalize_encoding('utf-16')
            triedEncodings.append(normEnc)
            decodedText = str(text, normEnc)
            if isPython:
                encodingSanityCheck(fName, decodedText, 'bom-utf-16')
            return decodedText, 'bom-utf-16'
        if text.startswith(BOM_UTF32):
            text = text[len(BOM_UTF32):]
            normEnc = encodings.normalize_encoding('utf-32')
            triedEncodings.append(normEnc)
            decodedText = str(text, normEnc)
            if isPython:
                encodingSanityCheck(fName, decodedText, 'bom-utf-32')
            return decodedText, 'bom-utf-32'
    except (UnicodeError, LookupError) as exc:
        logging.error("BOM signature bom-" + triedEncodings[0] +
                      " found in the file but decoding failed: " + str(exc))
        logging.error("Continue trying to decode...")

    # Check if it was a user assigned encoding
    userAssignedEncoding = getFileEncoding(fName)
    if userAssignedEncoding:
        if not isValidEncoding(userAssignedEncoding):
            logging.error("User assigned encoding " + userAssignedEncoding +
                          " is invalid. Continue trying to decode...")
        elif encodings.normalize_encoding(userAssignedEncoding) \
                not in triedEncodings:
            normEnc = encodings.normalize_encoding(userAssignedEncoding)
            triedEncodings.append(normEnc)
            try:
                decodedText = str(text, normEnc)
                if isPython:
                    encodingSanityCheck(fName, decodedText,
                                        userAssignedEncoding)
                return decodedText, userAssignedEncoding
            except (UnicodeError, LookupError) as exc:
                logging.error("Failed to decode using the user assigned "
                              "encoding " + userAssignedEncoding +
                              ". Continue trying...")

    # Step 3: extract encoding from the file
    encFromFile = getCodingFromBytes(text)
    if encFromFile:
        if not isValidEncoding(encFromFile):
            logging.error("Invalid encoding found in the content: " +
                          encFromFile + ". Continue trying...")
        elif encodings.normalize_encoding(encFromFile) not in triedEncodings:
            normEnc = encodings.normalize_encoding(encFromFile)
            triedEncodings.append(normEnc)
            try:
                decodedText = str(text, normEnc)
                if isPython:
                    encodingSanityCheck(fName, decodedText,
                                        encFromFile)
                return decodedText, encFromFile
            except (UnicodeError, LookupError) as exc:
                logging.error("Failed to decode using encoding " +
                              encFromFile + " found in the file. "
                              "Continue trying...")

    # Step 4: check the project default encoding
    project = GlobalData().project
    if project.isLoaded():
        projectEncoding = project.props['encoding']
        normProjectEncoding = encodings.normalize_encoding(projectEncoding)
        if projectEncoding:
            if not isValidEncoding(projectEncoding):
                logging.error("Invalid project encoding: " +
                              projectEncoding + ". Continue trying...")
            elif normProjectEncoding not in triedEncodings:
                triedEncodings.append(normProjectEncoding)
                try:
                    decodedText = str(text, normProjectEncoding)
                    if isPython:
                        encodingSanityCheck(fName, decodedText,
                                            projectEncoding)
                    return decodedText, projectEncoding
                except (UnicodeError, LookupError) as exc:
                    logging.error("Failed to decode using project encoding " +
                                  projectEncoding + ". Continue trying...")

    # Step 5: checks the IDE encoding
    ideEncoding = Settings()['encoding']
    if ideEncoding:
        normIdeEnc = encodings.normalize_encoding(ideEncoding)
        if not isValidEncoding(ideEncoding):
            logging.error("Invalid ide encoding: " +
                          ideEncoding + ". Continue trying...")
        elif normIdeEnc not in triedEncodings:
            triedEncodings.append(normIdeEnc)
            try:
                decodedText = str(text, normIdeEnc)
                if isPython:
                    encodingSanityCheck(fName, decodedText,
                                        ideEncoding)
                return decodedText, ideEncoding
            except (UnicodeError, LookupError) as exc:
                logging.error("Failed to decode using project encoding " +
                              ideEncoding + ". Continue trying...")

    # Step 6: default
    normDefEnc = encodings.normalize_encoding(DEFAULT_ENCODING)
    if normDefEnc not in triedEncodings:
        triedEncodings.append(normDefEnc)
        try:
            decodedText = str(text, normDefEnc)
            if isPython:
                encodingSanityCheck(fName, decodedText,
                                    DEFAULT_ENCODING)
            return decodedText, DEFAULT_ENCODING
        except (UnicodeError, LookupError) as exc:
            logging.error("Failed to decode using default encoding " +
                          DEFAULT_ENCODING + ". Continue trying...")

    # Step 7: last resort utf-8 with loosing information
    logging.warning("Last try: utf-8 decoding ignoring the errors...")
    return str(text, 'utf-8', 'ignore'), 'utf-8'


def detectNewFileWriteEncoding(editor, fName):
    """Detects a new file encoding"""
    # It could be one of two cases:
    # - the file is just created and there is no user typed content yet
    # - a new content has been modified
    isPython = isPythonFile(fName)

    if editor.explicitUserEncoding:
        # The user specifically set an encoding for a new buffer
        # It is impossible to set an invalid encoding
        if isPython:
            encFromText = getCodingFromText(editor.text)
            if encFromText:
                if not isValidEncoding(encFromText):
                    logging.warning(
                        "Encoding from the buffer (" + encFromText + ") is "
                        "invalid and does not match the explicitly set "
                        "encoding " + editor.explicitUserEncoding + ". The " +
                        editor.explicitUserEncoding + " is used")
                elif not areEncodingsEqual(editor.explicitUserEncoding,
                                           encFromText):
                    logging.warning(
                        "Encoding from the buffer (" + encFromText + ") does "
                        "not match the explicitly set encoding " +
                        editor.explicitUserEncoding + ". The " +
                        editor.explicitUserEncoding + " is used")
        return editor.explicitUserEncoding

    # This is rather paranoic. The user could have a file with a specific
    # encoding assigned. Then the file was deleted and the buffer is saved
    # again.
    userAssignedEncoding = getFileEncoding(fName)
    if userAssignedEncoding:
        if not isValidEncoding(userAssignedEncoding):
            logging.error(
                "User assigned encoding " + userAssignedEncoding + " is "
                "invalid. Please assign a valid one and try again.")
            return None
        if isPython:
            encFromText = getCodingFromText(editor.text)
            if encFromText:
                if not isValidEncoding(encFromText):
                    logging.warning(
                        "Encoding from the buffer (" + encFromText +
                        ") is invalid and does not match the explicitly "
                        "set encoding " + userAssignedEncoding + ". The " +
                        userAssignedEncoding + " is used")
                elif not areEncodingsEqual(userAssignedEncoding,
                                           encFromText):
                    logging.warning(
                        "Encoding from the buffer (" + encFromText + ") "
                        "does not match the explicitly set encoding " +
                        userAssignedEncoding + ". The " +
                        userAssignedEncoding + " is used")
        return userAssignedEncoding

    # Check the buffer
    if isPython:
        encFromText = getCodingFromText(editor.text)
        if encFromText:
            if not isValidEncoding(encFromText):
                logging.error(
                    "Encoding from the buffer (" + encFromText +
                    ") is invalid. Please fix the encoding in the source "
                    "or explicitly set the required one and try again.")
                return None
            return encFromText

    # Check the project default encoding
    project = GlobalData().project
    if project.isLoaded():
        projectEncoding = project.props['encoding']
        if projectEncoding:
            if not isValidEncoding(projectEncoding):
                logging.error(
                    "The prject encoding " + projectEncoding + " is invalid. "
                    "Please select a valid one in the project properties and "
                    "try again.")
                return None
            return projectEncoding

    # Check the IDE wide encoding
    ideEncoding = Settings()['encoding']
    if ideEncoding:
        if not isValidEncoding(ideEncoding):
            logging.error("The ide encoding " + ideEncoding + " is invalid. "
                          "Please set a valid one and try again.")
            return None
        return ideEncoding

    # The default one
    return DEFAULT_ENCODING


def detectExistingFileWriteEncoding(editor, fName):
    """Provides the previously opened file encoding"""
    isPython = isPythonFile(fName)

    # The file is not new and there are a few sources of the encoding:
    # - the one which was used during reading (editor.encoding)
    # - user explicitly specified
    # - encoding in the buffer
    userAssignedEncoding = getFileEncoding(fName)
    if userAssignedEncoding:
        if not isValidEncoding(userAssignedEncoding):
            logging.error(
                "User assigned encoding " + userAssignedEncoding + " is "
                "invalid. Please assign a valid one and try again.")
            return None
        if isPython:
            encFromText = getCodingFromText(editor.text)
            if encFromText:
                if not isValidEncoding(encFromText):
                    logging.warning(
                        "Encoding from the buffer (" + encFromText +
                        ") is invalid and does not match the explicitly "
                        "set encoding " + userAssignedEncoding + ". The " +
                        userAssignedEncoding + " is used")
                elif not areEncodingsEqual(userAssignedEncoding,
                                           encFromText):
                    logging.warning(
                        "Encoding from the buffer (" + encFromText + ") "
                        "does not match the explicitly set encoding " +
                        userAssignedEncoding + ". The " +
                        userAssignedEncoding + " is used")
        return userAssignedEncoding

    # Check the buffer
    if isPython:
        encFromText = getCodingFromText(editor.text)
        if encFromText:
            if not isValidEncoding(encFromText):
                logging.error(
                    "Encoding from the buffer (" + encFromText +
                    ") is invalid. Please fix the encoding in the source "
                    "or explicitly set the required one and try again.")
                return None
            return encFromText

    # Here: no explicitly specified encoding, no encoding in the buffer,
    #       then use the encoding the file was read with
    return editor.encoding


def detectWriteEncoding(editor, fName):
    """Detects the write encoding for a buffer"""
    # If editor.encoding is None => the file has never been saved
    # At the same time fName may exist, i.e. a new file overwrites the existing
    # one.
    if os.path.isabs(fName) and os.path.exists(fName) and \
        editor.encoding is not None:
        return detectExistingFileWriteEncoding(editor, fName)
    return detectNewFileWriteEncoding(editor, fName)


def writeEncodedFile(fName, content, encoding):
    """Writes into a file taking care of encoding"""
    normEnc = getNormalizedEncoding(encoding)
    try:
        if normEnc.startswith('bom_'):
            enc = normEnc[4:]
            if enc == 'utf_8':
                encContent = BOM_UTF8 + content.encode(enc)
            elif enc == 'utf_16':
                encContent = BOM_UTF16 + content.encode(enc)
            else:
                encContent = BOM_UTF32 + content.encode(enc)
        else:
            encContent = content.encode(normEnc)
    except (UnicodeError, LookupError) as exc:
        raise Exception('Error encoding the buffer content with ' + encoding +
                        ': ' + str(exc))

    try:
        with open(fName, 'wb') as diskfile:
            diskfile.write(encContent)
    except Exception as exc:
        raise Exception('Error writing encoded buffer content into ' +
                        fName + ': ' + str(exc))


def decodeURLContent(content):
    """Decodes the content read from a URL"""
    project = GlobalData().project
    if project.isLoaded():
        projectEncoding = project.props['encoding']
        if projectEncoding:
            if not isValidEncoding(projectEncoding):
                raise Exception(
                    "The prject encoding " + projectEncoding + " is invalid. "
                    "Please select a valid one in the project properties and "
                    "try again.")
            return content.decode(
                encodings.normalize_encoding(projectEncoding))

    # Check the IDE wide encoding
    ideEncoding = Settings()['encoding']
    if ideEncoding:
        if not isValidEncoding(ideEncoding):
            raise Exception("The ide encoding " + ideEncoding + " is invalid. "
                            "Please set a valid one and try again.")
        return content.decode(encodings.normalize_encoding(ideEncoding))

    # The default one
    return content.decode(DEFAULT_ENCODING)
