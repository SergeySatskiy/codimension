" Try / except / else / finally "

try:
    a = x / y
except ZeroDivisionError:
    print "?"
else:
    print "a = ", a
finally:
    print "finally"
