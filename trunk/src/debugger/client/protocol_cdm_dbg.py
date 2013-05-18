#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2002 - 2012 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module defining the debug protocol tokens.
"""

# The address used for debugger/client communications.
DebugAddress = '127.0.0.1'

# The protocol "words".
RequestOK =                '>OK?<'
RequestLoad =              '>Load<'
RequestContinue =          '>Continue<'
RequestStep =              '>Step<'
RequestStepOver =          '>StepOver<'
RequestStepOut =           '>StepOut<'
RequestStepQuit =          '>StepQuit<'
RequestBreak =             '>Break<'
RequestBreakEnable =       '>EnableBreak<'
RequestBreakIgnore =       '>IgnoreBreak<'
RequestWatch =             '>Watch<'
RequestWatchEnable =       '>EnableWatch<'
RequestWatchIgnore =       '>IgnoreWatch<'
RequestVariables =         '>Variables<'
RequestVariable =          '>Variable<'
RequestThreadList =        '>ThreadList<'
RequestThreadSet =         '>ThreadSet<'
RequestEval =              '>Eval<'
RequestExec =              '>Exec<'
RequestShutdown =          '>Shutdown<'
RequestForkTo =            '>ForkTo<'
RequestStack =             '>CurrentStack<'

ResponseOK =               '>OK<'
ResponseContinue =         '>Continue<'
ResponseException =        '>Exception<'
ResponseSyntax =           '>SyntaxError<'
ResponseExit =             '>Exit<'
ResponseLine =             '>Line<'
ResponseRaw =              '>Raw<'
ResponseClearBreak =       '>ClearBreak<'
ResponseBPConditionError = '>BPConditionError<'
ResponseClearWatch =       '>ClearWatch<'
ResponseWPConditionError = '>WPConditionError<'
ResponseVariables =        RequestVariables
ResponseVariable =         RequestVariable
ResponseThreadList =       RequestThreadList
ResponseThreadSet =        RequestThreadSet
ResponseStack =            RequestStack
ResponseForkTo =           RequestForkTo
ResponseEval =             RequestEval
ResponseEvalOK =           '>EvalOK<'
ResponseEvalError =        '>EvalError<'
ResponseExec =             RequestExec
ResponseExecError =        '>ExecError<'

PassiveStartup =           '>PassiveStartup<'

EOT = '>EOT<\n'
