# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2018  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Markdown support"""

import os.path
import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_mimetype
from pygments.formatters import HtmlFormatter
from utils.fileutils import getMagicMimeFromBuffer


# Notes:
# QTextBrowser is used to display the generated HTML. Unfortunately,
# QTextBrowser supports only a very specific set of attributes and sometimes
# renders the content quite unexpectedly. In particular, <div ...> are not
# really supported. So, styling of the markdown code blocks and quotes are done
# via tables.
# QWebEngineView (which supposedly is better in terms of rendering) does not
# work on all platforms out of the box (at least when used via PyQt).
# See also: http://www.prog.org.ru/topic_7398_0.html


CODE_BLOCK_STYLE = 'style="border-width:1px;border-style:solid;' \
                   'border-color:#ccc;margin-top:.5em;margin-bottom:.5em;"'
PRE_WRAP_START = '''<table cellspacing="0" cellpadding="8" width="100%" align="left"
       bgcolor="#f8f8f8"''' + CODE_BLOCK_STYLE + '><tr><td>'
PRE_WRAP_END = '</td></tr></table>'

QUOTE_TABLE = '<table cellspacing="0" width="100%" align="left" ' \
              'style="margin-top:.4em;margin-bottom:.4em;">'


def get_lexer(text, lang):
    """Tries to get the lexer for the text whether the lang is provided or not"""
    if lang:
        try:
            return get_lexer_by_name(lang, stripall=False)
        except:
            pass
        return None

    # No language provided, try to guess
    mime = getMagicMimeFromBuffer(text.strip())
    if mime:
        try:
            return get_lexer_for_mimetype(mime, stripall=False)
        except:
            pass

        # The pygments data sometimes miss mime options provided by python magic
        # library
        if mime.startswith('text/'):
            try:
                return get_lexer_for_mimetype(mime.replace('text/',
                                                           'application/'),
                                              stripall=False)
            except:
                pass

    return None


def block_code(text, lang, inlinestyles=False, linenos=False):
    """Renders a code block"""
    lexer = get_lexer(text, lang)
    if lexer:
        try:
            formatter = HtmlFormatter(noclasses=inlinestyles, linenos=linenos)
            code = highlight(text, lexer, formatter)
            return ''.join([PRE_WRAP_START, '<pre>',
                            code.replace('125%', '100%'), '</pre>',
                            PRE_WRAP_END, '\n'])
        except:
            pass

    return ''.join([PRE_WRAP_START, '<pre>', mistune.escape(text),
                    '</pre>', PRE_WRAP_END, '\n'])


class CDMMarkdownRenderer(mistune.Renderer):

    """Codimension custom markdown renderer"""

    def __init__(self, fileName):
        mistune.Renderer.__init__(self, inlinestyles=True, linenos=False)
        self.__fileName = fileName

    def block_code(self, text, lang):
        """Custom block code renderer"""
        # renderer has an options
        inlinestyles = self.options.get('inlinestyles', False)
        linenos = self.options.get('linenos', False)
        return block_code(text, lang, inlinestyles, linenos)

    def block_quote(self, text):
        """Custom block quote renderer"""
        # The text comes as \n separated paragraphs
        return ''.join(['<p>', QUOTE_TABLE,
                        '<tr><td bgcolor="#ccc" width="4"></td>',
                        '<td width="8"></td>',
                        '<td>',
                        text.rstrip('\n')
                            .replace('</p>\n', '</p>').replace('\n', '<br/>'),
                        '</td></tr></table></p>'])

    def image(self, src, title, alt_text):
        """Custom image handler"""
        if src and self.__fileName:
            if not os.path.isabs(src):
                newSrcPath = ''.join([os.path.dirname(self.__fileName),
                                      os.path.sep, src])
                src = os.path.normpath(newSrcPath)
        return mistune.Renderer.image(self, src, title, alt_text)

    def codespan(self, text):
        """Custom code span renderer"""
        return '<u>' + mistune.Renderer.codespan(self, text) + '</u>'

    def table(self, header, body):
        """Custom table tag renderer"""
        replacement = '<table cellspacing="0" cellpadding="4"' + \
                      CODE_BLOCK_STYLE + '>'
        return mistune.Renderer.table(self, header, body).replace('<table>',
                                                                  replacement)



def renderMarkdown(text, fileName):
    """Renders the given text"""
    warnings = []
    errors = []
    renderedText = None
    try:
        renderer = CDMMarkdownRenderer(fileName)
        markdown = mistune.Markdown(renderer=renderer)
        renderedText = markdown(text)
    except Exception as exc:
        errors.append(str(exc))
    except:
        errors.append('Unknown markdown rendering exception')
    return renderedText, errors, warnings
