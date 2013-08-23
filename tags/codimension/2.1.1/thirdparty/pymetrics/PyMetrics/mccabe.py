""" Compute McCabe's Cyclomatic Metric.

    This routine computes McCabe's Cyclomatic metric for each function
    in a module/file.

    $Id: mccabe.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

from metricbase import MetricBase

McCabeKeywords = {
    'assert':0,
    'break':1,
    'continue':1,
    'elif':1,
    'else':1,
    'for':1,
    'if':1,
    'while':1
    }
    
class McCabeMetric( MetricBase ):
    """ Compute McCabe's Cyclomatic McCabeMetric by function."""
    def __init__( self, context, runMetrics, metrics, pa, *args, **kwds ):
        self.context = context
        self.runMetrics = runMetrics
        self.metrics = metrics
        self.pa = pa
        self.inFile = context['inFile']
        self.fcnNames = {}
                
    def processToken( self, fcnName, className, tok, *args, **kwds ):
        """ Increment number of decision points in function."""
        if tok and tok.text in McCabeKeywords:
            self.fcnNames[fcnName] = self.fcnNames.get(fcnName,0) + 1
    
    def processFunction( self, fcnName, className, fcn, *args, **kwds ):
        """ Increment number of decision points in function."""
        self.fcnNames[fcnName] = self.fcnNames.get(fcnName,0) + 1
    
    def display( self ):
        """ Display McCabe Cyclomatic metric for each function """
        result = {}
        # the next three lines ensure that fcnNames[None] is treated
        # like fcnNames['__main__'] and are sorted into alphabetical
        # order.
        if self.fcnNames.has_key(None):
            self.fcnNames['__main__'] = self.fcnNames.get(None,0)
            del self.fcnNames[None]
        
        if self.pa.quietSw:
            return result
            
        hdr = "\nMcCabe Complexity Metric for file %s" % self.inFile
        print hdr
        print "-"*len(hdr) + "\n"
        keyList = self.fcnNames.keys()
        if len( keyList ) > 0:
            keyList.sort()
            for k in keyList:
                if k:
                    name = k
                else:
                    name = "__main__"
                print "%11d    %s" % (self.fcnNames[k],name) 
                result[k] = self.fcnNames[k]
        else:
            print "%11d    %s" % (1,'__main__')
            result['__main__'] = 1

        print
        return result
        
