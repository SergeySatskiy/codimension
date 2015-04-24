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
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

#include "cflowcomments.hpp"


int  main( int  argc, char **  argv )
{
    if ( argc != 2 )
    {
        printf( "Usage: %s <python file name>\n", argv[0] );
        return 1;
    }

    // Read the whole file
    FILE *  f;
    f = fopen( argv[1], "r" );
    if ( f == NULL )
    {
        printf( "Cannot open file %s\n", argv[1] );
        return 1;
    }

    struct stat     st;
    stat( argv[1], &st );

    if ( st.st_size > 0 )
    {
        char            buffer[st.st_size + 2];
        int             elem = fread( buffer, st.st_size, 1, f );

        fclose( f );
        if ( elem != 1 )
        {
            printf( "Cannot read file %s\n", argv[1] );
            return 1;
        }

        buffer[ st.st_size ] = '\n';
        buffer[ st.st_size + 1 ] = '\0';

        // Do the line shifts and comments
        int                         lineShifts[ 65536 ]; // Max supported lines
        std::deque<CommentLine>     comments;

        getLineShiftsAndComments( buffer, lineShifts, comments );
        printf( "Found comments count: %ld\n", comments.size() );
        for ( std::deque<CommentLine>::const_iterator
                    k = comments.begin(); k != comments.end(); ++k )
        {
            printf( "%d:%d Absolute begin:end %d:%d Type: %s\n",
                    k->line, k->pos, k->begin, k->end,
                    commentTypeToString( k->type ).c_str() );
            buffer[ k->end + 1 ] = '\0';
            printf( "    %s\n", &buffer[ k->begin ] );
        }
    }
    else
    {
        printf( "Zero length file, nothing to do\n" );
    }

    return 0;
}


