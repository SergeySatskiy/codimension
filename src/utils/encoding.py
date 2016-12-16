#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016 Sergey Satskiy <sergey.satskiy@gmail.com>
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

# There is no way to query a complete list of the supported codecs at run-time.
# So there is the list below.
# Note: aliases are not included into the list (could be retrieved at run-time)
# Note: there could be user registered codecs as well
# Note: the list is copied from the python documentation:
#       https://docs.python.org/3/library/codecs.html
SUPPORTED_CODECS = ['ascii', 'big5', 'big5hkscs', 'cp037', 'cp273', 'cp424',
                    'cp437', 'cp500', 'cp720', 'cp737', 'cp775', 'cp850',
                    'cp852', 'cp855', 'cp856', 'cp857', 'cp858', 'cp860',
                    'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866',
                    'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950',
                    'cp1006', 'cp1026', 'cp1125', 'cp1140', 'cp1250',
                    'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255',
                    'cp1256', 'cp1257', 'cp1258', 'cp65001', 'euc_jp',
                    'euc_jis_2004', 'euc_jisx0213', 'euc_kr', 'gb2312',
                    'gbk', 'gb18030', 'hz', 'iso2022_jp', 'iso2022_jp_1',
                    'iso2022_jp_2', 'iso2022_jp_2004', 'iso2022_jp_3',
                    'iso2022_jp_ext', 'iso2022_kr', 'latin_1', 'iso8859_2',
                    'iso8859_3', 'iso8859_4', 'iso8859_5', 'iso8859_6',
                    'iso8859_7', 'iso8859_8', 'iso8859_9', 'iso8859_10',
                    'iso8859_11', 'iso8859_13', 'iso8859_14', 'iso8859_15',
                    'iso8859_16', 'johab', 'koi8_r', 'koi8_t', 'koi8_u',
                    'kz1048', 'mac_cyrillic', 'mac_greek', 'mac_iceland',
                    'mac_latin2', 'mac_roman', 'mac_turkish', 'ptcp154',
                    'shift_jis', 'shift_jis_2004', 'shift_jisx0213',
                    'utf_32', 'utf_32_be', 'utf_32_le',
                    'utf_16', 'utf_16_be', 'utf_16_le',
                    'utf_7', 'utf_8', 'utf_8_sig']


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
