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

#include "cflowparser.hpp"
#include "cflowfragments.hpp"
#include "cflowcomments.hpp"


extern grammar      _PyParser_Grammar;  /* From graminit.c */


/* Holds the currently analysed scope */
enum Scope {
    GLOBAL_SCOPE,
    FUNCTION_SCOPE,
    CLASS_SCOPE,
    CLASS_METHOD_SCOPE,
    CLASS_STATIC_METHOD_SCOPE
};


/* Copied and adjusted from Python/pythonrun.c
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



static void processImport( node *  tree, FragmentBase *  parent,
                           Py::List &  flow, int *  lineShifts )
{
    assert( tree->n_type == import_stmt );
    assert( tree->n_nchildren == 1 );


    Import *        import( new Import );
    import->parent = parent;


    /* There must be one child of type import_from or import_name */
    tree = & (tree->n_child[ 0 ]);
    if ( tree->n_type == import_from )
    {

    }
    else
    {
        assert( tree->n_type == import_name );
        import->fromPart = Py::None();

        Fragment *      fragment = new Fragment;

        fragment->parent = import;
        fragment->begin = 
        fragment->end =
        fragment->beginLine =
        fragment->beginPos =
        fragment->endLine =
        fragment->endPos =


        import->whatPart = Py::asObject( fragment );
        // TODO: update import end
    }

    flow.append( Py::asObject( import ) );
    parent->updateBeginEnd( import );
    return;
}


void walk( node *                       tree,
           FragmentBase *               parent,
           Py::List &                   flow,
           int                          objectsLevel,
           enum Scope                   scope,
           const char *                 firstArgName,
           int                          entryLevel,
           int *                        lineShifts,
           int                          isStaticMethod )
{
    ++entryLevel;   // For module docstring only

    switch ( tree->n_type )
    {
        case import_stmt:
            processImport( tree, parent, flow, lineShifts );
            return;
#if 0
        case funcdef:
            processFuncDefinition( tree, callbacks,
                                   objectsLevel, scope, entryLevel,
                                   lineShifts, isStaticMethod );
            return;
        case classdef:
            processClassDefinition( tree, callbacks,
                                    objectsLevel, scope, entryLevel,
                                    lineShifts );
            return;
        case stmt:
            {
                node *      assignNode = isAssignment( tree );
                if ( assignNode != NULL )
                {
                    node *      testListNode = & ( assignNode->n_child[ 0 ] );
                    if ( scope == GLOBAL_SCOPE )
                        processAssign( testListNode, callbacks->onGlobal,
                                       objectsLevel, lineShifts );
                    else if ( scope == CLASS_SCOPE )
                        processAssign( testListNode,
                                       callbacks->onClassAttribute,
                                       objectsLevel, lineShifts );
                    else if ( scope == CLASS_METHOD_SCOPE )
                        processInstanceMember( testListNode, callbacks,
                                               firstArgName, objectsLevel,
                                               lineShifts );

                    /* The other scopes are not interesting */
                    return;
                }
            }
#endif

        default:
            break;
    }

//    int     staticDecor = 0;
    for ( int  i = 0; i < tree->n_nchildren; ++i )
    {
        node *      child = & ( tree->n_child[ i ] );

        if ( (entryLevel == 1) && (i == 0) )
        {
            /* This could be a module docstring */
//            checkForDocstring( tree, callbacks );
        }

        /* decorators are always before a class or a function definition on the
         * same level. So they will be picked by the following deinition
         */
//        if ( child->n_type == decorators )
//        {
//            staticDecor = processDecorators( child, callbacks, lineShifts );
//            continue;
//        }
        walk( child, callbacks, objectsLevel,
              scope, firstArgName, entryLevel, lineShifts, staticDecor );
//        staticDecor = 0;
    }

    return;
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
        walk( root, controlFlow, controlFlow->nsuite, -1,
              GLOBAL_SCOPE, NULL, 0, lineShifts, 0 );
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
        }
    }

    return Py::asObject( controlFlow );
}

