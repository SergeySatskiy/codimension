""" Simple test of effect of exdented comment which changed block depth incorrectly."""
def foo1():
    a = "Test 1 OK"
#   Comment 1 should NOT affect indentation
    if a:	# should work, but ends function if comment affects indentation
        print a

def foo2():
    if True:
#   Comment 2 should NOT affect indentation
        return "Test 2 OK"

def foo3():
    a = "Test 3 OK"
#   Comment 2 should NOT affect indentation
    if a:	# next line in error if comment affect indentation
        return a

def foo4():
# this comment at start of function should no effect compilation
    if True:
        return "Test 4 OK"
# this command should also not effect compilation
    return "Test 4 Failed"
    
foo1()
print foo2()
print foo3()
print foo4()

if True:
        # this comment should not effect the block structure of the program
    print "Test 5 OK"
else:
        # this comment should not effect program compilation or execution
    print "Test 5 failed!!!"

