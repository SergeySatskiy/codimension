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

c = """
    ...
    """ + \
    "123456"    # Side
                # Another side

'''
...
'''


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

def f4( a = """
            ...
            """ ):
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
    pass    # Last class statement side 1
            # Last class statement side 2

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

try:
    pass
except:
    pass

try:
    pass
except Exception:
    pass
except Exception, ex:
    pass
except:
    pass

# Leading 1
try:        # Side 1
    pass
# Leading 2
# Leading 2.1
except Exception:   # Side 2
                    # Side 2.1
    pass
except Exception, ex:
    pass
# Leading 4
except:         # Side 4
    pass

# Leading 1
try:        # Side 1
            # Side 2
    a = 10
    b = 20  # Side 1
            # Side 2
# Leading 2
# Leading 2.1
except Exception:   # Side 2
                    # Side 2.1
    pass
except Exception, ex:
    pass
# Leading 4
except:         # Side 4
    pass
# Leading 5
# Leadin 5.1
else:   # Side 5
    pass
# Leading 6
finally:    # Side 6
    pass


#
# break/continue
#

for x in y:
    break

for x in y:
    # Leading 1
    # Leading 2
    break   # Side 1
            # Side 2

while True:
    continue

while True:
    # Leading 1
    # Leading 2
    continue    # Side 1
                # Side 2


#
# Return
#

def f10():
    return

def f11():
    return None

def f12():
    return 154

def f13():
    return 154, \
           "Shakespeare"

def f14():
    # Leading
    return 154  # Side 1
                # Side 2

def f15():
    # Leading
    return ( 154,               # Side 1
             "Shakespeare" )    # Side 2

def f16():
    return """
           ...
           """

#
# Assert
#


assert x != 154

assert x != 154 and \
       y != 154 and \
       z != 154

# Leading
assert x != 154, ( "..."        # Side 1
                   "..." )      # side 2
                                # Side 3

assert """ one """, \
       """
       two
       """

#
# Raise
#

raise

raise Exception( "..." )

raise Exception( 1 +
                 2 +
                 3 )

# Leading
raise Exception( 1 +    # Side 1
                 3 )    # Side 2
                        # Side 3

raise """
      ...
      """

#
# sys.exit()
#

sys.exit( 0 )

sys.exit( 0 +
          0 +
          0 )

# Leading
sys.exit( 0 +   # Side 1
          0 )   # Side 2
                # Side 3

from sys import exit

exit( 0 )

exit( 0 +
      0 +
      0 )

# Leading
exit( 0 +   # Side 1
      0 )   # Side 2
            # Side 3

from sys import os, exit as EXIT

EXIT( 0 )

EXIT( 0 +
      0 +
      0 )

# Leading
EXIT( 0 +   # Side 1
      0 )   # Side 2
            # Side 3


#
# With
#

with open( "my.txt" ) as f:
    pass


with \
    open( "my.txt" ) \
        as \
            f:
    pass

# leading
with open( "my.txt" +           # Side 1
           "your.txt" ) as f:   # Side 2
                                # Side 3
    pass



#
# If
#

if True:
    pass

if True:
    pass
else:
    pass

if True:
    pass
elif False:
    pass
else:
    pass


# Leading
if True:    # Side 1
            # Side 2
    pass

    pass

    pass
# Leading
elif False: # Side 3
    pass
# Leading
else:       # Side 4
    pass


if a > 456 and \
   b < 76 or \
   c == 99:
    pass
elif a < 456 and \
     b > 76 or \
     c == 99:
    pass
else:
    pass

