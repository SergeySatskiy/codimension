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

#ifndef __r__h
#define __r__h
#include "CXX/Extensions.hxx"

#include STR_STREAM


// Making an extension object
class range: public Py::PythonExtension<range>
{
public:
    range( long start, long stop, long step = 1L );
    virtual ~range();
    static void init_type(void);

    long length() const;
    long item( int i ) const;
    range *slice( int i, int j ) const;
    range *extend( int k ) const;
    std::string asString() const;

    // override functions from PythonExtension
    virtual Py::Object repr();
    virtual Py::Object getattr( const char *name );

    virtual int sequence_length();
    virtual Py::Object sequence_item( Py_ssize_t i );
    virtual Py::Object sequence_concat( const Py::Object &j );
    virtual Py::Object sequence_slice( Py_ssize_t i, Py_ssize_t j );

    // define python methods of this object
    Py::Object amethod( const Py::Tuple &args );
    Py::Object value( const Py::Tuple &args );
    Py::Object assign( const Py::Tuple &args );
    Py::Object reference_count( const Py::Tuple &args );
    Py::Object c_value( const Py::Tuple & ) const;
    void c_assign( const Py::Tuple &, const Py::Object &rhs );

private:
    long    m_start;
    long    m_stop;
    long    m_step;
};

class RangeSequence: public Py::SeqBase<Py::Long>
{
public:

    explicit RangeSequence (PyObject *pyob, bool owned = false): Py::SeqBase<Py::Long>(pyob, owned)
    {
        validate();
    }

    explicit RangeSequence(int start, int stop, int step = 1) 
    {
        set (new range(start, stop, step), true);
    }

    RangeSequence(const RangeSequence& other): Py::SeqBase<Py::Long>(*other)
    {
        validate();
    }

    RangeSequence& operator= (const Py::Object& rhs)
    {
        return (*this = *rhs);
    }

    RangeSequence& operator= (PyObject* rhsp)
    {
        if(ptr() == rhsp) return *this;
        set(rhsp);
        return *this;
    }

    virtual bool accepts(PyObject *pyob) const
    {
        return pyob && range::check(pyob);
    }

    Py::Object value(const Py::Tuple& t) const
    {
        return static_cast<range *>(ptr())->c_value(t);
    }

    void assign(const Py::Tuple& t, const Py::Object& rhs)
    {
        static_cast<range *>(ptr())->c_assign(t, rhs);
    }
};
#endif
