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

"""dot output (plain) parser"""

import os
import os.path
from utils.fileutils import getFileContent, saveToFile, makeTempFile
from utils.run import checkOutput


def splitWithQuotasRespect(line):
    """Splits the space separated values and respects quoted values"""
    def skipSpaces(line, startPos):
        """Provides index of first non-space char"""
        while startPos < len(line):
            if line[startPos] != ' ':
                return startPos
            startPos += 1
        return startPos

    def skipTillSpace(line, startPos):
        """Provides index of first space char"""
        while startPos < len(line):
            if line[startPos] == ' ':
                return startPos
            startPos += 1
        return startPos

    def skipTillClosedQuote(line, startPos):
        """Provides index of a closing quote"""
        while startPos < len(line):
            if line[startPos] == '"':
                if line[startPos - 1] == '\\':
                    startPos += 1
                    continue
                return startPos
            startPos += 1
        return startPos

    result = []

    index = 0
    while index < len(line):
        # skip spaces if so
        index = skipSpaces(line, index)
        if index >= len(line):
            return result

        # First symbol is not a space so it is a beginning of a value.
        startIndex = index
        if line[startIndex] == '"':
            # Beginning of a quoted value
            nextIndex = skipTillClosedQuote(line, startIndex + 1)
            result.append(line[startIndex + 1:nextIndex])
            index = nextIndex + 1
        else:
            nextIndex = skipTillSpace(line, startIndex)
            result.append(line[startIndex:nextIndex])
            index = nextIndex
    return result


class Graph():

    """Holds a description of a single graph"""

    def __init__(self):
        self.scale = 0.0
        self.width = 0.0
        self.height = 0.0

        self.vSpace = 10.0
        self.hSpace = 10.0

        self.edges = []
        self.nodes = []

    def normalize(self, scaleX, scaleY):
        """normalizes all the measures"""
        self.width = self.width * self.scale * scaleX
        self.height = self.height * self.scale * scaleY

        for edge in self.edges:
            edge.normalize(self, scaleX, scaleY)
        for node in self.nodes:
            node.normalize(self, scaleX, scaleY)

        # increase the size to have borders around
        self.width = self.width + 2.0 * self.hSpace
        self.height = self.height + 2.0 * self.vSpace

    def initFromLine(self, line):
        """Parses a line and initializes the values"""
        # graph scale width height
        # graph 1.000 57.306 10.833

        parts = line.strip().split()
        if len(parts) != 4:
            raise Exception("Unexpected number of parts in 'graph' statement")

        self.scale = float(parts[1].strip())
        self.width = float(parts[2].strip())
        self.height = float(parts[3].strip())


class Edge():

    """Holds a single graph edge description"""

    def __init__(self):
        self.tail  = ""
        self.head  = ""
        self.points = []

        self.label = ""
        self.labelX = 0.0
        self.labelY = 0.0

        self.style = ""
        self.color = ""

    def normalize(self, graph, scaleX, scaleY):
        """Scales to the screen coordinates"""
        self.labelX = self.labelX * graph.scale * scaleX + graph.hSpace
        self.labelY = graph.height - self.labelY * graph.scale * scaleY + \
                      graph.vSpace

        index = 0
        while index < len(self.points):
            # x
            self.points[index][0] = self.points[index][0] * graph.scale * scaleX
            self.points[index][0] = self.points[index][0] + graph.hSpace
            # y
            self.points[index][1] = self.points[index][1] * graph.scale * scaleY
            self.points[index][1] = graph.height - self.points[index][1] + \
                                    graph.vSpace
            index = index + 1

    def initFromLine(self, line):
        """Parses a line and initializes the values"""
        # edge tail head n x1 y1 .. xn yn [label xl yl] style color
        # edge "obj1" "obj2"
        #  4 29.806 10.389 29.208 10.236 28.375 10.000 27.722 9.833 solid black

        parts = splitWithQuotasRespect(line.strip())

        if len(parts) < 8:
            raise Exception("Unexpected number of parts in 'edge' "
                            "statement. Line: " + line)

        self.tail = parts[1]
        self.head = parts[2]

        numberOfPoints = int(parts[3])

        if len(parts) < (numberOfPoints * 2 + 5):
            raise Exception("Unexpected number of parts in 'edge' "
                            "statement. Line: " + line)

        point = 0
        while point < numberOfPoints:
            self.points.append([float(parts[point * 2 + 4]),
                                float(parts[point * 2 + 4 + 1])])
            point += 1

        # It is possible that there are spaces in the label
        self.label = ""
        self.labelX = 0.0
        self.labelY = 0.0
        self.style = ""
        self.color = ""

        # Strip the points description
        parts = parts[numberOfPoints * 2 + 4:]
        if len(parts) == 2:
            # There is no label
            self.style = parts[0]
            self.color = parts[1]
        else:
            self.label = parts[0]
            self.labelX = float(parts[1])
            self.labelY = float(parts[2])
            self.style = parts[3]
            self.color = parts[4]


class Node:

    """Holds a single node description"""

    def __init__(self):
        self.name = ""
        self.posX = 0.0
        self.posY = 0.0
        self.width = 0.0
        self.height = 0.0
        self.label = ""
        self.style = ""
        self.shape = ""
        self.color = ""
        self.fillcolor = ""

    def normalize(self, graph, scaleX, scaleY):
        """Scales to the screen coordinates"""
        self.posX = self.posX * graph.scale * scaleX + graph.hSpace
        self.posY = graph.height - self.posY * graph.scale * scaleY + \
                    graph.vSpace
        self.width = self.width * graph.scale * scaleX
        self.height = self.height * graph.scale * scaleY

    def initFromLine(self, line):
        """Parses a line and initializes the values"""
        # node name x y width height label style shape color fillcolor
        # node "/usr/local/vim-7.1/bin/vim"  30.542 10.583 2.388 0.500
        #      "/usr/local/vim-7.1/bin/vim" solid ellipse black lightgrey

        parts = splitWithQuotasRespect(line.strip())
        if len(parts) < 11:
            raise Exception("Unexpected number of parts in 'node' "
                            "statement. Line: " + line)

        self.name = parts[1]
        self.posX = float(parts[2].strip())
        self.posY = float(parts[3].strip())
        self.width = float(parts[4].strip())
        self.height = float(parts[5].strip())
        self.label = parts[6]
        self.style = parts[7].strip()
        self.shape = parts[8].strip()
        self.color = parts[9].strip()
        self.fillcolor = parts[10].strip()


def getGraphFromPlainDotData(content):
    """Parses data and builds a normalized graph"""
    graph = Graph()
    expectContinue = False
    combinedLine = ""
    for line in content.split('\n'):
        line = line.strip()
        if line == "":
            continue
        if line.endswith('\\'):
            combinedLine += line[:-1]
            expectContinue = True
            continue
        if expectContinue:
            expectContinue = False
        combinedLine += line

        if combinedLine.startswith("graph"):
            graph.initFromLine(combinedLine)
            combinedLine = ""
            continue
        if combinedLine.startswith("node"):
            node = Node()
            node.initFromLine(combinedLine)
            graph.nodes.append(node)
            combinedLine = ""
            continue
        if combinedLine.startswith("edge"):
            edge = Edge()
            edge.initFromLine(combinedLine)
            graph.edges.append(edge)
            combinedLine = ""
            continue
        if combinedLine.startswith("stop"):
            break

        raise Exception("Unexpected plain dot line: " + combinedLine)
    return graph


def getGraphFromPlainDotFile(fName):
    """Parses file and builds a normalized graph"""
    if not os.path.exists(fName):
        raise Exception("Cannot open " + fName)

    # Not optimal however I don't care at the moment.
    # In most of the cases this will be an interactive call.
    return getGraphFromPlainDotData(getFileContent(fName))


def getGraphFromDescrptionFile(fName):
    """Runs dot and then parses and builds normalized graph"""
    return getGraphFromPlainDotData(checkOutput(["dot", "-Tplain", fName]))


def getGraphFromDescriptionData(content):
    """Runs dot and then parses and builds normalized graph"""
    tempFileName = makeTempFile()
    saveToFile(tempFileName, content)

    try:
        graph = getGraphFromDescrptionFile(tempFileName)
    finally:
        os.unlink(tempFileName)
    return graph
