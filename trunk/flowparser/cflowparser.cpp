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
 * Python control flow parser implementation
 */


#include "pycfLexer.h"
#include "pycfParser.h"

#include "cflowparser.hpp"
#include "cflowfragments.hpp"



Py::Object  parseInput( pANTLR3_INPUT_STREAM  input )
{
    ppycfLexer      lxr( pycfLexerNew( input ) );
    if ( lxr == NULL )
        throw Py::RuntimeError( "Cannot create lexer" );


    pANTLR3_COMMON_TOKEN_STREAM     tstream;



    ControlFlow *   controlFlow = new ControlFlow();
    return Py::asObject( controlFlow );
}


