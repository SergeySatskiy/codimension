"""Compatability wrapper between str and unicode."""
import sys
from functools import wraps

if sys.version_info[0] >= 3:
    unicode_t = str
    bytes_t = bytes
    decode_result = True
else:
    unicode_t = unicode
    bytes_t = str
    decode_result = False


def byte_args(positions):
    """Ensure argument at given position is a byte string.

    Will encode a unicode string to byte string if necessary.
    """
    def decorator(func):
        ordinals = set(positions)
        @wraps(func)
        def wrapper(*args, **kwargs):
            def encoder(args):
                for pos, arg in enumerate(args):
                    if pos in ordinals and isinstance(arg, unicode_t):
                        yield arg.encode()
                    else:
                        yield arg
            return func(*encoder(args), **kwargs)
        return wrapper
    return decorator


def iter_encode(iterable):
    """Iterate over sequence encoding all unicode elements.

    Non-unicode elements are yields unchanged.
    """
    for item in iterable:
        if isinstance(item, unicode_t):
            item = item.encode()
        yield item


def str_return(func):
    """Decode return result to unicode on Python3.

    Does nothing on Python 2.
    """
    if not decode_result:
        return func
    @wraps(func)
    def wrapper(*args, **kwargs):
        value = func(*args, **kwargs)
        return value.decode()
    return wrapper
