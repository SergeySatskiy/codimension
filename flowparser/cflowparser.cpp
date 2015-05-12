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


#include <Python.h>
#include <node.h>
#include <grammar.h>
#include <parsetok.h>
#include <graminit.h>
#include <errcode.h>
#include <token.h>

#include <string.h>
#include <list>

#include "cflowparser.hpp"
#include "cflowfragments.hpp"
#include "cflowcomments.hpp"


extern grammar      _PyParser_Grammar;  /* From graminit.c */


static FragmentBase *
walk( Context *             context,
      node *                tree,
      FragmentBase *        parent,
      Py::List &            flow,
      bool                  docstrProcessed );



/* Copied and adjusted from 
 * static void err_input(perrdetail *err)
 */
static std::string getErrorMessage( perrdetail *  err)
{
    char            buffer[ 64 ];
    sprintf( buffer, "%d:%d ", err->lineno, err->offset );

    std::string     message( buffer );
    switch ( err->error )
    {
        case E_ERROR:
            return std::string( "execution error" );
        case E_SYNTAX:
            if ( err->expected == INDENT )
                message += "expected an indented block";
            else if ( err->token == INDENT )
                message += "unexpected indent";
            else if (err->token == DEDENT)
                message += "unexpected unindent";
            else
                message += "invalid syntax";
            break;
        case E_TOKEN:
            message += "invalid token";
            break;
        case E_EOFS:
            message += "EOF while scanning triple-quoted string literal";
            break;
        case E_EOLS:
            message += "EOL while scanning string literal";
            break;
        case E_INTR:
            message = "keyboard interrupt";
            goto cleanup;
        case E_NOMEM:
            message = "no memory";
            goto cleanup;
        case E_EOF:
            message += "unexpected EOF while parsing";
            break;
        case E_TABSPACE:
            message += "inconsistent use of tabs and spaces in indentation";
            break;
        case E_OVERFLOW:
            message += "expression too long";
            break;
        case E_DEDENT:
            message += "unindent does not match any outer indentation level";
            break;
        case E_TOODEEP:
            message += "too many levels of indentation";
            break;
        case E_DECODE:
            message += "decode error";
            break;
        case E_LINECONT:
            message += "unexpected character after line continuation character";
            break;
        default:
            {
                char    code[ 32 ];
                sprintf( code, "%d", err->error );
                message += "unknown parsing error (error code " +
                           std::string( code ) + ")";
                break;
            }
    }

    if ( err->text != NULL )
        message += std::string( "\n" ) + err->text;

    cleanup:
    if (err->text != NULL)
    {
        PyObject_FREE(err->text);
        err->text = NULL;
    }
    return message;
}

/* Provides the total number of lines in the code */
static int getTotalLines( node *  tree )
{
    if ( tree == NULL )
        return -1;

    if ( tree->n_type != file_input )
        tree = &(tree->n_child[ 0 ]);

    assert( tree->n_type == file_input );
    for ( int k = 0; k < tree->n_nchildren; ++k )
    {
        node *  child = &(tree->n_child[ k ]);
        if ( child->n_type == ENDMARKER )
            return child->n_lineno;
    }
    return -1;
}


static node *  findLastPart( node *  tree )
{
    while ( tree->n_nchildren > 0 )
        tree = & (tree->n_child[ tree->n_nchildren - 1 ]);
    return tree;
}

static node *  findChildOfType( node *  from, int  type )
{
    for ( int  k = 0; k < from->n_nchildren; ++k )
        if ( from->n_child[ k ].n_type == type )
            return & (from->n_child[ k ]);
    return NULL;
}

static node *
findChildOfTypeAndValue( node *  from, int  type, const char *  val )
{
    for ( int  k = 0; k < from->n_nchildren; ++k )
        if ( from->n_child[ k ].n_type == type )
            if ( strcmp( from->n_child[ k ].n_str, val ) == 0 )
                return & (from->n_child[ k ]);
    return NULL;
}

/* Searches for a certain  node among the first children */
static node *
skipToNode( node *  tree, int nodeType )
{
    if ( tree == NULL )
        return NULL;

    for ( ; ; )
    {
        if ( tree->n_type == nodeType )
            return tree;
        if ( tree->n_nchildren < 1 )
            return NULL;
        tree = & ( tree->n_child[ 0 ] );
    }
    return NULL;
}

static void updateBegin( Fragment *  f, node *  firstPart,
                         int *  lineShifts )
{
    f->begin = lineShifts[ firstPart->n_lineno ] + firstPart->n_col_offset;
    f->beginLine = firstPart->n_lineno;
    f->beginPos = firstPart->n_col_offset + 1;
}


static void updateEnd( Fragment *  f, node *  lastPart,
                       int *  lineShifts )
{
    if ( lastPart->n_str != NULL )
    {
        int     lastPartLength = strlen( lastPart->n_str );

        f->end = lineShifts[ lastPart->n_lineno ] +
                 lastPart->n_col_offset + lastPartLength - 1;
        f->endLine = lastPart->n_lineno;
        f->endPos = lastPart->n_col_offset + lastPartLength;
    }
    else
    {
        f->end = lineShifts[ lastPart->n_lineno ] + lastPart->n_col_offset;
        f->endLine = lastPart->n_lineno;
        f->endPos = lastPart->n_col_offset;
    }
}


// It also discards the comment from the deque if it is a bang line
static void
checkForBangLine( const char *  buffer,
                  ControlFlow *  controlFlow,
                  std::deque< CommentLine > &  comments )
{
    if ( comments.empty() )
        return;

    CommentLine &       comment( comments.front() );
    if ( comment.line == 1 && comment.end - comment.begin > 1 &&
         buffer[ comment.begin + 1 ] == '!' )
    {
        // That's a bang line
        BangLine *          bangLine( new BangLine );
        bangLine->parent = controlFlow;
        bangLine->begin = comment.begin;
        bangLine->end = comment.end;
        bangLine->beginLine = 1;
        bangLine->beginPos = comment.pos;
        bangLine->endLine = 1;
        bangLine->endPos = bangLine->beginPos + ( bangLine->end -
                                                  bangLine->begin );
        controlFlow->bangLine = Py::asObject( bangLine );
        controlFlow->updateBeginEnd( bangLine );

        // Discard the shebang comment
        comments.pop_front();
    }
    return;
}


// It also discards the comment from the deque
static void processEncoding( const char *   buffer,
                             node *         tree,
                             ControlFlow *  controlFlow,
                             std::deque< CommentLine > &  comments )
{
    /* Unfortunately, the parser does not provide the position of the encoding
     * so it needs to be calculated
     */

    /* Another problem is that the python parser can replace what is found
       in the source code to a 'normal' name. The rules in the python source
       code are (Parser/tokenizer.c):
       'utf-8', 'utf-8-...' -> 'utf-8'
       'latin-1', 'iso-8859-1', 'iso-latin-1', 'latin-1-...',
       'iso-8859-1-...', 'iso-latin-1-...' -> 'iso-8859-1'

       Moreover, the first 12 characters may be converted as follows:
       '_' -> '-'
       all the other -> tolower()
    */

    if ( comments.empty() )
        return;

    CommentLine &       comment( comments.front() );
    EncodingLine *      encodingLine( new EncodingLine );

    encodingLine->normalizedName = Py::String( tree->n_str );
    encodingLine->parent = controlFlow;
    encodingLine->begin = comment.begin;
    encodingLine->end = comment.end;
    encodingLine->beginLine = comment.line;
    encodingLine->beginPos = comment.pos;
    encodingLine->endLine = comment.line;
    encodingLine->endPos = encodingLine->beginPos + ( encodingLine->end -
                                                      encodingLine->begin );
    controlFlow->encodingLine = Py::asObject( encodingLine );
    controlFlow->updateBeginEnd( encodingLine );

    comments.pop_front();
    return;
}


// Detects the leading comments block last line. -1 if none found
static int
detectLeadingBlock( Context * context, int  limit )
{
    if ( context->comments->empty() )
        return -1;

    const CommentLine &     first = context->comments->front();
    if ( first.line >= limit )
        return -1;

    int     lastInBlock( first.line );
    for ( std::deque< CommentLine >::const_iterator
            k = context->comments->begin();
            k != context->comments->end(); ++k )
    {
        if ( k->line >= limit )
            break;

        if ( k->line > lastInBlock + 1 )
            break;

        lastInBlock = k->line;
    }
    return lastInBlock;
}


// Parent is not set here
static Fragment *
createCommentFragment( const CommentLine &  comment )
{
    Fragment *      part( new Fragment );
    part->begin = comment.begin;
    part->end = comment.end;
    part->beginLine = comment.line;
    part->beginPos = comment.pos;
    part->endLine = comment.line;
    part->endPos = comment.pos + ( comment.end - comment.begin );
    return part;
}


static void
addLeadingCMLComment( Context *  context,
                      CMLComment *  leadingCML,
                      int  leadingLastLine,
                      int  firstStatementLine,
                      FragmentWithComments *  statement,
                      FragmentBase *  flowAsParent,
                      Py::List &  flow )
{
    leadingCML->extractProperties( context );
    if ( leadingLastLine + 1 == firstStatementLine )
    {
        statement->leadingCMLComments.append( Py::asObject( leadingCML ) );
    }
    else
    {
        flowAsParent->updateBeginEnd( leadingCML );
        flow.append( Py::asObject( leadingCML ) );
    }
    return;
}



static void
injectLeadingComments( Context *  context,
                       Py::List &  flow,
                       FragmentBase *  flowAsParent,
                       FragmentWithComments *  statement, // could be NULL
                       FragmentBase *  statementAsParent, // could be NULL
                       int  firstStatementLine )
{
    int     leadingLastLine = detectLeadingBlock( context,
                                                  firstStatementLine );

    while ( leadingLastLine != -1 )
    {
        CMLComment *    leadingCML = NULL;
        Comment *       leading = NULL;

        while ( ! context->comments->empty() )
        {
            CommentLine &       comment = context->comments->front();
            if ( comment.line > leadingLastLine )
                break;

            if ( comment.type == CML_COMMENT )
            {
                if ( leadingCML != NULL )
                {
                    addLeadingCMLComment( context, leadingCML,
                                          leadingLastLine, firstStatementLine,
                                          statement, flowAsParent, flow );
                    leadingCML = NULL;
                }

                Fragment *      part( createCommentFragment( comment ) );
                if ( leadingLastLine + 1 == firstStatementLine )
                    part->parent = statementAsParent;
                else
                    part->parent = flowAsParent;

                leadingCML = new CMLComment;
                leadingCML->updateBeginEnd( part );
                leadingCML->parts.append( Py::asObject( part ) );
            }


            if ( comment.type == CML_COMMENT_CONTINUE )
            {
                if ( leadingCML == NULL )
                {
                    // Bad thing: someone may deleted the proper
                    // cml comment beginning so the comment is converted into a
                    // regular one. The regular comment will be handled below.
                    context->flow->addWarning( comment.line,
                                               "Continue of the CML comment "
                                               "without the beginning. "
                                               "Treat it as a regular comment." );
                    comment.type = REGULAR_COMMENT;
                }
                else
                {
                    if ( leadingCML->endLine + 1 != comment.line )
                    {
                        // Bad thing: whether someone deleted the beginning of
                        // the cml comment or inserted an empty line between.
                        // So convert the comment into a regular one.
                        context->flow->addWarning( comment.line,
                                               "Continue of the CML comment "
                                               "without the beginning. "
                                               "Treat it as a regular comment." );
                        comment.type = REGULAR_COMMENT;
                    }
                    else
                    {
                        Fragment *      part( createCommentFragment( comment ) );
                        if ( leadingLastLine + 1 == firstStatementLine )
                            part->parent = statementAsParent;
                        else
                            part->parent = flowAsParent;

                        leadingCML->updateEnd( part );
                        leadingCML->parts.append( Py::asObject( part ) );
                    }
                }
            }

            if ( comment.type == REGULAR_COMMENT )
            {
                if ( leadingCML != NULL )
                {
                    addLeadingCMLComment( context, leadingCML,
                                          leadingLastLine, firstStatementLine,
                                          statement, flowAsParent, flow );
                    leadingCML = NULL;
                }

                Fragment *      part( createCommentFragment( comment ) );
                if ( leadingLastLine + 1 == firstStatementLine )
                    part->parent = statementAsParent;
                else
                    part->parent = flowAsParent;

                if ( leading == NULL )
                {
                    leading = new Comment;
                    leading->updateBegin( part );
                }
                leading->parts.append( Py::asObject( part ) );
                leading->updateEnd( part );
            }

            context->comments->pop_front();
        }

        if ( leadingCML != NULL )
        {
            addLeadingCMLComment( context, leadingCML,
                                  leadingLastLine, firstStatementLine,
                                  statement, flowAsParent, flow );
            leadingCML = NULL;
        }
        if ( leading != NULL )
        {
            if ( leadingLastLine + 1 == firstStatementLine )
                statement->leadingComment = Py::asObject( leading );
            else
            {
                flowAsParent->updateBeginEnd( leading );
                flow.append( Py::asObject( leading ) );
            }
            leading = NULL;
        }

        leadingLastLine = detectLeadingBlock( context, firstStatementLine );
    }
    return;
}


static void
addSideCMLCommentContinue( Context *  context,
                           CMLComment *  sideCML,
                           CommentLine &  comment,
                           FragmentBase *  statementAsParent )
{
    if ( sideCML == NULL )
    {
        // Bad thing: someone may deleted the proper
        // cml comment beginning so the comment is converted into a
        // regular one. The regular comment will be handled below.
        context->flow->addWarning( comment.line,
                    "Continue of the CML comment without the "
                    "beginning. Treat it as a regular comment." );
        comment.type = REGULAR_COMMENT;
        return;
    }

    // Check if there is the proper beginning
    if ( sideCML->endLine + 1 != comment.line )
    {
        // Bad thing: whether someone deleted the beginning of
        // the cml comment or inserted an empty line between.
        // So convert the comment into a regular one.
        context->flow->addWarning( comment.line,
                    "Continue of the CML comment without the beginning "
                    "in the previous line. Treat it as a regular comment." );
        comment.type = REGULAR_COMMENT;
        return;
    }

    // All is fine, let's add the CML continue
    Fragment *      part( createCommentFragment( comment ) );
    part->parent = statementAsParent;
    sideCML->updateEnd( part );
    sideCML->parts.append( Py::asObject( part ) );
    return;
}


static void
addSideCMLComment( Context *  context,
                   CMLComment *  sideCML,
                   FragmentWithComments *  statement,
                   FragmentBase *  flowAsParent )
{
    sideCML->extractProperties( context );
    statement->sideCMLComments.append( Py::asObject( sideCML ) );
    flowAsParent->updateEnd( sideCML );
    return;
}


static void
injectSideComments( Context *  context,
                    FragmentWithComments *  statement,
                    FragmentBase *  statementAsParent,
                    FragmentBase *  flowAsParent )
{
    CMLComment *        sideCML = NULL;
    Comment *           side = NULL;
    int                 lastCommentLine = -1;
    int                 lastCommentPos = -1;

    while ( ! context->comments->empty() )
    {
        CommentLine &       comment = context->comments->front();
        if ( comment.line > statementAsParent->endLine )
            break;

        lastCommentLine = comment.line;
        lastCommentPos = comment.pos;

        if ( comment.type == CML_COMMENT )
        {
            if ( sideCML != NULL )
            {
                addSideCMLComment( context, sideCML, statement, flowAsParent );
                sideCML = NULL;
            }

            Fragment *      part( createCommentFragment( comment ) );
            part->parent = statementAsParent;

            sideCML = new CMLComment;
            sideCML->updateBeginEnd( part );
            sideCML->parts.append( Py::asObject( part ) );
        }

        if ( comment.type == CML_COMMENT_CONTINUE )
        {
            // It may change the comment type to a REGULAR_COMMENT one
            addSideCMLCommentContinue( context, sideCML, comment,
                                       statementAsParent );
        }

        if ( comment.type == REGULAR_COMMENT )
        {
            Fragment *      part( createCommentFragment( comment ) );
            part->parent = statementAsParent;

            if ( side == NULL )
            {
                side = new Comment;
                side->updateBegin( part );
            }
            side->parts.append( Py::asObject( part ) );
            side->updateEnd( part );
        }

        context->comments->pop_front();
    }

    // Collect trailing comments which could be a continuation of the last side
    // comment
    while ( ! context->comments->empty() )
    {
        CommentLine &       comment = context->comments->front();
        if ( comment.line != lastCommentLine + 1 )
            break;
        if ( comment.pos != lastCommentPos )
            break;

        lastCommentLine = comment.line;

        if ( comment.type == CML_COMMENT )
        {
            if ( sideCML != NULL )
            {
                addSideCMLComment( context, sideCML, statement, flowAsParent );
                sideCML = NULL;
            }

            Fragment *      part( createCommentFragment( comment ) );
            part->parent = statementAsParent;

            sideCML = new CMLComment;
            sideCML->updateBeginEnd( part );
            sideCML->parts.append( Py::asObject( part ) );
        }

        if ( comment.type == CML_COMMENT_CONTINUE )
        {
            // It may change the comment type to a REGULAR_COMMENT one
            addSideCMLCommentContinue( context, sideCML, comment,
                                       statementAsParent );
        }

        if ( comment.type == REGULAR_COMMENT )
        {
            Fragment *      part( createCommentFragment( comment ) );
            part->parent = statementAsParent;

            if ( side == NULL )
            {
                side = new Comment;
                side->updateBegin( part );
            }
            side->parts.append( Py::asObject( part ) );
            side->updateEnd( part );
        }

        context->comments->pop_front();
    }


    // Insert the collected comments
    if ( sideCML != NULL )
    {
        addSideCMLComment( context, sideCML, statement, flowAsParent );
        sideCML = NULL;
    }
    if ( side != NULL )
    {
        statement->sideComment = Py::asObject( side );
        flowAsParent->updateEnd( side );
        side = NULL;
    }
    return;
}


// Injects comments to the control flow or to the statement
// The injected comments are deleted from the deque
static void
injectComments( Context *  context,
                Py::List &  flow,
                FragmentBase *  flowAsParent,
                FragmentWithComments *  statement,
                FragmentBase *  statementAsParent )
{
    injectLeadingComments( context, flow, flowAsParent, statement,
                           statementAsParent,
                           statementAsParent->beginLine );
    injectSideComments( context, statement, statementAsParent,
                        flowAsParent );
    return;
}


static FragmentBase *
processBreak( Context *  context,
              node *  tree, FragmentBase *  parent,
              Py::List &  flow )
{
    assert( tree->n_type == break_stmt );
    Break *         br( new Break );
    br->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = br;
    updateBegin( body, tree, context->lineShifts );
    body->end = body->begin + 4;        // 4 = strlen( "break" ) - 1
    body->endLine = tree->n_lineno;
    body->endPos = body->beginPos + 4;  // 4 = strlen( "break" ) - 1

    br->updateBeginEnd( body );
    br->body = Py::asObject( body );
    injectComments( context, flow, parent, br, br );
    flow.append( Py::asObject( br ) );
    return br;
}


static FragmentBase *
processContinue( Context *  context,
                 node *  tree, FragmentBase *  parent,
                 Py::List &  flow )
{
    assert( tree->n_type == continue_stmt );
    Continue *      cont( new Continue );
    cont->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = cont;
    updateBegin( body, tree, context->lineShifts );
    body->end = body->begin + 7;        // 7 = strlen( "continue" ) - 1
    body->endLine = tree->n_lineno;
    body->endPos = body->beginPos + 7;  // 7 = strlen( "continue" ) - 1

    cont->updateBeginEnd( body );
    cont->body = Py::asObject( body );
    injectComments( context, flow, parent, cont, cont );
    flow.append( Py::asObject( cont ) );
    return cont;
}


static FragmentBase *
processAssert( Context *  context,
               node *  tree, FragmentBase *  parent,
               Py::List &  flow )
{
    assert( tree->n_type == assert_stmt );
    Assert *            a( new Assert );
    a->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = a;
    updateBegin( body, tree, context->lineShifts );
    body->end = body->begin + 5;        // 5 = strlen( "assert" ) - 1
    body->endLine = tree->n_lineno;
    body->endPos = body->beginPos + 5;  // 5 = strlen( "assert" ) - 1

    a->updateBegin( body );

    // One test node must be there. The second one may not be there
    node *      firstTestNode = findChildOfType( tree, test );
    assert( firstTestNode != NULL );

    Fragment *      tst( new Fragment );
    node *          testLastPart = findLastPart( firstTestNode );

    tst->parent = a;
    updateBegin( tst, firstTestNode, context->lineShifts );
    updateEnd( tst, testLastPart, context->lineShifts );
    a->tst = Py::asObject( tst );

    // If a comma is there => there is a message part
    node *      commaNode = findChildOfType( tree, COMMA );
    if ( commaNode != NULL )
    {
        Fragment *      message( new Fragment );

        // Message test node must follow the comma node
        node *          secondTestNode = commaNode + 1;
        node *          secondTestLastPart = findLastPart( secondTestNode );

        message->parent = a;
        updateBegin( message, secondTestNode, context->lineShifts );
        updateEnd( message, secondTestLastPart, context->lineShifts );

        a->updateEnd( message );
        a->message = Py::asObject( message );
    }
    else
        a->updateEnd( tst );

    a->body = Py::asObject( body );
    injectComments( context, flow, parent, a, a );
    flow.append( Py::asObject( a ) );
    return a;
}



static FragmentBase *
processRaise( Context *  context,
              node *  tree, FragmentBase *  parent,
              Py::List &  flow )
{
    assert( tree->n_type == raise_stmt );
    Raise *         r( new Raise );
    r->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = r;
    updateBegin( body, tree, context->lineShifts );
    body->end = body->begin + 4;        // 4 = strlen( "raise" ) - 1
    body->endLine = tree->n_lineno;
    body->endPos = body->beginPos + 4;  // 4 = strlen( "raise" ) - 1

    r->updateBegin( body );

    node *      testNode = findChildOfType( tree, test );
    if ( testNode != NULL )
    {
        Fragment *      val( new Fragment );
        node *          lastPart = findLastPart( tree );

        val->parent = r;
        updateBegin( val, testNode, context->lineShifts );
        updateEnd( val, lastPart, context->lineShifts );

        r->updateEnd( val );
        r->value = Py::asObject( val );
    }
    else
        r->updateEnd( body );

    r->body = Py::asObject( body );
    injectComments( context, flow, parent, r, r );
    flow.append( Py::asObject( r ) );
    return r;
}


static FragmentBase *
processReturn( Context *  context, node *  tree,
               FragmentBase *  parent, Py::List &  flow )
{
    assert( tree->n_type == return_stmt );
    Return *        ret( new Return );
    ret->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = ret;
    updateBegin( body, tree, context->lineShifts );
    body->end = body->begin + 5;        // 5 = strlen( "return" ) - 1
    body->endLine = tree->n_lineno;
    body->endPos = body->beginPos + 5;  // 5 = strlen( "return" ) - 1

    ret->updateBegin( body );

    node *      testlistNode = findChildOfType( tree, testlist );
    if ( testlistNode != NULL )
    {
        Fragment *      val( new Fragment );
        node *          lastPart = findLastPart( testlistNode );

        val->parent = ret;
        updateBegin( val, testlistNode, context->lineShifts );
        updateEnd( val, lastPart, context->lineShifts );

        ret->updateEnd( val );
        ret->value = Py::asObject( val );
    }
    else
        ret->updateEnd( body );

    ret->body = Py::asObject( body );
    injectComments( context, flow, parent, ret, ret );
    flow.append( Py::asObject( ret ) );
    return ret;
}


// Handles 'else' and 'elif' clauses for various statements: 'if' branches,
// 'else' parts of 'while', 'for', 'try'
static ElifPart *
processElifPart( Context *  context, Py::List &  flow,
                 node *  tree, FragmentBase *  parent )
{
    assert( tree->n_type == NAME );
    assert( strcmp( tree->n_str, "else" ) == 0 ||
            strcmp( tree->n_str, "elif" ) == 0 ||
            strcmp( tree->n_str, "if" ) == 0 );

    ElifPart *      elifPart( new ElifPart );
    elifPart->parent = parent;

    node *      current = tree + 1;
    node *      colonNode = NULL;
    if ( current->n_type == test )
    {
        // This is an elif part, i.e. there is a condition part
        node *      last = findLastPart( current );
        Fragment *  condition( new Fragment );
        condition->parent = elifPart;
        updateBegin( condition, current, context->lineShifts );
        updateEnd( condition, last, context->lineShifts );
        elifPart->condition = Py::asObject( condition );

        colonNode = current + 1;
    }
    else
    {
        assert( current->n_type == COLON );
        colonNode = current;
    }

    node *          suiteNode = colonNode + 1;
    Fragment *      body( new Fragment );
    body->parent = elifPart;
    updateBegin( body, tree, context->lineShifts );
    updateEnd( body, colonNode, context->lineShifts );
    elifPart->updateBeginEnd( body );
    elifPart->body = Py::asObject( body );

    injectComments( context, flow, parent, elifPart, elifPart );
    FragmentBase *  lastAdded = walk( context, suiteNode, elifPart,
                                      elifPart->nsuite, false );
    if ( lastAdded == NULL )
        elifPart->updateEnd( body );
    else
        elifPart->updateEnd( lastAdded );
    return elifPart;
}


static FragmentBase *
processIf( Context *  context,
           node *  tree, FragmentBase *  parent,
           Py::List &  flow )
{
    assert( tree->n_type == if_stmt );

    If *        ifStatement( new If );
    ifStatement->parent = parent;

    for ( int k = 0; k < tree->n_nchildren; ++k )
    {
        node *  child = &(tree->n_child[ k ]);
        if ( child->n_type == NAME )
        {
            if ( strcmp( child->n_str, "if" ) == 0 )
            {
                node *      conditionNode = child + 1;
                assert( conditionNode->n_type == test );

                node *      last = findLastPart( conditionNode );
                Fragment *  condition( new Fragment );
                condition->parent = ifStatement;
                updateBegin( condition, conditionNode, context->lineShifts );
                updateEnd( condition, last, context->lineShifts );
                ifStatement->condition = Py::asObject( condition );

                node *      colonNode = conditionNode + 1;
                node *      suiteNode = colonNode + 1;

                Fragment *      body( new Fragment );
                body->parent = ifStatement;
                updateBegin( body, tree, context->lineShifts );
                updateEnd( body, colonNode, context->lineShifts );
                ifStatement->updateBeginEnd( body );
                ifStatement->body = Py::asObject( body );

                injectComments( context, flow, parent,
                                ifStatement, ifStatement );
                FragmentBase *  lastAdded = walk( context, suiteNode, ifStatement,
                                                  ifStatement->nsuite, false );
                if ( lastAdded == NULL )
                    ifStatement->updateEnd( body );
                else
                    ifStatement->updateEnd( lastAdded );
            }
            else
            {
                ElifPart *  elifPart = processElifPart( context, flow, child,
                                                        ifStatement );
                ifStatement->updateBegin( elifPart );
                ifStatement->elifParts.append( Py::asObject( elifPart ) );
            }
        }
    }

    flow.append( Py::asObject( ifStatement ) );
    return ifStatement;
}


static ExceptPart *
processExceptPart( Context *  context, Py::List &  flow,
                   node *  tree, FragmentBase *  parent )
{
    assert( tree->n_type == except_clause ||
            tree->n_type == NAME );

    ExceptPart *    exceptPart( new ExceptPart );
    exceptPart->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = exceptPart;

    // ':' node is the very next one
    node *          colonNode = tree + 1;
    updateBegin( body, tree, context->lineShifts );
    updateEnd( body, colonNode, context->lineShifts );
    exceptPart->updateBeginEnd( body );
    exceptPart->body = Py::asObject( body );

    // If it is NAME => it is 'finally' or 'else'
    // The clause could only be in the 'except' case
    if ( tree->n_type == except_clause )
    {
        node *      testNode = findChildOfType( tree, test );
        if ( testNode != NULL )
        {
            node *      last = findLastPart( tree );
            Fragment *  clause( new Fragment );

            clause->parent = exceptPart;
            updateBegin( clause, testNode, context->lineShifts );
            updateEnd( clause, last, context->lineShifts );
            exceptPart->clause = Py::asObject( clause );
        }
    }

    injectComments( context, flow, parent,
                    exceptPart, exceptPart );

    // 'suite' node follows the colon node
    node *          suiteNode = colonNode + 1;
    FragmentBase *  lastAdded = walk( context,
                                      suiteNode, exceptPart,
                                      exceptPart->nsuite, false );
    if ( lastAdded == NULL )
        exceptPart->updateEnd( body );
    else
        exceptPart->updateEnd( lastAdded );
    return exceptPart;
}


static FragmentBase *
processTry( Context *  context,
            node *  tree, FragmentBase *  parent,
            Py::List &  flow )
{
    assert( tree->n_type == try_stmt );

    Try *       tryStatement( new Try );
    tryStatement->parent = parent;

    Fragment *      body( new Fragment );
    node *          tryColonNode = findChildOfType( tree, COLON );
    body->parent = tryStatement;
    updateBegin( body, tree, context->lineShifts );
    updateEnd( body, tryColonNode, context->lineShifts );
    tryStatement->body = Py::asObject( body );
    tryStatement->updateBeginEnd( body );

    injectComments( context, flow, parent,
                    tryStatement, tryStatement );

    // suite
    node *          trySuiteNode = tryColonNode + 1;
    FragmentBase *  lastAdded = walk( context,
                                      trySuiteNode, tryStatement,
                                      tryStatement->nsuite, false );
    if ( lastAdded == NULL )
        tryStatement->updateEnd( body );
    else
        tryStatement->updateEnd( lastAdded );


    // except, finally, else parts
    for ( int k = 0; k < tree->n_nchildren; ++k )
    {
        node *  child = &(tree->n_child[ k ]);
        if ( child->n_type == except_clause )
        {
            ExceptPart *    exceptPart = processExceptPart( context, flow,
                                                            child,
                                                            tryStatement );
            tryStatement->exceptParts.append( Py::asObject( exceptPart ) );
            continue;
        }
        if ( child->n_type == NAME )
        {
            if ( strcmp( child->n_str, "else" ) == 0 )
            {
                ExceptPart *    elsePart = processExceptPart( context, flow,
                                                              child,
                                                              tryStatement );
                tryStatement->elsePart = Py::asObject( elsePart );
                continue;
            }
            if ( strcmp( child->n_str, "finally" ) == 0 )
            {
                ExceptPart *    finallyPart = processExceptPart( context, flow,
                                                                 child,
                                                                 tryStatement );
                tryStatement->finallyPart = Py::asObject( finallyPart );
            }
        }
    }

    flow.append( Py::asObject( tryStatement ) );
    return tryStatement;
}


static FragmentBase *
processWhile( Context *  context,
              node *  tree, FragmentBase *  parent,
              Py::List &  flow )
{
    assert( tree->n_type == while_stmt );

    While *     w( new While);
    w->parent = parent;

    Fragment *      body( new Fragment );
    node *          colonNode = findChildOfType( tree, COLON );
    node *          whileNode = findChildOfType( tree, NAME );

    body->parent = w;
    updateBegin( body, whileNode, context->lineShifts );
    updateEnd( body, colonNode, context->lineShifts );
    w->body = Py::asObject( body );
    w->updateBeginEnd( body );

    // condition
    node *          testNode = findChildOfType( tree, test );
    node *          lastPart = findLastPart( testNode );
    Fragment *      condition( new Fragment );

    condition->parent = w;
    updateBegin( condition, testNode, context->lineShifts );
    updateEnd( condition, lastPart, context->lineShifts );
    w->condition = Py::asObject( condition );

    injectComments( context, flow, parent, w, w );

    // suite
    node *          suiteNode = findChildOfType( tree, suite );
    FragmentBase *  lastAdded = walk( context, suiteNode, w, w->nsuite,
                                      false );
    if ( lastAdded == NULL )
        w->updateEnd( body );
    else
        w->updateEnd( lastAdded );

    // else part
    node *          elseNode = findChildOfTypeAndValue( tree, NAME, "else" );
    if ( elseNode != NULL )
    {
        ElifPart *      elsePart = processElifPart( context, flow, elseNode, w );
        w->elsePart = Py::asObject( elsePart );
    }

    flow.append( Py::asObject( w ) );
    return w;
}


static FragmentBase *
processWith( Context *  context,
             node *  tree, FragmentBase *  parent,
             Py::List &  flow )
{
    assert( tree->n_type == with_stmt );

    With *      w( new With );
    w->parent = parent;

    Fragment *      body( new Fragment );
    node *          colonNode = findChildOfType( tree, COLON );
    node *          whithNode = findChildOfType( tree, NAME );

    body->parent = w;
    updateBegin( body, whithNode, context->lineShifts );
    updateEnd( body, colonNode, context->lineShifts );
    w->body = Py::asObject( body );
    w->updateBeginEnd( body );

    // items
    node *      firstWithItem = findChildOfType( tree, with_item );
    node *      lastWithItem = NULL;
    for ( int  k = 0; k < tree->n_nchildren; ++k )
    {
        node *  child = &(tree->n_child[ k ]);
        if ( child->n_type == with_item )
            lastWithItem = child;
    }

    Fragment *      items( new Fragment );
    items->parent = w;
    updateBegin( items, firstWithItem, context->lineShifts );
    updateEnd( items, lastWithItem, context->lineShifts );
    w->items = Py::asObject( items );

    injectComments( context, flow, parent, w, w );

    // suite
    node *          suiteNode = findChildOfType( tree, suite );
    FragmentBase *  lastAdded = walk( context, suiteNode, w, w->nsuite,
                                      false );
    if ( lastAdded == NULL )
        w->updateEnd( body );
    else
        w->updateEnd( lastAdded );

    flow.append( Py::asObject( w ) );
    return w;
}


static FragmentBase *
processFor( Context *  context,
            node *  tree, FragmentBase *  parent,
            Py::List &  flow )
{
    assert( tree->n_type == for_stmt );

    For *       f( new For );
    f->parent = parent;

    Fragment *      body( new Fragment );
    node *          colonNode = findChildOfType( tree, COLON );
    node *          forNode = findChildOfType( tree, NAME );

    body->parent = f;
    updateBegin( body, forNode, context->lineShifts );
    updateEnd( body, colonNode, context->lineShifts );
    f->body = Py::asObject( body );
    f->updateBeginEnd( body );

    // Iteration
    node *          exprlistNode = findChildOfType( tree, exprlist );
    node *          testlistNode = findChildOfType( tree, testlist );
    node *          lastPart = findLastPart( testlistNode );
    Fragment *      iteration( new Fragment );

    iteration->parent = f;
    updateBegin( iteration, exprlistNode, context->lineShifts );
    updateEnd( iteration, lastPart, context->lineShifts );
    f->iteration = Py::asObject( iteration );

    injectComments( context, flow, parent, f, f );

    // suite
    node *          suiteNode = findChildOfType( tree, suite );
    FragmentBase *  lastAdded = walk( context, suiteNode, f, f->nsuite,
                                      false );
    if ( lastAdded == NULL )
        f->updateEnd( body );
    else
        f->updateEnd( lastAdded );

    // else part
    node *          elseNode = findChildOfTypeAndValue( tree, NAME, "else" );
    if ( elseNode != NULL )
    {
        ElifPart *      elsePart = processElifPart( context, flow, elseNode, f );
        f->elsePart = Py::asObject( elsePart );
    }

    flow.append( Py::asObject( f ) );
    return f;
}


static FragmentBase *
processImport( Context *  context,
               node *  tree, FragmentBase *  parent,
               Py::List &  flow )
{
    assert( tree->n_type == import_stmt );
    assert( tree->n_nchildren == 1 );


    Import *        import( new Import );
    import->parent = parent;

    Fragment *      body( new Fragment );
    node *          lastPart = findLastPart( tree );

    body->parent = import;
    updateBegin( body, tree, context->lineShifts );
    updateEnd( body, lastPart, context->lineShifts );

    /* There must be one child of type import_from or import_name */
    tree = & ( tree->n_child[ 0 ] );
    if ( tree->n_type == import_from )
    {
        Fragment *  fromFragment( new Fragment );
        Fragment *  whatFragment( new Fragment );

        node *      fromPartBegin = findChildOfType( tree, DOT );
        if ( fromPartBegin == NULL )
            fromPartBegin = findChildOfType( tree, dotted_name );
        assert( fromPartBegin != NULL );

        fromFragment->parent = import;
        whatFragment->parent = import;

        updateBegin( fromFragment, fromPartBegin, context->lineShifts );

        node *      lastFromPart = NULL;
        if ( fromPartBegin->n_type == DOT )
        {
            // it could be:
            // DOT ... DOT or
            // DOT ... DOT dotted_name
            lastFromPart = findChildOfType( tree, dotted_name );
            if ( lastFromPart == NULL )
            {
                // This is DOT ... DOT
                lastFromPart = fromPartBegin;
                while ( (lastFromPart+1)->n_type == DOT )
                    ++lastFromPart;
            }
            else
            {
                lastFromPart = findLastPart( lastFromPart );
            }
        }
        else
        {
            lastFromPart = findLastPart( fromPartBegin );
        }

        updateEnd( fromFragment, lastFromPart, context->lineShifts );

        node *      whatPart = findChildOfTypeAndValue( tree, NAME, "import" );
        assert( whatPart != NULL );

        ++whatPart;     // the very next after import is the first of the what part
        updateBegin( whatFragment, whatPart, context->lineShifts );
        updateEnd( whatFragment, lastPart, context->lineShifts );

        import->fromPart = Py::asObject( fromFragment );
        import->whatPart = Py::asObject( whatFragment );
    }
    else
    {
        assert( tree->n_type == import_name );
        import->fromPart = Py::None();

        Fragment *      whatFragment( new Fragment );
        node *          firstWhat = findChildOfType( tree, dotted_as_names );
        assert( firstWhat != NULL );

        whatFragment->parent = import;
        updateBegin( whatFragment, firstWhat, context->lineShifts );

        // The end matches the body
        whatFragment->end = body->end;
        whatFragment->endLine = body->endLine;
        whatFragment->endPos = body->endPos;

        import->whatPart = Py::asObject( whatFragment );
    }

    import->updateBeginEnd( body );
    import->body = Py::asObject( body );
    injectComments( context, flow, parent, import, import );
    flow.append( Py::asObject( import ) );
    return import;
}

static void
processDecor( Context *  context, Py::List &  flow,
              FragmentBase *  parent,
              node *  tree, std::list<Decorator *> &  decors )
{
    assert( tree->n_type == decorator );

    node *      atNode = findChildOfType( tree, AT );
    node *      nameNode = findChildOfType( tree, dotted_name );
    node *      lparNode = findChildOfType( tree, LPAR );
    assert( atNode != NULL );
    assert( nameNode != NULL );

    Decorator *     decor( new Decorator );
    Fragment *      nameFragment( new Fragment );
    node *          lastNameNode = findLastPart( nameNode );

    nameFragment->parent = decor;
    updateBegin( nameFragment, nameNode, context->lineShifts );
    updateEnd( nameFragment, lastNameNode, context->lineShifts );
    decor->name = Py::asObject( nameFragment );

    Fragment *      body( new Fragment );
    body->parent = decor;
    updateBegin( body, atNode, context->lineShifts );

    if ( lparNode == NULL )
    {
        // Decorator without arguments
        updateEnd( body, lastNameNode, context->lineShifts );
    }
    else
    {
        // Decorator with arguments
        node *          rparNode = findChildOfType( tree, RPAR );
        Fragment *      argsFragment( new Fragment );

        argsFragment->parent = decor;
        updateBegin( argsFragment, lparNode, context->lineShifts );
        updateEnd( argsFragment, rparNode, context->lineShifts );
        decor->arguments = Py::asObject( argsFragment );
        updateEnd( body, rparNode, context->lineShifts );
    }

    decor->body = Py::asObject( body );
    decor->updateBeginEnd( body );

    injectComments( context, flow, parent, decor, decor );
    decors.push_back( decor );
    return;
}


static std::list<Decorator *>
processDecorators( Context *  context, Py::List &  flow,
                   FragmentBase *  parent, node *  tree )
{
    assert( tree->n_type == decorators );

    int                         n = tree->n_nchildren;
    node *                      child;
    std::list<Decorator *>      decors;

    for ( int  k = 0; k < n; ++k )
    {
        child = & ( tree->n_child[ k ] );
        if ( child->n_type == decorator )
        {
            processDecor( context, flow, parent, child, decors );
        }
    }
    return decors;
}


static int
getNewLineParts( const char *  str, std::deque<const char *>  &  parts)
{
    int     count = 0;
    bool    found = false;

    while ( * str != '\0' )
    {
        if ( * str == '\r' )
        {
            if ( * (str + 1 ) == '\n' )
                ++str;
            found = true;
        }
        else if ( * str == '\n' )
            found = true;

        if ( found )
        {
            ++count;
            parts.push_back( str );
            found = false;
        }

        ++str;
    }
    return count;
}


// Multiline string literals do not have properly filled information
// They only have the last line info
static void
updateFragmentForMultilineStringLiteral( Context *  context,
                                         node *  stringChild,
                                         Fragment *  f )
{
    // Sick! The syntax parser provides column == -1 if it was a
    // multiline comment. So the only real information is the end line
    // of the multiline comment. All the rest I have to deduct myself
    std::deque< const char * >  newLines;
    int             count = getNewLineParts( stringChild->n_str,
                                             newLines );
    const char *    lastNewLine = newLines.back();
    int             strLen = strlen( stringChild->n_str );

    f->endLine = stringChild->n_lineno;
    f->beginLine = f->endLine - count;

    f->endPos = strlen( lastNewLine + 1 );
    f->end = context->lineShifts[ f->endLine ] + f->endPos - 1;

    f->begin = f->end - strLen + 1;
    f->beginPos = f->begin - context->lineShifts[ f->beginLine ] + 1;
    return;
}


// None or Docstring instance
static Docstring *
checkForDocstring( Context *  context, node *  tree )
{
    if ( tree == NULL )
        return NULL;

    node *      child = NULL;
    int         n = tree->n_nchildren;
    for ( int  k = 0; k < n; ++k )
    {
        /* need to skip NEWLINE and INDENT till stmt if so */
        child = & ( tree->n_child[ k ] );
        if ( child->n_type == NEWLINE )
            continue;
        if ( child->n_type == INDENT )
            continue;
        if ( child->n_type == stmt )
            break;

        return NULL;
    }

    child = skipToNode( child, atom );
    if ( child == NULL )
        return NULL;

    Docstring *     docstr( new Docstring );

    /* Atom has to have children of the STRING type only */
    node *          stringChild;

    n = child->n_nchildren;
    for ( int  k = 0; k < n; ++k )
    {
        stringChild = & ( child->n_child[ k ] );
        if ( stringChild->n_type != STRING )
        {
            delete docstr;
            return NULL;
        }

        // This is a docstring part
        Fragment *      part( new Fragment );
        part->parent = docstr;

        if ( stringChild->n_col_offset != -1 )
        {
            updateBegin( part, stringChild, context->lineShifts );
            updateEnd( part, stringChild, context->lineShifts );
        }
        else
        {
            updateFragmentForMultilineStringLiteral( context, stringChild,
                                                     part );
        }

        // In the vast majority of cases a docstring consists of a single part
        // so there is no need to optimize via updateBegin() & updateEnd()
        docstr->updateBeginEnd( part );
        docstr->parts.append( Py::asObject( part ) );
    }

    return docstr;
}


static FragmentBase *
processFuncDefinition( Context *                    context,
                       node *                       tree,
                       FragmentBase *               parent,
                       Py::List &                   flow,
                       std::list<Decorator *> &     decors )
{
    assert( tree->n_type == funcdef );
    assert( tree->n_nchildren > 1 );

    node *      defNode = & ( tree->n_child[ 0 ] );
    node *      nameNode = & ( tree->n_child[ 1 ] );
    node *      colonNode = findChildOfType( tree, COLON );

    assert( colonNode != NULL );

    Function *      func( new Function );
    func->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = func;
    updateBegin( body, defNode, context->lineShifts );
    updateEnd( body, colonNode, context->lineShifts );
    func->body = Py::asObject( body );

    Fragment *      name( new Fragment );
    name->parent = func;
    updateBegin( name, nameNode, context->lineShifts );
    updateEnd( name, nameNode, context->lineShifts );
    func->name = Py::asObject( name );

    node *      params = findChildOfType( tree, parameters );
    node *      lparNode = findChildOfType( params, LPAR );
    node *      rparNode = findChildOfType( params, RPAR );
    Fragment *  args( new Fragment );
    args->parent = func;
    updateBegin( args, lparNode, context->lineShifts );
    updateEnd( args, rparNode, context->lineShifts );
    func->arguments = Py::asObject( args );

    func->updateEnd( body );
    if ( decors.empty() )
    {
        func->updateBegin( body );
    }
    else
    {
        for ( std::list<Decorator *>::iterator  k = decors.begin();
              k != decors.end(); ++k )
        {
            Decorator *     dec = *k;
            dec->parent = func;
            func->decors.append( Py::asObject( dec ) );
        }
        func->updateBegin( *(decors.begin()) );
        decors.clear();
    }

    injectComments( context, flow, parent, func, func );

    // Handle docstring if so
    node *      suiteNode = findChildOfType( tree, suite );
    assert( suiteNode != NULL );

    Docstring *  docstr = checkForDocstring( context, suiteNode );
    if ( docstr != NULL )
    {
        docstr->parent = func;
        injectComments( context, func->nsuite, func, docstr, docstr );
        func->docstring = Py::asObject( docstr );

        // It could be that a docstring is the only item in the function suite
        func->updateEnd( docstr );
    }

    // Walk nested nodes
    FragmentBase *  lastAdded = walk( context, suiteNode, func,
                                      func->nsuite, docstr != NULL );
    if ( lastAdded == NULL )
        func->updateEnd( body );
    else
        func->updateEnd( lastAdded );
    flow.append( Py::asObject( func ) );
    return func;
}


static FragmentBase *
processClassDefinition( Context *                    context,
                        node *                       tree,
                        FragmentBase *               parent,
                        Py::List &                   flow,
                        std::list<Decorator *> &     decors )
{
    assert( tree->n_type == classdef );
    assert( tree->n_nchildren > 1 );

    node *      defNode = & ( tree->n_child[ 0 ] );
    node *      nameNode = & ( tree->n_child[ 1 ] );
    node *      colonNode = findChildOfType( tree, COLON );

    assert( colonNode != NULL );

    Class *      cls( new Class );
    cls->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = cls;
    updateBegin( body, defNode, context->lineShifts );
    updateEnd( body, colonNode, context->lineShifts );
    cls->body = Py::asObject( body );

    Fragment *      name( new Fragment );
    name->parent = cls;
    updateBegin( name, nameNode, context->lineShifts );
    updateEnd( name, nameNode, context->lineShifts );
    cls->name = Py::asObject( name );

    node *      lparNode = findChildOfType( tree, LPAR );
    if ( lparNode != NULL )
    {
        // There is a list of base classes
        node *      rparNode = findChildOfType( tree, RPAR );
        Fragment *  baseClasses( new Fragment );

        baseClasses->parent = cls;
        updateBegin( baseClasses, lparNode, context->lineShifts );
        updateEnd( baseClasses, rparNode, context->lineShifts );
        cls->baseClasses = Py::asObject( baseClasses );
    }

    cls->updateEnd( body );
    if ( decors.empty() )
    {
        cls->updateBegin( body );
    }
    else
    {
        for ( std::list<Decorator *>::iterator  k = decors.begin();
              k != decors.end(); ++k )
        {
            Decorator *     dec = *k;
            dec->parent = cls;
            cls->decors.append( Py::asObject( dec ) );
        }
        cls->updateBegin( *(decors.begin()) );
        decors.clear();
    }

    injectComments( context, flow, parent, cls, cls );

    // Handle docstring if so
    node *      suiteNode = findChildOfType( tree, suite );
    assert( suiteNode != NULL );

    Docstring *  docstr = checkForDocstring( context, suiteNode );
    if ( docstr != NULL )
    {
        docstr->parent = cls;
        injectComments( context, cls->nsuite, cls, docstr, docstr );
        cls->docstring = Py::asObject( docstr );

        // It could be that a docstring is the only item in the class suite
        cls->updateEnd( docstr );
    }

    // Walk nested nodes
    FragmentBase *  lastAdded = walk( context, suiteNode, cls, cls->nsuite,
                                      docstr != NULL );

    if ( lastAdded == NULL )
        cls->updateEnd( body );
    else
        cls->updateEnd( lastAdded );

    flow.append( Py::asObject( cls ) );
    return cls;
}




// Receives small_stmt
// Provides the meaningful node to process or NULL
static node *
getSmallStatementNodeToProcess( node *  tree )
{
    assert( tree->n_type == small_stmt );

    // small_stmt: (expr_stmt | print_stmt  | del_stmt | pass_stmt | flow_stmt
    //              | import_stmt | global_stmt | exec_stmt | assert_stmt)
    // flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt |
    //            yield_stmt
    if ( tree->n_nchildren <= 0 )
        return NULL;

    node *      child = & ( tree->n_child[ 0 ] );
    if ( child->n_type == flow_stmt )
    {
        if ( child->n_nchildren <= 0 )
            return NULL;
        // Return first flow_stmt child
        return & ( child->n_child[ 0 ] );
    }
    return child;
}


// Receives stmt
// Provides the meaningful node to process or NULL
static node *
getStmtNodeToProcess( node *  tree )
{
    // stmt: simple_stmt | compound_stmt
    assert( tree->n_type == stmt );

    if ( tree->n_nchildren <= 0 )
        return NULL;

    // simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE
    tree = & ( tree->n_child[ 0 ] );
    if ( tree->n_type == simple_stmt )
        return tree;

    // It is a compound statement
    // compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | with_stmt |
    //                funcdef | classdef | decorated
    // decorated: decorators (classdef | funcdef)
    assert( tree->n_type == compound_stmt );
    if ( tree->n_nchildren <= 0 )
        return NULL;
    return & ( tree->n_child[ 0 ] );
}

// Receives stmt or small_stmt
// Provides the meaningful node to process or NULL
static node *
getNodeToProcess( node *  tree )
{
    assert( tree->n_type == stmt || tree->n_type == small_stmt );

    if ( tree->n_type == small_stmt )
        return getSmallStatementNodeToProcess( tree );
    return getStmtNodeToProcess( tree );
}


static FragmentBase *
addCodeBlock( Context *  context,
              CodeBlock **  codeBlock,
              Py::List &    flow,
              FragmentBase *  parent )
{
    if ( *codeBlock == NULL )
        return NULL;

    CodeBlock *     p( *codeBlock );

    Fragment *      body( new Fragment );
    body->parent = p;

    // In case of multiline statement like ''' ... ''' the syntax tree does
    // not provide any information except the last line
    node *          firstNode = (node *)(p->firstNode);
    node *          lastItem = NULL;
    if ( firstNode->n_col_offset != -1 )
    {
        updateBegin( body, firstNode, context->lineShifts );
    }
    else
    {
        lastItem = findLastPart( firstNode );
        if ( lastItem->n_type == STRING && lastItem->n_str != NULL )
        {
            updateFragmentForMultilineStringLiteral( context, lastItem, body );
        }
        else
        {
            // NB: must never happened really
            updateBegin( body, firstNode, context->lineShifts );
        }
    }

    node *          lastNode = findLastPart( (node *)(p->lastNode) );
    if ( lastNode->n_col_offset != -1 )
    {
        updateEnd( body, lastNode, context->lineShifts );
    }
    else
    {
        if ( lastNode->n_type == STRING &&
             lastNode->n_str != NULL )
        {
            if ( lastItem != lastNode )
            {
                // If the string node is the only one then the end part is
                // updated above
                std::deque< const char * >  newLines;
                getNewLineParts( lastNode->n_str, newLines );
                const char *                lastNewLine = newLines.back();

                body->endLine = lastNode->n_lineno;
                body->endPos = strlen( lastNewLine + 1 );
                body->end = context->lineShifts[ body->endLine ] + body->endPos - 1;
            }
        }
        else
        {
            // NB: must never happened really
            updateEnd( body, lastNode, context->lineShifts );
        }
    }

    p->updateBeginEnd( body );
    p->body = Py::asObject( body );

    injectComments( context, flow, parent, p, p );
    flow.append( Py::asObject( p ) );
    *codeBlock = NULL;
    return p;
}


// Creates the code block and sets the beginning and the end of the block
static CodeBlock *
createCodeBlock( node *  tree, FragmentBase *  parent )
{
    CodeBlock *     codeBlock( new CodeBlock );
    codeBlock->parent = parent;

    codeBlock->firstNode = tree;
    codeBlock->lastNode = tree;

    node *      last = findLastPart( tree );
    codeBlock->lastLine = last->n_lineno;
    return codeBlock;
}


// Adds a statement to the code block and updates the end of the block
static void
addToCodeBlock( CodeBlock *  codeBlock, node *  tree )
{
    codeBlock->lastNode = tree;

    node *      last = findLastPart( tree );
    codeBlock->lastLine = last->n_lineno;
    return;
}


static int
getStringFirstLine( node *  n )
{
    n = findLastPart( n );
    if ( n->n_type != STRING || n->n_str == NULL )
        return n->n_lineno;

    std::deque< const char * >  newLines;
    int                         count = getNewLineParts( n->n_str, newLines );
    return n->n_lineno - count;
}


static FragmentBase *
walk( Context *                    context,
      node *                       tree,
      FragmentBase *               parent,
      Py::List &                   flow,
      bool                         docstrProcessed )
{
    CodeBlock *         codeBlock = NULL;
    FragmentBase *      lastAdded = NULL;
    int                 statementCount = 0;

    for ( int  i = 0; i < tree->n_nchildren; ++i )
    {
        node *      child = & ( tree->n_child[ i ] );
        if ( child->n_type != stmt )
            continue;

        ++statementCount;

        node *      nodeToProcess = getNodeToProcess( child );
        if ( nodeToProcess == NULL )
            continue;

        switch ( nodeToProcess->n_type )
        {
            case simple_stmt:
                // need to walk over the small_stmt
                for ( int  k = 0; k < nodeToProcess->n_nchildren; ++k )
                {
                    node *      simpleChild = & ( nodeToProcess->n_child[ k ] );
                    if ( simpleChild->n_type != small_stmt )
                        continue;

                    node *      nodeToProcess = getNodeToProcess( simpleChild );
                    if ( nodeToProcess == NULL )
                        continue;

                    switch ( nodeToProcess->n_type )
                    {
                        case import_stmt:
                            addCodeBlock( context, & codeBlock, flow, parent );
                            lastAdded = processImport( context, nodeToProcess,
                                                       parent, flow );
                            continue;
                        case assert_stmt:
                            addCodeBlock( context, & codeBlock, flow, parent );
                            lastAdded = processAssert( context, nodeToProcess,
                                                       parent, flow );
                            continue;
                        case break_stmt:
                            addCodeBlock( context, & codeBlock, flow, parent );
                            lastAdded = processBreak( context, nodeToProcess,
                                                      parent, flow );
                            continue;
                        case continue_stmt:
                            addCodeBlock( context, & codeBlock, flow, parent );
                            lastAdded = processContinue( context, nodeToProcess,
                                                         parent, flow );
                            continue;
                        case return_stmt:
                            addCodeBlock( context, & codeBlock, flow, parent );
                            lastAdded = processReturn( context, nodeToProcess,
                                                       parent, flow );
                            continue;
                        case raise_stmt:
                            addCodeBlock( context, & codeBlock, flow, parent );
                            lastAdded = processRaise( context, nodeToProcess,
                                                      parent, flow );
                            continue;
                        default: ;
                    }

                    // Some other statement
                    if ( statementCount == 1 && docstrProcessed )
                        continue;   // That's a docstring

                    // Not a docstring => add it to the code block
                    if ( codeBlock == NULL )
                    {
                        codeBlock = createCodeBlock( nodeToProcess, parent );
                    }
                    else
                    {
                        // If it a multilined string literal then we do not
                        // have the first line. We hav the last line
                        int     realFirstLine;
                        if ( nodeToProcess->n_col_offset == -1 )
                            realFirstLine = getStringFirstLine( nodeToProcess );
                        else
                            realFirstLine = nodeToProcess->n_lineno;

                        if ( realFirstLine - codeBlock->lastLine > 1 )
                        {
                            lastAdded = addCodeBlock( context, & codeBlock, flow,
                                                      parent );
                            codeBlock = createCodeBlock( nodeToProcess, parent );
                        }
                        else
                        {
                            addToCodeBlock( codeBlock, nodeToProcess );
                        }
                    }
                }
                continue;
            case if_stmt:
                addCodeBlock( context, & codeBlock, flow, parent );
                lastAdded = processIf( context, nodeToProcess, parent, flow );
                continue;
            case while_stmt:
                addCodeBlock( context, & codeBlock, flow, parent );
                lastAdded = processWhile( context, nodeToProcess, parent, flow );
                continue;
            case for_stmt:
                addCodeBlock( context, & codeBlock, flow, parent );
                lastAdded = processFor( context, nodeToProcess, parent, flow );
                continue;
            case try_stmt:
                addCodeBlock( context, & codeBlock, flow, parent );
                lastAdded = processTry( context, nodeToProcess, parent, flow );
                continue;
            case with_stmt:
                addCodeBlock( context, & codeBlock, flow, parent );
                lastAdded = processWith( context, nodeToProcess, parent, flow );
                continue;
            case funcdef:
                {
                    std::list<Decorator *>      noDecors;
                    addCodeBlock( context, & codeBlock, flow, parent );
                    lastAdded = processFuncDefinition( context, nodeToProcess,
                                                       parent, flow,
                                                       noDecors );
                }
                continue;
            case classdef:
                {
                    std::list<Decorator *>      noDecors;
                    addCodeBlock( context, & codeBlock, flow, parent );
                    lastAdded = processClassDefinition( context, nodeToProcess,
                                                        parent, flow,
                                                        noDecors );
                }
                continue;
            case decorated:
                {
                    // funcdef or classdef follows
                    if ( nodeToProcess->n_nchildren < 2 )
                        continue;

                    node *  decorsNode = & ( nodeToProcess->n_child[ 0 ] );
                    node *  classOrFuncNode = & ( nodeToProcess->n_child[ 1 ] );

                    if ( decorsNode->n_type != decorators )
                        continue;

                    std::list<Decorator *>      decors =
                            processDecorators( context, flow, parent,
                                               decorsNode );

                    if ( classOrFuncNode->n_type == funcdef )
                    {
                        addCodeBlock( context, & codeBlock, flow, parent );
                        lastAdded = processFuncDefinition( context,
                                                           classOrFuncNode,
                                                           parent, flow,
                                                           decors );
                    }
                    else if ( classOrFuncNode->n_type == classdef )
                    {
                        addCodeBlock( context, & codeBlock, flow, parent );
                        lastAdded = processClassDefinition( context,
                                                            classOrFuncNode,
                                                            parent, flow,
                                                            decors );
                    }
                }
                continue;
        }
    }

    // Add block if needed
    if ( codeBlock != NULL )
        return addCodeBlock( context, & codeBlock, flow, parent );
    return lastAdded;
}


Py::Object  parseInput( const char *  buffer, const char *  fileName,
                        bool  serialize )
{
    ControlFlow *           controlFlow = new ControlFlow();

    if ( serialize )
        controlFlow->content = buffer;

    perrdetail          error;
    PyCompilerFlags     flags = { 0 };
    node *              tree = PyParser_ParseStringFlagsFilename(
                                    buffer, fileName, &_PyParser_Grammar,
                                    file_input, &error, flags.cf_flags );

    if ( tree == NULL )
    {
        controlFlow->errors.append( Py::String( getErrorMessage( & error ) ) );
        PyErr_Clear();
    }
    else
    {
        /* Walk the tree and populate the python structures */
        node *      root = tree;
        int         totalLines = getTotalLines( tree );

        assert( totalLines >= 0 );
        int                         lineShifts[ totalLines + 1 ];
        std::deque< CommentLine >   comments;

        getLineShiftsAndComments( buffer, lineShifts, comments );
        checkForBangLine( buffer, controlFlow, comments );

        if ( root->n_type == encoding_decl )
        {
            processEncoding( buffer, tree, controlFlow, comments );
            root = & (root->n_child[ 0 ]);
        }


        assert( root->n_type == file_input );


        // Walk the syntax tree
        Context         context;
        context.flow = controlFlow;
        context.buffer = buffer;
        context.lineShifts = lineShifts;
        context.comments = & comments;

        // Check for the docstring first
        Docstring *  docstr = checkForDocstring( & context, root );
        if ( docstr != NULL )
        {
            docstr->parent = controlFlow;
            injectComments( & context, controlFlow->nsuite,
                            controlFlow, docstr, docstr );
            controlFlow->docstring = Py::asObject( docstr );
            controlFlow->updateBeginEnd( docstr );
        }

        walk( & context, root, controlFlow,
              controlFlow->nsuite, docstr != NULL );
        PyNode_Free( tree );

        // Inject trailing comments if so
        injectLeadingComments( & context, controlFlow->nsuite,
                               controlFlow, NULL, NULL, INT_MAX );
    }

    return Py::asObject( controlFlow );
}

