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

.PHONY: all gen clean cleanall

GENERATED_FILES=pycfLexer.h pycfParser.h \
		pycfLexer.c pycfParser.c pycf.tokens

FLAGS=-ffast-math -fomit-frame-pointer
INCLUDE=-I../thirdparty/libantlr3c-3.2 -I../thirdparty/libantlr3c-3.2/include

all: $(GENERATED_FILES) cdmcfparser.c lexerutils.o cf_test.c
	python setup.py build_ext --inplace
	gcc -O2 ${FLAGS} ${INCLUDE} -c -std=gnu99 cf_test.c
	gcc ${FLAGS} -o cf_test build/*/pycfLexer.o \
                               build/*/pycfParser.o \
                               cf_test.o lexerutils.o \
                               ../thirdparty/libantlr3c-3.2/.libs/libantlr3c.a

gen: pycf.g
	CLASSPATH=/home/swift/antlr/antlrworks-1.4.jar java org.antlr.Tool pycf.g

lexerutils.o: lexerutils.c
	gcc -O2 -I/usr/include/python2.7/ ${FLAGS} ${INCLUDE} -c lexerutils.c

clean:
	rm -rf *.o core.* _cdmcfparser.so build/ cf_test core *.pyc

cleanall: clean
	rm -f $(GENERATED_FILES)
