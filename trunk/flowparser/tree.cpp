
#include <sys/stat.h>

#include <Python.h>
#include <node.h>
#include <grammar.h>
#include <parsetok.h>
#include <graminit.h>
#include <errcode.h>
#include <token.h>

#include <iostream>
using namespace std;


extern grammar _PyParser_Grammar; // From graminit.c


struct PythonEnvironment
{
  PythonEnvironment()   { Py_Initialize(); }
  ~PythonEnvironment()  { Py_Finalize();   }
};



string errorCodeToString( int  error )
{
    switch ( error )
    {
        case E_OK:          return "E_OK";
        case E_EOF:         return "E_EOF";
        case E_INTR:        return "E_INTR";
        case E_TOKEN:       return "E_TOKEN";
        case E_SYNTAX:      return "E_SYNTAX";
        case E_NOMEM:       return "E_NOMEM";
        case E_DONE:        return "E_DONE";
        case E_ERROR:       return "E_ERROR";
        case E_TABSPACE:    return "E_TABSPACE";
        case E_OVERFLOW:    return "E_OVERFLOW";
        case E_TOODEEP:     return "E_TOODEEP";
        case E_DEDENT:      return "E_DEDENT";
        case E_DECODE:      return "E_DECODE";
        case E_EOFS:        return "E_EOFS";
        case E_EOLS:        return "E_EOLS";
        case E_LINECONT:    return "E_LINECONT";
        default:            break;
    }

    char    buf[256];
    sprintf( buf, "Unknown code %d", error );
    return buf;
}


void printError( perrdetail *  error )
{
    if ( error->error == E_OK || error->error == E_DONE )
    {
        cout << "No errors found" << endl;
        return;
    }

    cout << "Error structure" << endl
         << "  error: " << errorCodeToString( error->error ) << endl
         << "  filename: " << error->filename << endl
         << "  lineno: " << error->lineno << endl
         << "  offset: " << error->offset << endl;
    if ( error->text != NULL )
         cout << "  text: " << error->text << endl;
    cout << "  token: " << error->token << endl
         << "  expected: " << error->expected << endl;
}


string  nodeTypeToString( int  nodeType  )
{
    switch ( nodeType )
    {
        case single_input:      return "single_input";
        case file_input:        return "file_input";
        case eval_input:        return "eval_input";
        case decorator:         return "decorator";
        case decorators:        return "decorators";
        case decorated:         return "decorated";
        case funcdef:           return "funcdef";
        case parameters:        return "parameters";
        case varargslist:       return "varargslist";
        case fpdef:             return "fpdef";
        case fplist:            return "fplist";
        case stmt:              return "stmt";
        case simple_stmt:       return "simple_stmt";
        case small_stmt:        return "small_stmt";
        case expr_stmt:         return "expr_stmt";
        case augassign:         return "augassign";
        case print_stmt:        return "print_stmt";
        case del_stmt:          return "del_stmt";
        case pass_stmt:         return "pass_stmt";
        case flow_stmt:         return "flow_stmt";
        case break_stmt:        return "break_stmt";
        case continue_stmt:     return "continue_stmt";
        case return_stmt:       return "return_stmt";
        case yield_stmt:        return "yield_stmt";
        case raise_stmt:        return "raise_stmt";
        case import_stmt:       return "import_stmt";
        case import_name:       return "import_name";
        case import_from:       return "import_from";
        case import_as_name:    return "import_as_name";
        case dotted_as_name:    return "dotted_as_name";
        case import_as_names:   return "import_as_names";
        case dotted_as_names:   return "dotted_as_names";
        case dotted_name:       return "dotted_name";
        case global_stmt:       return "global_stmt";
        case exec_stmt:         return "exec_stmt";
        case assert_stmt:       return "assert_stmt";
        case compound_stmt:     return "compound_stmt";
        case if_stmt:           return "if_stmt";
        case while_stmt:        return "while_stmt";
        case for_stmt:          return "for_stmt";
        case try_stmt:          return "try_stmt";
        case with_stmt:         return "with_stmt";
        case with_item:         return "with_item";
        case except_clause:     return "except_clause";
        case suite:             return "suite";
        case testlist_safe:     return "testlist_safe";
        case old_test:          return "old_test";
        case old_lambdef:       return "old_lambdef";
        case test:              return "test";
        case or_test:           return "or_test";
        case and_test:          return "and_test";
        case not_test:          return "not_test";
        case comparison:        return "comparison";
        case comp_op:           return "comp_op";
        case expr:              return "expr";
        case xor_expr:          return "xor_expr";
        case and_expr:          return "and_expr";
        case shift_expr:        return "shift_expr";
        case arith_expr:        return "arith_expr";
        case term:              return "term";
        case factor:            return "factor";
        case power:             return "power";
        case atom:              return "atom";
        case listmaker:         return "listmaker";
        case testlist_comp:     return "testlist_comp";
        case lambdef:           return "lambdef";
        case trailer:           return "trailer";
        case subscriptlist:     return "subscriptlist";
        case subscript:         return "subscript";
        case sliceop:           return "sliceop";
        case exprlist:          return "exprlist";
        case testlist:          return "testlist";
        case dictorsetmaker:    return "dictorsetmaker";
        case classdef:          return "classdef";
        case arglist:           return "arglist";
        case argument:          return "argument";
        case list_iter:         return "list_iter";
        case list_for:          return "list_for";
        case list_if:           return "list_if";
        case comp_iter:         return "comp_iter";
        case comp_for:          return "comp_for";
        case comp_if:           return "comp_if";
        case testlist1:         return "testlist1";
        case encoding_decl:     return "encoding_decl";
        case yield_expr:        return "yield_expr";

        case ENDMARKER:         return "ENDMARKER";
        case NAME:              return "NAME";
        case NUMBER:            return "NUMBER";
        case STRING:            return "STRING";
        case NEWLINE:           return "NEWLINE";
        case INDENT:            return "INDENT";
        case DEDENT:            return "DEDENT";
        case LPAR:              return "LPAR";
        case RPAR:              return "RPAR";
        case LSQB:              return "LSQB";
        case RSQB:              return "RSQB";
        case COLON:             return "COLON";
        case COMMA:             return "COMMA";
        case SEMI:              return "SEMI";
        case PLUS:              return "PLUS";
        case MINUS:             return "MINUS";
        case STAR:              return "STAR";
        case SLASH:             return "SLASH";
        case VBAR:              return "VBAR";
        case AMPER:             return "AMPER";
        case LESS:              return "LESS";
        case GREATER:           return "GREATER";
        case EQUAL:             return "EQUAL";
        case DOT:               return "DOT";
        case PERCENT:           return "PERCENT";
        case BACKQUOTE:         return "BACKQUOTE";
        case LBRACE:            return "LBRACE";
        case RBRACE:            return "RBRACE";
        case EQEQUAL:           return "EQEQUAL";
        case NOTEQUAL:          return "NOTEQUAL";
        case LESSEQUAL:         return "LESSEQUAL";
        case GREATEREQUAL:      return "GREATEREQUAL";
        case TILDE:             return "TILDE";
        case CIRCUMFLEX:        return "CIRCUMFLEX";
        case LEFTSHIFT:         return "LEFTSHIFT";
        case RIGHTSHIFT:        return "RIGHTSHIFT";
        case DOUBLESTAR:        return "DOUBLESTAR";
        case PLUSEQUAL:         return "PLUSEQUAL";
        case MINEQUAL:          return "MINEQUAL";
        case STAREQUAL:         return "STAREQUAL";
        case SLASHEQUAL:        return "SLASHEQUAL";
        case PERCENTEQUAL:      return "PERCENTEQUAL";
        case AMPEREQUAL:        return "AMPEREQUAL";
        case VBAREQUAL:         return "VBAREQUAL";
        case CIRCUMFLEXEQUAL:   return "CIRCUMFLEXEQUAL";
        case LEFTSHIFTEQUAL:    return "LEFTSHIFTEQUAL";
        case RIGHTSHIFTEQUAL:   return "RIGHTSHIFTEQUAL";
        case DOUBLESTAREQUAL:   return "DOUBLESTAREQUAL";
        case DOUBLESLASH:       return "DOUBLESLASH";
        case DOUBLESLASHEQUAL:  return "DOUBLESLASHEQUAL";
        case AT:                return "AT";
        case OP:                return "OP";
        case ERRORTOKEN:        return "ERRORTOKEN";
        case N_TOKENS:          return "N_TOKENS";

        default:                break;
    }

    char    buf[256];
    sprintf( buf, "Unknown type %d", nodeType );
    return buf;
}



void printTree( node *  n, size_t  level )
{
    for ( size_t k = 0; k < level * 2; ++k )
        cout << " ";
    cout << "Type: " << nodeTypeToString( n->n_type ) << " line: " << n->n_lineno << " col: " << n->n_col_offset;
    if ( n->n_str != NULL )
         cout << " str: " << n->n_str;
    cout << endl;
    for ( int k = 0; k < n->n_nchildren; ++k )
        printTree( &(n->n_child[ k ]), level + 1 );
}


int getTotalLines( node *  tree )
{
    if ( tree == NULL )
        return -1;

    if ( tree->n_type != file_input )
        tree = &(tree->n_child[ 0 ]);

    for ( int k = 0; k < tree->n_nchildren; ++k )
    {
        node *  child = &(tree->n_child[ k ]);
        if ( child->n_type == ENDMARKER )
            return child->n_lineno;
    }
    return -1;
}


int main( int  argc, char *  argv[] )
{
    if ( argc != 2 && argc != 3 )
    {
        cerr << "Usage: " << argv[0] << " <python file name> [loops]" << endl;
        return EXIT_FAILURE;
    }

    FILE *              f = fopen( argv[1], "r" );
    if ( f == NULL )
    {
        cerr << "Cannot open " << argv[1] << endl;
        return EXIT_FAILURE;
    }

    int     loops = 1;
    if ( argc == 3 )
    {
        loops = atoi( argv[2] );
        if ( loops <= 0 )
        {
            cerr << "Number of loops must be >= 1" << endl;
            return EXIT_FAILURE;
        }
    }


    struct stat     st;
    stat( argv[1], &st );

    char            buffer[st.st_size + 2];
    fread( buffer, st.st_size, 1, f );
    buffer[ st.st_size ] = '\n';
    buffer[ st.st_size + 1 ] = '\0';
    fclose( f );

    PythonEnvironment   pyEnv;
    perrdetail          error;
    PyCompilerFlags     flags = { 0 };

    for ( int  k = 0; k < loops; ++k )
    {
        node *              n = PyParser_ParseStringFlagsFilename(
                                    buffer,
                                    argv[1],
                                    &_PyParser_Grammar,
                                    file_input, &error, flags.cf_flags );

        if ( n == NULL )
        {
            cerr << "Parser error" << endl;
            printError( &error );
            return EXIT_FAILURE;
        }

        if ( loops == 1 )
        {
            printTree( n, 0 );
            printError( &error );
            cout << "Total number of lines: " << getTotalLines( n ) << endl;
        }
        PyNode_Free( n );
    }

    return EXIT_SUCCESS;
}

