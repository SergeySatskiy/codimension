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
 * Python control flow parser implementation
 */

#ifndef CFLOWCOMMENTS_HPP
#define CFLOWCOMMENTS_HPP


#include <vector>


enum CommentType
{
    STANDALONE_COMMENT_LINE = 0,
    TRAILING_COMMENT_LINE = 1,

    UNKNOWN_COMMENT_LINE_TYPE = 99
};


struct Comment
{
    int             begin;      // Absolute position of the '#' character,
                                // 0-based
    int             end;        // Absolute position of the character
                                // before '\n', '\r' or '\0', 0-based
    int             line;       // 1-based line
    int             pos;        // 1-based column of the '#' character

    CommentType     type;       // Comment line type. Combining comment lines
                                // into block comments will be done later

    Comment( int  b, int  e, int  l, int  p, CommentType  t ) :
        begin( b ), end( e ), line( l ), pos( p ), type( t )
    {}
    Comment() :
        begin( -1 ), end( -1 ), line( -1 ), pos( -1 ),
        type( UNKNOWN_COMMENT_LINE_TYPE )
    {}
};



void getLineShiftsAndComments( const char *  buffer, int *  lineShifts,
                               std::vector< Comment > &  comments );


#endif

