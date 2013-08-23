""" Main computational modules for PyMetrics.

    $Id: compute.py 9 2011-01-16 20:49:40Z sergey.satskiy@gmail.com $
"""

__version__ = "$Revision: 1.2 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics-at-charneyday.com>'

import mytoken
from globals import *
from utils import *
MAXDISPLAY = 32

class ComputeMetrics( object ):
    """ Class used to compute basic metrics for given module."""
    def __init__( self, metricInstance, context, runMetrics, metrics, pa, so, co ):
        """ Initialize general computational object."""
        self.metricInstance = metricInstance
        self.context = context
        self.runMetrics = runMetrics
        self.metrics = metrics
        self.pa = pa
        self.so = so
        self.co = co
        
        self.fqnFunction = []
        self.fqnClass = []
        self.fcnExits = []
        
        self.token = None
        self.stmt = []
        self.block = []
        self.fcn = []
        self.cls = []
        self.mod = []
        self.run = []

        self.processSrcLineSubscribers = []
        self.processTokenSubscribers = []
        self.processStmtSubscribers = []
        self.processBlockSubscribers = []
        self.processFunctionSubscribers = []
        self.processClassSubscribers = []
        self.processModuleSubscribers = []
        self.processRunSubscribers = []
    
        self.__initMetrics( metricInstance )
        
    # this is same as function in TokenHandler !!!!!!!!
    def __extractFQN( self, fqn, default='__main__' ):
        """ Extract fully qualified name from list."""
        result = default
        if len( fqn ):
            result = fqn[-1][0]
        return result
        
    # this is same as function in TokenHandler !!!!!!!!
    def __incr( self, name ):
        "Increment count in metrics dictionary based on name as key."
        self.metrics[name] = self.metrics.get(name,0) + 1
    
    def processSrcLines( self, srcLine ):
        """ Handle processing of each physical source line.
        
        The fcnName and className are meaningless until the
        tokens are evaluated.
        """
        fcnName = self.__extractFQN( self.fqnFunction )
        className = self.__extractFQN( self.fqnClass, None )

        for subscriber in self.processSrcLineSubscribers:
            subscriber.processSrcLines( srcLine )

    def processToken( self, tok ):
        """ Handle processing after each token processed."""
        self.token = tok
        self.stmt.append( tok )     # we are always in a statememt
        self.block.append( tok )    # we are always in a block
        if self.fqnFunction:        # we are inside some function
            self.fcn.append( tok )
        if self.fqnClass:           # we are inside some class
            self.cls.append( tok )
        self.mod.append( tok )      # we are always in some module
        self.run.append( tok )      # we are always in some run
        
        fcnName = self.__extractFQN( self.fqnFunction )
        className = self.__extractFQN( self.fqnClass, None )
        for subscriber in self.processTokenSubscribers:
            subscriber.processToken( fcnName, className, self.token )
        
    def processStmt( self ):
        """ Handle processing at end of statement."""
        fcnName = self.__extractFQN( self.fqnFunction )
        className = self.__extractFQN( self.fqnClass, None )
        for subscriber in self.processStmtSubscribers:
            subscriber.processStmt( fcnName, className, self.stmt )

        self.stmt[:] = [] # clear out statement list
        
    def processBlock( self ):
        """ Handle processing at end of block."""
        fcnName = self.__extractFQN( self.fqnFunction )
        className = self.__extractFQN( self.fqnClass, None )
        for subscriber in self.processBlockSubscribers:
            subscriber.processBlock( fcnName, className, self.block )

        self.block[:] = [] # clear out block list
        
    def processFunction( self ):
        """ Handle processing at end of function. """
        msg = self.__checkNumberOfExits()
        fcnName = self.__extractFQN( self.fqnFunction )
        className = self.__extractFQN( self.fqnClass, None )
        for subscriber in self.processFunctionSubscribers:
            subscriber.processFunction( fcnName, className, self.fcn )
            
        self.fcn[:] = [] # clear out function list
            
        return msg

    def __checkNumberOfExits( self ):
        """" Generate warning message if more than one exit. """
        msg = None
        n = len( self.fcnExits )
        if n > 0:
            exits = ', '.join( [str(i) for i in self.fcnExits] )
            plural = ((n > 1) and 's') or ''
            exitStr = "exit%s at line%s" % (plural,plural)
            msg = ("In file %s, function %s has %d extra %s %s" % 
                    (self.context['inFile'],
                     self.__extractFQN( self.fqnFunction ),
                     n,
                     exitStr,
                     exits))
            for i in range( len( self.fcnExits ) ):
                del self.fcnExits[0]
            self.__incr( 'numMultipleExitFcns')
            
        return msg

    def processClass( self ):
        """ Handle processing at end of class. """
        fcnName = self.__extractFQN( self.fqnFunction )
        className = self.__extractFQN( self.fqnClass, None )
        for subscriber in self.processClassSubscribers:
            subscriber.processClass( fcnName, className, self.cls )
            
        self.cls[:] = []
        
    def processModule( self ):
        """ Handle processing at end of class. """
        moduleName = self.context['inFile']
        mod = self
        for subscriber in self.processModuleSubscribers:
            subscriber.processModule( moduleName, mod )
        
        self.mod[:] = []
        
    def processRun( self ):
        """ Handle processing at end of class. """
        for subsriber in self.processRunSubscribers:
            subsriber.processRun( self.run )
            
        self.run[:] = []

    def __call__( self, lex ):
        """ This function is the start of the heavy lifting 
        for computing the various metrics produced by PyMetrics."""
               
        for m in self.metricInstance.keys():
            self.metricInstance[m].processSrcLines( lex.srcLines )
        
        # Loop through list of tokens and count types as needed.
        
            # skipUntil is set after an error is detected. It is an attempt to 
            # find a point to restart the analysis so that we do not get
            # cascading errors. This problem often occurs in analysing
            # foreign character sets when normal ascii was expected.
        tokenList = lex.tokenlist

        skipUntil = None
        tokCount = 0
        invalidToken = mytoken.MyToken()
        
        for tok in tokenList:
            if skipUntil:
                if tok.text in skipUntil:   # found where to restart analysis
                    skipUntil = None
                elif tok.type == WS:    # count, but otherwise ignore, whitespace
                    tokCount = tokCount+1
                    self.metrics['numTokens'] = tokCount
                    self.__postToken( tok )
                    continue
                elif tok.type == ERRORTOKEN:
                    invalidToken.text += tok.text
                    continue
                    
            tokCount = self.handleToken( tokCount, tok )
                    
        return self.metrics

    def __initMetrics( self, metricInstance ):
        """ Initialize all the local variables that will be 
        needed for analysing tokens.:"""
        metricList = []
        for m in metricInstance.keys():
            if metricInstance[m]:       # only append valid instances
                metricList.append( metricInstance[m] )
        # clear out any old data while leaving reference to same 
        # thing (ie., pointers to these lists are always valid
        del self.processSrcLineSubscribers[:]
        del self.processTokenSubscribers[:]
        del self.processStmtSubscribers[:]
        del self.processBlockSubscribers[:]
        del self.processFunctionSubscribers[:]
        del self.processClassSubscribers[:]
        del self.processModuleSubscribers[:]
        del self.processRunSubscribers[:]
        # since all metric classes are derived from MetricBase,
        # we can assign all the processX functions to all the
        # metrics
        self.processSrcLineSubscribers.extend( metricList )
        self.processTokenSubscribers.extend( metricList )
        self.processStmtSubscribers.extend( metricList )
        self.processBlockSubscribers.extend( metricList )
        self.processFunctionSubscribers.extend( metricList )
        self.processClassSubscribers.extend( metricList )
        self.processModuleSubscribers.extend( metricList )
        self.processRunSubscribers.extend( metricList )

        self.numSrcLines = 0
        self.blockDepth = 0
        self.numBlocks = 0
        self.parenDepth = 0
        self.bracketDepth = 0
        self.braceDepth = 0
        self.numNestedClasses = 0
        self.numKeywords = 0
        self.numComments = 0
        self.numEmpty = 0
        self.classDepth = 0
        self.fcnDepth = 0
        self.classDepthIncr = 0
        self.fcnDepthIncr = 0
        self.maxBlockDepth = -1
        self.maxClassDepth = -1
        self.fqnName = []
        self.defFunction = False
        self.defClass = False
        self.docString = True
        self.findFcnHdrEnd = False
        self.findClassHdrEnd = False
        self.inClass = False
        self.inFunction = False
        self.metrics['numSrcLines'] = 0
        self.metrics['numTokens'] = 0
        self.metrics['numComments'] = 0
        self.metrics['numCommentsInline'] = 0
        self.metrics['numModuleDocStrings'] = 0
        self.metrics['numBlocks'] = 0
        self.metrics['numFunctions'] = 0
        self.metrics['numClasses'] = 0
        self.className = None
        self.fcnName = None
        self.saveTok = None
        self.skipUntil = None # used to skip invalid chars until valid char found
        self.invalidToken = None
        self.checkForModuleDocString = True
        
        return metricList
        
    def __fitIn( self, tok ):
        """ Truncate long tokens to MAXDISPLAY length.
        Also, newlines are replace with '\\n' so text fits on a line."""
        #tmpText = tok.text[:].replace( '\n', '\\n' )
        tmpText = tok.text[:]
        if len( tmpText ) > MAXDISPLAY:
            tmpText = tmpText[:10].strip() + ' ... ' + \
                      tmpText[-10:].strip()
        return tmpText
        
    def __incrEach( self, tok ):
        """ Increment count for each unique semantic type."""
        pfx = self.__genFQN( self.fqnName )
        key = self.__fitIn( tok )
        sep = tok.semtype == KEYWORD and ' ' or '.'
        if tok.semtype in [FCNNAME,CLASSNAME]:
            key = pfx
        else:
            if pfx:
                key = pfx + sep + key
            else:
                key = '__main__' + sep + key
        key = "%-10s %s" % (token.tok_name[tok.semtype],key)
        
        self.metrics[key] = self.metrics.get(key,0) + 1
    
    def __postToken( self, tok ):
        """ Post token processing for common tasks."""
        self.__incr( tok.type )
        if tok.semtype:         # then some semantic value here
            self.__incr( tok.semtype )  # count semantic type
            self.__incrEach( tok )
        self.processToken( tok )
        if self.pa.verbose > 1: 
	    print self.context, tok 
        self.so and self.so.write( self.context, tok, self.fqnFunction, self.fqnClass )
        self.co and self.co.write( self.context, tok, self.fqnFunction, self.fqnClass )
       
    def __genFQN( self, fqnName ):
        """ Generate a fully qualified name. """
        result = '.'.join( fqnName )
        return result
    
    def handleToken( self, tokCount, tok ):
        """ Common code for handling tokens."""
        if tokCount == 0:           # this is the first token of the module
            self.prevTok = None
        tokCount += 1
        self.metrics['numTokens'] = tokCount
        
        # don't treat whitespace as significant when looking at previous token
        if not tok.type in [WS,INDENT,DEDENT,EMPTY,ENDMARKER]:
            self.prevTok = self.saveTok
            self.saveTok = tok
        
        # set up context for current token
        self.context['blockNum'] = self.metrics.get('numBlocks',0)
        self.context['blockDepth'] = self.metrics.get('blockDepth',0)
        self.context['parenDepth'] = self.parenDepth
        self.context['bracketDepth'] = self.bracketDepth
        self.context['braceDepth'] = self.braceDepth

        # self.classDepthIncr is 1 if the class definition header 
        # has a newline after colon, else it is equal to zero 
        # meaning the class definition block is on same line as its header
        self.classDepth += self.classDepthIncr
        self.context['classDepth'] = self.classDepth
        self.classDepthIncr = 0
        
        # self.classFcnIncr is 1 if the function definition header 
        # has a newline after colon, else it is equal to zero 
        # meaning the function definition block is on same line
        # as its header
        self.fcnDepth += self.fcnDepthIncr # only incr at start of fcn body
        self.context['fcnDepth'] = self.fcnDepth
        self.fcnDepthIncr = 0
        
        # start testing for types that change in context
        
        if self.doDocString(tok): return tokCount
        if self.doInlineComment(tok, self.prevTok): return tokCount 
        if self.doHeaders(tok): return tokCount
            
        # return with types that don't change in context
        
        self.__postToken( tok )
        if tok.type == WS:
            return tokCount
            
        # treat end of file as end of statement
        if tok.type == EMPTY or tok.type == NEWLINE:
            self.processStmt()
            return tokCount
        
        # End of file forces closure of everything, but run
        if tok.type == ENDMARKER:
            self.processStmt()
            self.processBlock()
            self.processFunction()
            self.processClass()
            self.processModule()
            return tokCount
        
        # at this point, we have encountered a non-white space token
        # if a module doc string has not been found yet, 
        # it never will be.
        numModDocStrings = self.metrics['numModuleDocStrings']
        if self.checkForModuleDocString and numModDocStrings == 0:
            self.checkForModuleDocString = False
            msg = (("Module %s is missing a module doc string. "+
                    "Detected at line %d\n") %
                   (self.context['inFile'],tok.row)
                  )
            if msg and not self.pa.quietSw:
                print msg

        if self.doOperators(tok): return tokCount
        if self.doIndentDedent(tok): return tokCount
        
        self.docString = False
        self.doKeywords(tok, self.prevTok)
                        
        return tokCount

    def doKeywords(self, tok, prevTok):
        """ Count keywords and check if keyword 'return' used more than
        once in a given function/method."""
        if tok.semtype == KEYWORD:
            self.__incr( 'numKeywords')
            if tok.text == 'def':
                self.defFunction = True
            elif tok.text == 'class':
                self.defClass = True
            elif tok.text == 'return':
                assert self.fcnDepth == len( self.fqnFunction )
                if self.fcnDepth == 0:       # not in any function
                    if not self.pa.quietSw:  # report on these types of errors
                        print (("Module %s contains the return statement at "+
                               "line %d that is outside any function") % 
                               (self.context['inFile'],tok.row)
                              )
                if prevTok.text == ':': 
                    # this return on same line as conditional, 
                    # so it must be an extra return
                    self.fcnExits.append( tok.row )
                elif self.blockDepth > 1:
                    # Let fcnBlockDepth be the block depth of the function body.
                    # We are trying to count the number of return statements
                    # in this function. Only one is allowed at the fcnBlockDepth 
                    # for the function. If the self.blockDepth is greater than 
                    # fcnBlockDepth, then this is a conditional return - i.e., 
                    # an additional return
                    fcnBlockDepth = self.fqnFunction[-1][1] + 1
                    if self.blockDepth > fcnBlockDepth:
                        self.fcnExits.append( tok.row )

    def doIndentDedent(self, tok):
        """ Handle indents and dedents by keeping track of block depth.
        Also, handle cases where dedents close off blocks, functions, 
        and classes."""
        result = False
        if tok.type == INDENT:
            result = self.__doIndent()
        elif tok.type == DEDENT:
            result = self.__doDedent()
        return result

    def __doDedent(self):
        """ Handle dedents and remove function/class info as needed."""
        self._doDedentFcn()
        
        self.fcnName = None
        if len( self.fqnFunction ) > 0:
            self.fcnName = self.fqnFunction[-1][0]
            
        while len(self.fqnClass) and self.blockDepth <= self.fqnClass[-1][1]:
            self.processClass()
            self.classDepth -= 1
            if self.pa.verbose > 0: 
                print "Removing class %s" % self.__extractFQN( self.fqnClass, None )
            del self.fqnClass[-1]
            del self.fqnName[-1]
            
        self.className = None        
        if len( self.fqnClass ) > 0:
            self.className = self.fqnClass[-1][0]
  
        return True

    def _doDedentFcn(self):
        """ Remove function whose scope is ended."""
        assert self.fcnDepth == len( self.fqnFunction )
        self.blockDepth -= 1
        self.metrics['blockDepth'] = self.blockDepth
        while len(self.fqnFunction) and self.blockDepth<=self.fqnFunction[-1][1]:
            self.__doDedentRemoveMsg()
            del self.fqnFunction[-1]
            del self.fqnName[-1]
            self.fcnDepth -= 1
        assert self.fcnDepth == len( self.fqnFunction )

    def __doDedentRemoveMsg(self):
        """ Output message if debugging or user asks for info."""
        msg = self.processFunction()
        if msg and not self.pa.quietSw:
            print msg
        if self.pa.verbose > 0: 
            print "Removing function %s" % self.__extractFQN( self.fqnFunction )

    def __doIndent(self):
        """ Increment indent count and record if maximum depth."""
        self.__incr( 'numBlocks' )
        self.blockDepth += 1
        self.metrics['blockDepth'] = self.blockDepth
        if self.metrics.get('maxBlockDepth',0) < self.blockDepth:
            self.metrics['maxBlockDepth'] = self.blockDepth
        return True
        
    def doOperators(self, tok):
        """ Keep track of the number of each operator. Also, handle the
        case of the colon (:) terminating a class or def header."""
        result = False
        if tok.type == OP:
            if tok.text == ':':
                if self.findFcnHdrEnd:
                    self.findFcnHdrEnd = False
                    self.docString = True
                    self.fcnDepthIncr = 1
                elif self.findClassHdrEnd:
                    self.findClassHdrEnd = False
                    self.docString = True
                    self.classDepthIncr = 1
                result = True
            elif tok.text == '(':
                self.parenDepth += 1
            elif tok.text == ')':
                self.parenDepth -= 1
            elif tok.text == '[':
                self.bracketDepth += 1
            elif tok.text == ']':
                self.bracketDepth -= 1
            elif tok.text == '{':
                self.braceDepth += 1
            elif tok.text == '}':
                self.braceDepth -= 1
            result = True
        return result

    def doHeaders(self, tok):
        """ Process both class and function headers. 
        Create the fully qualified names and deal 
        with possibly erroneous headers."""
        result = False
        if self.defFunction:
            if tok.type == NAME:
                self.__incr( 'numFunctions')
                self.fqnName.append( tok.text )
                self.fcnName = self.__genFQN( self.fqnName )
                self.fqnFunction.append( (self.fcnName,self.blockDepth,FCNNAME) )
                self.defFunction = False
                self.findFcnHdrEnd = True
                if self.pa.verbose > 0: 
                    print ("fqnFunction=%s" % 
                           toTypeName( self.context, self.fqnFunction )
                          )
                self.__postToken( tok )
                result = True
            elif tok.type == ERRORTOKEN:
                # we must compensate for the simple scanner mishandling errors
                self.findFcnHdrEnd = True
                self.invalidToken = mytoken.MyToken(type=NAME, 
                                                    semtype=FCNNAME, 
                                                    text=tok.text, 
                                                    row=tok.row, 
                                                    col=tok.col, 
                                                    line=tok.line)
                self.skipUntil = '(:\n'
                result = True
        elif self.defClass and tok.type == NAME:
            self.__incr( 'numClasses' )
            self.fqnName.append( tok.text )
            self.className = self.__genFQN( self.fqnName )
            self.fqnClass.append( (self.className,self.blockDepth,CLASSNAME) )
            self.defClass = False
            self.findClassHdrEnd = True
            if self.pa.verbose > 0: 
                print "fqnClass=%s" % toTypeName( self.context, self.fqnClass )
            self.__postToken( tok )
            result = True
        return result

    def doInlineComment(self, tok, prevTok):
        """ Check for comments and distingish inline comments from
        normal comments."""
        result = False
        if tok.type == COMMENT:
            self.metrics['numComments'] += 1
            # compensate for older tokenize including newline
            # symbols in token when only thing on line is comment
            # this patch makes all comments consistent
            if tok.text[-1] == '\n':
                tok.text = tok.text[:-1]
                
            if prevTok and prevTok.type != NEWLINE and prevTok.type != EMPTY:
                tok.semtype = INLINE
                self.metrics['numCommentsInline'] += 1
            self.__postToken( tok )
            result = True
            
        return result
            
    def doDocString(self, tok):
        """ Determine if a given string is also a docstring. 
        Also, detect if docstring is also the module's docsting."""
        result = False
        if self.docString and tok.type == token.STRING:
            tok.semtype = DOCSTRING
            if self.checkForModuleDocString:  # found the module's doc string
                self.metrics['numModuleDocStrings'] += 1
                self.checkForModuleDocString = False
            self.__postToken( tok )
            self.docString = False
            result = True
        return result
