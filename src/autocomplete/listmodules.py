#!/usr/bin/python
#
# Locate all standard modules available in this build.
#
# This script is designed to run on Python 1.5.2 and newer.
#
# Written by Fredrik Lundh, January 2005
# Adopted for codimension by Sergey Satskiy, 2011
#

"""Routines to get a list of modules; sys and for a dir"""

import imp
import sys
import os
import re
from os import listdir, getcwd, readlink
from os.path import (isfile, basename, splitext, realpath, isdir,
                     sep, islink, isabs, dirname, normpath)

# known test packages
TEST_PACKAGES = "test.", "bsddb.test.", "distutils.tests."

__suffixes = imp.get_suffixes()


def __getSuffix(fileName):
    """Provides suffix info for a file name"""
    for suffix in __suffixes:
        if fileName[-len(suffix[0]):] == suffix[0]:
            return suffix
    return None


def getSysModules():
    """Provides a dictionary of system modules. The pwd dir is excluded."""
    paths = __getSysPathExceptCurrent()

    modules = {}
    for modName in sys.builtin_module_names:
        if modName not in ['__builtin__', '__main__']:
            modules[modName] = None

    # The os.path depends on the platform, so I insert it here as an exception
    modules["os.path"] = None

    for path in paths:
        modules.update(getModules(path))
    return modules


class DevNull:

    """Stderr supresser"""

    def __init__(self):
        pass

    def write(self, data):
        """Supresses everything what is written into a stream"""
        pass


def __isTestModule(modName):
    """Returns True if it is a test module"""
    for modToDel in TEST_PACKAGES:
        if modName.startswith(modToDel):
            return True
    return False


__regexpr = re.compile(r"(?i)[a-z_]\w*$")


def getModules(path):
    """Provides modules in a given directory.

    It expects absolute real path. Otherwise it is not guaranteed it
    works all right.
    """
    # Make sure the path does not have double separators
    # and has separator at the end
    path = normpath(path) + sep

    oldStderr = sys.stderr
    sys.stderr = DevNull()
    modules = {}
    for fName in listdir(path):
        fName = path + fName
        if isfile(fName):
            modName, _ = splitext(fName)
            suffix = __getSuffix(fName)
            if not suffix:
                continue
            modName = basename(modName)
            if modName == '__init__':
                continue
            if __regexpr.match(modName):
                if __isTestModule(modName):
                    continue
                if suffix[2] == imp.C_EXTENSION:
                    # The initial version checked if this module could
                    # be imported. It turned out that some libraries
                    # on Ubuntu in particular can just hang. So I do
                    # not check loading and voluntary add path to
                    # the list of modules. Otherwise autocomplete
                    # will not work for some important (and properly loadable)
                    # modules like PyQt5
                    resolved, isLoop = resolveLink(fName)
                    if not isLoop:
                        modules[modName] = resolved
                    continue
                if not fName.endswith('.pyc') and not fName.endswith('.pyo'):
                    resolved, isLoop = resolveLink(fName)
                    if not isLoop:
                        modules[modName] = resolved
        elif isdir(fName):
            modName = basename(fName)

            candidate = fName + sep + "__init__.py"
            if not isfile(candidate):
                candidate += "3"
                if not isfile(candidate):
                    continue

            if not __isTestModule(modName):
                resolved, isLoop = resolveLink(candidate)
                if not isLoop:
                    modules[modName] = resolved

            for subMod, fName in getModules(fName).items():
                candidate = modName + "." + subMod
                if not __isTestModule(candidate):
                    resolved, isLoop = resolveLink(fName)
                    if not isLoop:
                        modules[candidate] = resolved
    sys.stderr = oldStderr
    return modules


def resolveLink(path):
    """Resolves links and detects loops"""
    paths_seen = []
    while islink(path):
        if path in paths_seen:
            # Already seen this path, so we must have a symlink loop
            return path, True
        paths_seen.append(path)
        # Resolve where the link points to
        resolved = readlink(path)
        if not isabs(resolved):
            dir_name = dirname(path)
            path = normpath(dir_name + sep + resolved)
        else:
            path = normpath(resolved)
    return path, False


def __getSysPathExceptCurrent():
    """Provides a list of paths for system modules"""
    path = map(realpath, map(os.path.abspath, sys.path[:]))

    def __filterCallback(path, cwd=realpath(getcwd())):
        """get rid of non-existent directories and the current directory"""
        return isdir(path) and path != cwd

    return filter(__filterCallback, path)


if __name__ == "__main__":
    sysModules = getSysModules()
    names = list(sysModules.keys())
    names.sort()
    for name in names:
        print("Name: " + name + " Path: " + str(sysModules[name]))
