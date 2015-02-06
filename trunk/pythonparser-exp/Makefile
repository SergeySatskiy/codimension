#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

.PHONY: all clean

FLAGS=-ffast-math -fomit-frame-pointer -g
INCLUDE=-I/opt/python-2.7/include/python2.7/

all: cdmpyparser.c tree.cpp
	python setup.py build_ext --inplace
	g++ ${FLAGS} ${INCLUDE} -c tree.cpp
	g++ ${FLAGS} -o tree  tree.o -L/opt/python-2.7/lib/ -lpython2.7

clean:
	rm -rf *.o core.* _cdmpyparser.so build/ tree

