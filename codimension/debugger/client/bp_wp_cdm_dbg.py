# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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


#
# The file was taken from eric 6 and adopted for codimension.
# Original copyright:
# Copyright (c) 2016 - 2017 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Breakpoints and watches on the debugger client side
"""

import os


class Breakpoint:

    """
    Breakpoint class
    """

    BREAKS = {}             # (filename, lineno) -> Breakpoint
    BREAK_IN_FILE = {}      # filename -> lineno
    BREAK_IN_FRAME_CACHE = {}

    def __init__(self, filename, lineno, temporary=False, cond=None):
        filename = os.path.abspath(filename)
        self.file = filename
        self.line = lineno
        self.temporary = temporary
        self.cond = cond
        self.enabled = True
        self.ignore = 0
        self.hits = 0
        Breakpoint.BREAKS[(filename, lineno)] = self
        lines = Breakpoint.BREAK_IN_FILE.setdefault(filename, [])
        if lineno not in lines:
            lines.append(lineno)
        Breakpoint.BREAK_IN_FRAME_CACHE.clear()

    def deleteMe(self):
        """Clears this breakpoint"""
        try:
            del Breakpoint.BREAKS[(self.file, self.line)]
            Breakpoint.BREAK_IN_FILE[self.file].remove(self.line)
            if not Breakpoint.BREAK_IN_FILE[self.file]:
                del Breakpoint.BREAK_IN_FILE[self.file]
        except KeyError:
            pass

    def enable(self):
        """Enables this breakpoint"""
        self.enabled = True

    def disable(self):
        """Disables this breakpoint"""
        self.enabled = False

    @staticmethod
    def clear_break(filename, lineno):
        """Reimplemented from bdb.py to clear a breakpoint"""
        bp = Breakpoint.BREAKS.get((filename, lineno))
        if bp:
            bp.deleteMe()
        Breakpoint.BREAK_IN_FRAME_CACHE.clear()

    @staticmethod
    def clear_all_breaks():
        """Clears all breakpoints"""
        Breakpoint.BREAKS.clear()
        Breakpoint.BREAK_IN_FILE.clear()
        Breakpoint.BREAK_IN_FRAME_CACHE.clear()

    @staticmethod
    def get_break(filename, lineno):
        """Provides the breakpoint of a particular line"""
        return Breakpoint.BREAKS.get((filename, lineno))

    @staticmethod
    def effectiveBreak(filename, lineno, frame):
        """Determine which bp for this filename:lineno is to be acted upon"""
        b = Breakpoint.BREAKS[filename, lineno]
        if not b.enabled:
            return (None, False)

        # Count every hit when bp is enabled
        b.hits += 1
        if not b.cond:
            # If unconditional, and ignoring,
            # go on to next, else break
            if b.ignore > 0:
                b.ignore -= 1
                return (None, False)
            else:
                # breakpoint and marker that's ok
                # to delete if temporary
                return (b, True)
        else:
            # Conditional bp.
            # Ignore count applies only to those bpt hits where the
            # condition evaluates to true.
            try:
                val = eval(b.cond, frame.f_globals, frame.f_locals)
                if val:
                    if b.ignore > 0:
                        b.ignore -= 1
                        # continue
                    else:
                        return (b, True)
                # else:
                #   continue
            except Exception:
                # if eval fails, most conservative
                # thing is to stop on breakpoint
                # regardless of ignore count.
                # Don't delete temporary,
                # as another hint to user.
                return (b, False)
        return (None, False)


class Watch:

    """
    Watch class
    """

    WATCHES = []

    def __init__(self, cond, compiledCond, flag, temporary=False):
        if cond:
            self.cond = cond
            self.compiledCond = compiledCond
            self.temporary = temporary

            self.enabled = True
            self.ignore = 0

            self.created = False
            self.changed = False
            if flag == '??created??':
                self.created = True
            elif flag == '??changed??':
                self.changed = True

            self.values = {}
            Watch.WATCHES.append(self)
        else:
            raise Exception('Inconsistency: a watch has no condition')

    def deleteMe(self):
        """Clears this watch expression"""
        try:
            del Watch.WATCHES[self]
        except ValueError:
            pass

    def enable(self):
        """Enables this watch"""
        self.enabled = True

    def disable(self):
        """Disables this watch"""
        self.enabled = False

    @staticmethod
    def clear_watch(cond):
        """Clears a watch expression"""
        try:
            Watch.WATCHES.remove(Watch.get_watch(cond))
        except ValueError:
            pass

    @staticmethod
    def clear_all_watches():
        """Clears all watch expressions"""
        del Watch.WATCHES[:]

    @staticmethod
    def get_watch(cond):
        """Provides a watch expression"""
        for b in Watch.WATCHES:
            if b.cond == cond:
                return b

    @staticmethod
    def effectiveWatch(frame):
        """Determines if a watch expression is effective"""
        for b in Watch.WATCHES:
            if not b.enabled:
                continue
            try:
                val = eval(b.compiledCond, frame.f_globals, frame.f_locals)
                if b.created:
                    if frame in b.values:
                        continue
                    else:
                        b.values[frame] = [1, val, b.ignore]
                        return (b, True)
                elif b.changed:
                    try:
                        if b.values[frame][1] != val:
                            b.values[frame][1] = val
                        else:
                            continue
                    except KeyError:
                        b.values[frame] = [1, val, b.ignore]

                    if b.values[frame][2] > 0:
                        b.values[frame][2] -= 1
                        continue
                    else:
                        return (b, True)
                elif val:
                    if b.ignore > 0:
                        b.ignore -= 1
                        continue
                    else:
                        return (b, True)
            except Exception:
                continue
        return (None, False)
