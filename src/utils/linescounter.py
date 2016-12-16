#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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


"""Counts lines in python code"""

import sys
import os.path
from optparse import OptionParser


class LinesCounter:

    """Holds various line information, see the members comments"""

    def __init__(self):
        self.__reset()

    def __reset(self):
        " Resets all the values "
        self.files = 0          # Total number of analyzed files
        self.filesSize = 0      # Total size of all files in bytes
        self.codeLines = 0      # Number of non-empty non-comment lines
        self.emptyLines = 0     # Number of empty lines
        self.commentLines = 0   # Number of lines which start from the hash sign
        self.classes = 0        # Number of classes

    def __processFile(self, path):
        """Accumulates lines from a single file"""
        afile = open(path)
        for line in afile:
            self.__processLine(line)
        afile.close()

    def __processLine(self, line):
        """Process a single line"""
        line = line.strip()
        if line == "":
            self.emptyLines += 1
            return
        if line.startswith('#'):
            self.commentLines += 1
            return
        if line.startswith('class '):
            self.classes += 1
        self.codeLines += 1

    def __processDir(self, path, extensions):
        """Accumulates lines from all files in the given dir recursively"""
        for item in os.listdir(path):
            if item in ('.svn', '.cvs'):
                continue
            if os.path.isdir(path + os.path.sep + item):
                self.__processDir(path + os.path.sep + item, extensions)
                continue
            for ext in extensions:
                if item.endswith(ext):
                    self.files += 1
                    self.__processFile(path + os.path.sep + item)
                    self.filesSize += os.path.getsize(path + os.path.sep + item)
                continue

    def getLines(self, path, extensions=('.py', '.py3', '.pyw')):
        """Accumulates lines for a file or directory"""
        if not os.path.exists(path):
            raise Exception("Lines counter cannot open " + path)

        self.__reset()

        if os.path.isfile(path):
            for ext in extensions:
                if path.endswith(ext):
                    # It's OK
                    self.__processFile(path)
                    self.files = 1
                    self.filesSize = os.path.getsize(path)
                    return
            raise Exception("Lines counter detected inconsistency. "
                            "The file " + path + " does not have expected "
                            "extension (" + ", ".join(extensions) + ")")

        # It's a directory
        if not path.endswith(os.path.sep):
            path += os.path.sep

        self.__processDir(path, extensions)

    def getLinesInBuffer(self, editor):
        """Counts lines in the given Scintilla buffer"""
        self.__reset()
        txt = editor.text()
        self.filesSize = len(txt)
        for line in txt.split('\n'):
            self.__processLine(line)


# The script execution entry point
if __name__ == "__main__":

    parser = OptionParser(
        """
        %prog  <dir name>
        Counts lines in python code
        """)

    options, args = parser.parse_args()

    if len(args) != 1:
        print("One arguments expected", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args[0]):
        print("Path " + args[0] + " does not exist", file=sys.stderr)
        sys.exit(1)

    counter = LinesCounter()
    counter.getLines(args[0])

    totalLines = counter.codeLines + counter.commentLines + counter.emptyLines

    print("Lines info for " + args[0] + ":")
    print("Files analysed:    " + str(counter.files))
    print("Total size:        " + str(counter.filesSize) + " bytes\n")
    print("Classes:           " + str(counter.classes))
    print("Code lines:        " + str(counter.codeLines))
    print("Comment lines:     " + str(counter.commentLines))
    print("Empty lines:       " + str(counter.emptyLines))
    print("Total lines:       " + str(totalLines))

    sys.exit(0)
