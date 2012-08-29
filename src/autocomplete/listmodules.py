#!/usr/bin/python
# $Id$
#
# Locate all standard modules available in this build.
#
# This script is designed to run on Python 1.5.2 and newer.
#
# Written by Fredrik Lundh, January 2005
# Adopted for codimension by Sergey Satskiy, 2011
#

" Routines to get a list of modules; sys and for a dir "

import imp, sys, os, re
from os.path import isfile, basename, splitext, realpath, isdir, \
                    sep, islink, isabs, dirname, normpath
from os import listdir, getcwd, readlink

# known test packages
TEST_PACKAGES = "test.", "bsddb.test.", "distutils.tests."

__suffixes = imp.get_suffixes()

def __getSuffix( fileName ):
    " Provides suffix info for a file name "
    for suffix in __suffixes:
        if fileName[ -len( suffix[ 0 ] ) : ] == suffix[ 0 ]:
            return suffix
    return None


def getSysModules():
    " Provides a dictionary of system modules. The pwd dir is excluded. "

    paths = __getSysPathExceptCurrent()

    modules = {}
    for modName in sys.builtin_module_names:
        if modName not in [ '__builtin__', '__main__' ]:
            modules[ modName ] = None

    # The os.path depends on the platform, so I insert it here as an exception
    modules[ "os.path" ] = None

    for path in paths:
        modules.update( getModules( path ) )

    return modules


class DevNull:
    " Stderr supresser "
    def write( self, data ):
        " Supresses everything what is written into a stream "
        pass

def __isTestModule( modName ):
    " Returns True if it is a test module "
    for modToDel in TEST_PACKAGES:
        if modName[ : len( modToDel ) ] == modToDel:
            return True
    return False


__regexpr = re.compile("(?i)[a-z_]\w*$")

def getModules( path ):
    """ Provides modules in a given directory.
        It expects absolute real path. Otherwise it is not guaranteed it
        works all right. """

    oldStderr = sys.stderr
    sys.stderr = DevNull()
    modules = {}
    for fName in listdir( path ):
        fName = path + sep + fName
        if isfile( fName ):
            modName, e = splitext( fName )
            suffix = __getSuffix( fName )
            if not suffix:
                continue
            modName = basename( modName )
            if modName == "__init__":
                continue
            if __regexpr.match( modName ):
                if suffix[ 2 ] == imp.C_EXTENSION:
                    # check that this extension can be imported
                    try:
                        __import__( modName )
                    except:
                        # There could be different errors,
                        # so to be on the safe side all are supressed
                        continue
                if not __isTestModule( modName ):
                    if not fName.endswith( ".pyc" ):
                        resolved, isLoop = resolveLink( fName )
                        if not isLoop:
                            modules[ modName ] = resolved
        elif isdir( fName ):
            modName = basename( fName )
            if isfile( fName + sep + "__init__.py" ) or \
               isfile( fName + sep + "__init__.py3" ):
                if not __isTestModule( modName ):
                    resolved, isLoop = resolveLink( fName )
                    if not isLoop:
                        modules[ modName ] = resolved
                for subMod, fName in getModules( fName ).items():
                    candidate = modName + "." + subMod
                    if not __isTestModule( candidate ):
                        resolved, isLoop = resolveLink( fName )
                        if not isLoop:
                            modules[ candidate ] = resolved
    sys.stderr = oldStderr
    return modules


def resolveLink( path ):
    """ Resolves links and detects loops """
    paths_seen = []
    while islink( path ):
        if path in paths_seen:
            # Already seen this path, so we must have a symlink loop
            return path, True
        paths_seen.append( path )
        # Resolve where the link points to
        resolved = readlink( path )
        if not isabs( resolved ):
            dir_name = dirname( path )
            path = normpath( dir_name + sep + resolved )
        else:
            path = normpath( resolved )
    return path, False


def __getSysPathExceptCurrent():
    " Provides a list of paths for system modules "

    path = map( realpath, map( os.path.abspath, sys.path[ : ] ) )

    def __filterCallback( path, cwd = realpath( getcwd() ) ):
        " get rid of non-existent directories and the current directory "
        return isdir( path ) and path != cwd

    return filter( __filterCallback, path )

if __name__ == "__main__":
    names = getSysModules().keys()
    names.sort()
    for name in names:
        print name

