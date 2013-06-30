"""File type identification using libmagic.

A ctypes Python wrapper for libmagic library.

See libmagic(3) for low level details.
"""
from functools import wraps
import warnings
import weakref

try:
    from builtins import ResourceWarning as CleanupWarning
except ImportError:
    from exceptions import RuntimeWarning as CleanupWarning

from magic import api
from magic.api import MagicError
from magic.flags import MAGIC_NONE
from magic.compatability import byte_args, iter_encode, str_return


def raise_if_none(attrname, exception, message):
    "Raise an exception if the instance attribute is None."
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if getattr(self, attrname) is None:
                raise exception(message)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class Magic(object):
    """Identify and describe files using libmagic magic numbers.

    Manages the resources for libmagic. Provides two methods for identifying
    file contents.

     - id_buffer, identifies the contents of the buffer
     - id_filename, identifies the contents of the named file

    To get mime types rather than textual descriptions, pass the flag
    MAGIC_MIME_TYPE to the contructor. To get the encoding pass
    MAGIC_MIME_ENCODING.
    """

    def __init__(self, paths=None, flags=MAGIC_NONE):
        """Open and initialise resources from libmagic.

        ``paths`` is a list of magic database files to load.  If None, the
        default database will be loaded. For details on the magic database file
        see magic(5).

        ``flags`` controls how libmagic should behave. See libmagic(3) for
        details of these flags.
        """
        self._repr = "Magic(paths={0!r}, flags={1!r})".format(paths, flags)
        cookie = api.magic_open(flags)
        def cleanup(_):
            warnings.warn("Implicitly cleaning up {0!r}".format(cookie),
                    CleanupWarning)
            api.magic_close(cookie)
        self.weakref = weakref.ref(self, cleanup)
        self.cookie = cookie
        pathstr = b':'.join(iter_encode(paths)) if paths else None
        try:
            api.magic_load(self.cookie, pathstr)
        except MagicError:
            self.close()
            raise

    def __enter__(self):
        "__enter__() -> self."
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        "__exit__(*excinfo) -> None.  Closes libmagic resources."
        self.close()

    def __repr__(self):
        "x.__repr__() <==> repr(x)"
        return self._repr

    def close(self):
        "Close any resources opened by libmagic"
        if self.cookie:
            api.magic_close(self.cookie)
            del self.weakref
        self.cookie = None

    @property
    @raise_if_none('cookie', MagicError, 'object has already been closed')
    def consistent(self):
        "True if magic database is consistent"
        return api.magic_check(self.cookie, None) >= 0

    @raise_if_none('cookie', MagicError, 'object has already been closed')
    @byte_args(positions=[1])
    @str_return
    def id_buffer(self, buffer):
        "Return a textual description of the contents of buffer"
        return api.magic_buffer(self.cookie,
                api.ctypes.c_char_p(buffer),
                len(buffer))

    @raise_if_none('cookie', MagicError, 'object has already been closed')
    @byte_args(positions=[1])
    @str_return
    def id_filename(self, filename):
        "Return a textual description of the contents of the file"
        return api.magic_file(self.cookie, filename)

    @raise_if_none('cookie', MagicError, 'object has already been closed')
    def list(self, paths=None):
        "Print list of magic strings"
        pathstr = b':'.join(iter_encode(paths)) if paths else None
        try:
            api.magic_list(self.cookie, pathstr)
        except AttributeError:
            msg = 'list is not supported on this version of libmagic'
            raise MagicError(msg)
