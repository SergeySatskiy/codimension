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

#include <stdio.h>
#include <ctype.h>

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


void CommentLine::detectType( const char *  buffer )
{
    int     shift = begin + 1;
    while ( shift <= end )
    {
        // skip spaces if so
        if ( buffer[ shift ] == ' ' || buffer[ shift ] == '\t' )
        {
            ++shift;
            continue;
        }

        if ( strncmp( buffer + shift, "cml", 3 ) == 0 )
        {
            shift += 3;
            if ( buffer[ shift ] == '+' )
                type = CML_COMMENT_CONTINUE;
            else
                type = CML_COMMENT;
            return;
        }
        type = REGULAR_COMMENT;
        return;
    }

    type = REGULAR_COMMENT;
    return;
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


// CML comments parsing support

// It is used to get:
// - version
// - record type
// - value name
// - '=' character
std::string  getCMLCommentToken( const std::string &  comment,
                                 size_t &  pos )
{
    skipSpaces( comment, pos );

    size_t          lastPos( comment.size() - 1 );
    std::string     token;

    while ( pos <= lastPos )
    {
        char    symbol( comment[ pos ] );

        if ( symbol == '=' )
        {
            if ( token.empty() )
            {
                ++pos;
                return "=";     // This is a key-value separator
            }
            break;              // A key has ended
        }
        if ( isspace( symbol ) != 0 )
        {
            break;              // A token has ended
        }

        token += symbol;
        ++pos;
    }
    return token;
}


// It is used to get a value. '"' characters are stripped and if there are many
// parts then they are merged.
std::string  getCMLCommentValue( const std::string &  comment,
                                 size_t &  pos,
                                 std::string &  warning )
{
    skipSpaces( comment, pos );

    size_t          lastPos( comment.size() - 1 );
    if ( pos > lastPos )
        return "";

    if ( comment[ pos ] != '"' )
        return getCMLCommentToken( comment, pos );

    // Here: the value is in double quotes
    std::string     value;

    ++pos;
    while ( pos <= lastPos )
    {
        char    symbol( comment[ pos ] );
        if ( symbol == '\\' )
        {
            if ( pos < lastPos )
            {
                if ( comment[ pos + 1 ] == '"' )
                {
                    pos += 2;
                    value += std::string( "\"" );
                    continue;
                }
            }
        }
        else if ( symbol == '"' )
        {
            ++pos;

            // That's the end of the value or of a part.
            // It might be that the value continues in the next part so we need
            // to look ahead.
            size_t      tempPos( pos );
            skipSpaces( comment, tempPos );
            if ( tempPos <= lastPos )
            {
                if ( comment[ tempPos ] == '"' )
                {
                    // This is a value continue
                    pos = tempPos + 1;
                    continue;
                }
            }

            return value;
        }
        value += symbol;
        ++pos;
    }

    // Unfinished double quote
    warning = "Unfinished double quote for a property value";
    return "";
}

void  skipSpaces( const std::string &  comment,
                  size_t &  pos )
{
    size_t      lastPos( comment.size() - 1 );
    while ( pos <= lastPos )
    {
        if ( isspace( comment[ pos ] ) == 0 )
            return;
        ++pos;
    }
    return;
}

