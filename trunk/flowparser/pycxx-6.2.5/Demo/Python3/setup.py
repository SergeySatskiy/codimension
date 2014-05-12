#-----------------------------------------------------------------------------
#
# Copyright (c) 1998 - 2007, The Regents of the University of California
# Produced at the Lawrence Livermore National Laboratory
# All rights reserved.
#
# This file is part of PyCXX. For details,see http://cxx.sourceforge.net/. The
# full copyright notice is contained in the file COPYRIGHT located at the root
# of the PyCXX distribution.
#
# Redistribution  and  use  in  source  and  binary  forms,  with  or  without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of  source code must  retain the above  copyright notice,
#    this list of conditions and the disclaimer below.
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this  list of  conditions  and  the  disclaimer (as noted below)  in  the
#    documentation and/or materials provided with the distribution.
#  - Neither the name of the UC/LLNL nor  the names of its contributors may be
#    used to  endorse or  promote products derived from  this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT  HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR  IMPLIED WARRANTIES, INCLUDING,  BUT NOT  LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND  FITNESS FOR A PARTICULAR  PURPOSE
# ARE  DISCLAIMED.  IN  NO  EVENT  SHALL  THE  REGENTS  OF  THE  UNIVERSITY OF
# CALIFORNIA, THE U.S.  DEPARTMENT  OF  ENERGY OR CONTRIBUTORS BE  LIABLE  FOR
# ANY  DIRECT,  INDIRECT,  INCIDENTAL,  SPECIAL,  EXEMPLARY,  OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT  LIMITED TO, PROCUREMENT OF  SUBSTITUTE GOODS OR
# SERVICES; LOSS OF  USE, DATA, OR PROFITS; OR  BUSINESS INTERRUPTION) HOWEVER
# CAUSED  AND  ON  ANY  THEORY  OF  LIABILITY,  WHETHER  IN  CONTRACT,  STRICT
# LIABILITY, OR TORT  (INCLUDING NEGLIGENCE OR OTHERWISE)  ARISING IN ANY  WAY
# OUT OF THE  USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
#-----------------------------------------------------------------------------

import os, sys
from distutils.core import setup, Extension

support_dir = os.path.normpath(
                   os.path.join(
			sys.prefix,
			'share',
			'python%d.%d' % (sys.version_info[0],sys.version_info[1]),
			'CXX') )

if os.name == 'posix':
	CXX_libraries = ['stdc++','m']
else:
	CXX_libraries = []

setup (name = "CXXDemo",
       version = "5.1",
       maintainer = "Barry Scott",
       maintainer_email = "barry-scott@users.sourceforge.net",
       description = "Demo of facility for extending Python with C++",
       url = "http://cxx.sourceforge.net",
       
       packages = ['CXX'],
       package_dir = {'CXX': '.'},
       ext_modules = [
         Extension('CXX.example',
                   sources = ['example.cxx',
                         'range.cxx',
                         'rangetest.cxx',
                         os.path.join(support_dir,'cxxsupport.cxx'),
                         os.path.join(support_dir,'cxx_extensions.cxx'),
                         os.path.join(support_dir,'IndirectPythonInterface.cxx'),
                         os.path.join(support_dir,'cxxextensions.c')
                         ],
            )
       ]
)
