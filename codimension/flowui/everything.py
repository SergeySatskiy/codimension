#!/usr/bin/python
# encoding: utf-8
# cml 1 cc bg=#ffffff
# File top comment

# cml 1 cc fg=#ffffff bg=#000000
"""
File docstring
"""


#
# Code blocks
#


# cml 1 rt text="one"
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



# cml 1 rt text="Quite a \"long\" text\nOn two lines"
x = 720


d = 154
e = 154  # side
f = 154

# cml 1 cc fg=#000000
alone = 2

# cml 1 cc fg=#000000
# Leading
a = 10      # Side
            # Side


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


# cml 1 cc bg=#000000 fg=#eaeaea border=#ffffff
import sys, \
       os.path

# cml 1 cc bg=#eaeaea fg=#000000
# Leading
from sys import path        # Side
                            # Side last


#
# Functions
#


# Leading
def f( x ):     # Side
                # Last side

    # cml 1 cc fg=#ff0000
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


# cml 1 rt text="My own header"
def fReplaced( x ):
    pass


#
# Classes
#


# cml 1 cc bg=#dddddd fg=#ffffff
# Leading
class C:    # Side
            # Last side
    # cml 1 cc bg=#555555 fg=#ffffff
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
    # cml 1 cc bg=#ffffff
    " C3 doc "
    pass


class C4( C5 ):
    def member1( self ):
        pass
    # cml 1 cc bg=#777777 
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

if True:
    try:
        pass
    except Exception:
        pass
    except Exception as ex:
        pass
    except:
        pass
else:
    try:
        pass
    except Exception:
        pass


# Leading 1
try:        # Side 1
    pass
# Leading 2
# Leading 2.1
except Exception:   # Side 2
                    # Side 2.1
    pass
except Exception as ex:
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
except Exception as ex:
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
    # cml 1 cc bg=0,230,0 fg=255,255,255
    # Leading 1
    # Leading 2
    break   # Side 1
            # Side 2

while True:
    continue

# cml 1 cc bg=#dddddd fg=#343399
while True:
    # cml 1 cc bg=0,230,0 fg=255,255,255
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
    # cml 1 cc bg="230,0,0" fg="255,255,255" border=#000000
    # Leading
    return 154  # Side 1
                # Side 2

def f15():
    # cml 1 sw
    # Leading
    return ( 154,               # Side 1
             "Shakespeare" )    # Side 2

# cml 1 cc bg=#454545 fg=#ffffff border=#ff0000
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

# cml 1 cc bg=0,0,210 fg=255,255,255
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

# cml 1 cc bg=0,230,0 fg=0,0,230
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

# cml 1 cc bg="25, 200, 200"
# cml+     fg=#ffffff
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

# cml 1 cc bg=#dddddd fg=#343399 border=#ffffff
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

# cml 1 sw
if True:
    pass
else:
    pass

# cml 1 rt text = "Some text"
if a == 154 and \
   b == 155 and \
   c == 156:
    pass
elif False:
    pass

    pass
else:
    pass


# Leading
# cml 1 rt text = ""
if True:    # Side 1
            # Side 2
    pass

    pass

    pass
# Leading 3
# cml 1 sw
# cml 1 cc bg=#345678 fg=#ffffff border=#ffffff
elif False: # Side 3
    pass
# Leading 4
else:       # Side 4
    def f( a,
           b,       # side
           c ) :
        " docstring "
        pass


# cml 1 cc bg=#ee00ee fg=#ffffff
# cml 1 rt text="Salary is too high"
if a > 456 and \
   b < 76 or \
   d == 99:
    pass
elif a < 456 and \
     b > 76 or \
     c == 99:
    pass
else:
    pass

def ff(x):
    if True:
        # Something
        if x > 32:
            x = 32
    return
