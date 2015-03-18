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


// small helper functions
void throwUnknownAttribute( const char *  attrName )
{
    throw Py::AttributeError( "Unknown attribute '" +
                              std::string( attrName ) + "'" );
}

void throwWrongBufArgument( const char *  funcName )
{
    throw Py::RuntimeError( "Unexpected number of arguments. " +
                            std::string( funcName ) +
                            "() supports no arguments or one argument "
                            "(text buffer)" );
}

void throwWrongType( const char *  attrName, const char *  typeName )
{
     throw Py::AttributeError( "Attribute '" +
                               std::string( attrName ) + "' value "
                               "must be of type " + std::string( typeName ) );
}


// Convenience macros
#define GETINTATTR( member )                            \
    do { if ( strcmp( attrName, STR( member ) ) == 0 )  \
         { retval = PYTHON_INT_TYPE( member );          \
           return true; } } while ( 0 )
#define GETBOOLATTR( member )                           \
    do { if ( strcmp( attrName, STR( member ) ) == 0 )  \
         { retval = Py::Boolean( member );              \
           return true; } } while ( 0 )


#define SETINTATTR( member, value )                                 \
    do { if ( strcmp( attrName, STR( member ) ) == 0 )              \
         { if ( !value.isNumeric() )                                \
             throwWrongType( STR( member ), "int or long" );        \
           member = (INT_TYPE)(PYTHON_INT_TYPE( value ));           \
           return true;                                             \
         }                                                          \
       } while ( 0 )

#define SETBOOLATTR( member, value )                                \
    do { if ( strcmp( attrName, STR( member ) ) == 0 )              \
         { if ( !value.isBoolean() )                                \
             throwWrongType( STR( member ), "bool" );               \
           member = (bool)(Py::Boolean( value ));                   \
           return 0;                                                \
         }                                                          \
       } while ( 0 )


#define CHECKVALUETYPE( member, type )                                  \
    do { if ( ! val.isNone() )                                          \
           if ( strcmp( val.ptr()->ob_type->tp_name, type ) != 0 )      \
             throwWrongType( member, type );                            \
       } while ( 0 )


#define TOFRAGMENT( member )                \
    (static_cast<Fragment *>(member.ptr()))



std::string  representFragmentPart( const Py::Object &  value,
                                    const char *        name )
{
    if ( value.isNone() )
        return std::string( name ) + ": None";
    return std::string( name ) + ": " + TOFRAGMENT( value )->asStr();
}




FragmentBase::FragmentBase() :
    parent( NULL ), content( NULL ),
    kind( UNDEFINED_FRAGMENT ),
    begin( -1 ), end( -1 ), beginLine( -1 ), beginPos( -1 ),
    endLine( -1 ), endPos( -1 )
{}


FragmentBase::~FragmentBase()
{}


void  FragmentBase::appendMembers( Py::List &  container ) const
{
    container.append( Py::String( "kind" ) );
    container.append( Py::String( "begin" ) );
    container.append( Py::String( "end" ) );
    container.append( Py::String( "beginLine" ) );
    container.append( Py::String( "beginPos" ) );
    container.append( Py::String( "endLine" ) );
    container.append( Py::String( "endPos" ) );
    return;
}


bool  FragmentBase::getAttribute( const char *  attrName, Py::Object &  retval )
{
    GETINTATTR( kind );
    GETINTATTR( begin );
    GETINTATTR( end );
    GETINTATTR( beginLine );
    GETINTATTR( beginPos );
    GETINTATTR( endLine );
    GETINTATTR( endPos );

    return false;
}


bool  FragmentBase::setAttribute( const char *        attrName,
                                  const Py::Object &  value )
{
    SETINTATTR( kind, value );
    SETINTATTR( begin, value );
    SETINTATTR( end, value );
    SETINTATTR( beginLine, value );
    SETINTATTR( beginPos, value );
    SETINTATTR( endLine, value );
    SETINTATTR( endPos, value );

    return false;
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
    return Py::None();  // Suppress compiler warning
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

#if 0
// TODO: No need anymore?
// Updates the end of the fragment with a new candidate if the new end is
// further than the current
void  FragmentBase::updateEnd( INT_TYPE  otherEnd,
                               INT_TYPE  otherEndLine, INT_TYPE  otherEndPos )
{
    if ( end == -1 || otherEnd > end )
    {
        end = otherEnd;
        endLine = otherEndLine;
        endPos = otherEndPos;
    }
}

// Updates the begin of the fragment if needed
void  FragmentBase::updateBegin( INT_TYPE  otherBegin,
                                 INT_TYPE  otherBeginLine,
                                 INT_TYPE  otherBeginPos )
{
    if ( begin == -1 || otherBegin < begin )
    {
        begin = otherBegin;
        beginLine = otherBeginLine;
        beginPos = otherBeginPos;
    }
}
#endif


void FragmentBase::updateBeginEnd( const FragmentBase *  other )
{
    if ( begin == -1 || other->begin < begin )
    {
        begin = other->begin;
        beginLine = other->beginLine;
        beginPos = other->beginPos;
    }
    if ( end == -1 || other->end > end )
    {
        end = other->end;
        endLine = other->endLine;
        endPos = other->endPos;
    }

    // Spread the change to the upper levels
    if ( parent != NULL )
        parent->updateBeginEnd( other );
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


Py::Object Fragment::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        return members;
    }

    Py::Object      retval;
    if ( getAttribute( attrName, retval ) )
        return retval;
    return getattr_methods( attrName );
}


Py::Object  Fragment::repr( void )
{
    return Py::String( "<Fragment " + asStr() + ">" );
}


int  Fragment::setattr( const char *        attrName,
                        const Py::Object &  val )
{
    if ( setAttribute( attrName, val ) )
        return 0;
    throwUnknownAttribute( attrName );
    return -1;
}

// --- End of Fragment definition ---


FragmentWithComments::FragmentWithComments()
{
    leadingComment = Py::None();
    sideComment = Py::None();
    body = Py::None();
}

FragmentWithComments::~FragmentWithComments()
{}

void FragmentWithComments::appendMembers( Py::List &  container )
{
    container.append( Py::String( "leadingComment" ) );
    container.append( Py::String( "sideComment" ) );
    container.append( Py::String( "body" ) );
    return;
}

bool FragmentWithComments::getAttribute( const char *  attrName,
                                         Py::Object &  retval )
{
    if ( strcmp( attrName, "leadingComment" ) == 0 )
    {
        retval = leadingComment;
        return true;
    }
    if ( strcmp( attrName, "sideComment" ) == 0 )
    {
        retval = sideComment;
        return true;
    }
    if ( strcmp( attrName, "body" ) == 0 )
    {
        retval = body;
        return true;
    }
    return false;
}

bool FragmentWithComments::setAttribute( const char *        attrName,
                                         const Py::Object &  val )
{
    if ( strcmp( attrName, "body" ) == 0 )
    {
        CHECKVALUETYPE( "body", "Fragment" );
        body = val;
        return true;
    }
    if ( strcmp( attrName, "leadingComment" ) == 0 )
    {
        CHECKVALUETYPE( "leadingComment", "Comment" );
        leadingComment = val;
        return true;
    }
    if ( strcmp( attrName, "sideComment" ) == 0 )
    {
        CHECKVALUETYPE( "sideComment", "Comment" );
        sideComment = val;
        return true;
    }
    return false;
}

std::string  FragmentWithComments::asStr( void ) const
{
    std::string     ret;

    if ( body.isNone() )
        ret = ret + "Body: None";
    else
        ret = ret + "Body: " +
              TOFRAGMENT( body )->asStr();

    if ( leadingComment.isNone() )
        ret = ret + "\nLeadingComment: None";
    else
        ret = ret + "\nLeadingComment: " +
              TOFRAGMENT( leadingComment )->asStr();

    if ( sideComment.isNone() )
        ret = ret + "\nSideComment: None";
    else
        ret = ret + "\nSideComment: " +
              TOFRAGMENT( sideComment )->asStr();
    return ret;
}

// --- End of FragmentWithComments definition ---



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


Py::Object BangLine::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        return members;
    }

    Py::Object      retval;
    if ( getAttribute( attrName, retval ) )
        return retval;
    return getattr_methods( attrName );
}


Py::Object  BangLine::repr( void )
{
    return Py::String( "<BangLine " + asStr() + ">" );
}


int  BangLine::setattr( const char *        attrName,
                        const Py::Object &  val )
{
    if ( setAttribute( attrName, val ) )
        return 0;
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
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


Py::Object EncodingLine::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        return members;
    }

    Py::Object      retval;
    if ( getAttribute( attrName, retval ) )
        return retval;
    return getattr_methods( attrName );
}


Py::Object  EncodingLine::repr( void )
{
    return Py::String( "<EncodingLine " + asStr() + ">" );
}


int  EncodingLine::setattr( const char *        attrName,
                            const Py::Object &  val )
{
    if ( setAttribute( attrName, val ) )
        return 0;
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
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


Py::Object Comment::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        members.append( Py::String( "parts" ) );
        return members;
    }

    Py::Object      retval;
    if ( getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "parts" ) == 0 )
        return parts;
    return getattr_methods( attrName );
}


Py::Object  Comment::repr( void )
{
    Py::String      ret( "<Comment " + asStr() );
    for ( Py::List::size_type k( 0 ); k < parts.length(); ++k )
        ret = ret + Py::String( "\n" ) + Py::String( parts[ k ].repr() );
    ret = ret + Py::String( ">" );
    return ret;
}


int  Comment::setattr( const char *        attrName,
                       const Py::Object &  val )
{
    if ( setAttribute( attrName, val ) )
        return 0;

    if ( strcmp( attrName, "parts" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'parts' value "
                                      "must be a list" );
        parts = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}


Py::Object  Comment::getDisplayValue( const Py::Tuple &  args )
{
    size_t          argCount( args.length() );
    std::string     buf;
    std::string *   bufPointer;

    if ( argCount == 0 )
    {
        bufPointer = NULL;
    }
    else if ( argCount == 1 )
    {
        buf = Py::String( args[ 0 ] ).as_std_string();
        bufPointer = & buf;
    }
    else
    {
        throwWrongBufArgument( "getDisplayValue" );
        throw std::exception();     // Suppress compiler warning
    }


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


Py::Object Docstring::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        members.append( Py::String( "parts" ) );
        members.append( Py::String( "sideComment" ) );
        return members;
    }

    Py::Object      retval;
    if ( getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "parts" ) == 0 )
        return parts;
    if ( strcmp( attrName, "sideComment" ) == 0 )
        return sideComment;
    return getattr_methods( attrName );
}


Py::Object  Docstring::repr( void )
{
    Py::String      ret( "<Docstring " + asStr() );
    for ( Py::List::size_type k( 0 ); k < parts.length(); ++k )
        ret = ret + Py::String( "\n" ) + Py::String( parts[ k ].repr() );

    return ret +
           Py::String( "\n" + representFragmentPart( sideComment,
                                                     "SideComment" ) + ">" );
}


int  Docstring::setattr( const char *        attrName,
                         const Py::Object &  val )
{
    if ( setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "parts" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::ValueError( "Attribute 'parts' value "
                                  "must be a list" );
        parts = Py::List( val );
        return 0;
    }
    if ( strcmp( attrName, "sideComment" ) == 0 )
    {
        CHECKVALUETYPE( "sideComment", "Comment" );
        sideComment = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}


Py::Object  Docstring::getDisplayValue( const Py::Tuple &  args )
{
    size_t          argCount( args.length() );
    std::string     buf;
    std::string *   bufPointer;

    if ( argCount == 0 )
    {
        bufPointer = NULL;
    }
    else if ( argCount == 1 )
    {
        buf = Py::String( args[ 0 ] ).as_std_string();
        bufPointer = & buf;
    }
    else
    {
        throwWrongBufArgument( "getDisplayValue" );
        throw std::exception();     // suppress compiler warning
    }

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

    return result + joiner +
           Py::String( "\n" + representFragmentPart( sideComment,
                                                     "SideComment" ) );
}


std::string  Docstring::trimDocstring( const std::string &  docstring )
{
    if (docstring.empty())
        return "";

    // Split lines, expand tabs;
    // Detect the min indent (first line doesn't count)
    size_t                          indent( INT_MAX );
    std::vector< std::string >      lines( splitLines( docstring ) );
    for ( std::vector< std::string >::iterator  k( lines.begin() );
          k != lines.end(); ++k )
    {
        *k = expandTabs( *k );
        if ( k != lines.begin() )
        {
            size_t      strippedSize( strlen( trimStart( k->c_str() ) ) );
            if ( strippedSize > 0 )
                indent = std::min( indent, k->length() - strippedSize );
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

Decorator::Decorator()
{
    kind = DECORATOR_FRAGMENT;
    name = Py::None();
    arguments = Py::None();
}


Decorator::~Decorator()
{}


void Decorator::initType( void )
{
    behaviors().name( "Decorator" );
    behaviors().doc( DECORATOR_DOC );
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


Py::Object Decorator::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "name" ) );
        members.append( Py::String( "arguments" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "name" ) == 0 )
        return name;
    if ( strcmp( attrName, "arguments" ) == 0 )
        return arguments;
    return getattr_methods( attrName );
}


Py::Object  Decorator::repr( void )
{
    return Py::String( "<Decorator " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( name, "Name" ) +
                       "\n" + representFragmentPart( arguments, "Arguments" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}


int  Decorator::setattr( const char *        attrName,
                         const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "name" ) == 0 )
    {
        CHECKVALUETYPE( "name", "Fragment" );
        name = val;
        return 0;
    }
    if ( strcmp( attrName, "arguments" ) == 0 )
    {
        CHECKVALUETYPE( "arguments", "Fragment" );
        arguments = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}


// --- End of Decorator definition ---


CodeBlock::CodeBlock()
{
    kind = CODEBLOCK_FRAGMENT;
}


CodeBlock::~CodeBlock()
{}


void CodeBlock::initType( void )
{
    behaviors().name( "CodeBlock" );
    behaviors().doc( CODEBLOCK_DOC );
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


Py::Object CodeBlock::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    return getattr_methods( attrName );
}


Py::Object  CodeBlock::repr( void )
{
    return Py::String( "<CodeBlock " + FragmentBase::asStr() +
                       "\n" + FragmentWithComments::asStr() + ">" );
}


int  CodeBlock::setattr( const char *        attrName,
                         const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of CodeBlock definition ---


Function::Function()
{
    kind = FUNCTION_FRAGMENT;
    name = Py::None();
    arguments = Py::None();
    docstring = Py::None();
}


Function::~Function()
{}


void Function::initType( void )
{
    behaviors().name( "Function" );
    behaviors().doc( FUNCTION_DOC );
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

Py::Object Function::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "decorators" ) );
        members.append( Py::String( "name" ) );
        members.append( Py::String( "arguments" ) );
        members.append( Py::String( "docstring" ) );
        members.append( Py::String( "suite" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "decorators" ) == 0 )
        return decors;
    if ( strcmp( attrName, "name" ) == 0 )
        return name;
    if ( strcmp( attrName, "arguments" ) == 0 )
        return arguments;
    if ( strcmp( attrName, "docstring" ) == 0 )
        return docstring;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    return getattr_methods( attrName );
}

Py::Object  Function::repr( void )
{
    // TODO: the other members
    return Py::String( "<Function " + FragmentBase::asStr() +
                       "\n" + FragmentWithComments::asStr() + ">" );
}


int  Function::setattr( const char *        attrName,
                        const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "decorators" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'decorators' value "
                                      "must be a list" );
        decors = Py::List( val );
        return 0;
    }
    if ( strcmp( attrName, "name" ) == 0 )
    {
        CHECKVALUETYPE( "name", "Fragment" );
        name = val;
        return 0;
    }
    if ( strcmp( attrName, "arguments" ) == 0 )
    {
        CHECKVALUETYPE( "arguments", "Fragment" );
        arguments = val;
        return 0;
    }
    if ( strcmp( attrName, "docstring" ) == 0 )
    {
        CHECKVALUETYPE( "docstring", "Docstring" );
        docstring = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Function definition ---


Class::Class()
{
    kind = CLASS_FRAGMENT;
    name = Py::None();
    baseClasses = Py::None();
    docstring = Py::None();
}

Class::~Class()
{}

void Class::initType( void )
{
    behaviors().name( "Class" );
    behaviors().doc( CLASS_DOC );
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

Py::Object Class::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "decorators" ) );
        members.append( Py::String( "name" ) );
        members.append( Py::String( "baseClasses" ) );
        members.append( Py::String( "docstring" ) );
        members.append( Py::String( "suite" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "decorators" ) == 0 )
        return decors;
    if ( strcmp( attrName, "name" ) == 0 )
        return name;
    if ( strcmp( attrName, "baseClasses" ) == 0 )
        return baseClasses;
    if ( strcmp( attrName, "docstring" ) == 0 )
        return docstring;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    return getattr_methods( attrName );
}

Py::Object  Class::repr( void )
{
    // TODO: the other members
    return Py::String( "<Class " + FragmentBase::asStr() +
                       "\n" + FragmentWithComments::asStr() + ">" );
}


int  Class::setattr( const char *        attrName,
                     const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "decorators" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'decorators' value "
                                      "must be a list" );
        decors = Py::List( val );
        return 0;
    }
    if ( strcmp( attrName, "name" ) == 0 )
    {
        CHECKVALUETYPE( "name", "Fragment" );
        name = val;
        return 0;
    }
    if ( strcmp( attrName, "baseClasses" ) == 0 )
    {
        CHECKVALUETYPE( "baseClasses", "Fragment" );
        baseClasses = val;
        return 0;
    }
    if ( strcmp( attrName, "docstring" ) == 0 )
    {
        CHECKVALUETYPE( "docstring", "Docstring" );
        docstring = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Class definition ---

Break::Break()
{
    kind = BREAK_FRAGMENT;
}

Break::~Break()
{}

void Break::initType( void )
{
    behaviors().name( "Break" );
    behaviors().doc( BREAK_DOC );
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

Py::Object Break::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    return getattr_methods( attrName );
}

Py::Object  Break::repr( void )
{
    return Py::String( "<Break " + FragmentBase::asStr() +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  Break::setattr( const char *        attrName,
                     const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}


// --- End of Break definition ---

Continue::Continue()
{
    kind = CONTINUE_FRAGMENT;
}

Continue::~Continue()
{}

void Continue::initType( void )
{
    behaviors().name( "Continue" );
    behaviors().doc( CONTINUE_DOC );
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

Py::Object Continue::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    return getattr_methods( attrName );
}

Py::Object  Continue::repr( void )
{
    return Py::String( "<Continue " + FragmentBase::asStr() +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  Continue::setattr( const char *        attrName,
                        const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Continue definition ---

Return::Return()
{
    kind = RETURN_FRAGMENT;
    value = Py::None();
}

Return::~Return()
{}

void Return::initType( void )
{
    behaviors().name( "Return" );
    behaviors().doc( RETURN_DOC );
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

Py::Object Return::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "value" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "value" ) == 0 )
        return value;
    return getattr_methods( attrName );
}

Py::Object  Return::repr( void )
{
    return Py::String( "<Return " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( value, "Value" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  Return::setattr( const char *        attrName,
                      const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "value" ) == 0 )
    {
        CHECKVALUETYPE( "value", "Fragment" );
        value = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Return definition ---

Raise::Raise()
{
    kind = RAISE_FRAGMENT;
    value = Py::None();
}

Raise::~Raise()
{}

void Raise::initType( void )
{
    behaviors().name( "Raise" );
    behaviors().doc( RAISE_DOC );
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

Py::Object Raise::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "value" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "value" ) == 0 )
        return value;
    return getattr_methods( attrName );
}

Py::Object  Raise::repr( void )
{
    return Py::String( "<Raise " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( value, "Value" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  Raise::setattr( const char *        attrName,
                      const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "value" ) == 0 )
    {
        CHECKVALUETYPE( "value", "Fragment" );
        value = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Raise definition ---

Assert::Assert()
{
    kind = ASSERT_FRAGMENT;
    tst = Py::None();
    message = Py::None();
}

Assert::~Assert()
{}

void Assert::initType( void )
{
    behaviors().name( "Assert" );
    behaviors().doc( ASSERT_DOC );
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

Py::Object Assert::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "test" ) );
        members.append( Py::String( "message" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "test" ) == 0 )
        return tst;
    if ( strcmp( attrName, "message" ) == 0 )
        return message;
    return getattr_methods( attrName );
}

Py::Object  Assert::repr( void )
{
    return Py::String( "<Assert " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( tst, "Test" ) +
                       "\n" + representFragmentPart( message, "Message" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  Assert::setattr( const char *        attrName,
                      const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "test" ) == 0 )
    {
        CHECKVALUETYPE( "test", "Fragment" );
        tst = val;
        return 0;
    }
    if ( strcmp( attrName, "message" ) == 0 )
    {
        CHECKVALUETYPE( "message", "Fragment" );
        message = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Assert definition ---

SysExit::SysExit()
{
    kind = SYSEXIT_FRAGMENT;
    arg = Py::None();
}

SysExit::~SysExit()
{}

void SysExit::initType( void )
{
    behaviors().name( "SysExit" );
    behaviors().doc( SYSEXIT_DOC );
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

Py::Object SysExit::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "argument" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "argument" ) == 0 )
        return arg;
    return getattr_methods( attrName );
}

Py::Object  SysExit::repr( void )
{
    return Py::String( "<Assert " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( arg, "Argument" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  SysExit::setattr( const char *        attrName,
                       const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "argument" ) == 0 )
    {
        CHECKVALUETYPE( "argument", "Fragment" );
        arg = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}


// --- End of SysExit definition ---

While::While()
{
    kind = WHILE_FRAGMENT;
    condition = Py::None();
    elsePart = Py::None();
}

While::~While()
{}

void While::initType( void )
{
    behaviors().name( "While" );
    behaviors().doc( WHILE_DOC );
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

Py::Object While::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "condition" ) );
        members.append( Py::String( "suite" ) );
        members.append( Py::String( "elsePart" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "condition" ) == 0 )
        return condition;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    if ( strcmp( attrName, "elsePart" ) == 0 )
        return elsePart;
    return getattr_methods( attrName );
}

Py::Object  While::repr( void )
{
    // TODO: the other members
    return Py::String( "<While " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( condition, "Condition" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  While::setattr( const char *        attrName,
                     const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "condition" ) == 0 )
    {
        CHECKVALUETYPE( "condition", "Fragment" );
        condition = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    if ( strcmp( attrName, "elsePart" ) == 0 )
    {
        CHECKVALUETYPE( "elsePart", "IfPart" );
        elsePart = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}


// --- End of While definition ---

For::For()
{
    kind = FOR_FRAGMENT;
    iteration = Py::None();
    elsePart = Py::None();
}

For::~For()
{}

void For::initType( void )
{
    behaviors().name( "For" );
    behaviors().doc( FOR_DOC );
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

Py::Object For::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "iteration" ) );
        members.append( Py::String( "suite" ) );
        members.append( Py::String( "elsePart" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "iteration" ) == 0 )
        return iteration;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    if ( strcmp( attrName, "elsePart" ) == 0 )
        return elsePart;
    return getattr_methods( attrName );
}

Py::Object  For::repr( void )
{
    // TODO: the other members
    return Py::String( "<For " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( iteration, "Iteration" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  For::setattr( const char *        attrName,
                   const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "iteration" ) == 0 )
    {
        CHECKVALUETYPE( "iteration", "Fragment" );
        iteration = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    if ( strcmp( attrName, "elsePart" ) == 0 )
    {
        CHECKVALUETYPE( "elsePart", "IfPart" );
        elsePart = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of For definition ---

Import::Import()
{
    kind = IMPORT_FRAGMENT;
    fromPart = Py::None();
    whatPart = Py::None();
}

Import::~Import()
{}

void Import::initType( void )
{
    behaviors().name( "Import" );
    behaviors().doc( IMPORT_DOC );
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

Py::Object Import::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "fromPart" ) );
        members.append( Py::String( "whatPart" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "fromPart" ) == 0 )
        return fromPart;
    if ( strcmp( attrName, "whatPart" ) == 0 )
        return whatPart;
    return getattr_methods( attrName );
}

Py::Object  Import::repr( void )
{
    return Py::String( "<Import " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( fromPart, "FromPart" ) +
                       "\n" + representFragmentPart( whatPart, "WhatPart" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  Import::setattr( const char *        attrName,
                      const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "fromPart" ) == 0 )
    {
        CHECKVALUETYPE( "fromPart", "Fragment" );
        fromPart = val;
        return 0;
    }
    if ( strcmp( attrName, "whatPart" ) == 0 )
    {
        CHECKVALUETYPE( "whatPart", "Fragment" );
        whatPart = val;
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Import definition ---

IfPart::IfPart()
{
    kind = IF_PART_FRAGMENT;
    condition = Py::None();
}

IfPart::~IfPart()
{}

void IfPart::initType( void )
{
    behaviors().name( "IfPart" );
    behaviors().doc( IFPART_DOC );
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

Py::Object IfPart::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "condition" ) );
        members.append( Py::String( "suite" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "condition" ) == 0 )
        return condition;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    return getattr_methods( attrName );
}

Py::Object  IfPart::repr( void )
{
    // TODO: the other members
    return Py::String( "<IfPart " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( condition, "Condition" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  IfPart::setattr( const char *        attrName,
                      const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "condition" ) == 0 )
    {
        CHECKVALUETYPE( "condition", "Fragment" );
        condition = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of IfPart definition ---

If::If()
{
    kind = IF_FRAGMENT;
}

If::~If()
{}

void If::initType( void )
{
    behaviors().name( "If" );
    behaviors().doc( IF_DOC );
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

Py::Object If::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        members.append( Py::String( "parts" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "parts" ) == 0 )
        return parts;
    return getattr_methods( attrName );
}

Py::Object  If::repr( void )
{
    // TODO: the other members
    return Py::String( "<If " + FragmentBase::asStr() +
                       "\n" + ">" );
}

int  If::setattr( const char *        attrName,
                  const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "parts" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'parts' value "
                                      "must be a list" );
        parts = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of If definition ---

With::With()
{
    kind = WITH_FRAGMENT;
    object = Py::None();
}

With::~With()
{}

void With::initType( void )
{
    behaviors().name( "With" );
    behaviors().doc( WITH_DOC );
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

Py::Object With::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "object" ) );
        members.append( Py::String( "suite" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "object" ) == 0 )
        return object;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    return getattr_methods( attrName );
}

Py::Object  With::repr( void )
{
    // TODO: the other members
    return Py::String( "<With " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( object, "Object" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  With::setattr( const char *        attrName,
                    const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "object" ) == 0 )
    {
        CHECKVALUETYPE( "object", "Fragment" );
        object = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of With definition ---

ExceptPart::ExceptPart()
{
    kind = EXCEPT_PART_FRAGMENT;
    exceptionType = Py::None();
    variable = Py::None();
}

ExceptPart::~ExceptPart()
{}

void ExceptPart::initType( void )
{
    behaviors().name( "ExceptPart" );
    behaviors().doc( EXCEPTPART_DOC );
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

Py::Object ExceptPart::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "exceptionType" ) );
        members.append( Py::String( "variable" ) );
        members.append( Py::String( "suite" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "exceptionType" ) == 0 )
        return exceptionType;
    if ( strcmp( attrName, "variable" ) == 0 )
        return variable;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    return getattr_methods( attrName );
}

Py::Object  ExceptPart::repr( void )
{
    // TODO: the other members
    return Py::String( "<ExceptPart " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( exceptionType, "ExceptionType" ) +
                       "\n" + representFragmentPart( variable, "variable" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  ExceptPart::setattr( const char *        attrName,
                          const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "exceptionType" ) == 0 )
    {
        CHECKVALUETYPE( "exceptionType", "Fragment" );
        exceptionType = val;
        return 0;
    }
    if ( strcmp( attrName, "variable" ) == 0 )
    {
        CHECKVALUETYPE( "variable", "Fragment" );
        variable = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of ExceptPart definition ---

Try::Try()
{
    kind = TRY_FRAGMENT;
    finallyPart = Py::None();
}

Try::~Try()
{}

void Try::initType( void )
{
    behaviors().name( "Try" );
    behaviors().doc( TRY_DOC );
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

Py::Object Try::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        FragmentWithComments::appendMembers( members );
        members.append( Py::String( "exceptParts" ) );
        members.append( Py::String( "finallyPart" ) );
        members.append( Py::String( "suite" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( FragmentWithComments::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "exceptParts" ) == 0 )
        return exceptParts;
    if ( strcmp( attrName, "finallyPart" ) == 0 )
        return finallyPart;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    return getattr_methods( attrName );
}

Py::Object  Try::repr( void )
{
    // TODO: the other members
    return Py::String( "<Try " + FragmentBase::asStr() +
                       "\n" + representFragmentPart( finallyPart, "finallyPart" ) +
                       "\n" + FragmentWithComments::asStr() + ">" );
}

int  Try::setattr( const char *        attrName,
                   const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( FragmentWithComments::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "exceptParts" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'exceptParts' value "
                                      "must be a list" );
        exceptParts = val;
        return 0;
    }
    if ( strcmp( attrName, "finallyPart" ) == 0 )
    {
        CHECKVALUETYPE( "finallyPart", "Fragment" );
        finallyPart = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}

// --- End of Try definition ---

ControlFlow::ControlFlow()
{
    kind = CONTROL_FLOW_FRAGMENT;

    bangLine = Py::None();
    encodingLine = Py::None();
    docstring = Py::None();
    isOK = true;
}

ControlFlow::~ControlFlow()
{
    delete content;
    content = NULL;
}

void ControlFlow::initType( void )
{
    behaviors().name( "ControlFlow" );
    behaviors().doc( CONTROLFLOW_DOC );
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

Py::Object ControlFlow::getattr( const char *  attrName )
{
    // Support for dir(...)
    if ( strcmp( attrName, "__members__" ) == 0 )
    {
        Py::List    members;
        FragmentBase::appendMembers( members );
        members.append( Py::String( "bangLine" ) );
        members.append( Py::String( "encodingLine" ) );
        members.append( Py::String( "docstring" ) );
        members.append( Py::String( "suite" ) );
        members.append( Py::String( "isOK" ) );
        members.append( Py::String( "errors" ) );
        return members;
    }

    Py::Object      retval;
    if ( FragmentBase::getAttribute( attrName, retval ) )
        return retval;
    if ( strcmp( attrName, "bangLine" ) == 0 )
        return bangLine;
    if ( strcmp( attrName, "encodingLine" ) == 0 )
        return encodingLine;
    if ( strcmp( attrName, "docstring" ) == 0 )
        return docstring;
    if ( strcmp( attrName, "suite" ) == 0 )
        return nsuite;
    if ( strcmp( attrName, "isOK" ) == 0 )
        return Py::Boolean( isOK );
    if ( strcmp( attrName, "errors" ) == 0 )
        return errors;
    return getattr_methods( attrName );
}

Py::Object  ControlFlow::repr( void )
{
    std::string     ok( "true" );
    if ( !isOK )
        ok = "false";

    std::string     errorsPart;
    if ( errors.size() == 0 )
        errorsPart = "n/a";
    else
    {
        for ( size_t  k = 0; k < errors.size(); ++k )
        {
            if ( k != 0 )
                errorsPart += "\n";
            errorsPart += errors[ k ].str();
        }
    }

    std::string     suitePart;
    if ( nsuite.size() == 0 )
        suitePart = "n/a";
    else
        for ( size_t  k = 0; k < nsuite.size(); ++k )
        {
            if ( k != 0 )
                suitePart += "\n";
            suitePart += nsuite[ k ].str();
        }

    return Py::String( "<ControlFlow " + FragmentBase::asStr() +
                       "\nisOK: " + ok +
                       "\nErrors: " + errorsPart +
                       "\n" + representFragmentPart( bangLine, "BangLine" ) +
                       "\n" + representFragmentPart( encodingLine, "EncodingLine" ) +
                       "\n" + representFragmentPart( docstring, "Docstring" ) +
                       "\nSuite: " + suitePart +
                       ">" );
}

int  ControlFlow::setattr( const char *        attrName,
                           const Py::Object &  val )
{
    if ( FragmentBase::setAttribute( attrName, val ) )
        return 0;
    if ( strcmp( attrName, "bangLine" ) == 0 )
    {
        CHECKVALUETYPE( "bangLine", "BangLine" );
        bangLine = val;
        return 0;
    }
    if ( strcmp( attrName, "encodingLine" ) == 0 )
    {
        CHECKVALUETYPE( "encodingLine", "EncodingLine" );
        encodingLine = val;
        return 0;
    }
    if ( strcmp( attrName, "docstring" ) == 0 )
    {
        CHECKVALUETYPE( "docstring", "Docstring" );
        docstring = val;
        return 0;
    }
    if ( strcmp( attrName, "suite" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'suite' value "
                                      "must be a list" );
        nsuite = Py::List( val );
        return 0;
    }
    if ( strcmp( attrName, "isOK" ) == 0 )
    {
        if ( ! val.isBoolean() )
            throw Py::AttributeError( "Attribute 'isOK' value "
                                      "must be a boolean" );
        isOK = (bool)(Py::Boolean( val ));
        return 0;
    }
    if ( strcmp( attrName, "errors" ) == 0 )
    {
        if ( ! val.isList() )
            throw Py::AttributeError( "Attribute 'errors' value "
                                      "must be a list" );
        errors = Py::List( val );
        return 0;
    }
    throwUnknownAttribute( attrName );
    return -1;  // Suppress compiler warning
}


