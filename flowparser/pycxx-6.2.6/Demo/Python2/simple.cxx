//
//  Copyright (c) 2008-2010 Barry A. Scott
//
//
//  simple_moduile.cxx
//
//  This module defines a single function.
//
#ifdef _MSC_VER
// disable warning C4786: symbol greater than 255 character,
// nessesary to ignore as <map> causes lots of warning
#pragma warning(disable: 4786)
#endif

#include "CXX/Objects.hxx"
#include "CXX/Extensions.hxx"

#include <assert.h>

class new_style_class: public Py::PythonClass< new_style_class >
{
public:
    new_style_class( Py::PythonClassInstance *self, Py::Tuple &args, Py::Dict &kwds )
    : Py::PythonClass< new_style_class >::PythonClass( self, args, kwds )
    , m_value( "default value" )
    {
        std::cout << "new_style_class c'tor Called with " << args.length() << " normal arguments." << std::endl;
        Py::List names( kwds.keys() );
        std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
        for( Py::List::size_type i=0; i< names.length(); i++ )
        {
            Py::String name( names[i] );
            std::cout << "    " << name << std::endl;
        }
    }

    virtual ~new_style_class()
    {
        std::cout << "~new_style_class." << std::endl;
    }

    static void init_type(void)
    {
        behaviors().name( "new_style_class" );
        behaviors().doc( "documentation for new_style_class class" );
        behaviors().supportGetattro();
        behaviors().supportSetattro();

        PYCXX_ADD_NOARGS_METHOD( func_noargs, new_style_class_func_noargs, "docs for new_style_class_func_noargs" );
        PYCXX_ADD_VARARGS_METHOD( func_varargs, new_style_class_func_varargs, "docs for new_style_class_func_varargs" );
        PYCXX_ADD_KEYWORDS_METHOD( func_keyword, new_style_class_func_keyword, "docs for new_style_class_func_keyword" );

        PYCXX_ADD_NOARGS_METHOD( func_noargs_raise_exception, new_style_class_func_noargs_raise_exception,  "docs for new_style_class_func_noargs_raise_exception" );

        // Call to make the type ready for use
        behaviors().readyType();
    }

    Py::Object new_style_class_func_noargs( void )
    {
        std::cout << "new_style_class_func_noargs Called." << std::endl;
        std::cout << "value ref count " << m_value.reference_count() << std::endl;
        return Py::None();
    }
    PYCXX_NOARGS_METHOD_DECL( new_style_class, new_style_class_func_noargs )

    Py::Object new_style_class_func_varargs( const Py::Tuple &args )
    {
        std::cout << "new_style_class_func_varargs Called with " << args.length() << " normal arguments." << std::endl;
        return Py::None();
    }
    PYCXX_VARARGS_METHOD_DECL( new_style_class, new_style_class_func_varargs )

    Py::Object new_style_class_func_keyword( const Py::Tuple &args, const Py::Dict &kwds )
    {
        std::cout << "new_style_class_func_keyword Called with " << args.length() << " normal arguments." << std::endl;
        Py::List names( kwds.keys() );
        std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
        for( Py::List::size_type i=0; i< names.length(); i++ )
        {
            Py::String name( names[i] );
            std::cout << "    " << name << std::endl;
        }
        return Py::None();
    }
    PYCXX_KEYWORDS_METHOD_DECL( new_style_class, new_style_class_func_keyword )

    Py::Object new_style_class_func_noargs_raise_exception( void )
    {
        std::cout << "new_style_class_func_noargs_raise_exception Called." << std::endl;
        throw Py::RuntimeError( "its an error" );
        return Py::None();
    }
    PYCXX_NOARGS_METHOD_DECL( new_style_class, new_style_class_func_noargs_raise_exception )

    Py::Object getattro( const Py::String &name_ )
    {
        std::string name( name_.as_std_string( "utf-8" ) );

        if( name == "value" )
        {
            return m_value;
        }
        else
        {
            return genericGetAttro( name_ );
        }
    }

    int setattro( const Py::String &name_, const Py::Object &value )
    {
        std::string name( name_.as_std_string( "utf-8" ) );

        if( name == "value" )
        {
            m_value = value;
            return 0;
        }
        else
        {
            return genericSetAttro( name_, value );
        }
    }

    Py::String m_value;
};


class old_style_class: public Py::PythonExtension< old_style_class >
{
public:
    old_style_class()
    {
    }

    virtual ~old_style_class()
    {
    }

    static void init_type(void)
    {
        behaviors().name( "old_style_class" );
        behaviors().doc( "documentation for old_style_class class" );
        behaviors().supportGetattr();

        add_noargs_method( "old_style_class_func_noargs", &old_style_class::old_style_class_func_noargs );
        add_varargs_method( "old_style_class_func_varargs", &old_style_class::old_style_class_func_varargs );
        add_keyword_method( "old_style_class_func_keyword", &old_style_class::old_style_class_func_keyword );
    }

    // override functions from PythonExtension
    virtual Py::Object getattr( const char *name )
    {
        return getattr_methods( name );
    }

    Py::Object old_style_class_func_noargs( void )
    {
        std::cout << "old_style_class_func_noargs Called." << std::endl;
        return Py::None();
    }

    Py::Object old_style_class_func_varargs( const Py::Tuple &args )
    {
        std::cout << "old_style_class_func_varargs Called with " << args.length() << " normal arguments." << std::endl;
        return Py::None();
    }

    Py::Object old_style_class_func_keyword( const Py::Tuple &args, const Py::Dict &kwds )
    {
        std::cout << "old_style_class_func_keyword Called with " << args.length() << " normal arguments." << std::endl;
        Py::List names( kwds.keys() );
        std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
        for( Py::List::size_type i=0; i< names.length(); i++ )
        {
            Py::String name( names[i] );
            std::cout << "    " << name << std::endl;
        }
        return Py::None();
    }
};

class simple_module : public Py::ExtensionModule<simple_module>
{
public:
    simple_module()
    : Py::ExtensionModule<simple_module>( "simple" ) // this must be name of the file on disk e.g. simple.so or simple.pyd
    {
        old_style_class::init_type();
        new_style_class::init_type();

        add_varargs_method("old_style_class", &simple_module::factory_old_style_class, "documentation for old_style_class()");
        add_keyword_method("func", &simple_module::func, "documentation for func()");
        add_keyword_method("make_instance", &simple_module::make_instance, "documentation for make_instance()");

        add_keyword_method("decode_test", &simple_module::decode_test, "documentation for decode_test()");
        add_keyword_method("encode_test", &simple_module::encode_test, "documentation for encode_test()");

        // after initialize the moduleDictionary will exist
        initialize( "documentation for the simple module" );

        Py::Dict d( moduleDictionary() );
        d["var"] = Py::String( "var value" );
        Py::Object x( new_style_class::type() );
        d["new_style_class"] = x;
    }

    virtual ~simple_module()
    {}

private:
    Py::Object decode_test( const Py::Tuple &args, const Py::Dict &kwds )
    {
        Py::String s( args[0] );
        return s.decode("utf-8");
    }

    Py::Object encode_test( const Py::Tuple &args, const Py::Dict &kwds )
    {
        Py::String s( args[0] );
        return s.encode("utf-8");
    }

    Py::Object func( const Py::Tuple &args, const Py::Dict &kwds )
    {
        std::cout << "func Called with " << args.length() << " normal arguments." << std::endl;
        Py::List names( kwds.keys() );
        std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
        for( Py::List::size_type i=0; i< names.length(); i++ )
        {
            Py::String name( names[i] );
            std::cout << "    " << name << std::endl;
        }

        if( args.length() > 0 )
        {
            Py::Object x( args[0] );
            try
            {
                Py::PythonClassObject<new_style_class> x2( x );
                std::cout << "C++ pointer " << x2.getCxxObject() << std::endl;
            }
            catch( Py::TypeError &e )
            {
                // must clear the error
                e.clear();
                std::cout << "arg 1 is not a new_style_class" << std::endl;
            }
        }

        return Py::None();
    }

    Py::Object make_instance( const Py::Tuple &args, const Py::Dict &kwds )
    {
        std::cout << "make_instance Called with " << args.length() << " normal arguments." << std::endl;
        Py::List names( kwds.keys() );
        std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
        for( Py::List::size_type i=0; i< names.length(); i++ )
        {
            Py::String name( names[i] );
            std::cout << "    " << name << std::endl;
        }

        Py::Callable class_type( new_style_class::type() );

        Py::PythonClassObject<new_style_class> new_style_obj( class_type.apply( args, kwds ) );

        return new_style_obj;
    }


    Py::Object factory_old_style_class( const Py::Tuple &rargs )
    {
        Py::Object obj = Py::asObject( new old_style_class );
        return obj;
    }
};

#if defined( _WIN32 )
#define EXPORT_SYMBOL __declspec( dllexport )
#else
#define EXPORT_SYMBOL
#endif

#if defined( PY3 )
static simple_module *simple;

extern "C" EXPORT_SYMBOL PyObject *PyInit_simple()
{
#if defined(PY_WIN32_DELAYLOAD_PYTHON_DLL)
    Py::InitialisePythonIndirectPy::Interface();
#endif

    simple = new simple_module;
    return simple->module().ptr();
}

// symbol required for the debug version
extern "C" EXPORT_SYMBOL PyObject *PyInit_simple_d()
{ 
    return PyInit_simple();
}

#else

static simple_module *simple;

extern "C" EXPORT_SYMBOL void initsimple()
{
#if defined(PY_WIN32_DELAYLOAD_PYTHON_DLL)
    Py::InitialisePythonIndirectPy::Interface();
#endif

    simple = new simple_module;
}

// symbol required for the debug version
extern "C" EXPORT_SYMBOL void initsimple_d()
{ 
    initsimple();
}
#endif
