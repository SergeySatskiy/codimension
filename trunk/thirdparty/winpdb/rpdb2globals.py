
" Various global variables commonly used "

import threading

LOOPBACK = '127.0.0.1'
LOCALHOST = 'localhost'

PING_TIMEOUT = 4.0

SERVER_PORT_RANGE_START = 51000
SERVER_PORT_RANGE_LENGTH = 24

DICT_KEY_STACK = 'stack'
DEBUGGER_FILENAME = 'rpdb2.py'


STR_SPAWN_UNSUPPORTED = "The debugger does not know how to open a new " \
                        "console on this system. You can start the debuggee " \
                        "manually with the -d flag on a separate console " \
                        "and then use the 'attach' command to attach to it."
STR_STARTUP_SPAWN_NOTICE = "Starting debuggee..."
STR_PASSWORD_MUST_BE_SET = "A password should be set to secure debugger " \
                           "client-server communication."

PYTHON_FILE_EXTENSION = '.py'
PYTHONW_FILE_EXTENSION = '.pyw'
PYTHONW_SO_EXTENSION = '.so'
PYTHON_EXT_LIST = ['.py', '.pyw', '.pyc', '.pyd', '.pyo', '.so']


g_fFirewallTest = True

#
# Lock for the traceback module to prevent it from interleaving
# output from different threads.
#
g_traceback_lock = threading.RLock()

def tracebackLockAcquire():
    " Grabs the lock "
    global g_traceback_lock
    g_traceback_lock.acquire()
    return

def tracebackLockRelease():
    " Releases the lock "
    global g_traceback_lock
    g_traceback_lock.release()
    return



def getFirewallTest():
    " Provides the firewall test value "
    return g_fFirewallTest

def setFirewallTest( value ):
    " Sets the new firewall test value "
    global g_fFirewallTest

    g_fFirewallTest = value
    return


g_fScreen = False

def getScreen():
    " Provides the screen value "
    return g_fScreen

def setScreen( value ):
    " Sets the new screen value "
    global g_fScreen

    g_fScreen = value
    return


g_fDefaultStd = True

def getDefaultStd():
    " Provides the default std value "
    return g_fDefaultStd

def setDefaultStd( value ):
    " Sets the default std value "
    global g_fDefaultStd

    g_fDefaultStd = value
    return


g_initial_cwd = []

def getInitialCwd():
    " Provides the initial cwd "
    return g_initial_cwd

def setInitialCwd( value ):
    " Sets the initial cwd "
    global g_initial_cwd

    g_initial_cwd = value
    return



g_found_unicode_files = {}

def getFoundUnicodeFiles():
    " Provides the found unicode files "
    return g_found_unicode_files

def updateFoundUnicodeFiles( key, value ):
    " Updates the found unicode files "
    global g_found_unicode_files

    g_found_unicode_files[ key ] = value
    return

g_alertable_waiters = {}

def getAlertableWaiters():
    " Provides alertable waiters "
    return g_alertable_waiters

def updateAlertableWaiters( key, value ):
    " Updates the found alertable waiter "
    global g_alertable_waiters

    g_alertable_waiters[ key ] = value
    return

def delAlertableWaiter( key ):
    " deletes from alertable waiters "
    global g_alertable_waiters

    del g_alertable_waiters[ key ]
    return

