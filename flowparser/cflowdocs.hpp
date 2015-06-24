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

// CMLComment()
#define CREATE_CML_COMMENT_DOC \
"Creates the CMLComment class instance"

// Docstring()
#define CREATE_DOCSTRING_DOC \
"Creates the Docstring class instance"

// Decorator()
#define CREATE_DECORATOR_DOC \
"Creates the Decorator class instance"

// CodeBlock()
#define CREATE_CODEBLOCK_DOC \
"Creates the CodeBlock class instance"

// Function()
#define CREATE_FUNCTION_DOC \
"Creates the Function class instance"

// Class()
#define CREATE_CLASS_DOC \
"Creates the Class class instance"

// Break()
#define CREATE_BREAK_DOC \
"Creates the Break class instance"

// Continue()
#define CREATE_CONTINUE_DOC \
"Creates the Continue class instance"

// Return()
#define CREATE_RETURN_DOC \
"Creates the Return class instance"

// Raise()
#define CREATE_RAISE_DOC \
"Creates the Raise class instance"

// Assert()
#define CREATE_ASSERT_DOC \
"Creates the Assert class instance"

// SysExit()
#define CREATE_SYSEXIT_DOC \
"Creates the SysExit class instance"

// While()
#define CREATE_WHILE_DOC \
"Creates the While class instance"

// For()
#define CREATE_FOR_DOC \
"Creates the For class instance"

// Import()
#define CREATE_IMPORT_DOC \
"Creates the Import class instance"

// ElifPart()
#define CREATE_ELIFPART_DOC \
"Creates the ElifPart class instance"

// If()
#define CREATE_IF_DOC \
"Creates the If class instance"

// With()
#define CREATE_WITH_DOC \
"Creates the With class instance"

// ExceptPart()
#define CREATE_EXCEPTPART_DOC \
"Creates the ExceptPart class instance"

// Try()
#define CREATE_TRY_DOC \
"Creates the Try class instance"

// ControlFlow()
#define CREATE_CONTROLFLOW_DOC \
"Creates the ControlFlow class instance"


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

// CMLComment class docstring
#define CML_COMMENT_DOC \
"Represents a one or many lines CML comment"


// Docstring class docstring
#define DOCSTRING_DOC \
"Represents a docstring"

// Docstring::getDisplayValue()
#define DOCSTRING_GETDISPLAYVALUE_DOC \
"Provides the docstring without syntactic sugar"

// Decorator class docstring
#define DECORATOR_DOC \
"Represents a single decorator"

// CodeBlock class docstring
#define CODEBLOCK_DOC \
"Represents a code block"

// CodeBlock::getDisplayValue()
#define CODEBLOCK_GETDISPLAYVALUE_DOC \
"Provides the code block without trailing spaces and comments"

// Function class docstring
#define FUNCTION_DOC \
"Represents a single function"

// Class class docstring
#define CLASS_DOC \
"Represents a single class"

// Break class docstring
#define BREAK_DOC \
"Represents a single break statement"

// Continue class docstring
#define CONTINUE_DOC \
"Represents a single continue statement"

// Return class docstring
#define RETURN_DOC \
"Represents a single return statement"

// Raise class docstring
#define RAISE_DOC \
"Represents a single raise statement"

// Assert class docstring
#define ASSERT_DOC \
"Represents a single assert statement"

// SysExit class docstring
#define SYSEXIT_DOC \
"Represents a single sys.exit() call"

// While class docstring
#define WHILE_DOC \
"Represents a single while loop"

// For class docstring
#define FOR_DOC \
"Represents a single for loop"

// Import class docstring
#define IMPORT_DOC \
"Represents a single import statement"

// Import::getDisplayValue()
#define IMPORT_GETDISPLAYVALUE_DOC \
"Provides the import without trailing spaces and comments"

// ElifPart class docstring
#define ELIFPART_DOC \
"Represents a single 'elif' or 'else' branch in the if statement"

// ElifPart::getDisplayValue()
#define ELIFPART_GETDISPLAYVALUE_DOC \
"Provides the if condition without trailing spaces and comments"

// If class docstring
#define IF_DOC \
"Represents a single if statement"

// If::getDisplayValue()
#define IF_GETDISPLAYVALUE_DOC \
"Provides the if condition without trailing spaces and comments"

// With class docstring
#define WITH_DOC \
"Represents a single with statement"

// ExceptPart class docstring
#define EXCEPTPART_DOC \
"Represents a single except part"

// Try class docstring
#define TRY_DOC \
"Represents a single try statement"

// ControlFlow class docstring
#define CONTROLFLOW_DOC \
"Represents one python file content"


#endif

