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

#ifndef CFLOWMODULE_HPP
#define CFLOWMODULE_HPP


#include "CXX/Objects.hxx"
#include "CXX/Extensions.hxx"


class CDMControlFlowModule : public Py::ExtensionModule< CDMControlFlowModule >
{
    public:
        CDMControlFlowModule();
        virtual ~CDMControlFlowModule();

    private:
        Py::Object  createFragment( const Py::Tuple &  args );
        Py::Object  createBangLine( const Py::Tuple &  args );
        Py::Object  createEncodingLine( const Py::Tuple &  args );
        Py::Object  createComment( const Py::Tuple &  args );
        Py::Object  createFragmentWithComments( const Py::Tuple &  args );

        Py::Object  getControlFlowFromMemory( const Py::Tuple &  args );
        Py::Object  getControlFlowFromFile( const Py::Tuple &  args );
};


#endif

