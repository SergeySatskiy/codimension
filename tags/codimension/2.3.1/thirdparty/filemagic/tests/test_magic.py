import gc
import mock
import warnings
import sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import magic


class TestMagic(unittest.TestCase):

    def test_has_version(self):
        self.assertTrue(magic.__version__)

    def test_consistent_database(self):
        with magic.Magic() as m:
            self.assertTrue(m.consistent)

    def test_invalid_database(self):
        self.assertRaises(magic.MagicError, magic.Magic,
                paths=['test/magic/_false_'])

    def test_use_after_closed(self):
        with magic.Magic() as m:
            pass
        self.assertRaises(magic.MagicError, m.list, 'setup.py')

    def test_id_filename(self):
        with magic.Magic(paths=['tests/magic/python']) as m:
            id = m.id_filename('setup.py')
            self.assertTrue(id.startswith('Python script'))

    def test_id_buffer(self):
        with magic.Magic(paths=['tests/magic/python']) as m:
            id = m.id_buffer('#!/usr/bin/env python\n')
            self.assertTrue(id.startswith('Python script'))

    def test_mime_type_file(self):
        with magic.Magic(paths=['tests/magic/python'],
                flags=magic.MAGIC_MIME_TYPE) as m:
            id = m.id_filename('setup.py')
            self.assertEqual(id, 'text/x-python')

    def test_mime_type_desc(self):
        with magic.Magic(paths=['tests/magic/python'],
                flags=magic.MAGIC_MIME_TYPE) as m:
            id = m.id_buffer('#!/usr/bin/env python\n')
            self.assertEqual(id, 'text/x-python')

    def test_mime_encoding_file(self):
        with magic.Magic(paths=['tests/magic/python'],
                flags=magic.MAGIC_MIME_ENCODING) as m:
            id = m.id_filename('setup.py')
            self.assertEqual(id, 'us-ascii')

    def test_mime_encoding_desc(self):
        with magic.Magic(paths=['tests/magic/python'],
                flags=magic.MAGIC_MIME_ENCODING) as m:
            id = m.id_buffer('#!/usr/bin/env python\n')
            self.assertEqual(id, 'us-ascii')

    def test_repr(self):
        with magic.Magic(paths=['tests/magic/python'],
                flags=magic.MAGIC_MIME_ENCODING) as m:
            n = eval(repr(m), {'Magic': magic.Magic})
            n.close()

    @unittest.skipIf(not hasattr(unittest.TestCase, 'assertWarns'),
            'unittest does not support assertWarns')
    def test_resource_warning(self):
        with self.assertWarns(ResourceWarning):
            m = magic.Magic()
            del m

    @unittest.skipIf(hasattr(sys, 'pypy_version_info'),
            'garbarge collection on PyPy is not deterministic')
    def test_weakref(self):
        magic_close = magic.api.magic_close
        with mock.patch('magic.api.magic_close') as close_mock:
            close_mock.side_effect = magic_close
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                m = magic.Magic()
                del m
                gc.collect()
            self.assertEqual(close_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()
