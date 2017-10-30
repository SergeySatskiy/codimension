# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# The ideas and code samples are taken from the winpdb project.
# Credits: Nir Aides, Copyright (C) 2005-2009
#

"""Utility functions to support running scripts"""

import sys
import os.path
from subprocess import check_output, STDOUT
from shlex import quote
from .config import DEFAULT_ENCODING
from .runparams import RUN, PROFILE, DEBUG
from .encoding import detectFileEncodingToRead


def prepareArguments(arguments):
    """Prepares arguments for the command line"""
    args = []
    for index, _ in enumerate(arguments):
        args.append('${CDM_ARG' + str(index) + '}')
    return args


def prepareInterpreter(params):
    """Provides the intrpreter path, quoted if needed"""
    if params['useInherited']:
        return quote(sys.executable)
    return quote(params['customInterpreter'])


def prepareScript(path):
    """Provides the scropt path quoted if needed"""
    return quote(path)


def getTerminalCommandToRun(fileName, arguments, params,
                            tcpServerPort=None, procuuid=None):
    """Provides a command to run a separate shell terminal"""
    interpreter = prepareInterpreter(params)
    script = prepareScript(fileName)

    if params['redirected']:
        runClient = os.path.sep.join([os.path.dirname(sys.argv[0]),
                                      "debugger", "client",
                                      "client_cdm_run.py"])
        parts = [interpreter, runClient,
                 '--host', 'localhost', '--port', str(tcpServerPort),
                 '--procuuid', str(procuuid), '--', script] + \
                prepareArguments(arguments)
        return ' '.join(parts)

    # Non-redirected case, i.e. the user provided the a custom terminal string
    parts = [interpreter, script] + prepareArguments(arguments)
    customTerminal = params['customTerminal'].strip()
    if '${prog}' in customTerminal:
        return customTerminal.replace('${prog}', ' '.join(parts))

    return customTerminal + ' ' + ' '.join(parts)


def getTerminalCommandToProfile(fileName, arguments, params,
                                tcpServerPort=None, procuuid=None):
    """Provides a command to run a separate shell terminal"""
    interpreter = prepareInterpreter(params)
    script = prepareScript(fileName)

    from .globals import GlobalData
    outfile = GlobalData().getProfileOutputPath(procuuid)

    if params['redirected']:
        runClient = os.path.sep.join([os.path.dirname(sys.argv[0]),
                                      "debugger", "client",
                                      "client_cdm_profile.py"])
        parts = [interpreter, runClient,
                 '--host', 'localhost', '--port', str(tcpServerPort),
                 '--procuuid', str(procuuid), '--outfile', outfile,
                 '--', script] + \
                prepareArguments(arguments)
        return ' '.join(parts)

    # Non-redirected case, i.e. the user provided the a custom terminal string
    parts = [interpreter, script] + prepareArguments(arguments)
    customTerminal = params['customTerminal'].strip()
    if '${prog}' in customTerminal:
        return customTerminal.replace('${prog}', ' '.join(parts))

    return customTerminal + ' ' + ' '.join(parts)


def getTerminalCommandToDebug(fileName, arguments, params,
                              tcpServerPort, procuuid):
    """Provides a command line to debug in a separate shell terminal"""
    interpreter = prepareInterpreter(params)
    script = prepareScript(fileName)
    encoding = detectFileEncodingToRead(fileName)

    debugClient = os.path.sep.join([os.path.dirname(sys.argv[0]),
                                    "debugger", "client",
                                    "client_cdm_dbg.py"])
    parts = [interpreter, debugClient,
             '--host', 'localhost', '--port', str(tcpServerPort),
             '--procuuid', str(procuuid), '--encoding', encoding]

    # Get the debugging specific parameters
    from .settings import Settings
    debugSettings = Settings().getDebuggerSettings()

    # Form the debug client options
    if not debugSettings.reportExceptions:
        parts.append('--no-exc-report')
    if debugSettings.traceInterpreter:
        parts.append('--trace-python')
    if debugSettings.autofork:
        if debugSettings.followChild:
            parts.append('--fork-child')
        else:
            parts.append('--fork-parent')

    if not Settings()['calltrace']:
        parts.append('--no-call-trace')

    if params['redirected']:
        parts += ['--', script] + prepareArguments(arguments)
        return ' '.join(parts)

    # Append the option of a non redirected I/O
    parts.append('--no-redirect')
    parts += ['--', script] + prepareArguments(arguments)

    customTerminal = params['customTerminal'].strip()
    if '${prog}' in customTerminal:
        return customTerminal.replace('${prog}', ' '.join(parts))

    return customTerminal + ' ' + ' '.join(parts)


def parseCommandLineArguments(cmdLine):
    """Parses command line arguments provided by the user in the UI"""
    result = []

    cmdLine = cmdLine.strip()
    expectQuote = False
    expectDblQuote = False
    lastIndex = len(cmdLine) - 1
    argument = ""
    index = 0
    while index <= lastIndex:
        if expectQuote:
            if cmdLine[index] == "'":
                if cmdLine[index - 1] != '\\':
                    if argument != "":
                        result.append(argument)
                        argument = ""
                    expectQuote = False
                else:
                    argument = argument[: -1] + "'"
            else:
                argument += cmdLine[index]
            index += 1
            continue
        if expectDblQuote:
            if cmdLine[index] == '"':
                if cmdLine[index - 1] != '\\':
                    if argument != "":
                        result.append(argument)
                        argument = ""
                    expectDblQuote = False
                else:
                    argument = argument[: -1] + '"'
            else:
                argument += cmdLine[index]
            index += 1
            continue
        # Not in a string literal
        if cmdLine[index] == "'":
            if index == 0 or cmdLine[index - 1] != '\\':
                expectQuote = True
                if argument != "":
                    result.append(argument)
                    argument = ""
            else:
                argument = argument[: -1] + "'"
            index += 1
            continue
        if cmdLine[index] == '"':
            if index == 0 or cmdLine[index - 1] != '\\':
                expectDblQuote = True
                if argument != "":
                    result.append(argument)
                    argument = ""
            else:
                argument = argument[: -1] + '"'
            index += 1
            continue
        if cmdLine[index] in (' ', '\t'):
            if argument != "":
                result.append(argument)
                argument = ""
            index += 1
            continue
        argument += cmdLine[index]
        index += 1

    if argument != "":
        result.append(argument)

    if expectQuote or expectDblQuote:
        raise Exception("No closing quotation")
    return result


def getCwdCmdEnv(kind, path, params, tcpServerPort=None, procuuid=None):
    """Provides the working directory, command line and environment.

    It covers all: running/debugging/profiling a script
    """
    # The arguments parsing is going to pass OK because it
    # was checked in the run parameters dialogue
    if kind not in [RUN, PROFILE, DEBUG]:
        raise Exception("Unknown command requested. "
                        "Supported command types are: run, profile, debug.")

    arguments = parseCommandLineArguments(params['arguments'])
    if kind == RUN:
        cmd = getTerminalCommandToRun(path, arguments, params,
                                      tcpServerPort, procuuid)
    elif kind == PROFILE:
        cmd = getTerminalCommandToProfile(path, arguments, params,
                                          tcpServerPort, procuuid)
    elif kind == DEBUG:
        cmd = getTerminalCommandToDebug(path, arguments, params,
                                        tcpServerPort, procuuid)

    environment = getNoArgsEnvironment(params)
    for index, value in enumerate(arguments):
        environment['CDM_ARG' + str(index)] = value

    return cmd, environment


def getNoArgsEnvironment(params):
    """Provides a copy of the environment"""
    if params['envType'] == params.InheritParentEnv:
        # 'None' does not work here: popen stores last env somewhere and
        # uses it inappropriately
        return os.environ.copy()
    if params['envType'] == params.InheritParentEnvPlus:
        environment = os.environ.copy()
        environment.update(params['additionToParentEnv'])
        return environment
    return params['specificEnv'].copy()


def checkOutput(cmdLine, useShell=False):
    """Wrapper around Subprocess.check_output which respects encoding"""
    if useShell:
        if not isinstance(cmdLine, str):
            raise Exception("Running via shell requires "
                            "the command line as a string")
    else:
        if not isinstance(cmdLine, list):
            raise Exception("Running without shell requires "
                            "the command line as a list")
    return check_output(cmdLine, stderr=STDOUT,
                        shell=useShell).decode(DEFAULT_ENCODING)


if __name__ == '__main__':
    print("Current working dir: " + os.getcwd())
    print("Environment: " + str(os.environ))
    print("Arguments: " + str(sys.argv))
