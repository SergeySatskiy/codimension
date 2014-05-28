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

# TODO:
# - dependencies between cpp and hpp files are not here
# - C flags should not have -frtti
# - move object files to a build dir


.PHONY: all gen clean cleanall

VERSION=trunk

GENERATED_FILES=pycfLexer.h pycfParser.h pycfLexer.c pycfParser.c pycf.tokens

ANTLR_INCLUDE=-I../thirdparty/libantlr3c-3.2 \
              -I../thirdparty/libantlr3c-3.2/include
PYCXX_INCLUDE=-Ipycxx -Ipycxx/Src
PYTHON_INCLUDE=$(shell python -c 'import distutils.sysconfig; print distutils.sysconfig.get_python_inc()')
INCLUDE=${PYCXX_INCLUDE} -I${PYTHON_INCLUDE} ${ANTLR_INCLUDE}

VERSION_DEFINES=-DCDM_CF_PARSER_VERION=\"${VERSION}\"
FLAGS=-O2 -ffast-math -fomit-frame-pointer -fPIC -fexceptions -frtti -DNDEBUG -D_GNU_SOURCE ${VERSION_DEFINES}

PYCXX_OBJ_FILES=pycxx/Src/cxxsupport.o pycxx/Src/cxx_extensions.o \
                pycxx/Src/IndirectPythonInterface.o pycxx/Src/cxxextensions.o
CDM_OBJ_FILES=cflowmodule.o cflowfragments.o cflowutils.o
GRAMMAR_OBJ_FILES=lexerutils.o pycfLexer.o pycfParser.o


all: $(PYCXX_OBJ_FILES) $(CDM_OBJ_FILES) $(GRAMMAR_OBJ_FILES)
	g++ -shared -fPIC -fexceptions -frtti -o cdmcf.so $^ ../thirdparty/libantlr3c-3.2/.libs/libantlr3c.a
	gcc -O2 ${FLAGS} ${INCLUDE} -c -std=gnu99 cf_test.c
	gcc ${FLAGS} -o cf_test pycfLexer.o \
                            pycfParser.o \
                            cf_test.o lexerutils.o \
                            ../thirdparty/libantlr3c-3.2/.libs/libantlr3c.a

.cpp.o:
	g++ ${FLAGS} ${INCLUDE} -c -o $@ $^
pycxx/Src/%.o : pycxx/Src/%.cxx
	g++ ${FLAGS} ${INCLUDE} -c -o $@ $^
.c.o:
	g++ ${FLAGS} ${INCLUDE} -c -o $@ $^



gen: pycf.g
	CLASSPATH=/home/swift/antlr/antlrworks-1.4.jar java org.antlr.Tool pycf.g
	python adjust_generated.py

clean:
	rm -rf *.o core.* cdmcf.so cf_test core *.pyc

cleanall: clean
	rm -f $(GENERATED_FILES)
