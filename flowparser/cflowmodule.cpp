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

#include "cflowparser.hpp"

#include "cflowversion.hpp"
#include "cflowdocs.hpp"
#include "cflowfragmenttypes.hpp"
#include "cflowfragments.hpp"

#include "cflowmodule.hpp"



CDMControlFlowModule::CDMControlFlowModule() :
    Py::ExtensionModule< CDMControlFlowModule >( "cdmcf" )
{
    Fragment::initType();
    BangLine::initType();
    EncodingLine::initType();
    Comment::initType();
    Docstring::initType();
    Decorator::initType();
    CodeBlock::initType();

    Function::initType();
    Class::initType();
    Break::initType();
    Continue::initType();
    Return::initType();
    Raise::initType();
    Assert::initType();
    SysExit::initType();
    While::initType();
    For::initType();
    Import::initType();
    IfPart::initType();
    If::initType();
    With::initType();
    ExceptPart::initType();
    Try::initType();
    ControlFlow::initType();

    add_varargs_method( "Fragment",
                        &CDMControlFlowModule::createFragment,
                        CREATE_FRAGMENT_DOC );
    add_varargs_method( "BangLine",
                        &CDMControlFlowModule::createBangLine,
                        CREATE_BANGLINE_DOC );
    add_varargs_method( "EncodingLine",
                        &CDMControlFlowModule::createEncodingLine,
                        CREATE_ENCODINGLINE_DOC );
    add_varargs_method( "Comment",
                        &CDMControlFlowModule::createComment,
                        CREATE_COMMENT_DOC );
    add_varargs_method( "Docstring",
                        &CDMControlFlowModule::createDocstring,
                        CREATE_DOCSTRING_DOC );
    add_varargs_method( "Decorator",
                        &CDMControlFlowModule::createDecorator,
                        CREATE_DECORATOR_DOC );
    add_varargs_method( "CodeBlock",
                        &CDMControlFlowModule::createCodeBlock,
                        CREATE_CODEBLOCK_DOC );
    add_varargs_method( "Function",
                        &CDMControlFlowModule::createFunction,
                        CREATE_FUNCTION_DOC );
    add_varargs_method( "Class",
                        &CDMControlFlowModule::createClass,
                        CREATE_CLASS_DOC );
    add_varargs_method( "Break",
                        &CDMControlFlowModule::createBreak,
                        CREATE_BREAK_DOC );
    add_varargs_method( "Continue",
                        &CDMControlFlowModule::createContinue,
                        CREATE_CONTINUE_DOC );
    add_varargs_method( "Return",
                        &CDMControlFlowModule::createReturn,
                        CREATE_RETURN_DOC );
    add_varargs_method( "Raise",
                        &CDMControlFlowModule::createRaise,
                        CREATE_RAISE_DOC );
    add_varargs_method( "Assert",
                        &CDMControlFlowModule::createAssert,
                        CREATE_ASSERT_DOC );
    add_varargs_method( "SysExit",
                        &CDMControlFlowModule::createSysExit,
                        CREATE_SYSEXIT_DOC );
    add_varargs_method( "While",
                        &CDMControlFlowModule::createWhile,
                        CREATE_WHILE_DOC );
    add_varargs_method( "For",
                        &CDMControlFlowModule::createFor,
                        CREATE_FOR_DOC );
    add_varargs_method( "Import",
                        &CDMControlFlowModule::createImport,
                        CREATE_IMPORT_DOC );
    add_varargs_method( "IfPart",
                        &CDMControlFlowModule::createIfPart,
                        CREATE_IFPART_DOC );
    add_varargs_method( "If",
                        &CDMControlFlowModule::createIf,
                        CREATE_IF_DOC );
    add_varargs_method( "With",
                        &CDMControlFlowModule::createWith,
                        CREATE_WITH_DOC );
    add_varargs_method( "ExceptPart",
                        &CDMControlFlowModule::createExceptPart,
                        CREATE_EXCEPTPART_DOC );
    add_varargs_method( "Try",
                        &CDMControlFlowModule::createTry,
                        CREATE_TRY_DOC );
    add_varargs_method( "ControlFlow",
                        &CDMControlFlowModule::createControlFlow,
                        CREATE_CONTROLFLOW_DOC );

    // Free functions visible from the module
    add_varargs_method( "getControlFlowFromMemory",
                        &CDMControlFlowModule::getControlFlowFromMemory,
                        GET_CF_MEMORY_DOC );
    add_varargs_method( "getControlFlowFromFile",
                        &CDMControlFlowModule::getControlFlowFromFile,
                        GET_CF_FILE_DOC );


    initialize( MODULE_DOC );

    // Constants visible from the module
    Py::Dict        d( moduleDictionary() );
    d[ "VERSION" ]                  = Py::String( CDM_CF_PARSER_VERION );
    d[ "CML_VERSION" ]              = Py::String( CML_VERSION_AS_STRING );

    d[ "UNDEFINED_FRAGMENT" ]       = Py::Int( UNDEFINED_FRAGMENT );
    d[ "FRAGMENT" ]                 = Py::Int( FRAGMENT );
    d[ "BANG_LINE_FRAGMENT" ]       = Py::Int( BANG_LINE_FRAGMENT );
    d[ "ENCODING_LINE_FRAGMENT" ]   = Py::Int( ENCODING_LINE_FRAGMENT );
    d[ "COMMENT_FRAGMENT" ]         = Py::Int( COMMENT_FRAGMENT );
    d[ "DOCSTRING_FRAGMENT" ]       = Py::Int( DOCSTRING_FRAGMENT );
    d[ "DECORATOR_FRAGMENT" ]       = Py::Int( DECORATOR_FRAGMENT );
    d[ "CODEBLOCK_FRAGMENT" ]       = Py::Int( CODEBLOCK_FRAGMENT );
    d[ "FUNCTION_FRAGMENT" ]        = Py::Int( FUNCTION_FRAGMENT );
    d[ "CLASS_FRAGMENT" ]           = Py::Int( CLASS_FRAGMENT );
    d[ "BREAK_FRAGMENT" ]           = Py::Int( BREAK_FRAGMENT );
    d[ "CONTINUE_FRAGMENT" ]        = Py::Int( CONTINUE_FRAGMENT );
    d[ "RETURN_FRAGMENT" ]          = Py::Int( RETURN_FRAGMENT );
    d[ "RAISE_FRAGMENT" ]           = Py::Int( RAISE_FRAGMENT );
    d[ "ASSERT_FRAGMENT" ]          = Py::Int( ASSERT_FRAGMENT );
    d[ "SYSEXIT_FRAGMENT" ]         = Py::Int( SYSEXIT_FRAGMENT );
    d[ "WHILE_FRAGMENT" ]           = Py::Int( WHILE_FRAGMENT );
    d[ "FOR_FRAGMENT" ]             = Py::Int( FOR_FRAGMENT );
    d[ "IMPORT_FRAGMENT" ]          = Py::Int( IMPORT_FRAGMENT );
    d[ "IF_PART_FRAGMENT" ]         = Py::Int( IF_PART_FRAGMENT );
    d[ "IF_FRAGMENT" ]              = Py::Int( IF_FRAGMENT );
    d[ "WITH_FRAGMENT" ]            = Py::Int( WITH_FRAGMENT );
    d[ "EXCEPT_PART_FRAGMENT" ]     = Py::Int( EXCEPT_PART_FRAGMENT );
    d[ "TRY_FRAGMENT" ]             = Py::Int( TRY_FRAGMENT );
    d[ "CONTROL_FLOW_FRAGMENT" ]    = Py::Int( CONTROL_FLOW_FRAGMENT );

}


CDMControlFlowModule::~CDMControlFlowModule()
{}


Py::Object
CDMControlFlowModule::getControlFlowFromMemory( const Py::Tuple &  args )
{
    // One argument is expected: string with the python code
    if ( args.length() != 1 )
    {
        char    buf[ 32 ];
        sprintf( buf, "%ld", args.length() );
        throw Py::TypeError( "getControlFlowFromMemory() takes exactly 1 "
                             "argument (" + std::string( buf ) + "given)" );
    }

    Py::Object  fName( args[ 0 ] );
    if ( ! fName.isString() )
        throw Py::TypeError( "getControlFlowFromMemory() takes exactly 1 "
                             "argument of string type: python code buffer" );


    std::string     content( Py::String( fName ).as_std_string( "utf-8" ) );
    size_t          contentSize = content.size();

    if ( contentSize > 0 )
    {
        if ( content[ contentSize - 1 ] == '\n' )
        {
            return parseInput( content.c_str(), "dummy.py" );
        }

        // No \n at the end; it is safer to add it
        content += "\n";
        return parseInput( content.c_str(), "dummy.py" );
    }

    // Content size is zero
    ControlFlow *   controlFlow = new ControlFlow();
    return Py::asObject( controlFlow );
}


Py::Object
CDMControlFlowModule::getControlFlowFromFile( const Py::Tuple &  args )
{
    // One parameter is expected: python file name
    if ( args.length() != 1 )
    {
        char    buf[ 32 ];
        sprintf( buf, "%ld", args.length() );
        throw Py::TypeError( "getControlFlowFromFile() takes exactly 1 "
                             "argument (" + std::string( buf ) + "given)" );
    }

    Py::Object      fName( args[ 0 ] );
    if ( ! fName.isString() )
        throw Py::TypeError( "getControlFlowFromFile() takes exactly 1 "
                             "argument of string type: python file name" );


    std::string     fileName( Py::String( fName ).as_std_string( "utf-8" ) );
    if ( fileName.empty() )
        throw Py::RuntimeError( "Invalid argument: file name is empty" );

    // Read the whole file
    FILE *  f;
    f = fopen( fileName.c_str(), "r" );
    if ( f == NULL )
        throw Py::RuntimeError( "Cannot open file " + fileName );

    struct stat     st;
    stat( fileName.c_str(), &st );

    if ( st.st_size > 0 )
    {
        char            buffer[st.st_size + 2];
        int             elem = fread( buffer, st.st_size, 1, f );

        fclose( f );
        if ( elem != 1 )
            throw Py::RuntimeError( "Cannot read file " + fileName );

        buffer[ st.st_size ] = '\n';
        buffer[ st.st_size + 1 ] = '\0';
        return parseInput( buffer, fileName.c_str() );
    }

    // File size is zero
    fclose( f );

    ControlFlow *   controlFlow = new ControlFlow();
    return Py::asObject( controlFlow );
}



Py::Object  CDMControlFlowModule::createFragment( const Py::Tuple &  args )
{
    return Py::asObject( new Fragment() );
}

Py::Object  CDMControlFlowModule::createBangLine( const Py::Tuple &  args )
{
    return Py::asObject( new BangLine() );
}

Py::Object  CDMControlFlowModule::createEncodingLine( const Py::Tuple &  args )
{
    return Py::asObject( new EncodingLine() );
}

Py::Object  CDMControlFlowModule::createComment( const Py::Tuple &  args )
{
    return Py::asObject( new Comment() );
}

Py::Object  CDMControlFlowModule::createDocstring( const Py::Tuple &  args )
{
    return Py::asObject( new Docstring() );
}

Py::Object  CDMControlFlowModule::createDecorator( const Py::Tuple &  args )
{
    return Py::asObject( new Decorator() );
}

Py::Object  CDMControlFlowModule::createCodeBlock( const Py::Tuple &  args )
{
    return Py::asObject( new CodeBlock() );
}

Py::Object  CDMControlFlowModule::createFunction( const Py::Tuple &  args )
{
    return Py::asObject( new Function() );
}

Py::Object  CDMControlFlowModule::createClass( const Py::Tuple &  args )
{
    return Py::asObject( new Class() );
}

Py::Object  CDMControlFlowModule::createBreak( const Py::Tuple &  args )
{
    return Py::asObject( new Break() );
}

Py::Object  CDMControlFlowModule::createContinue( const Py::Tuple &  args )
{
    return Py::asObject( new Continue() );
}

Py::Object  CDMControlFlowModule::createReturn( const Py::Tuple &  args )
{
    return Py::asObject( new Return() );
}

Py::Object  CDMControlFlowModule::createRaise( const Py::Tuple &  args )
{
    return Py::asObject( new Raise() );
}

Py::Object  CDMControlFlowModule::createAssert( const Py::Tuple &  args )
{
    return Py::asObject( new Assert() );
}

Py::Object  CDMControlFlowModule::createSysExit( const Py::Tuple &  args )
{
    return Py::asObject( new SysExit() );
}

Py::Object  CDMControlFlowModule::createWhile( const Py::Tuple &  args )
{
    return Py::asObject( new While() );
}

Py::Object  CDMControlFlowModule::createFor( const Py::Tuple &  args )
{
    return Py::asObject( new For() );
}

Py::Object  CDMControlFlowModule::createImport( const Py::Tuple &  args )
{
    return Py::asObject( new Import() );
}

Py::Object  CDMControlFlowModule::createIfPart( const Py::Tuple &  args )
{
    return Py::asObject( new IfPart() );
}

Py::Object  CDMControlFlowModule::createIf( const Py::Tuple &  args )
{
    return Py::asObject( new If() );
}

Py::Object  CDMControlFlowModule::createWith( const Py::Tuple &  args )
{
    return Py::asObject( new With() );
}

Py::Object  CDMControlFlowModule::createExceptPart( const Py::Tuple &  args )
{
    return Py::asObject( new ExceptPart() );
}

Py::Object  CDMControlFlowModule::createTry( const Py::Tuple &  args )
{
    return Py::asObject( new Try() );
}

Py::Object  CDMControlFlowModule::createControlFlow( const Py::Tuple &  args )
{
    return Py::asObject( new ControlFlow() );
}



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


