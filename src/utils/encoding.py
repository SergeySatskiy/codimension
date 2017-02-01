# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Encoding related functions"""

import re
import encodings


# There is no way to query a complete list of the supported codecs at run-time.
# So there is the list below.
# Note: aliases are not included into the list (could be retrieved at run-time)
# Note: there could be user registered codecs as well
# Note: the list is copied from the python documentation:
#       https://docs.python.org/3/library/codecs.html
# Note: instead of the '_' char in the list the '-' was used: it looks nicer
SUPPORTED_CODECS = ['ascii', 'big5', 'big5hkscs', 'cp037', 'cp273', 'cp424',
                    'cp437', 'cp500', 'cp720', 'cp737', 'cp775', 'cp850',
                    'cp852', 'cp855', 'cp856', 'cp857', 'cp858', 'cp860',
                    'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866',
                    'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950',
                    'cp1006', 'cp1026', 'cp1125', 'cp1140', 'cp1250',
                    'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255',
                    'cp1256', 'cp1257', 'cp1258', 'cp65001', 'euc_jp',
                    'euc-jis-2004', 'euc-jisx0213', 'euc-kr', 'gb2312',
                    'gbk', 'gb18030', 'hz', 'iso2022-jp', 'iso2022-jp-1',
                    'iso2022-jp-2', 'iso2022-jp-2004', 'iso2022-jp-3',
                    'iso2022_jp-ext', 'iso2022-kr', 'latin-1', 'iso8859-2',
                    'iso8859-3', 'iso8859-4', 'iso8859-5', 'iso8859-6',
                    'iso8859-7', 'iso8859-8', 'iso8859-9', 'iso8859-10',
                    'iso8859-11', 'iso8859-13', 'iso8859-14', 'iso8859-15',
                    'iso8859-16', 'johab', 'koi8-r', 'koi8-t', 'koi8-u',
                    'kz1048', 'mac-cyrillic', 'mac-greek', 'mac-iceland',
                    'mac-latin2', 'mac-roman', 'mac-turkish', 'ptcp154',
                    'shift-jis', 'shift-jis-2004', 'shift-jisx0213',
                    'utf-32', 'utf-32-be', 'utf-32-le',
                    'utf-16', 'utf-16-be', 'utf-16-le',
                    'utf-7', 'utf-8', 'utf-8-sig']


def convertLineEnds(text, eol):
    """Converts the end of line characters in text to the given eol"""
    if eol == '\r\n':
        regexp = re.compile(r"(\r(?!\n)|(?<!\r)\n)")
        return regexp.sub(lambda m, eol='\r\n': eol, text)
    if eol == '\n':
        regexp = re.compile(r"(\r\n|\r)")
        return regexp.sub(lambda m, eol='\n': eol, text)
    if eol == '\r':
        regexp = re.compile(r"(\r\n|\n)")
        return regexp.sub(lambda m, eol='\r': eol, text)
    return text


def isValidEncoding(enc):
    """Checks if it is a valid encoding"""
    norm_enc = encodings.normalize_encoding(enc).lower()
    if norm_enc in SUPPORTED_CODECS:
        return True
    if norm_enc in [encodings.normalize_encoding(supp_enc)
                    for supp_enc in SUPPORTED_CODECS]:
        return True

    # Check the aliases as well
    if norm_enc in encodings.aliases.aliases:
        return True
    return False


def getNormalizedEncoding(enc):
    """Returns a normalized encoding or throws an exception"""
    if not isValidEncoding(enc):
        raise Exception('Unsupported encoding ' + enc)
    norm_enc = encodings.normalize_encoding(enc).lower()
    return encodings.aliases.aliases.get(norm_enc, norm_enc)


def areEncodingsEqual(enc_lhs, enc_rhs):
    """True if the encodings are essentially the same"""
    return getNormalizedEncoding(enc_lhs) == getNormalizedEncoding(enc_rhs)
