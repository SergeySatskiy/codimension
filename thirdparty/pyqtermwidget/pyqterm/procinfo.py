#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re


class ProcessInfo(object):

    def __init__(self):
        self.update()

    def update(self):
        processes = [int(entry)
                     for entry in os.listdir("/proc") if entry.isdigit()]
        parent = {}
        children = {}
        commands = {}
        for pid in processes:
            try:
                f = open("/proc/%s/stat" % pid)
            except IOError:
                continue
            stat = f.read().split()
            f.close()
            cmd = stat[1]
            ppid = int(stat[3])
            parent[pid] = ppid
            children.setdefault(ppid, []).append(pid)
            commands[pid] = cmd
        self.parent = parent
        self.children = children
        self.commands = commands

    def all_children(self, pid):
        cl = self.children.get(pid, [])[:]
        for child_pid in cl:
            cl.extend(self.children.get(child_pid, []))
        return cl

    def dump(self, pid, _depth=0):
        print " " * (_depth * 2), pid, self.commands[pid]
        for child_pid in self.children.get(pid, []):
            self.dump(child_pid, _depth + 1)

    def cwd(self, pid):
        try:
            path = os.readlink("/proc/%s/cwd" % pid)
        except OSError:
            return
        return path


if __name__ == "__main__":
    pi = ProcessInfo()
    pi.dump(4984)
    print pi.all_children(4984)
    print pi.cwd(4984)
    print pi.cwd(pi.all_children(4984)[-1])
