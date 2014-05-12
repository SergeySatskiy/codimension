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
#pragma warning(disable: 4786)
#endif

#include "range.hxx"
// Connect range objects to Python


Py::Object range::repr()
{
    return Py::String(asString());
}

int range::sequence_length()
{
    return length();
}

Py::Object range::sequence_item(Py_ssize_t i) 
{
    return Py::Int(item(i));
}

Py::Object range::sequence_concat( const Py::Object &j )
{
    Py::Int k(j);
    return Py::asObject(extend(int(k)));
}

Py::Object range::sequence_slice(Py_ssize_t i, Py_ssize_t j)
{
    return Py::asObject(slice(i,j));
}


Py::Object range::getattr( const char *name )
{
    if(std::string(name) == "c")
        return Py::Float(300.0);

    if(std::string(name) == "start")
        return Py::Int(start);

    return getattr_methods( name );
}

// "regular" methods...
Py::Object range::amethod( const Py::Tuple &t ) 
{
    t.verify_length(1);
    Py::List result;
    result.append(Py::Object(this));
    result.append(t[0]);

    return result;
}

Py::Object range::value( const Py::Tuple &t )
{
    return c_value(t);
}

Py::Object range::assign( const Py::Tuple &t ) 
{
    t.verify_length(2);

    Py::Tuple t1(t[0]); // subscripts
    Py::Object o2(t[1]); // rhs;
    c_assign (t1, o2);

    return Py::Nothing();
}

void range::init_type()
{
    behaviors().name("range");
    behaviors().doc("range objects: start, stop, step");
    behaviors().supportRepr();
    behaviors().supportGetattr();
    behaviors().supportSequenceType();

    add_varargs_method("amethod", &range::amethod, "demonstrate how to document amethod");
    add_varargs_method("assign", &range::assign);
    add_varargs_method("value", &range::value);
    add_varargs_method("reference_count", &range::reference_count);
}
