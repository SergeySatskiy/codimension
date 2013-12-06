/*
 * codimension - graphics python two-way code editor and analyzer
 * Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
 * Brief python parser test utility
 */


#include "pythonbriefLexer.h"
#include "pythonbriefParser.h"



void walk( pANTLR3_BASE_TREE    tree,
           int                  level )
{
    int     type = tree->getType( tree );
    if ( type == NEWLINE || type == DEDENT || type == INDENT )
        return;

    printf( "%03d", tree->getType( tree ) );
    for ( int k = 0; k < level; ++k )
        printf( "    " );

    // Print itself
    const char *    tok = (tree->toString( tree ))->chars;
    printf( "'%s'\n", tok );

    // Walk children
    if ( tree->children != NULL )
    {
        ANTLR3_UINT32   i;
        ANTLR3_UINT32   n = tree->children->count;
        for ( i = 0; i < n; i++ )
        {
            pANTLR3_BASE_TREE   t;
            t = (pANTLR3_BASE_TREE) tree->children->get( tree->children, i );
            walk( t, level + 1 );
        }
    }
    return;
}


int process( const char *  filename, int  count )
{
    int                     retVal = 0;
    pANTLR3_INPUT_STREAM    input = antlr3AsciiFileStreamNew( (pANTLR3_UINT8) filename );

    if ( input == NULL )
    {
        printf( "Error creating input stream for %s\n", filename );
        return 1;
    }

    // Create lexer
    ppythonbriefLexer       lxr = pythonbriefLexerNew( input );

    if ( lxr == NULL )
    {
        input->close( input );
        printf( "Error creating lexer\n" );
        return 1;
    }

    // Create token stream
    pANTLR3_COMMON_TOKEN_STREAM     tstream = antlr3CommonTokenStreamSourceNew( ANTLR3_SIZE_HINT,
                                                                                TOKENSOURCE( lxr ) );

    if ( tstream == NULL )
    {
        lxr->free(lxr);
        input->close( input );
        printf( "Error creating token stream\n" );
        return 1;
    }

    tstream->discardOffChannelToks( tstream, ANTLR3_TRUE );

    // Create parser
    ppythonbriefParser psr = pythonbriefParserNew( tstream );

    if ( psr == NULL )
    {
        tstream->free( tstream );
        lxr->free(lxr);
        input->close( input );
        printf( "Error creating parser\n" );
        return 1;
    }


    // Parse ...
    pANTLR3_BASE_TREE       tree = psr->file_input( psr ).tree;

    // Walk the built tree...
    if ( tree != 0 )
    {
        if ( count == 1 )
        {
            int  nextConsumed;
            int  streamSize;
            int  index;

            walk( tree, 0 );

            nextConsumed = tstream->p;
            streamSize = tstream->tokens->count;
            printf( "Next consumed: %d\n", nextConsumed );
            printf( "Size: %d\n", streamSize );

            for ( index = nextConsumed; index < streamSize; ++index )
            {
                pANTLR3_STRING  s;
                pANTLR3_COMMON_TOKEN    token = (pANTLR3_COMMON_TOKEN)( tstream->tokens->get( tstream->tokens, index ) );
                s = token->toString( token );
                printf( "  Non consumed token: %s\n", s->chars );
            }
        }
    }
    else
    {
        printf( "Error parsing the input file\n" );
        retVal = 1;
    }

    // Clean up
    psr->free( psr );
    tstream->free( tstream );
    lxr->free( lxr );
    input->close( input );

    return retVal;
}


void  searchForCoding( ppythonbriefLexer  ctx,
                       char *             lineStart,
                       ANTLR3_UINT32      lineNumber )
{
    /* fake function to avoid linking with python libs */
    return;
}


int main( int  argc, char **  argv )
{
    int     count = 1;
    int     k;

    if ( argc < 2 || argc > 3 )
    {
        printf( "Usage: %s <filename> [cycles]\n", argv[0] );
        return 1;
    }

    if ( argc == 3 )
    {
        count = atoi( argv[2] );
        if ( count <= 0 ) count = 1;
    }

    for ( k = 0; k < count; ++k )
        if ( process( argv[1], count ) != 0 ) return 1;

    return 0;
}

