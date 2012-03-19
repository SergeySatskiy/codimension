
" Password server proxy "

import sys
from rpdb2exceptions import BadVersion, EncryptionExpected, \
                            EncryptionNotSupported, DecryptionFailure, \
                            AuthenticationBadData, AuthenticationFailure, \
                            CConnectionException, AuthenticationBadIndex
from rpdb2utils import as_unicode, safe_str, \
                       get_interface_compatibility_version
from rpdb2debug import print_debug_exception, print_debug

try:
    import xmlrpclib
except:
    #
    # The above modules were renamed in Python 3 so try to import them 'as'
    #
    import xmlrpc.client as xmlrpclib

try:
    from Crypto.Cipher import DES
except ImportError:
    pass

def is_encryption_supported():
    " Is the Crypto module imported/available "
    return 'DES' in globals()



DISPACHER_METHOD = 'dispatcher_method'



def class_name(value):
    " Provides the class name "
    string = safe_str(value)

    if "'" in string:
        string = string.split("'")[1]

    assert(string.startswith(__name__ + '.'))
    return string




class CPwdServerProxy:
    """
    Encrypted proxy to the debuggee.
    Works by wrapping a xmlrpclib.ServerProxy object.
    """

    def __init__(self, crypto, uri, transport = None, target_rid = 0):
        self.m_crypto = crypto
        self.m_proxy = xmlrpclib.ServerProxy(uri, transport)

        self.m_fEncryption = is_encryption_supported()
        self.m_target_rid = target_rid

        self.m_method = getattr(self.m_proxy, DISPACHER_METHOD)


    def __set_encryption(self, fEncryption):
        " Sets encryption "
        self.m_fEncryption = fEncryption
        return


    def get_encryption(self):
        " Provides encryption "
        return self.m_fEncryption


    def __request(self, name, params):
        """
        Call debuggee method 'name' with parameters 'params'.
        """

        while True:
            try:
                #
                # Encrypt method and params.
                #
                fencrypt = self.get_encryption()
                args = (as_unicode(name), params, self.m_target_rid)
                (fcompress, digest, msg) = self.m_crypto.do_crypto(args,
                                                                   fencrypt)

                rpdb_version = as_unicode(get_interface_compatibility_version())

                rr = self.m_method(rpdb_version, fencrypt,
                                  fcompress, digest, msg)
                (fencrypt, fcompress, digest, msg) = rr

                #
                # Decrypt response.
                #
                ((max_index, _r, _e), \
                 identifier) = self.m_crypto.undo_crypto(fencrypt, fcompress,
                                                         digest, msg,
                                                         fVerifyIndex = False)

                if _e is not None:
                    raise _e

            except AuthenticationBadIndex:
                ee = sys.exc_info()[1]
                self.m_crypto.set_index(ee.m_max_index, ee.m_anchor)
                continue

            except xmlrpclib.Fault:
                fault = sys.exc_info()[1] 
                if class_name(BadVersion) in fault.faultString:
                    ss = fault.faultString.split("'")
                    version = ['', ss[1]][len(ss) > 0]
                    raise BadVersion(version)

                if class_name(EncryptionExpected) in fault.faultString:
                    raise EncryptionExpected

                elif class_name(EncryptionNotSupported) in fault.faultString:
                    if self.m_crypto.m_fAllowUnencrypted:
                        self.__set_encryption(False)
                        continue

                    raise EncryptionNotSupported

                elif class_name(DecryptionFailure) in fault.faultString:
                    raise DecryptionFailure

                elif class_name(AuthenticationBadData) in fault.faultString:
                    raise AuthenticationBadData

                elif class_name(AuthenticationFailure) in fault.faultString:
                    raise AuthenticationFailure

                else:
                    print_debug_exception()
                    assert False

            except xmlrpclib.ProtocolError:
                print_debug("Caught ProtocolError for %s" % name)
                #print_debug_exception()
                raise CConnectionException

            return _r

    def __getattr__(self, name):
        " Provides an attribute value "
        return xmlrpclib._Method(self.__request, name)


