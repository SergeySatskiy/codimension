#!/usr/bin/python
#
# File:   clean.py
#
# Author: Sergey Satskiy
#
# Date:   Apr 13, 2010
#
# $Id$
#

""" Deletes the compiled python files """

import sys, os.path
from optparse  import OptionParser


ext = [ '.pyc', '.out', '.pyo', '.o' ]

files = 0


def mainClean():
    """ Counter main function """

    parser = OptionParser(
    """
    %prog  <dir name>
    Deletes the compiled python files
    """ )

    options, args = parser.parse_args()

    if len( args ) != 1:
        raise Exception( "One argument expected" )


    if not os.path.exists( args[0] ) or \
       not os.path.isdir( args[0] ):
        raise Exception( "A directory name is expected" )

    processDir( args[0] )

    print "Project directory: " + args[0]
    print "Deleted files:    " + str( files )

    return 0


def processDir( path ):
    " Recursively deletes files in the given directory "

    global files
    global totalSize

    for item in os.listdir( path ):
        if os.path.isdir( path + '/' + item ):
            processDir( path + '/' + item )
            continue
        for ex in ext:
            if item.endswith( ex ):
                files += 1
                os.remove( path + '/' + item )
            continue


# The script execution entry point
if __name__ == "__main__":
    returnCode = 1
    try:
        returnCode = mainClean()
    except Exception, exception:
        print >> sys.stderr, str( exception )
    sys.exit( returnCode )

