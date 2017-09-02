#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2014-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Wrapper to run a script with redirected IO"""


import sys
import socket
import traceback
import os
import imp
from PyQt5.QtNetwork import QTcpSocket, QAbstractSocket, QHostAddress
from outredir_cdm_dbg import OutStreamRedirector
from cdm_dbg_utils import sendJSONCommand, parseJSONMessage
from protocol_cdm_dbg import (METHOD_PROC_ID_INFO, METHOD_PROLOGUE_CONTINUE,
                              METHOD_EPILOGUE_EXIT, METHOD_EPILOGUE_EXIT_CODE,
                              METHOD_STDIN)


WAIT_CONTINUE_TIMEOUT = 5   # in seconds
WAIT_EXIT_COMMAND = 5       # in seconds
RUN_WRAPPER = None
RUN_CLIENT_ORIG_INPUT = None


def runClientInput(prompt="", echo=True):
    """Replacement for the standard raw_input builtin"""
    if RUN_WRAPPER is None or not RUN_WRAPPER.redirected():
        return RUN_CLIENT_ORIG_INPUT(prompt)
    return RUN_WRAPPER.input(prompt, echo)


# Use our own input().
try:
    RUN_CLIENT_ORIG_INPUT = __builtins__.__dict__['input']
    __builtins__.__dict__['input'] = runClientInput
except (AttributeError, KeyError):
    import __main__
    RUN_CLIENT_ORIG_INPUT = __main__.__builtins__.__dict__['input']
    __main__.__builtins__.__dict__['input'] = runClientInput


class RedirectedIORunWrapper():

    """Wrapper to run a script with redirected IO"""

    def __init__(self):
        self.__socket = None
        self.__redirected = False
        self.__procid = None

    def redirected(self):
        """True if streams are redirected"""
        return self.__redirected

    def main(self):
        "Run wrapper driver"
        if '--' not in sys.argv:
            print("Unexpected arguments", file=sys.stderr)
            return 1

        self.__procid, host, port, args = self.parseArgs()
        if self.__procid is None or host is None or port is None:
            print("Not enough arguments", file=sys.stderr)
            return 1

        remoteAddress = self.resolveHost(host)
        self.connect(remoteAddress, port)
        sendJSONCommand(self.__socket, METHOD_PROC_ID_INFO,
                        self.__procid, None)

        try:
            self.__waitContinue()
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1

        # Setup redirections
        stdoutOld = sys.stdout
        stderrOld = sys.stderr
        sys.stdout = OutStreamRedirector(self.__socket, True, self.__procid)
        sys.stderr = OutStreamRedirector(self.__socket, False, self.__procid)
        self.__redirected = True

        # Run the script
        retCode = 0
        try:
            self.__runScript(args)
        except SystemExit as exc:
            if exc.code is None:
                retCode = 0
            elif isinstance(exc.code, int):
                retCode = exc.code
            else:
                retCode = 1
                print(str(exc.code), file=sys.stderr)
        except KeyboardInterrupt as exc:
            retCode = 1
            print(traceback.format_exc(), file=sys.stderr)
        except Exception as exc:
            retCode = 1
            print(traceback.format_exc(), file=sys.stderr)
        except:
            retCode = 1
            print(traceback.format_exc(), file=sys.stderr)

        sys.stderr = stderrOld
        sys.stdout = stdoutOld
        self.__redirected = False

        # Send the return code back
        try:
            sendJSONCommand(self.__socket, METHOD_EPILOGUE_EXIT_CODE,
                            self.__procid, {'ExitCode': retCode})
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            self.close()
            return 1

        self.close()
        return 0

    def connect(self, remoteAddress, port):
        """Establishes a connection with the IDE"""
        self.__socket = QTcpSocket()
        if remoteAddress is None:
            self.__socket.connectToHost(QHostAddress.LocalHost, port)
        else:
            self.__socket.connectToHost(remoteAddress, port)
        if not self.__socket.waitForConnected(1000):
            raise Exception('Cannot connect to the IDE')
        self.__socket.setSocketOption(QAbstractSocket.KeepAliveOption, 1)
        self.__socket.setSocketOption(QAbstractSocket.LowDelayOption, 1)

    def __waitForIDEMessage(self, msgType, timeout):
        """Waits for a certain message from the IDE"""
        if self.__socket.waitForReadyRead(timeout * 1000):
            jsonStr = bytes(self.__socket.readLine()).decode()
            try:
                method, _, params = parseJSONMessage(jsonStr)
                if method != msgType:
                    raise Exception('Unexpected message from IDE. Expected: ' +
                                    msgType + '. Received: ' + str(method))
                return params
            except (TypeError, ValueError) as exc:
                raise Exception('Error parsing IDE message: ' + str(exc))

        raise Exception('Timeout waiting an IDE message ' + msgType)

    def __waitContinue(self):
        """Waits the 'continue' command"""
        self.__waitForIDEMessage(METHOD_PROLOGUE_CONTINUE,
                                 WAIT_CONTINUE_TIMEOUT)

    def __waitExit(self):
        """Waits for the 'exit' command"""
        self.__waitForIDEMessage(METHOD_EPILOGUE_EXIT,
                                 WAIT_EXIT_COMMAND)

    def __runScript(self, arguments):
        """Runs the python script"""
        try:
            # In Py 2.x, the builtins were in __builtin__
            builtins = sys.modules['__builtin__']
        except KeyError:
            # In Py 3.x, they're in builtins
            builtins = sys.modules['builtins']

        fileName = arguments[0]

        oldMainMod = sys.modules['__main__']
        mainMod = imp.new_module('__main__')
        sys.modules['__main__'] = mainMod
        mainMod.__file__ = fileName
        mainMod.__builtins__ = builtins

        # Set sys.argv properly.
        oldArgv = sys.argv
        sys.argv = arguments

        # Without this imports of what is located at the script directory do
        # not work
        sys.path.insert(0, os.getcwd())

        f = open(fileName, "rU")
        source = f.read()
        f.close()

        # We have the source.  `compile` still needs the last line to be clean,
        # so make sure it is, then compile a code object from it.
        if not source or source[-1] != '\n':
            source += '\n'

        code = compile(source, fileName, "exec")
        exec(code, mainMod.__dict__)

        # Restore the old __main__
        sys.modules['__main__'] = oldMainMod

        # Restore the old argv and path
        sys.argv = oldArgv

    def close(self):
        """Closes the connection if so"""
        try:
            if self.__socket:
                # Wait exit needed because otherwise IDE may get socket
                # disconnected before it has a chance to read the script
                # exit code. Wait for the explicit command to exit guarantees
                # that all the data will be received.
                self.__waitExit()
                self.__socket.close()
        except:
            pass

    def input(self, prompt, echo):
        """Implements input() using the redirected input"""
        sendJSONCommand(self.__socket, METHOD_STDIN, self.__procid,
                        {'prompt': prompt, 'echo': echo})
        params = self.__waitForIDEMessage(METHOD_STDIN, 60 * 60 * 24 * 7)
        return params['input']

    @staticmethod
    def resolveHost(host):
        """Resolves a hostname to an IP address"""
        try:
            host, _ = host.split("@@")
            family = socket.AF_INET6
        except ValueError:
            # version = 'v4'
            family = socket.AF_INET
        return socket.getaddrinfo(host, None, family,
                                  socket.SOCK_STREAM)[0][4][0]

    @staticmethod
    def parseArgs():
        """Parses the arguments"""
        host = None
        port = None
        procid = None
        args = sys.argv[1:]

        while args[0]:
            if args[0] in ['-h', '--host']:
                host = args[1]
                del args[0]
                del args[0]
            elif args[0] in ['-p', '--port']:
                port = int(args[1])
                del args[0]
                del args[0]
            elif args[0] in ['-i', '--procid']:
                procid = int(args[1])
                del args[0]
                del args[0]
            elif args[0] == '--':
                del args[0]
                break

        return procid, host, port, args


if __name__ == "__main__":
    RUN_WRAPPER = RedirectedIORunWrapper()
    sys.exit(RUN_WRAPPER.main())
