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

" dot output (plain) parser "

import os, os.path, tempfile
from utils.misc import safeRun


class Graph():
    " Holds a description of a single graph "

    def __init__( self ):
        self.scale  = 0.0
        self.width  = 0.0
        self.height = 0.0

        self.vSpace = 10.0
        self.hSpace = 10.0

        self.edges = []
        self.nodes = []
        return

    def normalize( self ):
        " normalizes all the measures "

        self.scale = self.scale * 72 # points
        self.width = self.width * self.scale
        self.height = self.height * self.scale

        for edge in self.edges:
            edge.normalize( self )
        for node in self.nodes:
            node.normalize( self )

        # increase the size to have borders around
        self.width = self.width + 2.0 * self.hSpace
        self.height = self.height + 2.0 * self.vSpace
        return

    def initFromLine( self, line ):
        " Parses a line and initializes the values "

        # graph scale width height
        # graph 1.000 57.306 10.833

        parts = line.strip().split()
        if len( parts ) != 4:
            raise Exception( "Unexpected number of parts in 'graph' statement" )

        self.scale = float( parts[1].strip() )
        self.width = float( parts[2].strip() )
        self.height = float( parts[3].strip() )
        return


class Edge():
    " Holds a single graph edge description "

    def __init__( self ):
        self.tail   = ""
        self.head   = ""
        self.points = []

        self.label  = ""
        self.labelX = 0.0
        self.labelY = 0.0

        self.style  = ""
        self.color  = ""
        return

    def normalize( self, graph ):
        """ Scales to the screen coordinates """

        self.labelX = self.labelX * graph.scale + graph.hSpace
        self.labelY = self.labelY * graph.scale + graph.vSpace

        index = 0
        while index < len( self.points ):
            # x
            self.points[index][0] = self.points[index][0] * graph.scale + \
                                    graph.hSpace
            # y
            self.points[index][1] = self.points[index][1] * graph.scale
            self.points[index][1] = graph.height - self.points[index][1] + \
                                    graph.vSpace
            index = index + 1
        return

    def initFromLine( self, line ):
        " Parses a line and initializes the values "

        # edge tail head n x1 y1 .. xn yn [label xl yl] style color
        # edge "obj1" "obj2"
        #  4 29.806 10.389 29.208 10.236 28.375 10.000 27.722 9.833 solid black

        parts = line.strip().split()

        if len( parts ) < 8:
            raise Exception( "Unexpected number of parts in 'edge' statement" )

        self.tail = parts[1]
        if self.tail.startswith( '"' ) or self.tail.startswith( "'" ):
            self.tail = self.tail[ 1: ]
        if self.tail.endswith( '"' ) or self.tail.endswith( "'" ):
            self.tail = self.tail[ :-1 ]

        self.head = parts[2]
        if self.head.startswith( '"' ) or self.head.startswith( "'" ):
            self.head = self.head[ 1: ]
        if self.head.endswith( '"' ) or self.head.endswith( "'" ):
            self.head = self.head[ :-1 ]

        numberOfPoints = int( parts[3].strip() )

        if len( parts ) < (numberOfPoints * 2 + 5):
            raise Exception( "Unexpected number of parts in 'edge' statement" )

        point = 0
        while point < numberOfPoints:
            self.points.append( [ float( parts[ point * 2 + 4 ] ),
                                  float( parts[ point * 2 + 4 + 1 ] ) ] )
            point += 1

        # It is possible that there are spaces in the label
        self.label  = ""
        self.labelX = 0.0
        self.labelY = 0.0
        self.style  = ""
        self.color  = ""

        if parts[ numberOfPoints * 2 + 4 ][0] == '"' or \
           parts[ numberOfPoints * 2 + 4 ][0] == "'":
            # This is the label
            self.label = line.strip().split( '"' )[5]
            tailParts = line.strip().split( '"' )[6].strip().split()
            if len( tailParts ) != 4:
                raise Exception( "Unexpected number of parts " \
                                 "in 'edge' statement" )
            self.labelX = float( tailParts[0].strip() )
            self.labelY = float( tailParts[1].strip() )
            self.style = tailParts[2].strip()
            self.color = tailParts[3].strip()
        else:
            # There is no label
            if len( parts ) != (numberOfPoints * 2 + 6):
                raise Exception( "Unexpected number of parts " \
                                 "in 'edge' statement" )
            self.style = parts[ numberOfPoints * 2 + 4 ].strip()
            self.color = parts[ numberOfPoints * 2 + 5 ].strip()

        return


class Node:
    """ Holds a single node description """

    def __init__( self ):
        self.name      = ""
        self.posX      = 0.0
        self.posY      = 0.0
        self.width     = 0.0
        self.height    = 0.0
        self.label     = ""
        self.style     = ""
        self.shape     = ""
        self.color     = ""
        self.fillcolor = ""
        return

    def normalize( self, graph ):
        """ Scales to the screen coordinates """

        self.posX = self.posX * graph.scale + graph.hSpace
        self.posY = graph.height - self.posY * graph.scale + graph.vSpace
        self.width = self.width * graph.scale
        self.height = self.height * graph.scale
        return

    def initFromLine( self, line ):
        " Parses a line and initializes the values "

        # node name x y width height label style shape color fillcolor
        # node "/usr/local/vim-7.1/bin/vim"  30.542 10.583 2.388 0.500
        #      "/usr/local/vim-7.1/bin/vim" solid ellipse black lightgrey

        parts = line.strip().split()
        if len( parts ) != 11:
            raise Exception( "Unexpected number of parts in 'node' statement" )

        self.name = parts[1]
        if self.name.startswith( '"' ) or self.name.startswith( "'" ):
            self.name = self.name[ 1: ]
        if self.name.endswith( '"' ) or self.name.endswith( "'" ):
            self.name = self.name[ :-1 ]

        self.label = parts[6]
        if self.label.startswith( '"' ) or self.label.startswith( "'" ):
            self.label = self.label[ 1: ]
        if self.label.endswith( '"' ) or self.label.endswith( "'" ):
            self.label = self.label[ :-1 ]

        self.posX      = float( parts[2].strip() )
        self.posY      = float( parts[3].strip() )
        self.width     = float( parts[4].strip() )
        self.height    = float( parts[5].strip() )
        self.style     = parts[7].strip()
        self.shape     = parts[8].strip()
        self.color     = parts[9].strip()
        self.fillcolor = parts[10].strip()
        return


def getGraphFromPlainDotData( content ):
    " Parses data and builds a normalized graph "
    graph = Graph()
    for line in content.split( '\n' ):
        line = line.strip()
        if line == "":
            continue
        if line.startswith( "graph" ):
            graph.initFromLine( line )
            continue
        if line.startswith( "node" ):
            node = Node()
            node.initFromLine( line )
            graph.nodes.append( node )
            continue
        if line.startswith( "edge" ):
            edge = Edge()
            edge.initFromLine( line )
            graph.edges.append( edge )
            continue
        if line.startswith( "stop" ):
            break

        raise Exception( "Unexpected plain dot line: " + line )

    graph.normalize()
    return graph


def getGraphFromPlainDotFile( fName ):
    " Parses file and builds a normalized graph "
    if not os.path.exists( fName ):
        raise Exception( "Cannot open " + fName )

    # Not optimal however I don't care at the moment.
    # In most of the cases this will be an interactive call.
    f = open( fName )
    content = f.read()
    f.close()
    return getGraphFromPlainDotData( content )


def getGraphFromDescrptionFile( fName ):
    " Runs dot and then parses and builds normalized graph "
    return getGraphFromPlainDotData( safeRun( [ "dot", "-Tplain", fName ] ) )

def getGraphFromDescriptionData( content ):
    " Runs dot and then parses and builds normalized graph "
    graphtmp = tempfile.mkstemp()
    os.write( graphtmp[ 0 ], content )
    os.close( graphtmp[ 0 ] )

    try:
        graph = getGraphFromDescrptionFile( graphtmp[ 1 ] )
    except:
        os.unlink( graphtmp[ 1 ] )
        raise

    os.unlink( graphtmp[ 1 ] )
    return graph

