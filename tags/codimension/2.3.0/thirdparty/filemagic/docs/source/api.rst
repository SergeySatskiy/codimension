The filemagic API
=================

.. module:: magic
    :noindex:

Importing the :mod:`magic` module provides access to all *filemagic* primitives.
Most importantly the :class:`~magic.Magic` class.

Exceptions
----------

If something goes with *libmagic*, an exception will be raised.

.. module:: magic.api
    :noindex:

.. exception:: MagicError(errno, error)

    ``errno`` is the numerical error code returned by *libmagic*. ``error`` is
    the textual description of that error code, as supplied by *libmagic*.

:exc:`~magic.MagicError` inherits from ``EnvironmentError``.

Classes
-------

The :class:`~magic.Magic` class supports `context managers
<http://docs.python.org/library/stdtypes.html#context-manager-types>`_, meaning
it can be used with the ``with`` statement. Using the ``with`` statement is the
recommended usage as failing to call :meth:`~magic.Magic.close` will leak
resources. See :ref:`usage` for guidance.

.. module:: magic
    :noindex:

.. class:: Magic([paths, flags])

    Instances of this class provide access to *libmagics*'s file identification
    capabilities. Multiple instances may exist, each instance is independant
    from the others.

    To supply a custom list of magic database files instead of letting libmagic
    search the default paths, supply a list of filenames using the paths
    argument. These filenames may be unicode string as described in
    :ref:`unicode`.

    By default *flags* is :data:`magic.MAGIC_MIME_TYPE` which requests default
    behaviour from *libmagic*. This behaviour can be controlled by passing
    alternative :ref:`constants` for flags.

    .. method:: id_filename(filename)

        Identify a file from a given filename. The file will be opened by
        *libmagic*, reading sufficient contents to complete the identification.

    .. method:: id_buffer(buffer)

        Identify a file from the contents of a string or buffer.

    .. method:: close()

       Release any resources held by *libmagic*. This will be called
       automatically when a context manager exists.

    .. method:: list()

        Prints a list of magic entries to standard out. There is no return
        value. It's mostly intended for debugging.

    .. attribute:: consistent

        This property will be ``True`` if the magic database files loaded by
        libmagic are consistent.

This class encapsulates the low level ctypes api from :mod:`magic.api` that
interfaces directly with *libmagic*. It's not expected that the user would want
to do this.

If you do not know if *libmagic* is available, refer to the :ref:`installation`
section of the guide.

.. _constants:

Constants
---------

.. module:: magic.api
    :noindex:

.. data:: MAGIC_NONE

    Default flag for :class:`magic.Magic` that requests default behaviour from
    *libmagic*.

.. data:: MAGIC_MIME_TYPE

    Supply to :class:`magic.Magic` constructor to return mime type instead of
    textual description.

.. data:: MAGIC_MIME_ENCODING

    Supply to :class:`magic.Magic` constructor to return mime encoding instead
    of textual description.
