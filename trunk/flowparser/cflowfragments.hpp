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
                            Py::Object &        retval );
        bool  setAttribute( const char *        attrName,
                            const Py::Object &  val );

        std::string asStr( void ) const;

    public:
        Py::Object  getLineRange( void );
        Py::Object  getContent( const Py::Tuple &  args );
        std::string getContent( const std::string *  buf = NULL );
        Py::Object  getLineContent( const Py::Tuple &  args );
        #if 0
        // TODO: No need anymore?
        void        updateEnd( INT_TYPE  otherEnd,
                               INT_TYPE  otherEndLine, INT_TYPE  otherEndPos );
        void        updateBegin( INT_TYPE  otherBegin,
                                 INT_TYPE  otherBeginLine,
                                 INT_TYPE  otherBeginPos );
        #endif
        void        updateBeginEnd( const FragmentBase *  other );
};


// General idea is as follows:
// - the fragment in the base covers everything in the fragment, starting from
//   the very first character of the leading comment till the very last
//   character of the side comment of the last nested statement.
// - data members store fragments which describe the meaningfull parts of the
//   complex statements
// Naming convention
// - body: first character of the statement itself
// - nsuite: list of fragments in the statement scope if so
//           Note: the better name is simply 'suite' however python headers
//                 define suite as 300, so I had to call this member
//                 differently. The module however will display this member as
//                 good plain 'suite' without 'n' (nested) prefix



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
                             const Py::Object &  val );
};


// Not visible in Python.
// The class stores common parts of many complex statements.
class FragmentWithComments
{
    public:
        FragmentWithComments();
        virtual ~FragmentWithComments();

    public:
        Py::Object      leadingComment;     // None or Comment instance
        Py::Object      sideComment;        // None or Comment instance
        Py::Object      body;               // Fragment for the body

    public:
        void  appendMembers( Py::List &  container );
        bool  getAttribute( const char *        attrName,
                            Py::Object &        retval );
        bool  setAttribute( const char *        attrName,
                            const Py::Object &  val );
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
                             const Py::Object &  val );

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
                             const Py::Object &  val );

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
                             const Py::Object &  val );

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
                             const Py::Object &  val );

        Py::Object getDisplayValue( const Py::Tuple &  args );
        Py::Object niceStringify( const Py::Tuple &  args );

    private:
        static std::string  trimDocstring( const std::string &  docstring );

    public:
        Py::List        parts;          // List of Fragment instances
        Py::Object      sideComment;    // None or Comment instance
};


class Decorator : public FragmentBase,
                  public FragmentWithComments,
                  public Py::PythonExtension< Decorator >
{
    public:
        Decorator();
        virtual ~Decorator();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      name;           // None or Fragment for a name
        Py::Object      arguments;      // None or Fragment for arguments
                                        // Starting from '(', ending with ')'
};


class CodeBlock : public FragmentBase,
                  public FragmentWithComments,
                  public Py::PythonExtension< CodeBlock >
{
    public:
        CodeBlock();
        virtual ~CodeBlock();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );
};


class Function : public FragmentBase,
                 public FragmentWithComments,
                 public Py::PythonExtension< Function >
{
    public:
        Function();
        virtual ~Function();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::List        decors;         // Decorator instances
        Py::Object      name;           // Fragment for the function name
        Py::Object      arguments;      // Fragment for the function arguments
                                        // starting from '(', ending with ')'
        Py::Object      docstring;      // None or Docstring instance
        Py::List        nsuite;
};


class Class : public FragmentBase,
              public FragmentWithComments,
              public Py::PythonExtension< Class >
{
    public:
        Class();
        virtual ~Class();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::List        decors;         // Decorator instances
        Py::Object      name;           // Fragment for the function name
        Py::Object      baseClasses;    // Fragment for the class base classes
                                        // starting from '(', ending with ')'
        Py::Object      docstring;      // None or Docstring instance
        Py::List        nsuite;
};


class Break : public FragmentBase,
              public FragmentWithComments,
              public Py::PythonExtension< Break >
{
    public:
        Break();
        virtual ~Break();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );
};


class Continue : public FragmentBase,
                 public FragmentWithComments,
                 public Py::PythonExtension< Continue >
{
    public:
        Continue();
        virtual ~Continue();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );
};


class Return : public FragmentBase,
               public FragmentWithComments,
               public Py::PythonExtension< Return >
{
    public:
        Return();
        virtual ~Return();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      value;          // None or Fragment for the value
};


class Raise : public FragmentBase,
              public FragmentWithComments,
              public Py::PythonExtension< Raise >
{
    public:
        Raise();
        virtual ~Raise();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      value;          // None or Fragment for the value
};


class Assert : public FragmentBase,
               public FragmentWithComments,
               public Py::PythonExtension< Assert >
{
    public:
        Assert();
        virtual ~Assert();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      tst;            // Fragment for the test expression
        Py::Object      message;        // Fragment for the message
};


class SysExit : public FragmentBase,
                public FragmentWithComments,
                public Py::PythonExtension< SysExit >
{
    public:
        SysExit();
        virtual ~SysExit();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      arg;            // Fragment for the argument from '('
                                        // till ')'
};


class While : public FragmentBase,
              public FragmentWithComments,
              public Py::PythonExtension< While >
{
    public:
        While();
        virtual ~While();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      condition;      // Fragment for the condition
        Py::List        nsuite;         // List of suite Fragments
        Py::Object      elsePart;       // None or IfPart instance
};



class For : public FragmentBase,
            public FragmentWithComments,
            public Py::PythonExtension< For >
{
    public:
        For();
        virtual ~For();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      iteration;      // Fragment for the iteration
        Py::List        nsuite;         // List of Fragments for the suite
        Py::Object      elsePart;       // None or IfPart instance
};


class Import : public FragmentBase,
               public FragmentWithComments,
               public Py::PythonExtension< Import >
{
    public:
        Import();
        virtual ~Import();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      fromPart;   // None or Fragment for A in statements
                                    // like: from A import ...
        Py::Object      whatPart;   // Fragment for B in statements like:
                                    // from A import B
                                    // import B
};


class IfPart : public FragmentBase,
               public FragmentWithComments,
               public Py::PythonExtension< IfPart >
{
    public:
        IfPart();
        virtual ~IfPart();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      condition;  // None for 'else' part or Fragment instance
        Py::List        nsuite;     // Fragments for suite statements
};


class If : public FragmentBase,
           public Py::PythonExtension< If >
{
    public:
        If();
        virtual ~If();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::List        parts;      // List of IfPart fragments
};


class With : public FragmentBase,
             public FragmentWithComments,
             public Py::PythonExtension< With >
{
    public:
        With();
        virtual ~With();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      object;     // Fragment for the object
        Py::List        nsuite;     // List of suite statement fragments
};


class ExceptPart : public FragmentBase,
                   public FragmentWithComments,
                   public Py::PythonExtension< ExceptPart >
{
    public:
        ExceptPart();
        virtual ~ExceptPart();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object      exceptionType;  // Fragment or None for the
                                        // exception type
        Py::Object      variable;       // Fragment or None for the variable
                                        // It comes after ',' or 'as'
                                        // Always None for 'finally'
        Py::List        nsuite;         // List of suite statement fragments
};


class Try : public FragmentBase,
            public FragmentWithComments,
            public Py::PythonExtension< Try >
{
    public:
        Try();
        virtual ~Try();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::List        exceptParts;    // List of ExceptPart fragments
        Py::Object      finallyPart;    // None or ExceptPart for finally
        Py::List        nsuite;         // List of suite statement fragments
};


class ControlFlow : public FragmentBase,
                    public Py::PythonExtension< ControlFlow >
{
    public:
        ControlFlow();
        virtual ~ControlFlow();

        static void initType( void );
        Py::Object getattr( const char *  attrName );
        Py::Object repr( void );
        virtual int setattr( const char *        attrName,
                             const Py::Object &  val );

    public:
        Py::Object  bangLine;       // None or BangLine instance
        Py::Object  encodingLine;   // None or EncodingLine instance
        Py::Object  docstring;      // None or Docstring instance
        Py::List    nsuite;         // Suite statement fragments

        // Error reporting support
        bool        isOK;           // true if no errors detected
        Py::List    errors;         // List of Py::String objects
};


#endif

