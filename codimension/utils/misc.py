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

"""Miscellaneuos utility functions"""

import os.path
import re
import getpass
import locale
import datetime
from .globals import GlobalData
from .settings import SETTINGS_DIR
from .fileutils import getFileContent


# File name of the template for any new file.
# The file is searched nearby the project file.
templateFileName = 'template.py'

# File name with pylint settings
pylintFileName = 'pylintrc'


def splitThousands(value, sep="'"):
    """Provides thousands separated value"""
    if len(value) <= 3:
        return value
    return splitThousands(value[:-3], sep) + sep + value[-3:]


def getLocaleDate():
    """Provides locale formatted date"""
    now = datetime.datetime.now()
    try:
        date_format = locale.nl_langinfo(locale.D_FMT)
        return now.strftime(date_format)
    except:
        return now.strftime('%Y-%m-%d')


def getLocaleTime():
    """Provides locale formatted time"""
    now = datetime.datetime.now()
    try:
        time_format = locale.nl_langinfo(locale.T_FMT)
        return now.strftime(time_format)
    except:
        return now.strftime('%H:%M:%S')


def getLocaleDateTime():
    """Provides locale date time"""
    return getLocaleDate() + " " + getLocaleTime()


def getIDETemplateFile():
    """Provides the name of the IDE template file"""
    return SETTINGS_DIR + templateFileName


def getIDEPylintFile():
    """Provides the name of the IDE pylintrc file"""
    return SETTINGS_DIR + pylintFileName


def getProjectTemplateFile():
    """Provides the name of the project template file"""
    project = GlobalData().project
    if project.isLoaded():
        # Project is loaded - use from the project dir
        projectDir = os.path.dirname(project.fileName)
        if not projectDir.endswith(os.path.sep):
            projectDir += os.path.sep
        return projectDir + templateFileName
    return None


def getNewFileTemplate():
    """Searches for the template file and fills fields in it"""
    templateFile = getProjectTemplateFile()
    if templateFile is None:
        templateFile = getIDETemplateFile()
    elif not os.path.exists(templateFile):
        templateFile = getIDETemplateFile()

    if not os.path.exists(templateFile):
        return ""

    # read the file content: splitlines() eats the trailing \n
    content = getFileContent(templateFile)
    if content.endswith('\n') or content.endswith('\r\n'):
        content = content.splitlines() + ['']
    else:
        content = content.splitlines()

    # substitute the fields
    project = GlobalData().project
    projectLoaded = project.isLoaded()
    if projectLoaded:
        subs = [(re.compile(re.escape('$projectdate'), re.I),
                 project.props['creationdate']),
                (re.compile(re.escape('$author'), re.I),
                 project.props['author']),
                (re.compile(re.escape('$license'), re.I),
                 project.props['license']),
                (re.compile(re.escape('$copyright'), re.I),
                 project.props['copyright']),
                (re.compile(re.escape('$version'), re.I),
                 project.props['version']),
                (re.compile(re.escape('$email'), re.I),
                 project.props['email'])]
    else:
        subs = []

    # Common substitutions
    subs.append((re.compile(re.escape('$date'), re.I),
                 getLocaleDate()))
    subs.append((re.compile(re.escape('$time'), re.I),
                 getLocaleTime()))
    subs.append((re.compile(re.escape('$user'), re.I),
                 getpass.getuser()))

    if projectLoaded:
        # description could be multilined so it is a different story
        descriptionRegexp = re.compile(re.escape('$description'), re.I)
        description = project.props['description'].split('\n')

    result = []
    for line in content:
        for key, value in subs:
            line = re.sub(key, value, line)
        if projectLoaded:
            # description part if so
            match = re.search(descriptionRegexp, line)
            if match is not None:
                # description is in the line
                leadingPart = line[:match.start()]
                trailingPart = line[match.end():]
                for dline in description:
                    result.append(leadingPart + dline + trailingPart)
            else:
                result.append(line)
        else:
            result.append(line)

    return '\n'.join(result)


def getDefaultTemplate():
    """Provides a body (i.e. help) of the default template file"""
    return """#
# This template will be used when a new file is created.
#
# Codimension supports an IDE-wide template file and project-specific template
# files for each project. If a project is loaded then codimension checks the
# project-specific template file and IDE-wide one in this order. The first one
# found is used to create a new file. If no project is loaded then only the
# IDE-wide template file is checked.
# The IDE-wide template file is stored in the codimension settings directory
# while project-specific template files are stored in the top project
# directory. In both cases the template file is called 'template.py'.
#
# The following variables will be replaced with actual values if
# they are found in the template:
#
# $projectdate     Project creation date     (*)
# $author          Project author            (*)
# $license         Project license           (*)
# $copyright       Project copyright string  (*)
# $version         Project version           (*)
# $email           Project author e-mail     (*)
# $description     Project description       (*)
# $date            Current date
# $time            Current time
# $user            Current user name
#
# Note: variables marked with (*) are available only for the project-specific
#       templates. The values for the variables are taken from the project
#       properties dialogue.
#"""


# Dynamic mixin at runtime:
# http://stackoverflow.com/questions/8544983/
#        dynamically-mixin-a-base-class-to-an-instance-in-python
def extendInstance(obj, cls):
    base_cls = obj.__class__
    base_cls_name = obj.__class__.__name__
    obj.__class__ = type(base_cls_name, (base_cls, cls), {})
