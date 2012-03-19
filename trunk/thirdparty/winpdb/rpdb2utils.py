
" Various utility functions "


import sys
import locale
import codecs
import time
import os
import random
import zipfile
import zipimport

#
# Pre-Import needed by my_abspath1
#
try:
    from nt import _getfullpathname
except ImportError:
    pass

from rpdb2globals import PYTHON_FILE_EXTENSION, PYTHONW_FILE_EXTENSION, \
                         PYTHONW_SO_EXTENSION, getInitialCwd, \
                         getFoundUnicodeFiles, updateFoundUnicodeFiles


RPDB_VERSION = "RPDB_2_4_8"
RPDB_COMPATIBILITY_VERSION = "RPDB_2_4_0"
POSIX = 'posix'

RPDB_SETTINGS_FOLDER = '.rpdb2_settings'
RPDB_PWD_FOLDER = os.path.join(RPDB_SETTINGS_FOLDER, 'passwords')
RPDB_BPL_FOLDER = os.path.join(RPDB_SETTINGS_FOLDER, 'breakpoints')
RPDB_BPL_FOLDER_NT = 'rpdb2_breakpoints'



def get_version():
    " Provides rpdb2 version "
    return RPDB_VERSION


def get_interface_compatibility_version():
    " Provides the rpdb2 compatibility version "
    return RPDB_COMPATIBILITY_VERSION



def is_py3k():
    " True if it is python 3 "
    return sys.version_info[0] >= 3


def is_unicode(string):
    " True if it is a unicode string "
    if is_py3k() and type(string) == str:
        return True

    return type(string) == unicode


def as_unicode(string, encoding = 'utf-8', fstrict = False):
    " Provides unicode string "
    if is_unicode(string):
        return string

    if fstrict:
        return string.decode(encoding)
    return string.decode(encoding, 'replace')


def as_bytes(string, encoding = 'utf-8', fstrict = True):
    " Provides bytes "
    if not is_unicode(string):
        return string

    if fstrict:
        return string.encode(encoding)
    return string.encode(encoding, 'replace')


def as_string(string, encoding = 'utf-8', fstrict = False):
    " Provides a string "
    if is_py3k():
        if is_unicode(string):
            return string

        if fstrict:
            return string.decode(encoding)
        return string.decode(encoding, 'replace')

    if not is_unicode(string):
        return string

    if fstrict:
        return string.encode(encoding)
    return string.encode(encoding, 'replace')



ENCODING_AUTO = as_unicode('auto')





def safe_str(value):
    " Safe str() "
    try:
        return str(value)
    except:
        return 'N/A'


def safe_repr(value):
    " Safe repr() "
    try:
        return repr(value)
    except:
        return 'N/A'


def detect_locale():
    " Detects locale "
    encoding = locale.getdefaultlocale()[1]

    if encoding == None:
        return 'ascii'

    try:
        codecs.lookup(encoding)
        return encoding
    except:
        pass

    if encoding.lower().startswith('utf_8'):
        return 'utf-8'

    return 'ascii'


def detect_encoding(fileobj):
    " Provides encoding "
    try:
        encoding = fileobj.encoding
        if encoding == None:
            return detect_locale()
    except:
        return detect_locale()

    try:
        codecs.lookup(encoding)
        return encoding
    except:
        pass

    if encoding.lower().startswith('utf_8'):
        return 'utf-8'
    return 'ascii'


def safe_wait(lock, timeout = None):
    '''
    # workaround windows bug where signal handlers might raise exceptions
    # even if they return normally.
    '''

    while True:
        try:
            startTime = time.time()
            return lock.wait(timeout)

        except:
            if timeout == None:
                continue

            timeout -= (time.time() - startTime)
            if timeout <= 0:
                return
    return


def lock_notify_all(lock):
    try:
        if is_py3k():
            return lock.notify_all()

    except AttributeError:
        pass

    return lock.notifyAll()


def _print(string, f = sys.stdout, feol = True):
    " Prints the given string "
    string = as_unicode(string)

    encoding = detect_encoding(f)

    string = as_bytes(string, encoding, fstrict = False)
    string = as_string(string, encoding)

    if feol:
        f.write(string + '\n')
    else:
        f.write(string)
    return


def thread_is_alive(thread):
    " True if thread is alive "
    try:
        if is_py3k():
            return thread.is_alive()
    except AttributeError:
        pass
    return thread.isAlive()


def create_rpdb_settings_folder():
    """
    Create the settings folder on Posix systems:
    '~/.rpdb2_settings' with mode 700.
    """

    if os.name != POSIX:
        return

    home = os.path.expanduser('~')

    rsf = os.path.join(home, RPDB_SETTINGS_FOLDER)
    if not os.path.exists(rsf):
        os.mkdir(rsf, int('0700', 8))

    pwds = os.path.join(home, RPDB_PWD_FOLDER)
    if not os.path.exists(pwds):
        os.mkdir(pwds, int('0700', 8))

    bpl = os.path.join(home, RPDB_BPL_FOLDER)
    if not os.path.exists(bpl):
        os.mkdir(bpl, int('0700', 8))
    return



def calc_pwd_file_path(rid):
    """
    Calc password file path for Posix systems:
    '~/.rpdb2_settings/<rid>'
    """
    home = os.path.expanduser('~')
    rsf = os.path.join(home, RPDB_PWD_FOLDER)
    return os.path.join(rsf, rid)



def read_pwd_file(rid):
    """
    Read password from password file for Posix systems.
    """

    assert(os.name == POSIX)

    path = calc_pwd_file_path(rid)

    f = open(path, 'r')
    _rpdb2_pwd = f.read()
    f.close()

    return as_unicode(_rpdb2_pwd, fstrict = True)



def delete_pwd_file(rid):
    """
    Delete password file for Posix systems.
    """

    if os.name != POSIX:
        return

    path = calc_pwd_file_path(rid)
    try:
        os.remove(path)
    except:
        pass
    return


def calcURL(host, port):
    """
    Form HTTP URL from 'host' and 'port' arguments.
    """
    return "http://" + str(host) + ":" + str(port)


def is_valid_pwd(_rpdb2_pwd):
    " True if the password is valid "
    if _rpdb2_pwd in [None, '']:
        return False

    try:
        if not is_unicode(_rpdb2_pwd):
            _rpdb2_pwd = _rpdb2_pwd.decode('ascii')

        _rpdb2_pwd.encode('ascii')
    except:
        return False

    for char in _rpdb2_pwd:
        if char.isalnum():
            continue
        if char == '_':
            continue
        return False
    return True


def getcwdu():
    " Provides the current working directory "
    if hasattr(os, 'getcwdu'):
        return os.getcwdu()
    return os.getcwd()


def generate_rid():
    " Return a 7 digits random id "
    rid = repr(random.randint(1000000, 9999999))
    return as_unicode(rid)


def getGPLLicense():
    " Reads the GPL text from a file and returns it "
    if os.path.isabs( __file__ ):
        absPath = __file__
    else:
        absPath = os.path.normpath( os.getcwd() + os.path.sep + __file__ )

    licFile = os.path.dirname( absPath ) + os.path.sep + "rpdb2gpl.txt"
    try:
        f = open( licFile )
        content = f.read()
        f.close()
        return content
    except:
        return "Could not find license file: " + licFile


def winlower( path ):
    """
    return lowercase version of 'path' on NT systems.

    On NT filenames are case insensitive so lowercase filenames
    for comparison purposes on NT.
    """
    if os.name == 'nt':
        return path.lower()
    return path


def calcScriptName(filename, fAllowAnyExt = True):
    " Provides the script name "
    if filename.endswith(PYTHON_FILE_EXTENSION):
        return filename

    if filename.endswith(PYTHONW_FILE_EXTENSION):
        return filename

    if filename.endswith(PYTHONW_SO_EXTENSION):
        scriptname = filename[:-3] + PYTHON_FILE_EXTENSION
        return scriptname

    if filename[:-1].endswith(PYTHON_FILE_EXTENSION):
        scriptname = filename[:-1]
        return scriptname

    if fAllowAnyExt:
        return filename

    return filename + PYTHON_FILE_EXTENSION


def findFileAsModule(filename):
    " Searches for the file name as if it were a module "

    lowered = winlower(filename)
    (root, ext) = os.path.splitext(lowered)

    root_dotted = root.replace('\\', '.').replace('/', '.').replace(':', '.')

    match_list = []
    for (module_name, mod) in list(sys.modules.items()):
        lowered_module_name = winlower(module_name)
        if (root_dotted + '.').startswith(lowered_module_name + '.'):
            match_list.append((len(module_name), module_name))

            if lowered_module_name == root_dotted:
                break

    match_list.sort()
    match_list.reverse()

    for (matched_len, matched_module) in match_list:
        try:
            module_dir = findModuleDir(matched_module)
        except IOError:
            continue

        suffix = root[matched_len:]
        if suffix == '':
            path = module_dir + ext
        else:
            path = my_os_path_join(module_dir, suffix.strip('\\')) + ext

        scriptname = calcScriptName(path, fAllowAnyExt = False)
        if myisfile(scriptname):
            return scriptname

        #
        # Check .pyw files
        #
        scriptname += 'w'
        if scriptname.endswith(PYTHONW_FILE_EXTENSION) and myisfile(scriptname):
            return scriptname

    raise IOError


def findModuleDir(module_name):
    " Searches for a module directory "
    if module_name == '':
        raise IOError

    dot_index = module_name.rfind('.')
    if dot_index != -1:
        parent = module_name[: dot_index]
        child = module_name[dot_index + 1:]
    else:
        parent = ''
        child = module_name

    mod = sys.modules[module_name]

    if not hasattr(mod, '__file__') or mod.__file__ == None:
        parent_dir = findModuleDir(parent)
        module_dir = my_os_path_join(parent_dir, winlower(child))
        return module_dir

    if not os.path.isabs(mod.__file__):
        parent_dir = findModuleDir(parent)
        module_dir = my_os_path_join(parent_dir, winlower(child))
        return module_dir

    (root, ext) = os.path.splitext(mod.__file__)
    if root.endswith('__init__'):
        root = os.path.dirname(root)

    abspath = my_abspath(root)
    lowered = winlower(abspath)

    return lowered



def myisfile(path):
    """ myisfile() is similar to os.path.isfile()
        but also works with Python eggs """
    try:
        mygetfile(path, False)
        return True
    except:
        return False



def mygetfile(path, fread_file = True):
    " Read a file even if inside a Python egg "
    if os.path.isfile(path):
        if not fread_file:
            return

        if sys.platform == 'OpenVMS':
            #
            # OpenVMS filesystem does not support byte stream.
            #
            mode = 'r'
        else:
            mode = 'rb'

        f = open(path, mode)
        data = f.read()
        f.close()
        return data

    dname = os.path.dirname(path)

    while True:
        if os.path.exists(dname):
            break

        _dname = os.path.dirname(dname)
        if _dname in [dname, '']:
            raise IOError

        dname = _dname

    if not zipfile.is_zipfile(dname):
        raise IOError

    z_imp = zipimport.zipimporter(dname)

    try:
        data = z_imp.get_data(path[len(dname) + 1:])
        return data

    except:
        raise IOError


def my_abspath(path):
    """
    We need our own little version of os.path.abspath since the original
    code imports modules in the 'nt' code path which can cause our debugger
    to deadlock in unexpected locations.
    """

    if path[:1] == '<':
        #
        # 'path' may also be '<stdin>' in which case it is left untouched.
        #
        return path

    if os.name == 'nt':
        return my_abspath1(path)

    return  os.path.abspath(path)



def my_abspath1(path):
    """
    Modification of ntpath.abspath() that avoids doing an import.
    """

    if path:
        try:
            path = _getfullpathname(path)
        except WindowsError:
            pass
    else:
        try:
            path = os.getcwd()

        except UnicodeDecodeError:
            #
            # This exception can be raised in py3k (alpha) on nt.
            #
            path = getcwdu()

    normp = os.path.normpath(path)

    if (len(normp) >= 2) and (normp[1:2] == ':'):
        normp = normp[:1].upper() + normp[1:]

    return normp


def my_os_path_join(dirname, basename):
    " Custom version of os.path.join() "
    if is_py3k() or (type(dirname) == str and type(basename) == str):
        return os.path.join(dirname, basename)

    encoding = sys.getfilesystemencoding()

    if type(dirname) == str:
        dirname = dirname.decode(encoding)

    if type(basename) == str:
        basename = basename.decode(encoding)

    return os.path.join(dirname, basename)




def findFile( filename, sources_paths = [],
              fModules = False, fAllowAnyExt = True ):
    """
    findFile looks for the full path of a script in a rather non-strict
    and human like behavior.

    ENCODING:
    filename should be either Unicode or encoded with sys.getfilesystemencoding()!
    Returned value is encoded with sys.getfilesystemencoding().

    It will always look for .py or .pyw files even if a .pyc or no
    extension is given.

    1. It will check against loaded modules if asked.
    1. full path (if exists).
    2. sources_paths.
    2. current path.
    3. PYTHONPATH
    4. PATH
    """

    if filename in getFoundUnicodeFiles():
        return filename

    if filename.startswith('<'):
        raise IOError

    filename = filename.strip('\'"')
    filename = os.path.expanduser(filename)

    if fModules and not (os.path.isabs(filename) or filename.startswith('.')):
        try:
            return winlower(findFileAsModule(filename))
        except IOError:
            pass

    if fAllowAnyExt:
        try:
            abspath = findFile(
                            filename,
                            sources_paths,
                            fModules = False,
                            fAllowAnyExt = False
                            )
            return abspath
        except IOError:
            pass

    if os.path.isabs(filename) or filename.startswith('.'):
        try:
            scriptname = None

            abspath = my_abspath(filename)
            lowered = winlower(abspath)
            scriptname = calcScriptName(lowered, fAllowAnyExt)

            if myisfile(scriptname):
                return scriptname

            #
            # Check .pyw files
            #
            scriptname += 'w'
            if scriptname.endswith(PYTHONW_FILE_EXTENSION) and \
               myisfile(scriptname):
                return scriptname

            scriptname = None
            raise IOError

        finally:
            if not is_py3k() and is_unicode(scriptname):
                fse = sys.getfilesystemencoding()
                val = as_string(scriptname, fse)
                if '?' in val:
                    updateFoundUnicodeFiles(val, scriptname)
                return val

    scriptname = calcScriptName(filename, fAllowAnyExt)

    try:
        cwd = [os.getcwd(), getcwdu()]

    except UnicodeDecodeError:
        #
        # This exception can be raised in py3k (alpha) on nt.
        #
        cwd = [getcwdu()]

    env_path = os.environ['PATH']
    paths = sources_paths + cwd + getInitialCwd() + \
            sys.path + env_path.split(os.pathsep)

    try:
        lowered = None

        for path in paths:
            f = my_os_path_join(path, scriptname)
            abspath = my_abspath(f)
            lowered = winlower(abspath)

            if myisfile(lowered):
                return lowered

            #
            # Check .pyw files
            #
            lowered += 'w'
            if lowered.endswith(PYTHONW_FILE_EXTENSION) and myisfile(lowered):
                return lowered

        lowered = None
        raise IOError

    finally:
        if not is_py3k() and is_unicode(lowered):
            fse = sys.getfilesystemencoding()
            _low = as_string(lowered, fse)
            if '?' in _low:
                updateFoundUnicodeFiles(_low, lowered)
            return _low




