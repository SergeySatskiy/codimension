""" Simple Metrics for each function within a file.

    $Id: simple.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__version__ = "$Revision: 1.4 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

from metricbase import MetricBase
from globals import *

class SimpleMetric( MetricBase ):
    """ Compute simple metrics by function."""
    def __init__( self, context, runMetrics, metrics, pa, *args, **kwds ):
        self.context = context
        self.runMetrics = runMetrics
        self.metrics = metrics
        self.pa = pa
        self.inFile = context['inFile']
        self.simpleMetrics = {}
        self.mcc = {}
        self.fcnNames = {}
        self.classNames = {}
        self.lastFcnName = None
        self.lastClassName = None
        self.metrics['DocFunctions'] = []
        self.metrics['DocClasses'] = []
                
    def processToken( self, currentFcn, currentClass, tok, *args, **kwds ):
        """ Collect token and context sensitive data for simple metrics."""
        if tok.semtype == DOCSTRING:
            self.metrics['numDocStrings'] = self.metrics.get('numDocStrings',0) + 1
            if currentFcn and currentFcn != "__main__":
                if self.lastFcnName != currentFcn:
                    self.lastFcnName = currentFcn
                    self.metrics['numFcnDocStrings'] = self.metrics.get('numFcnDocStrings',0) + 1
                    self.fcnNames[currentFcn] = tok.row
            elif currentClass == None: # this doc string must be module doc string
                self.lastFcnName = "__main__"
                self.metrics['numFcnDocStrings'] = self.metrics.get('numFcnDocStrings',0) + 1
                self.fcnNames[self.lastFcnName] = tok.row
            if currentClass:
                if self.lastClassName != currentClass:
                    self.lastClassName = currentClass
                    self.metrics['numClassDocStrings'] = self.metrics.get('numClassDocStrings',0) + 1
                    self.classNames[currentClass] = tok.row
        elif tok.semtype == FCNNAME:
            self.fcnNames[currentFcn] = 0
        elif tok.semtype == CLASSNAME:
            self.classNames[currentClass] = 0
        
    def processBlock( self, currentFcn, currentClass, block, *args, **kwds ):
        """ Collect token and context sensitive data for simple metrics."""
        self.metrics['numBlocks'] = self.metrics.get('numBlocks',0)+1  
        
    def compute( self, *args, **kwds ):
        """ Compute any values needed."""
        if self.metrics.get('numModuleDocStrings', 0) > 0:
            self.metrics['numFunctions'] = self.metrics.get('numFunctions', 0) + 1
        
        try:
            self.simpleMetrics['%Comments'] = 100.0 * self.metrics['numComments']/self.metrics['numLines']
        except (KeyError, ZeroDivisionError):
            self.simpleMetrics['%Comments'] = 0.0
            
        try:
            self.simpleMetrics['%CommentsInline'] = 100.0 * self.metrics['numCommentsInline']/self.metrics['numLines']
        except (KeyError, ZeroDivisionError):
            self.simpleMetrics['%CommentsInline'] = 0.0
            
        if 0:
            try:
                self.simpleMetrics['%DocStrings'] = 100.0 * self.metrics['numDocStrings']/(self.metrics['numModuleDocStrings']+self.metrics['numClasses']+self.metrics['numFunctions'])
            except (KeyError, ZeroDivisionError):
                self.simpleMetrics['%DocStrings'] = 0.0
                
        try:
            self.simpleMetrics['%FunctionsHavingDocStrings'] = 100.0 * self.metrics['numFcnDocStrings']/self.metrics['numFunctions']
        except (KeyError, ZeroDivisionError):
            self.simpleMetrics['%FunctionsHavingDocStrings'] = 0.0
            
        try:
            self.simpleMetrics['%ClassesHavingDocStrings'] = 100.0 * self.metrics['numClassDocStrings']/self.metrics['numClasses']
        except (KeyError, ZeroDivisionError):
            self.simpleMetrics['%ClassesHavingDocStrings'] = 0.0
        
        return self.simpleMetrics
        
    def display( self, currentFcn=None ):
        """ Display and return simple metrics for given function."""
        
        def __printNames( typeName, names ):
            """ Pretty print list of functions/classes that have doc strings."""
            if len( names ):    # only output something if it exists
                hdr = "%s DocString present(+) or missing(-)" % typeName
                print
                print hdr
                print "-"*len(hdr) + "\n"
                result = []
                keys = names.keys()
                keys.sort()
                for k in keys:
                    if k:
                        pfx = (names[k] and '+') or '-'
                        print "%c %s" % (pfx,k) 
                print
                
            result = (self.inFile, names)
            return result
            
        self.compute()
        keyList = self.simpleMetrics.keys()
        keyList.sort()
        for k in keyList:
            if self.pa.zeroSw or self.simpleMetrics[k]:
                fmt = ( k[0] == '%' and "%14.2f %s" ) or "%11d    %s"
                print fmt % (self.simpleMetrics[k],k)
            
        self.metrics['DocFunctions'].append( __printNames( 'Functions', self.fcnNames ) )
        self.metrics['DocClasses'].append( __printNames( 'Classes', self.classNames ) )

        return self.simpleMetrics
