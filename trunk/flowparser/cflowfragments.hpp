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

#ifndef CFLOWFRAGMENTS_HPP
#define CFLOWFRAGMENTS_HPP


#include "CXX/Objects.hxx"
#include "CXX/Extensions.hxx"


// To make it easy to try with 'int' or 'long'
#define INT_TYPE    long



// Base class for all the fragments. It is visible in C++ only, python users
// are not aware of it
class FragmentBase
{
    public:
        FragmentBase();
        virtual ~FragmentBase();

    protected:
        FragmentBase *  parent; // Pointer to the parent fragment.
                                // The most top level fragment has it as NULL

    protected:
        INT_TYPE    kind;       // Fragment type

        INT_TYPE    begin;      // Absolute position of the first fragment
                                // character. 0-based. It must never be -1.
        INT_TYPE    end;        // Absolute position of the last fragment
                                // character. 0-based. It must never be -1.

        // Excessive members for convenience. This makes it easier to work with
        // the editor buffer directly.
        INT_TYPE    beginLine;  // 1-based line number
        INT_TYPE    beginPos;   // 1-based position number in the line
        INT_TYPE    endLine;    // 1-based line number
        INT_TYPE    endPos;     // 1-based position number in the line

        bool        serialized; // true if has been serialized

        Py::List    getMembers( void ) const;
        Py::Object  getAttribute( const char *  name );

    public:
        // C++ only; helpers to make it a bit faster
        static Py::List     members;
        static void Init( void );
};



class Fragment : public FragmentBase,
                 public Py::PythonExtension< Fragment >
{
    public:
        Fragment();
        virtual ~Fragment();

        static void InitType( void );
        Py::Object getattr( const char *  name );
};


#endif

