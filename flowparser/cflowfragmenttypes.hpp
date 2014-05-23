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
 * Python extension module - control flow fragment types
 */

#ifndef CFLOWFRAGMENTTYPES_HPP
#define CFLOWFRAGMENTTYPES_HPP


#define UNDEFINED_FRAGMENT      -1
#define FRAGMENT                0
#define BANG_LINE_FRAGMENT      1
#define ENCODING_LINE_FRAGMENT  2
#define COMMENT_FRAGMENT        3
#define FRAGMENT_WITH_COMMENTS  4
#define DOCSTRING_FRAGMENT      5
#define DECORATOR_FRAGMENT      6
#define CODEBLOCK_FRAGMENT      7
#define FUNCTION_FRAGMENT       8
#define CLASS_FRAGMENT          9
#define BREAK_FRAGMENT          10
#define CONTINUE_FRAGMENT       11
#define RETURN_FRAGMENT         12
#define RAISE_FRAGMENT          13
#define ASSERT_FRAGMENT         14
#define SYSEXIT_FRAGMENT        15
#define WHILE_FRAGMENT          16
#define FOR_FRAGMENT            17
#define IMPORT_FRAGMENT         18
#define IF_PART_FRAGMENT        19
#define IF_FRAGMENT             20
#define WITH_FRAGMENT           21
#define EXCEPT_PART_FRAGMENT    22
#define TRY_FRAGMENT            23


// Represents the complete source code
#define CONTROL_FLOW_FRAGMENT   64



#endif

