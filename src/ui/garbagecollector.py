#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# The code is taken from here and slightly tweaked:
# http://pydev.blogspot.ru/2014/03/should-python-garbage-collector-be.html
#


"""Custom garbage collector"""


import gc
import logging
from .qt import QObject, QTimer


class GarbageCollector(QObject):

    '''Disable automatic garbage collection and instead collect manually
       every INTERVAL milliseconds.

       This is done to ensure that garbage collection only happens in the GUI
       thread, as otherwise Qt can crash.
    '''

    INTERVAL = 10000

    def __init__(self, parent):
        QObject.__init__(self, parent)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)

        self.threshold = gc.get_threshold()
        gc.disable()
        self.timer.start(self.INTERVAL)

    def check(self):
        """Called by the QTimer periodically in the GUI thread"""
        # return self.debug_cycles() # uncomment to just debug cycles
        lvl0, lvl1, lvl2 = gc.get_count()
        logging.debug("gc_check called: " +
                      ", ".join([str(lvl0), str(lvl1), str(lvl2)]))
        if lvl0 > self.threshold[0]:
            num = gc.collect(0)
            logging.debug("collecting gen 0, found: " +
                          str(num) + " unreachable")
            if lvl1 > self.threshold[1]:
                num = gc.collect(1)
                logging.debug("collecting gen 1, found: " +
                              str(num) + " unreachable")
                if lvl2 > self.threshold[2]:
                    num = gc.collect(2)
                    logging.debug("collecting gen 2, found: " +
                                  str(num) + " unreachable")

    def debug_cycles(self):
        """Debugging support"""
        gc.set_debug(gc.DEBUG_SAVEALL)
        gc.collect()
        for obj in gc.garbage:
            logging.debug(repr(obj) + " " + str(type(obj)))
