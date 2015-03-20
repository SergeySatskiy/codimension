//-----------------------------------------------------------------------------
//
// Copyright (c) 1998 - 2007, The Regents of the University of California
// Produced at the Lawrence Livermore National Laboratory
// All rights reserved.
//
// This file is part of PyCXX. For details,see http://cxx.sourceforge.net/. The
// full copyright notice is contained in the file COPYRIGHT located at the root
// of the PyCXX distribution.
//
// Redistribution  and  use  in  source  and  binary  forms,  with  or  without
// modification, are permitted provided that the following conditions are met:
//
//  - Redistributions of  source code must  retain the above  copyright notice,
//    this list of conditions and the disclaimer below.
//  - Redistributions in binary form must reproduce the above copyright notice,
//    this  list of  conditions  and  the  disclaimer (as noted below)  in  the
//    documentation and/or materials provided with the distribution.
//  - Neither the name of the UC/LLNL nor  the names of its contributors may be
//    used to  endorse or  promote products derived from  this software without
//    specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT  HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR  IMPLIED WARRANTIES, INCLUDING,  BUT NOT  LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND  FITNESS FOR A PARTICULAR  PURPOSE
// ARE  DISCLAIMED.  IN  NO  EVENT  SHALL  THE  REGENTS  OF  THE  UNIVERSITY OF
// CALIFORNIA, THE U.S.  DEPARTMENT  OF  ENERGY OR CONTRIBUTORS BE  LIABLE  FOR
// ANY  DIRECT,  INDIRECT,  INCIDENTAL,  SPECIAL,  EXEMPLARY,  OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT  LIMITED TO, PROCUREMENT OF  SUBSTITUTE GOODS OR
// SERVICES; LOSS OF  USE, DATA, OR PROFITS; OR  BUSINESS INTERRUPTION) HOWEVER
// CAUSED  AND  ON  ANY  THEORY  OF  LIABILITY,  WHETHER  IN  CONTRACT,  STRICT
// LIABILITY, OR TORT  (INCLUDING NEGLIGENCE OR OTHERWISE)  ARISING IN ANY  WAY
// OUT OF THE  USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
// DAMAGE.
//
//-----------------------------------------------------------------------------

#ifdef _MSC_VER
// disable warning C4786: symbol greater than 255 character,
// nessesary to ignore as <map> causes lots of warning
#pragma warning( disable: 4786 )
#endif

#include "range.hxx"
// Connect range objects to Python

range::range( long start, long stop, long step )
: Py::PythonExtension<range>()
, m_start( start )
, m_stop( stop )
, m_step( step )
{
    std::cout   << "range object created " << this
                << " " << asString() << std::endl;
}

range::~range()
{
    std::cout << "range object destroyed " << this << std::endl;
}

long range::length() const
{
    return (m_stop - m_start + 1)/m_step;
}

long range::item( int i ) const
{
    if( i >= length() )
        // this exception stops a Python for loop over range.
        throw Py::IndexError("index too large");

    return m_start + i * m_step;
}

range *range::slice( int i, int j ) const
{
    int first = m_start + i * m_step;
    int last = m_start + j * m_step;
    return new range( first, last, m_step );
}

range *range::extend( int k ) const
{
    return new range( m_start, m_stop + k, m_step);      
}

std::string range::asString() const
{
    std::OSTRSTREAM s;
    s << "range(" << m_start << ", " << m_stop << ", " << m_step << ")" << std::ends;

    return std::string( s.str() );
}

Py::Object range::reference_count( const Py::Tuple &args )
{
    return Py::Long( ob_refcnt );
}

Py::Object range::c_value(const Py::Tuple&) const
{
    Py::List result;
    for( int i = m_start; i <= m_stop; i += m_step )
    {
        result.append( Py::Long(i) );
    }

    return result;
}

void range::c_assign( const Py::Tuple &, const Py::Object &rhs )
{
    Py::Tuple w( rhs );
    w.verify_length( 3 );
    m_start = Py::Long( w[0] ).as_long();
    m_stop = Py::Long( w[1] ).as_long();
    m_step = Py::Long( w[2] ).as_long();
}

Py::Object range::repr()
{
    return Py::String( asString() );
}

int range::sequence_length()
{
    return length();
}

Py::Object range::sequence_item( Py_ssize_t i ) 
{
    return Py::Long( item( i ) );
}

Py::Object range::sequence_concat( const Py::Object &j )
{
    Py::Long k( j );
    return Py::asObject( extend( k.as_long() ) );
}

Py::Object range::sequence_slice( Py_ssize_t i, Py_ssize_t j )
{
    return Py::asObject( slice( i, j ) );
}


Py::Object range::getattr( const char *name )
{
    if( std::string( name ) == "c" )
        return Py::Float( 300.0 );

    if( std::string( name ) == "start" )
        return Py::Long( m_start );

    return getattr_methods( name );
}

// "regular" methods...
Py::Object range::amethod( const Py::Tuple &t ) 
{
    t.verify_length( 1 );
    Py::List result;
    result.append( Py::Object( this ) );
    result.append( t[0] );

    return result;
}

Py::Object range::value( const Py::Tuple &t )
{
    return c_value( t );
}

Py::Object range::assign( const Py::Tuple &t ) 
{
    t.verify_length( 2 );

    Py::Tuple t1( t[0] ); // subscripts
    Py::Object o2( t[1] ); // rhs;
    c_assign ( t1, o2 );

    return Py::None();
}

void range::init_type()
{
    behaviors().name( "range" );
    behaviors().doc( "range objects: start, stop, step" );
    behaviors().supportRepr();
    behaviors().supportGetattr();
    behaviors().supportSequenceType();

    add_varargs_method( "amethod", &range::amethod, "demonstrate how to document amethod" );
    add_varargs_method( "assign", &range::assign );
    add_varargs_method( "value", &range::value );
    add_varargs_method( "reference_count", &range::reference_count );
}
