//
//  Copyright (c) 2008 Barry A. Scott
//
//
//  simple2_moduile.cxx
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
#include <map>

template<TEMPLATE_TYPENAME T>
class EnumString
{
public:
    EnumString();
    ~EnumString() {}

    const std::string &toTypeName( T )
    {
        return m_type_name;
    }

    const std::string &toString( T value )
    {
        static std::string not_found( "-unknown-" );
        EXPLICIT_TYPENAME std::map<T,std::string>::iterator it = m_enum_to_string.find( value );
        if( it != m_enum_to_string.end() )
            return (*it).second;

        not_found = "-unknown (";
        int u1000 = value/1000 % 10;
        int u100 = value/100 % 10;
        int u10 = value/10 % 10;
        int u1 = value % 10;
        not_found += char( '0' + u1000 );
        not_found += char( '0' + u100 );
        not_found += char( '0' + u10 );
        not_found += char( '0' + u1 );
        not_found += ")-";
        return not_found;
    }

    bool toEnum( const std::string &string, T &value )
    {
        EXPLICIT_TYPENAME std::map<std::string,T>::iterator it = m_string_to_enum.find( string );
        if( it != m_string_to_enum.end() )
        {
            value = (*it).second;
            return true;
        }

        return false;
    }

    EXPLICIT_TYPENAME std::map<std::string,T>::iterator begin()
    {
        return m_string_to_enum.begin();
    }

    EXPLICIT_TYPENAME std::map<std::string,T>::iterator end()
    {
        return m_string_to_enum.end();
    }

private:
    void add( T value, std::string string )
    {
        m_string_to_enum[string] = value;
        m_enum_to_string[value] = string;
    }
 
    std::string             m_type_name;
    std::map<std::string,T> m_string_to_enum;
    std::map<T,std::string> m_enum_to_string;
};

template<TEMPLATE_TYPENAME T>
class pysvn_enum_value : public Py::PythonExtension< EXPLICIT_CLASS pysvn_enum_value<T> >
{
public:
    pysvn_enum_value( T _value)
        : Py::PythonExtension<pysvn_enum_value>()
        , m_value( _value )
    { }

    virtual ~pysvn_enum_value()
    { }

    virtual int compare( const Py::Object &other )
    {
        if( pysvn_enum_value::check( other ) )
        {
            pysvn_enum_value<T> *other_value = static_cast<pysvn_enum_value *>( other.ptr() );
            if( m_value == other_value->m_value )
                return 0;

            if( m_value > other_value->m_value )
                return 1;
            else
                return -1;
        }
        else
        {
            std::string msg( "expecting " );
            msg += toTypeName( m_value );
            msg += " object for compare ";
            throw Py::AttributeError( msg );
        }
    }

    virtual Py::Object repr()
    {
        std::string s("<");
        s += toTypeName( m_value );
        s += ".";
        s += toString( m_value );
        s += ">";

        return Py::String( s );
    }

    virtual Py::Object str()
    {
        return Py::String( toString( m_value ) );
    }

    // need a hash so that the enums can go into a map
    virtual long hash()
    {
        static Py::String type_name( toTypeName( m_value ) );

        // use the m_value plus the hash of the type name
        return long( m_value ) + type_name.hashValue();
    }

    static void init_type(void);

public:
    T m_value;
};

//------------------------------------------------------------
template<TEMPLATE_TYPENAME T>
class pysvn_enum : public Py::PythonExtension< EXPLICIT_CLASS pysvn_enum<T> >
{
public:
    pysvn_enum()
        : Py::PythonExtension<pysvn_enum>()
    { }

    virtual ~pysvn_enum()
    { }

    virtual Py::Object getattr( const char *_name )
    {
        std::string name( _name );
        T value;

        if( name == "__methods__" )
        {
            return Py::List();
        }

        if( name == "__members__" )
        {
            return memberList( static_cast<T>( 0 ) );
        }

        if( toEnum( name, value ) )
        {
            return Py::asObject( new pysvn_enum_value<T>( value ) );
        }

        return this->getattr_methods( _name );    
    }

    static void init_type(void);
};

template<TEMPLATE_TYPENAME T>
const std::string &toTypeName( T value )
{
    static EnumString< T > enum_map;

    return enum_map.toTypeName( value );
}

template<TEMPLATE_TYPENAME T>
const std::string &toString( T value )
{
    static EnumString< T > enum_map;

    return enum_map.toString( value );
}

template<TEMPLATE_TYPENAME T>
bool toEnum( const std::string &string, T &value )
{
    static EnumString< T > enum_map;

    return enum_map.toEnum( string, value );
}

template<TEMPLATE_TYPENAME T>
Py::List memberList( T value )
{
    static EnumString< T > enum_map;

    Py::List members;

    EXPLICIT_TYPENAME std::map<std::string,T>::iterator it = enum_map.begin();
    while( it != enum_map.end() )
    {
        members.append( Py::String( (*it).first ) );
        ++it;
    }
    
    return members;
}

typedef enum {
    xxx_first = 1,
    xxx_second,
    xxx_third
    } xxx_t;



template <> EnumString< xxx_t >::EnumString()
: m_type_name( "xxx" )
{ 
    add( xxx_first, "first" );
    add( xxx_second, "second" );
    add( xxx_third, "third" );
}
template <> void pysvn_enum< xxx_t >::init_type(void)
{
    behaviors().name("xxx");
    behaviors().doc("xxx enumeration");
    behaviors().supportGetattr();
}

template <> void pysvn_enum_value< xxx_t >::init_type(void)
{
    behaviors().name("xxx");
    behaviors().doc("xxx value");
    behaviors().supportRepr();
    behaviors().supportStr();
    behaviors().supportHash();
}

class cls: public Py::PythonExtension< cls >
{
public:
    cls()
    {
    }

    virtual ~cls()
    {
    }

    static void init_type(void)
    {
        behaviors().name( "cls" );
        behaviors().doc( "documentation for cls class" );
        behaviors().supportGetattr();

        add_noargs_method( "cls_func_noargs", &cls::cls_func_noargs );
        add_varargs_method( "cls_func_varargs", &cls::cls_func_varargs );
        add_keyword_method( "cls_func_keyword", &cls::cls_func_keyword );
    }

    // override functions from PythonExtension
    virtual Py::Object getattr( const char *name )
    {
        return getattr_methods( name );
    }

    Py::Object cls_func_noargs( void )
    {
        std::cout << "cls_func_noargs Called." << std::endl;
        return Py::None();
    }

    Py::Object cls_func_varargs( const Py::Tuple &args )
    {
        std::cout << "cls_func_varargs Called with " << args.length() << " normal arguments." << std::endl;
        return Py::None();
    }

    Py::Object cls_func_keyword( const Py::Tuple &args, const Py::Dict &kws )
    {
        std::cout << "cls_func_keyword Called with " << args.length() << " normal arguments." << std::endl;
        Py::List names( kws.keys() );
        std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
        for( Py::List::size_type i=0; i< names.length(); i++ )
        {
            Py::String name( names[i] );
            std::cout << "    " << name << std::endl;
        }
        return Py::None();
    }
};

class simple2_module : public Py::ExtensionModule<simple2_module>
{
public:
    simple2_module()
    : Py::ExtensionModule<simple2_module>( "simple2" ) // this must be name of the file on disk e.g. simple2.so or simple2.pyd
    {
        cls::init_type();

        pysvn_enum< xxx_t >::init_type();
        pysvn_enum_value< xxx_t >::init_type();

        add_varargs_method("cls", &simple2_module::factory_cls, "documentation for cls()");
        add_keyword_method("func", &simple2_module::func, "documentation for func()");

        // after initialize the moduleDictionary with exist
        initialize( "documentation for the simple2 module" );

        Py::Dict d( moduleDictionary() );
        d["xxx"] = Py::asObject( new pysvn_enum< xxx_t >() );
        d["var"] = Py::String( "var value" );
    }

    virtual ~simple2_module()
    {}

private:
    Py::Object func( const Py::Tuple &args, const Py::Dict &kws )
    {
        return Py::None();
    }

    Py::Object factory_cls( const Py::Tuple &rargs )
    {
        return Py::asObject( new cls );
    }
};

extern "C" PyObject *PyInit_simple2()
{
#if defined(PY_WIN32_DELAYLOAD_PYTHON_DLL)
    Py::InitialisePythonIndirectPy::Interface();
#endif

    static simple2_module* simple2 = new simple2_module;
    return simple2->module().ptr();
}

// symbol required for the debug version
extern "C" PyObject *PyInit_simple2_d()
{ 
    return PyInit_simple2();
}
