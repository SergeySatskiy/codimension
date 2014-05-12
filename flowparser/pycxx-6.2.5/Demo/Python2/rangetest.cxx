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

#include "CXX/Extensions.hxx"
#include "range.hxx"

// This test also illustrates using the Py namespace explicitly

extern void debug_check_ref_queue();


std::string test_extension_object() 
{ 
    debug_check_ref_queue();

    Py::Tuple a; // just something that isn't an range...

    Py::ExtensionObject<range> r1( new range(1, 20, 3) );
    if(range::check(a))
        std::cout << "range::check failed (1).";
    if(!range::check(r1))
        return "r::check failed (2).";

    debug_check_ref_queue();

    RangeSequence r2(1, 10, 2);
    if(r2[1] != Py::Int(3))
        return "RangeSequence check failed. ";

    debug_check_ref_queue();

    // calling an extension object method using getattr
    Py::Callable w(r2.getAttr("amethod"));
    Py::Tuple args(1);
    Py::Int j(3);
    args[0]=j;
    Py::List answer(w.apply(args));
    if(answer[0] != r2)
        return ("Extension object test failed (1)");

    if(answer[1] != args[0])
        return ("Extension object test failed (2)");

    // calling an extension object method using callMemberFunction
    Py::List answer2( r2.callMemberFunction( "amethod", args ) );
    if(answer2[0] != r2)
        return ("Extension object test failed (3)");

    if(answer2[1] != args[0])
        return ("Extension object test failed (4)");

    debug_check_ref_queue();

    Py::Tuple nv(3);
    nv[0] = Py::Int(1);
    nv[1] = Py::Int(20);
    nv[2] = Py::Int(3);
    Py::Tuple unused;
    Py::List r2value;
    r2.assign(unused, nv);
    r2value = r2.value(unused);
    if(r2value[1] != Py::Int(4))
        return("Extension object test failed (5)");

    debug_check_ref_queue();

    // repeat using getattr
    w = r2.getAttr("assign");
    Py::Tuple the_arguments(2);
    the_arguments[0] = unused;
    the_arguments[1] = nv;
    w.apply(the_arguments);

    debug_check_ref_queue();

    w = r2.getAttr("value");
    Py::Tuple one_arg(1);
    one_arg[0] = unused;
    r2value = w.apply(one_arg);
    if(r2value[1] != Py::Int(4))
        return("Extension object test failed. (6)");

    debug_check_ref_queue();
    {
        Py::ExtensionObject<range> rheap( new range(1, 10, 2) );

        debug_check_ref_queue();

        // delete rheap
    }

    debug_check_ref_queue();

    return "ok.";
}
