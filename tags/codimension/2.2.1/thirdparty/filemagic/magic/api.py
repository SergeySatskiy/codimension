"""File type identification using libmagic.

A ctypes Python wrapper for the libmagic library.

See libmagic(3) for low level details.
"""
import ctypes.util
import ctypes
import platform
import warnings

libname = ctypes.util.find_library('magic')
if not libname:
    if platform.system() == 'SunOS':
        libname = 'libmagic.so'
        warnings.warn("ctypes.util.find_library does not function as "
                      "expected on Solaris; manually setting libname to {0}. "
                      "If import fails, verify that libmagic is installed "
                      "to a directory registered with crle. ".format(libname),
                      ImportWarning)
    else:
        raise ImportError('Unable to find magic library')

try:
    lib = ctypes.CDLL(libname)
except Exception:
    raise ImportError('Loading {0} failed'.format(libname))


# magic_t type
class Cookie(ctypes.Structure):
    "Magic data structure"

c_cookie_p = ctypes.POINTER(Cookie)


# error handling
class MagicError(EnvironmentError):
    "Error occured inside libmagic"


def errcheck_int(result, func, arguments):
    "Raise an error if return integer is less than 0"
    if result < 0:
        cookie = arguments[0]
        errno = magic_errno(cookie)
        error = magic_error(cookie)
        raise MagicError(errno, error)
    return result


def errcheck_null(result, func, arguments):
    "Raise an error if the return pointer is NULL"
    if not result:
        cookie = arguments[0]
        errno = magic_errno(cookie)
        error = magic_error(cookie)
        raise MagicError(errno, error)
    return result

# dynamically load library
lib.magic_open.argtypes = [ctypes.c_int]
lib.magic_open.restype = c_cookie_p
lib.magic_open.err_check = errcheck_null
magic_open = lib.magic_open

lib.magic_close.argyptes = [c_cookie_p]
lib.magic_close.restype = None
magic_close = lib.magic_close

lib.magic_error.argyptes = [c_cookie_p]
lib.magic_error.restype = ctypes.c_char_p
magic_error = lib.magic_error

lib.magic_errno.argyptes = [c_cookie_p]
lib.magic_errno.restype = ctypes.c_int
magic_errno = lib.magic_errno

lib.magic_file.argyptes = [c_cookie_p, ctypes.c_char_p]
lib.magic_file.restype = ctypes.c_char_p
lib.magic_file.errcheck = errcheck_null
magic_file = lib.magic_file

lib.magic_buffer.argyptes = [c_cookie_p, ctypes.c_void_p, ctypes.c_size_t]
lib.magic_buffer.restype = ctypes.c_char_p
lib.magic_buffer.errcheck = errcheck_null
magic_buffer = lib.magic_buffer

lib.magic_setflags.argyptes = [c_cookie_p, ctypes.c_int]
lib.magic_setflags.restype = ctypes.c_int
lib.magic_setflags.errcheck = errcheck_int
magic_setflags = lib.magic_setflags

lib.magic_check.argyptes = [c_cookie_p, ctypes.c_char_p]
lib.magic_check.restype = ctypes.c_int
lib.magic_check.errcheck = errcheck_int
magic_check = lib.magic_check

lib.magic_compile.argyptes = [c_cookie_p, ctypes.c_char_p]
lib.magic_compile.restype = ctypes.c_int
lib.magic_compile.errcheck = errcheck_int
magic_compile = lib.magic_compile

lib.magic_load.argyptes = [c_cookie_p, ctypes.c_char_p]
lib.magic_load.restype = ctypes.c_int
lib.magic_load.errcheck = errcheck_int
magic_load = lib.magic_load

try:
    lib.magic_list.argyptes = [c_cookie_p, ctypes.c_char_p]
    lib.magic_list.restype = ctypes.c_int
    lib.magic_list.errcheck = errcheck_int
    magic_list = lib.magic_list
except AttributeError:
    pass
