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
 * Python extension module
 */


#include "cflowversion.hpp"
#include "cflowdocs.hpp"

#include "cflowmodule.hpp"



CDMControlFlowModule::CDMControlFlowModule() :
    Py::ExtensionModule< CDMControlFlowModule >( "cdmcf" )
{
//    Fragment::InitType();
//    FragmentWithComments::InitType();

//    add_varargs_method( "Fragment",
//                        &CDMControlFlowModule::createFragment,
//                        "Creates the Fragment class instance" );
//    add_varargs_method( "FragmentWithComments",
//                        &CDMControlFlowModule::createFragmentWithComments,
//                        "Creates the FragmentWithComments class instance" );

    initialize( MODULE_DOC );

    // Setup what is visible from the module
    Py::Dict        d( moduleDictionary() );
    d[ "VERSION" ] = Py::String( CDM_CF_PARSER_VERION );
    d[ "CML_VERSION" ] = Py::String( CML_VERSION_AS_STRING );
}


CDMControlFlowModule::~CDMControlFlowModule()
{}




//Py::Object  CDMControlFlowModule::CreateFragment( const Py::Tuple &  args )
//{
//    return Py::asObject( new Fragment() );
//}

//Py::Object createFragmentWithComments( const Py::Tuple &  args )
//{
//    return Py::asObject( new FragmentWithComments() );
//}




static CDMControlFlowModule *  CDMControlFlow;

extern "C" void initcdmcf()
{
    CDMControlFlow = new CDMControlFlowModule;
}

// symbol required for the debug version
extern "C" void initcdmcf_d()
{
    initcdmcf();
}


