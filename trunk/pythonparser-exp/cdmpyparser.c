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


#include <sys/stat.h>

#include <Python.h>
#include <node.h>
#include <grammar.h>
#include <parsetok.h>
#include <graminit.h>
#include <errcode.h>
#include <token.h>

#include <string.h>

#ifndef CDM_PY_PARSER_VERSION
#define CDM_PY_PARSER_VERSION       "trunk"
#endif

#define MAX_DOTTED_NAME_LENGTH      512
#define MAX_ARG_VAL_SIZE            2048
/* I saw some files which have bigger than 32kb docstrings! */
#define MAX_DOCSTRING_SIZE          65535
#define MAX_ERROR_MSG_SIZE          32768


extern grammar      _PyParser_Grammar;  /* From graminit.c */


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
    PyObject *      onArgumentValue;
    PyObject *      onBaseClass;
    PyObject *      onError;
    PyObject *      onLexerError;
};

/* Forward declaration */
void walk( node *                       tree,
           struct instanceCallbacks *   callbacks,
           int                          objectsLevel,
           enum Scope                   scope,
           const char *                 firstArgName,
           int                          entryLevel,
           int *                        lineShifts,
           int                          isStaticMethod );


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
    GET_CALLBACK( onArgumentValue );
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
    FREE_CALLBACK( onArgumentValue );
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
    PyObject *  argName = PyString_FromStringAndSize( name, length );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onArg, argName, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( argName );
    return;
}


static void
callOnArgVal( PyObject *  onArgVal, const char *  value, int  length )
{
    PyObject *  argVal = PyString_FromStringAndSize( value, length );
    PyObject *  ret = PyObject_CallFunctionObjArgs( onArgVal, argVal, NULL );

    if ( ret != NULL )
        Py_DECREF( ret );
    Py_DECREF( argVal );
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


/* Provides the total number of lines in the code */
static int getTotalLines( node *  tree )
{
    if ( tree == NULL )
        return -1;

    if ( tree->n_type != file_input )
        tree = &(tree->n_child[ 0 ]);

    assert( tree->n_type == file_input );

    node *          child;
    int             n = tree->n_nchildren;
    for ( int  k = 0; k < n; ++k )
    {
        child = &(tree->n_child[ k ]);
        if ( child->n_type == ENDMARKER )
            return child->n_lineno;
    }
    return -1;
}



/* Fills the given buffer */
static char *   getDottedName( node *   tree,
                               char *   name,
                               int *    len )
{
    int                     n = tree->n_nchildren;
    int                     partLen;
    node *                  child;
    char *                  first = NULL;

    /* tree must be of 'dotted_name' type */
    assert( tree->n_type == dotted_name );

    for ( int  k = 0; k < n; ++k )
    {
        child = & (tree->n_child[k]);
        if ( child->n_type == NAME )
        {
            partLen = strlen( child->n_str );
            memcpy( name + *len, child->n_str, partLen );
            *len += partLen;
            if ( k == 0 )
                first = child->n_str;
        }
        else
        {
            /* This is DOT */
            assert( child->n_type == DOT );
            name[ *len ] = '.';
            *len += 1;
        }
    }
    name[ *len ] = '\0';
    return first;
}


static node *  findChildOfType( node *  from, int  type )
{
    int         n = from->n_nchildren;
    for ( int  k = 0; k < n; ++k )
        if ( from->n_child[ k ].n_type == type )
            return & (from->n_child[ k ]);
    return NULL;
}


/* Collects the string parts of the test node recursively.  */
/* It is used in:                                           */
/* - the default argument values                            */
/* - class inheritance                                      */
static void  collectTestString( node *  from, char *  buffer, int *  length )
{
    if ( from->n_str != NULL )
    {
        if ( from->n_str[ 0 ] == ')' ||
             from->n_str[ 0 ] == ']' ||
             from->n_str[ 0 ] == '}' )
        {
            buffer[ *length ] = ' ';
            ++(*length);
            buffer[ *length ] = from->n_str[ 0 ];
            ++(*length);
        }
        else if ( from->n_str[ 0 ] == '(' ||
                  from->n_str[ 0 ] == '[' ||
                  from->n_str[ 0 ] == '{' ||
                  from->n_str[ 0 ] == ',' )
        {
            buffer[ *length ] = from->n_str[ 0 ];
            ++(*length);
            buffer[ *length ] = ' ';
            ++(*length);
        }
        else if ( strcmp( from->n_str, "-" ) == 0 ||
                  strcmp( from->n_str, "+" ) == 0 ||
                  strcmp( from->n_str, "/" ) == 0 ||
                  strcmp( from->n_str, "*" ) == 0 ||
                  strcmp( from->n_str, ":" ) == 0 ||
                  strcmp( from->n_str, "**" ) == 0 ||
                  strcmp( from->n_str, "~" ) == 0 ||
                  strcmp( from->n_str, "%" ) == 0 ||
                  strcmp( from->n_str, "//" ) == 0 ||
                  strcmp( from->n_str, "not" ) == 0 ||
                  strcmp( from->n_str, "<" ) == 0 ||
                  strcmp( from->n_str, ">" ) == 0 ||
                  strcmp( from->n_str, "==" ) == 0 ||
                  strcmp( from->n_str, ">=" ) == 0 ||
                  strcmp( from->n_str, "<=" ) == 0 ||
                  strcmp( from->n_str, "<>" ) == 0 ||
                  strcmp( from->n_str, "!=" ) == 0 ||
                  strcmp( from->n_str, "in" ) == 0 ||
                  strcmp( from->n_str, "is" ) == 0 ||
                  strcmp( from->n_str, "|" ) == 0 ||
                  strcmp( from->n_str, "^" ) == 0 ||
                  strcmp( from->n_str, "&" ) == 0 ||
                  strcmp( from->n_str, "<<" ) == 0 ||
                  strcmp( from->n_str, ">>" ) == 0 ||
                  strcmp( from->n_str, "or" ) == 0 ||
                  strcmp( from->n_str, "and" ) == 0 ||
                  strcmp( from->n_str, "if" ) == 0 ||
                  strcmp( from->n_str, "elif" ) == 0 ||
                  strcmp( from->n_str, "else" ) == 0 )
        {
            buffer[ *length ] = ' ';
            ++(*length);
            int     len = strlen( from->n_str );
            memcpy( & ( buffer[ *length ] ), from->n_str, len );
            *length += len;
            buffer[ *length ] = ' ';
            ++(*length);
        }
        else
        {
            int     len = strlen( from->n_str );
            memcpy( & ( buffer[ *length ] ), from->n_str, len );
            *length += len;
        }
    }

    int         n = from->n_nchildren;
    for ( int  k = 0; k < n; ++k )
        collectTestString( & ( from->n_child[ k ] ), buffer, length );
}


/* returns 1 or 3, i.e. the number of quotes used in a string literal part */
static size_t getStringLiteralPrefixLength( node *  tree )
{
    /* tree must be of STRING type */
    assert( tree->n_type == STRING );
    if ( strncmp( tree->n_str, "\"\"\"", 3 ) == 0 )
        return 3;
    if ( strncmp( tree->n_str, "'''", 3 ) == 0 )
        return 3;
    return 1;
}


/* Searches for a certain  node among the first children */
static node *  skipToNode( node *  tree, int nodeType )
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



static void checkForDocstring( node *                       tree,
                               struct instanceCallbacks *   callbacks )
{
    if ( tree == NULL )
        return;

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

        return;
    }

    child = skipToNode( child, atom );
    if ( child == NULL )
        return;

    /* Atom has to have children of the STRING type only */
    char            buffer[ MAX_DOCSTRING_SIZE ];
    int             collected = 0;
    int             charsToSkip;
    int             charsToCopy;
    node *          stringChild;
    n = child->n_nchildren;
    for ( int  k = 0; k < n; ++k )
    {
        stringChild = & ( child->n_child[ k ] );
        if ( stringChild->n_type != STRING )
            return;

        charsToSkip = getStringLiteralPrefixLength( stringChild );
        charsToCopy = strlen( stringChild->n_str ) - 2 * charsToSkip;

        if ( collected + charsToCopy + 1 > MAX_DOCSTRING_SIZE )
        {
            memcpy( buffer + collected,
                    stringChild->n_str + charsToSkip,
                    MAX_DOCSTRING_SIZE - collected - 1 );
            collected = MAX_DOCSTRING_SIZE - 1;
            break;
        }

        memcpy( buffer + collected,
                stringChild->n_str + charsToSkip,
                charsToCopy );
        collected += charsToCopy;
    }

    buffer[ collected ] = 0;
    callOnDocstring( callbacks->onDocstring,
                     buffer, collected, child->n_lineno );
    return;
}


static void  processImport( node *                       tree,
                            struct instanceCallbacks *   callbacks,
                            int *                        lineShifts )
{
    assert( tree->n_type == import_stmt );
    assert( tree->n_nchildren == 1 );

    /* There must be one child of type import_from or import_name */
    tree = & (tree->n_child[ 0 ]);
    if ( tree->n_type == import_from )
    {
        char    name[ MAX_DOTTED_NAME_LENGTH ];
        int     length = 0;
        int     needFlush = 0;
        node *  firstNameNode = NULL;
        int     n = tree->n_nchildren;

        for ( int  k = 0; k < n; ++k )
        {
            node *      child = & ( tree->n_child[ k ] );
            if ( child->n_type == DOT )
            {
                // Part of the name
                name[ length ] = '.';
                ++length;
                if ( firstNameNode == NULL )
                    firstNameNode = child;
                needFlush = 1;
                continue;
            }
            if ( child->n_type == dotted_name )
            {
                getDottedName( child, name, & length );
                if ( firstNameNode == NULL )
                    firstNameNode = child;
                needFlush = 1;
                continue;
            }

            if ( needFlush == 1 )
            {
                assert( length > 0 );
                name[ length ] = '\0';

                callOnImport( callbacks->onImport, name, length, firstNameNode->n_lineno,
                              firstNameNode->n_col_offset + 1, /* Make it 1-based */
                              lineShifts[ firstNameNode->n_lineno ] + firstNameNode->n_col_offset );

                needFlush = 0;
            }

            if ( child->n_type == import_as_names )
            {
                // This is what is imported from the module
                for ( int  j = 0; j < child->n_nchildren; ++j )
                {
                    node *      whatChild = & ( child->n_child[ j ] );
                    if ( whatChild->n_type == import_as_name )
                    {
                        assert( whatChild->n_nchildren == 1 ||
                                whatChild->n_nchildren == 3 );
                        node *  whatName = & ( whatChild->n_child[ 0 ] );

                        callOnWhat( callbacks->onWhat, whatName->n_str,
                                    strlen( whatName->n_str ),
                                    whatName->n_lineno,
                                    whatName->n_col_offset + 1, /* Make it 1-based */
                                    lineShifts[ whatName->n_lineno ] + whatName->n_col_offset );

                        if ( whatChild->n_nchildren == 3 )
                        {
                            node *  asName = & ( whatChild->n_child[ 2 ] );
                            callOnAs( callbacks->onAs,
                                      asName->n_str,
                                      strlen( asName->n_str ) );
                        }
                    }
                }
            }
        }
    }
    else
    {
        assert( tree->n_type == import_name );

        tree = findChildOfType( tree, dotted_as_names );
        assert( tree != NULL );

        node *      child;
        for ( int  k = 0; k < tree->n_nchildren; ++k )
        {
            child = & ( tree->n_child[ k ] );
            if ( child->n_type == dotted_as_name )
            {
                int     expect_as_name = 0;
                for ( int  j = 0; j < child->n_nchildren; ++j )
                {
                    node *      subchild = & ( child->n_child[ j ] );

                    if ( subchild->n_type == dotted_name )
                    {
                        char    name[ MAX_DOTTED_NAME_LENGTH ];
                        int     length = 0;

                        getDottedName( subchild, name, & length );

                        callOnImport( callbacks->onImport, name, length, subchild->n_lineno,
                                      subchild->n_col_offset + 1, /* Make it 1-based */
                                      lineShifts[ subchild->n_lineno ] + subchild->n_col_offset );
                        continue;
                    }
                    if ( subchild->n_type == NAME )
                    {
                        if ( expect_as_name == 1 )
                        {
                            callOnAs( callbacks->onAs, subchild->n_str, strlen( subchild->n_str ) );
                            expect_as_name = 0;
                            continue;
                        }

                        if ( strcmp( subchild->n_str, "as" ) == 0 )
                            expect_as_name = 1;
                    }
                }

            }
        }
    }
}


static const char *  processArgument( node *        tree,
                                      PyObject *    onArg )
{
    assert( tree->n_type == fpdef );
    assert( tree->n_nchildren > 0 );

    node *      nameNode = & ( tree->n_child[ 0 ] );
    assert( nameNode->n_type == NAME );

    callOnArg( onArg, nameNode->n_str, strlen( nameNode->n_str ) );
    return nameNode->n_str;
}


static int processDecor( node *                        tree,
                         struct instanceCallbacks *    callbacks,
                         int *                         lineShifts )
{
    int     staticMethod = 0;
    assert( tree->n_type == decorator );

    node *      nameNode = findChildOfType( tree, dotted_name );
    assert( nameNode != NULL );

    char        name[ MAX_DOTTED_NAME_LENGTH ];
    int         length = 0;
    getDottedName( nameNode, name, & length );

    callOnDecorator( callbacks->onDecorator,
                     name, length,
                     nameNode->n_lineno,
                     nameNode->n_col_offset + 1,    /* Make it 1-based */
                     lineShifts[ nameNode->n_lineno ] + nameNode->n_col_offset );

    if ( strcmp( name, "staticmethod" ) == 0 )
    {
        staticMethod = 1;
    }

    node *      argsNode = findChildOfType( tree, arglist );
    if ( argsNode != NULL )
    {
        /* There are decorator arguments */
        node *      child;
        for ( int  k = 0; k < argsNode->n_nchildren; ++k )
        {
            child = & ( argsNode->n_child[ k ] );
            if ( child->n_type == argument )
            {
                char        arg[ MAX_ARG_VAL_SIZE ];
                int         length = 0;
                collectTestString( child, arg, & length );

                callOnArg( callbacks->onDecoratorArgument, arg, length );
            }
        }
    }

    return staticMethod;
}

static int processDecorators( node *                        tree,
                              struct instanceCallbacks *    callbacks,
                              int *                         lineShifts )
{
    int         staticMethod = 0;
    node *      child;
    int         n = tree->n_nchildren;
    assert( tree->n_type == decorators );

    for ( int  k = 0; k < n; ++k )
    {
        child = & ( tree->n_child[ k ] );
        if ( child->n_type == decorator )
        {
            int     isStatic = 0;
            isStatic = processDecor( child, callbacks, lineShifts );
            if ( staticMethod == 0 )
                staticMethod = isStatic;
        }
    }

    return staticMethod;
}



static void  processClassDefinition( node *                       tree,
                                     struct instanceCallbacks *   callbacks,
                                     int                          objectsLevel,
                                     enum Scope                   scope,
                                     int                          entryLevel,
                                     int *                        lineShifts )
{
    assert( tree->n_type == classdef );
    assert( tree->n_nchildren > 1 );

    node *      classNode = & ( tree->n_child[ 0 ] );
    node *      nameNode = & ( tree->n_child[ 1 ] );
    node *      colonNode = findChildOfType( tree, COLON );

    assert( colonNode != NULL );


    ++objectsLevel;
    callOnClass( callbacks->onClass,
                 nameNode->n_str, strlen( nameNode->n_str ),
                 /* Class name line and pos */
                 nameNode->n_lineno,
                 nameNode->n_col_offset + 1,         /* To make it 1-based */
                 lineShifts[ nameNode->n_lineno ] + nameNode->n_col_offset,
                 /* Keyword 'class' line and pos */
                 classNode->n_lineno,
                 classNode->n_col_offset + 1,          /* To make it 1-based */
                 /* ':' line and pos */
                 colonNode->n_lineno,
                 colonNode->n_col_offset + 1,        /* To make it 1-based */
                 objectsLevel );

    /* Collect inheritance list */
    node *      listNode = findChildOfType( tree, testlist );
    if ( listNode != NULL )
    {
        node *      child;
        int         n = listNode->n_nchildren;
        for ( int  k = 0; k < n; ++k )
        {
            child = & ( listNode->n_child[ k ] );
            if ( child->n_type == test )
            {
                char        buffer[ MAX_ARG_VAL_SIZE ];
                int         length = 0;

                collectTestString( child, buffer, & length );
                callOnBaseClass( callbacks->onBaseClass, buffer, length );
            }
        }
    }


    node *      suiteNode = findChildOfType( tree, suite );
    assert( suiteNode != NULL );
    checkForDocstring( suiteNode, callbacks );

    walk( suiteNode, callbacks, objectsLevel,
          CLASS_SCOPE, NULL, entryLevel, lineShifts, 0 );
    return;
}


static void
processFuncDefinition( node *                       tree,
                       struct instanceCallbacks *   callbacks,
                       int                          objectsLevel,
                       enum Scope                   scope,
                       int                          entryLevel,
                       int *                        lineShifts,
                       int                          isStaticMethod )
{
    assert( tree->n_type == funcdef );
    assert( tree->n_nchildren > 1 );

    node *      defNode = & ( tree->n_child[ 0 ] );
    node *      nameNode = & ( tree->n_child[ 1 ] );
    node *      colonNode = findChildOfType( tree, COLON );

    assert( colonNode != NULL );

    ++objectsLevel;
    callOnFunction( callbacks->onFunction,
                    nameNode->n_str, strlen( nameNode->n_str ),
                    /* Function name line and pos */
                    nameNode->n_lineno,
                    nameNode->n_col_offset + 1,         /* To make it 1-based */
                    lineShifts[ nameNode->n_lineno ] + nameNode->n_col_offset,
                    /* Keyword 'def' line and pos */
                    defNode->n_lineno,
                    defNode->n_col_offset + 1,          /* To make it 1-based */
                    /* ':' line and pos */
                    colonNode->n_lineno,
                    colonNode->n_col_offset + 1,        /* To make it 1-based */
                    objectsLevel );

    const char *    firstArgName = NULL;
    int             firstArg = 1;
    node *          paramNode = findChildOfType( tree, parameters );
    assert( paramNode != NULL );

    node *      argsNode = findChildOfType( paramNode, varargslist );
    if ( argsNode != NULL )
    {
        /* The function has arguments */
        int         k = 0;
        node *      child;
        while ( k < argsNode->n_nchildren )
        {
            child = & ( argsNode->n_child[ k ] );
            if ( child->n_type == fpdef )
            {
                if ( firstArg == 1 )
                {
                    firstArgName = processArgument( child,
                                                    callbacks->onArgument );
                    firstArg = 0;
                }
                else
                {
                    processArgument( child, callbacks->onArgument );
                }
            }
            else if ( child->n_type == STAR )
            {
                ++k;
                node *      nameChild = & ( argsNode->n_child[ k ] );
                int         nameLen = strlen( nameChild->n_str );
                char        starName[ MAX_DOTTED_NAME_LENGTH ];

                starName[ 0 ] = '*';
                memcpy( & ( starName[ 1 ] ), nameChild->n_str, nameLen );
                callOnArg( callbacks->onArgument, starName, nameLen + 1 );
            }
            else if ( child->n_type == DOUBLESTAR )
            {
                ++k;
                node *      nameChild = & ( argsNode->n_child[ k ] );
                int         nameLen = strlen( nameChild->n_str );
                char        starName[ MAX_DOTTED_NAME_LENGTH ];

                starName[ 0 ] = '*';
                starName[ 1 ] = '*';
                memcpy( & ( starName[ 2 ] ), nameChild->n_str, nameLen );
                callOnArg( callbacks->onArgument, starName, nameLen + 2 );
            }
            else if ( child->n_type == test )
            {
                char        buffer[ MAX_ARG_VAL_SIZE ];
                int         length = 0;

                collectTestString( child, buffer, & length );
                callOnArgVal( callbacks->onArgumentValue, buffer, length );
            }

            ++k;
        }
    }


    node *      suiteNode = findChildOfType( tree, suite );
    assert( suiteNode != NULL );
    checkForDocstring( suiteNode, callbacks );

    /* Detect the new scope */
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

    walk( suiteNode, callbacks, objectsLevel,
          newScope, firstArgName, entryLevel, lineShifts, 0 );
    return;
}


static void processAssign( node *              tree,
                           PyObject *          onVariable,
                           int                 objectsLevel,
                           int *               lineShifts )
{
    assert( tree->n_type == testlist ||
            tree->n_type == testlist_comp );

    node *      child;
    for ( int  k = 0; k < tree->n_nchildren; ++k )
    {
        child = & ( tree->n_child[ k ] );
        if ( child->n_type == test )
        {
            node *      powerNode = skipToNode( child, power );
            child = skipToNode( powerNode, atom );
            if ( child == NULL )
                continue;
            /* trailer means it is usage, not the initialization */
            if ( findChildOfType( powerNode, trailer ) != NULL )
                continue;

            if ( child->n_child[ 0 ].n_type == LPAR ||
                 child->n_child[ 0 ].n_type == LSQB )
            {
                node *      listNode = findChildOfType( child, testlist_comp );
                if ( listNode == NULL )
                    listNode = findChildOfType( child, listmaker );
                if ( listNode != NULL )
                    processAssign( listNode, onVariable,
                                   objectsLevel, lineShifts );
                continue;
            }

            char    name[ MAX_ARG_VAL_SIZE ];
            int     length = 0;

            collectTestString( child, name, & length );
            callOnVariable( onVariable,
                            name, length,
                            child->n_lineno,
                            child->n_col_offset + 1, /* Make it 1-based */
                            lineShifts[ child->n_lineno ] + child->n_col_offset,
                            objectsLevel );
        }
    }
    return;
}

static void processInstanceMember( node *                      tree,
                                   struct instanceCallbacks *  callbacks,
                                   const char *                firstArgName,
                                   int                         objectsLevel,
                                   int *                       lineShifts )
{
    if ( firstArgName == NULL )
        return;

    assert( tree->n_type == testlist ||
            tree->n_type == testlist_comp );

    node *      child;
    int         n = tree->n_nchildren;
    for ( int  k = 0; k < n; ++k )
    {
        child = & ( tree->n_child[ k ] );
        if ( child->n_type == test )
        {
            node *      powerNode = skipToNode( child, power );
            child = skipToNode( powerNode, atom );
            if ( child == NULL )
                continue;

            if ( child->n_child[ 0 ].n_type == LPAR ||
                 child->n_child[ 0 ].n_type == LSQB )
            {
                node *      listNode = findChildOfType( child, testlist_comp );
                if ( listNode == NULL )
                    listNode = findChildOfType( child, listmaker );
                if ( listNode != NULL )
                    processInstanceMember( listNode, callbacks, firstArgName,
                                           objectsLevel, lineShifts );
                continue;
            }

            /* Count the trailer nodes. If there are more than one then it is
             * the usage, not initialization */
            int         trailerCount = 0;
            node *      trailerNode = NULL;
            for ( int  j = 0; j < powerNode->n_nchildren; ++j )
            {
                if ( powerNode->n_child[ j ].n_type == trailer )
                {
                    ++trailerCount;
                    trailerNode = & ( powerNode->n_child[ j ] );
                }
            }
            if ( trailerCount != 1 )
                continue;
            if ( trailerNode->n_nchildren != 2 )
                continue;
            if ( trailerNode->n_child[ 0 ].n_type != DOT )
                continue;
            if ( trailerNode->n_child[ 1 ].n_type != NAME )
                continue;

            /* collect the first part of the name and match it with the first
             * argument name */
            char    name[ MAX_ARG_VAL_SIZE ];
            int     length = 0;

            collectTestString( child, name, & length );
            name[ length ] = '\0';
            if ( strcmp( name, firstArgName ) != 0 )
                continue;

            /* Here: the trailer is what needs to be collected */
            node *      nameNode = & ( trailerNode->n_child[ 1 ] );
            callOnInstanceAttribute( callbacks->onInstanceAttribute,
                                     nameNode->n_str, strlen( nameNode->n_str ),
                                     nameNode->n_lineno,
                                     nameNode->n_col_offset + 1, /* Make it 1-based */
                                     lineShifts[ nameNode->n_lineno ] + nameNode->n_col_offset,
                                     objectsLevel );
        }
    }

    return;
}



/* Provides non NULL node to expr_stmt if it is an assignment */
static node *  isAssignment( node *  tree )
{
    assert( tree->n_type == stmt );
    if ( tree->n_nchildren < 1 )                    return NULL;
    tree = & ( tree->n_child[ 0 ] );
    if ( tree->n_type != simple_stmt )              return NULL;
    if ( tree->n_nchildren < 1 )                    return NULL;
    tree = & ( tree->n_child[ 0 ] );
    if ( tree->n_type != small_stmt )               return NULL;
    if ( tree->n_nchildren < 1 )                    return NULL;
    tree = & ( tree->n_child[ 0 ] );
    if ( tree->n_type != expr_stmt )                return NULL;
    if ( tree->n_nchildren < 2 )                    return NULL;
    if ( tree->n_child[ 0 ].n_type != testlist )    return NULL;
    if ( tree->n_child[ 1 ].n_type != EQUAL )       return NULL;
    return tree;
}



void walk( node *                       tree,
           struct instanceCallbacks *   callbacks,
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
            processImport( tree, callbacks, lineShifts );
            return;
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

        default:
            break;
    }


    int         staticDecor = 0;
    node *      child;
    int         n = tree->n_nchildren;
    for ( int  i = 0; i < n; ++i )
    {
        child = & ( tree->n_child[ i ] );

        if ( (entryLevel == 1) && (i == 0) )
        {
            /* This could be a module docstring */
            checkForDocstring( tree, callbacks );
        }

        /* decorators are always before a class or a function definition on the
         * same level. So they will be picked by the following deinition
         */
        if ( child->n_type == decorators )
        {
            staticDecor = processDecorators( child, callbacks, lineShifts );
            continue;
        }
        walk( child, callbacks, objectsLevel,
              scope, firstArgName, entryLevel, lineShifts, staticDecor );
        staticDecor = 0;
    }

    return;
}



/* Calculates the line shifts in terms of absolute position */
void calculateLineShifts( char *  buffer, int *  lineShifts )
{
    int     absPos = 0;
    char    symbol;
    int     line = 1;

    /* index 0 is not used; The first line starts with shift 0 */
    lineShifts[ 1 ] = 0;
    while ( buffer[ absPos ] != '\0' )
    {
        symbol = buffer[ absPos ];
        if ( symbol == '\r' )
        {
            ++absPos;
            if ( buffer[ absPos ] == '\n' )
            {
                ++absPos;
            }
            ++line;
            lineShifts[ line ] = absPos;
            continue;
        }

        if ( symbol == '\n' )
        {
            ++absPos;
            ++line;
            lineShifts[ line ] = absPos;
            continue;
        }
        ++absPos;
    }
    return;
}

/* Copied and adjusted from Python/pythonrun.c
 * static void err_input(perrdetail *err)
 */
static void getErrorMessage( char *  buffer, perrdetail *  err)
{
    sprintf( buffer, "%d:%d ", err->lineno, err->offset );
    int     len = strlen( buffer );

    switch ( err->error )
    {
        case E_ERROR:
            sprintf( buffer,
                     "execution error" );
            return;
        case E_SYNTAX:
            if ( err->expected == INDENT )
                sprintf( & buffer[ len ],
                         "expected an indented block" );
            else if ( err->token == INDENT )
                sprintf( & buffer[ len ],
                         "unexpected indent" );
            else if (err->token == DEDENT)
                sprintf( & buffer[ len ],
                         "unexpected unindent" );
            else
                sprintf( & buffer[ len ],
                         "invalid syntax" );
            break;
        case E_TOKEN:
            sprintf( & buffer[ len ],
                     "invalid token" );
            break;
        case E_EOFS:
            sprintf( & buffer[ len ],
                     "EOF while scanning triple-quoted string literal" );
            break;
        case E_EOLS:
            sprintf( & buffer[ len ],
                     "EOL while scanning string literal" );
            break;
        case E_INTR:
            sprintf( buffer,
                     "keyboard interrupt" );
            goto cleanup;
        case E_NOMEM:
            sprintf( buffer,
                    "no memory" );
            goto cleanup;
        case E_EOF:
            sprintf( & buffer[ len ],
                     "unexpected EOF while parsing" );
            break;
        case E_TABSPACE:
            sprintf( & buffer[ len ],
                     "inconsistent use of tabs and spaces in indentation" );
            break;
        case E_OVERFLOW:
            sprintf( & buffer[ len ],
                     "expression too long" );
            break;
        case E_DEDENT:
            sprintf( & buffer[ len ],
                     "unindent does not match any outer indentation level" );
            break;
        case E_TOODEEP:
            sprintf( & buffer[ len ],
                     "too many levels of indentation" );
            break;
        case E_DECODE:
            sprintf( & buffer[ len ],
                     "decode error" );
            break;
        case E_LINECONT:
            sprintf( & buffer[ len ],
                     "unexpected character after line continuation character" );
            break;
        default:
            sprintf( & buffer[ len ],
                     "unknown parsing error (error code %d)", err->error);
            break;
    }

    if ( err->text != NULL )
        sprintf( & buffer[ strlen( buffer ) ], "\n%s", err->text );

    cleanup:
    if (err->text != NULL)
    {
        PyObject_FREE(err->text);
        err->text = NULL;
    }
}



static void processEncoding( char *                         buffer,
                             node *                         tree,
                             struct instanceCallbacks *     callbacks )
{
    /* Unfortunately, the parser does not provide the position of the encoding
     * so it needs to be calculated
     */
    char *      start = strstr( buffer, tree->n_str );
    if ( start == NULL )
        return;     /* would be really strange */

    int         line = 1;
    int         col = 1;
    char *      current = buffer;
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

    callOnEncoding( callbacks->onEncoding, tree->n_str,
                    line, col, start - buffer );
}


static PyObject *
parse_input( char *                         buffer,
             const char *                   fileName,
             struct instanceCallbacks *     callbacks )
{
    perrdetail          error;
    PyCompilerFlags     flags = { 0 };
    node *              tree = PyParser_ParseStringFlagsFilename(
                                    buffer, fileName, &_PyParser_Grammar,
                                    file_input, &error, flags.cf_flags );

    if ( tree == NULL )
    {
        char        buffer[ MAX_ERROR_MSG_SIZE ];

        getErrorMessage( buffer, & error );
        callOnError( callbacks->onError, buffer );
        PyErr_Clear();
    }
    else
    {
        /* Walk the tree and populate the python structures */
        node *      root = tree;
        int         totalLines = getTotalLines( tree );

        assert( totalLines >= 0 );
        int         lineShifts[ totalLines + 1 ];

        calculateLineShifts( buffer, lineShifts );

        if ( root->n_type == encoding_decl )
        {
            processEncoding( buffer, tree, callbacks );
            root = & (root->n_child[ 0 ]);
        }


        assert( root->n_type == file_input );
        walk( root, callbacks, -1, GLOBAL_SCOPE, NULL, 0, lineShifts, 0 );
        PyNode_Free( tree );
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
    PyObject *                  retValue;
    FILE *                      f;
    struct stat                 st;

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

    f = fopen( fileName, "r" );
    if ( f == NULL )
    {
        clearCallbacks( & callbacks );
        PyErr_SetString( PyExc_RuntimeError, "Cannot open file" );
        return NULL;
    }

    /* Get the file size */
    stat( fileName, &st );

    if ( st.st_size > 0 )
    {
        char            buffer[st.st_size + 2];
        int             elem = fread( buffer, st.st_size, 1, f );
        if ( elem != 1 )
        {
            fclose( f );
            clearCallbacks( & callbacks );
            PyErr_SetString( PyExc_RuntimeError, "Cannot read file" );
            return NULL;
        }

        buffer[ st.st_size ] = '\n';
        buffer[ st.st_size + 1 ] = '\0';
        fclose( f );

        retValue = parse_input( buffer, fileName, & callbacks );
    }
    else
    {
        fclose( f );
        clearCallbacks( & callbacks );
        Py_INCREF( Py_None );
        return Py_None;
    }

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
    int                         length;
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

    length = strlen( content );
    if ( content[ length - 1 ] == '\n' )
    {
        retValue = parse_input( content, "dummy.py", & callbacks );
    }
    else
    {
        char *  buffer = (char *)malloc( length + 2 );
        memcpy( buffer, content, length );
        buffer[ length ] = '\n';
        buffer[ length + 1 ] = '\0';

        retValue = parse_input( content, "dummy.py", & callbacks );
        free( buffer );
    }

    clearCallbacks( & callbacks );
    return retValue;
}



static PyMethodDef _cdm_py_parser_methods[] =
{
    { "getBriefModuleInfoFromFile",   py_modinfo_from_file, METH_VARARGS,
                                      py_modinfo_from_file_doc },
    { "getBriefModuleInfoFromMemory", py_modinfo_from_mem,  METH_VARARGS,
                                      py_modinfo_from_mem_doc },
    { NULL, NULL, 0, NULL }
};


#if PY_MAJOR_VERSION < 3
    /* Python 2 initialization */
    void init_cdmpyparser( void )
    {
        PyObject *  module = Py_InitModule( "_cdmpyparser",
                                            _cdm_py_parser_methods );
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

