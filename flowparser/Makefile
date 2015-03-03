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

PYCXX_INCLUDE=-Ipycxx -Ipycxx/Src
PYTHON_INCLUDE=$(shell python -c 'import distutils.sysconfig; print distutils.sysconfig.get_python_inc()')
INCLUDE=${PYCXX_INCLUDE} -I${PYTHON_INCLUDE}

VERSION_DEFINES=-DCDM_CF_PARSER_VERION=\"${VERSION}\"
FLAGS=-Wall -O2 -ffast-math -fomit-frame-pointer -fPIC -fexceptions -frtti -DNDEBUG -D_GNU_SOURCE ${VERSION_DEFINES}

PYCXX_OBJ_FILES=pycxx/Src/cxxsupport.o pycxx/Src/cxx_extensions.o \
                pycxx/Src/IndirectPythonInterface.o pycxx/Src/cxxextensions.o
PYCXX_SRC_FILES=pycxx/Src/cxxsupport.cxx pycxx/Src/cxx_extensions.cxx \
                pycxx/Src/IndirectPythonInterface.cxx pycxx/Src/cxxextensions.c
CDM_SRC_FILES=cflowmodule.cpp cflowfragments.cpp cflowutils.cpp cflowparser.cpp cflowcomments.cpp
CDM_INC_FILES=cflowmodule.hpp cflowfragments.hpp cflowutils.hpp cflowparser.hpp cflowcomments.hpp


all: $(CDM_SRC_FILES) $(CDM_INC_FILES) $(PYCXX_SRC_FILES)
	python setup.py build_ext --inplace
	g++ ${FLAGS} -I ${PYTHON_INCLUDE} -c tree.cpp
	g++ ${FLAGS} -o tree  tree.o -L/opt/python-2.7/lib/ -lpython2.7

clean:
	rm -rf *.o core.* cdmcf.so *.pyc tree

