
" rpc client classes "

import sys
import socket
import os
import time

try:
    import xmlrpclib
    import httplib
except:
    #
    # The above modules were renamed in Python 3 so try to import them 'as'
    #
    import xmlrpc.client as xmlrpclib
    import http.client as httplib


from rpdb2debug import print_debug
from rpdb2utils import is_py3k, _print
from rpdb2globals import PING_TIMEOUT


LOCAL_TIMEOUT = 1.0


class CTimeoutHTTPConnection(httplib.HTTPConnection):
    """
    Modification of httplib.HTTPConnection with timeout for sockets.
    """

    _rpdb2_timeout = PING_TIMEOUT

    def connect(self):
        """Connect to the host and port specified in __init__."""

        # New Python version of connect().
        if hasattr(self, 'timeout'):
            self.timeout = self._rpdb2_timeout
            return httplib.HTTPConnection.connect(self)

        # Old Python version of connect().
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(self.host, self.port, 0,
                                      socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                self.sock.settimeout(self._rpdb2_timeout)
                if self.debuglevel > 0:
                    print_debug("connect: (%s, %s)" % (self.host, self.port))
                self.sock.connect(sa)
            except socket.error:
                msg = sys.exc_info()[1]
                if self.debuglevel > 0:
                    print_debug('connect fail: ' + repr((self.host, self.port)))
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error(msg)



class CLocalTimeoutHTTPConnection(CTimeoutHTTPConnection):
    """
    Modification of httplib.HTTPConnection with timeout for sockets.
    """

    _rpdb2_timeout = LOCAL_TIMEOUT



if is_py3k():
    class httplib_HTTP(object):
        " Stub type "
        pass
else:
    httplib_HTTP = httplib.HTTP



class CTimeoutHTTP(httplib_HTTP):
    """
    Modification of httplib.HTTP with timeout for sockets.
    """

    _connection_class = CTimeoutHTTPConnection



class CLocalTimeoutHTTP(httplib_HTTP):
    """
    Modification of httplib.HTTP with timeout for sockets.
    """

    _connection_class = CLocalTimeoutHTTPConnection



class CLocalTransport(xmlrpclib.Transport):
    """
    Modification of xmlrpclib.Transport to work around Zonealarm sockets
    bug.
    """

    _connection_class = httplib.HTTPConnection
    _connection_class_old = httplib_HTTP


    def make_connection(self, host):
        # New Python version of connect().
        # However, make_connection is hacked to always create a new connection
        # Otherwise all threads use single connection and crash.
        if hasattr(self, '_connection'):
            chost, self._extra_headers, x509 = self.get_host_info(host)
            return self._connection_class(chost)

        # Old Python version of connect().
        # create a HTTP connection object from a host descriptor
        host, extra_headers, x509 = self.get_host_info(host)
        return self._connection_class_old(host)


    def __parse_response(self, fileObj, sock):
        " read response from input file/socket, and parse it "

        pp, uu = self.getparser()

        while 1:
            if sock:
                response = sock.recv(1024)
            else:
                time.sleep(0.002)
                response = fileObj.read(1024)
            if not response:
                break
            if self.verbose:
                _print("body: " + repr(response))
            pp.feed(response)

        fileObj.close()
        pp.close()

        return uu.close()

    if os.name == 'nt':
        _parse_response = __parse_response


class CTimeoutTransport(CLocalTransport):
    """
    Modification of xmlrpclib.Transport with timeout for sockets.
    """

    _connection_class = CTimeoutHTTPConnection
    _connection_class_old = CTimeoutHTTP



class CLocalTimeoutTransport(CLocalTransport):
    """
    Modification of xmlrpclib.Transport with timeout for sockets.
    """

    _connection_class = CLocalTimeoutHTTPConnection
    _connection_class_old = CLocalTimeoutHTTP


