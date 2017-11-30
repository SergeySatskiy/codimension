# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""CML utilities"""

from sys import maxsize
from cdmcfparser import (IF_FRAGMENT, FOR_FRAGMENT, WHILE_FRAGMENT,
                         TRY_FRAGMENT, CONTROL_FLOW_FRAGMENT, CLASS_FRAGMENT,
                         FUNCTION_FRAGMENT)
from utils.colorfont import buildColor


def escapeCMLTextValue(src):
    """Escapes the string before inserting it to the code (CML value)"""
    dst = ''
    for char in src:
        if char == '\n':
            dst += '\\n'
        elif char in ('"', '\\'):
            dst += '\\' + char
        else:
            dst += char
    return dst


def unescapeCMLTextValue(src):
    """Removes escaping from the value received from the code"""
    dst = ''
    lastIndex = len(src) - 1
    index = 0
    while index <= lastIndex:
        if src[index] == '\\' and index < lastIndex:
            if src[index + 1] == '\\':
                dst += '\\'
                index += 1
            elif src[index + 1] == 'n':
                dst += '\n'
                index += 1
            elif src[index + 1] == '"':
                dst += '"'
                index += 1
            else:
                dst += '\\'     # forgiving the other escape characters
        else:
            dst += src[index]
        index += 1
    return dst


class CMLCommentBase:

    """Base class for all the CML comments"""

    def __init__(self, ref=None):
        self.ref = ref

    def validateRecordType(self, code):
        """Validates the record type"""
        if self.ref.recordType != code:
            raise Exception("Invalid CML comment type. "
                            "Expected: '" + code + "'. Received: '" +
                            self.ref.recordType + "'.")

    def __isSideComment(self, editor):
        """True if it is a side comment"""
        # The only first part needs to be checked
        firstPart = self.ref.parts[0]
        # Editor has 0-based lines
        leftStripped = editor.lines[firstPart.beginLine - 1].lstrip()
        return not leftStripped.startswith(firstPart.getContent())

    def removeFromText(self, editor):
        """Removes the comment from the code"""
        # Note: it is supposed that the 'with editor:' is done outside.
        #       This is because the required changes could be done for more
        #       than one place.
        if editor is None:
            return

        isSideComment = self.__isSideComment(editor)

        oldLine, oldPos = editor.cursorPosition
        line = self.ref.endLine
        while line >= self.ref.beginLine:
            if isSideComment:
                raise Exception("Side CML comments removal "
                                "has not been implemented yet")
            else:
                # Editor has 0-based lines
                del editor.lines[line - 1]
                if oldLine >= line - 1:
                    oldLine -= 1
            line -= 1

        editor.cursorPosition = oldLine, oldPos


class CMLsw(CMLCommentBase):

    """Covers the 'if' statement CML SW (switch branches) comments"""

    CODE = "sw"

    def __init__(self, ref):
        CMLCommentBase.__init__(self, ref)
        self.validate()

    def validate(self):
        """Validates the CML comment"""
        self.validateRecordType(CMLsw.CODE)
        CMLVersion.validate(self.ref)

    @staticmethod
    def description():
        """Provides the CML comment description"""
        return "The '" + CMLsw.CODE + \
               "' comment is used for 'if' and 'elif' statements " \
               "to switch default branch location i.e. to have " \
               "the 'No' branch at the right.\n" \
               "Supported properties: none\n\n" \
               "Example:\n" \
               "# cml 1 " + CMLsw.CODE

    @staticmethod
    def generate(pos=1):
        """Generates a complete line to be inserted"""
        return " " * (pos - 1) + "# cml 1 sw"


class CMLcc(CMLCommentBase):

    """Covers 'Custom Colors' spec for most of the items"""

    CODE = "cc"

    def __init__(self, ref):
        CMLCommentBase.__init__(self, ref)
        self.bgColor = None      # background color
        self.fgColor = None      # foreground color
        self.border = None
        self.validate()

    def validate(self):
        """Validates the CML comment"""
        self.validateRecordType(CMLcc.CODE)
        CMLVersion.validate(self.ref)

        if "background" in self.ref.properties:
            self.bgColor = buildColor(self.ref.properties["background"])
        if "foreground" in self.ref.properties:
            self.fgColor = buildColor(self.ref.properties["foreground"])
        if "border" in self.ref.properties:
            self.border = buildColor(self.ref.properties["border"])

        if self.bgColor is None:
            if self.fgColor is None:
                if self.border is None:
                    raise Exception("The '" + CMLcc.CODE +
                                    "' CML comment does not supply neither "
                                    "background nor foreground color nor "
                                    "border color")

    @staticmethod
    def description():
        """Provides the CML comment description"""
        return "The '" + CMLcc.CODE + \
               "' comment is used for custom colors of most of " \
               "the graphics items.\n" \
               "Supported properties:\n" \
               "- 'background': background color for the item\n" \
               "- 'foreground': foreground color for the item\n" \
               "- 'border': border color for the item\n" \
               "Color spec formats:\n" \
               "- '#hhhhhh': hexadecimal RGB\n" \
               "- '#hhhhhhhh': hexadecimal RGB + alpha\n" \
               "- 'ddd,ddd,ddd': decimal RGB\n" \
               "- 'ddd,ddd,ddd,ddd': decimal RGB + alpha\n\n" \
               "Example:\n" \
               "# cml 1 " + CMLcc.CODE + \
               " background=#f6f4e4 foreground=#000000 border=#ffffff"

    @staticmethod
    def generate(background, foreground, border, pos=1):
        """Generates a complete line to be inserted"""
        res = " " * (pos - 1) + "# cml 1 cc"
        if background is not None:
            bgColor = background.name()
            bgalpha = background.alpha()
            if bgalpha != 255:
                bgColor += hex(bgalpha)[2:]
            res += " background=" + bgColor
        if foreground is not None:
            fgColor = foreground.name()
            fgalpha = foreground.alpha()
            if fgalpha != 255:
                fgColor += hex(fgalpha)[2:]
            res += " foreground=" + fgColor
        if border is not None:
            brd = border.name()
            brdalpha = border.alpha()
            if brdalpha != 255:
                brd += hex(brdalpha)[2:]
            res += " border=" + brd
        return res


class CMLrt(CMLCommentBase):

    """Covers 'Replace text' comment"""

    CODE = "rt"

    def __init__(self, ref):
        CMLCommentBase.__init__(self, ref)
        self.text = None
        self.validate()

    def validate(self):
        """Validates the CML rt comment"""
        self.validateRecordType(CMLrt.CODE)
        CMLVersion.validate(self.ref)

        if "text" in self.ref.properties:
            self.text = self.ref.properties["text"]

        if self.text is None:
            raise Exception("The '" + CMLrt.CODE +
                            "' CML comment does not supply text")

    @staticmethod
    def description():
        """Provides the CML comment description"""
        return "The '" + CMLrt.CODE + \
               "' comment is used for replacing the text of most of " \
               "the graphics items.\n" \
               "Supported properties:\n" \
               "- 'text': text to be shown instead of the real code\n\n" \
               "Example:\n" \
               "# cml 1 " + CMLrt.CODE + " text=\"Reset the dictionary\""

    @staticmethod
    def generate(txt, pos=1):
        """Generates a complete line to be inserted"""
        res = " " * (pos - 1) + "# cml 1 rt"
        if txt is not None:
            res += " text=\"" + escapeCMLTextValue(txt) + "\""
        return res

    def getText(self):
        """Provides unescaped text"""
        if self.text is None:
            return None
        return unescapeCMLTextValue(self.text)


class CMLVersion:

    """Describes the current CML version"""

    VERSION = 1     # Current CML version
    COMMENT_TYPES = {CMLsw.CODE: CMLsw,
                     CMLcc.CODE: CMLcc,
                     CMLrt.CODE: CMLrt}

    def __init__(self):
        pass

    @staticmethod
    def validate(cmlComment):
        """Valides the vestion"""
        if cmlComment.version > CMLVersion.VERSION:
            raise Exception("The CML comment version " +
                            str(cmlComment.version) +
                            " is not supported. Max supported version is " +
                            str(CMLVersion.VERSION))

    @staticmethod
    def find(cmlComments, cmlType):
        """Finds the CML comment"""
        for comment in cmlComments:
            if hasattr(comment, "CODE"):
                if comment.CODE == cmlType.CODE:
                    return comment
        return None

    @staticmethod
    def getType(cmlComment):
        """Provides the CML comment type"""
        try:
            return CMLVersion.COMMENT_TYPES[cmlComment.recordType]
        except KeyError:
            return None

    @staticmethod
    def validateCMLComments(item):
        """Validates recursively all the CML items in the control flow.

           Replaces the recognized CML comments from the
           module with their higher level counterparts.
           Returns back a list of warnings.
        """
        warnings = []
        if hasattr(item, "leadingCMLComments"):
            warnings += CMLVersion.validateCMLList(item.leadingCMLComments)

        # Some items are containers
        if item.kind == IF_FRAGMENT:
            for part in item.parts:
                warnings += CMLVersion.validateCMLComments(part)
        elif item.kind in [FOR_FRAGMENT, WHILE_FRAGMENT]:
            if item.elsePart:
                warnings += CMLVersion.validateCMLComments(item.elsePart)
        elif item.kind == TRY_FRAGMENT:
            if item.elsePart:
                warnings += CMLVersion.validateCMLComments(item.elsePart)
            if item.finallyPart:
                warnings += CMLVersion.validateCMLComments(item.finallyPart)
            for part in item.exceptParts:
                warnings += CMLVersion.validateCMLComments(part)

        if item.kind in [CONTROL_FLOW_FRAGMENT,
                         CLASS_FRAGMENT, FUNCTION_FRAGMENT]:
            if item.docstring:
                warnings += CMLVersion.validateCMLList(
                    item.docstring.leadingCMLComments)
                warnings += CMLVersion.validateCMLList(
                    item.docstring.sideCMLComments)

        if hasattr(item, "sideCMLComments"):
            warnings += CMLVersion.validateCMLList(item.sideCMLComments)

        if hasattr(item, "suite"):
            for nestedItem in item.suite:
                warnings += CMLVersion.validateCMLComments(nestedItem)
        return warnings

    @staticmethod
    def validateCMLList(comments):
        """Validates the CML comments in the provided list (internal use)"""
        warnings = []
        if comments:
            count = len(comments)
            for index in range(count):
                cmlComment = comments[index]
                cmlType = CMLVersion.getType(cmlComment)
                if cmlType:
                    try:
                        highLevel = cmlType(cmlComment)
                        comments[index] = highLevel
                    except Exception as exc:
                        line = cmlComment.parts[0].beginLine
                        pos = cmlComment.parts[0].beginPos
                        warnings.append((line, pos,
                                         "Invalid CML comment: " + str(exc)))
                else:
                    line = cmlComment.parts[0].beginLine
                    pos = cmlComment.parts[0].beginPos
                    warnings.append((line, pos,
                                     "CML comment type '" +
                                     cmlComment.recordType +
                                     "' is not supported"))
        return warnings

    @staticmethod
    def getFirstLine(comments):
        """Provides the first line of the comment"""
        # The list may contain raw comments and high level comments
        line = maxsize
        if comments:
            if hasattr(comments[0], "ref"):
                # High level CML comment
                return comments[0].ref.parts[0].beginLine
            # Raw CML comment
            if comments[0].parts:
                return comments[0].parts[0].beginLine
        return line
