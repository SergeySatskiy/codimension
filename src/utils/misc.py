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

" Miscellaneuos utility functions "

import os.path, re
from globals import GlobalData


# File name of the template for any new file.
# The file is searched nearby the project file.
templateFileName = "template.py"


def splitThousands( value, sep = "'" ):
    " provides thousands separated value "
    if len( value ) <= 3:
        return value
    return splitThousands( value[ : -3 ], sep ) + sep + value[ -3 : ]

def getNewFileTemplate():
    " Searches for the template file and fills fields in it "

    projectFile = GlobalData().project.fileName
    if projectFile == "":
        return ""

    # Project is currently loaded - search for the template file
    templateFile = os.path.dirname( projectFile ) + os.path.sep + \
                   templateFileName
    if not os.path.exists( templateFile ):
        return ""

    # read the file content
    content = []
    f = open( templateFile, "r" )
    for line in f:
        content.append( line.rstrip() )
    f.close()

    # substitute the fields
    project = GlobalData().project
    subs = [ ( re.compile( re.escape( '$creationdate' ), re.I ),
               project.creationDate ),
             ( re.compile( re.escape( '$author' ), re.I ),
               project.author ),
             ( re.compile( re.escape( '$license' ), re.I ),
               project.license ),
             ( re.compile( re.escape( '$copyright' ), re.I ),
               project.copyright ),
             ( re.compile( re.escape( '$version' ), re.I ),
               project.version ),
             ( re.compile( re.escape( '$email' ), re.I ),
               project.email ) ]

    # description could be multilined so it is a different story
    descriptionRegexp = re.compile( re.escape( '$description' ), re.I )
    description = project.description.split( '\n' )

    result = []
    for line in content:
        for key, value in subs:
            line = re.sub( key, value, line )
        # description part
        match = re.search( descriptionRegexp, line )
        if match is not None:
            # description is in the line
            leadingPart = line[ : match.start() ]
            trailingPart = line[ match.end() : ]
            for dline in description:
                result.append( leadingPart + dline + trailingPart )
        else:
            result.append( line )

    return "\n".join( result )

