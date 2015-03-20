import sys
sys.path.insert( 0, 'pyds%d%d' % (sys.version_info[0], sys.version_info[1]) )


import pycxx_iter

IT=pycxx_iter.IterT(5,7)


for i in IT:
    print i, IT

print "refcount of IT:",sys.getrefcount(IT)

for i in IT.reversed():
    print i
print "refcount of IT:",sys.getrefcount(IT)

