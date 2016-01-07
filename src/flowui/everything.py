#!/usr/bin/python
# encoding: utf-8
# File top comment

"""
File docstring
"""


#
# Code blocks
#


alone = 1

one = 1
two = 2

# Leading
a = 10      # Side
b = 20      # Side
            # Side last


#
# Imports
#


import sys, \
       os.path

# Leading
import sys      # Side
                # Side last

# Leading
from sys import path        # Side
                            # Side last


#
# Functions
#


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


#
# Classes
#


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


class C4( C5 ):
    def member1( self ):
        pass
    # Leading 1
    # Leading 2
    def member2( self,      # Side 1
                 x, y ):        # Side 2
                                # Side 3
        pass


#
# Decorators
#

@decor1
def d():
    pass

# Leading
@decor2     # Side 1
            # Side 2
def d():
    pass

# Leading
@decor2( x,     # Side 1
         y )    # Side 2
def d():
    pass

@decor3
@decor4
class Cd:
    pass


#
# For
#


for x in y:
    pass

# Leading
for x in y:     # Side 1
    pass

for x in y:     # Side 1
                # Side 2
    pass

for x in y:
    pass
else:
    pass

for x in y:
    pass
# Leading
else:   # Side 1
        # Side 2
    pass

# Leading 1
# Leading 2
for x in y: # Side 1
            # Side 2
    pass
# Leading
else:   # Side 1
        # Side 2
    pass

#
# While
#

while True:
    pass

# Leading
while True:     # Side 1
    pass

while True:     # Side 1
                # Side 2
    pass

while True:
    pass
else:
    pass

while True:
    pass
# Leading
else:   # Side 1
        # Side 2
    pass

# Leading 1
# Leading 2
while True: # Side 1
            # Side 2
    pass
# Leading
else:   # Side 1
        # Side 2
    pass



#
# Try
#


#
# break/continue
#


#
# Return
#


#
# Assert
#


#
# Raise
#



#
# sys.exit()
#

#
# 
#
