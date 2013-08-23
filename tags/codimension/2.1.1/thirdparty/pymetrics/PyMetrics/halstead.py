""" Compute HalsteadMetric Metrics. 

HalsteadMetric metrics, created by Maurice H. HalsteadMetric in 1977, consist 
of a number of measures, including:

Program length (N):     N = N1 + N2
Program vocabulary (n): n = n1 + n2
Volume (V):             V = N * LOG2(n)
Difficulty (D):         D = (n1/2) * (N2/n2)
Effort (E):             E = D * V
Average Volume (avgV)   avgV = sum(V)/m
Average Effort (avgE)   avgE = sum(E)/m

where:

n1 = number of distinct operands
n2 = number of distinct operators
N1 = total number of operands
N2 = total number of operators
m  = number of modules

What constitues an operand or operator is often open to 
interpretation. In this implementation for the Python language:

    operators are of type OP, INDENT, DEDENT, or NEWLINE since these
        serve the same purpose as braces and semicolon in C/C++, etc.
    operands are not operators or whitespace or comments 
        (this means operands include keywords)

    $Id: halstead.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import math
import time
from metricbase import MetricBase
from globals import *

class HalsteadMetric( MetricBase ):
    """ Compute various HalsteadMetric metrics. """
    totalV = 0
    totalE = 0
    numModules = 0
    def __init__( self, context, runMetrics, metrics, pa, *args, **kwds ):
        """ Initialization for the HalsteadMetric metrics."""
        self.inFile = context['inFile']
        self.context = context
        self.runMetrics = runMetrics
        self.metrics = metrics
        self.pa = pa
        self.inFile = context['inFile']
        self.numOperators = 0
        self.numOperands = 0
        self.uniqueOperators = {}
        self.uniqueOperands = {}
        HalsteadMetric.numModules += 1
        
        # initialize category accummulators as dictionaries
        self.hsDict = {}
        for t in ['token','stmt','block','function','class','module','run']:
            self.uniqueOperators[t] = {}
            self.uniqueOperands[t] = {}
            #for v in ['N','N1','N2','n','n1','n2','V','D','E','avgV','avgE']:
            #    self.hsDict[(t,v)] = 0
        
    def processToken( self, currentFcn, currentClass, tok, *args, **kwds ):
        """ Collect token data for Halstead metrics."""
        if tok.type in [WS, EMPTY, ENDMARKER, NEWLINE, EMPTY, COMMENT]:
            pass
        elif tok.type in [OP, INDENT, DEDENT]:
            self.numOperators += 1
            self.uniqueOperators['token'][tok.text] = self.uniqueOperators['token'].get(tok.text, 0) + 1
        else:
            self.numOperands += 1
            sDict = self.context.__repr__()
            k = (sDict,tok.text)
            self.uniqueOperands['token'][k] = self.uniqueOperands['token'].get(tok.text, 0) + 1

    def processStmt( self, currentFcn, currentClass, stmt, *args, **kwds ):
        """ Collect statement data for Halstead metrics."""
        
        result = None
        
        # the two lines following this comment would compute the Halstead 
        # metrics for each statement in the run, However, it is 
        # normally overkill, so these lines are commented out.
        
        #lineNum = stmt[0].row
        #result = self.computeCategory( 'stmt', lineNum, stmt )
        
        return result
        
    def processBlock( self, currentFcn, currentClass, block, *args, **kwds ):
        """ Collect block data for Halstead metrics."""

        result = None

        # the two lines following this comment would compute the Halstead 
        # metrics for each statement in the run, However, it is 
        # normally overkill, so the two lines are commented out.
        
        #blockNum = self.context['blockNum']
        #result = self.computeCategory( 'block', blockNum, block )
        
        return result

    def processFunction( self, currentFcn, currentClass, fcn, *args, **kwds ):
        """ Collect function data for Halstead metrics."""
        result = self.computeCategory( 'function', currentFcn, fcn )
        return result
        
    def processClass( self, currentFcn, currentClass, cls, *args, **kwds ):
        """ Collect class data for Halstead metrics."""
        result = self.computeCategory( 'class', currentClass, cls )
        return result
        
    def processModule( self, moduleName, mod, *args, **kwds ):
        """ Collect module data for Halstead metrics."""
        result = self.computeCategory( 'module', moduleName, mod )
        return result
        
    def processRun( self, run, *args, **kwds ):
        """ Collect run data for Halstead metrics."""
        datestamp = time.strftime("%Y-%m-%d.%H:%m%Z",time.localtime())
        result = self.computeCategory( 'run', datestamp, run )
        return result
        
    def __LOGb( self, x, b ): 
        """ convert to LOGb(x) from natural logs."""
        try:
            result = math.log( x ) / math.log ( b )
        except OverflowError:
            result = 1.0
        return result

    def computeIncr( self, cat, tok, uniqueOperators, uniqueOperands ):
        """ Compute increment for token depending on which category it falls into."""
        operatorIncr = operandIncr = 0
        if tok.type in [WS, EMPTY, ENDMARKER, NEWLINE, EMPTY, COMMENT]:
            return (operatorIncr,operandIncr)
            
        if tok.type in [OP, INDENT, DEDENT]:
            operatorIncr = 1
            uniqueOperators[tok.text] = uniqueOperators.get(tok.text, 0) + 1
        else:
            operandIncr = 1
            uniqueOperands[tok.text] = uniqueOperands.get(tok.text,0) + 1
            
        return (operatorIncr,operandIncr)
        
    def computeCategory( self, cat, mod, lst ):
        """ Collection data for cat of code."""
        modID= id( mod )
        numOperators = numOperands = 0
        for tok in lst:
            result = self.computeIncr( cat, tok, self.uniqueOperators[cat], self.uniqueOperands[cat] )
            numOperators += result[0]
            numOperands += result[1]
        result = self.compute( cat, modID, numOperators, numOperands, self.uniqueOperators[cat], self.uniqueOperands[cat] )
        return result
        
    def compute( self, cat, modID, numOperators, numOperands, uniqueOperators, uniqueOperands, *args, **kwds ):
        """ Do actual calculations here."""
        
        n1 = len( uniqueOperands )
        n2 = len( uniqueOperators )
        N1 = numOperands
        N2 = numOperators
        N = N1 + N2
        n = n1 + n2
        V = float(N) * self.__LOGb( n, 2 )
        try:
            D = (float(n1)/2.0) * (float(N2)/float(n2))
        except ZeroDivisionError:
            D = 0.0
        E = D * V
        HalsteadMetric.totalV += V
        HalsteadMetric.totalE += E
        avgV = HalsteadMetric.totalV / HalsteadMetric.numModules
        avgE = HalsteadMetric.totalE / HalsteadMetric.numModules
        
        self.hsDict[(cat,modID,'n1')] = n1
        self.hsDict[(cat,modID,'n2')] = n2
        self.hsDict[(cat,modID,'N1')] = N1
        self.hsDict[(cat,modID,'N2')] = N2
        self.hsDict[(cat,modID,'N')] = N
        self.hsDict[(cat,modID,'n')] = n
        self.hsDict[(cat,modID,'V')] = V
        self.hsDict[(cat,modID,'D')] = D
        self.hsDict[(cat,modID,'E')] = E
        self.hsDict[(cat,modID,'numModules')] = HalsteadMetric.numModules
        self.hsDict[(cat,modID,'avgV')] = avgV
        self.hsDict[(cat,modID,'avgE')] = avgE
        
        return self.hsDict
        
    def display( self, cat=None ):
        """ Display the computed Halstead Metrics."""
        if self.pa.quietSw:
            return self.hsDict
            
        hdr = "\nHalstead Metrics for %s" % self.inFile
        print hdr
        print "-"*len(hdr) + '\n'
        
        if len( self.hsDict ) == 0:
            print "%-8s %-30s " % ('**N/A**','All Halstead metrics are zero')
            return self.hsDict
            
        keyList = self.hsDict.keys()
        keyList.sort()
        if 0:
            for k,i,v in keyList:
                if cat:
                    if k!=cat:
                        continue
                print "%14.2f %s %s %s" % (self.hsDict[(k,i,v)],k,i,v) 
            print
        hdr1 = "Category Identifier                                D        E     N   N1   N2        V     avgE     avgV     n   n1   n2"
        hdr2 = "-------- ---------------------------------- -------- -------- ----- ---- ---- -------- -------- -------- ----- ---- ----"
        #       12345678 123456789012345678901234567890  12345678 12345678 12345 1234 1234 12345678 12345678 12345678 12345 1234 1234
        fmt1 = "%-8s %-33s "
        fmt2 = "%8.2e %8.2e %5d %4d %4d %8.2e %8.2e %8.2e %5d %4d %4d"
        
        # this loop uses the Main Line Standards break logic. It does this to convert the
        # normal vertical output to a horizontal format. The control variables are the
        # category name and the identifier value.
        
        oldK = oldI = None
        vDict = {}
        vList = []
        hdrSw = True                # output header for first time thru
        for k,i,v in keyList:
            # only print data for the category we want
            if cat:
                if k != cat:
                    continue 
                    
            if v == "numModules":    # ignore this value for now
                continue
                
            if (oldK,oldI) != (k,i):    # change in category/id
                if oldK and oldI:           # this is not first time thru
                    #t = tuple([self.hsDict[(k,i,v)] for v in vList])
                    t = tuple([vDict[v] for v in vList])
                    print fmt1 % (k,i),
                    print fmt2 % t
                # initialize for next set of category/id
                vDict = {}
                vDict[v] = self.hsDict[(k,i,v)]
                vList = []
                vList.append( v )
                oldK = k
                oldI = i
                if hdrSw:
                    print hdr1
                    print hdr2
                    hdrSw = False
            else:       # we are still in the same category/id
                vDict[v] = self.hsDict[(k,i,v)]
                vList.append( v )

        print
                
        return self.hsDict
