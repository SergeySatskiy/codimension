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

#include "CXX/Extensions.hxx"
#include "range.hxx"
#include "test_assert.hxx"

// This test also illustrates using the Py namespace explicitly

void test_extension_object() 
{
    Py::List a; // just something that is not a range...

    Py::ExtensionObject<range> r1( new range( 1, 20, 3 ) );
    test_assert( "extension object check() incompatible", false, range::check( a ) );
    test_assert( "extension object check() incompatible", true, range::check( r1 ) );

    RangeSequence r2( 1, 10, 2 );
    test_assert( "extension object index", r2[ 1 ], Py::Long( 3 ) );

    // calling an extension object method using getattr
    Py::Callable w( r2.getAttr( "amethod" ) );
    {
    Py::Tuple args( 1 );
    Py::Long j( 3 );
    args[0] = j;
    Py::List answer( w.apply( args ) );

    test_assert( "extension object amethod 1 q1", answer[0], r2 );
    test_assert( "extension object amethod 1q2", answer[1], args[0] );
    }

    {
    // calling an extension object method using callMemberFunction
    Py::Tuple args( 1 );
    Py::Long j( 3 );
    args[0] = j;
    Py::List answer( r2.callMemberFunction( "amethod", args ) );

    test_assert( "extension object amethod 2 q1", answer[0], r2 );
    test_assert( "extension object amethod 2 q2", answer[1], args[0] );
    }

    Py::Tuple nv( 3 );
    nv[0] = Py::Long( 1 );
    nv[1] = Py::Long( 20 );
    nv[2] = Py::Long( 3 );
    Py::Tuple unused;
    Py::List r2value;
    r2.assign( unused, nv );
    r2value = r2.value( unused );

    test_assert( "extension object q3", r2value[1], Py::Long( 4 ) );

    // repeat using getattr
    w = r2.getAttr( "assign" );
    Py::Tuple the_arguments( 2 );
    the_arguments[0] = unused;
    the_arguments[1] = nv;
    w.apply( the_arguments );


    {
        Py::ExtensionObject<range> rheap( new range( 1, 10, 2 ) );

        // delete rheap
    }

    w = r2.getAttr( "value" );
    Py::Tuple one_arg( 1 );
    one_arg[0] = unused;
    r2value = w.apply( one_arg );
    test_assert( "extension object q4", r2value[1], Py::Long( 4 ) );
}
