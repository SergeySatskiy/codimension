""" doctestsw - used to globally set/unset doctest testing.

This switch is needed because the standard doctest can not handle
raise statements with arguments. Basically, if gDoctest is True,
no arguments are passed when an exception is raised. Normally, 
gDoctest is False and we do raise exceptions with arguments.

You must modify the doctestSw value to True/False to 
activate/deactivate use of the doctest module tests.

To used this module, use the 'from' form of the import
statement and write:

from doctestsw import *
...
if __name__ == "__main__":
  if doctestSw:
    import doctest
    doctest.testmod( sys.modules[__name__] )

$Id$
"""
__version__ = "$Revision: 1.2 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

doctestSw = True
