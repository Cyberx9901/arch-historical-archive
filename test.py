#!/usr/bin/env python

import upload_pkg_internetarchive

import mock
from unittest.mock import MagicMock
import unittest

class TestUploader(unittest.TestCase):

    def test_upload_pkg(self):
        mock_uploader = MagicMock()
        app = upload_pkg_internetarchive.ArchiveUploader(mock_uploader)
        app.main('./test-data/archive/packages/f/fb-client')

        mock_uploader.upload.assert_called_with('archlinux_pkg_fb-client',
                files=['./test-data/archive/packages/f/fb-client/fb-client-2.0.4-1-any.pkg.tar.xz',
                    './test-data/archive/packages/f/fb-client/fb-client-2.0.3-2-any.pkg.tar.xz',
                    './test-data/archive/packages/f/fb-client/fb-client-2.0.4-1-any.pkg.tar.xz.sig',
                    './test-data/archive/packages/f/fb-client/fb-client-2.0.3-2-any.pkg.tar.xz.sig'],
                metadata=mock.ANY)



if __name__ == '__main__':
    unittest.main()
