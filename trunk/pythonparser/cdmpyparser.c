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
 * Python extension module
 */


#include <Python.h>
#include "pythonbriefLexer.h"
#include "pythonbriefParser.h"

#include <string.h>

#ifndef CDM_PY_PARSER_VERSION
#define CDM_PY_PARSER_VERSION       "trunk"
#endif
#define MAX_DOTTED_NAME_LENGTH      512


/* copied (and modified) from libantlr3 to avoid indirect function calls */
static ANTLR3_UINT32 getType( pANTLR3_BASE_TREE tree )
{
    pANTLR3_COMMON_TREE    theTree = (pANTLR3_COMMON_TREE)(tree->super);

    if (theTree->token == NULL)
        return 0;
    return theTree->token->type;
}
static pANTLR3_COMMON_TOKEN getToken( pANTLR3_BASE_TREE  tree )
{
    return  ((pANTLR3_COMMON_TREE)(tree->super))->token;
}



/* Holds the currently analysed scope */
enum Scope {
    GLOBAL_SCOPE,
    FUNCTION_SCOPE,
    CLASS_SCOPE,
    CLASS_METHOD_SCOPE,
    CLASS_STATIC_METHOD_SCOPE
};


/* The structure holds resolved callbacks for Python class methods */
struct instanceCallbacks
{
    PyObject *      onEncoding;
    PyObject *      onGlobal;
    PyObject *      onFunction;
    PyObject *      onClass;
    PyObject *      onImport;
    PyObject *      onAs;
    PyObject *      onWhat;
    PyObject *      onClassAttribute;
    PyObject *      onInstanceAttribute;
    PyObject *      onDecorator;
    PyObject *      onDecoratorArgument;
    PyObject *      onDocstring;
    PyObject *      onArgument;
    PyObject *      onBaseClass;
    PyObject *      onError;
    PyObject *      onLexerError;
};

/* Forward declaration */
void walk( pANTLR3_BASE_TREE            tree,
           struct instanceCallbacks *   callbacks,
           int                          objectsLevel,
           enum Scope                   scope,
           const char *                 firstArgName,
           int                          entryLevel );


#define GET_CALLBACK( name )                                                \
    callbacks->name = PyObject_GetAttrString( instance, "_" #name );        \
    if ( (! callbacks->name) || (! PyCallable_Check(callbacks->name)) )     \
    {                                                                       \
        PyErr_SetString( PyExc_TypeError, "Cannot get _" #name " method" ); \
        return 1;                                                           \
    }

#define FREE_CALLBACK( name )           \
    if ( callbacks->name )              \
    {                                   \
        Py_DECREF( callbacks->name );   \
    }



/* Helper function to extract and check method pointers */
static int
getInstanceCallbacks( PyObject *                  instance,
                      struct instanceCallbacks *  callbacks )
{
    memset( callbacks, 0, sizeof( struct instanceCallbacks ) );

    GET_CALLBACK( onEncoding );
    GET_CALLBACK( onGlobal );
    GET_CALLBACK( onClass );
    GET_CALLBACK( onFunction );
    GET_CALLBACK( onImport );
    GET_CALLBACK( onAs );
    GET_CALLBACK( onWhat );
    GET_CALLBACK( onClassAttribute );
    GET_CALLBACK( onInstanceAttribute );
    GET_CALLBACK( onDecorator );
    GET_CALLBACK( onDecoratorArgument );
    GET_CALLBACK( onDocstring );
    GET_CALLBACK( onArgument );
    GET_CALLBACK( onBaseClass );
    GET_CALLBACK( onError );
    GET_CALLBACK( onLexerError );

    return 0;
}

static void
clearCallbacks( struct instanceCallbacks *  callbacks )
{
    if ( callbacks == NULL )
        return;

    FREE_CALLBACK( onEncoding );
    FREE_CALLBACK( onGlobal );
    FREE_CALLBACK( onFunction);
    FREE_CALLBACK( onClass );
    FREE_CALLBACK( onImport );
    FREE_CALLBACK( onAs );
    FREE_CALLBACK( onWhat );
    FREE_CALLBACK( onClassAttribute );
    FREE_CALLBACK( onInstanceAttribute );
    FREE_CALLBACK( onDecorator );
    FREE_CALLBACK( onDecoratorArgument );
    FREE_CALLBACK( onDocstring );
    FREE_CALLBACK( onArgument );
    FREE_CALLBACK( onBaseClass );
    FREE_CALLBACK( onError );
    FREE_CALLBACK( onLexerError );
    return;
}

static void
callOnEncoding( PyObject *  onEncoding, const char *  encoding_,
                int  line_,  int  pos_,  int  absPosition_ )
{
    PyObject *  encoding = PyString_FromString( encoding_ );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onEncoding, encoding,
                                                    line, pos, absPos,
                                                    NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( encoding );
    return;
}


static void
callOnError( PyObject *  onError_, const char *  error_ )
{
    PyObject *  error = PyString_FromString( error_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onError_, error, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( error );
    return;
}


static void
callOnArg( PyObject *  onArg, const char *  name, int  length )
{
    register PyObject *  argName = PyString_FromStringAndSize( name, length );
    register PyObject *  ret = PyObject_CallFunctionObjArgs( onArg, argName, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( argName );
    return;
}


static void
callOnVariable( PyObject *  onVariable, const char *  name, int  length,
                int  line_, int  pos_, int  absPosition_, int  objectsLevel_ )
{
    PyObject *  varName = PyString_FromStringAndSize( name, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  objectsLevel = PyInt_FromLong( objectsLevel_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onVariable, varName, line, pos,
                                                    absPos, objectsLevel, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( objectsLevel );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( varName );
    return;
}


static void
callOnImport( PyObject *  onImport, const char *  name, int  length,
              int  line_, int  pos_, int  absPosition_ )
{
    PyObject *  import = PyString_FromStringAndSize( name, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onImport, import, line, pos,
                                                    absPos, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( import );
    return;
}


static void
callOnAs( PyObject *  onAs, const char *  name, int  length)
{
    PyObject *  as = PyString_FromStringAndSize( name, length );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onAs, as, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( as );
    return;
}


static void
callOnWhat( PyObject *  onWhat, const char *  name, int  length,
            int  line_, int  pos_, int  absPosition_ )
{
    PyObject *  what = PyString_FromStringAndSize( name, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onWhat, what, line, pos,
                                                    absPos, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( what );
    return;
}


static void
callOnDocstring( PyObject *  onDocstring, const char *  doc, int  length,
                 int  line_ )
{
    PyObject *  docstring = PyString_FromStringAndSize( doc, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onDocstring, docstring,
                                                    line, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( line );
    Py_DECREF( docstring );
    return;
}



static void
callOnDecorator( PyObject *  onDecorator,
                 const char *  name, int  length,
                 int  line_, int  pos_, int  absPosition_ )
{
    PyObject *  decorName = PyString_FromStringAndSize( name, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onDecorator, decorName,
                                                    line, pos,
                                                    absPos, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( decorName );
    return;
}


static void
callOnClass( PyObject *  onClass,
             const char *  name, int  length,
             int  line_, int  pos_, int  absPosition_,
             int  kwLine_, int  kwPos_,
             int  colonLine_, int  colonPos_,
             int  objectsLevel_ )
{
    PyObject *  className = PyString_FromStringAndSize( name, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  kwLine = PyInt_FromLong( kwLine_ );
    PyObject *  kwPos = PyInt_FromLong( kwPos_ );
    PyObject *  colonLine = PyInt_FromLong( colonLine_ );
    PyObject *  colonPos = PyInt_FromLong( colonPos_ );
    PyObject *  objectsLevel = PyInt_FromLong( objectsLevel_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs(
                                onClass, className, line, pos,
                                absPos, kwLine, kwPos, colonLine, colonPos,
                                objectsLevel, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( objectsLevel );
    Py_DECREF( colonPos );
    Py_DECREF( colonLine );
    Py_DECREF( kwPos );
    Py_DECREF( kwLine );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( className );
    return;
}


static void
callOnInstanceAttribute( PyObject *  onInstanceAttribute,
                         const char *  name, int  length,
                         int  line_, int  pos_, int  absPosition_,
                         int  objectsLevel_ )
{
    PyObject *  attrName = PyString_FromStringAndSize( name, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  objectsLevel = PyInt_FromLong( objectsLevel_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs(
                                onInstanceAttribute, attrName,
                                line, pos, absPos, objectsLevel, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( objectsLevel );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( attrName );
    return;
}


static void
callOnFunction( PyObject *  onFunction,
                const char *  name, int  length,
                int  line_, int  pos_, int  absPosition_,
                int  kwLine_, int  kwPos_,
                int  colonLine_, int  colonPos_,
                int  objectsLevel_ )
{
    PyObject *  funcName = PyString_FromStringAndSize( name, length );
    PyObject *  line = PyInt_FromLong( line_ );
    PyObject *  pos = PyInt_FromLong( pos_ );
    PyObject *  absPos = PyInt_FromLong( absPosition_ );
    PyObject *  kwLine = PyInt_FromLong( kwLine_ );
    PyObject *  kwPos = PyInt_FromLong( kwPos_ );
    PyObject *  colonLine = PyInt_FromLong( colonLine_ );
    PyObject *  colonPos = PyInt_FromLong( colonPos_ );
    PyObject *  objectsLevel = PyInt_FromLong( objectsLevel_ );
    PyObject *  ret = PyObject_CallFunctionObjArgs(
                                onFunction, funcName, line, pos,
                                absPos, kwLine, kwPos, colonLine, colonPos,
                                objectsLevel, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( objectsLevel );
    Py_DECREF( colonPos );
    Py_DECREF( colonLine );
    Py_DECREF( kwPos );
    Py_DECREF( kwLine );
    Py_DECREF( absPos );
    Py_DECREF( pos );
    Py_DECREF( line );
    Py_DECREF( funcName );
    return;
}


static void
callOnBaseClass( PyObject *  onBaseClass,
                 const char *  name, int  length )
{
    PyObject *  baseClassName = PyString_FromStringAndSize( name, length );
    PyObject *  ret = PyObject_CallFunctionObjArgs(
                                onBaseClass, baseClassName, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( baseClassName );
    return;
}



/* Fills the given buffer
 * Returns: token of the first name tokens
 */
static pANTLR3_COMMON_TOKEN  getDottedName( pANTLR3_BASE_TREE  tree,
                                            char *             name,
                                            int *              len )
{
    ANTLR3_UINT32           n = tree->children->count;
    ANTLR3_UINT32           k;
    pANTLR3_COMMON_TOKEN    firstToken = NULL;
    pANTLR3_COMMON_TOKEN    currentToken;
    pANTLR3_BASE_TREE       child;
    int                     partLen;

    *len = 0;

    for ( k = 0; k < n; ++k )
    {
        child = vectorGet( tree->children, k );

        currentToken = getToken( child );
        if ( k != 0 )
        {
            name[ *len ] = '.';
            ++(*len);
        }
        else
            firstToken = currentToken;

        /* It is possible by some reasons that a DOTTED_NAME node is formed
         * of length 1 however the first token start and stop is NULL. That
         * happens when there is no actual name after a syntax construction
         * found, e.g.:
         * import
         * So there is an explicit check here.
         * I have no ideas why the DOTTED_NAME is formed at all...
         */
        if ( currentToken->start == 0 )
        {
            name[ *len ] = '\0';
            return firstToken;
        }

        partLen = (char *)(currentToken->stop) - (char *)(currentToken->start) + 1;
        memcpy( name + *len, (char *)(currentToken->start), partLen );
        *len += partLen;
    }
    name[ *len ] = '\0';
    return firstToken;
}


/* returns 1 or 3, i.e. the number of quotes used in a string literal part */
static size_t getStringLiteralPrefixLength( pANTLR3_COMMON_TOKEN  token )
{
    char *      firstChar = (char *)token->start;
    // char *      lastChar = (char *)token->stop;

    if ( strncmp( firstChar, "\"\"\"", 3 ) == 0 )
        return 3;
    if ( strncmp( firstChar, "'''", 3 ) == 0 )
        return 3;
    return 1;
}


/* I saw some files which have bigger than 32kb docstrings! */
#define MAX_DOCSTRING_SIZE      65535

static void checkForDocstring( pANTLR3_BASE_TREE             tree,
                               struct instanceCallbacks *    callbacks )
{
    if ( tree == NULL )
        return;

    if ( getType( tree ) == TEST_LIST )
    {
        if ( tree->children->count < 1 )
            return;

        tree = vectorGet( tree->children, 0 );
    }

    if ( getType( tree ) != STRING_LITERAL )
        return;

    {
        char                    buffer[ MAX_DOCSTRING_SIZE ];
        size_t                  collected = 0;
        pANTLR3_BASE_TREE       currentPart;
        pANTLR3_COMMON_TOKEN    currentToken;
        size_t                  index = 0;
        size_t                  charsToSkip;
        size_t                  charsToCopy;

        while ( index < tree->children->count )
        {
            currentPart = vectorGet( tree->children, index );
            currentToken = getToken( currentPart );
            charsToSkip = getStringLiteralPrefixLength( currentToken );
            charsToCopy = (char *)currentToken->stop -
                          (char *)currentToken->start - 2 * charsToSkip + 1;

            if ( collected + charsToCopy + 1 > MAX_DOCSTRING_SIZE )
            {
                memcpy( buffer + collected,
                        (char *)currentToken->start + charsToSkip,
                        MAX_DOCSTRING_SIZE - collected - 1 );
                collected = MAX_DOCSTRING_SIZE - 1;
                break;
            }

            memcpy( buffer + collected,
                    (char *)currentToken->start + charsToSkip,
                    charsToCopy );
            collected += charsToCopy;
            ++index;
        }

        buffer[ collected ] = 0;
        callOnDocstring( callbacks->onDocstring, buffer, collected,
                         tree->getLine( tree ) );
    }
    return;
}


static void  processWhat( pANTLR3_BASE_TREE            tree,
                          struct instanceCallbacks *   callbacks )
{
    ANTLR3_UINT32           n = tree->children->count;
    ANTLR3_UINT32           k;
    pANTLR3_STRING          s;
    pANTLR3_BASE_TREE       child;
    pANTLR3_BASE_TREE       asChild;
    pANTLR3_COMMON_TOKEN    token;

    for ( k = 0; k < n; ++k )
    {
        child = vectorGet( tree->children, k );
        if ( getType( child ) == AS )
        {
            asChild = vectorGet( child->children, 0 );
            s = asChild->toString( asChild );
            callOnAs( callbacks->onAs, (const char *)(s->chars), s->len );
        }
        else
        {
            /* Otherwise it is what is imported */
            token = getToken( child );
            s = child->toString( child );
            callOnWhat( callbacks->onWhat, (const char *)(s->chars), s->len,
                        token->line,
                        token->charPosition + 1, /* Make it 1-based */
                        (char *)token->start - (char *)token->input->data );
        }
    }
    return;
}


static void  processImport( pANTLR3_BASE_TREE            tree,
                            struct instanceCallbacks *   callbacks )
{
    ANTLR3_UINT32       n = tree->children->count;
    ANTLR3_UINT32       k;
    char                name[ MAX_DOTTED_NAME_LENGTH ];
    pANTLR3_BASE_TREE   t;
    ANTLR3_UINT32       type;
    int                 import_called = 0;

    /* NB: if there is a mistake in the code similar to:
     * from import os
     * then the built tree would still have IMPORT_STMT and the WHAT node
     * however will not have the DOTTED_NAME node. This causes one of the
     * following: incorrect attach of what imported (to the previous import)
     * or an exception.
     * To cope with this I first check if a dotted name was there.
     */


    /* There could be many imports in a single import statement */
    for ( k = 0; k < n; ++k )
    {
        /* The children must be a dotted name or what exported */
        t = vectorGet( tree->children, k );
        type = getType( t );

        if ( type == DOTTED_NAME )
        {
            int                     length;
            pANTLR3_COMMON_TOKEN    token = getDottedName( t, name, &length );
            if ( token->start != 0 )
            {
                callOnImport( callbacks->onImport, name, length, token->line,
                              token->charPosition + 1, /* Make it 1-based */
                              (char *)(token->start) - (char *)token->input->data );
                import_called = 1;
            }
        }
        else if ( type == WHAT && import_called != 0 )
        {
            processWhat( t, callbacks );
        }
        else if ( type == AS && import_called != 0 )
        {
            pANTLR3_BASE_TREE   asChild = vectorGet( t->children, 0 );
            pANTLR3_STRING      s = asChild->toString( asChild );

            callOnAs( callbacks->onAs, (const char *)(s->chars), s->len );
        }
    }
    return;
}


static const char *  processArguments( pANTLR3_BASE_TREE    tree,
                                       PyObject *           onArg )
{
    const char *    firstArgument = NULL;   /* For non-static class members only,
                                               so it cannot be * or ** */

    ANTLR3_UINT32       i;
    ANTLR3_UINT32       n = tree->children->count;
    pANTLR3_BASE_TREE   arg;
    pANTLR3_STRING      s;
    char                augName[ MAX_DOTTED_NAME_LENGTH ];

    for ( i = 0; i < n; ++i )
    {
        arg = vectorGet( tree->children, i );
        s = arg->toString( arg );
        switch ( getType( arg ) )
        {
            case NAME_ARG:
                {
                    callOnArg( onArg, (const char *)(s->chars), s->len );
                    if ( i == 0 )
                        firstArgument = (const char *)(s->chars);
                }
                break;
            case STAR_ARG:
                {
                    augName[0] = '*';
                    memcpy( augName + 1, s->chars, s->len );
                    callOnArg( onArg, augName, s->len + 1 );
                }
                break;
            case DBL_STAR_ARG:
                {
                    augName[0] = '*';
                    augName[1] = '*';
                    memcpy( augName + 2, s->chars, s->len );
                    callOnArg( onArg, augName, s->len + 2 );
                }
                break;
        }
    }
    return firstArgument;
}


static int processDecor( pANTLR3_BASE_TREE            tree,
                         struct instanceCallbacks *   callbacks )
{
    int                     isStaticMethod = 0;
    char                    name[ MAX_DOTTED_NAME_LENGTH ];     /* decor name */
    int                     length;
    pANTLR3_COMMON_TOKEN    token = getDottedName( vectorGet( tree->children, 0 ),
                                                   name, & length );
    if ( token->start != 0 )
    {
        callOnDecorator( callbacks->onDecorator,
                         name, length,
                         token->line,
                         token->charPosition + 1, /* Make it 1-based */
                         (char *)token->start - (char *)token->input->data );
    }
    if ( strcmp( name, "staticmethod" ) == 0 )
    {
        isStaticMethod = 1;
    }

    /* decor arguments */
    if ( tree->children->count > 1 )
    {
        /* There are arguments - process the ARGUMENTS node*/
        processArguments( vectorGet( tree->children, 1 ),
                          callbacks->onDecoratorArgument );
    }

    return isStaticMethod;
}


static void  processClassDefinition( pANTLR3_BASE_TREE            tree,
                                     struct instanceCallbacks *   callbacks,
                                     int                          objectsLevel,
                                     enum Scope                   scope,
                                     int                          entryLevel )
{
    pANTLR3_BASE_TREE       nameChild = vectorGet( tree->children, 0 );
    ANTLR3_UINT32           n = tree->children->count;
    ANTLR3_UINT32           k;
    pANTLR3_COMMON_TOKEN    token = getToken( nameChild );
    pANTLR3_STRING          s;
    pANTLR3_BASE_TREE       t;

    /*
     * user1 field is used for line and charPosition of the 'def' keyword.
     * user2 field is used for line and charPosition of the ':' character.
     */

    ++objectsLevel;
    callOnClass( callbacks->onClass,
                 (const char *)(token->start),
                 (char *)token->stop - (char *)token->start + 1,
                 /* Function name line and pos */
                 token->line,
                 token->charPosition + 1,         /* To make it 1-based */
                 (char *)token->start - (char *)token->input->data,
                 /* Keyword 'def' line and pos */
                 token->user1 >> 16,
                 (token->user1 & 0xFFFF) + 1,     /* To make it 1-based */
                 /* ':' line and pos */
                 token->user2 >> 16,
                 (token->user2 & 0xFFFF) + 1,     /* To make it 1-based */
                 objectsLevel );

    for ( k = 1; k < n; ++k )
    {
        t = vectorGet( tree->children, k );
        switch ( getType( t ) )
        {
            case DECOR:
                processDecor( t, callbacks );
                continue;
            case CLASS_INHERITANCE:
                {
                    ANTLR3_UINT32       n = t->children->count;
                    ANTLR3_UINT32       k;
                    pANTLR3_BASE_TREE   base;
                    for ( k = 0; k < n; ++k )
                    {
                        base = vectorGet( t->children, k );
                        s = base->toString( base );
                        callOnBaseClass( callbacks->onBaseClass,
                                         (const char *)(s->chars), s->len );
                    }
                }
                continue;
            case BODY:
                checkForDocstring( vectorGet( t->children, 0 ), callbacks );
                walk( t, callbacks, objectsLevel, CLASS_SCOPE, NULL, entryLevel );
                return;     /* Body child is the last */
        }
    }
    return;
}


static void  processFuncDefinition( pANTLR3_BASE_TREE            tree,
                                    struct instanceCallbacks *   callbacks,
                                    int                          objectsLevel,
                                    enum Scope                   scope,
                                    int                          entryLevel )
{
    pANTLR3_BASE_TREE       nameChild = vectorGet( tree->children, 0 );
    ANTLR3_UINT32           n = tree->children->count;
    ANTLR3_UINT32           k;
    int                     isStaticMethod = 0;
    const char *            firstArgumentName = NULL; /* for class methods only */
    pANTLR3_COMMON_TOKEN    token = getToken( nameChild );


    /*
     * user1 field is used for line and charPosition of the 'def' keyword.
     * user2 field is used for line and charPosition of the ':' character.
     */

    ++objectsLevel;
    callOnFunction( callbacks->onFunction,
                    (const char *)(token->start),
                    (char *)token->stop - (char *)token->start + 1,
                    /* Function name line and pos */
                    token->line,
                    token->charPosition + 1,         /* To make it 1-based */
                    (char *)token->start - (char *)token->input->data,
                    /* Keyword 'def' line and pos */
                    token->user1 >> 16,
                    (token->user1 & 0xFFFF) + 1,     /* To make it 1-based */
                    /* ':' line and pos */
                    token->user2 >> 16,
                    (token->user2 & 0xFFFF) + 1,     /* To make it 1-based */
                    objectsLevel );

    for ( k = 1; k < n; ++k )
    {
        pANTLR3_BASE_TREE   t = vectorGet( tree->children, k );
        switch ( getType( t ) )
        {
            case DECOR:
                isStaticMethod += processDecor( t, callbacks );
                continue;
            case ARGUMENTS:
                firstArgumentName = processArguments( t, callbacks->onArgument );
                continue;
            case BODY:
                checkForDocstring( vectorGet( t->children, 0 ), callbacks );
                {
                    enum Scope  newScope = FUNCTION_SCOPE; /* Avoid the compiler complains */
                    switch ( scope )
                    {
                        case GLOBAL_SCOPE:
                        case FUNCTION_SCOPE:
                        case CLASS_METHOD_SCOPE:
                        case CLASS_STATIC_METHOD_SCOPE:
                            newScope = FUNCTION_SCOPE;
                            break;
                        case CLASS_SCOPE:
                            /* It could be a static method if there is
                             * the '@staticmethod' decorator */
                            if ( isStaticMethod != 0 ) newScope = CLASS_STATIC_METHOD_SCOPE;
                            else                       newScope = CLASS_METHOD_SCOPE;
                            break;
                    }
                    walk( t, callbacks, objectsLevel, newScope,
                          firstArgumentName, entryLevel );
                }
                return;     /* Body child is the last */
        }
    }
    return;
}

static void processAssign( pANTLR3_BASE_TREE   tree,
                           PyObject *          onVariable,
                           int                 objectsLevel )
{
    ANTLR3_UINT32           i;
    ANTLR3_UINT32           n;
    pANTLR3_STRING          s;
    pANTLR3_BASE_TREE       child;
    pANTLR3_COMMON_TOKEN    token;


    if ( tree->children->count == 0 )
        return;

    /* Step to the LHS part */
    tree = vectorGet( tree->children, 0 );

    /* iterate over the LHS names */
    n = tree->children->count;
    for ( i = 0; i < n; ++i )
    {
        child = vectorGet( tree->children, i );
        if ( getType( child ) == HEAD_NAME )
        {
            if ( i == (n-1) )
            {
                child = vectorGet( child->children, 0 );
                token = getToken( child );
                s = child->toString( child );

                callOnVariable( onVariable, (const char *)(s->chars), s->len,
                                token->line,
                                token->charPosition + 1, /* Make it 1-based */
                                (char *)token->start - (char *)token->input->data,
                                objectsLevel );
                return;
            }

            {
                /* Not last child - check the next */
                pANTLR3_BASE_TREE   nextChild = vectorGet( tree->children, i + 1 );
                if ( getType( nextChild ) == HEAD_NAME )
                {
                    child = vectorGet( child->children, 0 );
                    token = getToken( child );
                    s = child->toString( child );

                    callOnVariable( onVariable, (const char *)(s->chars), s->len,
                                    token->line,
                                    token->charPosition + 1, /* Make it 1-based */
                                    (char *)token->start - (char *)token->input->data,
                                    objectsLevel );
                }
            }
        }
    }
    return;
}

static void processInstanceMember( pANTLR3_BASE_TREE           tree,
                                   struct instanceCallbacks *  callbacks,
                                   const char *                firstArgName,
                                   int                         objectsLevel )
{
    ANTLR3_UINT32           i;
    ANTLR3_UINT32           n;
    pANTLR3_COMMON_TOKEN    token;
    pANTLR3_BASE_TREE       lookAhead;
    pANTLR3_STRING          s;


    if ( firstArgName == NULL )         return;
    if ( tree->children->count == 0 )   return;

    /* Step to the LHS part */
    tree = vectorGet( tree->children, 0 );

    /* iterate over the LHS names */
    n = tree->children->count;

    for ( i = 0; i < n; ++i )
    {
        pANTLR3_BASE_TREE   child = vectorGet( tree->children, i );
        pANTLR3_BASE_TREE   nameNode;

        if ( getType( child ) != HEAD_NAME )
            continue;

        /* Check that the beginning of the name matches the method first
         * argument */
        nameNode = vectorGet( child->children, 0 );
        if ( strcmp( firstArgName,
                     (const char *)nameNode->toString( nameNode )->chars ) != 0 )
            continue;

        /* OK, the beginning matches. Check that it has the trailing part */
        if ( i == (n-1) )
            continue;

        /* Do the step */
        child = vectorGet( tree->children, i+1 );
        if ( getType( child ) != TRAILER_NAME )
            continue;

        /* Check that there is no node after the trailer or the next one is the
         * HEAD_NAME */
        if ( (i+1) == (n-1) )
        {
            /* There is no more. Do the callback. */
            child = vectorGet( child->children, 0 );
            token = getToken( child );
            s = child->toString( child );
            callOnInstanceAttribute( callbacks->onInstanceAttribute,
                                     (const char *)(s->chars), s->len,
                                     token->line,
                                     token->charPosition + 1, /* Make it 1-based */
                                     (char *)token->start - (char *)token->input->data,
                                     objectsLevel );
            return;
        }

        ++i;
        lookAhead = vectorGet( tree->children, i+1 );
        if ( getType( lookAhead ) != HEAD_NAME )
            continue;

        /* Here it is, we should get it */
        child = vectorGet( child->children, 0 );
        token = getToken( child );
        s = child->toString( child );
        callOnInstanceAttribute( callbacks->onInstanceAttribute,
                                 (const char *)(s->chars), s->len,
                                 token->line,
                                 token->charPosition + 1, /* Make it 1-based */
                                 (char *)token->start - (char *)token->input->data,
                                 objectsLevel );
    }
    return;
}


void walk( pANTLR3_BASE_TREE            tree,
           struct instanceCallbacks *   callbacks,
           int                          objectsLevel,
           enum Scope                   scope,
           const char *                 firstArgName,
           int                          entryLevel )
{
    ++entryLevel;   // For module docstring only

    switch ( getType( tree ) )
    {
        case IMPORT_STMT:
            processImport( tree, callbacks );
            return;
        case CLASS_DEF:
            processClassDefinition( tree, callbacks,
                                    objectsLevel, scope, entryLevel );
            return;
        case FUNC_DEF:
            processFuncDefinition( tree, callbacks,
                                   objectsLevel, scope, entryLevel );
            return;
        case ASSIGN:
            if ( scope == GLOBAL_SCOPE )
                processAssign( tree, callbacks->onGlobal, objectsLevel );
            if ( scope == CLASS_SCOPE )
                processAssign( tree, callbacks->onClassAttribute, objectsLevel );
            if ( scope == CLASS_METHOD_SCOPE )
                processInstanceMember( tree, callbacks, firstArgName, objectsLevel );

            /* The other scopes are not interesting */
            return;

        default:
            break;
    }

    // Walk the children
    if ( tree->children != NULL )
    {
        ANTLR3_UINT32       i;
        ANTLR3_UINT32       n = tree->children->count;
        pANTLR3_BASE_TREE   t;

        for ( i = 0; i < n; i++ )
        {
            t = vectorGet( tree->children, i );
            if ( (entryLevel == 1) && (i == 0) )
            {
                /* This could be a module docstring */
                checkForDocstring( t, callbacks );
            }
            walk( t, callbacks, objectsLevel,
                  scope, firstArgName, entryLevel );
        }
    }
    return;
}


/* Note: the lineNumber and lineStart cannot be calculated
 *       in searchForCoding(...) from ctx. It seems to me that
 *       the ctx has been updated at the time searchForCoding(...)
 *       is called. So these values are initialized before the rule
 *       and passed to searchForEncoding(...)
 */
void  searchForCoding( ppythonbriefLexer  ctx,
                       char *             lineStart,
                       ANTLR3_UINT32      lineNumber )
{
    if ( ctx->onEncoding != NULL )
    {
        /* Analysis is disabled after first found encoding */

        /* There were two version of this functions before which used regexps.
         * The first version used this regexp: coding[=:]\s*([-\w.]+)
         * I could not make it working at all.
         * The second version used this: coding[=:]\\s*
         * It worked fine on Linux however introduced problems on Windows and
         * CygWin. So it was decided to get rid of regexps completely and to use
         * dumb plain string search. A side effect of it is reducing dependencies
         * in general.
         */

        /* Find the end of the line and put \0 there */
        char *      endofline = lineStart;
        char        current;
        char *      begin;

        for ( ; ; ++endofline )
        {
            current = *endofline;
            if ( current == '\0' || current == '\n' ||
                 current == '\r' )
                break;
        }

        /* replace the endofline char with '\0' */
        *endofline = '\0';

        begin = strstr( lineStart, "coding" );
        if ( begin != NULL )
        {
            char *      end;
            char        last;

            /* The beginning has been found. Check the first character after. */
            begin += 6;     /* len( 'coding' ) */
            if ( *begin == ':' || *begin == '=' )
                ++begin;
            while ( isspace( *begin ) )
                ++begin;

            for ( end = begin; ; ++end )
            {
                last = *end;
                if ( last == '\0' || isspace( last ) )
                    break;
            }

            *end = '\0';
            callOnEncoding( (PyObject*)ctx->onEncoding, begin, lineNumber,
                            begin - lineStart + 1, /* Make it 1-based */
                            begin - (char *)ctx->pLexer->input->data );
            *end = last;
            ctx->onEncoding = NULL;
        }

        /* revert back the last line symbol */
        *endofline = current;
    }
    return;
}


static int      unknownError = 0;
static int      errorCount = 0;

// The code is taken from the libantlr3 and modified to collect the message
// in a buffer and then call the python onError callback
void onError( pANTLR3_BASE_RECOGNIZER    recognizer,
              pANTLR3_UINT8 *            tokenNames )
{
    pANTLR3_PARSER          parser;
    pANTLR3_TREE_PARSER     tparser;
    pANTLR3_INT_STREAM      is;
    pANTLR3_STRING          ttext;
    pANTLR3_STRING          ftext;
    pANTLR3_EXCEPTION       ex;
    pANTLR3_COMMON_TOKEN    theToken;
    pANTLR3_BASE_TREE       theBaseTree;
    pANTLR3_COMMON_TREE     theCommonTree;

    size_t                  buffer_size = 4096;
    char                    buffer[ 4096 ];
    size_t                  length = 0;

    // Retrieve some info for easy reading.
    ex    = recognizer->state->exception;
    ttext = NULL;

    errorCount += 1;

    // See if there is a 'filename' we can use
    if ( ex->streamName == NULL )
    {
        if ( ((pANTLR3_COMMON_TOKEN)(ex->token))->type == ANTLR3_TOKEN_EOF )
        {
            length = snprintf( buffer, buffer_size, "-end of input-(" );
        }
        else
        {
            length = snprintf( buffer, buffer_size, "-unknown source-(" );
        }
    }
    else
    {
        ftext = ex->streamName->to8( ex->streamName );
        length = snprintf( buffer, buffer_size, "%s(", ftext->chars );
    }

    // Next comes the line number

    if ( length < buffer_size )
        length += snprintf( buffer + length, buffer_size - length, "%d) ",
                            recognizer->state->exception->line );
    if ( length < buffer_size )
        length += snprintf( buffer + length, buffer_size - length, " : error %d : %s",
                            recognizer->state->exception->type,
                            (pANTLR3_UINT8) (recognizer->state->exception->message) );


    // How we determine the next piece is dependent on which thing raised the
    // error.
    switch ( recognizer->type )
    {
    case ANTLR3_TYPE_PARSER:

        // Prepare the knowledge we know we have
        parser   = (pANTLR3_PARSER) (recognizer->super);
        tparser  = NULL;
        is       = parser->tstream->istream;
        theToken = (pANTLR3_COMMON_TOKEN)(recognizer->state->exception->token);
        ttext    = theToken->toString( theToken );

        if ( length < buffer_size )
            length += snprintf( buffer + length, buffer_size - length,
                                ", at offset %d",
                                recognizer->state->exception->charPositionInLine );
        if  ( theToken != NULL )
        {
            if ( theToken->type == ANTLR3_TOKEN_EOF )
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length, ", at <EOF>" );
            }
            else
            {
                // Guard against null text in a token
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "\n    near %s\n    ",
                                        ttext == NULL ? (pANTLR3_UINT8)"<no text for the token>" : ttext->chars );
            }
        }
        break;

    case ANTLR3_TYPE_TREE_PARSER:

        tparser     = (pANTLR3_TREE_PARSER) (recognizer->super);
        parser      = NULL;
        is          = tparser->ctnstream->tnstream->istream;
        theBaseTree = (pANTLR3_BASE_TREE)(recognizer->state->exception->token);
        ttext       = theBaseTree->toStringTree( theBaseTree );

        if  (theBaseTree != NULL)
        {
            theCommonTree = (pANTLR3_COMMON_TREE) theBaseTree->super;

            if ( theCommonTree != NULL )
            {
                theToken = (pANTLR3_COMMON_TOKEN) theBaseTree->getToken( theBaseTree );
            }
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    ", at offset %d", theBaseTree->getCharPositionInLine( theBaseTree ) );
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    ", near %s", ttext->chars );
        }
        break;

    default:

        if ( length < buffer_size )
            length += snprintf( buffer + length, buffer_size - length,
                                "Base recognizer function displayRecognitionError called by unknown parser type - provide override for this function\n" );
        if ( recognizer->userData != NULL )
        {
            callOnError( (PyObject *)(recognizer->userData), buffer );
        }
        else
        {
            unknownError += 1;
        }
        return;
    }

    // Although this function should generally be provided by the implementation, this one
    // should be as helpful as possible for grammar developers and serve as an example
    // of what you can do with each exception type. In general, when you make up your
    // 'real' handler, you should debug the routine with all possible errors you expect
    // which will then let you be as specific as possible about all circumstances.
    //
    // Note that in the general case, errors thrown by tree parsers indicate a problem
    // with the output of the parser or with the tree grammar itself. The job of the parser
    // is to produce a perfect (in traversal terms) syntactically correct tree, so errors
    // at that stage should really be semantic errors that your own code determines and handles
    // in whatever way is appropriate.
    //
    switch ( ex->type )
    {
    case ANTLR3_UNWANTED_TOKEN_EXCEPTION:

        // Indicates that the recognizer was fed a token which seesm to be
        // spurious input. We can detect this when the token that follows
        // this unwanted token would normally be part of the syntactically
        // correct stream. Then we can see that the token we are looking at
        // is just something that should not be there and throw this exception.
        if ( tokenNames == NULL )
        {
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    " : Extraneous input..." );
        }
        else
        {
            if ( ex->expecting == ANTLR3_TOKEN_EOF )
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        " : Extraneous input - expected <EOF>\n" );
            }
            else
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        " : Extraneous input - expected %s ...\n", tokenNames[ ex->expecting ] );
            }
        }
        break;

    case ANTLR3_MISSING_TOKEN_EXCEPTION:

        // Indicates that the recognizer detected that the token we just
        // hit would be valid syntactically if preceeded by a particular 
        // token. Perhaps a missing ';' at line end or a missing ',' in an
        // expression list, and such like.
        if ( tokenNames == NULL )
        {
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    " : Missing token (%d)...\n", ex->expecting );
        }
        else
        {
            if ( ex->expecting == ANTLR3_TOKEN_EOF )
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        " : Missing <EOF>\n" );
            }
            else
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        " : Missing %s \n", tokenNames[ ex->expecting ] );
            }
        }
        break;

    case ANTLR3_RECOGNITION_EXCEPTION:

        // Indicates that the recognizer received a token
        // in the input that was not predicted. This is the basic exception type 
        // from which all others are derived. So we assume it was a syntax error.
        // You may get this if there are not more tokens and more are needed
        // to complete a parse for instance.
        //
        if ( length < buffer_size )
            length += snprintf( buffer + length, buffer_size - length,
                                " : syntax error...\n" );
        break;

    case ANTLR3_MISMATCHED_TOKEN_EXCEPTION:

        // We were expecting to see one thing and got another. This is the
        // most common error if we coudl not detect a missing or unwanted token.
        // Here you can spend your efforts to
        // derive more useful error messages based on the expected
        // token set and the last token and so on. The error following
        // bitmaps do a good job of reducing the set that we were looking
        // for down to something small. Knowing what you are parsing may be
        // able to allow you to be even more specific about an error.
        if ( tokenNames == NULL )
        {
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    " : syntax error...\n" );
        }
        else
        {
            if ( ex->expecting == ANTLR3_TOKEN_EOF )
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        " : expected <EOF>\n" );
            }
            else
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        " : expected %s ...\n", tokenNames[ ex->expecting ] );
            }
        }
        break;

    case ANTLR3_NO_VIABLE_ALT_EXCEPTION:

        // We could not pick any alt decision from the input given
        // so god knows what happened - however when you examine your grammar,
        // you should. It means that at the point where the current token occurred
        // that the DFA indicates nowhere to go from here.
        if ( length < buffer_size )
            length += snprintf( buffer + length, buffer_size - length,
                                " : cannot match to any predicted input...\n" );

        break;

    case ANTLR3_MISMATCHED_SET_EXCEPTION:

        {
            ANTLR3_UINT32   count;
            ANTLR3_UINT32   bit;
            ANTLR3_UINT32   size;
            ANTLR3_UINT32   numbits;
            pANTLR3_BITSET  errBits;

            // This means we were able to deal with one of a set of
            // possible tokens at this point, but we did not see any
            // member of that set.
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    " : unexpected input...\n  expected one of : " );

            // What tokens could we have accepted at this point in the
            // parse?
            count   = 0;
            errBits = antlr3BitsetLoad( ex->expectingSet );
            numbits = errBits->numBits( errBits );
            size    = errBits->size( errBits );

            if  (size > 0)
            {
                // However many tokens we could have dealt with here, it is usually
                // not useful to print ALL of the set here. I arbitrarily chose 8
                // here, but you should do whatever makes sense for you of course.
                // No token number 0, so look for bit 1 and on.
                for ( bit = 1; bit < numbits && count < 8 && count < size; bit++ )
                {
                    // TODO: This doesn't look right - should be asking if the bit is set!!
                    if ( tokenNames[ bit ] )
                    {
                        if ( length < buffer_size )
                            length += snprintf( buffer + length, buffer_size - length,
                                                "%s%s", count > 0 ? ", " : "", tokenNames[ bit ] );
                        count++;
                    }
                }
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "\n" );
            }
            else
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "Actually dude, we didn't seem to be expecting anything here, or at least\n" );
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "I could not work out what I was expecting, like so many of us these days!\n" );
            }
        }
        break;

    case ANTLR3_EARLY_EXIT_EXCEPTION:

        // We entered a loop requiring a number of token sequences
        // but found a token that ended that sequence earlier than
        // we should have done.
        if ( length < buffer_size )
            length += snprintf( buffer + length, buffer_size - length,
                                " : missing elements...\n" );
        break;

    default:

        // We don't handle any other exceptions here, but you can
        // if you wish. If we get an exception that hits this point
        // then we are just going to report what we know about the
        // token.
        if ( length < buffer_size )
            length += snprintf( buffer + length, buffer_size - length,
                                " : syntax not recognized...\n" );
        break;
    }

    if ( recognizer->userData != NULL )
    {
        callOnError( (PyObject *)(recognizer->userData), buffer );
    }
    else
    {
        unknownError += 1;
    }

    // Here you have the token that was in error which if this is
    // the standard implementation will tell you the line and offset
    // and also record the address of the start of the line in the
    // input stream. You could therefore print the source line and so on.
    // Generally though, I would expect that your lexer/parser will keep
    // its own map of lines and source pointers or whatever as there
    // are a lot of specific things you need to know about the input
    // to do something like that.
    // Here is where you do it though :-).
}


// The function is taken from the libantlr3 and modified to collect the message
// in a buffer and then call the python onLexerError callback.
// Original function: antlr3lexer.c:407 displayRecognitionError(...)
void
onLexerError( pANTLR3_BASE_RECOGNIZER   recognizer,
              pANTLR3_UINT8 *           tokenNames)
{
    pANTLR3_LEXER           lexer;
    pANTLR3_EXCEPTION       ex;
    pANTLR3_STRING          ftext;

    size_t                  buffer_size = 4096;
    char                    buffer[ 4096 ];
    size_t                  length = 0;

    errorCount += 1;

    lexer = (pANTLR3_LEXER)(recognizer->super);
    ex    = lexer->rec->state->exception;

    // See if there is a 'filename' we can use
    //
    if (ex->name == NULL)
    {
        length = snprintf( buffer, buffer_size, "-unknown source-(" );
    }
    else
    {
        ftext = ex->streamName->to8(ex->streamName);
        length = snprintf( buffer, buffer_size, "%s(", ftext->chars );
    }

    if ( length < buffer_size )
        length += snprintf( buffer + length, buffer_size - length, "%d) ",
                            recognizer->state->exception->line);
    if ( length < buffer_size )
        length += snprintf( buffer + length, buffer_size - length,
                            ": lexer error %d :\n\t%s at offset %d, ",
                            ex->type,
                            (pANTLR3_UINT8)(ex->message),
                            ex->charPositionInLine + 1 );
    {
        ANTLR3_INT32    width;

        width = ANTLR3_UINT32_CAST(( (pANTLR3_UINT8)(lexer->input->data) +
                                     (lexer->input->size(lexer->input) )) -
                                     (pANTLR3_UINT8)(ex->index));

        if (width >= 1)
        {
            if (isprint(ex->c))
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "near '%c' :\n", ex->c );
            }
            else
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "near char(%#02X) :\n", (ANTLR3_UINT8)(ex->c) );
            }
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    "\t%.*s\n", width > 20 ? 20 : width ,((pANTLR3_UINT8)ex->index) );
        }
        else
        {
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    "(end of input).\n\t This indicates a poorly specified lexer RULE\n\t or unterminated input element such as: \"STRING[\"]\n");
            if ( length < buffer_size )
                length += snprintf( buffer + length, buffer_size - length,
                                    "\t The lexer was matching from line %d, offset %d, which\n\t ",
                                   (ANTLR3_UINT32)(lexer->rec->state->tokenStartLine),
                                   (ANTLR3_UINT32)(lexer->rec->state->tokenStartCharPositionInLine) );
            width = ANTLR3_UINT32_CAST(((pANTLR3_UINT8)(lexer->input->data)+(lexer->input->size(lexer->input))) - (pANTLR3_UINT8)(lexer->rec->state->tokenStartCharIndex));

            if (width >= 1)
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "looks like this:\n\t\t%.*s\n", width > 20 ? 20 : width ,(pANTLR3_UINT8)(lexer->rec->state->tokenStartCharIndex));
            }
            else
            {
                if ( length < buffer_size )
                    length += snprintf( buffer + length, buffer_size - length,
                                        "is also the end of the line, so you must check your lexer rules\n");
            }
        }
    }

    if ( recognizer->userData != NULL )
    {
        callOnError( (PyObject *)(recognizer->userData), buffer );
    }
}


static PyObject *
parse_input( pANTLR3_INPUT_STREAM           input,
             struct instanceCallbacks *     callbacks )
{
    ppythonbriefLexer               lxr;
    pANTLR3_COMMON_TOKEN_STREAM     tstream;
    ppythonbriefParser              psr;
    pANTLR3_BASE_TREE               tree;

    unknownError = 0;
    errorCount = 0;
    if ( input == NULL )
    {
        PyErr_SetString( PyExc_RuntimeError, "Cannot open file/memory buffer" );
        return NULL;
    }

    lxr = pythonbriefLexerNew( input );
    if ( lxr == NULL )
    {
        input->close( input );
        PyErr_SetString( PyExc_RuntimeError, "Cannot create lexer" );
        return NULL;
    }

    tstream = antlr3CommonTokenStreamSourceNew( ANTLR3_SIZE_HINT,
                                                TOKENSOURCE( lxr ) );
    if ( tstream == NULL )
    {
        input->close( input );
        lxr->free( lxr );
        PyErr_SetString( PyExc_RuntimeError, "Cannot create token stream" );
        return NULL;
    }
    tstream->discardOffChannelToks( tstream, ANTLR3_TRUE );

    // Create parser
    psr = pythonbriefParserNew( tstream );
    if ( psr == NULL )
    {
        input->close( input );
        tstream->free( tstream );
        lxr->free( lxr );
        PyErr_SetString( PyExc_RuntimeError, "Cannot create parser" );
        return NULL;
    }

    /* Memorize callbacks for coding and errors */
    lxr->onEncoding = callbacks->onEncoding;

    lxr->pLexer->rec->userData = callbacks->onLexerError;
    lxr->pLexer->rec->displayRecognitionError = onLexerError;
    psr->pParser->rec->userData = callbacks->onError;
    psr->pParser->rec->displayRecognitionError = onError;

    /* Bug in the run-time library */
    lxr->pLexer->input->charPositionInLine = 0;


    /* Parse... */
    tree = psr->file_input( psr ).tree;

    if ( tree == NULL )
    {
        input->close( input );
        tstream->free( tstream );
        lxr->free( lxr );
        PyErr_SetString( PyExc_RuntimeError, "Cannot parse python code" );
        return NULL;
    }

    /* Walk the tree and populate the python structures */
    walk( tree, callbacks, -1, GLOBAL_SCOPE, NULL, 0 );

    /* Check that the parser consumed all the tokens */
    if ( errorCount == 0 &&
         tstream->p != tstream->tokens->count )
    {
        /* The parser stopped somewhere in a middle */
        char                    message[ 4096 ];
        pANTLR3_COMMON_TOKEN    token = (pANTLR3_COMMON_TOKEN)(vectorGet( tstream->tokens,
                                                                          tstream->p ));

        sprintf( message, "Cannot match to any predicted input near line %d",
                          token->line );
        callOnError( callbacks->onLexerError, message );
    }

    /* cleanup */
    psr->free( psr );
    tstream->free( tstream );
    lxr->free( lxr );
    input->close( input );

    if ( unknownError != 0 )
    {
        // This is a fallback which should not happened
        callOnError( callbacks->onError, "Unknown error" );
        unknownError = 0;
    }

    Py_INCREF( Py_None );
    return Py_None;
}


/* Parses the given file */
static char py_modinfo_from_file_doc[] = "Get brief module info from a file";
static PyObject *
py_modinfo_from_file( PyObject *  self,     /* unused */
                      PyObject *  args )
{
    PyObject *                  callbackClass = NULL;
    char *                      fileName;
    struct instanceCallbacks    callbacks;
    pANTLR3_INPUT_STREAM        input;
    PyObject *                  retValue;

    /* Parse the passed arguments */
    if ( ! PyArg_ParseTuple( args, "Os", & callbackClass, & fileName ) )
    {
        PyErr_SetString( PyExc_TypeError, "Incorrect arguments. "
                                          "Expected: callback class "
                                          "instance and file name" );
        return NULL;
    }

    /* Check the passed argument */
    if ( ! fileName )
    {
        PyErr_SetString( PyExc_TypeError, "Incorrect file name" );
        return NULL;
    }
    if ( ! callbackClass )
    {
        PyErr_SetString( PyExc_TypeError, "Invalid callback class argument" );
        return NULL;
    }
    /*
       Ommit the check below: the old style classes worked fine with
       PyInstance_Check(...). With new style classes (i.e. derived from
       'object') none of the checks PyInstance_Check(...) or PyType_Check(...)
       is working. It is though more or less ok not to have the check at all
       because the member functions are retrieved with checks anyway.
       if ( ! PyInstance_Check( callbackClass ) )
       if ( ! PyType_Check( callbackClass ) )
       {
           PyErr_SetString( PyExc_TypeError, "Incorrect callback class instance" );
           return NULL;
       }
    */

    /* Get pointers to the members */
    if ( getInstanceCallbacks( callbackClass, & callbacks ) != 0 )
    {
        clearCallbacks( & callbacks );
        return NULL;
    }

    /* Start the parser business */
    input = antlr3AsciiFileStreamNew( (pANTLR3_UINT8) fileName );

    /* Dirty hack:
     * it's a problem if a comment is the last one in the file and it does not
     * have EOL at the end. It's easier to add EOL here (if EOL is not the last
     * character) than to change the grammar.
     * The run-time library reserves one byte in the patched version for EOL if
     * needed.
     */
    if ( input != NULL )
    {
        if ( input->sizeBuf > 0 )
        {
            if ( ((char*)(input->data))[ input->sizeBuf - 1 ] != '\n' )
            {
                ((char*)(input->data))[ input->sizeBuf ] = '\n';
                input->sizeBuf += 1;
            }
        }
    }

    /* There is no need to revert the changes because the input is closed */
    retValue = parse_input( input, & callbacks );
    clearCallbacks( & callbacks );
    return retValue;
}


/* Parses the given code */
static char py_modinfo_from_mem_doc[] = "Get brief module info from memory";
static PyObject *
py_modinfo_from_mem( PyObject *  self,      /* unused */
                     PyObject *  args )
{
    PyObject *                  callbackClass;
    char *                      content;
    struct instanceCallbacks    callbacks;
    pANTLR3_INPUT_STREAM        input;
    int                         eolAddedAt;
    PyObject *                  retValue;


    /* Parse the passed arguments */
    if ( ! PyArg_ParseTuple( args, "Os", & callbackClass, & content ) )
    {
        PyErr_SetString( PyExc_TypeError, "Incorrect arguments. "
                                          "Expected: callback class "
                                          "instance and buffer with python code" );
        return NULL;
    }

    /* Check the passed argument */
    if ( ! content )
    {
        PyErr_SetString( PyExc_TypeError, "Incorrect memory buffer" );
        return NULL;
    }
    if ( ! callbackClass )
    {
        PyErr_SetString( PyExc_TypeError, "Invalid callback class argument" );
        return NULL;
    }
    /*
       Ommit the check below: the old style classes worked fine with
       PyInstance_Check(...). With new style classes (i.e. derived from
       'object') none of the checks PyInstance_Check(...) or PyType_Check(...)
       is working. It is though more or less ok not to have the check at all
       because the member functions are retrieved with checks anyway.
       if ( ! PyInstance_Check( callbackClass ) )
       if ( ! PyType_Check( callbackClass ) )
       {
           PyErr_SetString( PyExc_TypeError, "Incorrect callback class instance" );
           return NULL;
       }
    */

    /* Get pointers to the members */
    if ( getInstanceCallbacks( callbackClass, & callbacks ) != 0 )
    {
        clearCallbacks( & callbacks );
        return NULL;
    }

    /* Start the parser business */
    input = antlr3NewAsciiStringInPlaceStream( (pANTLR3_UINT8) content,
                                               strlen( content ), NULL );

    /* Dirty hack:
     * it's a problem if a comment is the last one in the file and it does not
     * have EOL at the end. It's easier to add EOL here (if EOL is not the last
     * character) than to change the grammar.
     * The \0 byte is used for temporary injection of EOL.
     */
    eolAddedAt = 0;
    if ( input != NULL )
    {
        if ( input->sizeBuf > 0 )
        {
            if ( ((char*)(input->data))[ input->sizeBuf - 1 ] != '\n' )
            {
                eolAddedAt = input->sizeBuf;
                ((char*)(input->data))[ eolAddedAt ] = '\n';
                input->sizeBuf += 1;
            }
        }
    }

    retValue = parse_input( input, & callbacks );
    clearCallbacks( & callbacks );

    /* Revert the hack changes back if needed.
     * Input is closed here so the original content pointer is used.
     */
    if ( eolAddedAt != 0 )
    {
        content[ eolAddedAt ] = 0;
    }
    return retValue;
}



static PyMethodDef _cdm_py_parser_methods[] =
{
    { "getBriefModuleInfoFromFile",   py_modinfo_from_file,      METH_VARARGS, py_modinfo_from_file_doc },
    { "getBriefModuleInfoFromMemory", py_modinfo_from_mem,       METH_VARARGS, py_modinfo_from_mem_doc },
    { NULL, NULL, 0, NULL }
};


#if PY_MAJOR_VERSION < 3
    /* Python 2 initialization */
    void init_cdmpyparser( void )
    {
        PyObject *  module = Py_InitModule( "_cdmpyparser", _cdm_py_parser_methods );
        PyModule_AddStringConstant( module, "version", CDM_PY_PARSER_VERSION );
    }
#else
    /* Python 3 initialization */
    static struct PyModuleDef _cdm_py_parser_module =
    {
        PyModuleDef_HEAD_INIT,
        "_cdmpyparser",
        NULL,
        -1,
        _cdm_py_parser_methods
    };

    PyMODINIT_FUNC
    PyInit__cdmpyparser( void )
    {
        PyObject *  module;
        module = PyModule_Create( & _cdm_py_parser_module );
        PyModule_AddStringConstant( module, "version", CDM_PY_PARSER_VERSION );
        return module;
    }
#endif

