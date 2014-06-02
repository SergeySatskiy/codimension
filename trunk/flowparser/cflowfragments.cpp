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
 * Python extension module - control flow fragments
 */


#include <string>

#include "cflowfragments.hpp"
#include "cflowfragmenttypes.hpp"
#include "cflowversion.hpp"
#include "cflowdocs.hpp"
#include "cflowutils.hpp"


// Convenience macros
#define GETINTATTR( member )                        \
    do { if ( strcmp( name, STR( member ) ) == 0 )  \
        return PYTHON_INT_TYPE( member ); } while ( 0 )
#define GETBOOLATTR( member )                       \
    do { if ( strcmp( name, STR( member ) ) == 0 )  \
        return Py::Boolean( member ); } while ( 0 )


#define SETINTATTR( member, value )                                 \
    do { if ( strcmp( name, STR( member ) ) == 0 )                  \
         { if ( !value.isNumeric() )                                \
           {                                                        \
             throw Py::ValueError( "Attribute '"                    \
                        STR( member ) "' value must be numeric" );  \
           }                                                        \
           member = (INT_TYPE)(PYTHON_INT_TYPE( value ));           \
           return 0;                                                \
         }                                                          \
       } while ( 0 )

#define SETBOOLATTR( member, value )                                \
    do { if ( strcmp( name, STR( member ) ) == 0 )                  \
         { if ( !value.isBoolean() )                                \
           {                                                        \
             throw Py::ValueError( "Attribute '"                    \
                        STR( member ) "' value must be boolean" );  \
           }                                                        \
           member = (bool)(Py::Boolean( value ));                   \
           return 0;                                                \
         }                                                          \
       } while ( 0 )





Py::List    FragmentBase::members;

FragmentBase::FragmentBase() :
    parent( NULL ), content( NULL ),
    kind( UNDEFINED_FRAGMENT ),
    begin( -1 ), end( -1 ), beginLine( -1 ), beginPos( -1 ),
    endLine( -1 ), endPos( -1 )
{}


FragmentBase::~FragmentBase()
{}


void FragmentBase::init( void )
{
    members.append( Py::String( "kind" ) );
    members.append( Py::String( "begin" ) );
    members.append( Py::String( "end" ) );
    members.append( Py::String( "beginLine" ) );
    members.append( Py::String( "beginPos" ) );
    members.append( Py::String( "endLine" ) );
    members.append( Py::String( "endPos" ) );
    return;
}


Py::List  FragmentBase::getMembers( void ) const
{
    return members;
}


Py::Object  FragmentBase::getAttribute( const char *  name )
{
    GETINTATTR( kind );
    GETINTATTR( begin );
    GETINTATTR( end );
    GETINTATTR( beginLine );
    GETINTATTR( beginPos );
    GETINTATTR( endLine );
    GETINTATTR( endPos );

    return Py::None();
}


int  FragmentBase::setAttr( const char *        name,
                            const Py::Object &  value )
{
    SETINTATTR( kind, value );
    SETINTATTR( begin, value );
    SETINTATTR( end, value );
    SETINTATTR( beginLine, value );
    SETINTATTR( beginPos, value );
    SETINTATTR( endLine, value );
    SETINTATTR( endPos, value );

    return -1;
}


std::string  FragmentBase::getContent( const std::string *  buf )
{
    if ( buf != NULL )
        return buf->substr( begin, end - begin + 1 );

    // Check if serialized
    FragmentBase *      current = this;
    while ( current->parent != NULL )
        current = current->parent;
    if ( current->content != NULL )
        return current->content->substr( begin, end - begin + 1 );

    throw Py::RuntimeError( "Cannot get content of not serialized "
                            "fragment without its buffer" );
}


Py::Object  FragmentBase::getContent( const Py::Tuple &  args )
{
    size_t      argCount( args.length() );

    if ( argCount == 0 )
        return Py::String( getContent( NULL ) );

    if ( argCount == 1 )
    {
        std::string  content( Py::String( args[ 0 ] ).as_std_string() );
        return Py::String( getContent( & content ) );
    }

    throwWrongBufArgument( "getContent" );
}


Py::Object  FragmentBase::getLineContent( const Py::Tuple &  args )
{
    size_t      argCount( args.length() );

    if ( argCount == 0 )
        return Py::String( std::string( beginPos - 1, ' ' ) +
                           getContent( NULL ) );

    if ( argCount == 1 )
    {
        std::string  content( Py::String( args[ 0 ] ).as_std_string() );
        return Py::String( std::string( beginPos - 1, ' ' ) +
                           getContent( & content ) );
    }

    throw Py::RuntimeError( "Unexpected number of arguments. getLineContent() "
                            "supports no arguments or one argument "
                            "(text buffer)" );
}


Py::Object  FragmentBase::getLineRange( void )
{
    return Py::TupleN( PYTHON_INT_TYPE( beginLine ),
                       PYTHON_INT_TYPE( endLine ) );
}


std::string  FragmentBase::asStr( void ) const
{
    char    buffer[ 64 ];
    sprintf( buffer, "[%ld:%ld] (%ld,%ld) (%ld,%ld)",
                     begin, end,
                     beginLine, beginPos,
                     endLine, endPos );
    return buffer;
}


void  FragmentBase::throwWrongBufArgument( const std::string &  funcName )
{
    throw Py::RuntimeError( "Unexpected number of arguments. " + funcName +
                            "() supports no arguments or one argument "
                            "(text buffer)" );
}

// --- End of FragmentBase definition ---


Fragment::Fragment()
{
    kind = FRAGMENT;
}


Fragment::~Fragment()
{}


void Fragment::initType( void )
{
    behaviors().name( "Fragment" );
    behaviors().doc( FRAGMENT_DOC );
    behaviors().supportGetattr();
    behaviors().supportSetattr();
    behaviors().supportRepr();

    add_noargs_method( "getLineRange", &FragmentBase::getLineRange,
                       GETLINERANGE_DOC );
    add_varargs_method( "getContent", &FragmentBase::getContent,
                        GETCONTENT_DOC );
    add_varargs_method( "getLineContent", &FragmentBase::getLineContent,
                        GETLINECONTENT_DOC );
}


Py::Object Fragment::getattr( const char *  name )
{
    // Support for dir(...)
    if ( strcmp( name, "__members__" ) == 0 )
        return getMembers();

    Py::Object      value = getAttribute( name );
    if ( value.isNone() )
        return getattr_methods( name );
    return value;
}


Py::Object  Fragment::repr( void )
{
    return Py::String( "<Fragment " + asStr() + ">" );
}


int  Fragment::setattr( const char *        name,
                        const Py::Object &  value )
{
    if ( FragmentBase::setAttr( name, value ) != 0 )
        throw Py::AttributeError( "Unknown attribute '" +
                                  std::string( name ) + "'" );
    return 0;
}


// --- End of Fragment definition ---

BangLine::BangLine()
{
    kind = BANG_LINE_FRAGMENT;
}


BangLine::~BangLine()
{}


void BangLine::initType( void )
{
    behaviors().name( "BangLine" );
    behaviors().doc( BANGLINE_DOC );
    behaviors().supportGetattr();
    behaviors().supportSetattr();
    behaviors().supportRepr();

    add_noargs_method( "getLineRange", &FragmentBase::getLineRange,
                       GETLINERANGE_DOC );
    add_varargs_method( "getContent", &FragmentBase::getContent,
                        GETCONTENT_DOC );
    add_varargs_method( "getLineContent", &FragmentBase::getLineContent,
                        GETLINECONTENT_DOC );
    add_varargs_method( "getDisplayValue", &BangLine::getDisplayValue,
                        BANGLINE_GETDISPLAYVALUE_DOC );
}


Py::Object BangLine::getattr( const char *  name )
{
    // Support for dir(...)
    if ( strcmp( name, "__members__" ) == 0 )
        return getMembers();

    Py::Object      value = getAttribute( name );
    if ( value.isNone() )
        return getattr_methods( name );
    return value;
}


Py::Object  BangLine::repr( void )
{
    return Py::String( "<BangLine " + asStr() + ">" );
}


int  BangLine::setattr( const char *        name,
                        const Py::Object &  value )
{
    if ( FragmentBase::setAttr( name, value ) != 0 )
        throw Py::AttributeError( "Unknown attribute '" +
                                  std::string( name ) + "'" );
    return 0;
}


Py::Object  BangLine::getDisplayValue( const Py::Tuple &  args )
{
    std::string     content;

    switch ( args.length() )
    {
        case 0:
            content = FragmentBase::getContent( NULL );
            break;
        case 1:
            {
                std::string  buf( Py::String( args[ 0 ] ).as_std_string() );
                content = FragmentBase::getContent( & buf );
                break;
            }
        default:
            throwWrongBufArgument( "getDisplayValue" );
    }

    if ( content.length() < 2 )
        throw Py::RuntimeError( "Unexpected bang line fragment. The fragment "
                                "is shorter than 2 characters." );
    if ( content[ 0 ] != '#' || content[ 1 ] != '!' )
        throw Py::RuntimeError( "Unexpected bang line fragment. There is "
                                "no #! at the beginning." );

    return Py::String( trim( content.c_str() + 2, content.length() - 2 ) );
}

// --- End of BangLine definition ---

EncodingLine::EncodingLine()
{
    kind = ENCODING_LINE_FRAGMENT;
}


EncodingLine::~EncodingLine()
{}


void EncodingLine::initType( void )
{
    behaviors().name( "EncodingLine" );
    behaviors().doc( ENCODINGLINE_DOC );
    behaviors().supportGetattr();
    behaviors().supportSetattr();
    behaviors().supportRepr();

    add_noargs_method( "getLineRange", &FragmentBase::getLineRange,
                       GETLINERANGE_DOC );
    add_varargs_method( "getContent", &FragmentBase::getContent,
                        GETCONTENT_DOC );
    add_varargs_method( "getLineContent", &FragmentBase::getLineContent,
                        GETLINECONTENT_DOC );
    add_varargs_method( "getDisplayValue", &EncodingLine::getDisplayValue,
                        ENCODINGLINE_GETDISPLAYVALUE_DOC );
}


Py::Object EncodingLine::getattr( const char *  name )
{
    // Support for dir(...)
    if ( strcmp( name, "__members__" ) == 0 )
        return getMembers();

    Py::Object      value = getAttribute( name );
    if ( value.isNone() )
        return getattr_methods( name );
    return value;
}


Py::Object  EncodingLine::repr( void )
{
    return Py::String( "<EncodingLine " + asStr() + ">" );
}


int  EncodingLine::setattr( const char *        name,
                            const Py::Object &  value )
{
    if ( FragmentBase::setAttr( name, value ) != 0 )
        throw Py::AttributeError( "Unknown attribute '" +
                                  std::string( name ) + "'" );
    return 0;
}


Py::Object  EncodingLine::getDisplayValue( const Py::Tuple &  args )
{
    std::string     content;

    switch ( args.length() )
    {
        case 0:
            content = FragmentBase::getContent( NULL );
            break;
        case 1:
            {
                std::string  buf( Py::String( args[ 0 ] ).as_std_string() );
                content = FragmentBase::getContent( & buf );
                break;
            }
        default:
            throwWrongBufArgument( "getDisplayValue" );
    }

    const char *    lineStart( content.c_str() );
    const char *    encBegin( strstr( lineStart, "coding" ) );

    if ( encBegin == NULL )
        throw Py::RuntimeError( "Inconsistency detected. Cannot find 'coding' "
                                "substring in the EncodingLine fragment" );

    encBegin += 6;     /* len( 'coding' ) */
    if ( *encBegin == ':' || *encBegin == '=' )
        ++encBegin;
    while ( isspace( *encBegin ) )
        ++encBegin;

    const char *    encEnd( encBegin );
    while ( *encEnd != '\0' && isspace( *encEnd ) == 0 )
        ++encEnd;

    return Py::String( encBegin, encEnd - encBegin );
}

// --- End of EncodingLine definition ---


Comment::Comment()
{
    kind = COMMENT_FRAGMENT;
}


Comment::~Comment()
{}


void Comment::initType( void )
{
    behaviors().name( "Comment" );
    behaviors().doc( COMMENT_DOC );
    behaviors().supportGetattr();
    behaviors().supportSetattr();
    behaviors().supportRepr();

    add_noargs_method( "getLineRange", &FragmentBase::getLineRange,
                       GETLINERANGE_DOC );
    add_varargs_method( "getContent", &FragmentBase::getContent,
                        GETCONTENT_DOC );
    add_varargs_method( "getLineContent", &FragmentBase::getLineContent,
                        GETLINECONTENT_DOC );
    add_varargs_method( "getDisplayValue", &Comment::getDisplayValue,
                        COMMENT_GETDISPLAYVALUE_DOC );
    add_varargs_method( "niceStringify", &Comment::niceStringify,
                        COMMENT_NICESTRINGIFY_DOC );
}


Py::Object Comment::getattr( const char *  name )
{
    // Support for dir(...)
    if ( strcmp( name, "__members__" ) == 0 )
    {
        Py::List    members;
        Py::List    baseMembers( getMembers() );

        for ( Py::List::size_type k( 0 ); k < baseMembers.length(); ++k )
            members.append( baseMembers[ k ] );

        members.append( Py::String( "parts" ) );
        return members;
    }

    Py::Object      value = getAttribute( name );
    if ( value.isNone() )
    {
        if ( strcmp( name, "parts" ) == 0 )
            return parts;
        return getattr_methods( name );
    }
    return value;
}


Py::Object  Comment::repr( void )
{
    Py::String      ret( "<Comment " + asStr() );
    for ( Py::List::size_type k( 0 ); k < parts.length(); ++k )
        ret = ret + Py::String( "\n" ) + Py::String( parts[ k ].repr() );
    ret = ret + Py::String( ">" );
    return ret;
}


int  Comment::setattr( const char *        name,
                       const Py::Object &  value )
{
    if ( FragmentBase::setAttr( name, value ) != 0 )
    {
        if ( strcmp( name, "parts" ) == 0 )
        {
            if ( ! value.isList() )
                throw Py::ValueError( "Attribute 'parts' value "
                                      "must be a list" );
            parts = Py::List( value );
        }
        else
        {
            throw Py::AttributeError( "Unknown attribute '" +
                                      std::string( name ) + "'" );
        }
    }
    return 0;
}


Py::Object  Comment::getDisplayValue( const Py::Tuple &  args )
{
    size_t          argCount( args.length() );
    std::string     buf;
    std::string *   bufPointer;

    if ( argCount == 0 )
        bufPointer = NULL;
    else if ( argCount == 1 )
    {
        buf = Py::String( args[ 0 ] ).as_std_string();
        bufPointer = & buf;
    }
    else
        throwWrongBufArgument( "getDisplayValue" );


    Py::List::size_type     partCount( parts.length() );

    if (partCount == 0)
        return Py::String( "" );

    Fragment *  firstFragment( static_cast<Fragment *>(parts[ 0 ].ptr()) );
    INT_TYPE    minShift( firstFragment->beginPos );
    bool        sameShift( true );

    for ( Py::List::size_type k( 1 ); k < partCount; ++k )
    {
        INT_TYPE    shift( static_cast<Fragment *>(parts[ k ].ptr())->beginPos );
        if ( shift != minShift )
        {
            sameShift = false;
            if ( shift < minShift )
                minShift = shift;
        }
    }

    std::string      content;
    INT_TYPE         currentLine( firstFragment->beginLine );

    for ( Py::List::size_type k( 0 ); k < partCount; ++k )
    {
        Fragment *  currentFragment( static_cast<Fragment *>(parts[ k ].ptr()) );

        if ( k != 0 )
            content += "\n";
        if ( currentFragment->beginLine - currentLine > 1 )
        {
            for ( INT_TYPE  j( 1 ); j < currentFragment->beginLine - currentLine; ++j )
                content += "\n";
        }
        if ( sameShift )
            content += currentFragment->getContent( bufPointer );
        else
        {
            if ( currentFragment->beginPos > minShift )
                content += std::string( ' ', currentFragment->beginPos - minShift ) +
                           currentFragment->getContent( bufPointer );
            else
                content += currentFragment->getContent( bufPointer );
        }
        currentLine = currentFragment->beginLine;
    }

    return Py::String( content );
}


Py::Object  Comment::niceStringify( const Py::Tuple &  args )
{
    if ( args.length() != 1 )
        throw Py::TypeError( "niceStringify() takes exactly 1 argument" );

    if ( ! args[ 0 ].isNumeric() )
        throw Py::TypeError( "niceStringify() takes 1 integer argument" );

    INT_TYPE    level( (INT_TYPE)(PYTHON_INT_TYPE( args[ 0 ] )) );
    Py::String  joiner( "\n" + std::string( ' ', (level + 1) * 4 ) );
    Py::String  result( std::string( ' ', level * 4 ) + "Comment: " + asStr() );

    Py::List::size_type     partCount( parts.length() );
    for ( Py::List::size_type k( 0 ); k < partCount; ++k )
    {
        result = result + joiner + Py::String( parts[ k ].repr() );
    }

    return result;
}

// --- End of Comment definition ---

Docstring::Docstring()
{
    kind = DOCSTRING_FRAGMENT;
    sideComment = Py::None();
}


Docstring::~Docstring()
{}


void Docstring::initType( void )
{
    behaviors().name( "Docstring" );
    behaviors().doc( DOCSTRING_DOC );
    behaviors().supportGetattr();
    behaviors().supportSetattr();
    behaviors().supportRepr();

    add_noargs_method( "getLineRange", &FragmentBase::getLineRange,
                       GETLINERANGE_DOC );
    add_varargs_method( "getContent", &FragmentBase::getContent,
                        GETCONTENT_DOC );
    add_varargs_method( "getLineContent", &FragmentBase::getLineContent,
                        GETLINECONTENT_DOC );
    add_varargs_method( "getDisplayValue", &Docstring::getDisplayValue,
                        DOCSTRING_GETDISPLAYVALUE_DOC );
    add_varargs_method( "niceStringify", &Docstring::niceStringify,
                        DOCSTRING_NICESTRINGIFY_DOC );
}


Py::Object Docstring::getattr( const char *  name )
{
    // Support for dir(...)
    if ( strcmp( name, "__members__" ) == 0 )
    {
        Py::List    members;
        Py::List    baseMembers( getMembers() );

        for ( Py::List::size_type k( 0 ); k < baseMembers.length(); ++k )
            members.append( baseMembers[ k ] );

        members.append( Py::String( "parts" ) );
        members.append( Py::String( "sideComment" ) );
        return members;
    }

    Py::Object      value = getAttribute( name );
    if ( value.isNone() )
    {
        if ( strcmp( name, "parts" ) == 0 )
            return parts;
        if ( strcmp( name, "sideComment" ) == 0 )
            return sideComment;
        return getattr_methods( name );
    }
    return value;
}


Py::Object  Docstring::repr( void )
{
    Py::String      ret( "<Docstring " + asStr() );
    for ( Py::List::size_type k( 0 ); k < parts.length(); ++k )
        ret = ret + Py::String( "\n" ) + Py::String( parts[ k ].repr() );
    if (sideComment.isNone())
        ret = ret + Py::String( "\nSideComment: None" );
    else
        ret = ret + Py::String( "\nSideComment: " ) +
              Py::String( static_cast<Fragment *>(sideComment.ptr())->asStr() );
    ret = ret + Py::String( ">" );
    return ret;
}


int  Docstring::setattr( const char *        name,
                         const Py::Object &  value )
{
    if ( FragmentBase::setAttr( name, value ) != 0 )
    {
        if ( strcmp( name, "parts" ) == 0 )
        {
            if ( ! value.isList() )
                throw Py::ValueError( "Attribute 'parts' value "
                                      "must be a list" );
            parts = Py::List( value );
        }
        else if ( strcmp( name, "sideComment" ) == 0 )
        {
            if ( ! value.isString() )
                throw Py::ValueError( "Attribute 'sideComment' value "
                                      "must be a string");
            sideComment = Py::String( value );
        }
        else
        {
            throw Py::AttributeError( "Unknown attribute '" +
                                      std::string( name ) + "'" );
        }
    }
    return 0;
}


Py::Object  Docstring::getDisplayValue( const Py::Tuple &  args )
{
    size_t          argCount( args.length() );
    std::string     buf;
    std::string *   bufPointer;

    if ( argCount == 0 )
        bufPointer = NULL;
    else if ( argCount == 1 )
    {
        buf = Py::String( args[ 0 ] ).as_std_string();
        bufPointer = & buf;
    }
    else
        throwWrongBufArgument( "getDisplayValue" );

    std::string     rawContent( FragmentBase::getContent( bufPointer ) );
    size_t          stripCount( 1 );
    if ( strncmp( rawContent.c_str(), "'''", 3 ) == 0 ||
         strncmp( rawContent.c_str(), "\"\"\"", 3 ) == 0 )
        stripCount = 3;

    return Py::String( trimDocstring(
                            rawContent.substr(
                                stripCount,
                                rawContent.length() - stripCount * 2 ) ) );
}


Py::Object  Docstring::niceStringify( const Py::Tuple &  args )
{
    if ( args.length() != 1 )
        throw Py::TypeError( "niceStringify() takes exactly 1 argument" );

    if ( ! args[ 0 ].isNumeric() )
        throw Py::TypeError( "niceStringify() takes 1 integer argument" );

    INT_TYPE    level( (INT_TYPE)(PYTHON_INT_TYPE( args[ 0 ] )) );
    Py::String  joiner( "\n" + std::string( ' ', (level + 1) * 4 ) );
    Py::String  result( std::string( ' ', level * 4 ) + "Docstring: " + asStr() );

    Py::List::size_type     partCount( parts.length() );
    for ( Py::List::size_type k( 0 ); k < partCount; ++k )
    {
        result = result + joiner + Py::String( parts[ k ].repr() );
    }

    result = result + joiner;
    if ( sideComment.isNone() )
        result = result + Py::String( "SideComment: None" );
    else
        result = result + Py::String( "\nSideComment: " ) +
                 Py::String( static_cast<Fragment *>(sideComment.ptr())->asStr() );
    return result;
}


std::string  Docstring::trimDocstring( const std::string &  docstring )
{
    if (docstring.empty())
        return "";

    // Split lines, expand tabs;
    // Detect the min indent (first line doesn't count)
    int                             indent( INT_MAX );
    std::vector< std::string >      lines( splitLines( docstring ) );
    for ( std::vector< std::string >::iterator  k( lines.begin() );
          k != lines.end(); ++k )
    {
        *k = expandTabs( *k );
        if ( k != lines.begin() )
        {
            int     strippedSize( strlen( trimStart( k->c_str() ) ) );
            if ( strippedSize > 0 )
                indent = std::min( indent, int(k->length()) - strippedSize );
        }
    }

    // Remove indentation (first line is special)
    lines[ 0 ] = trim( lines[ 0 ].c_str(), lines[ 0 ].length() );
    if ( indent < INT_MAX )
    {
        std::vector< std::string >::iterator    k( lines.begin() );
        for ( ++k; k != lines.end(); ++k )
        {
            std::string     rightStripped( trimEnd( k->c_str() ) );
            if ( rightStripped.length() > indent )
                *k = std::string( rightStripped.c_str() + indent );
            else
                *k = "";
        }
    }

    // Strip off trailing and leading blank lines
    ssize_t     startIndex( 0 );
    ssize_t     endIndex( lines.size() - 1 );

    for ( ssize_t    k( startIndex ); k <= endIndex; ++k )
    {
        if ( lines[ k ].length() != 0 )
            break;
        startIndex = k;
    }

    for ( ssize_t   k( endIndex ); k >= 0; --k )
    {
        if ( lines[ k ].length() != 0 )
            break;
        endIndex = k;
    }

    std::string     result;
    for (ssize_t    k( startIndex ); k <= endIndex; ++k )
    {
        if ( k != startIndex )
            result += "\n";
        result += lines[ k ];
    }

    return result;
}


// --- End of Docstring definition ---






