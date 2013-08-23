""" Global variables for PyMetrics.

    $Id: globals.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import token
import tokenize

# our token types
KEYWORD     = token.NT_OFFSET + 1
TEXT        = token.NT_OFFSET + 2
WS          = token.NT_OFFSET + 3
DOCSTRING   = token.NT_OFFSET + 4
VARNAME     = token.NT_OFFSET + 5
CLASSNAME   = token.NT_OFFSET + 6
FCNNAME     = token.NT_OFFSET + 7
INLINE      = token.NT_OFFSET + 8
UNKNOWN     = token.NT_OFFSET + 9
SEMTOKEN    = token.NT_OFFSET + 10  # to distinguish semantic tokens
NONTOKEN    = token.NT_OFFSET + 11  # to distinguish non-tokens
DECORATOR   = token.NT_OFFSET + 12  # to indicate decorator token
NUMBER      = token.NUMBER
OP          = token.OP
STRING      = token.STRING
COMMENT     = tokenize.COMMENT
NAME        = token.NAME
ERRORTOKEN  = token.ERRORTOKEN
ENDMARKER   = token.ENDMARKER
INDENT      = token.INDENT
DEDENT      = token.DEDENT
NEWLINE     = token.NEWLINE
EMPTY       = tokenize.NL

# new token types added to allow for character representation of new codes

token.tok_name[KEYWORD] = "KEYWORD"     # one of Python's reserved words
token.tok_name[TEXT] = "TEXT"           # obsolete - but kept for compatibility
token.tok_name[WS] = "WS"               # some form of whitespace
token.tok_name[DOCSTRING] = "DOCSTRING" # literal that is also doc string
token.tok_name[VARNAME] = "VARNAME"     # name that is not keyword
token.tok_name[CLASSNAME] = "CLASSNAME" # name defined in class statment
token.tok_name[FCNNAME] = "FCNNAME"     # name defined in def statement
token.tok_name[INLINE] = "INLINE"       # comment that follows other text on same line
token.tok_name[UNKNOWN] = "UNKNOWN"     # Unknown semantic type - this should not occur
token.tok_name[DECORATOR] = 'DECORATOR' # Decorator marker
