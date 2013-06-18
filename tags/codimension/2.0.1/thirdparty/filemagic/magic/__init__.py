"""File type identification using libmagic.

The magic.Magic class provides a high level API to the libmagic library.

    >>> import magic
    >>> with magic.Magic() as m:
    ...     m.id_filename('setup.py')
    ...
    'ASCII text'

Instances of magic.Magic support the context manager protocol (the 'with'
statement). If not used, the close() method must be called to free resources
allocated by libmagic.

See http://filemagic.readthedocs.org for detailed documentation.
"""
from magic.flags import *
from magic.identify import Magic, MagicError
from magic.version import __version__
