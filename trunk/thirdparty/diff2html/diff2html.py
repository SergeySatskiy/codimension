#! /usr/bin/python
# vim: fileencoding=utf8 tabstop=4 shiftwidth=4
# coding=utf-8
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Transform a unified diff from stdin to a colored
# side-by-side HTML page on stdout.
#
# Authors: Olivier Matz <zer0@droids-corp.org>
#          Alan De Smet <adesmet@cs.wisc.edu>
#          Sergey Satskiy <sergey.satskiy@gmail.com>
#          scito <info at scito.ch>
#          Alex Quinn <http://www.alexquinn.org>
#
# Inspired by diff2html.rb from Dave Burt <dave (at) burt.id.au>
# (mainly for html theme)

import sys, re, htmlentitydefs, codecs, datetime, contextlib, optparse, StringIO
from xml.sax.saxutils import quoteattr
from utils.globals import GlobalData
try:
    from simplediff import diff
except ImportError:
    # There is no need in this output for codimension. codimension uses word diff
    # sys.stderr.write("info: simplediff module not found, only linediff is available\n")
    # sys.stderr.write("info: it can be downloaded at https://github.com/paulgb/simplediff\n")
    pass


def converttohex( value ):
    " Converts to a 2 digits representation "
    result = hex( value ).replace( "0x", "" )
    if len( result ) == 1:
        return "0" + result
    return result

def toCSSColor( color ):
    " Converts the color to the CSS format "
    r, g, b, a = color.getRgb()
    return "#" + converttohex( r ) + converttohex( g ) + converttohex( b )



skin = GlobalData().skin

CSS_RULES = {
    u'span.diffchanged2' : u'background:' + toCSSColor( skin.diffchanged2Paper ) + u';color:' + toCSSColor( skin.diffchanged2Color ),
    u'span.diffponct'    : u'color:' + toCSSColor( skin.diffponctColor ),
    u'table'             : u'border:0px;border-collapse:collapse;width:98%;font-size:' + str( skin.nolexerFont.pointSize() ) + 'pt; font-family:"' + skin.nolexerFont.family() + '";',
    u'td.diffline'       : u'vertical-align:top;color:' + toCSSColor( skin.difflineColor ),
    u'th'                : u'background:' + toCSSColor( skin.diffthPaper ) + u';color:' + toCSSColor( skin.diffthColor ),
    u'tr.diffadded'      : u'vertical-align:top;background:' + toCSSColor( skin.diffaddedPaper ),
    u'tr.diffchanged'    : u'vertical-align:top;background:' + toCSSColor( skin.diffchangedPaper ) + u';color:' + toCSSColor( skin.diffchangedColor ),
    u'tr.diffcomment'    : u'font-style:italic',
    u'tr.diffdeleted'    : u'vertical-align:top;background:' + toCSSColor( skin.diffdeletedPaper ),
    u'tr.diffhunkinfo'   : u'vertical-align:top;text-align:center;background:' + toCSSColor( skin.diffhunkinfoPaper ) + u';color:' + toCSSColor( skin.diffhunkinfoColor ),
    u'tr.diffunmodified' : u'vertical-align:top;background:' + toCSSColor( skin.diffunmodifiedPaper ) + u';color:' + toCSSColor( skin.diffunmodifiedColor )
}
# Color scheme:  http://colorschemedesigner.com/#2m61L9FWqCkzc

# CSS standard recommends (!= requires) quoting font family with spaces, e.g., "Lucida Console"
# http://www.w3.org/TR/CSS21/fonts.html#propdef-font-family

# Create a mapping from these CSS selectors to ones with meaningless single-letter class
# names.  This is used only if the user requests minified HTML.
CSS_ABBREVIATIONS = dict((k,k) for k in CSS_RULES if "." not in k)
CSS_ABBREVIATIONS.update((s,s.split(".")[0] + "." + chr(97+i)) for (i,s) in enumerate(
                           c for c in sorted(CSS_RULES, key=lambda c:c.split(".")[-1])
                           if "." in c))
# Ex:  {'table':'table', 'th':'th', 'tr.diffadded':'tr.a', 'tr.diffchanged':'tr.b', ...}

LANG      = "en"
DESC      = "File comparison"
DIFFON    = "\x01"       # signifies beginning of part of text that was changed
DIFFOFF   = "\x02"       # signifies end of part of text that was changed
WORDBREAK = " \t;.,/):-" # Characters we're willing to word wrap on
DIFF2HTML_URL = "http://git.droids-corp.org/gitweb/?p=diff2html.git"

HTML_HEADER_FORMAT = """<!DOCTYPE html>
<html lang="{lang}" dir="ltr">
<head>
    <meta charset="{encoding}">
    <meta name="generator" content="diff2html.py ({diff2html_url})">
    <title>HTML Diff {input_file_name}</title>
    <link rel="shortcut icon" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQAgMAAABinRfyAAAACVBMVEXAAAAAgAD///+K/HwIAAAAJUlEQVQI12NYBQQM2IgGBQ4mCIEQW7oyK4phampkGIQAc1G1AQCRxCNbyW92oQAAAABJRU5ErkJggg==" type="image/png">
    <meta property="dc:language" content="{lang}">
    <meta property="dc:modified" content="{modified_date}">
    <meta name="description" content="{desc}">
    <meta property="dc:abstract" content="{desc}">
    {style_section}
</head>
<body bgcolor='""" + toCSSColor( skin.nolexerPaper ) + """'>
"""

#HTML_FOOTER_FORMAT = """
#<footer><p>Modified at {modification_time}. HTML formatting created by <a href={diff2html_url_quoted}>diff2html</a>.</p></footer>
#</body>
#</html>
#"""
HTML_FOOTER_FORMAT = """</body></html>"""



def main():
    options = parse_command_line_options()

    if options.input_file_name:
        input_file = codecs.open(options.input_file_name, "r", options.encoding)
    else:
        input_file = codecs.getreader(options.encoding)(sys.stdin) # Use default:  stdin

    doc = Document(
        filename=options.output_file_name,
        encoding = options.encoding,
        input_file_name = options.input_file_name,
        inline_style = options.inline_style,
        minify = options.minify,
        exclude_headers = options.exclude_headers,
        show_hunk_infos = options.show_hunk_infos,
        line_size = options.line_size,
        tab_size = options.tab_size,
        show_cr = options.show_cr,
        algorithm = options.algorithm,
    )
    process(input_file, doc)


def process(input_file, doc):
    line_pairs = []
    line_numbers = [0,0]
    num_added_lines = num_deleted_lines = 0

    while True:
        line = input_file.readline()
        if line == "":
            break
        m = re.match(r'^--- (.*)', line)
        if m:
            doc.empty_buffer(line_pairs, line_numbers, num_added_lines, num_deleted_lines)
            num_added_lines = num_deleted_lines = 0
            filename_old = m.groups()[0]
            while True:
                line = input_file.readline()
                m = re.match(r'^\+\+\+ (.*)', line)
                if m:
                    filename_new = m.groups()[0]
                    break
            doc.add_filenames(filename_old, filename_new)
            hunks = (Hunk(), Hunk())
        else:

            m = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*)", line)
            # About the unified diff format:  http://www.artima.com/weblogs/viewpost.jsp?thread=164293
            if m is None and line.startswith("+"):
                num_added_lines += 1
                hunks[1].size -= 1
                line_pairs.append((None, line[1:]))
            elif m is None and line.startswith("-"):
                num_deleted_lines += 1
                hunks[0].size -= 1
                line_pairs.append((line[1:], None))
            else:
                doc.empty_buffer(line_pairs, line_numbers, num_added_lines, num_deleted_lines)
                num_added_lines = num_deleted_lines = 0
                if m:
                    hunk_data = [x=="" and 1 or int(x) for x in m.groups()]
                    hunks[0].offset, hunks[0].size, hunks[1].offset, hunks[1].size = hunk_data
                    line_numbers = [hunks[0].offset, hunks[1].offset]
                    doc.add_hunk_indicator(hunks, at_start=(max(line_numbers)==1))

                elif hunks[0].size == 0 == hunks[1].size == 0:
                    doc.add_comment(line)

                elif line.startswith(" ") and hunks[0].size and hunks[1].size:
                    hunks[0].size -= 1
                    hunks[1].size -= 1
                    line_pairs.append((line[1:], line[1:]))
                else:
                    doc.add_comment(line)

    doc.empty_buffer(line_pairs, line_numbers, num_added_lines, num_deleted_lines)
    doc.finish()

class Document(object):
    """
    Manages building an HTML document.

    This encapsulates most of the user's settings and mediates access to the output file.
    """
    def __init__(self, filename, encoding, input_file_name, inline_style, minify, exclude_headers,
                                            show_hunk_infos, line_size, algorithm, tab_size, show_cr):
        self._outfile = OutFile(filename, encoding)
        self._encoding = encoding
        self._input_filename = input_file_name
        self._inline_style = inline_style
        self._minify = minify
        self._exclude_headers = exclude_headers
        self._show_hunk_infos = show_hunk_infos
        self._line_size = line_size
        self._algorithm = algorithm
        self._tab_size = tab_size
        self._show_cr = show_cr
        self._start_time = datetime.datetime.now()
        self._nest_level = 1
        self._last_written_was_text = False

        self._start()

    def _start(self):
        if not self._exclude_headers:
            if self._inline_style:
                style_section = ""
            else:
                css_rules = CSS_RULES
                if self._minify:
                    css_rules = dict((CSS_ABBREVIATIONS[k],v) for (k,v) in CSS_RULES.iteritems())
                style_section = "\n".join("%s { %s }"%(k,v) for (k,v) in css_rules.iteritems())
                style_section = "<style>\n" + style_section + "\n</style>"

            html_header = HTML_HEADER_FORMAT.format(
                input_file_name=self._input_filename,
                encoding=self._encoding,
                desc=DESC,
                blank="",
                modified_date="%s+01:00"%self._start_time.isoformat(),
                lang=LANG,
                diff2html_url = DIFF2HTML_URL,
                style_section = style_section,
            )
            if self._minify:
                html_header = "".join(line.strip() for line in html_header.splitlines())
            self._write(html_header)

        html = open_tag("table.diff", inline_style=self._inline_style, minify=self._minify)
        if not self._minify:
            html = " "*12 + html + "\n" + " "*4
        self._write(html)

    def _write(self, text):
        self._outfile.write(text)

    def _write_open_tag(self, css_selector, **attrs):
        html = open_tag(css_selector, inline_style=self._inline_style, minify=self._minify, **attrs)
        if not self._minify:
            html = "\n" + " "*self._nest_level + html
        self._write(html)
        self._nest_level += 1
        self._last_written_was_text = False

    def _write_close_tag(self, css_selector):
        # According to the HTML5 standard, </td> and </tr> are optional.
        #     http://dev.w3.org/html5/html-author/#unquoted-attr
        # We will omit them if and only if the user requested minified HTML output.
        tag_name = css_selector.split(".")[0]
        if not self._minify or tag_name not in ("td", "tr"):
            html = "</" + tag_name + ">"
            self._nest_level -= 1
            if not self._minify:
                if not self._last_written_was_text:
                    html = "\n" + " "*self._nest_level + html
            self._write(html)
        self._last_written_was_text = False

    def add_comment(self, s):
        with self._open_tag("tr.diffcomment"):
            with self._open_tag("td", colspan="4"):
                self._add_content_text(s)

    def add_filenames(self, filename_old, filename_new):
        with self._open_tag("tr"):
            for filename in (filename_old, filename_new):
                with self._open_tag("th", colspan="2"):
                    self._add_content_text(filename, line_size=self._line_size)

    def add_hunk_indicator(self, hunks, at_start):
        if self._show_hunk_infos or not at_start:  # don't add ellipsis at start
            with self._open_tag("tr.diffhunkinfo"):
                for hunk in hunks:
                    with self._open_tag("td", colspan="2"):
                        if self._show_hunk_infos:
                            self._add_content_text('Offset %d, %d lines modified'%(hunk.offset, hunk.size))
                        else:
                            self._write(u'\N{VERTICAL ELLIPSIS}')

    @contextlib.contextmanager
    def _open_tag(self, css_selector, **attrs):
        self._write_open_tag(css_selector, **attrs)
        yield
        self._write_close_tag(css_selector)

    def add_line_with_line_numbers(self, line_numbers, line_left, line_right):
        if line_left == None and line_right == None:
            tr_class = "tr.diffunmodified"
        elif line_left == None or line_left == "":
            tr_class = "tr.diffadded"
        elif line_right == None or line_left == "":
            tr_class = "tr.diffdeleted"
        elif line_left == line_right:
            tr_class = "tr.diffunmodified"
        else:
            tr_class = "tr.diffchanged"
            if self._algorithm == 1:
                line_left, line_right = diff_changed_words(line_right, line_left), diff_changed_words(line_left, line_right)
            elif self._algorithm == 2:
                line_left, line_right = diff_changed(line_right, line_left), diff_changed(line_left, line_right)
            else: # default
                line_left, line_right = linediff(line_left, line_right)

        with self._open_tag(tr_class):
            for i,s in enumerate((line_left, line_right)):
                if s is not None and s != "":
                    # s may be "..."
                    with self._open_tag("td.diffline"):
                        self._add_content_text("%d"%line_numbers[i])
                    with self._open_tag("td"):
                        self._add_content_text(s, line_size=self._line_size, ponct=1)
                    line_numbers[i] += 1
                else:
                    with self._open_tag("td", colspan="2"):
                        self._write(" ")

    def empty_buffer(self, line_pairs, line_numbers, num_added_lines, num_deleted_lines):
        if num_deleted_lines == 0 or num_added_lines == 0:
            for line_left,line_right in line_pairs:
                self.add_line_with_line_numbers(line_numbers, line_left, line_right)
        else:
            lines_left,lines_right = ([lines[i] for lines in line_pairs if lines[i] is not None] for i in (0,1))
            for i in xrange(max(len(lines_left), len(lines_right))):
                line_left  = lines_left[i]  if i < len(lines_left)  else ""
                line_right = lines_right[i] if i < len(lines_right) else ""
                self.add_line_with_line_numbers(line_numbers, line_left, line_right)
        del line_pairs[:]

    def finish(self):
        self._write_close_tag("table")
        if not self._exclude_headers:
            html_footer = HTML_FOOTER_FORMAT.format(
                modification_time=self._start_time.strftime("%d.%m.%Y"),
                diff2html_url_quoted = quoteattr(DIFF2HTML_URL)
            )
            if self._minify:
                html_footer = "".join(line.strip() for line in html_footer.splitlines())
            self._write(html_footer)

    def _add_content_text(self, s, line_size=0, ponct=0):
        num_chars_in_current_word = 0
        line_in_progress = LineInProgress(inline_style=self._inline_style, minify=self._minify)

        for char in s:
            if char == DIFFON:     # used by diffs
                line_in_progress.set_in_change(True)
            elif char == DIFFOFF:  # used by diffs
                line_in_progress.set_in_change(False)
            elif char in u'&<>':  # make it HTML-safe
                line_in_progress.write("&" + htmlentitydefs.codepoint2name[ord(char)] + ";")
            elif char == "\t" and ponct == 1:  # make tab characters visible
                cols_left_in_this_tab_stop = self._tab_size-(num_chars_in_current_word%self._tab_size)
                if cols_left_in_this_tab_stop == 0:
                    cols_left_in_this_tab_stop = self._tab_size
                line_in_progress.write(u'\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}', is_whitespace_mark=True)
                line_in_progress.write(u'\N{NO-BREAK SPACE}'*(cols_left_in_this_tab_stop-1))
            elif char == " " and ponct == 1:  # make spaces visible
                line_in_progress.write(u'\N{MIDDLE DOT}', is_whitespace_mark=True)
            elif char == "\n" and ponct == 1 and self._show_cr:  # make carriage returns visible
                line_in_progress.write(u'\N{PILCROW SIGN}', is_whitespace_mark=True) # paragraph mark
            elif char not in "\n\r":   # other text (but never \r or \n)
#            else:   # other text
                line_in_progress.write(char)
                num_chars_in_current_word += 1

            if line_size and (WORDBREAK.count(char) == 1 or num_chars_in_current_word > line_size):
                line_in_progress.write_zero_width_space()
                num_chars_in_current_word = 0

        self._write( line_in_progress.get_text() )
        self._last_written_was_text = True

class LineInProgress(object):
    """
    Manages the state while converting a content string to the HTML that will be displayed.

    The primary purpose is to ensure that we don't add consecutive spans with the same class.
    Text in the changed part is wrapped in <span class="diffchanged"> to highlight it in yellow.
    Markers for whitespace characters are wrapped in <span.diffponct> to give them a distinctive font.
    The spans may be nexted in either order.
    """
    def __init__(self, inline_style, minify):
        self._parts = []        # segments of this line, to be joined when we're done.
        self._in_change = False # flag to track if next text is part of changed portion of line
        self._inline_style = inline_style
        self._open_styles = []  # stack to track which spans are currently open
        self._minify = minify

    def write(self, text, is_whitespace_mark=False):
        style_in_changed_part = "span.diffchanged2"
        style_whitespace_mark = "span.diffponct"

        # Close spans until no spans are open that don't match the needed formatting.
        while (style_whitespace_mark in self._open_styles and not is_whitespace_mark) or \
              (style_in_changed_part in self._open_styles and not self._in_change):
            self._parts.append("</span>")
            self._open_styles.pop()

        # Open span for in_changed, if needed.
        if self._in_change and style_in_changed_part not in self._open_styles:
            self._write_open_tag(style_in_changed_part)
            self._open_styles.append(style_in_changed_part)

        # Open span for whitespace mark, if needed.
        if is_whitespace_mark and style_whitespace_mark not in self._open_styles:
            self._write_open_tag(style_whitespace_mark)
            self._open_styles.append(style_whitespace_mark)

        assert len(self._open_styles) <= 2
        assert len(self._open_styles) <= 1 or self._open_styles[0] != self._open_styles[1]

        self._parts.append(text)

    def write_zero_width_space(self):
        return
        self._parts.append(u'\N{ZERO WIDTH SPACE}') # no need to switch style since invisible

    def _write_open_tag(self, css_selector):
        html = open_tag(css_selector, inline_style=self._inline_style, minify=self._minify)
        self._parts.append(html)

    def get_text(self):
        return "".join(self._parts) + "</span>"*len(self._open_styles)

    def set_in_change(self, value):
        self._in_change = value

class OutFile(object):
    """
    Manages encoding of output.

    Characters that cannot be encoded using the selected encoding will be converted to named
    HTML entities (e.g., "&nbsp;"), if possible, or else numeric entities (e.g., &#a0;).
    """
    def __init__(self, filename, encoding):
        if isinstance( filename, StringIO.StringIO ):
            self._file = filename
        else:
            self._file = open(filename, "wb") if filename else sys.stdout
        self._encoding = encoding

        # See which of the HTML entities of interest are supported by this encoding.
        self._char_replacements = {}
        for code_point,html_enity_name in htmlentitydefs.codepoint2name.iteritems():
            char = unichr(code_point)
            try:
                char.encode(encoding)
            except UnicodeEncodeError:
                self._char_replacements[char] = "&" + html_enity_name + ";"
        self._char_replacements.update((unichr(i),".") for i in xrange(32) if unichr(i) not in u"\t\n\r")
        self._dbg_saw_html = False

    def write(self, s):
        s = "".join(self._char_replacements.get(char, char) for char in s)
        s = s.encode(self._encoding)
        self._file.write(s)

class Hunk(object):
    def __init__(self):
        self.offset = 0
        self.size = 0

def parse_command_line_options():
    parser = optparse.OptionParser(description="Transform a unified diff from stdin to a colored side-by-side HTML page.",
                      epilog="Note:  stdout may not work with UTF-8, instead use -o option.")
    parser.add_option("-i", metavar="F", dest="input_file_name",
                      help="set input file (default: stdin)")
    parser.add_option("-e", metavar="E", dest="encoding", default="utf-8",
                      help="set file encoding (default: utf-8)")
    parser.add_option("-o", "--output", metavar="F", dest="output_file_name",
                      help="set output file (default: stdout)")
    parser.add_option("-x", "--exclude-html-headers", action="store_true", dest="exclude_headers",
                      help="exclude html header and footer")
    parser.add_option("-s", "--inline-style", action="store_true", dest="inline_style",
                      help="style attributes inline instead of CSS classes")
    parser.add_option("-m", "--minify", action="store_true", dest="minify",
                      help="generate HTML that is more compact, but less readable")
    parser.add_option("-t", "--tabsize", metavar="N", type="int", dest="tab_size", default=8,
                      help="set tab size (default: 8)")
    parser.add_option("-l", "--linesize", metavar="N", type="int", default=20, dest="line_size",
                      help="set maximum line size is there is no word break (default: 20)")
    parser.add_option("-r", "--show-cr", action="store_true", dest="show_cr",
                      help="show \\r characters")
    parser.add_option("-k", "--show-hunk-infos", action="store_true", dest="show_hunk_infos",
                      help="show hunk infos")
    parser.add_option("-a", "--algorithm", metavar="A", choices=(0, 1, 2), default=0, dest="algorithm",
                      help="line diff algorithm (0: linediff characters, 1: word, 2: simplediff characters) (default: 0)")
    (options,args) = parser.parse_args() # [pylint] args is unused : pylint:disable=W0612

    if not options.input_file_name and sys.stdin.isatty():
        parser.print_help()
        sys.exit(1)

    return options

def sane(x):
    return u"".join((char if ord(char) >= 32 or char in "\t\n\r" else ".") for char in x)

def linediff(s, t):
    '''
    Original line diff algorithm of diff2html. It's character based.
    '''
    if len(s):
        s = unicode(reduce(lambda x, y:x+y, [ sane(c) for c in s ]))
    if len(t):
        t = unicode(reduce(lambda x, y:x+y, [ sane(c) for c in t ]))

    m, n = len(s), len(t)
    d = [[(0, 0) for i in range(n+1)] for i in range(m+1)]

    d[0][0] = (0, (0, 0))
    for i in range(m+1)[1:]:
        d[i][0] = (i,(i-1, 0))
    for j in range(n+1)[1:]:
        d[0][j] = (j,(0, j-1))

    for i in range(m+1)[1:]:
        for j in range(n+1)[1:]:
            if s[i-1] == t[j-1]:
                cost = 0
            else:
                cost = 1
            d[i][j] = min((d[i-1][j][0] + 1, (i-1, j)),
                          (d[i][j-1][0] + 1, (i, j-1)),
                          (d[i-1][j-1][0] + cost, (i-1, j-1)))

    l = []
    coord = (m, n)
    while coord != (0, 0):
        l.insert(0, coord)
        x, y = coord
        coord = d[x][y][1]

    l1 = []
    l2 = []

    for coord in l:
        cx, cy = coord
        child_val = d[cx][cy][0]

        father_coord = d[cx][cy][1]
        fx, fy = father_coord
        father_val = d[fx][fy][0]

        differences = (cx-fx, cy-fy)

        if differences == (0, 1):
            l1.append("")
            l2.append(DIFFON + t[fy] + DIFFOFF)
        elif differences == (1, 0):
            l1.append(DIFFON + s[fx] + DIFFOFF)
            l2.append("")
        elif child_val-father_val == 1:
            l1.append(DIFFON + s[fx] + DIFFOFF)
            l2.append(DIFFON + t[fy] + DIFFOFF)
        else:
            l1.append(s[fx])
            l2.append(t[fy])

    r1, r2 = (reduce(lambda x, y:x+y, l1), reduce(lambda x, y:x+y, l2))
    return r1, r2

def diff_changed(old, new):
    '''
    Returns the differences basend on characters between two strings
    wrapped with DIFFON and DIFFOFF using `diff`.
    '''
    con = {'=': (lambda x: x),
           '+': (lambda x: DIFFON + x + DIFFOFF),
           '-': (lambda x: '')}
    return "".join([(con[a])("".join(b)) for a, b in diff(old, new)])

def word_diff(old, new):
    '''
    Returns the difference between the old and new strings based on words. Punctuation is not part of the word.

    Params:
        old the old string
        new the new string

    Returns:
        the output of `diff` on the two strings after splitting them
        on whitespace (a list of change instructions; see the docstring
        of `diff`)
    '''
    separator_pattern = r'(\W+)'
    return diff(re.split(separator_pattern, old, flags=re.UNICODE), re.split(separator_pattern, new, flags=re.UNICODE))

def diff_changed_words(old, new):
    '''
    Returns the difference between two strings based on words (see `word_diff`)
    wrapped with DIFFON and DIFFOFF.

    Returns:
        the output of the diff expressed delimited with DIFFON and DIFFOFF.
    '''
    con = {'=': (lambda x: x),
           '+': (lambda x: DIFFON + x + DIFFOFF),
           '-': (lambda x: '')}
    return "".join([(con[a])("".join(b)) for a, b in word_diff(old, new)])

def open_tag(css_selector, inline_style, minify, **attrs):
    """
    Create opening tag using either a class attribute or a style attribute
    """
    tag,css_class = re.match(r'^(\w+)(?:\.(\w+))?$', css_selector).groups()

    if inline_style:
        style = ";".join(CSS_RULES[s] for s in (tag, css_selector) if s in CSS_RULES)
        if style:
            attrs["style"] = style
    elif css_class:
        if minify and "." in css_selector:
            if css_selector in CSS_ABBREVIATIONS:
                css_class = CSS_ABBREVIATIONS[css_selector].split(".")[1]
            else:
                css_class = None
        if css_class:
            attrs["class"] = css_class

    quote_fn = quote_attr_if_needed if minify else quoteattr

    if tag == "table":
        return "<" + tag + " align='center'" + "".join(" %s=%s"%(k, quote_fn(v)) for (k,v) in attrs.iteritems()) + ">"
    return "<" + tag + "".join(" %s=%s"%(k, quote_fn(v)) for (k,v) in attrs.iteritems()) + ">"

def quote_attr_if_needed(s):
    # According to the HTML5 standard, attributes that do not contain ["'=<>`] may be used as is, without quotes.
    # http://dev.w3.org/html5/html-author/#unquoted-attr
    if not any(char in s for char in ('"', "'", "=", "<", ">", "`")):
        return s
    else:
        return quoteattr(s)

def parse_from_memory(txt, exclude_headers, show_hunk_infos):
    " Parses diff from memory and returns a string with html "
    input_stream = StringIO.StringIO(txt)
    output_stream = StringIO.StringIO()

    doc = Document(
        filename=output_stream,
        encoding = "utf-8",
        input_file_name = "unknown",
        inline_style = False,
        minify = False,
        exclude_headers = exclude_headers,
        show_hunk_infos = show_hunk_infos,
        line_size = 20,
        tab_size = 4,
        show_cr = False,
        algorithm = 1,
    )
    process(input_stream, doc)
    return output_stream.getvalue()


if __name__ == "__main__":
    main()
