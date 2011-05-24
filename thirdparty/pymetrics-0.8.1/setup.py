#!/usr/bin/python

from distutils.core import setup

setup (name = "PyMetrics",
       version = "PYMETRICS_VERSION",
       author = "Reg. Charney",
       author_email = "pymetrics@charneyday.com",
       description = "PyMetrics produces metrics for Python programs",
       url = "http://sourceforge.net/projects/pymetrics/",
       packages = ['PyMetrics'],
       scripts = ['pymetrics']
)
