import os, sys
from glob import glob
from distutils.command.install import install
from distutils.core import setup

headers = (glob( os.path.join( "CXX","*.hxx" ) )
          +glob( os.path.join( "CXX","*.h" ) ))
sources = (glob( os.path.join( "Src", "*.cxx" ) )
          +glob( os.path.join( "Src", "*.c" ) ))


class my_install (install):

    def finalize_options (self):
        if not self.install_data or (len(self.install_data) < 8) :
            self.install_data = "$base/share/python$py_version_short"
        install.finalize_options (self)

    def run (self):
        self.distribution.data_files = [("CXX", sources)]
        self.distribution.headers = headers
        install.run (self)


setup (name             = "CXX",
       version          = "6.2.4",
       maintainer       = "Barry Scott",
       maintainer_email = "barry-scott@users.sourceforge.net",
       description      = "Facility for extending Python with C++",
       url              = "http://cxx.sourceforge.net",
       
       cmdclass         = {'install': my_install},
       packages         = ['CXX'],
       package_dir      = {'CXX': 'Lib'}
      )
