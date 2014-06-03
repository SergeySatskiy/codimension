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
#define INT_TYPE            long
#define PYTHON_INT_TYPE     Py::Long



// Base class for all the fragments. It is visible in C++ only, python users
// are not aware of it
class FragmentBase
{
    public:
        FragmentBase();
        virtual ~FragmentBase();

    public:
        FragmentBase *  parent; // Pointer to the parent fragment.
                                // The most top level fragment has it as NULL
        std::string *   content;// Owner of this field is the ControlFlow
                                // object. Other derivatives must not touch it.

    public:
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

        Py::List    getMembers( void ) const;
        Py::Object  getAttribute( const char *  name );
        int         setAttr( const char *        name,
                             const Py::Object &  value );

        std::string asStr( void ) const;

    public:
        Py::Object  getLineRange( void );
        Py::Object  getContent( const Py::Tuple &  args );
        std::string getContent( const std::string *  buf = NULL );
        Py::Object  getLineContent( const Py::Tuple &  args );

        // C++ only; helpers to make it a bit faster
        static Py::List     members;
        static void init( void );

    protected:
        void throwWrongBufArgument( const std::string &  funcName );
};



class Fragment : public FragmentBase,
                 public Py::PythonExtension< Fragment >
{
    public:
        Fragment();
        virtual ~Fragment();

        static void initType( void );
        Py::Object getattr( const char *  name );
        Py::Object repr( void );
        virtual int setattr( const char *        name,
                             const Py::Object &  value );
};


class BangLine : public FragmentBase,
                 public Py::PythonExtension< BangLine >
{
    public:
        BangLine();
        virtual ~BangLine();

        static void initType( void );
        Py::Object getattr( const char *  name );
        Py::Object repr( void );
        virtual int setattr( const char *        name,
                             const Py::Object &  value );

        Py::Object getDisplayValue( const Py::Tuple &  args );
};


class EncodingLine : public FragmentBase,
                     public Py::PythonExtension< EncodingLine >
{
    public:
        EncodingLine();
        virtual ~EncodingLine();

        static void initType( void );
        Py::Object getattr( const char *  name );
        Py::Object repr( void );
        virtual int setattr( const char *        name,
                             const Py::Object &  value );

        Py::Object getDisplayValue( const Py::Tuple &  args );
};


class Comment : public FragmentBase,
                public Py::PythonExtension< Comment >
{
    public:
        Comment();
        virtual ~Comment();

        static void initType( void );
        Py::Object getattr( const char *  name );
        Py::Object repr( void );
        virtual int setattr( const char *        name,
                             const Py::Object &  value );

        Py::Object getDisplayValue( const Py::Tuple &  args );
        Py::Object niceStringify( const Py::Tuple &  args );

    public:
        Py::List    parts;      // Fragment instances
};


class Docstring : public FragmentBase,
                  public Py::PythonExtension< Docstring >
{
    public:
        Docstring();
        virtual ~Docstring();

        static void initType( void );
        Py::Object getattr( const char *  name );
        Py::Object repr( void );
        virtual int setattr( const char *        name,
                             const Py::Object &  value );

        Py::Object getDisplayValue( const Py::Tuple &  args );
        Py::Object niceStringify( const Py::Tuple &  args );

    private:
        static std::string  trimDocstring( const std::string &  docstring );

    public:
        Py::List        parts;          // List of Fragment instances
        Py::Object      sideComment;    // None or Comment instance
};


class Decorator : public FragmentBase,
                  public Py::PythonExtension< Decorator >
{
    public:
        Decorator();
        virtual ~Decorator();

        static void initType( void );
        Py::Object getattr( const char *  name );
        Py::Object repr( void );
        virtual int setattr( const char *        name,
                             const Py::Object &  value );

    public:
        Py::Object      name;           // None or Fragment for a name
        Py::Object      arguments;      // None or Fragment for arguments
                                        // Starting from '(', ending with ')'
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


//
// NOTE: do not introduce FragmentWithComments
//       have separate members instead
//


#endif

