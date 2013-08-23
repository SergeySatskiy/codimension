#!/usr/bin/env python
from setuptools import setup
import re
import sys


def load_version(filename='magic/version.py'):
    "Parse a __version__ number from a source file"
    with open(filename) as source:
        text = source.read()
        match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", text)
        if not match:
            msg = "Unable to find version number in {}".format(filename)
            raise RuntimeError(msg)
        version = match.group(1)
        return version


def load_rst(filename='docs/source/guide_content'):
    "Purge refs directives from restructured text"
    with open(filename) as source:
        text = source.read()
        doc = re.sub(r':\w+:`~?([a-zA-Z._()]+)`', r'*\1*', text)
        return doc

PYTHON3K = sys.version_info[0] > 2

setup(
    name="filemagic",
    version=load_version(),
    packages=['magic'],
    zip_safe=False,
    author="Aaron Iles",
    author_email="aaron.iles@gmail.com",
    url="http://filemagic.readthedocs.org",
    description="A Python API for libmagic, the library behind the Unix file command",
    long_description=load_rst(),
    license="ASL",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    tests_require=['mock'] + [] if PYTHON3K else ['unittest2'],
    test_suite="tests" if PYTHON3K else "unittest2.collector"
)
