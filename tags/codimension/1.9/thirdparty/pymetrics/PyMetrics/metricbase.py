""" Metric base class for new user-defined metrics.

    $Id$
"""
__version__ = "$Revision: 1.2 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

class MetricBase( object ):
    """ Metric template class."""
    def __init__( self, *args, **kwds ):
        pass
        
    def processSrcLines( self, srcLines, *args, **kwds ):
        """ Handle physical line after tab expansion."""
        pass
        
    def processToken( self, fcnName, className, tok, *args, **kwds ):
        """ Handle processing after each token processed."""
        pass
        
    def processStmt( self, fcnName, className, stmt, *args, **kwds ):
        """ Handle processing at end of statement."""
        pass
        
    def processBlock( self, fcnName, className, block, *args, **kwds ):
        """ Handle processing at end of block."""
        pass
        
    def processFunction( self, fcnName, className, fcn, *args, **kwds ):
        """ Handle processing at end of function. """
        pass
        
    def processClass( self, fcnName, className, cls, *args, **kwds ):
        """ Handle processing at end of class. """
        pass
        
    def processModule( self, moduleName, module, *args, **kwds ):
        """ Handle processing at end of module. """
        pass
        
    def processRun( self, run, *args, **kwds ):
        """ Handle processing at end of run. """
        pass

    def compute( self, *args, **kwds ):
        """ Compute the metric given all needed info known."""
        pass
        
