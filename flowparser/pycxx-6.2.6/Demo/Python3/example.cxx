//-----------------------------------------------------------------------------
//
// Copyright (c) 1998 - 2007, The Regents of the University of California
// Produced at the Lawrence Livermore National Laboratory
// All rights reserved.
//
// This file is part of PyCXX. For details, see http://cxx.sourceforge.net. The
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
#pragma warning(disable: 4786)
#endif

#include "CXX/Objects.hxx"
#include "CXX/Extensions.hxx"

#include <assert.h>

#include "range.hxx"  // Extension object
#include "test_assert.hxx"

extern void test_extension_object();

#include <algorithm>

void test_compare()
{
    test_assert( "compare == true", true, Py::Long( 100 ) == Py::Long( 100 ) );
    test_assert( "compare == false", false, Py::Long( 100 ) == Py::Long( 101 ) );

    test_assert( "compare != true", true, Py::Long( 100 ) != Py::Long( 101 ) );
    test_assert( "compare != false", false, Py::Long( 100 ) != Py::Long( 100 ) );

    test_assert( "compare < true", true, Py::Long( 100 ) < Py::Long( 101 ) );
    test_assert( "compare < false", false, Py::Long( 100 ) < Py::Long( 99 ) );

    test_assert( "compare <= true", true, Py::Long( 100 ) <= Py::Long( 101 ) );
    test_assert( "compare <= true", true, Py::Long( 100 ) <= Py::Long( 100 ) );
    test_assert( "compare <= false", false, Py::Long( 100 ) <= Py::Long( 99 ) );

    test_assert( "compare > true", true, Py::Long( 100 ) > Py::Long( 99 ) );
    test_assert( "compare > false", false, Py::Long( 100 ) > Py::Long( 101 ) );

    test_assert( "compare >= true", true, Py::Long( 100 ) >= Py::Long( 99 ) );
    test_assert( "compare >= true", true, Py::Long( 100 ) >= Py::Long( 100 ) );
    test_assert( "compare >= false", false, Py::Long( 100 ) >= Py::Long( 101 ) );

    test_assert( "compare == true", true, Py::Float( 100 ) == Py::Float( 100 ) );
    test_assert( "compare == false", false, Py::Float( 100 ) == Py::Float( 101 ) );

    test_assert( "compare != true", true, Py::Float( 100 ) != Py::Float( 101 ) );
    test_assert( "compare != false", false, Py::Float( 100 ) != Py::Float( 100 ) );

    test_assert( "compare < true", true, Py::Float( 100 ) < Py::Float( 101 ) );
    test_assert( "compare < false", false, Py::Float( 100 ) < Py::Float( 99 ) );

    test_assert( "compare <= true", true, Py::Float( 100 ) <= Py::Float( 101 ) );
    test_assert( "compare <= true", true, Py::Float( 100 ) <= Py::Float( 100 ) );
    test_assert( "compare <= false", false, Py::Float( 100 ) <= Py::Float( 99 ) );

    test_assert( "compare > true", true, Py::Float( 100 ) > Py::Float( 99 ) );
    test_assert( "compare > false", false, Py::Float( 100 ) > Py::Float( 101 ) );

    test_assert( "compare >= true", true, Py::Float( 100 ) >= Py::Float( 99 ) );
    test_assert( "compare >= true", true, Py::Float( 100 ) >= Py::Float( 100 ) );
    test_assert( "compare >= false", false, Py::Float( 100 ) >= Py::Float( 101 ) );
}

void test_String()
{
    Py::String s( "hello" );
    Py::Char blank = ' ';
    Py::String r1( "world in brief", 5 );

    s = s + blank + r1;
    test_assert( "string concat", s, "hello world" );

    s = s * 2;
    test_assert( "string multiple", s, "hello worldhello world" );

    // test conversion
    std::string w = static_cast<std::string>( s );
    std::string w2 = s;

    test_assert( "string convert to std::string", w, w2 );

    Py::String r2( "12345 789" );
    Py::Char c6 = r2[5];
    test_assert( "string convert to std::string", c6, blank );

    Py::Char c7 = r2.front();
    Py::Char c8 = r2.back();
}

void test_boolean()
{
    Py::Object o;
    Py::Boolean pb1;
    Py::Boolean pb2;
    Py::String st1;
    Py::Long int1;
    bool b1;

    // True tests
    o = Py::True();
    test_assert( "boolean Py::True", o.isTrue(), true );

    pb1 = o;
    test_assert( "boolean true pybool var ", pb1 ? true : false, true );

    b1 = pb1;
    test_assert( "boolean true bool = pybool", pb1 ? true : false, true );

    pb2 = pb1;
    test_assert( "boolean true pybool = pybool", pb2 ? true : false, true );

    pb2 = true;
    test_assert( "boolean true pybool = true", pb2 ? true : false, true );

    test_assert( "boolean operator bool true", true, bool( pb2 ) );

    // False tests
    o = Py::False();
    test_assert( "boolean Py::False", o.isTrue(), false );

    pb1 = o;
    test_assert( "boolean false pybool var ", pb1 ? true : false, false );

    b1 = pb1;
    test_assert( "boolean false bool = pybool", pb1 ? true : false, false );

    pb2 = pb1;
    test_assert( "boolean false pybool = pybool", pb2 ? true : false, false );

    pb2 = false;
    test_assert( "boolean false pybool = false", pb2 ? true : false, false );

    test_assert( "boolean operator bool false", false, bool( pb2 ) );

    // conversion tests
    int1 = 0;
    pb1 = int1;
    test_assert( "boolean int 0", pb1 ? true : false, false );
    int1 = 99;
    pb1 = int1;
    test_assert( "boolean int 99", pb1 ? true : false, true );

    st1 = "";
    pb1 = st1;
    test_assert( "boolean string \"\"", pb1 ? true : false, false );
    st1 = "x";
    pb1 = st1;
    test_assert( "boolean string \"x\"", pb1 ? true : false, true );
}

void test_long()
{
    long cxx_long1( 100 );
    long cxx_long2( 0 );
    long cxx_long3( 0 );
    Py::Long py_long1( 100 );
    Py::Long py_long2( 0 );
    Py::Long py_long3( 0 );

    test_assert( "long constructor", cxx_long1, py_long1.as_long() );

    cxx_long2 = cxx_long1++;
    py_long2 = py_long1++;
    test_assert( "long num++", cxx_long2, py_long2.as_long() );

    cxx_long2 = ++cxx_long1;
    py_long2 = ++py_long1;
    test_assert( "long ++num", cxx_long2, py_long2.as_long() );

    cxx_long2 = cxx_long1--;
    py_long2 = py_long1--;
    test_assert( "long num--", cxx_long2, py_long2.as_long() );

    cxx_long2 = --cxx_long1;
    py_long2 = --py_long1;
    test_assert( "long --num", cxx_long2, py_long2.as_long() );

    cxx_long1 = 1000;
    py_long1 = 1000;
    test_assert( "long num =", cxx_long1, py_long1.as_long() );

    // comparison tests
    cxx_long1 = 2;
    cxx_long2 = 3;
    cxx_long3 = 3;
    py_long1 = cxx_long1;
    py_long2 = cxx_long2;
    py_long3 = cxx_long3;
   

    // ------------------------------------------------------------
    test_assert( "long operator ==", cxx_long2 == cxx_long3, py_long2  == py_long3 );
    test_assert( "long operator ==", cxx_long2 == cxx_long3, cxx_long2 == py_long3 );
    test_assert( "long operator ==", cxx_long2 == cxx_long3, py_long2  == cxx_long3 );

    test_assert( "long operator ==", cxx_long1 == cxx_long3, py_long1  == py_long3 );
    test_assert( "long operator ==", cxx_long1 == cxx_long3, cxx_long1 == py_long3 );
    test_assert( "long operator ==", cxx_long1 == cxx_long3, py_long1  == cxx_long3 );

    // ------------------------------------------------------------
    test_assert( "long operator !=", cxx_long1 != cxx_long2, py_long1  != py_long2 );
    test_assert( "long operator !=", cxx_long1 != cxx_long2, cxx_long1 != py_long2 );
    test_assert( "long operator !=", cxx_long1 != cxx_long2, py_long1  != cxx_long2 );

    test_assert( "long operator !=", cxx_long2 != cxx_long3, py_long2  != py_long3 );
    test_assert( "long operator !=", cxx_long2 != cxx_long3, cxx_long2 != py_long3 );
    test_assert( "long operator !=", cxx_long2 != cxx_long3, py_long2  != cxx_long3 );

    // ------------------------------------------------------------
    test_assert( "long operator < ", cxx_long1 <  cxx_long2, py_long1  <  py_long2 );
    test_assert( "long operator < ", cxx_long1 <  cxx_long2, cxx_long1 <  py_long2 );
    test_assert( "long operator < ", cxx_long1 <  cxx_long2, py_long1  <  cxx_long2 );

    test_assert( "long operator < ", cxx_long2 <  cxx_long1, py_long2  <  py_long1 );
    test_assert( "long operator < ", cxx_long2 <  cxx_long1, cxx_long2 <  py_long1 );
    test_assert( "long operator < ", cxx_long2 <  cxx_long1, py_long2  <  cxx_long1 );

    // ------------------------------------------------------------
    test_assert( "long operator > ", cxx_long2 >  cxx_long1, py_long2  >  py_long1 );
    test_assert( "long operator > ", cxx_long2 >  cxx_long1, cxx_long2 >  py_long1 );
    test_assert( "long operator > ", cxx_long2 >  cxx_long1, py_long2  >  cxx_long1 );

    test_assert( "long operator > ", cxx_long1 >  cxx_long2, py_long1  >  py_long2 );
    test_assert( "long operator > ", cxx_long1 >  cxx_long2, cxx_long1 >  py_long2 );
    test_assert( "long operator > ", cxx_long1 >  cxx_long2, py_long1  >  cxx_long2 );

    // ------------------------------------------------------------
    test_assert( "long operator <=", cxx_long1 <= cxx_long2, py_long1  <= py_long2 );
    test_assert( "long operator <=", cxx_long1 <= cxx_long2, cxx_long1 <= py_long2 );
    test_assert( "long operator <=", cxx_long1 <= cxx_long2, py_long1  <= cxx_long2 );

    test_assert( "long operator <=", cxx_long2 <= cxx_long3, py_long2  <= py_long3 );
    test_assert( "long operator <=", cxx_long2 <= cxx_long3, cxx_long2 <= py_long3 );
    test_assert( "long operator <=", cxx_long2 <= cxx_long3, py_long2  <= cxx_long3 );

    test_assert( "long operator <=", cxx_long2 <= cxx_long1, py_long2  <= py_long1 );
    test_assert( "long operator <=", cxx_long2 <= cxx_long1, cxx_long2 <= py_long1 );
    test_assert( "long operator <=", cxx_long2 <= cxx_long1, py_long2  <= cxx_long1 );

    // ------------------------------------------------------------
    test_assert( "long operator >=", cxx_long2 >= cxx_long1, py_long2  >= py_long1 );
    test_assert( "long operator >=", cxx_long2 >= cxx_long1, cxx_long2 >= py_long1 );
    test_assert( "long operator >=", cxx_long2 >= cxx_long1, py_long2  >= cxx_long1 );

    test_assert( "long operator >=", cxx_long2 >= cxx_long3, py_long2  >= py_long3 );
    test_assert( "long operator >=", cxx_long2 >= cxx_long3, cxx_long2 >= py_long3 );
    test_assert( "long operator >=", cxx_long2 >= cxx_long3, py_long2  >= cxx_long3 );

    test_assert( "long operator >=", cxx_long1 >= cxx_long2, py_long1  >= py_long2 );
    test_assert( "long operator >=", cxx_long1 >= cxx_long2, cxx_long1 >= py_long2 );
    test_assert( "long operator >=", cxx_long1 >= cxx_long2, py_long1  >= cxx_long2 );

    // ------------------------------------------------------------
    test_assert( "long operator long", cxx_long2, long( py_long2 ) );
    test_assert( "long operator int", int( cxx_long2 ), int( py_long2 ) );
}

void test_float()
{
    double cxx_float1( 100 );
    double cxx_float2( 0 );
    double cxx_float3( 0 );
    Py::Float py_float1( 100.0 );
    Py::Float py_float2( 0.0 );
    Py::Float py_float3( 0.0 );

    test_assert( "float constructor", cxx_float1, py_float1.as_double() );

    cxx_float1 = 1000;
    py_float1 = 1000;
    test_assert( "float num =", cxx_float1, py_float1.as_double() );

    // comparison tests
    cxx_float1 = 2;
    cxx_float2 = 3;
    cxx_float3 = 3;
    py_float1 = cxx_float1;
    py_float2 = cxx_float2;
    py_float3 = cxx_float3;

    //------------------------------------------------------------   
    test_assert( "float operator ==", cxx_float2 == cxx_float3, py_float2  == py_float3 );
    test_assert( "float operator ==", cxx_float2 == cxx_float3, cxx_float2 == py_float3 );
    test_assert( "float operator ==", cxx_float2 == cxx_float3, py_float2  == cxx_float3 );

    test_assert( "float operator ==", cxx_float1 == cxx_float3, py_float1  == py_float3 );
    test_assert( "float operator ==", cxx_float1 == cxx_float3, cxx_float1 == py_float3 );
    test_assert( "float operator ==", cxx_float1 == cxx_float3, py_float1  == cxx_float3 );

    //------------------------------------------------------------   
    test_assert( "float operator !=", cxx_float1 != cxx_float2, py_float1  != py_float2 );
    test_assert( "float operator !=", cxx_float1 != cxx_float2, cxx_float1 != py_float2 );
    test_assert( "float operator !=", cxx_float1 != cxx_float2, py_float1  != cxx_float2 );

    test_assert( "float operator !=", cxx_float2 != cxx_float3, py_float2  != py_float3 );
    test_assert( "float operator !=", cxx_float2 != cxx_float3, cxx_float2 != py_float3 );
    test_assert( "float operator !=", cxx_float2 != cxx_float3, py_float2  != cxx_float3 );

    //------------------------------------------------------------   
    test_assert( "float operator < ", cxx_float1 <  cxx_float2, py_float1  <  py_float2 );
    test_assert( "float operator < ", cxx_float1 <  cxx_float2, cxx_float1 <  py_float2 );
    test_assert( "float operator < ", cxx_float1 <  cxx_float2, py_float1  <  cxx_float2 );

    test_assert( "float operator < ", cxx_float2 <  cxx_float1, py_float2  <  py_float1 );
    test_assert( "float operator < ", cxx_float2 <  cxx_float1, cxx_float2 <  py_float1 );
    test_assert( "float operator < ", cxx_float2 <  cxx_float1, py_float2  <  cxx_float1 );

    //------------------------------------------------------------   
    test_assert( "float operator > ", cxx_float2 >  cxx_float1, py_float2  >  py_float1 );
    test_assert( "float operator > ", cxx_float2 >  cxx_float1, cxx_float2 >  py_float1 );
    test_assert( "float operator > ", cxx_float2 >  cxx_float1, py_float2  >  cxx_float1 );

    test_assert( "float operator > ", cxx_float1 >  cxx_float2, py_float1  >  py_float2 );
    test_assert( "float operator > ", cxx_float1 >  cxx_float2, cxx_float1 >  py_float2 );
    test_assert( "float operator > ", cxx_float1 >  cxx_float2, py_float1  >  cxx_float2 );

    //------------------------------------------------------------   
    test_assert( "float operator <=", cxx_float1 <= cxx_float2, py_float1  <= py_float2 );
    test_assert( "float operator <=", cxx_float1 <= cxx_float2, cxx_float2 <= py_float2 );
    test_assert( "float operator <=", cxx_float1 <= cxx_float2, py_float1  <= cxx_float2 );

    test_assert( "float operator <=", cxx_float2 <= cxx_float3, py_float2  <= py_float3 );
    test_assert( "float operator <=", cxx_float2 <= cxx_float3, cxx_float2 <= py_float3 );
    test_assert( "float operator <=", cxx_float2 <= cxx_float3, py_float2  <= cxx_float3 );

    test_assert( "float operator <=", cxx_float2 <= cxx_float1, py_float2  <= py_float1 );
    test_assert( "float operator <=", cxx_float2 <= cxx_float1, cxx_float2 <= py_float1 );
    test_assert( "float operator <=", cxx_float2 <= cxx_float1, py_float2  <= cxx_float1 );

    //------------------------------------------------------------   
    test_assert( "float operator >=", cxx_float2 >= cxx_float1, py_float2  >= py_float1 );
    test_assert( "float operator >=", cxx_float2 >= cxx_float1, cxx_float2 >= py_float1 );
    test_assert( "float operator >=", cxx_float2 >= cxx_float1, py_float2  >= cxx_float1 );

    test_assert( "float operator >=", cxx_float2 >= cxx_float3, py_float2  >= py_float3 );
    test_assert( "float operator >=", cxx_float2 >= cxx_float3, cxx_float2 >= py_float3 );
    test_assert( "float operator >=", cxx_float2 >= cxx_float3, py_float2  >= cxx_float3 );

    test_assert( "float operator >=", cxx_float1 >= cxx_float2, py_float1  >= py_float2 );
    test_assert( "float operator >=", cxx_float1 >= cxx_float2, cxx_float1 >= py_float2 );
    test_assert( "float operator >=", cxx_float1 >= cxx_float2, py_float1  >= cxx_float2 );

    //------------------------------------------------------------   
    test_assert( "float operator float", cxx_float2, float( py_float2 ) );
}

void test_numbers()
{
    test_long();
    test_float();

    // test the basic numerical classes
    Py::Long i;
    Py::Long j(2);
    Py::Long k = Py::Long(3);

    i = 2;

    Py::Float a;
    a = 3 + i; //5.0
    Py::Float b( 4.0 );
    a = (1.0 + 2*a + (b*3.0)/2.0 + k)/Py::Float(5); // 4.0
    i = a - 1.0; // 3

    test_assert( "number calculation", i.as_long(), k.as_long() );
}

void test_List()
{
    // test the Py::List class
    Py::List list1;
    Py::List list2;

    test_assert( "list empty len()", list1.size(), static_cast<size_t>( 0 ) );

    list2.append( Py::String( "list2 index 0" ) );
    list2.append( Py::String( "list2 index 1" ) );

    list1.append( Py::Long( 3 ) );
    list1.append( Py::Float( 6.0 ) );
    list1.append( list2 );
    list1.append( Py::String( "world" ) );

    test_assert( "list len()", static_cast<size_t>( 4 ), list1.size() );

    test_assert( "list index[0]", Py::Long( 3 ), list1[0] );
    test_assert( "list index[1]", Py::Float( 6.0 ), list1[1] );
    test_assert( "list index[-1]", Py::String( "world" ), list1[-1] );

    Py::List::iterator it1 = list1.begin();
    test_assert( "list iterator not end != [0]", true, it1 != list1.end() );
    test_assert( "list iterator not end == [0]", false, it1 == list1.end() );
    test_assert( "list iterator compare [0]", Py::Long( 3 ), *it1 );
    ++it1;
    test_assert( "list iterator not end != [1]", true, it1 != list1.end() );
    test_assert( "list iterator not end == [1]", false, it1 == list1.end() );
    test_assert( "list iterator compare [1]", Py::Float( 6.0 ), *it1 );
    ++it1;
    test_assert( "list iterator not end != [2]", true, it1 != list1.end() );
    test_assert( "list iterator not end == [2]", false, it1 == list1.end() );
    test_assert( "list iterator compare [2]", list2, *it1 );
    ++it1;
    Py::List::iterator it2 = list1.end();
    test_assert( "list iterator not end != [3]", true, it1 != list1.end() );
    test_assert( "list iterator not end == [3]", false, it1 == list1.end() );
    test_assert( "list iterator compare [3]", Py::String( "world" ), *it1 );
    ++it1;
    test_assert( "list iterator at end != [4]", false, it1 != list1.end() );
    test_assert( "list iterator at end == [4]", true, it1 == list1.end() );

    list1[ 3 ] = Py::String( "hello" );
    test_assert( "list index assign", list1[ 3 ], Py::String( "hello" ) );

    Py::List list3;
    list3 = list1 + list2;
    test_assert( "list operator+ count", static_cast<size_t>( 6 ), list3.size() );

    Py::Tuple tuple1( list1 );
    test_assert( "list construct from tuple", list1.size(), tuple1.size() );
}

void test_Tuple()
{
    // test the Tuple class
    Py::Float f1( 1.0 );
    Py::Float f2( 2.0 );
    Py::Float f3( 3.0 );

    Py::Tuple tuple1( 3 );
    tuple1[0] = f1; // should be ok since no other reference owned
    tuple1[1] = f2;
    tuple1[2] = f3;

    Py::Tuple tuple2( tuple1 );

    Py::Tuple::iterator it2 = tuple2.begin();
    test_assert( "tuple iterator not end [0]", true, it2 != tuple2.end() );
    test_assert( "tuple iterator compare [0]", Py::Float( 1.0 ), *it2 );
    ++it2;
    test_assert( "tuple iterator not end [1]", true, it2 != tuple2.end() );
    test_assert( "tuple iterator compare [1]", Py::Float( 2.0 ), *it2 );
    ++it2;
    test_assert( "tuple iterator not end [2]", true, it2 != tuple2.end() );
    test_assert( "tuple iterator compare [2]", Py::Float( 3.0 ), *it2 );
    ++it2;
    test_assert( "tuple iterator at end [3]", true, it2 == tuple2.end() );

    bool test_passed = false;

    Py::Tuple tuple3 = tuple1;

    try
    {
        tuple3[0] = Py::Long( 1 ); // should fail, tuple has multiple references
    }
    catch( Py::Exception &e )
    {
        e.clear();
        test_passed = true;
    }

    test_assert( "tuple assign exception with multiple referencese", test_passed, true );

    Py::List list1( tuple1 );
    test_assert( "tuple construct from list", list1.size(), tuple1.size() );

    Py::TupleN t0;
    test_assert( "TupleN construction", 0, t0.size() );
    Py::TupleN t1(  Py::Long( 1 ) );
    test_assert( "TupleN construction", 1, t1.size() );
    Py::TupleN t2(  Py::Long( 1 ), Py::Long( 2 ) );
    test_assert( "TupleN construction", 2, t2.size() );
    Py::TupleN t3(  Py::Long( 1 ), Py::Long( 2 ), Py::Long( 3 ) );
    test_assert( "TupleN construction", 3, t3.size() );
    Py::TupleN t4(  Py::Long( 1 ), Py::Long( 2 ), Py::Long( 3 ),
                    Py::Long( 4 ) );
    test_assert( "TupleN construction", 4, t4.size() );
    Py::TupleN t5(  Py::Long( 1 ), Py::Long( 2 ), Py::Long( 3 ),
                    Py::Long( 4 ), Py::Long( 5 ) );
    test_assert( "TupleN construction", 5, t5.size() );
    Py::TupleN t6(  Py::Long( 1 ), Py::Long( 2 ), Py::Long( 3 ),
                    Py::Long( 4 ), Py::Long( 5 ), Py::Long( 6 ) );
    test_assert( "TupleN construction", 6, t6.size() );
    Py::TupleN t7(  Py::Long( 1 ), Py::Long( 2 ), Py::Long( 3 ),
                    Py::Long( 4 ), Py::Long( 5 ), Py::Long( 6 ),
                    Py::Long( 7 ) );
    test_assert( "TupleN construction", 7, t7.size() );
    Py::TupleN t8(  Py::Long( 1 ), Py::Long( 2 ), Py::Long( 3 ),
                    Py::Long( 4 ), Py::Long( 5 ), Py::Long( 6 ),
                    Py::Long( 7 ), Py::Long( 8 ) );
    test_assert( "TupleN construction", 8, t8.size() );
    Py::TupleN t9(  Py::Long( 1 ), Py::Long( 2 ), Py::Long( 3 ),
                    Py::Long( 4 ), Py::Long( 5 ), Py::Long( 6 ),
                    Py::Long( 7 ), Py::Long( 8 ), Py::Long( 9 ) );
    test_assert( "TupleN construction", 9, t9.size() );
}

void test_Dict()
{
    // test the Dict class
    Py::Dict dict1;
    Py::List list1;
    Py::String str1( "two" );

    dict1[ "one" ] = Py::Long( 1 );
    dict1[ str1 ] = Py::Long( 2 );
    dict1[ "three" ] = Py::Long( 3 );

    test_assert( "dict index[char *]", dict1[ "one" ], Py::Long( 1 ) );
    test_assert( "dict index[std::string]", dict1[ std::string("one") ], Py::Long( 1 ) );
    test_assert( "dict index[Py::String]", dict1[ str1 ], Py::Long( 2 ) );

    test_assert( "dict keys()", dict1.keys().size(), static_cast<size_t>( 3 ) );
    test_assert( "dict values()", dict1.values().size(), static_cast<size_t>( 3 ) );

    Py::Dict::iterator it1 = dict1.begin();
    test_assert( "dict iterator not end != [0]", true, it1 != dict1.end() );
    test_assert( "dict iterator not end == [0]", false, it1 == dict1.end() );
    ++it1;
    test_assert( "dict iterator not end != [1]", true, it1 != dict1.end() );
    test_assert( "dict iterator not end == [1]", false, it1 == dict1.end() );
    ++it1;
    test_assert( "dict iterator not end != [2]", true, it1 != dict1.end() );
    test_assert( "dict iterator not end == [2]", false, it1 == dict1.end() );
    ++it1;
    
    Py::Dict::iterator it2 = dict1.end();
    bool x = it1 != it2;
    test_assert( "x", false, x );
    test_assert( "dict iterator at end != [3]", false, it1 != dict1.end() );
    test_assert( "dict iterator at end == [3]", true, it1 == dict1.end() );

    list1 = dict1.values();
    list1.sort();

    for( long k = 1; k < 4; ++k )
    {
        test_assert( "dict values as expected", Py::Long( list1[ k-1 ] ).as_long(), k );
    }

    Py::Dict dict2 = dict1;
    dict2.clear();
    test_assert( "dict clear()", dict2.keys().length(), static_cast<size_t>( 0 ) );

    const Py::Dict c;
    for (Py::Dict::const_iterator it = c.begin(); it != c.end(); ++it)
    {
    }
}

void test_STL()
{
    Py::List list1;

    list1.append( Py::Long(5) );
    list1.append( Py::Long(1) );
    list1.append( Py::Long(4) );
    list1.append( Py::Long(2) );
    list1.append( Py::Long(3) );
    list1.append( Py::Long(1) );

    test_assert( "STL count", 2, std::count( list1.begin(), list1.end(), Py::Long( 1 ) ) );

    Py::Dict dict1;
    Py::String s1( "blah" );
    Py::String s2( "gorf" );

    dict1[ "one" ] = s1;
    dict1[ "two" ] = s1;
    dict1[ "three" ] = s2;
    dict1[ "four" ] = s2;

    Py::Dict::iterator it( dict1.begin() );

    test_assert( "STL ad hoc", true, it != dict1.end() );

    while( it != dict1.end() )
    {
        Py::Dict::value_type    vt( *it );
        Py::String rs = vt.second.repr();
        Py::Bytes bs = rs.encode( "utf-8" );
        std::string ls = bs.as_std_string();
        std::cout << "STL test: " << ls << std::endl;
        ++it;
    }
}

void debug_check_ref_queue()
{
#ifdef Py_TRACE_REFS
    // create an element to find the queue
    Py::Long list_element;

    PyObject *p_slow = list_element.ptr();
    PyObject *p_fast = p_slow;

    do
    {
        assert( p_slow->_ob_next->_ob_prev == p_slow );
        assert( p_slow->_ob_prev->_ob_next == p_slow );

        p_slow = p_slow->_ob_next;
        p_fast = p_slow->_ob_next->_ob_next;

        assert( p_slow != p_fast );    
    }
    while( p_slow != list_element.ptr() );

#endif
}


class example_module : public Py::ExtensionModule<example_module>
{
public:
    example_module()
    : Py::ExtensionModule<example_module>( "example" )
    {
        range::init_type();

        add_varargs_method( "string", &example_module::ex_string, "string( s ) = return string" );
        add_varargs_method( "sum", &example_module::ex_sum, "sum( arglist ) = sum of arguments" );
        add_varargs_method( "test", &example_module::ex_test, "test( arglist ) runs a test suite" );
        add_varargs_method( "range", &example_module::new_r, "range( start, stop, step )" );
        add_keyword_method( "kw", &example_module::ex_keyword, "kw()" );

        initialize( "documentation for the example module" );

        Py::Dict d( moduleDictionary() );

        Py::Object b( Py::asObject( new range( 1, 10, 2 ) ) );

        d["a_constant"] = b.getAttr("c");
        d["a_range"] = b;
    }

    virtual ~example_module()
    {}

private:
    Py::Object ex_keyword( const Py::Tuple &args, const Py::Dict &kws )
    {
        std::cout << "Called with " << args.length() << " normal arguments." << std::endl;
        Py::List names( kws.keys() );
        std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
        for( Py::List::size_type i=0; i< names.length(); i++ )
        {
            Py::String name( names[i] );
            std::cout << "    " << name << std::endl;
        }

        return Py::Long(0);
    }

    Py::Object new_r (const Py::Tuple &rargs)
    {
        if (rargs.length() < 2 || rargs.length() > 3)
        {
            throw Py::RuntimeError("Incorrect # of args to range(start,stop [,step]).");
        }

        Py::Long start( rargs[0] );
        Py::Long stop( rargs[1] );
        Py::Long step( 1 );
        if (rargs.length() == 3)
        {
            step = rargs[2];
        }
        std::cout   << "new_r"
                    << " start: " << start.as_long()
                    << " stop: " << stop.as_long()
                    << " step: " << step.as_long()
                    << std::endl;
        if( start.as_long() > stop.as_long() + 1 || step.as_long() == 0 )
        {
            throw Py::RuntimeError("Bad arguments to range( start, stop [,step] )");
        }

        return Py::asObject( new range( start.as_long(), stop.as_long(), step.as_long() ) );
    }

    Py::Object ex_string( const Py::Tuple &a )
    {
        std::cout << "ex_std::string: s1 is first arg" << std::endl;
        Py::Object o1( a[0] );
        std::cout << "ex_string: s1.isString() " << o1.isString() << std::endl;

        if( o1.isString() )
        {
            Py::String s1( o1 );

            std::cout << "ex_string: s1.size() " << s1.size() << std::endl;
            std::cout << "ex_string: s2 is s1.encode( utf-8 )" << std::endl;
            Py::Bytes b1( s1.encode( "utf-8" ) );
            std::cout << "ex_string: s1.isString() " << b1.isString() << std::endl;
            std::cout << "ex_string: s1.size() " << b1.size() << std::endl;
            return b1;
        }
        else
        {
            Py::Bytes b1( o1 );
            std::cout << "ex_string: s1 is b1.decode( utf-8 )" << std::endl;
            Py::String s1( b1.decode( "utf-8" ) );
            std::cout << "ex_string: s1.isString() " << s1.isString() << std::endl;
            std::cout << "ex_string: s1.size() " << s1.size() << std::endl;
            return s1;
        }
    }

    Py::Object ex_sum (const Py::Tuple &a)
    {
        // this is just to test the function verify_length:
        try
        {
            a.verify_length(0);
            std::cout << "I see that you refuse to give me any work to do." << std::endl;
        }
        catch (Py::Exception& e)
        {
            e.clear();
            std::cout << "I will now add up your elements, oh great one." << std::endl;
        }


        Py::Float f(0.0);
        for( Py::Sequence::size_type i = 0; i < a.length(); i++ )
        {    
            Py::Float g (a[i]);
            f = f + g;
        }

        return f;
    }

    Py::Object ex_test( const Py::Tuple &args )
    {
        debug_check_ref_queue();

        std::cout << "Example Test starting" << std::endl;

        try
        {
            Py::String s("this should fail");
            Py::Long k( s.ptr() );
            throw TestError( "convert a Py::String to an Py::Long must not succeed" );
        }
        catch( Py::TypeError &e )
        {
            e.clear();

            std::cout << "PASSED: Correctly caught " << Py::type(e) << std::endl;
            std::cout << "PASSED:   Py::Exception value: " << Py::value(e) << std::endl;
            std::cout << "PASSED:   Py::Exception traceback: " << Py::trace(e) << std::endl;
        }

        try
        {
            debug_check_ref_queue();

            std::cout << "Start: test_compare" << std::endl;
            test_compare();
            debug_check_ref_queue();

            std::cout << "Start: test_boolean" << std::endl;
            test_boolean();
            debug_check_ref_queue();

            std::cout << "Start: test_numbers" << std::endl;
            test_numbers();
            debug_check_ref_queue();

            std::cout << "Start: test_String" << std::endl;
            test_String();
            debug_check_ref_queue();

            std::cout << "Start: test_List" << std::endl;
            test_List();
            debug_check_ref_queue();

            std::cout << "Start: test_Dict" << std::endl;
            test_Dict();
            debug_check_ref_queue();

            std::cout << "Start: test_Tuple" << std::endl;
            test_Tuple();
            debug_check_ref_queue();

            std::cout << "Start: test_STL" << std::endl;
            test_STL();
            std::cout << "Done: test_STL" << std::endl;
            debug_check_ref_queue();

            std::cout << "Start: test_extension_object" << std::endl;
            test_extension_object();
            debug_check_ref_queue();
        }
        catch( TestError &e )
        {
            std::cout << "FAILED: Test error - " << e.m_description << std::endl;
        }

        Py::Module m("sys");
        Py::Object s = m.getAttr("stdout");
        Py::Object nun;
        nun = PyObject_CallMethod(s.ptr(), "write", "s", "Module test ok.\n");
        return Py::None();
    }
};

#if defined( _WIN32 )
#define EXPORT_SYMBOL __declspec( dllexport )
#else
#define EXPORT_SYMBOL
#endif

extern "C" EXPORT_SYMBOL PyObject *PyInit_example()
{
#if defined(PY_WIN32_DELAYLOAD_PYTHON_DLL)
    Py::InitialisePythonIndirectPy::Interface();
#endif

    static example_module *example = new example_module;

    return example->module().ptr();
}

// symbol required for the debug version
extern "C" EXPORT_SYMBOL PyObject *PyInit_example_d()
{ 
    return PyInit_example();
}
