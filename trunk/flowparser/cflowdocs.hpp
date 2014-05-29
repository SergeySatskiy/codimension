/*
 * codimension - graphics python two-way code editor and analyzer
 * Copyright (C) 2014  Sergey Satskiy <sergey.satskiy@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * $Id$
 *
 * Python extension module - various documentation strings
 */

#ifndef CFLOWDOCS_HPP
#define CFLOWDOCS_HPP

// Module docstring
#define MODULE_DOC \
"Codimension Control Flow module types and procedures"

// getControlFlowFromMemory( content ) docstring
#define GET_CF_MEMORY_DOC \
"Provides the control flow object for the given content"

// getControlFlowFromFile( fileName ) docstring
#define GET_CF_FILE_DOC \
"Provides the control flow object for the given file"

// Fragment()
#define CREATE_FRAGMENT_DOC \
"Creates the Fragment class instance"

// BangLine()
#define CREATE_BANGLINE_DOC \
"Creates the BangLine class instance"

// EncodingLine()
#define CREATE_ENCODINGLINE_DOC \
"Creates the EncodingLine class instance"


// Comment()
#define CREATE_COMMENT_DOC \
"Creates the Comment class instance"


// Fragment class docstring
#define FRAGMENT_DOC \
"Represents a single text fragment of a python file"


// getLineRange() docstring
#define GETLINERANGE_DOC \
"Provides line range for the fragment"

// getContent(...) docstring
#define GETCONTENT_DOC \
"Provides the content of the fragment"

// getLineContent(...) docstring
#define GETLINECONTENT_DOC \
"Provides a content with complete lines including leading spaces if so"


// BangLine class docstring
#define BANGLINE_DOC \
"Represents a line with the bang notation"

// BangLine::getDisplayValue()
#define BANGLINE_GETDISPLAYVALUE_DOC \
"Provides the actual bang line"


// EncodingLine class docstring
#define ENCODINGLINE_DOC \
"Represents a line with the file encoding"

// EncodingLine::getDisplayValue()
#define ENCODINGLINE_GETDISPLAYVALUE_DOC \
"Provides the encoding"


// Comment class docstring
#define COMMENT_DOC \
"Represents a one or many lines comment"

// Comment::getDisplayValue()
#define COMMENT_GETDISPLAYVALUE_DOC \
"Provides the comment without trailing spaces"

// Comment::niceStringify()
#define COMMENT_NICESTRINGIFY_DOC \
"Returns a string representation with new lines and shifts"


#endif

