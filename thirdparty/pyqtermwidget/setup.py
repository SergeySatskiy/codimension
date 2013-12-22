#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name="pyqterm",
        version="0.2",
        description="Simple terminal/console widget for PyQt4 with vt100 support",
        author="Henning Schroeder",
        author_email="henning.schroeder@gmail.com",
        url="https://bitbucket.org/henning/pyqtermwidget",
        zip_safe=True,
        license="GPL2",
        keywords="pyqt pyqt4 console terminal shell vt100 widget",
        packages=find_packages(),
    )
