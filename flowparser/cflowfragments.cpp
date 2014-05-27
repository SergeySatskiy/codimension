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


#include "cflowfragments.hpp"
#include "cflowfragmenttypes.hpp"
#include "cflowversion.hpp"
#include "cflowdocs.hpp"


// Convenience macros
#define GETINTATTR( member )                        \
    do { if ( strcmp( name, STR( member ) ) == 0 )  \
        return Py::Long( member ); } while ( 0 )
#define GETBOOLATTR( member )                       \
    do { if ( strcmp( name, STR( member ) ) == 0 )  \
        return Py::Boolean( member ); } while ( 0 )




Py::List    FragmentBase::members;

FragmentBase::FragmentBase() :
    parent( NULL ),
    kind( UNDEFINED_FRAGMENT ),
    begin( -1 ), end( -1 ), beginLine( -1 ), beginPos( -1 ),
    endLine( -1 ), endPos( -1 ), serialized( false )
{}


FragmentBase::~FragmentBase()
{}


void FragmentBase::Init( void )
{
    members.append( Py::String( "kind" ) );
    members.append( Py::String( "begin" ) );
    members.append( Py::String( "end" ) );
    members.append( Py::String( "beginLine" ) );
    members.append( Py::String( "beginPos" ) );
    members.append( Py::String( "endLine" ) );
    members.append( Py::String( "endPos" ) );
    members.append( Py::String( "serialized" ) );
    return;
}


Py::List    FragmentBase::getMembers( void ) const
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
    GETBOOLATTR( serialized );

    return Py::None();
}



// -----------------------------

Fragment::Fragment()
{
    kind = FRAGMENT;
}


Fragment::~Fragment()
{}


void Fragment::InitType( void )
{
    behaviors().name( "Fragment" );
    behaviors().doc( FRAGMENT_DOC );
    behaviors().supportGetattr();
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


