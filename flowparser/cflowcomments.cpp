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

#include <string.h>
#include <stdexcept>

#include "cflowcomments.hpp"



std::string  commentTypeToString( CommentType  t )
{
    switch ( t )
    {
        case REGULAR_COMMENT:
            return "REGULAR_COMMENT";
        case CML_COMMENT:
            return "CML_COMMENT";
        case CML_COMMENT_CONTINUE:
            return "CML_COMMENT_CONTINUE";
        case UNKNOWN_COMMENT:
            return "UNKNOWN_COMMENT";
        default:
            break;
    }
    return "ERROR: COMMENT TYPE";
}


// Comment search state
enum ExpectState
{
    expectCommentStart,
    expectCommentEnd,
    expectClosingSingleQuote,
    expectClosingDoubleQuote,
    expectClosingTripleSingleQuote,
    expectClosingTripleDoubleQuote
};



static bool
isEscaped( const char *  buffer, int  absPos )
{
    if ( absPos == 0 )
        return false;
    return buffer[ absPos - 1 ] == '\\';
}


static bool
isTriple( const char *  buffer, int  absPos )
{
    char    symbol = buffer[ absPos ];
    if ( buffer[ absPos + 1 ] != symbol )
        return false;
    if ( buffer[ absPos + 2 ] != symbol )
        return false;
    return true;
}


CommentType
CommentLine::detectType( const char *  buffer )
{
    int     shift = begin + 1;
    while ( shift <= end )
    {
        if ( buffer[ shift ] == ' ' || buffer[ shift ] == '\t' )
        {
            ++shift;
            continue;
        }

        if ( strcmp( buffer + shift, "cml+" ) == 0 )
        {
            type = CML_COMMENT_CONTINUE;
            break;
        }
        if ( strcmp( buffer + shift, "cml" ) == 0 )
        {
            type = CML_COMMENT;
            break;
        }
        type = REGULAR_COMMENT;
        break;
    }

    return type;
}


// The function walks the given buffer and provides two things:
// - an array of absolute positions of the beginning of each line
// - a deque of found comments
void getLineShiftsAndComments( const char *  buffer, int *  lineShifts,
                               std::deque< CommentLine > &  comments )
{
    int             absPos = 0;
    char            symbol;
    int             line = 1;
    int             column = 1;
    ExpectState     expectState = expectCommentStart;
    CommentLine     comment;

    /* index 0 is not used; The first line starts with shift 0 */
    lineShifts[ 1 ] = 0;
    while ( buffer[ absPos ] != '\0' )
    {
        symbol = buffer[ absPos ];

        if ( symbol == '#' )
        {
            if ( expectState == expectCommentStart )
            {
                comment.begin = absPos;
                comment.line = line;
                comment.pos = column;
                expectState = expectCommentEnd;

                ++absPos;
                ++column;
                continue;
            }
        }
        else if ( expectState != expectCommentEnd )
        {
            if ( symbol == '\"' || symbol == '\'' )
            {
                if ( isEscaped( buffer, absPos ) )
                {
                    ++absPos;
                    ++column;
                    continue;
                }

                // It is not escaped some kind of quote
                if ( symbol == '\"' &&
                        ( expectState == expectClosingSingleQuote ||
                          expectState == expectClosingTripleSingleQuote ) )
                {
                    // " inside ' or '''
                    ++absPos;
                    ++column;
                    continue;
                }
                if ( symbol == '\'' &&
                        ( expectState == expectClosingDoubleQuote ||
                          expectState == expectClosingTripleDoubleQuote ) )
                {
                    // ' inside " or """
                    ++absPos;
                    ++column;
                    continue;
                }

                // String literal beginning case
                if ( expectState == expectCommentStart )
                {
                    if ( isTriple( buffer, absPos ) == true )
                    {
                        if ( symbol == '\"' )
                            expectState = expectClosingTripleDoubleQuote;
                        else
                            expectState = expectClosingTripleSingleQuote;
                        absPos += 3;
                        column += 3;
                    }
                    else
                    {
                        if ( symbol == '\"' )
                            expectState = expectClosingDoubleQuote;
                        else
                            expectState = expectClosingSingleQuote;
                        ++absPos;
                        ++column;
                    }
                    continue;
                }

                // String literal end case
                if ( expectState == expectClosingSingleQuote ||
                     expectState == expectClosingDoubleQuote )
                {
                    expectState = expectCommentStart;
                    ++absPos;
                    ++column;
                    continue;
                }
                else if ( expectState == expectClosingTripleSingleQuote ||
                          expectState == expectClosingTripleDoubleQuote )
                {
                    if ( isTriple( buffer, absPos ) == true )
                    {
                        expectState = expectCommentStart;
                        absPos += 3;
                        column += 3;
                        continue;
                    }
                    ++absPos;
                    ++column;
                    continue;
                }
                else
                    throw std::runtime_error( "Fatal error: unknown quote state" );
            }
        }



        if ( symbol == '\r' )
        {
            comment.end = absPos - 1;   // will not harm but will unify the code
            ++absPos;
            if ( buffer[ absPos ] == '\n' )
            {
                ++absPos;
            }
            ++line;
            lineShifts[ line ] = absPos;
            column = 1;
            if ( expectState == expectCommentEnd )
            {
                comment.detectType( buffer );
                comments.push_back( comment );
                comment.begin = -1;
                expectState = expectCommentStart;
            }
            continue;
        }

        if ( symbol == '\n' )
        {
            comment.end = absPos - 1;   // will not harm but will unify the code
            ++absPos;
            ++line;
            lineShifts[ line ] = absPos;
            column = 1;
            if ( expectState == expectCommentEnd )
            {
                comment.detectType( buffer );
                comments.push_back( comment );
                comment.begin = -1;
                expectState = expectCommentStart;
            }
            continue;
        }
        ++absPos;
        ++column;
    }

    if ( comment.begin != -1 )
    {
        // Need to flush the collected comment
        comment.detectType( buffer );
        comment.end = absPos - 1;
        comments.push_back( comment );
    }

    return;
}

