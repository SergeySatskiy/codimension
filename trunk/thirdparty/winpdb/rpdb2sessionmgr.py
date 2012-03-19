
" Session managers (client side) "

import os
import sys
import time
import subprocess
import threading
import socket
import pickle
import re
import hmac
import stat
import tempfile
import random
import errno
import base64
import string

try:
    import thread
    import commands
except:
    #
    # The above modules were renamed in Python 3 so try to import them 'as'
    #
    import _thread as thread
    import subprocess as commands


from rpdb2exceptions import BadVersion, AuthenticationBadData, \
                            AuthenticationFailure, UnexpectedData, \
                            AlreadyAttached, NotAttached, \
                            DebuggerNotBroken, BadArgument, CException, \
                            CConnectionException, UnknownServer, \
                            SpawnUnsupported, \
                            UnsetPassword, BadMBCSPath, FirewallBlock, \
                            EncryptionNotSupported, EncryptionExpected, \
                            DecryptionFailure, NoThreads, NoExceptionFound
from rpdb2utils import is_unicode, as_unicode, as_bytes, as_string, _print, \
                       get_version, thread_is_alive, POSIX, RPDB_BPL_FOLDER, \
                       RPDB_BPL_FOLDER_NT, calc_pwd_file_path, detect_locale, \
                       calcURL, is_valid_pwd, getcwdu, generate_rid, \
                       ENCODING_AUTO, delete_pwd_file, myisfile, \
                       findFile, my_os_path_join, is_py3k
from rpdb2events import CEventUnhandledException, CEventState, CEventExit, \
                        CEventStackDepth, CEventNoThreads, \
                        CEventConflictingModules, CEventSignalIntercepted, \
                        CEventSignalException, CEventEmbeddedSync, \
                        CEventSynchronicity, CEventTrap, CEventForkMode, \
                        CEventForkSwitch, CEventExecSwitch, CEventEncoding, \
                        CEventStackFrameChange, CEventNamespace, \
                        CEventDispatcher, EVENT_EXCLUDE, CEventBreakpoint
from rpdb2statemgr import CStateManager, STATE_BROKEN, STATE_DETACHED, \
                          STATE_ANALYZE, STATE_SPAWNING, STATE_ATTACHING, \
                          STATE_DETACHING
from rpdb2pwdsrvproxy import CPwdServerProxy
from rpdb2debug import print_debug_exception, print_debug, getDebugMode, \
                       print_exception
from rpdb2globals import LOOPBACK, LOCALHOST, PING_TIMEOUT, \
                         SERVER_PORT_RANGE_START, SERVER_PORT_RANGE_LENGTH, \
                         DICT_KEY_STACK, DEBUGGER_FILENAME, \
                         STR_SPAWN_UNSUPPORTED, STR_STARTUP_SPAWN_NOTICE, \
                         STR_PASSWORD_MUST_BE_SET, getFirewallTest, \
                         getScreen, getDefaultStd, getFoundUnicodeFiles
from rpdb2rpcclient import CTimeoutTransport, CLocalTransport
from rpdb2crypto import CCrypto



STARTUP_TIMEOUT = 3.0
STARTUP_RETRIES = 3
COMMUNICATION_RETRIES = 5
IDLE_MAX_RATE = 2.0
MAX_BPL_FILES = 100


STR_STARTUP_NOTICE = "Attaching to debuggee..."
STR_MULTIPLE_DEBUGGEES = "WARNING: There is more than one debuggee '%s'."
STR_ATTACH_CRYPTO_MODE = "Debug Channel is%s encrypted."
STR_ATTACH_CRYPTO_MODE_NOT = "NOT"
STR_ATTACH_SUCCEEDED = "Successfully attached to '%s'."
STR_ATTACH_FAILED_NAME = "Failed to attach to '%s'."
STR_ERROR_OTHER = "Command returned the following error:\n%(type)s, " \
                  "%(value)s.\nPlease check stderr for stack trace and " \
                  "report to support."
STR_SPAWN_UNSUPPORTED_SCREEN_SUFFIX =  """Alternatively, you can use the screen utility and invoke rpdb2 in screen mode with the -s command-line flag as follows:
screen rpdb2 -s some-script.py script-arg1 script-arg2..."""
STR_DISPLAY_ERROR = """If the X server (Windowing system) is not started you need to use rpdb2 with the screen utility and invoke rpdb2 in screen mode with the -s command-line flag as follows:
screen rpdb2 -s some-script.py script-arg1 script-arg2..."""
STR_CONFLICTING_MODULES = "The modules: %s, which are incompatible with " \
                          "the debugger were detected and can possibly " \
                          "cause the debugger to fail."
STR_SIGNAL_INTERCEPT = "The signal %s(%d) was intercepted inside debugger " \
                       "tracing logic. It will be held pending until the " \
                       "debugger continues. Any exceptions raised by the " \
                       "handler will be ignored!"
STR_SIGNAL_EXCEPTION = "Exception %s raised by handler of signal %s(%d) " \
                       "inside debugger tracing logic was ignored!"
STR_DEBUGGEE_TERMINATED = "Debuggee has terminated."
STR_ATTEMPTING_TO_DETACH = "Detaching from script..."
STR_DETACH_SUCCEEDED = "Detached from script."
STR_ATTEMPTING_TO_STOP = "Requesting script to stop."
STR_RANDOM_PASSWORD = "Password has been set to a random password."
STR_COMMUNICATION_FAILURE = "Failed to communicate with debugged script."
STR_LOST_CONNECTION = "Lost connection to debuggee."
STR_FIREWALL_BLOCK = "A firewall is blocking the local communication chanel " \
                     "(socket) that is required between the debugger and " \
                     "the debugged script. Please make sure that the " \
                     "firewall allows that communication."
STR_BAD_VERSION = "A debuggee was found with incompatible " \
                  "debugger version %(value)s."
STR_UNEXPECTED_DATA = "Unexpected data received."
STR_DEBUGGEE_UNKNOWN = "Failed to find script."
STR_DEBUGGEE_NO_ENCRYPTION = "Debuggee does not support encrypted mode. " \
                             "Either install the python-crypto package on " \
                             "the debuggee machine or allow unencrypted " \
                             "connections."
STR_ENCRYPTION_EXPECTED = "While attempting to find debuggee, at least one " \
                          "debuggee denied connection since it accepts " \
                          "encrypted connections only."
STR_DECRYPTION_FAILURE = "Bad packet was received by the debuggee."
STR_ACCESS_DENIED = "While attempting to find debuggee, at least one " \
                    "debuggee denied connection because of mismatched " \
                    "passwords. Please verify your password."
STR_BAD_MBCS_PATH = "The debugger can not launch the script since the path " \
                    "to the Python executable or the debugger scripts can " \
                    "not be encoded into the default system code page. " \
                    "Please check the settings of 'Language for non-Unicode " \
                    "programs' in the Advanced tab of the Windows Regional " \
                    "and Language Options dialog."
STR_ALREADY_ATTACHED = "Already attached. Detach from debuggee and try again."
STR_NOT_ATTACHED = "Not attached to any script. " \
                   "Attach to a script and try again."
STR_DEBUGGEE_NOT_BROKEN = "Debuggee has to be waiting at break " \
                          "point to complete this command."
STR_NO_THREADS = "Operation failed since no traced threads were found."
STR_EXCEPTION_NOT_FOUND = "No exception was found."

RPDBTERM = 'RPDBTERM'
COLORTERM = 'COLORTERM'
KDE_PREFIX = 'KDE'
GNOME_PREFIX = 'GNOME'
RXVT = 'rxvt'
XTERM = 'xterm'
KDE_DEFAULT_TERM_QUERY = "kreadconfig --file kdeglobals --group General " \
                         "--key TerminalApplication --default konsole"
GNOME_DEFAULT_TERM = 'gnome-terminal'
MAC = 'mac'
DARWIN = 'darwin'
SCREEN = 'screen'
NT_DEBUG = 'nt_debug'


BREAKPOINTS_FILE_EXT = '.bpl'


if is_py3k():
    g_safe_base64_to = bytes.maketrans(as_bytes('/+='), as_bytes('_-#'))
    g_safe_base64_from = bytes.maketrans(as_bytes('_-#'), as_bytes('/+='))
else:
    g_safe_base64_to = string.maketrans(as_bytes('/+='), as_bytes('_-#'))
    g_safe_base64_from = string.maketrans(as_bytes('_-#'), as_bytes('/+='))




g_error_mapping = {
    socket.error:               STR_COMMUNICATION_FAILURE,

    CConnectionException:       STR_LOST_CONNECTION,
    FirewallBlock:              STR_FIREWALL_BLOCK,
    BadVersion:                 STR_BAD_VERSION,
    UnexpectedData:             STR_UNEXPECTED_DATA,
    SpawnUnsupported:           STR_SPAWN_UNSUPPORTED,
    UnknownServer:              STR_DEBUGGEE_UNKNOWN,
    UnsetPassword:              STR_PASSWORD_MUST_BE_SET,
    EncryptionNotSupported:     STR_DEBUGGEE_NO_ENCRYPTION,
    EncryptionExpected:         STR_ENCRYPTION_EXPECTED,
    DecryptionFailure:          STR_DECRYPTION_FAILURE,
    AuthenticationBadData:      STR_ACCESS_DENIED,
    AuthenticationFailure:      STR_ACCESS_DENIED,
    BadMBCSPath:                STR_BAD_MBCS_PATH,

    AlreadyAttached:            STR_ALREADY_ATTACHED,
    NotAttached:                STR_NOT_ATTACHED,
    DebuggerNotBroken:          STR_DEBUGGEE_NOT_BROKEN,
    NoThreads:                  STR_NO_THREADS,
    NoExceptionFound:           STR_EXCEPTION_NOT_FOUND,
}



#
# Map between OS type and relevant command to initiate a new OS console.
# entries for other OSs can be added here.
# '%s' serves as a place holder.
#
# Currently there is no difference between 'nt' and NT_DEBUG, since now
# both of them leave the terminal open after termination of debuggee to
# accommodate scenarios of scripts with child processes.
#
osSpawn = {
    'nt':               'start "rpdb2 - Version ' + get_version() + \
                        ' - Debuggee Console" cmd.exe ' \
                        '/K ""%(exec)s" %(options)s"',
    NT_DEBUG:           'start "rpdb2 - Version ' + get_version() + \
                        ' - Debuggee Console" cmd.exe ' \
                        '/K ""%(exec)s" %(options)s"',
    POSIX:              "%(term)s -e %(shell)s -c " \
                        "'%(exec)s %(options)s; %(shell)s' &",
    'Terminal':         "Terminal --disable-server -x %(shell)s -c " \
                        "'%(exec)s %(options)s; %(shell)s' &",
    GNOME_DEFAULT_TERM: "gnome-terminal --disable-factory -x %(shell)s -c " \
                        "'%(exec)s %(options)s; %(shell)s' &",
    MAC:                '%(exec)s %(options)s',
    DARWIN:             '%(exec)s %(options)s',
    SCREEN:             'screen -t debuggee_console %(exec)s %(options)s'
}


def controlRate(t_last_call, max_rate):
    """
    Limits rate at which this function is called by sleeping.
    Returns the time of invocation.
    """
    pp = 1.0 / max_rate
    t_current = time.time()
    dt = t_current - t_last_call

    if dt < pp:
        time.sleep(pp - dt)
    return t_current



def generate_random_password():
    " Generate an 8 characters long password "

    chars = 'abdefghijmnqrt' + 'ABDEFGHJLMNQRTY'
    digits_chars = '23456789_' + chars

    _rpdb2_pwd = generate_random_char(chars)

    for i in xrange(0, 7):
        _rpdb2_pwd += generate_random_char(digits_chars)

    return as_unicode(_rpdb2_pwd)


def generate_random_char(_str):
    " Return a random character from string argument "
    if _str == '':
        return ''
    return _str[ random.randint(0, len(_str) - 1) ]



def split_command_line_path_filename_args(command_line):
    """
    Split command line to a 3 elements tuple (path, filename, args)
    """

    command_line = command_line.strip()
    if len(command_line) == 0:
        return ('', '', '')

    if myisfile(command_line):
        (_path, _filename) = split_path(command_line)
        return (_path, _filename, '')

    if command_line[0] in ['"', "'"]:
        _command_line = command_line[1:]
        i = _command_line.find(command_line[0])
        if i == -1:
            (_path, filename) = split_path(_command_line)
            return (_path, filename, '')
        else:
            (_path, filename) = split_path(_command_line[: i])
            args = _command_line[i + 1:].strip()
            return (_path, filename, args)
    else:
        i = command_line.find(' ')
        if i == -1:
            (_path, filename) = split_path(command_line)
            return (_path, filename, '')
        else:
            args = command_line[i + 1:].strip()
            (_path, filename) = split_path(command_line[: i])
            return (_path, filename, args)



def split_path(path):
    " Splits the path to dir and the file name "
    (_path, filename) = os.path.split(path)

    #
    # Make sure path separator (e.g. '/') ends the splitted path if it was in
    # the original path.
    #
    if (_path[-1:] not in [os.path.sep, os.path.altsep]) and \
        (path[len(_path): len(_path) + 1] in [os.path.sep, os.path.altsep]):
        _path = _path + path[len(_path): len(_path) + 1]

    return (_path, filename)



def calcUserShell():
    " Provides the user shell name "
    try:
        envVar = os.getenv('SHELL')
        if envVar != None:
            return envVar

        import getpass
        username = getpass.getuser()

        f = open('/etc/passwd', 'r')
        content = f.read()
        f.close()

        lines = content.split('\n')
        users = dict([(e.split(':', 1)[0], e.split(':')[-1]) for e in lines])

        return users[username]

    except:
        return 'sh'


def isFileInPath(filename):
    " Checks if the file is in path "
    if filename == '':
        return False

    try:
        findFile(filename)
        return True

    except IOError:
        return False


def isPrefixInEnviron(_str):
    " True if the prefix is in environment "
    for var_name in os.environ.keys():
        if var_name.startswith(_str):
            return True
    return False


def calcTerminalCommand():
    """
    Calc the unix command to start a new terminal, for example: xterm
    """

    if RPDBTERM in os.environ:
        term = os.environ[RPDBTERM]
        if isFileInPath(term):
            return term

    if COLORTERM in os.environ:
        term = os.environ[COLORTERM]
        if isFileInPath(term):
            return term

    if isPrefixInEnviron(KDE_PREFIX):
        (ss, term) = commands.getstatusoutput(KDE_DEFAULT_TERM_QUERY)
        if (ss == 0) and isFileInPath(term):
            return term

    elif isPrefixInEnviron(GNOME_PREFIX):
        if isFileInPath(GNOME_DEFAULT_TERM):
            return GNOME_DEFAULT_TERM

    if isFileInPath(XTERM):
        return XTERM

    if isFileInPath(RXVT):
        return RXVT

    raise SpawnUnsupported


def calcMacTerminalCommand(command):
    """
    Calculate what to put in popen to start a given script.
    Starts a tiny Applescript that performs the script action.
    """

    #
    # Quoting is a bit tricky; we do it step by step.
    # Make Applescript string: put backslashes before double quotes and
    # backslashes.
    #
    command = command.replace('\\', '\\\\').replace('"', '\\"')

    #
    # Make complete Applescript command.
    #
    command = 'tell application "Terminal" to do script "%s"' % command

    #
    # Make a shell single quoted string (put backslashed single quotes
    # outside string).
    #
    command = command.replace("'", "'\\''")

    #
    # Make complete shell command.
    #
    return "osascript -e '%s'" % command


def create_pwd_file(rid, _rpdb2_pwd):
    """
    Create password file for Posix systems.
    """

    if os.name != POSIX:
        return

    path = calc_pwd_file_path(rid)

    fd = os.open(path, os.O_WRONLY | os.O_CREAT, int('0600', 8))

    os.write(fd, as_bytes(_rpdb2_pwd))
    os.close(fd)
    return


def calc_bpl_filename(filename):
    " Name for the breakpoints file "
    key = as_bytes(filename)
    tmp_filename = hmac.new(key).hexdigest()[:10]

    if os.name == POSIX:
        home = os.path.expanduser('~')
        bpldir = os.path.join(home, RPDB_BPL_FOLDER)
        cleanup_bpl_folder(bpldir)
        path = os.path.join(bpldir, tmp_filename) + BREAKPOINTS_FILE_EXT
        return path

    #
    # gettempdir() is used since it works with unicode user names on
    # Windows.
    #

    tmpdir = tempfile.gettempdir()
    bpldir = os.path.join(tmpdir, RPDB_BPL_FOLDER_NT)

    if not os.path.exists(bpldir):
        #
        # Folder creation is done here since this is a temp folder.
        #
        try:
            os.mkdir(bpldir, int('0700', 8))
        except:
            print_debug_exception()
            raise CException

    else:
        cleanup_bpl_folder(bpldir)

    return os.path.join(bpldir, tmp_filename) + BREAKPOINTS_FILE_EXT



def cleanup_bpl_folder(path):
    " Cleans up breakpoints directory "
    if random.randint(0, 10) > 0:
        return

    lst = os.listdir(path)
    if len(lst) < MAX_BPL_FILES:
        return

    try:
        ll = [(os.stat(os.path.join(path, f))[stat.ST_ATIME], f) for f in lst]
    except:
        return

    ll.sort()

    for (tt, f) in ll[: -MAX_BPL_FILES]:
        try:
            os.remove(os.path.join(path, f))
        except:
            pass
    return



class CSession:
    """
    Basic class that communicates with the debuggee server.
    """

    def __init__(self, host, port, _rpdb2_pwd, fAllowUnencrypted, rid):
        self.m_crypto = CCrypto(_rpdb2_pwd, fAllowUnencrypted, rid)

        self.m_host = host
        self.m_port = port
        self.m_proxy = None
        self.m_server_info = None
        self.m_exc_info = None

        self.m_fShutDown = False
        self.m_fRestart = False
        return


    def get_encryption(self):
        " Provides encryption "
        return self.m_proxy.get_encryption()


    def getServerInfo(self):
        " Provides server info "
        return self.m_server_info


    def pause(self):
        " Pause "
        self.m_fRestart = True
        return


    def restart(self, sleep = 0, timeout = 10):
        " Restarts "
        self.m_fRestart = True

        time.sleep(sleep)
        startTime = time.time()

        try:
            try:
                while time.time() < startTime + timeout:
                    try:
                        self.connect()
                        return

                    except socket.error:
                        continue

                raise CConnectionException

            except:
                self.m_fShutDown = True
                raise

        finally:
            self.m_fRestart = False
        return


    def shut_down(self):
        " Shuts the session "
        self.m_fShutDown = True
        return


    def getProxy(self):
        """
        Return the proxy object.
        With this object you can invoke methods on the server.
        """

        while self.m_fRestart:
            time.sleep(0.1)

        if self.m_fShutDown:
            raise NotAttached

        return self.m_proxy


    def connectAsync(self):
        " Connects asynchronously "
        thr = threading.Thread(target = self.connectNoThrow)
        #thread_set_daemon(thr, True)
        thr.start()
        return thr


    def connectNoThrow(self):
        " Connect without exceptions "
        try:
            self.connect()
        except:
            self.m_exc_info = sys.exc_info()
        return


    def connect(self):
        " Connect "
        host = self.m_host
        if host.lower() == LOCALHOST:
            host = LOOPBACK

        server = CPwdServerProxy(self.m_crypto, calcURL(host, self.m_port),
                                 CTimeoutTransport())
        server_info = server.server_info()

        self.m_proxy = CPwdServerProxy(self.m_crypto,
                                       calcURL(host, self.m_port),
                                       CLocalTransport(),
                                       target_rid = server_info.m_rid)
        self.m_server_info = server_info
        return


    def isConnected(self):
        " True if connected "
        return self.m_proxy is not None



class CServerList:
    " Auxiliary for session manager: holds a list of debuggee servers "
    def __init__(self, host):
        self.m_host = host
        self.m_list = []
        self.m_errors = {}
        return


    def calcList(self, _rpdb2_pwd, rid, key = None):
        " Builds a list of servers "
        sil = []
        sessions = []
        self.m_errors = {}

        port = SERVER_PORT_RANGE_START
        while port < SERVER_PORT_RANGE_START + SERVER_PORT_RANGE_LENGTH:
            session = CSession(self.m_host, port, _rpdb2_pwd,
                               fAllowUnencrypted = True, rid = rid)
            thr = session.connectAsync()
            sessions.append((session, thr))
            port += 1

        for (session, thr) in sessions:
            thr.join()

            if (session.m_exc_info is not None):
                if not issubclass(session.m_exc_info[0], socket.error):
                    self.m_errors.setdefault(session.m_exc_info[0],
                                             []).append(session.m_exc_info)

                continue

            si = session.getServerInfo()
            if si is not None:
                sil.append((-si.m_age, si))

            sil.sort()
            self.m_list = [session[1] for session in sil]

            if key != None:
                try:
                    return self.findServers(key)[0]
                except:
                    pass

        if key != None:
            raise UnknownServer

        sil.sort()
        self.m_list = [session[1] for session in sil]

        return self.m_list


    def get_errors(self):
        " Provides errors "
        return self.m_errors


    def findServers(self, key):
        " Searches for servers "
        try:
            keyAsInt = int(key)
            _s = [s for s in self.m_list \
                    if (s.m_pid == keyAsInt) or (s.m_rid == key)]

        except ValueError:
            key = as_string(key, sys.getfilesystemencoding())
            _s = [s for s in self.m_list if key in s.m_filename]

        if _s == []:
            raise UnknownServer

        return _s




class CSimpleSessionManager:
    """
    This is a wrapper class that simplifies launching and controlling of a
    debuggee from within another program. For example, an IDE that launches
    a script for debugging puposes can use this class to launch, debug and
    stop a script.
    """

    def __init__(self, fAllowUnencrypted = True):
        self.__sm = CSessionManagerInternal(
                            _rpdb2_pwd = None,
                            fAllowUnencrypted = fAllowUnencrypted,
                            fAllowRemote = False,
                            host = LOCALHOST
                            )

        self.m_fRunning = False

        event_type_dict = {CEventUnhandledException: {}}
        self.__sm.register_callback(self.__unhandled_exception,
                                    event_type_dict, fSingleUse = False)

        event_type_dict = {CEventState: {}}
        self.__sm.register_callback(self.__state_calback,
                                    event_type_dict, fSingleUse = False)

        event_type_dict = {CEventExit: {}}
        self.__sm.register_callback(self.__termination_callback,
                                    event_type_dict, fSingleUse = False)
        return


    def shutdown(self):
        " Shutdown the manager "
        return self.__sm.shutdown()


    def launch(self, fchdir, command_line, encoding = 'utf-8',
                     fload_breakpoints = False):
        " Launch debugging "
        command_line = as_unicode(command_line, encoding, fstrict = True)
        self.m_fRunning = False
        self.__sm.launch(fchdir, command_line, fload_breakpoints)
        return


    def request_go(self):
        " Request Go "
        return self.__sm.request_go()


    def detach(self):
        " Detach from the debuggee "
        self.__sm.detach()
        return


    def stop_debuggee(self):
        " Stop the debuggee "
        self.__sm.stop_debuggee()
        return


    def get_session_manager(self):
        " Provides tge session manager "
        return self.__sm


    def prepare_attach(self):
        """
        Use this method to attach a debugger to the debuggee after an
        exception is caught.
        """

        _rpdb2_pwd = self.__sm.get_password()

        sinfo = self.__sm.get_server_info()
        rid = sinfo.m_rid

        if os.name == 'posix':
            #
            # On posix systems the password is set at the debuggee via
            # a special temporary file.
            #
            create_pwd_file(rid, _rpdb2_pwd)
            _rpdb2_pwd = None

        return (rid, _rpdb2_pwd)


    #
    # Override these callbacks to react to the related events.
    #

    def unhandled_exception_callback(self):
        " Unhandeled exception callback "
        _print('unhandled_exception_callback')
        self.request_go()
        return


    def script_paused(self):
        " Script paused callback "
        _print('script_paused')
        self.request_go()
        return


    def script_terminated_callback(self):
        " Script terminated callback "
        _print('script_terminated_callback')
        return


    #
    # Private Methods
    #

    def __unhandled_exception(self, event):
        " Unhandled exception "
        self.unhandled_exception_callback()
        return


    def __termination_callback(self, event):
        " Termination callback "
        self.script_terminated_callback()
        return


    def __state_calback(self, event):
        """
        Handle state change notifications from the debugge.
        """

        if event.m_state != STATE_BROKEN:
            return

        if not self.m_fRunning:
            #
            # First break comes immediately after launch.
            #
            print_debug('Simple session manager continues on first break.')
            self.m_fRunning = True
            self.request_go()
            return

        if self.__sm.is_unhandled_exception():
            return

        slist = self.__sm.get_stack(tid_list = [], fAll = False)
        if len(slist) == 0:
            self.request_go()
            return

        st = slist[0]
        ss = st.get(DICT_KEY_STACK, [])
        if len(ss) == 0:
            self.request_go()
            return

        ee = ss[-1]

        function_name = ee[2]
        filename = os.path.basename(ee[0])

        if filename != DEBUGGER_FILENAME:
            #
            # This is a user breakpoint (e.g. rpdb2.setbreak())
            #
            self.script_paused()
            return

        #
        # This is the setbreak() before a fork, exec or program
        # termination.
        #
        self.request_go()
        return



class CSessionManager:
    """
    Interface to the session manager.
    This is the interface through which the debugger controls and
    communicates with the debuggee.

    Accepted strings are either utf-8 or Unicode unless specified otherwise.
    Returned strings are Unicode (also when embedded in data structures).

    You can study the way it is used in StartClient()
    """

    def __init__(self, _rpdb2_pwd, fAllowUnencrypted, fAllowRemote, host):
        if _rpdb2_pwd != None:
            assert(is_valid_pwd(_rpdb2_pwd))
            _rpdb2_pwd = as_unicode(_rpdb2_pwd, fstrict = True)

        self.__smi = CSessionManagerInternal(
                            _rpdb2_pwd,
                            fAllowUnencrypted,
                            fAllowRemote,
                            host
                            )


    def shutdown(self):
        " Shutdown the manager "
        return self.__smi.shutdown()


    def set_printer(self, printer):
        """
        'printer' is a function that takes one argument and prints it.
        You can study CConsoleInternal.printer() as example for use
        and rational.
        """
        return self.__smi.set_printer(printer)


    def report_exception(self, excType, value, tback):
        """
        Sends exception information to the printer.
        """
        return self.__smi.report_exception(excType, value, tback)


    def register_callback(self, callback, event_type_dict, fSingleUse):
        """
        Receive events from the session manager.
        The session manager communicates it state mainly by firing events.
        You can study CConsoleInternal.__init__() as example for use.
        For details see CEventDispatcher.register_callback()
        """
        return self.__smi.register_callback(
                                callback,
                                event_type_dict,
                                fSingleUse
                                )


    def remove_callback(self, callback):
        " Removes the callback "
        return self.__smi.remove_callback(callback)


    def refresh(self):
        """
        Fire again all relevant events needed to establish the current state.
        """
        return self.__smi.refresh()


    def launch(self, fchdir, command_line, encoding = 'utf-8',
                     fload_breakpoints = True):
        """
        Launch debuggee in a new process and attach.
        fchdir - Change current directory to that of the debuggee.
        command_line - command line arguments pass to the script as a string.
        fload_breakpoints - Load breakpoints of last session.

        if command line is not a unicode string it will be decoded into unicode
        with the given encoding
        """

        command_line = as_unicode(command_line, encoding, fstrict = True)
        return self.__smi.launch(fchdir, command_line, fload_breakpoints)


    def restart(self):
        """
        Restart debug session with same command_line and fchdir arguments
        which were used in last launch.
        """
        return self.__smi.restart()


    def get_launch_args(self):
        """
        Return command_line and fchdir arguments which were used in last
        launch as (last_fchdir, last_command_line).
        Returns (None, None) if there is no info.
        """
        return self.__smi.get_launch_args()


    def attach(self, key, name = None, encoding = 'utf-8'):
        """
        Attach to a debuggee (establish communication with the debuggee-server)
        key - a string specifying part of the filename or PID of the debuggee.

        if key is not a unicode string it will be decoded into unicode
        with the given encoding
        """
        key = as_unicode(key, encoding, fstrict = True)
        return self.__smi.attach(key, name)


    def detach(self):
        """
        Let the debuggee go...
        """
        return self.__smi.detach()


    def request_break(self):
        " Request break "
        return self.__smi.request_break()


    def request_go(self):
        " Request go "
        return self.__smi.request_go()


    def request_go_breakpoint(self, filename, scope, lineno):
        """
        Go (run) until the specified location is reached.
        """
        filename = as_unicode(filename, fstrict = True)
        scope = as_unicode(scope, fstrict = True)
        return self.__smi.request_go_breakpoint(filename, scope, lineno)


    def request_step(self):
        """
        Go until the next line of code is reached.
        """
        return self.__smi.request_step()


    def request_next(self):
        """
        Go until the next line of code in the same scope is reached.
        """
        return self.__smi.request_next()


    def request_return(self):
        """
        Go until end of scope is reached.
        """
        return self.__smi.request_return()


    def request_jump(self, lineno):
        """
        Jump to the specified line number in the same scope.
        """
        return self.__smi.request_jump(lineno)


    #
    # REVIEW: should return breakpoint ID
    #
    def set_breakpoint(self, filename, scope, lineno, fEnabled, expr):
        """
        Set a breakpoint.

            filename - (Optional) can be either a file name or a module name,
                       full path, relative path or no path at all.
                       If filname is None or '', then the current module is
                       used.
            scope    - (Optional) Specifies a dot delimited scope for the
                       breakpoint, such as: foo or myClass.foo
            lineno   - (Optional) Specify a line within the selected file or
                       if a scope is specified, an zero-based offset from the
                       start of the scope.
            expr     - (Optional) A Python expression that will be evaluated
                       locally when the breakpoint is hit. The break will
                       occur only if the expression evaluates to true.
        """

        filename = as_unicode(filename, fstrict = True)
        scope = as_unicode(scope, fstrict = True)
        expr = as_unicode(expr, fstrict = True)

        return self.__smi.set_breakpoint(
                                filename,
                                scope,
                                lineno,
                                fEnabled,
                                expr
                                )


    def disable_breakpoint(self, id_list, fAll):
        """
        Disable breakpoints

            id_list - (Optional) A list of breakpoint ids.
            fAll    - disable all breakpoints regardless of id_list.
        """
        return self.__smi.disable_breakpoint(id_list, fAll)


    def enable_breakpoint(self, id_list, fAll):
        """
        Enable breakpoints

            id_list - (Optional) A list of breakpoint ids.
            fAll    - disable all breakpoints regardless of id_list.
        """
        return self.__smi.enable_breakpoint(id_list, fAll)


    def delete_breakpoint(self, id_list, fAll):
        """
        Delete breakpoints

            id_list - (Optional) A list of breakpoint ids.
            fAll    - disable all breakpoints regardless of id_list.
        """
        return self.__smi.delete_breakpoint(id_list, fAll)


    def get_breakpoints(self):
        """
        Return breakpoints in a dictionary of id keys to CBreakPoint values
        """
        return self.__smi.get_breakpoints()


    def save_breakpoints(self, _filename = ''):
        """
        Save breakpoints to file, locally (on the client side)
        """
        return self.__smi.save_breakpoints(_filename)


    def load_breakpoints(self, _filename = ''):
        """
        Load breakpoints from file, locally (on the client side)
        """
        return self.__smi.load_breakpoints(_filename)


    def set_trap_unhandled_exceptions(self, ftrap):
        """
        Set trap-unhandled-exceptions mode.
        ftrap with a value of False means unhandled exceptions will be ignored.
        The session manager default is True.
        """
        return self.__smi.set_trap_unhandled_exceptions(ftrap)


    def get_trap_unhandled_exceptions(self):
        """
        Get trap-unhandled-exceptions mode.
        """
        return self.__smi.get_trap_unhandled_exceptions()


    def set_fork_mode(self, ffork_into_child, ffork_auto):
        """
        Determine how to handle os.fork().

        ffork_into_child - True|False - If True, the debugger will debug the
            child process after a fork, otherwise the debugger will continue
            to debug the parent process.

        ffork_auto - True|False - If True, the debugger will not pause before
            a fork and will automatically make a decision based on the
            value of the ffork_into_child flag.
        """
        return self.__smi.set_fork_mode(ffork_into_child, ffork_auto)


    def get_fork_mode(self):
        """
        Return the fork mode in the form of a (ffork_into_child, ffork_auto)
        flags tuple.
        """
        return self.__smi.get_fork_mode()


    def get_stack(self, tid_list, fAll):
        " Provides the stack "
        return self.__smi.get_stack(tid_list, fAll)


    def get_source_file(self, filename, lineno, nlines):
        " Provides the source file "
        filename = as_unicode(filename, fstrict = True)
        return self.__smi.get_source_file(filename, lineno, nlines)


    def get_source_lines(self, nlines, fAll):
        " Provides the source line "
        return self.__smi.get_source_lines(nlines, fAll)


    def set_frame_index(self, frame_index):
        """
        Set frame index. 0 is the current executing frame, and 1, 2, 3,
        are deeper into the stack.
        """
        return self.__smi.set_frame_index(frame_index)


    def get_frame_index(self):
        """
        Get frame index. 0 is the current executing frame, and 1, 2, 3,
        are deeper into the stack.
        """
        return self.__smi.get_frame_index()


    def set_analyze(self, fAnalyze):
        """
        Toggle analyze mode. In analyze mode the stack switches to the
        exception stack for examination.
        """
        return self.__smi.set_analyze(fAnalyze)


    def set_host(self, host):
        """
        Set host to specified host (string) for attaching to debuggies on
        specified host. host can be a host name or ip address in string form.
        """
        return self.__smi.set_host(host)


    def get_host(self):
        " Provides the host "
        return self.__smi.get_host()


    def calc_server_list(self):
        """
        Calc servers (debuggable scripts) list on specified host.
        Returns a tuple of a list and a dictionary.
        The list is a list of CServerInfo objects sorted by their age
        ordered oldest last.
        The dictionary is a dictionary of errors that were encountered
        during the building of the list. The dictionary has error (exception)
        type as keys and number of occurances as values.
        """
        return self.__smi.calc_server_list()


    def get_server_info(self):
        """
        Return CServerInfo server info object that corresponds to the
        server (debugged script) to which the session manager is
        attached.
        """
        return self.__smi.get_server_info()


    def get_namespace(self, nlist, filter_level, repr_limit = 128,
                            fFilter = "DEPRECATED"):
        """
        get_namespace is designed for locals/globals panes that let
        the user inspect a namespace tree in GUI debuggers such as Winpdb.
        You can study the way it is used in Winpdb.

        nlist - List of tuples, where each tuple is made of a python expression
                as string and a flag that controls whether to "expand" the
                value, that is, to return its children as well in case it has
                children e.g. lists, dictionaries, etc...

        filter_level - 0, 1, or 2. Filter out methods and functions from
            classes and objects. (0 - None, 1 - Medium, 2 - Maximum).

        repr_limit - Length limit (approximated) to be imposed on repr() of
             returned items.

        examples of expression lists: 

          [('x', false), ('y', false)]
          [('locals()', true)]
          [('a.b.c', false), ('my_object.foo', false), ('another_object', true)]

        Return value is a list of dictionaries, where every element
        in the list corresponds to an element in the input list 'nlist'.

        Each dictionary has the following keys and values:
          DICT_KEY_EXPR - the original expression string.
          DICT_KEY_REPR - A repr of the evaluated value of the expression.
          DICT_KEY_IS_VALID - A boolean that indicates if the repr value is
                          valid for the purpose of re-evaluation.
          DICT_KEY_TYPE - A string representing the type of the experession's
                          evaluated value.
          DICT_KEY_N_SUBNODES - If the evaluated value has children like items
                          in a list or in a dictionary or members of a class,
                          etc, this key will have their number as value.
          DICT_KEY_SUBNODES - If the evaluated value has children and the
                          "expand" flag was set for this expression, then the
                          value of this key will be a list of dictionaries as
                          described below.
          DICT_KEY_ERROR - If an error prevented evaluation of this expression
                          the value of this key will be a repr of the
                          exception info: repr(sys.exc_info())

        Each dictionary for child items has the following keys and values:
          DICT_KEY_EXPR - The Python expression that designates this child.
                          e.g. 'my_list[0]' designates the first child of the
                          list 'my_list'
          DICT_KEY_NAME - a repr of the child name, e.g '0' for the first item
                          in a list.
          DICT_KEY_REPR - A repr of the evaluated value of the expression.
          DICT_KEY_IS_VALID - A boolean that indicates if the repr value is
                          valid for the purpose of re-evaluation.
          DICT_KEY_TYPE - A string representing the type of the experession's
                          evaluated value.
          DICT_KEY_N_SUBNODES - If the evaluated value has children like items
                          in a list or in a dictionary or members of a class,
                          etc, this key will have their number as value.
        """
        if fFilter != "DEPRECATED":
            filter_level = fFilter

        filter_level = int(filter_level)

        return self.__smi.get_namespace(nlist, filter_level, repr_limit)


    #
    # REVIEW: remove warning item.
    #
    def evaluate(self, expr):
        """
        Evaluate a python expression in the context of the current thread
        and frame.

        Return value is a tuple (v, w, e) where v is a repr of the evaluated
        expression value, w is always '', and e is an error string if an error
        occurred.

        NOTE: This call might not return since debugged script logic can lead
        to tmporary locking or even deadlocking.
        """
        expr = as_unicode(expr, fstrict = True)
        return self.__smi.evaluate(expr)


    def execute(self, suite):
        """
        Execute a python statement in the context of the current thread
        and frame.

        Return value is a tuple (w, e) where w and e are warning and
        error strings (respectively) if an error occurred.

        NOTE: This call might not return since debugged script logic can lead
        to tmporary locking or even deadlocking.
        """
        suite = as_unicode(suite, fstrict = True)
        return self.__smi.execute(suite)


    def complete_expression(self, expr):
        """
        Return matching completions for expression.
        Accepted expressions are of the form a.b.c

        Dictionary lookups or functions call are not evaluated. For
        example: 'getobject().complete' or 'dict[item].complete' are
        not processed.

        On the other hand partial expressions and statements are
        accepted. For example: 'foo(arg1, arg2.member.complete' will
        be accepted and the completion for 'arg2.member.complete' will
        be calculated.

        Completions are returned as a tuple of two items. The first item
        is a prefix to expr and the second item is a list of completions.
        For example if expr is 'foo(self.comp' the returned tuple can
        be ('foo(self.', ['complete', 'completion', etc...])
        """
        expr = as_unicode(expr, fstrict = True)
        return self.__smi.complete_expression(expr)


    def set_encoding(self, encoding, fraw = False):
        """
        Set the encoding that will be used as source encoding for execute()
        evaluate() commands and in strings returned by get_namespace().

        The encoding value can be either 'auto' or any encoding accepted by
        the codecs module. If 'auto' is specified, the encoding used will be
        the source encoding of the active scope, which is utf-8 by default.

        The default encoding value is 'auto'.

        If fraw is True, strings returned by evaluate() and get_namespace()
        will represent non ASCII characters as an escape sequence.
        """
        return self.__smi.set_encoding(encoding, fraw)


    def get_encoding(self):
        """
        return the (encoding, fraw) tuple.
        """
        return self.__smi.get_encoding()


    def set_synchronicity(self, fsynchronicity):
        """
        Set the synchronicity mode.

        Traditional Python debuggers that use the inspected thread (usually
        the main thread) to query or modify the script name-space have to
        wait until the script hits a break-point. Synchronicity allows the
        debugger to query and modify the script name-space even if its
        threads are still running or blocked in C library code by using
        special worker threads. In some rare cases querying or modifying data
        in synchronicity can crash the script. For example in some Linux
        builds of wxPython querying the state of wx objects from a thread
        other than the GUI thread can crash the script. If this happens or
        if you want to restrict these operations to the inspected thread,
        turn synchronicity off.

        On the other hand when synchronicity is off it is possible to
        accidentally deadlock or block indefinitely the script threads by
        querying or modifying particular data structures.

        The default is on (True).
        """
        return self.__smi.set_synchronicity(fsynchronicity)


    def get_synchronicity(self):
        " Provides the sync mode "
        return self.__smi.get_synchronicity()


    def get_state(self):
        """
        Get the session manager state. Return one of the STATE_* constants
        defined below, for example STATE_DETACHED, STATE_BROKEN, etc...
        """
        return self.__smi.get_state()


    #
    # REVIEW: Improve data strucutre.
    #
    def get_thread_list(self):
        " Provides the threads list "
        return self.__smi.get_thread_list()


    def set_thread(self, tid):
        """
        Set the focused thread to the soecified thread.
        tid - either the OS thread id or the zero based index of the thread
              in the thread list returned by get_thread_list().
        """
        return self.__smi.set_thread(tid)


    def set_password(self, _rpdb2_pwd):
        """
        Set the password that will govern the authentication and encryption
        of client-server communication.
        """
        _rpdb2_pwd = as_unicode(_rpdb2_pwd, fstrict = True)
        return self.__smi.set_password(_rpdb2_pwd)


    def get_password(self):
        """
        Get the password that governs the authentication and encryption
        of client-server communication.
        """
        return self.__smi.get_password()


    def get_encryption(self):
        """
        Get the encryption mode. Return True if unencrypted connections are
        not allowed. When launching a new debuggee the debuggee will inherit
        the encryption mode. The encryption mode can be set via command-line
        only.
        """
        return self.__smi.get_encryption()


    def set_remote(self, fAllowRemote):
        """
        Set the remote-connections mode. if True, connections from remote
        machine are allowed. When launching a new debuggee the debuggee will
        inherit this mode. This mode is only relevant to the debuggee.
        """
        return self.__smi.set_remote(fAllowRemote)


    def get_remote(self):
        """
        Get the remote-connections mode. Return True if connections from
        remote machine are allowed. When launching a new debuggee the
        debuggee will inherit this mode. This mode is only relevant to the
        debuggee.
        """
        return self.__smi.get_remote()


    def set_environ(self, envmap):
        """
        Set the environment variables mapping. This mapping is used
        when a new script is launched to modify its environment.

        Example for a mapping on Windows: [('Path', '%Path%;c:\\mydir')]
        Example for a mapping on Linux: [('PATH', '$PATH:~/mydir')]

        The mapping should be a list of tupples where each tupple is
        composed of a key and a value. Keys and Values must be either
        strings or Unicode strings. Other types will raise the BadArgument
        exception.

        Invalid arguments will be silently ignored.
        """
        return self.__smi.set_environ(envmap)


    def get_environ(self):
        """
        Return the current environment mapping.
        """
        return self.__smi.get_environ()


    def stop_debuggee(self):
        """
        Stop the debuggee immediately.
        """
        return self.__smi.stop_debuggee()



class CSessionManagerInternal:
    " Implementation of the session manager "

    def __init__(self, _rpdb2_pwd, fAllowUnencrypted, fAllowRemote, host):
        self.m_rpdb2_pwd = [_rpdb2_pwd, None][_rpdb2_pwd in [None, '']]
        self.m_fAllowUnencrypted = fAllowUnencrypted
        self.m_fAllowRemote = fAllowRemote
        self.m_rid = generate_rid()

        self.m_host = host
        self.m_server_list_object = CServerList(host)

        self.m_session = None
        self.m_server_info = None

        self.m_worker_thread = None
        self.m_worker_thread_ident = None
        self.m_fStop = False

        self.m_stack_depth = None
        self.m_stack_depth_exception = None
        self.m_frame_index = 0
        self.m_frame_index_exception = 0

        self.m_completions = {}

        self.m_remote_event_index = 0
        self.m_event_dispatcher_proxy = CEventDispatcher()
        self.m_event_dispatcher = CEventDispatcher( \
                                            self.m_event_dispatcher_proxy)
        self.m_state_manager = CStateManager(STATE_DETACHED,
                                             self.m_event_dispatcher,
                                             self.m_event_dispatcher_proxy)

        self.m_breakpoints_proxy = CBreakPointsManagerProxy(self)

        event_type_dict = {CEventState: {EVENT_EXCLUDE: [STATE_BROKEN,
                                                         STATE_ANALYZE]}}
        self.register_callback(self.reset_frame_indexes, event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventStackDepth: {}}
        self.register_callback(self.set_stack_depth, event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventNoThreads: {}}
        self.register_callback(self._reset_frame_indexes, event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventExit: {}}
        self.register_callback(self.on_event_exit, event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventConflictingModules: {}}
        self.register_callback(self.on_event_conflicting_modules,
                               event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventSignalIntercepted: {}}
        self.register_callback(self.on_event_signal_intercept, event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventSignalException: {}}
        self.register_callback(self.on_event_signal_exception, event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventEmbeddedSync: {}}
        self.register_callback(self.on_event_embedded_sync, event_type_dict,
                               fSingleUse = False)

        event_type_dict = {CEventSynchronicity: {}}
        self.m_event_dispatcher_proxy.register_callback( \
                                                self.on_event_synchronicity,
                                                event_type_dict,
                                                fSingleUse = False)
        self.m_event_dispatcher.register_chain_override(event_type_dict)

        event_type_dict = {CEventTrap: {}}
        self.m_event_dispatcher_proxy.register_callback(self.on_event_trap,
                                                        event_type_dict,
                                                        fSingleUse = False)
        self.m_event_dispatcher.register_chain_override(event_type_dict)

        event_type_dict = {CEventForkMode: {}}
        self.m_event_dispatcher_proxy.register_callback(self.on_event_fork_mode,
                                                        event_type_dict,
                                                        fSingleUse = False)
        self.m_event_dispatcher.register_chain_override(event_type_dict)

        self.m_printer = self.__nul_printer

        self.m_last_command_line = None
        self.m_last_fchdir = None

        self.m_fsynchronicity = True
        self.m_ftrap = True

        self.m_ffork_into_child = False
        self.m_ffork_auto = False

        self.m_environment = []

        self.m_encoding = ENCODING_AUTO
        self.m_fraw = False
        return


    def shutdown(self):
        " Shuts the debuggee down "
        self.m_event_dispatcher_proxy.shutdown()
        self.m_event_dispatcher.shutdown()
        self.m_state_manager.shutdown()
        return


    def __nul_printer(self, _str):
        " Null printer "
        pass


    def set_printer(self, printer):
        " Sets the printer "
        self.m_printer = printer
        return


    def register_callback(self, callback, event_type_dict, fSingleUse):
        " Registers the callback "
        return self.m_event_dispatcher.register_callback(callback,
                                                         event_type_dict,
                                                         fSingleUse)


    def remove_callback(self, callback):
        " Removes the callback "
        return self.m_event_dispatcher.remove_callback(callback)


    def __wait_for_debuggee(self, rid):
        " Waits for debuggee "
        try:
            time.sleep(STARTUP_TIMEOUT / 2)

            for i in range(STARTUP_RETRIES):
                try:
                    print_debug('Scanning for debuggee...')

                    startTime = time.time()
                    return self.m_server_list_object.calcList(self.m_rpdb2_pwd,
                                                              self.m_rid, rid)

                except UnknownServer:
                    delta = time.time() - startTime
                    if delta < STARTUP_TIMEOUT:
                        time.sleep(STARTUP_TIMEOUT - delta)

                    continue

            return self.m_server_list_object.calcList(self.m_rpdb2_pwd,
                                                      self.m_rid, rid)

        finally:
            errors = self.m_server_list_object.get_errors()
            self.__report_server_errors(errors, fsupress_pwd_warning = True)


    def get_encryption(self):
        " Provides the encryption "
        return self.getSession().get_encryption()


    def launch(self, fchdir, command_line, fload_breakpoints = True):
        " Launches debugging "
        assert(is_unicode(command_line))

        self.__verify_unattached()

        if not os.name in [POSIX, 'nt']:
            self.m_printer(STR_SPAWN_UNSUPPORTED)
            raise SpawnUnsupported

        if getFirewallTest():
            firewall_test = CFirewallTest(self.get_remote())
            if not firewall_test.run():
                raise FirewallBlock
        else:
            print_debug('Skipping firewall test.')

        if self.m_rpdb2_pwd is None:
            self.set_random_password()

        if command_line == '':
            raise BadArgument

        (path, \
         filename, \
         args) = split_command_line_path_filename_args(command_line)

        #if not IsPythonSourceFile(filename):
        #    raise NotPythonSource

        _filename = my_os_path_join(path, filename)

        expandedFilename = findFile(_filename)
        self.set_host(LOCALHOST)

        self.m_printer(STR_STARTUP_SPAWN_NOTICE)

        rid = generate_rid()

        create_pwd_file(rid, self.m_rpdb2_pwd)

        self.m_state_manager.set_state(STATE_SPAWNING)

        try:
            try:
                self._spawn_server(fchdir, expandedFilename, args, rid)
                server = self.__wait_for_debuggee(rid)
                self.attach(server.m_rid, server.m_filename,
                            fsupress_pwd_warning = True, fsetenv = True,
                            ffirewall_test = False, server = server,
                            fload_breakpoints = fload_breakpoints)

                self.m_last_command_line = command_line
                self.m_last_fchdir = fchdir

            except:
                if self.m_state_manager.get_state() != STATE_DETACHED:
                    self.m_state_manager.set_state(STATE_DETACHED)

                raise

        finally:
            delete_pwd_file(rid)
        return


    def restart(self):
        """
        Restart debug session with same command_line and fchdir arguments
        which were used in last launch.
        """

        if None in (self.m_last_fchdir, self.m_last_command_line):
            return

        if self.m_state_manager.get_state() != STATE_DETACHED:
            self.stop_debuggee()

        self.launch(self.m_last_fchdir, self.m_last_command_line)
        return


    def get_launch_args(self):
        """
        Return command_line and fchdir arguments which were used in last
        launch as (last_fchdir, last_command_line).
        Returns None if there is no info.
        """

        if None in (self.m_last_fchdir, self.m_last_command_line):
            return (None, None)

        return (self.m_last_fchdir, self.m_last_command_line)


    def _spawn_server(self, fchdir, expandedFilename, args, rid):
        """
        Start an OS console to act as server.
        What it does is to start rpdb again in a new
        console in server only mode.
        """

        if getScreen():
            name = SCREEN
        elif sys.platform == DARWIN:
            name = DARWIN
        else:
            try:
                import terminalcommand
                name = MAC
            except:
                name = os.name

        if name == 'nt' and getDebugMode():
            name = NT_DEBUG

        ee = ['', ' --encrypt'][not self.m_fAllowUnencrypted]
        rr = ['', ' --remote'][self.m_fAllowRemote]
        cc = ['', ' --chdir'][fchdir]
        pp = ['', ' --pwd="%s"' % self.m_rpdb2_pwd][os.name == 'nt']

        bb = ''

        encoding = detect_locale()
        fse = sys.getfilesystemencoding()

        expandedFilename = getFoundUnicodeFiles().get(expandedFilename,
                                                      expandedFilename)
        expandedFilename = as_unicode(expandedFilename, fse)

        if as_bytes('?') in as_bytes(expandedFilename,
                                     encoding, fstrict = False):
            _u = as_bytes(expandedFilename)
            _b = base64.encodestring(_u)
            _b = _b.strip(as_bytes('\n')).translate(g_safe_base64_to)
            _b = as_string(_b, fstrict = True)
            bb = ' --base64=%s' % _b

        debugger = os.path.abspath(__file__)
        if debugger[-1:] == 'c':
            debugger = debugger[:-1]

        debugger = as_unicode(debugger, fse)

        debug_prints = ['', ' --debug'][getDebugMode()]

        options = '"%s"%s --debugee%s%s%s%s%s --rid=%s "%s" %s' % \
                        (debugger, debug_prints,
                         pp, ee, rr, cc, bb, rid, expandedFilename, args)

        python_exec = sys.executable
        if python_exec.endswith('w.exe'):
            python_exec = python_exec[:-5] + '.exe'

        python_exec = as_unicode(python_exec, fse)

        if as_bytes('?') in as_bytes(python_exec + debugger,
                                     encoding, fstrict = False):
            raise BadMBCSPath

        if name == POSIX:
            shell = calcUserShell()
            terminal_command = calcTerminalCommand()

            if terminal_command in osSpawn:
                command = osSpawn[terminal_command] % {'shell': shell,
                                                       'exec': python_exec,
                                                       'options': options}
            else:
                command = osSpawn[name] % {'term': terminal_command,
                                           'shell': shell,
                                           'exec': python_exec,
                                           'options': options}
        else:
            command = osSpawn[name] % {'exec': python_exec, 'options': options}

        if name == DARWIN:
            ss = 'cd "%s" ; %s' % (getcwdu(), command)
            command = calcMacTerminalCommand(ss)

        print_debug('Terminal open string: %s' % repr(command))

        command = as_string(command, encoding)

        if name == MAC:
            terminalcommand.run(command)
        else:
            subprocess.Popen(command, shell=True)
        return


    def attach(self, key, name = None, fsupress_pwd_warning = False,
                     fsetenv = False, ffirewall_test = True, server = None,
                     fload_breakpoints = True):
        " Attach "
        assert(is_unicode(key))

        self.__verify_unattached()

        if key == '':
            raise BadArgument

        if self.m_rpdb2_pwd is None:
            #self.m_printer(STR_PASSWORD_MUST_BE_SET)
            raise UnsetPassword

        if getFirewallTest() and ffirewall_test:
            firewall_test = CFirewallTest(self.get_remote())
            if not firewall_test.run():
                raise FirewallBlock
        elif not getFirewallTest() and ffirewall_test:
            print_debug('Skipping firewall test.')

        if name is None:
            name = key

        _name = name

        self.m_printer(STR_STARTUP_NOTICE)
        self.m_state_manager.set_state(STATE_ATTACHING)

        try:
            servers = [server]
            if server == None:
                self.m_server_list_object.calcList(self.m_rpdb2_pwd, self.m_rid)
                servers = self.m_server_list_object.findServers(key)
                server = servers[0]

            _name = server.m_filename

            errors = self.m_server_list_object.get_errors()
            if not key in [server.m_rid, str(server.m_pid)]:
                self.__report_server_errors(errors, fsupress_pwd_warning)

            self.__attach(server, fsetenv)
            if len(servers) > 1:
                self.m_printer(STR_MULTIPLE_DEBUGGEES % key)
            self.m_printer(STR_ATTACH_CRYPTO_MODE % \
                                ([' ' + STR_ATTACH_CRYPTO_MODE_NOT, ''] \
                                    [self.get_encryption()]))
            self.m_printer(STR_ATTACH_SUCCEEDED % server.m_filename)

            try:
                if fload_breakpoints:
                    self.load_breakpoints()
            except:
                pass

        except (socket.error, CConnectionException):
            self.m_printer(STR_ATTACH_FAILED_NAME % _name)
            self.m_state_manager.set_state(STATE_DETACHED)
            raise

        except:
            print_debug_exception()
            assert False
        return


    def report_exception(self, _type, value, tback):
        " Reports an exception "
        msg = g_error_mapping.get(_type, STR_ERROR_OTHER)

        if _type == SpawnUnsupported and os.name == POSIX and \
           not getScreen() and getDefaultStd():
            msg += ' ' + STR_SPAWN_UNSUPPORTED_SCREEN_SUFFIX

        if _type == UnknownServer and os.name == POSIX and \
           not getScreen() and getDefaultStd():
            msg += ' ' + STR_DISPLAY_ERROR

        _str = msg % {'type': _type, 'value': value, 'traceback': tback}
        self.m_printer(_str)

        if not _type in g_error_mapping:
            print_exception(_type, value, tback, True)
        return


    def __report_server_errors(self, errors, fsupress_pwd_warning = False):
        " Reports server error "
        for k, el in errors.items():
            if fsupress_pwd_warning and k in [BadVersion,
                                              AuthenticationBadData,
                                              AuthenticationFailure]:
                continue

            if k in [BadVersion]:
                for (tt, vv, tback) in el:
                    self.report_exception(tt, vv, None)
                continue

            (tt, vv, tback) = el[0]
            self.report_exception(tt, vv, tback)
        return


    def __attach(self, server, fsetenv):
        " Does attaching "
        self.__verify_unattached()

        session = CSession(self.m_host, server.m_port, self.m_rpdb2_pwd,
                           self.m_fAllowUnencrypted, self.m_rid)
        session.connect()

        if (session.getServerInfo().m_pid != server.m_pid) or \
           (session.getServerInfo().m_filename != server.m_filename):
            raise UnexpectedData

        self.m_session = session

        self.m_server_info = self.get_server_info()

        self.getSession().getProxy().set_synchronicity(self.m_fsynchronicity)
        self.getSession().getProxy().set_trap_unhandled_exceptions(self.m_ftrap)
        self.getSession().getProxy().set_fork_mode(self.m_ffork_into_child,
                                                   self.m_ffork_auto)

        if fsetenv and len(self.m_environment) != 0:
            self.getSession().getProxy().set_environ(self.m_environment)

        self.request_break()
        self.refresh(True)

        self.__start_event_monitor()

        print_debug('Attached to debuggee on port %d.' % session.m_port)

        #self.enable_breakpoint([], fAll = True)
        return


    def __verify_unattached(self):
        " Sanity check "
        if self.__is_attached():
            raise AlreadyAttached


    def __verify_attached(self):
        " Sanity check "
        if not self.__is_attached():
            raise NotAttached


    def __is_attached(self):
        " True if already attached "
        return (self.m_state_manager.get_state() != STATE_DETACHED) and \
               (self.m_session is not None)


    def __verify_broken(self):
        " Sanity check "
        if self.m_state_manager.get_state() not in [STATE_BROKEN,
                                                    STATE_ANALYZE]:
            raise DebuggerNotBroken


    def refresh(self, fSendUnhandled = False):
        " Refreshes "
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        self.m_remote_event_index = self.getSession().getProxy(). \
                                        sync_with_events(fAnalyzeMode,
                                                         fSendUnhandled)
        self.m_breakpoints_proxy.sync()
        return


    def __start_event_monitor(self):
        " Starts event monitor "
        self.m_fStop = False
        self.m_worker_thread = \
                    threading.Thread(target = self.__event_monitor_proc)
        #thread_set_daemon(self.m_worker_thread, True)
        self.m_worker_thread.start()
        return


    def __event_monitor_proc(self):
        " Event monitor procedure "
        self.m_worker_thread_ident = thread.get_ident()
        t_rate_last = 0
        nfailures = 0

        while not self.m_fStop:
            try:
                t_rate_last = controlRate(t_rate_last, IDLE_MAX_RATE)
                if self.m_fStop:
                    return

                (nn, sel) = self.getSession().getProxy().wait_for_event( \
                                                    PING_TIMEOUT,
                                                    self.m_remote_event_index)

                if True in [isinstance(e, CEventForkSwitch) for e in sel]:
                    print_debug('Received fork switch event.')

                    self.getSession().pause()
                    threading.Thread(target = self.restart_session_job).start()

                if True in [isinstance(e, CEventExecSwitch) for e in sel]:
                    print_debug('Received exec switch event.')

                    self.getSession().pause()
                    threading.Thread(target = self.restart_session_job,
                                     args = (True, )).start()

                if True in [isinstance(e, CEventExit) for e in sel]:
                    self.getSession().shut_down()
                    self.m_fStop = True

                if nn > self.m_remote_event_index:
                    #print >> sys.__stderr__, (nn, sel)
                    self.m_remote_event_index = nn
                    self.m_event_dispatcher_proxy.fire_events(sel)

                nfailures = 0

            except CConnectionException:
                if not self.m_fStop:
                    self.report_exception(*sys.exc_info())
                    threading.Thread(target = self.detach_job).start()

                return

            except socket.error:
                if nfailures < COMMUNICATION_RETRIES:
                    nfailures += 1
                    continue

                if not self.m_fStop:
                    self.report_exception(*sys.exc_info())
                    threading.Thread(target = self.detach_job).start()

                return


    def on_event_conflicting_modules(self, event):
        " On conflicting modules "
        modules = ', '.join(event.m_modules_list)
        self.m_printer(STR_CONFLICTING_MODULES % modules)
        return


    def on_event_signal_intercept(self, event):
        " On intercepting a signal "
        if self.m_state_manager.get_state() in [STATE_ANALYZE,
                                                STATE_BROKEN]:
            self.m_printer(STR_SIGNAL_INTERCEPT % \
                            (event.m_signame, event.m_signum))
        return


    def on_event_signal_exception(self, event):
        " On signal exception "
        self.m_printer(STR_SIGNAL_EXCEPTION % (event.m_description,
                                               event.m_signame,
                                               event.m_signum))
        return


    def on_event_embedded_sync(self, event):
        " On embedded sync "
        #
        # time.sleep() allows pending break requests to go through...
        #
        time.sleep(0.001)
        self.getSession().getProxy().embedded_sync()
        return


    def on_event_exit(self, event):
        " On exit event "
        self.m_printer(STR_DEBUGGEE_TERMINATED)
        threading.Thread(target = self.detach_job).start()
        return


    def restart_session_job(self, fSendExitOnFailure = False):
        " Restarts the session job "
        try:
            self.getSession().restart(sleep = 3)
            return

        except:
            pass

        self.m_fStop = True

        if fSendExitOnFailure:
            self.m_event_dispatcher_proxy.fire_event(CEventExit())
            return

        self.m_printer(STR_LOST_CONNECTION)
        self.detach_job()
        return


    def detach_job(self):
        " Detaches the job "
        try:
            self.detach()
        except:
            pass


    def detach(self):
        " Detaches the debuggee "
        self.__verify_attached()

        try:
            self.save_breakpoints()
        except:
            print_debug_exception()

        self.m_printer(STR_ATTEMPTING_TO_DETACH)

        self.m_state_manager.set_state(STATE_DETACHING)

        self.__stop_event_monitor()

        try:
            #self.disable_breakpoint([], fAll = True)

            try:
                self.getSession().getProxy(). \
                                    set_trap_unhandled_exceptions(False)
                self.request_go(fdetach = True)

            except DebuggerNotBroken:
                pass

        finally:
            self.m_state_manager.set_state(STATE_DETACHED)
            self.m_session = None
            self.m_printer(STR_DETACH_SUCCEEDED)
        return


    def __stop_event_monitor(self):
        " Stops event monitor "
        self.m_fStop = True
        if self.m_worker_thread is not None:
            if thread.get_ident() != self.m_worker_thread_ident:
                try:
                    self.getSession().getProxy().null()
                except:
                    pass

                self.m_worker_thread.join()

            self.m_worker_thread = None
            self.m_worker_thread_ident = None
        return


    def request_break(self):
        " Requests break "
        self.getSession().getProxy().request_break()
        return


    def request_go(self, fdetach = False):
        " Requests Go "
        self.getSession().getProxy().request_go(fdetach)
        return


    def request_go_breakpoint(self, filename, scope, lineno):
        " Requests go breakpoint "
        frame_index = self.get_frame_index()
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        self.getSession().getProxy().request_go_breakpoint(filename, scope,
                                                           lineno, frame_index,
                                                           fAnalyzeMode)
        return


    def request_step(self):
        " Requests step "
        self.getSession().getProxy().request_step()
        return


    def request_next(self):
        " Requests next "
        self.getSession().getProxy().request_next()
        return


    def request_return(self):
        " Requests return "
        self.getSession().getProxy().request_return()
        return


    def request_jump(self, lineno):
        " Requests jump "
        self.getSession().getProxy().request_jump(lineno)
        return


    def set_breakpoint(self, filename, scope, lineno, fEnabled,
                             expr, encoding = None):
        " Sets a breakpoint "
        frame_index = self.get_frame_index()
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        if encoding == None:
            encoding = self.m_encoding

        self.getSession().getProxy().set_breakpoint(filename, scope, lineno,
                                                    fEnabled, expr, frame_index,
                                                    fAnalyzeMode, encoding)
        return


    def disable_breakpoint(self, id_list, fAll):
        " Disables breakpoint "
        self.getSession().getProxy().disable_breakpoint(id_list, fAll)
        return


    def enable_breakpoint(self, id_list, fAll):
        " Enables breakpoint "
        self.getSession().getProxy().enable_breakpoint(id_list, fAll)
        return


    def delete_breakpoint(self, id_list, fAll):
        " Deletes breakpoint "
        self.getSession().getProxy().delete_breakpoint(id_list, fAll)
        return


    def get_breakpoints(self):
        " Provides breakpoints list "
        self.__verify_attached()

        return self.m_breakpoints_proxy.get_breakpoints()


    def save_breakpoints(self, filename = ''):
        " Saves breakpoints "
        self.__verify_attached()

        module_name = self.getSession().getServerInfo().m_module_name
        if module_name[:1] == '<':
            return

        if sys.platform == 'OpenVMS':
            #
            # OpenVMS filesystem does not support byte stream.
            #
            mode = 'w'
        else:
            mode = 'wb'

        path = calc_bpl_filename(module_name + filename)
        f = open(path, mode)

        try:
            try:
                bpl = self.get_breakpoints()
                sbpl = pickle.dumps(bpl)
                f.write(sbpl)

            except:
                print_debug_exception()
                raise CException

        finally:
            f.close()
        return


    def load_breakpoints(self, filename = ''):
        " Loads breakpoints "
        self.__verify_attached()

        module_name = self.getSession().getServerInfo().m_module_name
        if module_name[:1] == '<':
            return

        if sys.platform == 'OpenVMS':
            #
            # OpenVMS filesystem does not support byte stream.
            #
            mode = 'r'
        else:
            mode = 'rb'

        path = calc_bpl_filename(module_name + filename)
        f = open(path, mode)

        ferror = False

        try:
            try:
                bpl = pickle.load(f)
                self.delete_breakpoint([], True)

            except:
                print_debug_exception()
                raise CException

            #
            # No Breakpoints were found in file.
            #
            if filename == '' and len(bpl.values()) == 0:
                raise IOError

            for bpoint in bpl.values():
                try:
                    if bpoint.m_scope_fqn != None:
                        bpoint.m_scope_fqn = as_unicode(bpoint.m_scope_fqn)

                    if bpoint.m_filename != None:
                        bpoint.m_filename = as_unicode(bpoint.m_filename)

                    if bpoint.m_expr != None:
                        bpoint.m_expr = as_unicode(bpoint.m_expr)

                    if bpoint.m_expr in [None, '']:
                        bpoint.m_encoding = as_unicode('utf-8')

                    self.set_breakpoint(bpoint.m_filename, bpoint.m_scope_fqn,
                                        bpoint.m_scope_offset,
                                        bpoint.m_fEnabled,
                                        bpoint.m_expr, bpoint.m_encoding)
                except:
                    print_debug_exception()
                    ferror = True

            if ferror:
                raise CException

        finally:
            f.close()
        return

    def on_event_synchronicity(self, event):
        " On synchronicity "
        ffire = self.m_fsynchronicity != event.m_fsynchronicity
        self.m_fsynchronicity = event.m_fsynchronicity

        if ffire:
            event = CEventSynchronicity(event.m_fsynchronicity)
            self.m_event_dispatcher.fire_event(event)
        return


    def set_synchronicity(self, fsynchronicity):
        " Sets synchronicity "
        self.m_fsynchronicity = fsynchronicity

        if self.__is_attached():
            try:
                self.getSession().getProxy().set_synchronicity(fsynchronicity)
            except NotAttached:
                pass

        event = CEventSynchronicity(fsynchronicity)
        self.m_event_dispatcher.fire_event(event)
        return


    def get_synchronicity(self):
        " True if synchronized "
        return self.m_fsynchronicity


    def on_event_trap(self, event):
        " On trap event "
        ffire = self.m_ftrap != event.m_ftrap
        self.m_ftrap = event.m_ftrap

        if ffire:
            event = CEventTrap(event.m_ftrap)
            self.m_event_dispatcher.fire_event(event)
        return


    def set_trap_unhandled_exceptions(self, ftrap):
        " Sets trap unhandled exception "
        self.m_ftrap = ftrap

        if self.__is_attached():
            try:
                self.getSession().getProxy(). \
                        set_trap_unhandled_exceptions(self.m_ftrap)
            except NotAttached:
                pass

        event = CEventTrap(ftrap)
        self.m_event_dispatcher.fire_event(event)
        return


    def get_trap_unhandled_exceptions(self):
        " True if unhandled exceptions are trapped "
        return self.m_ftrap


    def is_unhandled_exception(self):
        " True if unhandled exception "
        self.__verify_attached()
        return self.getSession().getProxy().is_unhandled_exception()


    def on_event_fork_mode(self, event):
        " On fork event "
        ffire = ((self.m_ffork_into_child , self.m_ffork_auto) !=
            (event.m_ffork_into_child, event.m_ffork_auto))

        self.m_ffork_into_child = event.m_ffork_into_child
        self.m_ffork_auto = event.m_ffork_auto

        if ffire:
            event = CEventForkMode(self.m_ffork_into_child, self.m_ffork_auto)
            self.m_event_dispatcher.fire_event(event)
        return


    def set_fork_mode(self, ffork_into_child, ffork_auto):
        " Sets fork mode "
        self.m_ffork_into_child = ffork_into_child
        self.m_ffork_auto = ffork_auto

        if self.__is_attached():
            try:
                self.getSession().getProxy().set_fork_mode(
                    self.m_ffork_into_child,
                    self.m_ffork_auto
                    )

            except NotAttached:
                pass

        event = CEventForkMode(ffork_into_child, ffork_auto)
        self.m_event_dispatcher.fire_event(event)
        return


    def get_fork_mode(self):
        " Provides the current fork mode "
        return (self.m_ffork_into_child, self.m_ffork_auto)


    def get_stack(self, tid_list, fAll):
        " Provides stack "
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)
        return self.getSession().getProxy().get_stack(tid_list, fAll,
                                                      fAnalyzeMode)


    def get_source_file(self, filename, lineno, nlines):
        " Provides source file "
        assert(is_unicode(filename))

        frame_index = self.get_frame_index()
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        return self.getSession().getProxy().get_source_file(filename, lineno,
                                                            nlines, frame_index,
                                                            fAnalyzeMode)


    def get_source_lines(self, nlines, fAll):
        " Provides source lines "
        frame_index = self.get_frame_index()
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        return self.getSession().getProxy().get_source_lines(nlines, fAll,
                                                             frame_index,
                                                             fAnalyzeMode)


    def get_thread_list(self):
        " Provides threads list "
        (current_thread_id, \
         thread_list) = self.getSession().getProxy().get_thread_list()
        return (current_thread_id, thread_list)


    def set_thread(self, tid):
        " Sets thread "
        self.reset_frame_indexes(None)
        self.getSession().getProxy().set_thread(tid)
        return


    def get_namespace(self, nlist, filter_level, repr_limit):
        " Provides a namespace "
        frame_index = self.get_frame_index()
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        return self.getSession().getProxy().get_namespace(nlist, filter_level,
                                                          frame_index,
                                                          fAnalyzeMode,
                                                          repr_limit,
                                                          self.m_encoding,
                                                          self.m_fraw)


    def evaluate(self, expr, fclear_completions = True):
        " Evaluates the expression "
        assert(is_unicode(expr))

        self.__verify_attached()
        self.__verify_broken()

        frame_index = self.get_frame_index()
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        (value,
         warning,
         error) = self.getSession().getProxy().evaluate(expr, frame_index,
                                                        fAnalyzeMode,
                                                        self.m_encoding,
                                                        self.m_fraw)

        if fclear_completions:
            self.m_completions.clear()

        return (value, warning, error)


    def execute(self, suite):
        " Executes the suite "
        assert(is_unicode(suite))

        self.__verify_attached()
        self.__verify_broken()

        frame_index = self.get_frame_index()
        fAnalyzeMode = (self.m_state_manager.get_state() == STATE_ANALYZE)

        (warning,
         error) = self.getSession().getProxy().execute(suite, frame_index,
                                                       fAnalyzeMode,
                                                       self.m_encoding)

        self.m_completions.clear()

        return (warning, error)


    def set_encoding(self, encoding, fraw):
        " Sets encoding "
        if (self.m_encoding, self.m_fraw) == (encoding, fraw):
            return

        self.m_encoding = encoding
        self.m_fraw = fraw

        event = CEventEncoding(encoding, fraw)
        self.m_event_dispatcher.fire_event(event)

        if self.__is_attached():
            self.refresh()
        return


    def get_encoding(self):
        " Provides encoding "
        return (self.m_encoding, self.m_fraw)


    def set_host(self, host):
        " Sets host "
        self.__verify_unattached()

        try:
            if not is_unicode(host):
                host = host.decode('ascii')

            host.encode('ascii')

        except:
            raise BadArgument

        host = as_string(host, 'ascii') 

        try:
            socket.getaddrinfo(host, 0, 0, socket.SOCK_STREAM)

        except socket.gaierror:
            if host.lower() != LOCALHOST:
                raise

            #
            # Work-around for gaierror:
            #   (-8, 'Servname not supported for ai_socktype')
            #
            return self.set_host(LOOPBACK)

        self.m_host = host
        self.m_server_list_object = CServerList(host)
        return


    def get_host(self):
        " Provides the host "
        return as_unicode(self.m_host)


    def calc_server_list(self):
        " Calcs the server list "
        if self.m_rpdb2_pwd is None:
            raise UnsetPassword

        if getFirewallTest():
            firewall_test = CFirewallTest(self.get_remote())
            if not firewall_test.run():
                raise FirewallBlock
        else:
            print_debug('Skipping firewall test.')

        server_list = self.m_server_list_object.calcList(self.m_rpdb2_pwd,
                                                         self.m_rid)
        errors = self.m_server_list_object.get_errors()
        self.__report_server_errors(errors)

        return (server_list, errors)


    def get_server_info(self):
        " Provides the server info "
        return self.getSession().getServerInfo()


    def complete_expression(self, expr):
        " Completes the expression "
        match = re.search(
                r'(?P<unsupported> \.)? ' \
                 '(?P<match> ((?P<scope> (\w+\.)* \w+) \.)? ' \
                 '(?P<complete>\w*) $)',
                expr,
                re.U | re.X
                )

        if match == None:
            raise BadArgument

        dic = match.groupdict()

        unsupported, scope, complete = (dic['unsupported'], dic['scope'],
                                        dic['complete'])

        if unsupported != None:
            raise BadArgument

        if scope == None:
            _scope = as_unicode('list(globals().keys()) + ' \
                                'list(locals().keys()) + ' \
                                'list(_RPDB2_builtins.keys())')
        else:
            _scope = as_unicode('dir(%s)' % scope)

        if not _scope in self.m_completions:
            (val, warn, err) = self.evaluate(_scope, fclear_completions = False)
            if warn != '' or err != '':
                print_debug('evaluate() returned the following ' \
                            'warning/error: %s' % warn + err)
                return (expr, [])

            clist = list(set(eval(val)))
            if '_RPDB2_builtins' in clist:
                clist.remove('_RPDB2_builtins')
            self.m_completions[_scope] = clist

        completions = [attr for attr \
                            in self.m_completions[_scope] \
                            if attr.startswith(complete)]
        completions.sort()

        if complete == '':
            prefix = expr
        else:
            prefix = expr[:-len(complete)]

        return (prefix, completions)


    def _reset_frame_indexes(self, event):
        " Resets the frame indexes "
        self.reset_frame_indexes(None)
        return


    def reset_frame_indexes(self, event):
        " Resets frame indexes "
        try:
            self.m_state_manager.acquire()
            if event is None:
                self.__verify_broken()
            elif self.m_state_manager.get_state() in [STATE_BROKEN,
                                                      STATE_ANALYZE]:
                return

            self.m_stack_depth = None
            self.m_stack_depth_exception = None
            self.m_frame_index = 0
            self.m_frame_index_exception = 0

            self.m_completions.clear()

        finally:
            self.m_state_manager.release()
        return


    def set_stack_depth(self, event):
        " Sets the stack depth "
        try:
            self.m_state_manager.acquire()
            self.__verify_broken()

            self.m_stack_depth = event.m_stack_depth
            self.m_stack_depth_exception = event.m_stack_depth_exception
            self.m_frame_index = min(self.m_frame_index,
                                     self.m_stack_depth - 1)
            self.m_frame_index_exception = min(self.m_frame_index_exception,
                                               self.m_stack_depth_exception - 1)
        finally:
            self.m_state_manager.release()
        return


    def set_frame_index(self, frame_index):
        " Sets the frame index "
        try:
            self.m_state_manager.acquire()
            self.__verify_broken()

            if (frame_index < 0) or (self.m_stack_depth is None):
                return self.get_frame_index(fLock = False)

            if self.m_state_manager.get_state() == STATE_ANALYZE:
                self.m_frame_index_exception = \
                                    min(frame_index,
                                        self.m_stack_depth_exception - 1)
                sindex = self.m_frame_index_exception

            else:
                self.m_frame_index = min(frame_index, self.m_stack_depth - 1)
                sindex = self.m_frame_index
        finally:
            self.m_state_manager.release()

        event = CEventStackFrameChange(sindex)
        self.m_event_dispatcher.fire_event(event)

        event = CEventNamespace()
        self.m_event_dispatcher.fire_event(event)
        return sindex


    def get_frame_index(self, fLock = True):
        " Provides the frame index "
        try:
            if fLock:
                self.m_state_manager.acquire()

            self.__verify_attached()

            if self.m_state_manager.get_state() == STATE_ANALYZE:
                return self.m_frame_index_exception
            return self.m_frame_index

        finally:
            if fLock:
                self.m_state_manager.release()


    def set_analyze(self, fAnalyze):
        " Sets analyze "
        try:
            self.m_state_manager.acquire()

            if fAnalyze and (self.m_state_manager.get_state() != STATE_BROKEN):
                raise DebuggerNotBroken

            if (not fAnalyze) and \
               (self.m_state_manager.get_state() != STATE_ANALYZE):
                return

            state = [STATE_BROKEN, STATE_ANALYZE][fAnalyze]
            self.m_state_manager.set_state(state, fLock = False)
        finally:
            self.m_state_manager.release()

            self.refresh()
        return


    def getSession(self):
        " Provides session "
        self.__verify_attached()
        return self.m_session


    def get_state(self):
        " Provides state "
        return as_unicode(self.m_state_manager.get_state())


    def set_password(self, _rpdb2_pwd):
        " Sets a password "
        assert(is_unicode(_rpdb2_pwd))

        if not is_valid_pwd(_rpdb2_pwd):
            raise BadArgument

        try:
            self.m_state_manager.acquire()

            self.__verify_unattached()

            self.m_rpdb2_pwd = _rpdb2_pwd
        finally:
            self.m_state_manager.release()
        return


    def set_random_password(self):
        " Sets random password "
        try:
            self.m_state_manager.acquire()

            self.__verify_unattached()

            self.m_rpdb2_pwd = generate_random_password()
            self.m_printer(STR_RANDOM_PASSWORD)
        finally:
            self.m_state_manager.release()
        return


    def get_password(self):
        " Provides the password "
        return self.m_rpdb2_pwd


    def set_remote(self, fAllowRemote):
        " Sets remote "
        try:
            self.m_state_manager.acquire()

            self.__verify_unattached()

            self.m_fAllowRemote = fAllowRemote
        finally:
            self.m_state_manager.release()
        return


    def get_remote(self):
        " Provides remote "
        return self.m_fAllowRemote


    def set_environ(self, envmap):
        " Sets environment "
        self.m_environment = []

        try:
            for key, val in envmap:
                key = as_unicode(key, fstrict = True)
                val = as_unicode(val, fstrict = True)

                self.m_environment.append((key, val))
        except:
            raise BadArgument
        return


    def get_environ(self):
        " Provides environment "
        return self.m_environment


    def stop_debuggee(self):
        " Stops debuggee "
        self.__verify_attached()

        try:
            self.save_breakpoints()
        except:
            print_debug_exception()

        self.m_printer(STR_ATTEMPTING_TO_STOP)
        self.m_printer(STR_ATTEMPTING_TO_DETACH)

        self.m_state_manager.set_state(STATE_DETACHING)

        self.__stop_event_monitor()

        try:
            self.getSession().getProxy().stop_debuggee()
        finally:
            self.m_state_manager.set_state(STATE_DETACHED)
            self.m_session = None
            self.m_printer(STR_DETACH_SUCCEEDED)
        return


class CFirewallTest:
    " Firewall test "
    m_port = None
    m_thread_server = None
    m_thread_client = None
    m_lock = threading.RLock()


    def __init__(self, fremote = False, timeout = 4):
        if fremote:
            self.m_loopback = ''
        else:
            self.m_loopback = LOOPBACK

        self.m_timeout = timeout

        self.m_result = None

        self.m_last_server_error = None
        self.m_last_client_error = None
        return


    def run(self):
        " Runs the test "
        CFirewallTest.m_lock.acquire()

        try:
            #
            # If either the server or client are alive after a timeout
            # it means they are blocked by a firewall. Return False.
            #
            server = CFirewallTest.m_thread_server
            if server != None and thread_is_alive(server):
                server.join(self.m_timeout * 1.5)
                if thread_is_alive(server):
                    return False

            client = CFirewallTest.m_thread_client
            if client != None and thread_is_alive(client):
                client.join(self.m_timeout * 1.5)
                if thread_is_alive(client):
                    return False

            CFirewallTest.m_port = None
            self.m_result = None

            startTime = time.time()
            server = threading.Thread(target = self.__server)
            server.start()
            CFirewallTest.m_thread_server = server

            #
            # If server exited or failed to setup after a timeout 
            # it means it was blocked by a firewall.
            #
            while CFirewallTest.m_port == None and thread_is_alive(server):
                if time.time() - startTime > self.m_timeout * 1.5:
                    return False

                time.sleep(0.1)

            if not thread_is_alive(server):
                return False

            startTime = time.time()
            client = threading.Thread(target = self.__client)
            client.start()
            CFirewallTest.m_thread_client = client

            while self.m_result == None and thread_is_alive(client):
                if time.time() - startTime > self.m_timeout * 1.5:
                    return False

                time.sleep(0.1)

            return self.m_result

        finally:
            CFirewallTest.m_lock.release()


    def __client(self):
        " client what? "
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.m_timeout)

        try:
            try:
                sock.connect((LOOPBACK, CFirewallTest.m_port))

                sock.send(as_bytes('Hello, world'))
                # data = self.__recv(sock, 1024)
                self.__recv(sock, 1024)
                self.m_result = True

            except socket.error:
                excInfo = sys.exc_info()[1]
                self.m_last_client_error = excInfo
                self.m_result = False

        finally:
            sock.close()
        return

    def __server(self):
        " Server what? "
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.m_timeout)

        if os.name == POSIX:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        port = SERVER_PORT_RANGE_START

        while True:
            try:
                sock.bind((self.m_loopback, port))
                break

            except socket.error:
                ee = sys.exc_info()[1]

                if __GetSocketError(ee) != errno.EADDRINUSE:
                    self.m_last_server_error = ee
                    sock.close()
                    return

                if port >= SERVER_PORT_RANGE_START + \
                           SERVER_PORT_RANGE_LENGTH - 1:
                    self.m_last_server_error = ee
                    sock.close()
                    return

                port += 1

        CFirewallTest.m_port = port

        try:
            try:
                conn = None
                sock.listen(1)
                conn, addr = sock.accept()

                while True:
                    data = self.__recv(conn, 1024)
                    if not data:
                        return

                    conn.send(data)

            except socket.error:
                err = sys.exc_info()[1]
                self.m_last_server_error = err

        finally:
            if conn != None:
                conn.close()
            sock.close()
        return


    def __recv(self, sock, length):
        " Receive "
        startTime = time.time()

        while True:
            try:
                data = sock.recv(1024)
                return data

            except socket.error:
                excInfo = sys.exc_info()[1]
                if __GetSocketError(excInfo) != errno.EWOULDBLOCK:
                    print_debug('socket error was caught, %s' % repr(excInfo))
                    raise

                if time.time() - startTime > self.m_timeout:
                    raise

                continue


def __GetSocketError(excInfo):
    " Provides the socket error "
    if (not isinstance(excInfo.args, tuple)) or (len(excInfo.args) == 0):
        return -1

    return excInfo.args[0]



class CBreakPointsManagerProxy:
    """
    A proxy for the breakpoint manager.
    While the breakpoint manager resides on the debuggee (the server),
    the proxy resides in the debugger (the client - session manager)
    """

    def __init__(self, session_manager):
        self.m_session_manager = session_manager

        self.m_break_points_by_file = {}
        self.m_break_points_by_id = {}

        self.m_lock = threading.Lock()

        #
        # The breakpoint proxy inserts itself between the two chained
        # event dispatchers in the session manager.
        #

        event_type_dict = {CEventBreakpoint: {}}

        self.m_session_manager.m_event_dispatcher_proxy. \
                        register_callback(self.update_bp,
                                          event_type_dict, fSingleUse = False)
        self.m_session_manager.m_event_dispatcher. \
                        register_chain_override(event_type_dict)


    def update_bp(self, event):
        """
        Handle breakpoint updates that arrive via the event dispatcher.
        """

        try:
            self.m_lock.acquire()

            if event.m_fAll:
                id_list = list(self.m_break_points_by_id.keys())
            else:
                id_list = event.m_id_list

            if event.m_action == CEventBreakpoint.REMOVE:
                for iD in id_list:
                    try:
                        bp = self.m_break_points_by_id.pop(iD)
                        bpm = self.m_break_points_by_file[bp.m_filename]
                        del bpm[bp.m_lineno]
                        if len(bpm) == 0:
                            del self.m_break_points_by_file[bp.m_filename]
                    except KeyError:
                        pass
                return

            if event.m_action == CEventBreakpoint.DISABLE:
                for iD in id_list:
                    try:
                        bp = self.m_break_points_by_id[iD]
                        bp.disable()
                    except KeyError:
                        pass
                return

            if event.m_action == CEventBreakpoint.ENABLE:
                for iD in id_list:
                    try:
                        bp = self.m_break_points_by_id[iD]
                        bp.enable()
                    except KeyError:
                        pass
                return

            bpm = self.m_break_points_by_file.get(event.m_bp.m_filename, {})
            bpm[event.m_bp.m_lineno] = event.m_bp

            self.m_break_points_by_id[event.m_bp.m_id] = event.m_bp

        finally:
            self.m_lock.release()

            self.m_session_manager.m_event_dispatcher.fire_event(event)


    def sync(self):
        " Synchronize "
        try:
            self.m_lock.acquire()

            self.m_break_points_by_file = {}
            self.m_break_points_by_id = {}

        finally:
            self.m_lock.release()

        break_points_by_id = \
                self.m_session_manager.getSession().getProxy().get_breakpoints()

        try:
            self.m_lock.acquire()

            self.m_break_points_by_id.update(break_points_by_id)

            for bp in list(self.m_break_points_by_id.values()):
                bpm = self.m_break_points_by_file.get(bp.m_filename, {})
                bpm[bp.m_lineno] = bp

        finally:
            self.m_lock.release()


    def clear(self):
        " Clears breakpoints "
        try:
            self.m_lock.acquire()

            self.m_break_points_by_file = {}
            self.m_break_points_by_id = {}

        finally:
            self.m_lock.release()


    def get_breakpoints(self):
        " Provides breakpoints "
        return self.m_break_points_by_id


    def get_breakpoint(self, filename, lineno):
        " Provides a breakpoint "
        bpm = self.m_break_points_by_file[filename]
        return bpm[lineno]

