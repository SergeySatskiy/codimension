# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Patching rope for better performances
See this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/57de5731f202537a
"""

import inspect


def getargfromdoc(obj):
    """Get arguments from object doc"""
    doc, name = obj.__doc__, obj.__name__
    if doc is not None and name+'(' in doc:
        return doc[doc.find(name+'(')+len(name)+1:doc.find(')')].split()

def getargs(obj):
    """Get the names and default values of a function's arguments"""
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        func_obj = obj
    elif inspect.ismethod(obj):
        func_obj = obj.im_func
    elif inspect.isclass(obj) and hasattr(obj, '__init__'):
        func_obj = getattr(obj, '__init__')
    else:
        return []
    if not hasattr(func_obj, 'func_code'):
        # Builtin: try to extract info from doc
        return getargfromdoc(func_obj)
    args, _, _ = inspect.getargs(func_obj.func_code)
    if not args:
        return getargfromdoc(obj)

    # Supporting tuple arguments in def statement:
    for i_arg, arg in enumerate(args):
        if isinstance(arg, list):
            args[i_arg] = "(%s)" % ", ".join(arg)

    defaults = func_obj.func_defaults
    if defaults is not None:
        for index, default in enumerate(defaults):
            args[index+len(args)-len(defaults)] += '='+repr(default)
    if inspect.isclass(obj) or inspect.ismethod(obj):
        if len(args) == 1:
            return None
        if 'self' in args:
            args.remove('self')
    return args


def applyRopePatch():
    """Monkey patching rope for better performances"""
    from rope import VERSION as ROPE_VERSION
    if ROPE_VERSION not in ('0.9.4', '0.9.3', '0.9.2'):
        raise ImportError, "rope %s can't be patched" % ROPE_VERSION

    # Patching pycore.PyCore, so that forced builtin modules (i.e. modules
    # that were declared as 'extension_modules' in rope preferences)
    # will be indeed recognized as builtins by rope, as expected
    from rope.base import pycore
    class PatchedPyCore(pycore.PyCore):
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
    pycore.PyCore = PatchedPyCore

    # Patching BuiltinFunction for the calltip/doc functions to be
    # able to retrieve the function signatures with forced builtins
    from rope.base import builtins, pyobjects
    class PatchedBuiltinFunction(builtins.BuiltinFunction):
        def __init__(self, returned=None, function=None, builtin=None,
                     argnames=[], parent=None):
            builtins._BuiltinElement.__init__(self, builtin, parent)
            pyobjects.AbstractFunction.__init__(self)
            self.argnames = argnames
            if not argnames and builtin:
                self.argnames = getargs(self.builtin)
            if self.argnames is None:
                self.argnames = []
            self.returned = returned
            self.function = function
    builtins.BuiltinFunction = PatchedBuiltinFunction

    # Patching BuiltinName for the go to definition feature to simply work
    # with forced builtins
    from rope.base import libutils
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
                pycore = self._pycore()
                if pycore and pycore.project:
                    resource = libutils.path_to_resource(pycore.project, path)
                    module = pyobjects.PyModule(pycore, None, resource)
                    return (module, lineno)
            return (None, None)
    builtins.BuiltinName = PatchedBuiltinName

