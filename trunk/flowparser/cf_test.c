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
 * Control flow python parser test utility
 */


#include "pycfLexer.h"
#include "pycfParser.h"



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
        ANTLR3_UINT32   n = tree->children->size( tree->children );
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
    ppycfLexer     lxr = pycfLexerNew( input );

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

    // I cannot discard off channel tokens because all the comments
    // will be discarded. Instead there is another pass to collect comment
    // tokens from the lexer.
    // tstream->discardOffChannelToks( tstream, ANTLR3_TRUE );

    // Create parser
    ppycfParser psr = pycfParserNew( tstream );

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
            walk( tree, 0 );
        }
    }
    else
    {
        printf( "Error parsing the input file\n" );
        retVal = 1;
    }

    size_t      tokenCount = tstream->tokens->size( tstream->tokens );
    printf( "Number of tokens in the stream: %ld\n", tokenCount );

    for ( size_t  k = 0; k < tokenCount; ++k )
    {
        pANTLR3_COMMON_TOKEN    tok = tstream->tokens->get( tstream->tokens, k );
        if ( tok->type == COMMENT )
        {
            size_t      line = tok->line;

            // Adjust the last character of the comment
            char *      lastChar = (char *)tok->stop;
            while ( *lastChar == '\n' || *lastChar == '\r' || *lastChar == 0 )
                --lastChar;
            char *      firstChar = (char *)tok->start;
            while ( *firstChar != '#' )
            {
                ++firstChar;
                ++tok->charPosition;
            }
            size_t      commentSize = lastChar - firstChar + 1;
            size_t      begin = (void*)firstChar - (void*)tok->input->data;
            size_t      end = begin + commentSize - 1;
            char        buffer[ 4096 ];

            snprintf( buffer, commentSize + 1, "%s", firstChar );
            printf( "COMMENT size: %03ld start: %06ld end: %06ld line: %03d pos: %03d content: '%s'\n",
                    commentSize, begin, end, line, tok->charPosition + 1, buffer );
        }
        else
        {
            printf( "Token line: %03ld Token type: %03ld\n",
                    tok->line, tok->type );
        }
    }

    // Clean up
    psr->free( psr );
    tstream->free( tstream );
    lxr->free( lxr );
    input->close( input );

    return retVal;
}


void  searchForCoding( ppycfLexer     ctx,
                       char *         lineStart,
                       ANTLR3_UINT32  lineNumber )
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

