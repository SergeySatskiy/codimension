.. filemagic documentation master file, created by
   sphinx-quickstart on Wed Mar 14 21:50:10 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introducing filemagic
=====================

*filemagic* provides a Python API for *libmagic*, the library behind Unix
*file* command. It enables the Python developer to easilty test for file types
from the extensive identification library that is shipped with *libmagic*.

    "Any sufficiently advanced technology is indistinguishable from magic."

    -- Arthur C. Clark, 1961

.. The *file* command and *libmagic* have been maintained since August, 1987. It's predecessor dates back to Bell Labs UNIX from 1973.

Features
========

* Simple, Python API.
* Identifies named files or strings.
* Return a textual description, mime type or mime encoding.
* Provide custom magic files to customize file detection.
* Support for both Python2 and Python3.
* Support for both CPython and PyPy.

Table of Contents
=================

.. toctree::
    :maxdepth: 2

    guide
    command
    api

Issues
======

If you encounter problems, please refer to :ref:`issues` from the guide.
