

" Crypto "


import threading
import hmac
import random
import base64
import zlib
import time
import pickle

try:
    from Crypto.Cipher import DES
except ImportError:
    pass

try:
    import hashlib
    _md5 = hashlib.md5
except:
    import md5
    _md5 = md5

from rpdb2utils import is_unicode, as_bytes, as_unicode
from rpdb2exceptions import EncryptionExpected, EncryptionNotSupported, \
                            DecryptionFailure, AuthenticationFailure, \
                            AuthenticationBadData, AuthenticationBadIndex
from rpdb2debug import print_debug_exception


INDEX_TABLE_SIZE = 100


def is_encryption_supported():
    " Is the Crypto module imported/available "
    return 'DES' in globals()


class CCrypto:
    """
    Handle authentication and encryption of data, using password protection.
    """

    m_keys = {}

    def __init__(self, _rpdb2_pwd, fAllowUnencrypted, rid):
        assert(is_unicode(_rpdb2_pwd))
        assert(is_unicode(rid))

        self.m_rpdb2_pwd = _rpdb2_pwd
        self.m_key = self.__calc_key(_rpdb2_pwd)

        self.m_fAllowUnencrypted = fAllowUnencrypted
        self.m_rid = rid

        self.m_failure_lock = threading.RLock()

        self.m_lock = threading.RLock()

        self.m_index_anchor_in = random.randint(0, 1000000000)
        self.m_index_anchor_ex = 0

        self.m_index = 0
        self.m_index_table = {}
        self.m_index_table_size = INDEX_TABLE_SIZE
        self.m_max_index = 0


    def __calc_key(self, _rpdb2_pwd):
        """
        Create and return a key from a password.
        A Weak password means a weak key.
        """

        if _rpdb2_pwd in CCrypto.m_keys:
            return CCrypto.m_keys[_rpdb2_pwd]

        key = as_bytes(_rpdb2_pwd)
        suffix = key[:16]

        dd = hmac.new(key, digestmod = _md5)

        #
        # The following loop takes around a second to complete
        # and should strengthen the password by ~12 bits.
        # a good password is ~30 bits strong so we are looking
        # at ~42 bits strong key
        #
        for i in range(2 ** 12):
            dd.update((key + suffix) * 16)
            key = dd.digest()

        CCrypto.m_keys[_rpdb2_pwd] = key

        return key


    def set_index(self, i, anchor):
        " Sets an index "
        try:
            self.m_lock.acquire()

            self.m_index = i
            self.m_index_anchor_ex = anchor

        finally:
            self.m_lock.release()


    def get_max_index(self):
        " Provides max index "
        return self.m_max_index


    def do_crypto(self, args, fencrypt):
        """
        Sign args and possibly encrypt.
        Return signed/encrypted string.
        """

        if not fencrypt and not self.m_fAllowUnencrypted:
            raise EncryptionExpected

        if fencrypt and not is_encryption_supported():
            raise EncryptionNotSupported

        (digest, ss) = self.__sign(args)

        fcompress = False

        if len(ss) > 50000:
            _s = zlib.compress(ss)

            if len(_s) < len(ss) * 0.4:
                ss = _s
                fcompress = True

        if fencrypt:
            ss = self.__encrypt(ss)

        ss = base64.encodestring(ss)
        uu = as_unicode(ss)

        return (fcompress, digest, uu)


    def undo_crypto(self, fencrypt, fcompress,
                          digest, msg, fVerifyIndex = True):
        """
        Take crypto string, verify its signature and decrypt it, if
        needed.
        """

        if not fencrypt and not self.m_fAllowUnencrypted:
            raise EncryptionExpected

        if fencrypt and not is_encryption_supported():
            raise EncryptionNotSupported

        ss = as_bytes(msg)
        ss = base64.decodestring(ss)

        if fencrypt:
            ss = self.__decrypt(ss)

        if fcompress:
            ss = zlib.decompress(ss)

        args, iD = self.__verify_signature(digest, ss, fVerifyIndex)

        return (args, iD)


    def __encrypt(self, ss):
        " Encrypts "
        s_padded = ss + as_bytes('\x00') * \
                   (DES.block_size - (len(ss) % DES.block_size))

        key_padded = (self.m_key + as_bytes('0') * \
                      (DES.key_size - \
                       (len(self.m_key) % DES.key_size))) \
                        [:DES.key_size]
        iv = '0' * DES.block_size

        dd = DES.new(key_padded, DES.MODE_CBC, iv)
        return dd.encrypt(s_padded)


    def __decrypt(self, ss):
        " Decrypts "
        try:
            key_padded = (self.m_key + as_bytes('0') * \
                          (DES.key_size - \
                           (len(self.m_key) % DES.key_size))) \
                            [:DES.key_size]
            iv = '0' * DES.block_size

            dd = DES.new(key_padded, DES.MODE_CBC, iv)
            _s = dd.decrypt(ss).strip(as_bytes('\x00'))

            return _s

        except:
            self.__wait_a_little()
            raise DecryptionFailure


    def __sign(self, args):
        " Signs "
        i = self.__get_next_index()
        pack = (self.m_index_anchor_ex, i, self.m_rid, args)

        #print_debug('***** 1' + repr(args)[:50])
        ss = pickle.dumps(pack, 2)
        #print_debug('***** 2' + repr(args)[:50])

        hh = hmac.new(self.m_key, ss, digestmod = _md5)
        dd = hh.hexdigest()

        #if 'coding:' in ss:
        #    print_debug('%s, %s, %s\n\n==========\n\n%s' % (len(ss),
        #                                                    dd,
        #                                                    repr(args),
        #                                                    repr(ss)))

        return (dd, ss)


    def __get_next_index(self):
        " Provides next index "
        try:
            self.m_lock.acquire()

            self.m_index += 1
            return self.m_index
        finally:
            self.m_lock.release()


    def __verify_signature(self, digest, ss, fVerifyIndex):
        " Verify signature "
        try:
            hh = hmac.new(self.m_key, ss, digestmod = _md5)
            dd = hh.hexdigest()

            #if 'coding:' in ss:
            #    print_debug('%s, %s, %s, %s' % (len(s), digest, dd, repr(s)))

            if dd != digest:
                self.__wait_a_little()
                raise AuthenticationFailure

            pack = pickle.loads(ss)
            (anchor, i, iD, args) = pack

        except AuthenticationFailure:
            raise

        except:
            print_debug_exception()
            self.__wait_a_little()
            raise AuthenticationBadData

        if fVerifyIndex:
            self.__verify_index(anchor, i, iD)

        return args, iD


    def __verify_index(self, anchor, i, iD):
        """
        Manage messages ids to prevent replay of old messages.
        """

        try:
            try:
                self.m_lock.acquire()

                if anchor != self.m_index_anchor_in:
                    raise AuthenticationBadIndex(self.m_max_index,
                                                 self.m_index_anchor_in)

                if i > self.m_max_index + INDEX_TABLE_SIZE // 2:
                    raise AuthenticationBadIndex(self.m_max_index,
                                                 self.m_index_anchor_in)

                i_mod = i % INDEX_TABLE_SIZE
                (iv, idl) = self.m_index_table.get(i_mod, (None, None))

                #print >> sys.__stderr__, i, i_mod, iv, self.m_max_index

                if (iv is None) or (i > iv):
                    idl = [iD]
                elif (iv == i) and (not iD in idl):
                    idl.append(iD)
                else:
                    raise AuthenticationBadIndex(self.m_max_index,
                                                 self.m_index_anchor_in)

                self.m_index_table[i_mod] = (i, idl)

                if i > self.m_max_index:
                    self.m_max_index = i

                return self.m_index

            finally:
                self.m_lock.release()

        except:
            self.__wait_a_little()
            raise


    def __wait_a_little(self):
        " Waits a bit "
        self.m_failure_lock.acquire()
        time.sleep((1.0 + random.random()) / 2)
        self.m_failure_lock.release()
        return


