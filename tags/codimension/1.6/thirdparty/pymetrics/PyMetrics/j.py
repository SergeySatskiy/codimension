pfx = ''
try:
  n = pfx+'simple'
  m = __import__(n,globals(),locals(),['xxx'])
  print m.__doc__
  n = pfx+'sloc'
  m = __import__(n,globals(),locals(),['xxx'])
  print m.__doc__
  n = pfx+'xxxx'
  m = __import__(n,globals(),locals(),['xxx'])
  print m.__doc__
except ImportError:
  print 'Unable to import %s' % n
