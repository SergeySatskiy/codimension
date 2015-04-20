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
walk( node *                       tree,
      FragmentBase *               parent,
      Py::List &                   flow,
      int *                        lineShifts,
      std::list<Decorator *> &     decors,
      bool                         docstrProcessed );




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

static void processEncoding( const char *   buffer,
                             node *         tree,
                             ControlFlow *  controlFlow,
                             const std::vector< CommentLine > &  comments )
{
    /* Unfortunately, the parser does not provide the position of the encoding
     * so it needs to be calculated
     */
    const char *      start = strstr( buffer,
                                tree->n_str );
    if ( start == NULL )
        return;     /* would be really strange */

    int             line = 1;
    int             col = 1;
    const char *    current = buffer;
    while ( current != start )
    {
        if ( * current == '\r' )
        {
            if ( * (current + 1) == '\n' )
                ++current;
            ++line;
            col = 0;
        }
        else if ( * current == '\n' )
        {
            ++line;
            col = 0;
        }
        ++col;
        ++current;
    }

    int     commentIndex = 0;
    for ( ; ; )
    {
        if ( comments[ commentIndex ].line == line )
            break;
        ++commentIndex;
    }


    EncodingLine *      encodingLine( new EncodingLine );
    encodingLine->parent = controlFlow;
    encodingLine->begin = comments[ commentIndex ].begin;
    encodingLine->end = comments[ commentIndex ].end;
    encodingLine->beginLine = line;
    encodingLine->beginPos = comments[ commentIndex ].pos;
    encodingLine->endLine = line;
    encodingLine->endPos = encodingLine->beginPos + ( encodingLine->end -
                                                      encodingLine->begin );
    controlFlow->encodingLine = Py::asObject( encodingLine );
    controlFlow->updateBeginEnd( encodingLine );
}


static FragmentBase *
processBreak( node *  tree, FragmentBase *  parent,
              Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == break_stmt );
    Break *         br( new Break );
    br->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = br;
    updateBegin( body, tree, lineShifts );
    body->end = body->begin + 4;        // 4 = strlen( "break" ) - 1
    body->endLine = tree->n_lineno;
    body->endPos = body->beginPos + 4;  // 4 = strlen( "break" ) - 1

    br->updateBeginEnd( body );
    br->body = Py::asObject( body );
    flow.append( Py::asObject( br ) );
    return br;
}


static FragmentBase *
processContinue( node *  tree, FragmentBase *  parent,
                 Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == continue_stmt );
    Continue *      cont( new Continue );
    cont->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = cont;
    updateBegin( body, tree, lineShifts );
    body->end = body->begin + 7;        // 7 = strlen( "continue" ) - 1
    body->endLine = tree->n_lineno;
    body->endPos = body->beginPos + 7;  // 7 = strlen( "continue" ) - 1

    cont->updateBeginEnd( body );
    cont->body = Py::asObject( body );
    flow.append( Py::asObject( cont ) );
    return cont;
}

static FragmentBase *
processAssert( node *  tree, FragmentBase *  parent,
               Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == assert_stmt );
    Assert *            a( new Assert );
    a->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = a;
    updateBegin( body, tree, lineShifts );
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
    updateBegin( tst, firstTestNode, lineShifts );
    updateEnd( tst, testLastPart, lineShifts );
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
        updateBegin( message, secondTestNode, lineShifts );
        updateEnd( message, secondTestLastPart, lineShifts );

        a->updateEnd( message );
        a->message = Py::asObject( message );
    }
    else
        a->updateEnd( tst );

    a->body = Py::asObject( body );
    flow.append( Py::asObject( a ) );
    return a;
}



static FragmentBase *
processRaise( node *  tree, FragmentBase *  parent,
              Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == raise_stmt );
    Raise *         r( new Raise );
    r->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = r;
    updateBegin( body, tree, lineShifts );
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
        updateBegin( val, testNode, lineShifts );
        updateEnd( val, lastPart, lineShifts );

        r->updateEnd( val );
        r->value = Py::asObject( val );
    }
    else
        r->updateEnd( body );

    r->body = Py::asObject( body );
    flow.append( Py::asObject( r ) );
    return r;
}


static FragmentBase *
processReturn( node *  tree, FragmentBase *  parent,
               Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == return_stmt );
    Return *        ret( new Return );
    ret->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = ret;
    updateBegin( body, tree, lineShifts );
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
        updateBegin( val, testlistNode, lineShifts );
        updateEnd( val, lastPart, lineShifts );

        ret->updateEnd( val );
        ret->value = Py::asObject( val );
    }
    else
        ret->updateEnd( body );

    ret->body = Py::asObject( body );
    flow.append( Py::asObject( ret ) );
    return ret;
}


// Handles 'else' and 'elif' clauses for various statements: 'if' branches,
// 'else' parts of 'while', 'for', 'try'
static ElifPart *
processElifPart( node *  tree, FragmentBase *  parent,
                 int *  lineShifts )
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
        updateBegin( condition, current, lineShifts );
        updateEnd( condition, last, lineShifts );
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
    updateBegin( body, tree, lineShifts );
    updateEnd( body, colonNode, lineShifts );
    elifPart->updateBegin( body );
    elifPart->body = Py::asObject( body );

    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( suiteNode,
                                                  elifPart, elifPart->nsuite,
                                                  lineShifts, emptyDecors,
                                                  false );
    if ( lastAdded == NULL )
        elifPart->updateEnd( body );
    else
        elifPart->updateEnd( lastAdded );
    return elifPart;
}


static FragmentBase *
processIf( node *  tree, FragmentBase *  parent,
           Py::List &  flow, int *  lineShifts )
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
                updateBegin( condition, conditionNode, lineShifts );
                updateEnd( condition, last, lineShifts );
                ifStatement->condition = Py::asObject( condition );

                node *      colonNode = conditionNode + 1;
                node *      suiteNode = colonNode + 1;

                Fragment *      body( new Fragment );
                body->parent = ifStatement;
                updateBegin( body, tree, lineShifts );
                updateEnd( body, colonNode, lineShifts );
                ifStatement->updateBegin( body );
                ifStatement->body = Py::asObject( body );

                std::list<Decorator *>      emptyDecors;
                FragmentBase *              lastAdded = walk( suiteNode,
                                                              ifStatement,
                                                              ifStatement->nsuite,
                                                              lineShifts, emptyDecors,
                                                              false );
                if ( lastAdded == NULL )
                    ifStatement->updateEnd( body );
                else
                    ifStatement->updateEnd( lastAdded );
            }
            else
            {
                ElifPart *  elifPart = processElifPart( child, ifStatement,
                                                        lineShifts );
                ifStatement->updateBegin( elifPart );
                ifStatement->elifParts.append( Py::asObject( elifPart ) );
            }
        }
    }

    flow.append( Py::asObject( ifStatement ) );
    return ifStatement;
}


static ExceptPart *
processExceptPart( node *  tree, FragmentBase *  parent, int *  lineShifts )
{
    assert( tree->n_type == except_clause ||
            tree->n_type == NAME );

    ExceptPart *    exceptPart( new ExceptPart );
    exceptPart->parent = parent;

    Fragment *      body( new Fragment );
    body->parent = exceptPart;

    // ':' node is the very next one
    node *          colonNode = tree + 1;
    updateBegin( body, tree, lineShifts );
    updateEnd( body, colonNode, lineShifts );
    exceptPart->updateBegin( body );
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
            updateBegin( clause, testNode, lineShifts );
            updateEnd( clause, last, lineShifts );
            exceptPart->clause = Py::asObject( clause );
        }
    }

    // 'suite' node follows the colon node
    node *                      suiteNode = colonNode + 1;
    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( suiteNode, exceptPart,
                                                  exceptPart->nsuite,
                                                  lineShifts, emptyDecors,
                                                  false );
    if ( lastAdded == NULL )
        exceptPart->updateEnd( body );
    else
        exceptPart->updateEnd( lastAdded );
    return exceptPart;
}


static FragmentBase *
processTry( node *  tree, FragmentBase *  parent,
            Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == try_stmt );

    Try *       tryStatement( new Try );
    tryStatement->parent = parent;

    Fragment *      body( new Fragment );
    node *          tryColonNode = findChildOfType( tree, COLON );
    body->parent = tryStatement;
    updateBegin( body, tree, lineShifts );
    updateEnd( body, tryColonNode, lineShifts );
    tryStatement->body = Py::asObject( body );
    tryStatement->updateBegin( body );

    // suite
    node *                      trySuiteNode = tryColonNode + 1;
    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( trySuiteNode, tryStatement,
                                                  tryStatement->nsuite,
                                                  lineShifts, emptyDecors,
                                                  false );
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
            ExceptPart *    exceptPart = processExceptPart( child,
                                                            tryStatement,
                                                            lineShifts );
            tryStatement->exceptParts.append( Py::asObject( exceptPart ) );
            continue;
        }
        if ( child->n_type == NAME )
        {
            if ( strcmp( child->n_str, "else" ) == 0 )
            {
                ExceptPart *    elsePart = processExceptPart( child,
                                                              tryStatement,
                                                              lineShifts );
                tryStatement->elsePart = Py::asObject( elsePart );
                continue;
            }
            if ( strcmp( child->n_str, "finally" ) == 0 )
            {
                ExceptPart *    finallyPart = processExceptPart( child,
                                                                 tryStatement,
                                                                 lineShifts );
                tryStatement->finallyPart = Py::asObject( finallyPart );
            }
        }
    }

    flow.append( Py::asObject( tryStatement ) );
    return tryStatement;
}


static FragmentBase *
processWhile( node *  tree, FragmentBase *  parent,
              Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == while_stmt );

    While *     w( new While);
    w->parent = parent;

    Fragment *      body( new Fragment );
    node *          colonNode = findChildOfType( tree, COLON );
    node *          whileNode = findChildOfType( tree, NAME );

    body->parent = w;
    updateBegin( body, whileNode, lineShifts );
    updateEnd( body, colonNode, lineShifts );
    w->body = Py::asObject( body );
    w->updateBegin( body );

    // condition
    node *          testNode = findChildOfType( tree, test );
    node *          lastPart = findLastPart( testNode );
    Fragment *      condition( new Fragment );

    condition->parent = w;
    updateBegin( condition, testNode, lineShifts );
    updateEnd( condition, lastPart, lineShifts );
    w->condition = Py::asObject( condition );

    // suite
    node *                      suiteNode = findChildOfType( tree, suite );
    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( suiteNode, w, w->nsuite,
                                                  lineShifts, emptyDecors,
                                                  false );
    if ( lastAdded == NULL )
        w->updateEnd( body );
    else
        w->updateEnd( lastAdded );

    // else part
    node *          elseNode = findChildOfTypeAndValue( tree, NAME, "else" );
    if ( elseNode != NULL )
    {
        ElifPart *      elsePart = processElifPart( elseNode, w, lineShifts );
        w->elsePart = Py::asObject( elsePart );
    }

    flow.append( Py::asObject( w ) );
    return w;
}


static FragmentBase *
processWith( node *  tree, FragmentBase *  parent,
             Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == with_stmt );

    With *      w( new With );
    w->parent = parent;

    Fragment *      body( new Fragment );
    node *          colonNode = findChildOfType( tree, COLON );
    node *          whithNode = findChildOfType( tree, NAME );

    body->parent = w;
    updateBegin( body, whithNode, lineShifts );
    updateEnd( body, colonNode, lineShifts );
    w->body = Py::asObject( body );
    w->updateBegin( body );

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
    updateBegin( items, firstWithItem, lineShifts );
    updateEnd( items, lastWithItem, lineShifts );
    w->items = Py::asObject( items );

    // suite
    node *                      suiteNode = findChildOfType( tree, suite );
    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( suiteNode, w, w->nsuite,
                                                  lineShifts, emptyDecors,
                                                  false );
    if ( lastAdded == NULL )
        w->updateEnd( body );
    else
        w->updateEnd( lastAdded );

    flow.append( Py::asObject( w ) );
    return w;
}


static FragmentBase *
processFor( node *  tree, FragmentBase *  parent,
            Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == for_stmt );

    For *       f( new For );
    f->parent = parent;

    Fragment *      body( new Fragment );
    node *          colonNode = findChildOfType( tree, COLON );
    node *          forNode = findChildOfType( tree, NAME );

    body->parent = f;
    updateBegin( body, forNode, lineShifts );
    updateEnd( body, colonNode, lineShifts );
    f->body = Py::asObject( body );
    f->updateBegin( body );

    // Iteration
    node *          exprlistNode = findChildOfType( tree, exprlist );
    node *          testlistNode = findChildOfType( tree, testlist );
    node *          lastPart = findLastPart( testlistNode );
    Fragment *      iteration( new Fragment );

    iteration->parent = f;
    updateBegin( iteration, exprlistNode, lineShifts );
    updateEnd( iteration, lastPart, lineShifts );
    f->iteration = Py::asObject( iteration );

    // suite
    node *                      suiteNode = findChildOfType( tree, suite );
    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( suiteNode, f, f->nsuite,
                                                  lineShifts, emptyDecors,
                                                  false );
    if ( lastAdded == NULL )
        f->updateEnd( body );
    else
        f->updateEnd( lastAdded );

    // else part
    node *          elseNode = findChildOfTypeAndValue( tree, NAME, "else" );
    if ( elseNode != NULL )
    {
        ElifPart *      elsePart = processElifPart( elseNode, f, lineShifts );
        f->elsePart = Py::asObject( elsePart );
    }

    flow.append( Py::asObject( f ) );
    return f;
}


static FragmentBase *
processImport( node *  tree, FragmentBase *  parent,
               Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == import_stmt );
    assert( tree->n_nchildren == 1 );


    Import *        import( new Import );
    import->parent = parent;

    Fragment *      body( new Fragment );
    node *          lastPart = findLastPart( tree );

    body->parent = import;
    updateBegin( body, tree, lineShifts );
    updateEnd( body, lastPart, lineShifts );

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

        updateBegin( fromFragment, fromPartBegin, lineShifts );

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

        updateEnd( fromFragment, lastFromPart, lineShifts );

        node *      whatPart = findChildOfTypeAndValue( tree, NAME, "import" );
        assert( whatPart != NULL );

        ++whatPart;     // the very next after import is the first of the what part
        updateBegin( whatFragment, whatPart, lineShifts );
        updateEnd( whatFragment, lastPart, lineShifts );

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
        updateBegin( whatFragment, firstWhat, lineShifts );

        // The end matches the body
        whatFragment->end = body->end;
        whatFragment->endLine = body->endLine;
        whatFragment->endPos = body->endPos;

        import->whatPart = Py::asObject( whatFragment );
    }

    import->updateBeginEnd( body );
    import->body = Py::asObject( body );
    flow.append( Py::asObject( import ) );
    return import;
}

static void
processDecor( node *  tree, int *  lineShifts,
              std::list<Decorator *> &  decors )
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
    updateBegin( nameFragment, nameNode, lineShifts );
    updateEnd( nameFragment, lastNameNode, lineShifts );
    decor->name = Py::asObject( nameFragment );

    Fragment *      body( new Fragment );
    body->parent = decor;
    updateBegin( body, atNode, lineShifts );

    if ( lparNode == NULL )
    {
        // Decorator without arguments
        updateEnd( body, lastNameNode, lineShifts );
    }
    else
    {
        // Decorator with arguments
        node *          rparNode = findChildOfType( tree, RPAR );
        Fragment *      argsFragment( new Fragment );

        argsFragment->parent = decor;
        updateBegin( argsFragment, lparNode, lineShifts );
        updateEnd( argsFragment, rparNode, lineShifts );
        decor->arguments = Py::asObject( argsFragment );
        updateEnd( body, rparNode, lineShifts );
    }

    decor->body = Py::asObject( body );
    decor->updateBeginEnd( body );
    decors.push_back( decor );
    return;
}


static std::list<Decorator *>
processDecorators( node *  tree, int *  lineShifts )
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
            processDecor( child, lineShifts, decors );
        }
    }
    return decors;
}


// None or Docstring instance
Docstring *  checkForDocstring( node *  tree, int *  lineShifts )
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
        updateBegin( part, stringChild, lineShifts );
        updateEnd( part, stringChild, lineShifts );

        // In the vast majority of cases a docstring consists of a single part
        // so there is no need to optimize via updateBegin() & updateEnd()
        docstr->updateBeginEnd( part );
        docstr->parts.append( Py::asObject( part ) );
    }

    return docstr;
}


static FragmentBase *
processFuncDefinition( node *                       tree,
                       FragmentBase *               parent,
                       Py::List &                   flow,
                       int *                        lineShifts,
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
    updateBegin( body, defNode, lineShifts );
    updateEnd( body, colonNode, lineShifts );
    func->body = Py::asObject( body );

    Fragment *      name( new Fragment );
    name->parent = func;
    updateBegin( name, nameNode, lineShifts );
    updateEnd( name, nameNode, lineShifts );
    func->name = Py::asObject( name );

    node *      params = findChildOfType( tree, parameters );
    node *      lparNode = findChildOfType( params, LPAR );
    node *      rparNode = findChildOfType( params, RPAR );
    Fragment *  args( new Fragment );
    args->parent = func;
    updateBegin( args, lparNode, lineShifts );
    updateEnd( args, rparNode, lineShifts );
    func->arguments = Py::asObject( args );

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

    // Handle docstring if so
    node *      suiteNode = findChildOfType( tree, suite );
    assert( suiteNode != NULL );

    Docstring *  docstr = checkForDocstring( suiteNode, lineShifts );
    if ( docstr != NULL )
    {
        docstr->parent = func;
        func->docstring = Py::asObject( docstr );

        // It could be that a docstring is the only item in the function suite
        func->updateEnd( docstr );
    }

    // Walk nested nodes
    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( suiteNode, func,
                                                  func->nsuite,
                                                  lineShifts, emptyDecors,
                                                  docstr != NULL );
    if ( lastAdded == NULL )
        func->updateEnd( body );
    else
        func->updateEnd( lastAdded );
    flow.append( Py::asObject( func ) );
    return func;
}


static FragmentBase *
processClassDefinition( node *                       tree,
                        FragmentBase *               parent,
                        Py::List &                   flow,
                        int *                        lineShifts,
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
    updateBegin( body, defNode, lineShifts );
    updateEnd( body, colonNode, lineShifts );
    cls->body = Py::asObject( body );

    Fragment *      name( new Fragment );
    name->parent = cls;
    updateBegin( name, nameNode, lineShifts );
    updateEnd( name, nameNode, lineShifts );
    cls->name = Py::asObject( name );

    node *      lparNode = findChildOfType( tree, LPAR );
    if ( lparNode != NULL )
    {
        // There is a list of base classes
        node *      rparNode = findChildOfType( tree, RPAR );
        Fragment *  baseClasses( new Fragment );

        baseClasses->parent = cls;
        updateBegin( baseClasses, lparNode, lineShifts );
        updateEnd( baseClasses, rparNode, lineShifts );
        cls->baseClasses = Py::asObject( baseClasses );
    }

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

    // Handle docstring if so
    node *      suiteNode = findChildOfType( tree, suite );
    assert( suiteNode != NULL );

    Docstring *  docstr = checkForDocstring( suiteNode, lineShifts );
    if ( docstr != NULL )
    {
        docstr->parent = cls;
        cls->docstring = Py::asObject( docstr );

        // It could be that a docstring is the only item in the class suite
        cls->updateEnd( docstr );
    }

    // Walk nested nodes
    std::list<Decorator *>      emptyDecors;
    FragmentBase *              lastAdded = walk( suiteNode, cls, cls->nsuite,
                                                  lineShifts, emptyDecors,
                                                  docstr != NULL );

    if ( lastAdded == NULL )
        cls->updateEnd( body );
    else
        cls->updateEnd( lastAdded );

    flow.append( Py::asObject( cls ) );
    return cls;
}



static FragmentBase *
walk( node *                       tree,
      FragmentBase *               parent,
      Py::List &                   flow,
      int *                        lineShifts,
      std::list<Decorator *> &     decors,
      bool                         docstrProcessed )
{
    switch ( tree->n_type )
    {
        case import_stmt:
            return processImport( tree, parent, flow, lineShifts );
        case funcdef:
            return processFuncDefinition( tree, parent, flow,
                                          lineShifts, decors );
        case classdef:
            return processClassDefinition( tree, parent, flow,
                                           lineShifts, decors );
        case return_stmt:
            return processReturn( tree, parent, flow, lineShifts );
        case break_stmt:
            return processBreak( tree, parent, flow, lineShifts );
        case continue_stmt:
            return processContinue( tree, parent, flow, lineShifts );
        case raise_stmt:
            return processRaise( tree, parent, flow, lineShifts );
        case assert_stmt:
            return processAssert( tree, parent, flow, lineShifts );
        case while_stmt:
            return processWhile( tree, parent, flow, lineShifts );
        case for_stmt:
            return processFor( tree, parent, flow, lineShifts );
        case if_stmt:
            return processIf( tree, parent, flow, lineShifts );
        case try_stmt:
            return processTry( tree, parent, flow, lineShifts );
        case with_stmt:
            return processWith( tree, parent, flow, lineShifts );

        default:
            break;
    }

    FragmentBase *              lastAdded( NULL );
    std::list<Decorator *>      foundDecors;
    int                         statementCount = 0;
    for ( int  i = 0; i < tree->n_nchildren; ++i )
    {
        node *      child = & ( tree->n_child[ i ] );
        if ( child->n_type == NEWLINE || child->n_type == INDENT )
            continue;

        ++statementCount;

        /* decorators are always before a class or a function definition on the
         * same level. So they will be picked by the following definition
         */
        if ( child->n_type == decorators )
        {
            foundDecors = processDecorators( child, lineShifts );
            continue;
        }

        // Skip processing a statement if it is a docstring which has already
        // been processed on the previous step
        if ( statementCount != 1 || docstrProcessed == false )
        {
            lastAdded = walk( child, parent, flow,
                              lineShifts, foundDecors, false );
        }
    }

    return lastAdded;
}




Py::Object  parseInput( const char *  buffer, const char *  fileName )
{
    ControlFlow *           controlFlow = new ControlFlow();

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
        std::vector< CommentLine >  comments;

        comments.reserve( totalLines );     // There are no more comments than lines
        getLineShiftsAndComments( buffer, lineShifts, comments );

        if ( root->n_type == encoding_decl )
        {
            processEncoding( buffer, tree, controlFlow, comments );
            root = & (root->n_child[ 0 ]);
        }


        assert( root->n_type == file_input );

        // Check for the docstring first
        Docstring *  docstr = checkForDocstring( root, lineShifts );
        if ( docstr != NULL )
        {
            docstr->parent = controlFlow;
            controlFlow->docstring = Py::asObject( docstr );
            controlFlow->updateBeginEnd( docstr );
        }

        // Walk the syntax tree
        std::list<Decorator *>      decors;
        walk( root, controlFlow, controlFlow->nsuite,
              lineShifts, decors, docstr != NULL );
        PyNode_Free( tree );

        // Second pass: inject comments
        for ( std::vector< CommentLine >::const_iterator
                k = comments.begin(); k != comments.end(); ++k )
        {
            if ( k->line == 1 &&
                 k->end - k->begin > 1 &&
                 buffer[ k->begin + 1 ] == '!' )
            {
                // That's a bang line
                BangLine *          bangLine( new BangLine );
                bangLine->parent = controlFlow;
                bangLine->begin = k->begin;
                bangLine->end = k->end;
                bangLine->beginLine = 1;
                bangLine->beginPos = k->pos;
                bangLine->endLine = 1;
                bangLine->endPos = bangLine->beginPos + ( bangLine->end -
                                                          bangLine->begin );
                controlFlow->bangLine = Py::asObject( bangLine );
                controlFlow->updateBeginEnd( bangLine );
                continue;
            }

            // Regular comment (not encoding, not bang)
        }
    }

    return Py::asObject( controlFlow );
}

