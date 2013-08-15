""" Metrics for New Features introduced in Python 2.4.

    $Id: newFeatures24.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""
__version__ = "$Revision: 1.1 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics-at-charneyday.com>'

from metricbase import MetricBase
from globals import *

class NewFeatures24Metric( MetricBase ):
    """ Compute simple metrics by function."""
    firstPass = True
    def __init__( self, context, runMetrics, metrics, pa, *args, **kwds ):
      """ Count features introduced after v2.3."""
      self.context = context
      self.runMetrics = runMetrics
      self.metrics = metrics
      self.pa = pa
      self.inFile = context['inFile']
      
      self.prevTokText = ''
      self.userDefinedSet = False
      self.featureMetrics = {}
      self.numGeneratorFunctions = 0
      self.numGeneratorExpressions = 0
      self.numListComprehension = 0
      self.numClassProperties = 0
      self.numClassVariables = 0
      self.numClassFunctions = 0
      self.numDecorators = 0
      self.isGeneratorFunction = False
      self.isGeneratorExpression = False
      self.isListComprehension = False
      self.usedInbuiltSets = False
      self.usedDecorators = False
      self.maybeSetKeyword = False
      self.stackParenOrBracket = [];
      self.featureMetrics['numGeneratorFunctions'] = 0
      self.featureMetrics['numGeneratorExpressions'] = 0
      self.featureMetrics['numListComprehensions'] = 0
      self.featureMetrics['numModulesUsingSets'] = 0
      self.featureMetrics['numDecorators'] = 0

      if NewFeatures24Metric.firstPass:
        self.runMetrics['modulesUsingGeneratorFunctions'] = []
        self.runMetrics['modulesUsingGeneratorExpressions'] = []
        self.runMetrics['modulesUsingListComprehension'] = []
        self.runMetrics['modulesUsingSets'] = []
        self.runMetrics['modulesUsingDecorators'] = []
        NewFeatures24Metric.firstPass = False
         
    def processToken( self, currentFcn, currentClass, tok, *args, **kwds ):
      """ Collect token and context sensitive data for simple metrics."""
      if tok.semtype == KEYWORD:
        self.__handleKeywords( currentFcn, currentClass, tok, *args, **kwds )
      elif tok.type == OP:
        if self.maybeSetKeyword and tok.text == '(':
          if not self.userDefinedSet:
            self.usedInbuiltSets = True
          self.maybeSetKeyword = False
        elif tok.text == '(' or tok.text == '[':
          self.stackParenOrBracket.append( tok.text )
        elif tok.text == ')' or tok.text == ']':
          if len( self.stackParenOrBracket ) > 0:
            del self.stackParenOrBracket[-1]
        elif tok.text == '@':
          self.usedDecorators = True
          self.featureMetrics['numDecorators'] += 1
      elif tok.semtype == VARNAME:
        if tok.text in ['set', 'frozenset']:
          if not self.prevTokText in ['.', 'def', 'class']:
            self.maybeSetKeyword = True
      elif tok.semtype in [FCNNAME,CLASSNAME]:
        # We need to ignore user-defined global set 
        # functions and classes.
        if tok.text in ['set', 'frozenset']:
          self.userDefinedSet = True
      if tok.type != WS:
        self.prevTokText = tok.text
      return
        
    def __handleKeywords( self, currentFcn, currentClass, tok, *args, **kwds ):
      """ Check for generator functions or expressions and list comprehension."""
      if tok.text == "yield":
        self.isGeneratorFunction = True
      elif tok.text == "for":
        if len( self.stackParenOrBracket ) > 0:
          punct = self.stackParenOrBracket[-1]
          if punct == '(':
            self.featureMetrics['numGeneratorExpressions'] += 1
          elif punct == '[':
            self.featureMetrics['numListComprehensions'] += 1
      return

    def processStmt( self, fcnName, className, stmt, *args, **kwds ):
      """ Handle processing at end of statement."""
      self.stackParenOrBracket = []
        
    def processFunction( self, fcnName, className, block, *args, **kwds ):
      """ Output stats at end of each function."""
      if self.isGeneratorFunction:
        self.featureMetrics['numGeneratorFunctions'] += 1
        self.isGenerator = False
      if self.usedInbuiltSets:
        self.featureMetrics['numModulesUsingSets'] += 1
        self.usedInbuiltSets = False
        
    def processModule( self, moduleName, mod, *args, **kwds ):
        """ Output stats at end of each module."""
        self.moduleName = moduleName
        if self.featureMetrics['numModulesUsingSets'] > 0:
          self.runMetrics['modulesUsingSets'].append( moduleName )
        if self.featureMetrics['numGeneratorFunctions'] > 0:
          self.runMetrics['modulesUsingGeneratorFunctions'].append( moduleName )
        if self.featureMetrics['numGeneratorExpressions'] > 0:
          self.runMetrics['modulesUsingGeneratorExpressions'].append( moduleName )
        if self.featureMetrics['numListComprehensions'] > 0:
          self.runMetrics['modulesUsingListComprehension'].append( moduleName )
        if self.featureMetrics['numDecorators'] > 0:
          self.runMetrics['modulesUsingDecorators'].append( moduleName )
        return
        
    def processRun( self, run, *args, **kwds ):
        """ Output stats at end of run."""        
        def __printHeader( printHeader ):
          """ Only print heading if something in body of report."""
          if printHeader:
            print """Python 2.4 Features Used During Run"""
            print """-----------------------------------"""
          return False
            
        def __printSubHeader( printHeader, key, desc ):
          if len( self.runMetrics[key] ) > 0:
            printHeader = __printHeader( printHeader )
            h1 = "Modules using %s" % desc
            h2 = '.'*len( h1 )
            print
            print h1
            print h2
            print
            for modName in self.runMetrics[key]:
              print modName
          return False
                       
        printHeader = True
        printHeader = __printSubHeader( printHeader, 
                        'modulesUsingSets', 
                        'builtin set/frozenset (PEP 218)' )
        printHeader = __printSubHeader( printHeader, 
                        'modulesUsingGeneratorFunctions',
                        'Generator Functions' )
        printHeader = __printSubHeader( printHeader, 
                        'modulesUsingGeneratorExpressions (PEP 289)',
                        'Generator Expressions' )
        printHeader = __printSubHeader( printHeader, 
                        'modulesUsingListComprehension',
                        'List Comprehension' )
        printHeader = __printSubHeader( printHeader, 
                        'modulesUsingDecorators',
                        'Decorators (PEP 318)' )
        
        return None
          
    def compute( self, *args, **kwds ):
        """ Compute any values needed."""
        try:
            self.featureMetrics['%FunctionsThatAreGenerators'] = 100.0 * self.featureMetrics['numGeneratorFunctions']/self.metrics['numFunctions']
        except (KeyError, ZeroDivisionError):
            self.featureMetrics['%FunctionsThatAreGenerators'] = 0.0
            
        return self.featureMetrics
        
    def display( self, currentFcn=None ):
        """ Display and return new features in 2.4 metrics for given function."""
        def __printDisplayHdr():
            """ Only print heading if something in body of report."""
            h1 = """Python 2.4 Features Used in %s""" % self.inFile
            h2 = '-'*len( h1 )
            print h1
            print h2
            print
            return False
            
        printHeader = True
        self.compute()
        keyList = self.featureMetrics.keys()
        keyList.sort()
        for k in keyList:
            if self.pa.zeroSw or self.featureMetrics[k]:
                fmt = ( k[0] == '%' and "%14.2f %s" ) or "%11d    %s"
                if printHeader: printHeader = __printDisplayHdr()
                print fmt % (self.featureMetrics[k],k)
        print
        
        return self.featureMetrics

if __name__=="__main__":
  def Incr( init ):
    for i in range(10):
      yield i
  s = set(i for i in range(0,10,2))
  fs = frozenset(i for i in range(5))
  print s, fs
