/*
 [The 'BSD licence']
 Copyright (c) 2010-2013 Sergey Satskiy <sergey.satskiy@gmail.com>

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions
 are met:
 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
 2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
 3. The name of the author may not be used to endorse or promote products
    derived from this software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/*
 * There are two sources for this grammar:
 * - http://www.antlr.org/grammar/1200715779785/Python.g
 *   Copyright (c) 2004 Terence Parr and Loring Craymer
 * - http://devel-www.cyber.cz/files/python3grammarC.tar.gz
 *   Copyright (c) 2009 Ales Teska
 *
 * They were modified by Sergey Satskiy to fit python 2.7 and the
 * codimension project requirements
 *
 * $Id$
 */


grammar pythonbrief;

options
{
    language        = C;
    backtrack       = true;
    output          = AST;
    ASTLabelType    = pANTLR3_BASE_TREE;
}

tokens
{
    INDENT;
    DEDENT;

    CLASS_DEF;
    FUNC_DEF;
    BODY;

    DEL_STMT;
    PASS_STMT;
    BREAK_STMT;
    CONTINUE_STMT;
    RETURN_STMT;
    RAISE_STMT;
    YIELD_STMT;
    PRINT_STMT;
    DECOR;
    DOTTED_NAME;
    ASSERT_STMT;
    EXEC_STMT;
    GLOBAL_STMT;
    IMPORT_STMT;
    WHAT;
    AS;
    IF_STMT;
    ELSE_STMT;
    ELIF_STMT;
    WHILE_STMT;
    FOR_STMT;
    WITH_STMT;
    TEST_LIST;
    NAME_ARG;
    STAR_ARG;
    DBL_STAR_ARG;
    TRY_STMT;
    FINALLY_STMT;
    EXCEPT_STMT;

    LIST;
    DICTIONARY;
    STRING_LITERAL;
    NOT_IN;
    IS_NOT;

    TRAILER_NAME;
    HEAD_NAME;

    // Used in lexerutils.c
    CLASS_INHERITANCE;
    ARGUMENTS;
}

////////////////////////////////////////////////////////////////////////////////

@lexer::header
{
    #define ANTLR3_INLINE_INPUT_ASCII
}

// This going to context structure definition of a lexer
@lexer::context
{
    ANTLR3_INT32    implicitLineJoiningLevel;
    ANTLR3_INT32    startPos;

    pANTLR3_STACK   identStack;
    pANTLR3_VECTOR  tokens;
    void *          onEncoding;

    void (*origFree) ( struct pythonbriefLexer_Ctx_struct *  ctx );
    pANTLR3_COMMON_TOKEN (*origNextToken)( pANTLR3_TOKEN_SOURCE  toksource );
}

// Declare functions from lexerutils.c
@lexer::members
{
    pANTLR3_COMMON_TOKEN    pythonbriefLexer_createLexerToken( pANTLR3_LEXER  lexer,
                                                               ANTLR3_UINT32  tokenType,
                                                               pANTLR3_UINT8  text );
    char *                  pythonbriefLexer_syntetizeEmptyString( int  spaces );
    void                    pythonbriefLexer_initLexer( ppythonbriefLexer  ctx );
    void                    searchForCoding( ppythonbriefLexer  ctx,
                                             char *             lineStart,
                                             ANTLR3_UINT32      lineNumber );
}

@parser::members
{
    pANTLR3_BASE_TREE pythonbriefInsertInheritance( struct pythonbriefParser_Ctx_struct *  ctx,
                                                    pANTLR3_VECTOR                         args );

    pANTLR3_BASE_TREE pythonbriefInsertArguments( struct pythonbriefParser_Ctx_struct *  ctx,
                                                  pANTLR3_VECTOR                         args );
    void addTypedName( pANTLR3_VECTOR       v,
                       ANTLR3_UINT32        type,
                       pANTLR3_UINT8        name );
}

// This going to lexer constructor
@lexer::apifuncs
{
    pythonbriefLexer_initLexer( ctx );
}



/////////////////////////////// PARSER /////////////////////////////////////////

single_input    : NEWLINE
                | simple_stmt
                | compound_stmt NEWLINE
                ;

file_input      : EOF
                | ( NEWLINE | stmt )*
                    -> stmt*
                | COMMENT EOF
                ;

eval_input      : NEWLINE*  testlist  NEWLINE*
                ;

decorator       : '@' dotted_name ( LPAREN decor_arglist? RPAREN )? NEWLINE
                    -> ^( DECOR dotted_name decor_arglist? )
                ;
decorators      : decorator+
                ;

/* To distinguish it from arglist which is also used in other place */
decor_arglist
                @init
                {
                    pANTLR3_VECTOR  args = antlr3VectorNew( ANTLR3_VECTOR_INTERNAL_SIZE );
                }
                @after
                {
                    args->free( args );
                }
                : ( a1 = argument { addTypedName( args, NAME_ARG, $a1.text->chars ); } COMMA )*
                (     (a2 = argument { addTypedName( args, NAME_ARG, $a2.text->chars ); } )?
                    | STAR t1 = test { addTypedName( args, STAR_ARG, $t1.text->chars ); } ( COMMA a3 = argument { addTypedName( args, NAME_ARG, $a3.text->chars ); } )* ( COMMA DOUBLESTAR t2 = test { addTypedName( args, DBL_STAR_ARG, $t2.text->chars ); } )?
                    | DOUBLESTAR t3 = test { addTypedName( args, DBL_STAR_ARG, $t3.text->chars ); }
                )
                    -> { pythonbriefInsertArguments( ctx, args ) }
                ;

                /* keyword position is saved in user1 field,
                   colon position is saved in user2 field */
funcdef         : decorators? kw = 'def'
                        n = NAME { $n->user1 = ($kw->line << 16) + $kw->charPosition; }
                        parameters
                        c = COLON { $n->user2 = ($c->line << 16) + $c->charPosition; } suite
                    -> ^( FUNC_DEF NAME  decorators? parameters  ^( BODY suite ) )
                ;

parameters      : LPAREN  varargslist?  RPAREN
                    -> varargslist?
                ;

defparameter    : fpdef ( '=' test )?
                ;

varargslist
                @init
                {
                    pANTLR3_VECTOR  f_args = antlr3VectorNew( ANTLR3_VECTOR_INTERNAL_SIZE );
                }
                @after
                {
                    f_args->free( f_args );
                }
                : (( d = defparameter { addTypedName( f_args, NAME_ARG, $d.text->chars ); } COMMA )*
                    ( STAR n1 = NAME { addTypedName( f_args, STAR_ARG, $n1.text->chars ); } ( COMMA DOUBLESTAR n2 = NAME { addTypedName( f_args, DBL_STAR_ARG, $n2.text->chars ); } )? | DOUBLESTAR n3 = NAME { addTypedName( f_args, DBL_STAR_ARG, $n3.text->chars ); } )
                | dp1 = defparameter { addTypedName( f_args, NAME_ARG, $dp1.text->chars ); }
                    ( options { greedy = true; } : COMMA dp2 = defparameter { addTypedName( f_args, NAME_ARG, $dp2.text->chars ); } )* COMMA? )
                    -> { pythonbriefInsertArguments( ctx, f_args ) }
                ;

fpdef           : NAME
                    -> NAME
                | LPAREN fplist RPAREN
                    -> fplist
                ;

fplist          : fpdef ( options { greedy = true; } : COMMA fpdef )*  COMMA?
                ;

stmt            : simple_stmt
                | compound_stmt
                ;

simple_stmt     : small_stmt ( options { greedy = true; } : SEMI small_stmt )*  SEMI?  (NEWLINE | EOF)
                    -> small_stmt+
                ;

small_stmt      : expr_stmt
                | print_stmt
                | del_stmt
                | pass_stmt
                | flow_stmt
                | import_stmt
                | global_stmt
                | exec_stmt
                | assert_stmt
                ;

expr_stmt       : testlist
                    (
                        augassign^ ( yield_expr | testlist )
                        | ( ASSIGN^ ( yield_expr | testlist ) )*
                    )
                ;

augassign       : '+='
                | '-='
                | '*='
                | '/='
                | '%='
                | '&='
                | '|='
                | '^='
                | '<<='
                | '>>='
                | '**='
                | '//='
                ;

// Python 3 (or python 2 with future imported) can have print as a function
// so allow both of them.
print_stmt      : 'print' ( (( printlist | '>>' printlist )?) | (LPAREN arglist? RPAREN) )
                    -> PRINT_STMT
                ;

printlist       : test ( options { k = 2; } : COMMA test )*  COMMA?
                ;

del_stmt        : 'del' exprlist
                    -> DEL_STMT
                ;

pass_stmt       : 'pass'
                    -> PASS_STMT
                ;

flow_stmt       : break_stmt
                | continue_stmt
                | return_stmt
                | raise_stmt
                | yield_stmt
                ;

break_stmt      : 'break'
                    -> BREAK_STMT
                ;

continue_stmt   : 'continue'
                    -> CONTINUE_STMT
                ;

return_stmt     : 'return' testlist?
                    -> RETURN_STMT
                ;

yield_stmt      : yield_expr
                    -> YIELD_STMT
                ;

raise_stmt      : 'raise' ( test ( COMMA test ( COMMA test )? )? )?
                    -> RAISE_STMT
                ;

import_stmt     : import_name
                    -> ^( IMPORT_STMT import_name )
                | import_from
                    -> ^( IMPORT_STMT import_from )
                ;

import_name     : 'import' dotted_as_names
                    -> dotted_as_names
                ;

import_from     : 'from' import_path 'import'
                (   STAR
                        -> import_path ^( WHAT STAR )
                    | import_as_names
                        -> import_path ^( WHAT import_as_names )
                    | LPAREN import_as_names RPAREN
                        -> import_path ^( WHAT import_as_names )
                )
                ;

import_path     : DOT* dotted_name
                    -> dotted_name
                | DOT+
                    -> ^( DOTTED_NAME DOT+ )
                ;


import_as_name  : n1 = NAME ( 'as' n2 = NAME )?
                    -> $n1 ^( AS $n2 )?
                ;

dotted_as_name  : dotted_name ( 'as' NAME )?
                    -> dotted_name ^( AS NAME )?
                ;

import_as_names : import_as_name ( COMMA import_as_name) *  COMMA?
                    -> import_as_name+
                ;

dotted_as_names : dotted_as_name ( COMMA dotted_as_name )*
                    -> dotted_as_name+
                ;

dotted_name     : NAME ( DOT NAME )*
                    -> ^( DOTTED_NAME NAME+ )
                ;

global_stmt     : 'global' NAME ( options { k = 2; } : COMMA NAME )*
                    -> GLOBAL_STMT
                ;

exec_stmt       : 'exec' expr ( 'in' test ( COMMA test )? )?
                    -> EXEC_STMT
                ;

assert_stmt     : 'assert' test ( COMMA test )?
                    -> ASSERT_STMT
                ;

compound_stmt   : if_stmt
                | while_stmt
                | for_stmt
                | try_stmt
                | with_stmt
                | funcdef
                | classdef
                ;

if_stmt         : 'if' test COLON s1 = suite elif_clause*  ( 'else' COLON s2 = suite )?
                    -> ^( IF_STMT  $s1  elif_clause*  ^( ELSE_STMT  $s2 )? )
                ;

elif_clause     : 'elif' test COLON suite
                    -> ^( ELIF_STMT suite )
                ;

while_stmt      : 'while' test COLON s1 = suite ( 'else' COLON s2 = suite )?
                    -> ^( WHILE_STMT  $s1  ^( ELSE_STMT  $s2 )? )
                ;

for_stmt        : 'for' exprlist 'in' testlist COLON s1 = suite ( 'else' COLON s2 = suite )?
                    -> ^( FOR_STMT  $s1  ^( ELSE_STMT  $s2 )? )
                ;

try_stmt        : 'try' COLON suite try_closure
                    -> ^( TRY_STMT  suite  try_closure )
                ;

try_closure     : except_closure+ ( 'else' COLON s1 = suite )? ( 'finally' COLON s2 = suite )?
                    -> except_closure+  ^( ELSE_STMT  $s1 )?  ^( FINALLY_STMT  $s2 )?
                | 'finally' COLON suite
                    -> ^( FINALLY_STMT  suite )
                ;

except_closure  : except_clause COLON suite
                    -> ^( EXCEPT_STMT  suite )
                ;

with_stmt       : 'with' with_item ( COMMA with_item )* COLON suite
                    -> ^( WITH_STMT  suite )
                ;

with_item       : test ( 'as' expr )?
                ;

except_clause   : 'except' ( test ( ( 'as' | COMMA ) test )? )?
                ;

suite           : simple_stmt
                    -> simple_stmt
                | NEWLINE  INDENT  stmt+  ( DEDENT | EOF )
                    -> stmt+
                ;

testlist_safe   : old_test ( ( COMMA old_test )+  COMMA? )?
                ;

old_test        : or_test
                | old_lambdef
                ;

old_lambdef     : 'lambda' varargslist? COLON old_test
                ;

test            : or_test ( 'if' or_test 'else' test )?
                | lambdef
                ;

or_test         : and_test ( 'or'^ and_test )*
                ;

and_test        : not_test ( 'and'^ not_test )*
                ;

not_test        : 'not' not_test
                | comparison
                ;

comparison      : expr ( comp_op^ expr )*
                ;

comp_op         : '<'
                | '>'
                | '=='
                | '>='
                | '<='
                | '<>'
                | '!='
                | 'in'
                | 'not' 'in'
                    -> NOT_IN
                | 'is'
                | 'is' 'not'
                    -> IS_NOT
                ;

expr            : xor_expr ( '|'^ xor_expr )*
                ;

xor_expr        : and_expr ( '^'^ and_expr )*
                ;

and_expr        : shift_expr ( '&'^ shift_expr )*
                ;

shift_expr      : arith_expr ( ( '<<' | '>>' )^ arith_expr )*
                ;

arith_expr      : term ( ( '+' | '-' )^ term )*
                ;

term            : factor ( ( STAR | '/' | '%' | '//' )^ factor )*
                ;

factor          : '+'^ factor
                | '-'^ factor
                | '~'^ factor
                | power
                ;

power           : atom  trailer*  ( options { greedy = true; } : DOUBLESTAR factor )?
                ;

// Attention: the sequence of rules is very important.
//            If the rule 'LPAREN RPAREN' is moved down - the 'a = ()'
//            statement will not be recognised.
//            And I still don't understand why the second rule does not work
//            for the first 'special case'.
atom            : LPAREN RPAREN
                | LPAREN ( yield_expr -> yield_expr | testlist_comp -> testlist_comp )? RPAREN
                | LBRACK listmaker? RBRACK
                    -> LIST
                | LCURLY dictorsetmaker? RCURLY
                    -> DICTIONARY
                | '`' testlist '`'
                | NAME
                    -> ^( HEAD_NAME  NAME )
                | INTEGER
                | LONGINT
                | FLOATNUMBER
                | IMAGNUMBER
                | string
                    -> ^( STRING_LITERAL  string )
//                | TRUE        Sick! Some modules have True & False as a part of the dotted name
//                | FALSE       So it could not be here! The 'True' and 'False' will be identifiers!
//                | 'None'      'None' goes into this cathegory just in case
                ;

listmaker       : test
                (   list_for
                    | ( options { greedy = true; } : COMMA test )*  COMMA?
                )
                ;

testlist_comp   : test
                (   comp_for -> comp_for
                    | ( options { k = 2; } : COMMA test )*  COMMA? -> test*
                )
                ;

lambdef         : 'lambda' varargslist? COLON test
                ;

trailer         : LPAREN arglist? RPAREN
                    -> arglist?
                | LBRACK subscriptlist RBRACK
                    -> LIST
                | DOT NAME
                    -> ^( TRAILER_NAME NAME )
                ;

subscriptlist   : subscript ( options { greedy = true; } : COMMA subscript )*  COMMA?
                ;

subscript       : DOT DOT DOT
                | test ( COLON test?  ( sliceop )? )?
                | COLON test?  sliceop?
                ;

sliceop         : COLON test?
                ;

exprlist        : expr ( options { k = 2; } : COMMA expr )*  COMMA?
                    -> expr+
                ;

testlist        : test ( options { k = 2; } : COMMA test )*  COMMA?
                    -> ^( TEST_LIST  test+ )
                ;

dictorsetmaker  : test ( dictmakerclause | setmakerclause )
                ;

dictmakerclause : COLON test ( comp_for | ( COMMA test COLON test )* COMMA? )
                ;

setmakerclause  : comp_for | ( COMMA test )* COMMA?
                ;


                /* keyword position is saved in user1 field,
                   colon position is saved in user2 field */
classdef        : decorators? kw = 'class'
                        n = NAME { $n->user1 = ($kw->line << 16) + $kw->charPosition; }
                        ( LPAREN inheritancelist? RPAREN )?
                        c = COLON { $n->user2 = ($c->line << 16) + $c->charPosition; } suite
                    -> ^( CLASS_DEF  NAME  decorators?  inheritancelist?  ^( BODY suite ) )
                ;

inheritancelist
                @init
                {
                    pANTLR3_VECTOR  arguments = antlr3VectorNew( ANTLR3_VECTOR_INTERNAL_SIZE );
                }
                @after
                {
                    arguments->free( arguments );
                }
                : t1 = test { vectorAdd( arguments, $t1.text->chars, NULL ); }
                    ( options { k = 2; } : COMMA t2 = test { vectorAdd( arguments, $t2.text->chars, NULL ); } )*  COMMA?
                    -> { pythonbriefInsertInheritance( ctx, arguments ) }
                ;


arglist         : ( argument  COMMA )*
                (     argument?
                    | STAR test ( COMMA argument )* ( COMMA DOUBLESTAR test )?
                    | DOUBLESTAR test
                )
                ;

argument        : test ( ( '=' test ) | comp_for )?
                ;

list_iter       : list_for
                | list_if
                ;

list_for        : 'for' exprlist 'in' testlist_safe  list_iter?
                ;

list_if         : 'if' old_test  list_iter?
                ;

comp_iter       : comp_for
                | comp_if
                ;

comp_for        : 'for' exprlist 'in' or_test comp_iter?
                ;

comp_if         : 'if' old_test comp_iter?
                ;

testlist1       : test ( options { k = 2; } : COMMA  test )?
                ;

yield_expr      : 'yield'  testlist?
                ;

string          : STRINGLITERAL+
                | BYTESLITERAL +
                ;


//////////////////////////////////// LEXER /////////////////////////////////////

// String and Bytes literals
// http://docs.python.org/3.1/reference/lexical_analysis.html#string-and-bytes-literals

STRINGLITERAL   : STRINGPREFIX? ( SHORTSTRING | LONGSTRING ) ;

fragment STRINGPREFIX
                : ( 'r' | 'R' | 'u' | 'U' | 'ur' | 'UR' | 'Ur' | 'uR' ) ;

fragment SHORTSTRING
                : '"' ( ESCAPESEQ | ~( '\\' | '\n' | '"' ) )* '"'
                | '\'' ( ESCAPESEQ | ~( '\\' | '\n' | '\'' ) )* '\''
                ;

fragment LONGSTRING
                : '\'\'\'' ( options { greedy = false; } : TRIAPOS )* '\'\'\''
                | '"""' ( options { greedy = false; } : TRIQUOTE )* '"""'
                ;

BYTESLITERAL    : BYTESPREFIX ( SHORTBYTES | LONGBYTES ) ;

fragment BYTESPREFIX
                : ( 'b' | 'B' ) ( 'r' | 'R' )? ;

fragment SHORTBYTES
                : '"' ( ESCAPESEQ | ~( '\\' | '\n' | '"' ) )* '"'
                | '\'' ( ESCAPESEQ | ~( '\\' | '\n' | '\'' ) )* '\''
                ;

fragment LONGBYTES
                : '\'\'\'' ( options { greedy = false; } : TRIAPOS )* '\'\'\''
                | '"""' ( options { greedy = false; } : TRIQUOTE )* '"""'
                ;

fragment TRIAPOS
                : ( '\'' '\'' | '\''? ) ( ESCAPESEQ | ~( '\\' | '\'' ) )+ ;

fragment TRIQUOTE
                : ( '"' '"' | '"'? ) ( ESCAPESEQ | ~( '\\' | '"' ) )+ ;

fragment ESCAPESEQ
                : '\\' . ;


// Integer literals
// http://docs.python.org/3.1/reference/lexical_analysis.html#integer-literals

INTEGER         : DECIMALINTEGER | OCTINTEGER | HEXINTEGER | BININTEGER;
LONGINT         : INTEGER ( 'l' | 'L' );        // For python 2

fragment DECIMALINTEGER
                : NONZERODIGIT DIGIT* | '0' ;

fragment NONZERODIGIT
                : '1' .. '9' ;

fragment DIGIT
                : '0' .. '9' ;

fragment OCTINTEGER
                : '0' ( 'o' | 'O' )? OCTDIGIT+;

fragment HEXINTEGER
                : '0' ( 'x' | 'X' ) HEXDIGIT+ ;

fragment BININTEGER
                : '0' ( 'b' | 'B' ) BINDIGIT+ ;

fragment OCTDIGIT
                : '0' .. '7' ;
fragment NONZEROOCTDIGIT
                : '1' .. '7' ;

fragment HEXDIGIT
                : DIGIT | 'a' .. 'f' | 'A' .. 'F' ;

fragment BINDIGIT
                : '0' | '1' ;



// Floating point literals
// http://docs.python.org/3.1/reference/lexical_analysis.html#floating-point-literals

FLOATNUMBER     : POINTFLOAT | EXPONENTFLOAT ;

fragment POINTFLOAT
                : ( INTPART? FRACTION )
                | ( INTPART '.' )
                ;

fragment EXPONENTFLOAT
                : ( INTPART | POINTFLOAT ) EXPONENT ;

fragment INTPART
                : DIGIT+ ;

fragment FRACTION
                : '.' DIGIT+ ;

fragment EXPONENT
                : ( 'e' | 'E' ) ( '+' | '-' )? DIGIT+ ;


// Imaginary literals
// http://docs.python.org/3.1/reference/lexical_analysis.html#imaginary-literals

IMAGNUMBER      : ( FLOATNUMBER | INTPART ) ( 'j' | 'J' ) ;


// Identifiers
// http://docs.python.org/3.1/reference/lexical_analysis.html#identifiers

NAME            : ID_START ID_CONTINUE* ;

// TODO: <all characters in general categories Lu, Ll, Lt, Lm, Lo, Nl,
//       the underscore, and characters with the Other_ID_Start property>
// - see python3_pep3131.g
fragment ID_START
                : '_'
                | 'A'.. 'Z'
                | 'a' .. 'z'
                ;

// TODO: <all characters in id_start, plus characters in the categories
//       Mn, Mc, Nd, Pc and others with the Other_ID_Continue property>
// - see python3_pep3131.g
fragment ID_CONTINUE
                : '_'
                | 'A'.. 'Z'
                | 'a' .. 'z'
                | '0' .. '9'
                ;

STAR            : '*' ;
DOUBLESTAR      : '**' ;




// Delimiters
// http://docs.python.org/3.1/reference/lexical_analysis.html#delimiters

// Implicit line joining
// http://docs.python.org/3.1/reference/lexical_analysis.html#implicit-line-joining
LPAREN          : '('   { ctx->implicitLineJoiningLevel += 1; } ;
RPAREN          : ')'   { ctx->implicitLineJoiningLevel -= 1; } ;
LBRACK          : '['   { ctx->implicitLineJoiningLevel += 1; } ;
RBRACK          : ']'   { ctx->implicitLineJoiningLevel -= 1; } ;
LCURLY          : '{'   { ctx->implicitLineJoiningLevel += 1; } ;
RCURLY          : '}'   { ctx->implicitLineJoiningLevel -= 1; } ;

COMMA           : ',' ;
COLON           : ':' ;
DOT             : '.' ;
SEMI            : ';' ;

ASSIGN          : '=' ;

// Line structure
// http://docs.python.org/3.1/reference/lexical_analysis.html#line-structure

/** Consume a newline and any whitespace at start of next line
 *  unless the next line contains only white space, in that case
 *  emit a newline.
 */
CONTINUED_LINE  : '\\' ( '\r' )? '\n' ( ' ' | '\t' )* { $channel = HIDDEN; }
                ( NEWLINE { static char __newlinebuf[] = "\n"; EMITNEW( pythonbriefLexer_createLexerToken( LEXER, TOKTEXT( NEWLINE, __newlinebuf ) ) ); } )?
                ;

/** Treat a sequence of blank lines as a single blank line.  If
 *  nested within a (..), {..}, or [..], then ignore newlines.
 *  If the first newline starts in column one, they are to be ignored.
 *
 *  Frank Wierzbicki added: Also ignore FORMFEEDS (\u000C).
 */
NEWLINE         : ( '\u000C'? '\r'? '\n' )+
                {
                    if ( ( ctx->startPos == 0 ) || ( ctx->implicitLineJoiningLevel > 0 ) )
                    {
                        $channel = HIDDEN;
                    }
                }
                ;

// Whitespace
// http://docs.python.org/3.1/reference/lexical_analysis.html#whitespace-between-tokens

WS              : { ctx->startPos > 0 }?=> ( ' ' | '\t' )+ { $channel = HIDDEN; };

// http://docs.python.org/3.1/reference/lexical_analysis.html#indentation]
/** Grab everything before a real symbol.  Then if newline, kill it
 *  as this is a blank line.  If whitespace followed by comment, kill it
 *  as it's a comment on a line by itself.
 *
 *  Ignore leading whitespace when nested in [..], (..), {..}.
 */
LEADING_WS
    @init
    {
        int spaces = 0;
    }
    : { ctx->startPos == 0 }?=>
    (
        {ctx->implicitLineJoiningLevel > 0}? ( ' ' | '\t' )+ { $channel = HIDDEN; }
        |
        (
              ' '  { spaces += 1; }
            | '\t' { spaces += 8; spaces -= (spaces \% 8); }
        )+
            {
                EMITNEW( pythonbriefLexer_createLexerToken( LEXER, TOKTEXT( LEADING_WS, pythonbriefLexer_syntetizeEmptyString( spaces ) ) ) );
            }
        // kill trailing newline if present and then ignore
        (
            '\r'? '\n'
            {
                if ( LTOKEN != NULL )
                {
                    LTOKEN->setChannel( LTOKEN, HIDDEN );
                }
                else
                {
                    $channel = HIDDEN;
                }
            }
        )*
    )
    ;


// Comments
// http://docs.python.org/3.1/reference/lexical_analysis.html#comments

COMMENT
    @init
    {
        $channel = HIDDEN;

        ANTLR3_UINT32   initLine = ctx->pLexer->input->line;
        char *          lineStartBuf = (char*)ctx->pLexer->input->currentLine;
    }
    : (
      { ctx->startPos == 0 }?=> ( ' ' | '\t' )* a='#' ( ~'\n' )* '\n'+
    | { ctx->startPos > 0  }?=> b='#' ( ~'\n' )* // let NEWLINE handle \n unless char pos==0 for '#'
      ) {
            if ( initLine <= 2 ) searchForCoding( ctx, lineStartBuf, initLine );
        }
    ;


// Following two lexer rules are imaginary, condition is never meet ... they are here just to suppress warnings
DEDENT: { 0 == 1 }?=> ( '\n' );
INDENT: { 0 == 1 }?=> ( '\n' );

