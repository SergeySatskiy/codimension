#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QApplication, QTabWidget, QPushButton

from pyqterm import TerminalWidget
from pyqterm.procinfo import ProcessInfo


class TabbedTerminal(QTabWidget):

    def __init__(self, parent=None):
        super(TabbedTerminal, self).__init__(parent)
        self.proc_info = ProcessInfo()
        self.setTabPosition(QTabWidget.South)
        self._new_button = QPushButton(self)
        self._new_button.setText("New")
        self._new_button.clicked.connect(self.new_terminal)
        self.setCornerWidget(self._new_button)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setWindowTitle("Terminal")
        self.resize(800, 600)
        self._terms = []
        self.tabCloseRequested[int].connect(self._on_close_request)
        self.currentChanged[int].connect(self._on_current_changed)
        QTimer.singleShot(0, self.new_terminal)  # create lazy on idle
        self.startTimer(1000)

    def _on_close_request(self, idx):
        term = self.widget(idx)
        term.stop()

    def _on_current_changed(self, idx):
        term = self.widget(idx)
        self._update_title(term)

    def new_terminal(self):
        term = TerminalWidget(self)
        term.session_closed.connect(self._on_session_closed)
        self.addTab(term, "Terminal")
        self._terms.append(term)
        self.setCurrentWidget(term)
        term.setFocus()

    def timerEvent(self, event):
        self._update_title(self.currentWidget())

    def _update_title(self, term):
        if term is None:
            self.setWindowTitle("Terminal")
            return
        idx = self.indexOf(term)
        pid = term.pid()
        self.proc_info.update()
        child_pids = [pid] + self.proc_info.all_children(pid)
        for pid in reversed(child_pids):
            cwd = self.proc_info.cwd(pid)
            if cwd:
                break
        try:
            cmd = self.proc_info.commands[pid]
            title = "%s: %s" % (os.path.basename(cwd), cmd)
        except:
            title = "Terminal"
        self.setTabText(idx, title)
        self.setWindowTitle(title)

    def _on_session_closed(self):
        term = self.sender()
        try:
            self._terms.remove(term)
        except:
            pass
        self.removeTab(self.indexOf(term))
        widget = self.currentWidget()
        if widget:
            widget.setFocus()
        if self.count() == 0:
            self.new_terminal()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TabbedTerminal()
    win.show()
    app.exec_()
