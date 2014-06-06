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

        void  appendMembers( Py::List &  container ) const;
        bool  getAttribute( const char *        attrName,
                            Py::Object          retval );
        bool  setAttribute( const char *        attrName,
                            const Py::Object &  value );

        std::string asStr( void ) const;

    public:
        Py::Object  getLineRange( void );
        Py::Object  getContent( const Py::Tuple &  args );
        std::string getContent( const std::string *  buf = NULL );
        Py::Object  getLineContent( const Py::Tuple &  args );
};


// General idea is as follows:
// - the fragment in the base covers everything in the fragment, starting from
//   the very first character of the leading comment till the very last
//   character of the side comment of the last nested statement.
// - data members store fragments which describe the meaningfull parts of the
//   complex statements
// Naming convention
// - body: first character of the statement itself
// - nested: list of fragments in the statement scope if so



// The most basic fragment. It is used to describe some parts of the other
// complex fragments.
class Fragment : public FragmentBase,
                 public Py::PythonExtension< Fragment >
{
    public:
        Fragment();
        virtual ~Fragment();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );
};


// Not visible in Python.
// The class stores common parts of many complex statements.
class Statement
{
    public:
        Statement();
        virtual ~Statement();

    public:
        Py::Object      leadingComment;     // None or Comment instance
        Py::Object      sideComment;        // None or Comment instance
        Py::Object      body;               // Fragment for the body

    public:
        void  appendMembers( Py::List &  container );
        bool  getAttribute( const char *        attrName,
                            Py::Object          retval );
        bool  setAttribute( const char *        attrName,
                            const Py::Object &  value );
        std::string  asStr( void ) const;
};


// Below are the fragments which are visible from Python

class BangLine : public FragmentBase,
                 public Py::PythonExtension< BangLine >
{
    public:
        BangLine();
        virtual ~BangLine();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
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
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
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
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
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
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
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
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      name;           // None or Fragment for a name
        Py::Object      arguments;      // None or Fragment for arguments
                                        // Starting from '(', ending with ')'
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class CodeBlock : public FragmentBase,
                  public Py::PythonExtension< CodeBlock >
{
    public:
        CodeBlock();
        virtual ~CodeBlock();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      body;           // Fragment of the code block
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class Function : public FragmentBase,
                 public Py::PythonExtension< Function >
{
    public:
        Function();
        virtual ~Function();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::List        decorators;     // Decorator instances
        Py::Object      name;           // Fragment for the function name
        Py::Object      arguments;      // Fragment for the function arguments
                                        // starting from '(', ending with ')'
        Py::Object      docstring;      // None or Docstring instance
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
        Py::List        body;
};


class Class : public FragmentBase,
              public Py::PythonExtension< Class >
{
    public:
        Class();
        virtual ~Class();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::List        decorators;     // Decorator instances
        Py::Object      name;           // Fragment for the function name
        Py::Object      baseClasses;    // Fragment for the class base classes
                                        // starting from '(', ending with ')'
        Py::Object      docstring;      // None or Docstring instance
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
        Py::List        body;
};


class Break : public FragmentBase,
              public Py::PythonExtension< Break >
{
    public:
        Break();
        virtual ~Break();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      body;           // Fragment for the break statement
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class Continue : public FragmentBase,
                 public Py::PythonExtension< Continue >
{
    public:
        Continue();
        virtual ~Continue();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      body;           // Fragment for the continue statement
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class Return : public FragmentBase,
               public Py::PythonExtension< Return >
{
    public:
        Return();
        virtual ~Return();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      body;           // Fragment for the return statement
        Py::Object      value;          // None or Fragment for the value
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class Raise : public FragmentBase,
              public Py::PythonExtension< Raise >
{
    public:
        Raise();
        virtual ~Raise();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      body;           // Fragment for the raise statement
        Py::Object      value;          // None or Fragment for the value
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class Assert : public FragmentBase,
               public Py::PythonExtension< Assert >
{
    public:
        Assert();
        virtual ~Assert();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      body;           // Fragment for the assert statement
        Py::Object      test;           // Fragment for the test expression
        Py::Object      message;        // Fragment for the message
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class SysExit : public FragmentBase,
                public Py::PythonExtension< SysExit >
{
    public:
        SysExit();
        virtual ~SysExit();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      body;           // Fragment for the sys.exit statement
        Py::Object      argument;       // Fragment for the argument from '('
                                        // till ')'
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class While : public FragmentBase,
              public Py::PythonExtension< While >
{
    public:
        While();
        virtual ~While();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      condition;      // Fragment for the condition
        Py::List        body;           // List of Fragments for the body
        Py::Object      elsePart;       // None or IfPart instance

        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};



class For : public FragmentBase,
            public Py::PythonExtension< For >
{
    public:
        For();
        virtual ~For();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      iteration;      // Fragment for the iteration
        Py::Object      body;
        Py::List        nested;         // List of Fragments for the nested statements
        Py::Object      elsePart;       // None or IfPart instance

        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};


class Import : public FragmentBase,
               public Py::PythonExtension< Import >
{
    public:
        Import();
        virtual ~Import();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  value );

    public:
        Py::Object      fromPart;   // None or Fragment for A in statements
                                    // like: from A import ...
        Py::Object      whatPart;   // Fragment for B in statements like:
                                    // from A import B
                                    // import B
        Py::Object      body;       //
        Py::Object      leadingComment; // None or Comment instance
        Py::Object      sideComment;    // None or Comment instance
};





//
// NOTE: do not introduce FragmentWithComments
//       have separate members instead
//



// Class
// Break
// Continue
// Return
// Raise
// Assert
// SysExit
// While
// For
// Import
// IfPart
// If
// With
// ExceptPart
// Try

// ControlFlow

#endif

