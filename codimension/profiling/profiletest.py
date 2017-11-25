#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy sergey.satskiy@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Profiler test"""
# import sys
import time

x = 0
while False:
    time.sleep(0.1)
    x += 1


v = range(175)
z = (x*x for x in range(10))
c = compile('sum([1, 2, 3])', '', 'single')
e = Ellipsis

raise Exception('dkdkdkd')

try:
    raise Exception('hey')
except Exception as exc:
    import sys
    x1, x2, x3 = sys.exc_info()

class A:
    def __init__(self):
        self.__d = 10
        self.d = 20
    def f():
        pass
    @property
    def x(self):
        return self.__x

def f( bla ):
    " F function docstring "
    if bla == -1:
        return -1
#    if bla >= 5:
#        return -1
    return f( bla + 1 )

def g( foo ):
    " g function doc "
    f( foo )

a = A()
b = set()
c = {1: '1', 2: '2'}

f( 0 )
g( -1 )

