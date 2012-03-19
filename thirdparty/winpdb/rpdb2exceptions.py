
"""
Exceptions used in rpdb2
"""

class CException(Exception):
    """ Base exception class for the debugger. """

    def __init__(self, *args):
        Exception.__init__(self, *args)


class BadMBCSPath(CException):
    """
    Raised on Windows systems when the python executable or debugger script
    path can not be encoded with the file system code page. This means that
    the Windows code page is misconfigured.
    """


class NotPythonSource(CException):
    """
    Raised when an attempt to load non Python source is made.
    """



class InvalidScopeName(CException):
    """
    Invalid scope name.
    This exception might be thrown when a request was made to set a breakpoint
    to an unknown scope.
    """



class BadArgument(CException):
    """ Bad Argument. """



class ThreadNotFound(CException):
    """ Thread not found. """



class NoThreads(CException):
    """ No Threads. """



class ThreadDone(CException):
    """ Thread Done. """



class DebuggerNotBroken(CException):
    """
    Debugger is not broken.
    This exception is thrown when an operation that can only be performed
    while the debuggee is broken, is requested while the debuggee is running.
    """



class InvalidFrame(CException):
    """
    Invalid Frame.
    This exception is raised if an operation is requested on a stack frame
    that does not exist.
    """



class NoExceptionFound(CException):
    """
    No Exception Found.
    This exception is raised when exception information is requested, but no
    exception is found, or has been thrown.
    """



class CConnectionException(CException):
    " Base class for connection related exceptions "
    def __init__(self, *args):
        CException.__init__(self, *args)



class FirewallBlock(CConnectionException):
    """ Firewall is blocking socket communication. """



class BadVersion(CConnectionException):
    """ Bad Version. """
    def __init__(self, version):
        CConnectionException.__init__(self)

        self.m_version = version

    def __str__(self):
        return repr(self.m_version)



class UnexpectedData(CConnectionException):
    """ Unexpected data. """



class AlreadyAttached(CConnectionException):
    """ Already Attached. """



class NotAttached(CConnectionException):
    """ Not Attached. """



class SpawnUnsupported(CConnectionException):
    """ Spawn Unsupported. """



class UnknownServer(CConnectionException):
    """ Unknown Server. """



class CSecurityException(CConnectionException):
    " Base class for security exceptions "
    def __init__(self, *args):
        CConnectionException.__init__(self, *args)



class UnsetPassword(CSecurityException):
    """ Unset Password. """



class EncryptionNotSupported(CSecurityException):
    """ Encryption Not Supported. """



class EncryptionExpected(CSecurityException):
    """ Encryption Expected. """


class DecryptionFailure(CSecurityException):
    """ Decryption Failure. """



class AuthenticationBadData(CSecurityException):
    """ Authentication Bad Data. """



class AuthenticationFailure(CSecurityException):
    """ Authentication Failure. """



class AuthenticationBadIndex(CSecurityException):
    """ Authentication Bad Index. """
    def __init__(self, max_index = 0, anchor = 0):
        CSecurityException.__init__(self)

        self.m_max_index = max_index
        self.m_anchor = anchor

    def __str__(self):
        return repr((self.m_max_index, self.m_anchor))

