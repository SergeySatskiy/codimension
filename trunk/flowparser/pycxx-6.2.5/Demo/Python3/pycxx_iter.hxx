#include "CXX/Extensions.hxx"
#include <iostream>
#include <sstream>
#include <string>

class IterT : public Py::PythonExtension<IterT> 
{
    int from, count, last;
    int fwd_iter;
    bool do_it_reversed;
public:
    static void init_type(void);    // announce properties and methods

    IterT(int _from, int _last)
    : from(_from)
    , last(_last)
    , fwd_iter(0)
    , do_it_reversed(false)
    {}

    Py::Object repr()
    {
        std::string s;
        std::ostringstream s_out;
        s_out << "IterT count(" << count << ")";
        return Py::String(s_out.str());
    }

    Py::Object reversed(const Py::Tuple&)
    {
        do_it_reversed= true;    // indicate backward iteration
        return Py::Object(this,false);    // increment the refcount
    }

    Py::Object iter()
    {
        if( do_it_reversed )
        {
            fwd_iter = -1;
            do_it_reversed=false;
        }
        else
            fwd_iter = 1;    // indicate forward iteration
        return Py::Object(this,false);    // increment the refcount
    }
    
    PyObject* iternext()
    {
        int ct;
        if( ! fwd_iter )
            return NULL;    // signal StopIteration
        if( fwd_iter > 0 )
        {
            if( fwd_iter == 1 )
                {
                    ct = from;
                    count = from+1;
                    fwd_iter=2;
                }
            else if( count <= last )
                ct= count++; 
            else
                return NULL;    // signal StopIteration
        }
        else if( fwd_iter == -1 )
            {
                ct = last;
                count = last-1;
                fwd_iter=-2;
            }
        else if( count >= from )
            ct= count--;
        else
            return NULL;    // signal StopIteration

        Py::Long Result(ct);
        Result.increment_reference_count();
        return Result.ptr();
    }
};
