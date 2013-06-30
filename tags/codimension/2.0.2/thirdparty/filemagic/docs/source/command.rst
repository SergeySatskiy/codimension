Command Line Invocation
=======================

*filemagic* can be invoked from the command line by running the
:mod:`magic.command` module as a script. Pass ``-h`` or ``--help`` to print
usage information. ::

    $ python -m magic.command --help
    Usage: python -m magic [options] file ...

    Options:
      -h, --help            show this help message and exit
      -m PATHS, --magic=PATHS
                            A colon separated list of magic files to use
      --json                Format output in JSON

One or more files can be passed to be identified. The textual description,
mimetype and encoding type will be printed beneath each file's name.::

    $ python -m magic.command setup.py 
    setup.py
        Python script, ASCII text executable
        text/x-python
        us-ascii

The output can also be rendered in machine parseable `JSON
<http://en.wikipedia.org/wiki/JSON>`_ instead of the simple textual description
of above.. ::

    $ python -m magic.command --json setup.py 
    {
      "setup.py": {
        "textual": "Python script, ASCII text executable", 
        "mimetype": "text/x-python", 
        "encoding": "us-ascii"
      }
    }

The :mod:`magic.command` module is not intended to be a replacement for the
*file* command. 
