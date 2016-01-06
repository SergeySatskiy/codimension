#!/usr/bin/python
# encoding: utf-8
# File top comment

"""
File docstring
"""



# Code blocks

# Leading
a = 10      # Side
b = 20      # Side
            # Side last



# Imports

import sys, \
       os.path

# Leading
import sys      # Side
                # Side last

# Leading
from sys import path        # Side
                            # Side last



# Functions


# Leading
def f( x ):     # Side
                # Last side
    """ f doc
        f doc line 2
    """
    pass

def f1( x,
        y ):
    " f1 doc "
    pass

def f2( x, y, z ):
    pass


# Leading
def f3( x,      # Side 1
        y,      # Side 2
        z ):
    " f3 doc "
    pass


# Classes


# Leading
class C:    # Side
            # Last side
    """
    Class C doc
    Class C doc line 2
    """
    pass

class C1( B1,
          B2 ):
    " C1 doc "
    pass

# Leading
class C3( B1,       # Side 1
          B2,       # Side 2
          B3 ):
    " C3 doc "
    pass
