//
//  Copyright (c) 2008-2009 Barry A. Scott
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT  HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR  IMPLIED WARRANTIES, INCLUDING,  BUT NOT  LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND  FITNESS FOR A PARTICULAR  PURPOSE
// ARE  DISCLAIMED.  IN  NO  EVENT  SHALL  THE  REGENTS  OF  THE  UNIVERSITY OF
// CALIFORNIA, THE U.S.  DEPARTMENT  OF  ENERGY OR CONTRIBUTORS BE  LIABLE  FOR
// ANY  DIRECT,  INDIRECT,  INCIDENTAL,  SPECIAL,  EXEMPLARY,  OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT  LIMITED TO, PROCUREMENT OF  SUBSTITUTE GOODS OR
// SERVICES; LOSS OF  USE, DATA, OR PROFITS; OR  BUSINESS INTERRUPTION) HOWEVER
// CAUSED  AND  ON  ANY  THEORY  OF  LIABILITY,  WHETHER  IN  CONTRACT,  STRICT
// LIABILITY, OR TORT  (INCLUDING NEGLIGENCE OR OTHERWISE)  ARISING IN ANY  WAY
// OUT OF THE  USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
// DAMAGE.
//
//  test_assert.hxx
//  
class TestError
{
public:
    TestError( const std::string &description )
    : m_description( description )
    {}

    ~TestError()
    {}

    std::string m_description;
};

template <TEMPLATE_TYPENAME T> static void test_assert_scaler( const char *description, const char *type, T benchmark, T value )
{
    std::ostringstream full_description;
    full_description << description << ": " << type << " benchmark=" << benchmark << " " << type << " value=" << value;

    if( benchmark != value )
    {
        throw TestError( full_description.str() );
    }
    else
    {
        std::cout << "PASSED: " << full_description.str() << std::endl;
    }
}

static void test_assert( const char *description, bool benchmark, bool value )
{
    test_assert_scaler( description, "bool", benchmark, value );
}

static void test_assert( const char *description, long benchmark, long value )
{
    test_assert_scaler( description, "long", benchmark, value );
}

static void test_assert( const char *description, int benchmark, int value )
{
    test_assert_scaler( description, "int", benchmark, value );
}

static void test_assert( const char *description, size_t benchmark, size_t value )
{
    test_assert_scaler( description, "size_t", benchmark, value );
}

static void test_assert( const char *description, int benchmark, size_t value )
{
    test_assert_scaler( description, "size_t", size_t( benchmark ), value );
}

static void test_assert( const char *description, double benchmark, double value )
{
    test_assert_scaler( description, "float", benchmark, value );
}

static void test_assert( const char *description, const std::string &benchmark, const std::string &value )
{
    test_assert_scaler( description, "std::string", benchmark, value );
}

static void test_assert( const char *description, const Py::Object &benchmark, const Py::Object &value )
{
    test_assert_scaler( description, "Py::Object", benchmark, value );
}
