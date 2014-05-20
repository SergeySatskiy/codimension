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
 * The original file was taken from the ANTLR3 example created by
 * Ales Teska on 5.10.09 and then extended and modified to fit the
 * codimension project requirements.
 */


#include "pycfLexer.h"
#include "pycfParser.h"
#include <assert.h>


#ifdef __LP64__
    #if __LP64__ == 1
        /* 64 bit arch */
        typedef ANTLR3_INT64        STACK_INT;
    #else
        /* 32 bit: just in case */
        typedef ANTLR3_INT32        STACK_INT;
    #endif
#else
    /* 32 bit arch */
    typedef ANTLR3_INT32        STACK_INT;
#endif



// helper function to create token in lexer
pANTLR3_COMMON_TOKEN  pycfLexer_createLexerToken( pANTLR3_LEXER  lexer,
                                                  ANTLR3_UINT32  tokenType,
                                                  pANTLR3_UINT8  text )
{
    pANTLR3_COMMON_TOKEN    newToken = lexer->rec->state->tokFactory->newToken( lexer->rec->state->tokFactory );

    if ( newToken != NULL )
    {
        newToken->type = tokenType;
        newToken->input = lexer->rec->state->tokFactory->input;

        if (text != NULL)
        {
            newToken->textState = ANTLR3_TEXT_CHARP;
            newToken->tokText.chars = (pANTLR3_UCHAR)text;
        }
        else
        {
            newToken->textState = ANTLR3_TEXT_NONE;
        }
    }
    return  newToken;
}


static
char  emptyString[] = "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        "
                      "                                        ";
static
char *   endofemptystring = &emptyString[ sizeof( emptyString ) - 1 ];

char *  pycfLexer_syntetizeEmptyString( int  spaces )
{

    assert((endofemptystring-spaces) >= emptyString);
    return endofemptystring-spaces;
}


static STACK_INT  FIRST_CHAR_POSITION = 0;

/*
 * This is another level of nextToken - this one handles
 * setting of startPos and calling original handler
 */
static pANTLR3_COMMON_TOKEN  pycfLexer_nextTokenLowerLevelImpl( ppycfLexer            ctx,
                                                                pANTLR3_TOKEN_SOURCE  toksource )
{
    ctx->startPos = ctx->pLexer->getCharPositionInLine( ctx->pLexer );

    // This is workaround for bug in libantlr3c (3.1.3, 3.2)
    // See http://www.antlr.org/pipermail/antlr-interest/2009-October/036252.html
    // (ANTLR mailing list, bug report)
    if ( ctx->startPos == -1 )
    {
        ctx->pLexer->input->charPositionInLine = 0;
        ctx->startPos = 0;
    }

    return ctx->origNextToken( toksource );
}


static pANTLR3_COMMON_TOKEN pycfLexer_createDedentIdentToken( ppycfLexer         ctx,
                                                              ANTLR3_UINT32      toktype,
                                                              ANTLR3_UINT32      tokline )
{
    pANTLR3_COMMON_TOKEN    tok = ctx->pLexer->rec->state->tokFactory->newToken( ctx->pLexer->rec->state->tokFactory );

    tok->type = toktype;
    tok->input = ctx->pLexer->rec->state->tokFactory->input;
    tok->textState = ANTLR3_TEXT_NONE;
    tok->charPosition = 0;
    tok->line = tokline;

    return tok;
}


// Return the index on stack of previous indent level == i else -1
static STACK_INT  pycfLexer_findPreviousIndent( ppycfLexer  ctx,
                                                STACK_INT   i )
{
    STACK_INT   j;

    for ( j = ctx->identStack->vector->count - 1; j >= 0; --j )
    {
        STACK_INT    pos = (STACK_INT) (stackGet( ctx->identStack, j ));
        if ( pos == i )
            return j;
    }

    return FIRST_CHAR_POSITION;
}


static void
pycfLexer_insertImaginaryIndentDedentTokens( ppycfLexer            ctx,
                                             pANTLR3_TOKEN_SOURCE  toksource )
{
    pANTLR3_COMMON_TOKEN    t = pycfLexer_nextTokenLowerLevelImpl( ctx, toksource );
    vectorAdd( ctx->tokens, t, NULL );

    // if not a NEWLINE, doesn't signal indent/dedent work; just enqueue
    if ( t->type != NEWLINE )
        return;

    // Ignore newlines on hidden channel
    if ( t->channel == HIDDEN )
        return;

    ANTLR3_INT32    newlineno = t->line + 1;

    // grab first token of next line (skip COMMENT tokens)
    for ( ; ; )
    {
        t = pycfLexer_nextTokenLowerLevelImpl( ctx, toksource );

        if ( t->type == COMMENT ) // Pass comments to output stream (= skip processing here)
        {
            vectorAdd( ctx->tokens, t, NULL );
            continue;
        }

        //Ignore LEADING_WS on HIDDEN channel - these are emited by empty line with some whitespaces on it
        if ( (t->type == LEADING_WS) && (t->channel == HIDDEN))
            continue;

        break;
    }

    // compute cpos as the char pos of next non-WS token in line
    STACK_INT   cpos;
    switch ( t->type )
    {

        case EOF:
            cpos = -1;  // pretend EOF always happens at left edge
            break;

        case LEADING_WS:
            cpos = t->getText( t )->len;
            break;

        default:
            cpos = t->charPosition;
            break;
    }

    STACK_INT       lastIndent = (STACK_INT) stackPeek( ctx->identStack );
    ANTLR3_INT32    lineno = t->line;
    if ( lineno <= 0 )
        lineno = newlineno;

    if ( cpos > lastIndent )
    {
        stackPush( ctx->identStack, (void *)cpos, NULL );
        vectorAdd( ctx->tokens,
                   pycfLexer_createDedentIdentToken( ctx, INDENT, lineno ),
                   NULL );
    }
    else if (cpos < lastIndent)
    {
        ANTLR3_INT32 prevIndex = pycfLexer_findPreviousIndent( ctx, cpos );

        // generate DEDENTs for each indent level we backed up over
        while ( ctx->identStack->vector->count > (prevIndex + 1) )
        {
            vectorAdd( ctx->tokens,
                       pycfLexer_createDedentIdentToken( ctx, DEDENT, lineno ),
                       NULL );
            stackPop( ctx->identStack );
        }
    }

    // Filter out LEADING_WS tokens
    if ( t->type != LEADING_WS )
        vectorAdd( ctx->tokens, t, NULL );
}



static pANTLR3_COMMON_TOKEN  pycfLexer_nextTokenImpl( pANTLR3_TOKEN_SOURCE  toksource )
{
    pANTLR3_LEXER       lexer = (pANTLR3_LEXER)( toksource->super );
    ppycfLexer          ctx = (ppycfLexer) lexer->ctx;

    for ( ; ; )
    {
        if ( ctx->tokens->count > 0 )
        {
            return (pANTLR3_COMMON_TOKEN) vectorRemove( ctx->tokens, 0 );
        }

        pycfLexer_insertImaginaryIndentDedentTokens( ctx, toksource );
    }

    assert( 0 == 1 ); // This part of code should be never reached
}



static void  pycfLexer_FreeImpl( struct pycfLexer_Ctx_struct *  ctx )
{
    vectorFree( ctx->tokens );
    stackFree( ctx->identStack );

    ctx->origFree( ctx );
}



void  pycfLexer_initLexer( ppycfLexer  ctx )
{
    ctx->implicitLineJoiningLevel = 0;
    ctx->startPos = -1;

    ctx->tokens = antlr3VectorNew( 16384 );
    ctx->identStack = antlr3StackNew( ANTLR3_LIST_SIZE_HINT );
    stackPush( ctx->identStack, (void *)FIRST_CHAR_POSITION, NULL );

    // Override nextToken implementation by Python specific
    ctx->origNextToken = ctx->pLexer->rec->state->tokSource->nextToken;
    ctx->pLexer->rec->state->tokSource->nextToken = pycfLexer_nextTokenImpl;

    ctx->origFree = ctx->free;
    ctx->free = pycfLexer_FreeImpl;

    ctx->onEncoding = NULL;
    return;
}


pANTLR3_BASE_TREE pycfInsertInheritance( struct pycfParser_Ctx_struct *  ctx,
                                         pANTLR3_VECTOR                         args )
{
    ANTLR3_UINT32   n = args->count;
    if ( n == 0 ) return NULL;      /* No base classes, so do not create the CLASS_INHERITANCE node */

    pANTLR3_BASE_TREE   inheritance_root = ctx->adaptor->nilNode( ctx->adaptor );
    inheritance_root = ctx->adaptor->becomeRoot( ctx->adaptor,
                                                 ctx->adaptor->createTypeText( ctx->adaptor,
                                                                               CLASS_INHERITANCE,
                                                                               (pANTLR3_UINT8) "CLASS_INHERITANCE" ),
                                                 inheritance_root );

    /* Add children stored in the vector of args */
    ANTLR3_UINT32   k;

    for ( k = 0; k < n; ++k )
    {
        const char *        item = (const char *) (vectorGet( args, k ));
        pANTLR3_BASE_TREE   child = ctx->adaptor->createTypeText( ctx->adaptor, CLASS_INHERITANCE, (pANTLR3_UINT8) item );

        ctx->adaptor->addChild( ctx->adaptor, inheritance_root, child );
    }

    return inheritance_root;
}


struct function_argument
{
    pANTLR3_UINT8   name;
    ANTLR3_UINT32   type;
};

void addTypedName( pANTLR3_VECTOR       v,
                   ANTLR3_UINT32        type,
                   pANTLR3_UINT8        name )
{
    struct function_argument *  item = malloc( sizeof( struct function_argument ) );
    item->name = name;
    item->type = type;
    vectorAdd( v, item, free );

    return;
}

pANTLR3_BASE_TREE pycfInsertArguments( struct pycfParser_Ctx_struct *  ctx,
                                       pANTLR3_VECTOR                  args )
{
    ANTLR3_UINT32   n = args->count;

    if ( n == 0 )   return NULL;    /* No arguments so do not insert the ARGUMENTS node */

    pANTLR3_BASE_TREE   arguments_root = ctx->adaptor->nilNode( ctx->adaptor );
    arguments_root = ctx->adaptor->becomeRoot( ctx->adaptor,
                                               ctx->adaptor->createTypeText( ctx->adaptor,
                                                                             ARGUMENTS,
                                                                             (pANTLR3_UINT8) "ARGUMENTS" ),
                                               arguments_root );

    /* Add children stored in the vector of args */
    ANTLR3_UINT32   k;
    for ( k = 0; k < n; ++k )
    {
        struct function_argument *  item = (struct function_argument *) (vectorGet( args, k ));
        pANTLR3_BASE_TREE           child = ctx->adaptor->createTypeText( ctx->adaptor,
                                                                          item->type, item->name );

        ctx->adaptor->addChild( ctx->adaptor, arguments_root, child );
    }

    return arguments_root;
}

