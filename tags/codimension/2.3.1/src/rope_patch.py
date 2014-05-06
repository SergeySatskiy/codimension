# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

# The patch is taken from spyderlib and adopted for codimension

"""
Patching rope:

[1] is not applicable for codimension

[2] For better performances, see this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/57de5731f202537a

[3] To avoid considering folders without __init__.py as Python packages, thus
avoiding side effects as non-working introspection features on a Python module
or package when a folder in current directory has the same name.
See this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/924c4b5a6268e618

[4] To avoid rope adding a 2 spaces indent to every docstring it gets, because
it breaks the work of Sphinx on the Object Inspector.
"""

import inspect
import rope
import re
from rope.base import pycore
from rope.base import builtins, libutils, pyobjects
import os.path as osp
from rope.contrib import codeassist
from rope.base import exceptions



def getsignaturesfromtext(text, objname):
    """Get object signatures from text (object documentation)
    Return a list containing a single string in most cases
    Example of multiple signatures: PyQt4 objects"""
    #FIXME: the following regexp is not working with this example of docstring:
    # QObject.connect(QObject, SIGNAL(), QObject, SLOT(), Qt.ConnectionType=Qt.AutoConnection) -> bool QObject.connect(QObject, SIGNAL(), callable, Qt.ConnectionType=Qt.AutoConnection) -> bool QObject.connect(QObject, SIGNAL(), SLOT(), Qt.ConnectionType=Qt.AutoConnection) -> bool

    # Note: codimension does not use this function for PyQt objects and
    #       functions. Instead it redirects the calltip requests to the
    #       original rope code and then extracts signatures from there.
    # The rest of the cases, e.g. numpy is handled here.
    if isinstance(text, dict):
        text = text.get('docstring', '')
    return re.findall(objname+r'\([^\)]+\)', text)


def getdoc( obj ):
    """
    Return text documentation from an object. This comes in a form of
    dictionary with four keys:

    name:
      The name of the inspected object
    argspec:
      It's argspec
    note:
      A phrase describing the type of object (function or method) we are
      inspecting, and the module it belongs to.
    docstring:
      It's docstring
    """
   
    docstring = inspect.getdoc( obj ) or inspect.getcomments( obj ) or ''
   
    # Most of the time doc will only contain ascii characters, but there are
    # some docstrings that contain non-ascii characters. Not all source files
    # declare their encoding in the first line, so querying for that might not
    # yield anything, either. So assume the most commonly used
    # multi-byte file encoding (which also covers ascii).
    try:
        docstring = unicode( docstring )
    except:
        pass
   
    # Doc dict keys
    doc = { 'name': '',
            'argspec': '',
            'note': '',
            'docstring': docstring}
   
    if callable( obj ):
        try:
            name = obj.__name__
        except AttributeError:
            doc[ 'docstring' ] = docstring
            return doc
        if inspect.ismethod( obj ):
            imclass = obj.im_class
            if obj.im_self is not None:
                doc[ 'note' ] = 'Method of %s instance' \
                                % obj.im_self.__class__.__name__
            else:
                doc[ 'note' ] = 'Unbound %s method' % imclass.__name__
            obj = obj.im_func
        elif hasattr( obj, '__module__' ):
            doc[ 'note' ] = 'Function of %s module' % obj.__module__
        else:
            doc[ 'note' ] = 'Function'
        doc[ 'name' ] = obj.__name__
        if inspect.isfunction( obj ):
            args, varargs, varkw, defaults = inspect.getargspec( obj )
            doc[ 'argspec' ] = inspect.formatargspec( args, varargs, varkw,
                                                      defaults,
                                                      formatvalue = lambda o:'='+repr(o))
            if name == '<lambda>':
                doc[ 'name' ] = name + ' lambda '
                doc[ 'argspec' ] = doc[ 'argspec' ][ 1 : -1 ] # remove parentheses
        else:
            # Try to extract the argspec from the first docstring line
            docstring_lines = doc[ 'docstring' ].split( "\n" )
            first_line = docstring_lines[ 0 ].strip()
            argspec = getsignaturesfromtext( first_line, '' )
            if argspec:
                doc[ 'argspec' ] = argspec[ 0 ]
                # Many scipy and numpy docstrings begin with a function
                # signature on the first line. This ends up begin redundant
                # when we are using title and argspec to create the
                # rich text "Definition:" field. We'll carefully remove this
                # redundancy but only under a strict set of conditions:
                # Remove the starting charaters of the 'doc' portion *iff*
                # the non-whitespace characters on the first line
                # match *exactly* the combined function title
                # and argspec we determined above.
                name_and_argspec = doc[ 'name' ] + doc[ 'argspec' ]
                if first_line == name_and_argspec:
                    doc[ 'docstring' ] = doc[ 'docstring' ].replace(
                                              name_and_argspec, '', 1 ).lstrip()
            else:
                doc[ 'argspec' ] = '(...)'
       
        # Remove self from argspec
        argspec = doc[ 'argspec' ]
        doc[ 'argspec' ] = argspec.replace( '(self)', '()' ).replace( '(self, ', '(' )
       
    return doc

def applyRopePatch():
    """Monkey patching rope for better performance"""
    if rope.VERSION not in ('0.9.4', '0.9.3', '0.9.2'):
        raise ImportError, "rope %s can't be patched" % rope.VERSION

    # Patching pycore.PyCore...
    class PatchedPyCore(pycore.PyCore):
        # [2] ...so that forced builtin modules (i.e. modules that were
        # declared as 'extension_modules' in rope preferences) will be indeed
        # recognized as builtins by rope, as expected
        #
        # This patch is included in rope 0.9.4+ but applying it anyway is ok
        def get_module(self, name, folder=None):
            """Returns a `PyObject` if the module was found."""
            # check if this is a builtin module
            pymod = self._builtin_module(name)
            if pymod is not None:
                return pymod
            module = self.find_module(name, folder)
            if module is None:
                raise pycore.ModuleNotFoundError(
                                            'Module %s not found' % name)
            return self.resource_to_pyobject(module)
        # [3] ...to avoid considering folders without __init__.py as Python
        # packages
        def _find_module_in_folder(self, folder, modname):
            module = folder
            packages = modname.split('.')
            for pkg in packages[:-1]:
                if  module.is_folder() and module.has_child(pkg):
                    module = module.get_child(pkg)
                else:
                    return None
            if module.is_folder():
                if module.has_child(packages[-1]) and \
                   module.get_child(packages[-1]).is_folder() and \
                   module.get_child(packages[-1]).has_child('__init__.py'):
                    return module.get_child(packages[-1])
                elif module.has_child(packages[-1] + '.py') and \
                     not module.get_child(packages[-1] + '.py').is_folder():
                    return module.get_child(packages[-1] + '.py')
    pycore.PyCore = PatchedPyCore

    # [2] Patching BuiltinName for the go to definition feature to simply work
    # with forced builtins
    class PatchedBuiltinName(builtins.BuiltinName):
        def _pycore(self):
            p = self.pyobject
            while p.parent is not None:
                p = p.parent
            if isinstance(p, builtins.BuiltinModule) and p.pycore is not None:
                return p.pycore
        def get_definition_location(self):
            if not inspect.isbuiltin(self.pyobject):
                _lines, lineno = inspect.getsourcelines(self.pyobject.builtin)
                path = inspect.getfile(self.pyobject.builtin)
                if (path.endswith('pyc') or path.endswith('pyo')) and osp.isfile(path[:-1]):
                    path = path[:-1]
                pycore = self._pycore()
                if pycore and pycore.project:
                    resource = libutils.path_to_resource(pycore.project, path)
                    module = pyobjects.PyModule(pycore, None, resource)
                    return (module, lineno)
            return (None, None)
    builtins.BuiltinName = PatchedBuiltinName

    # [4] Patching several PyDocExtractor methods:
    # 1. get_doc:
    # To force rope to return the docstring of any object which has one, even
    # if it's not an instance of AbstractFunction, AbstractClass, or
    # AbstractModule.
    # Also, to use utils.dochelpers.getdoc to get docs from forced builtins.
    #
    # 2. _get_class_docstring and _get_single_function_docstring:
    # To not let rope add a 2 spaces indentation to every docstring, which was
    # breaking our rich text mode. The only value that we are modifying is the
    # 'indents' keyword of those methods, from 2 to 0.
    #
    # 3. get_calltip
    # To easily get calltips of forced builtins
    class PatchedPyDocExtractor(codeassist.PyDocExtractor):
        def get_builtin_doc(self, pyobject):
            buitin = pyobject.builtin
            return getdoc(buitin)

        def __isPyQtObject( self, pyobject ):
            "Returns True if it was a PyQt object "
            try:
                currentObject = pyobject
                while hasattr( currentObject, "_parent" ):
                    currentObject = currentObject._parent
                return currentObject.name.startswith( "PyQt" )
            except:
                return False

        def get_doc(self, pyobject):
            if hasattr(pyobject, 'builtin'):
                if not self.__isPyQtObject( pyobject ):
                    doc = self.get_builtin_doc(pyobject)
                    return doc
            if isinstance(pyobject, builtins.BuiltinModule):
                docstring = pyobject.get_doc()
                if docstring is not None:
                    docstring = self._trim_docstring(docstring)
                else:
                    docstring = ''
                # TODO: Add a module_name key, so that the name could appear
                # on the OI text filed but not be used by sphinx to render
                # the page
                doc = {'name': '',
                       'argspec': '',
                       'note': '',
                       'docstring': docstring
                       }
                return doc
            if isinstance(pyobject, pyobjects.AbstractFunction):
                return self._get_function_docstring(pyobject)
            if isinstance(pyobject, pyobjects.AbstractClass):
                return self._get_class_docstring(pyobject)
            if isinstance(pyobject, pyobjects.AbstractModule):
                return self._trim_docstring(pyobject.get_doc())
            if pyobject.get_doc() is not None:  # Spyder patch
                return self._trim_docstring(pyobject.get_doc())
            return None

        def get_calltip(self, pyobject, ignore_unknown=False, remove_self=False):
            if hasattr(pyobject, 'builtin'):
                if not self.__isPyQtObject( pyobject ):
                    doc = self.get_builtin_doc(pyobject)
                    return doc['name'] + doc['argspec']
            try:
                if isinstance(pyobject, pyobjects.AbstractClass):
                    pyobject = pyobject['__init__'].get_object()
                if not isinstance(pyobject, pyobjects.AbstractFunction):
                    pyobject = pyobject['__call__'].get_object()
            except exceptions.AttributeNotFoundError:
                return None
            if ignore_unknown and not isinstance(pyobject, pyobjects.PyFunction):
                return None
            if isinstance(pyobject, pyobjects.AbstractFunction):
                result = self._get_function_signature(pyobject, add_module=True)
                if remove_self and self._is_method(pyobject):
                    return result.replace('(self)', '()').replace('(self, ', '(')
                return result

        def _get_class_docstring(self, pyclass):
            contents = self._trim_docstring(pyclass.get_doc(), indents=0)
            supers = [super.get_name() for super in pyclass.get_superclasses()]
            doc = 'class %s(%s):\n\n' % (pyclass.get_name(), ', '.join(supers)) + contents

            if '__init__' in pyclass:
                init = pyclass['__init__'].get_object()
                if isinstance(init, pyobjects.AbstractFunction):
                    doc += '\n\n' + self._get_single_function_docstring(init)
            return doc

        def _get_single_function_docstring(self, pyfunction):
            # signature = self._get_function_signature(pyfunction)
            docs = pyfunction.get_doc()
            return self._trim_docstring(docs, indents=0)
    codeassist.PyDocExtractor = PatchedPyDocExtractor

