
" Debug support "

import time
import sys
import os
import traceback


from rpdb2utils import _print
from rpdb2globals import tracebackLockAcquire, tracebackLockRelease


class CFileWrapper:
    " Simple file wrapper "
    def __init__(self, f):
        self.m_f = f
        return

    def write(self, ss):
        " Writes to the file "
        _print(ss, self.m_f, feol = False)
        return

    def __getattr__(self, name):
        return self.m_f.__getattr__(name)




#
# In debug mode errors and tracebacks are printed to stdout
#
g_fDebug = False


def getDebugMode():
    " True if debugging is on "
    return g_fDebug

def setDebugMode( value ):
    " Switches debugging mode "
    global g_fDebug

    g_fDebug = value
    return


def print_debug(_str):
    " Print debug if needed "
    if not g_fDebug:
        return

    tt = time.time()
    lt = time.localtime(tt)
    st = time.strftime('%H:%M:%S', lt) + '.%03d' % ((tt - int(tt)) * 1000)

    f = sys._getframe(1)

    filename = os.path.basename(f.f_code.co_filename)
    lineno = f.f_lineno
    name = f.f_code.co_name

    string = '%s %s:%d in %s: %s' % (st, filename, lineno, name, _str)

    _print(string, sys.__stderr__)
    return


def print_debug_exception(fForce = False):
    """
    Print exceptions to stdout when in debug mode.
    """

    if not g_fDebug and not fForce:
        return

    (tt, vv, tb) = sys.exc_info()
    print_exception(tt, vv, tb, fForce)
    return


def print_exception(tt, vv, tb, fForce = False):
    """
    Print exceptions to stderr when in debug mode.
    """
    if not g_fDebug and not fForce:
        return

    try:
        tracebackLockAcquire()
        traceback.print_exception(tt, vv, tb, file = CFileWrapper(sys.stderr))
    finally:
        tracebackLockRelease()
    return


def print_stack():
    """
    Print stack to stdout when in debug mode.
    """
    if g_fDebug == True:
        try:
            tracebackLockAcquire()
            traceback.print_stack(file = CFileWrapper(sys.stderr))
        finally:
            tracebackLockRelease()
    return


