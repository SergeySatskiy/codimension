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


#include "pycfLexer.h"
#include "pycfParser.h"

#include "cflowparser.hpp"
#include "cflowfragments.hpp"



Py::Object  parseInput( pANTLR3_INPUT_STREAM  input )
{
    ppycfLexer      lxr( pycfLexerNew( input ) );
    if ( lxr == NULL )
        throw Py::RuntimeError( "Cannot create lexer" );


    pANTLR3_COMMON_TOKEN_STREAM     tstream( antlr3CommonTokenStreamSourceNew(
                                                ANTLR3_SIZE_HINT,
                                                TOKENSOURCE( lxr ) ) );
    if ( tstream == NULL )
    {
        lxr->free( lxr );
        throw Py::RuntimeError( "Cannot create token stream" );
    }

    // I cannot discard off channel tokens because all the comments
    // will be discarded. Instead there is another pass to collect comment
    // tokens from the lexer.
    // tstream->discardOffChannelToks( tstream, ANTLR3_TRUE );

    // Create parser
    ppycfParser     psr( pycfParserNew( tstream ) );
    if ( psr == NULL )
    {
        tstream->free( tstream );
        lxr->free( lxr );
        throw Py::RuntimeError( "Error creating parser" );
    }

    // Get the tree and walk it
    pANTLR3_BASE_TREE       tree( psr->file_input( psr ).tree );
    ControlFlow *           controlFlow = new ControlFlow();

    if ( tree == NULL )
    {
        psr->free( psr );
        tstream->free( tstream );
        lxr->free( lxr );
        throw Py::RuntimeError( "Parsing error" );
    }

    // Walk the tree and insert collected info into the controlFlow object


    // Second walk - comments
    size_t      tokenCount = tstream->tokens->count;
    for ( size_t  k = 0; k < tokenCount; ++k )
    {
        pANTLR3_COMMON_TOKEN    tok( (pANTLR3_COMMON_TOKEN)vectorGet( tstream->tokens, k ) );
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
            size_t      begin = firstChar - (char*)(tok->input->data);
            size_t      end = begin + commentSize - 1;
            char        buffer[ commentSize + 1 ];

            if ( line == 1 )
            {
                // This might be a bang line
                if ( commentSize > 2 )
                {
                    if ( firstChar[ 1 ] == '!' )
                    {
                        BangLine *      bangLine( new BangLine );
                        bangLine->parent = controlFlow;
                        bangLine->begin = firstChar - (char *)(input->data);
                        bangLine->end = lastChar - (char *)(input->data);
                        bangLine->beginLine = line;
                        bangLine->beginPos = tok->charPosition + 1;
                        bangLine->endLine = line;
                        bangLine->endPos = bangLine->beginPos + commentSize - 1;
                        controlFlow->updateEnd( bangLine->end,
                                                bangLine->endLine,
                                                bangLine->endPos );
                        controlFlow->updateBegin( bangLine->begin,
                                                  bangLine->beginLine,
                                                  bangLine->beginPos );
                        controlFlow->bangLine = Py::asObject( bangLine );
                        continue;
                    }
                }
            }



            snprintf( buffer, commentSize + 1, "%s", firstChar );
            printf( "COMMENT size: %03ld start: %06ld end: %06ld line: %03ld pos: %03d content: '%s'\n",
                    commentSize, begin, end, line, tok->charPosition + 1, buffer );
        }
    }

    // Cleanup
    psr->free( psr );
    tstream->free( tstream );
    lxr->free( lxr );

    // Provide the result object
    return Py::asObject( controlFlow );
}

