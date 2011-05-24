""" Compute COCOMO 2's SLOC (Source Lines Of Code) metric.

    Compute Source Lines Of Code for each function/class/file. 
    This is based on COCOMO 2's definition of constitutes a
    line of code.  
    
    Algorithm:
        Delete all non-literal blank lines
        Delete all non-literal comments
        Delete all doc strings
        Combine parenthesised expressions into one logical line
        Combine continued lines into one logical line
        Return count of resulting lines
        
    Conventions:
        Continued lines are those ending in \) are treated as one 
          physical line.
        Paremeter lists and expressions enclosed in parens (), 
          braces {}, or brackets [] are treated as being part
          of one physical line.
        All literals are treated as being part of one physical 
          line
        
    $Id$
"""
__revision__ = "$Revision: 1.1 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

import re

from metricbase import MetricBase

class SLOCMetric( MetricBase ):
    """ Compute Source Lines Of Code metric."""
    def __init__( self, context, runMetrics, metrics, pa, *args, **kwds ):
        # pattern definitions
        patBackslashQuote = r'\\\'|\\\"'
        patTripleQuote1 = r"r?'''.*?'''"
        patTripleQuote2 = r'r?""".*?"""'
        patQuote1 = r"'.*?'"
        patQuote2 = r'".*?"'
        self.patLiteral = patTripleQuote1 + '|' + patQuote1 + '|' + patTripleQuote2 + '|' + patQuote2
        self.patComment = '#.*\n'
        self.patParen = '\(.*?\)'
        self.patDefOrClass = '^\s*(def|class)\s+\w.*:'
        self.patAllBlank = '^\s*\n|^\s*@\n|^\s*~\n'
        # compile patterns
        self.reBackslashQuote = re.compile( patBackslashQuote )
        self.reLiteral = re.compile( self.patLiteral, re.M + re.S )
        self.reComment = re.compile( self.patComment )
        self.reParen = re.compile( self.patParen, re.M + re.S )
        self.reDefOrClass = re.compile( self.patDefOrClass, re.M + re.S )
        self.reAllBlank = re.compile( self.patAllBlank, re.M + re.S )
        
        self.numSLOC = 0
        self.context = context
        self.runMetrics = runMetrics
        self.metrics = metrics
        self.pa = pa
        self.inFile = context['inFile']
        self.fcnNames = {}
                
    def processSrcLines( self, rawLines, *args, **kwds ):
        """ Process all raw source lines in one fell swoop.
        If a given line is not blank and contains something
        besides a comment, then increment the numSLOC."""
        if len( rawLines ) == 0:
            # ignore file
            self.numSLOC = 0
            return
            
        noBackslashQuotes = re.sub( self.reBackslashQuote, '*', rawLines )
        noLiteralLines = re.sub( self.reLiteral, '@', noBackslashQuotes )
        noCommentLines = re.sub( self.reComment, '~\n', noLiteralLines )
        noBlankLines = re.sub( self.reAllBlank, '%', noCommentLines )
        noParenLines = re.sub( self.reParen, '(...)', noBlankLines )
        self.numSLOC = noParenLines.count( '\n' )
        return
        
    def display( self ):
        """ Display SLOC metric for each file """
        result = {}
        result[self.inFile] = self.numSLOC
        
        if self.pa.quietSw:
            return result
            
        hdr = "\nCOCOMO 2's SLOC Metric for %s" % self.inFile
        print hdr
        print "-"*len(hdr) + "\n"
        print "%11d    %s" % (self.numSLOC,self.inFile) 
        print
        
        return result
        
def __main( fn, debugSw ):
    """ Process lines from input file."""
    fd = open( fn )
    rawLines = fd.read()
    fd.close()
    
    class PA: pass
    pa = PA()
    pa.quietSw = True
    pa.debugSw = debugSw
    
    __processFile(fn, pa, rawLines)

def __processFile(fn, pa, rawLines):
    """ Invoke metric function after setting up scaffolding."""
    sloc = SLOCMetric( {'inFile':fn},[],pa )
    sloc.processSrcLines( rawLines )
    print sloc.display()

def __getFNList():
    """ Return list of input file names, 
    regardless of whether the list came 
    from a file or the command line."""
    import sys
    debugSw = False
    fnList = []
    for arg in sys.argv[1:]:
        if arg == '-d':
            debugSw = True
            continue
        if arg == '-f':
            fd = open(sys.argv[2])
            lines = fd.read()
            fd.close()
            fnList = __normalizeLines( lines )
            continue
        fnList.append( arg )
    return fnList,debugSw

def __normalizeLines( lines ):
    """ Remove trailing newlines, if needed, 
    and return list of input file names."""
    fnList = []
    if len( lines ) > 0:
        if lines[-1] == '\n':
            lines = lines[:-1]
        fnList = lines.split( '\n' )
    return fnList

if __name__ == "__main__":    
    fnList,debugSw = __getFNList()
    for fn in fnList:
        try:
            fn!='' and __main( fn, debugSw )
        except:
            pass
