#include "pycxx_iter.hxx"
#include "CXX/Objects.hxx"

void IterT::init_type()
{
    behaviors().name( "IterT" );
    behaviors().doc( "IterT( ini_count )" );
    // you must have overwritten the virtual functions
    // Py::Object iter() and Py::Object iternext()
    behaviors().supportIter();    // set entries in the Type Table
    behaviors().supportRepr();
    add_varargs_method( "reversed", &IterT::reversed, "reversed()" );
}

class MyIterModule : public Py::ExtensionModule<MyIterModule>
{

public:
    MyIterModule() : Py::ExtensionModule<MyIterModule>( "pycxx_iter" )
    {
        IterT::init_type();
        add_varargs_method( "IterT", &MyIterModule::new_IterT, "IterT(from,last)" );
        initialize( "MyIterModule documentation" ); // register with Python
    }
    
    virtual ~MyIterModule()
    {}

private:
    Py::Object new_IterT( const Py::Tuple &args )
    {
        if( args.length() != 2 )
        {
            throw Py::RuntimeError( "Incorrect # of args to IterT(from,to)." );
        }
        return Py::asObject( new IterT( Py::Long( args[0] ).as_long(), Py::Long( args[1] ).as_long() ) );
    }
};

#if defined( _WIN32 )
#define EXPORT_SYMBOL __declspec( dllexport )
#else
#define EXPORT_SYMBOL
#endif

extern "C" EXPORT_SYMBOL PyObject *PyInit_pycxx_iter()
{
    // the following constructor call registers our extension module
    // with the Python runtime system
    static MyIterModule *iter = new MyIterModule;

    return iter->module().ptr();
}
