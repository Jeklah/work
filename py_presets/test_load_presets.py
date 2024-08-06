import unittest
from unittest.mock import patch, MagicMock, call
import os
import paramiko  # type: ignore
from io import StringIO

from load_presets import sftp_connect, upload_preset_dir, does_file_exist, transport_connect, sftp_upload


# Mocking user credentials
USER = 'qxuser'
PASSW = 'phabrixqx'
LXP500_USER = 'root'
LXP500_PASS = 'PragmaticPhantastic'


class TestSFTPScript(unittest.TestCase):

    @patch('load_presets.paramiko.Transport')
    def test_does_file_exist(self, MockSFTPClient):
        mock_sftp = MockSFTPClient.return_value
        mock_sftp.stat.return_value = None

        # Test if file exists
        self.assertTrue(does_file_exist('my_preset.preset', mock_sftp))

        # Test if file does not exist
        mock_sftp.stat.side_effect = FileNotFoundError
        self.assertFalse(does_file_exist(
            'presets/my_preset.preset', mock_sftp))

    @patch('load_presets.paramiko.Transport')
    def test_transport_connect(self, MockTransport):
        mock_transport = MockTransport.return_value

        transport = transport_connect('qx-022160', USER, PASSW)
        mock_transport.connect.assert_called_with(
            username=USER, password=PASSW)
        self.assertEqual(transport, mock_transport)

    @patch('load_presets.paramiko.SFTPClient')
    @patch('load_presets.transport_connect')
    @patch('load_presets.os.path.exists')
    @patch('load_presets.os.getcwd')
    def test_sftp_upload(self, mock_getcwd, mock_exists, mock_transport_connect, MockSFTPClient):
        mock_getcwd.return_value = '/home/arthur/projects/work/py_presets'
        mock_exists.return_value = True
        # mock_transport = mock_transport_connect.return_value
        mock_sftp = MockSFTPClient.from_transport.return_value

        # Test upload success
        with patch('builtins.input', return_value='y'):
            mock_sftp.put.return_value = None
            self.assertTrue(sftp_upload('qx-022160', 'my_preset.preset'))

        # Test file overwrite scenario
        mock_sftp.put.side_effect = None
        with patch('builtins.input', return_value='y'):
            self.assertTrue(sftp_upload('qx-022160',  'my_preset.preset'))

        # Test upload cancellation due to existing file.
        with patch('builtins.input', return_value='n'):
            self.assertFalse(sftp_upload('qx-022160', 'my_preset.preset'))

    @patch('load_presets.sftp_upload')
    @patch('load_presets.os.path.exists')
    def test_sftp_connect(self, mock_exists, mock_sftp_upload):
        mock_exists.return_value = True
        mock_sftp_upload.return_value = True

        # Test successful upload
        self.assertTrue(sftp_connect('qx-022160', 'my_preset.preset'))

        # Test file does not exist locally
        mock_exists.return_value = False
        self.assertFalse(sftp_connect('qx-022160', 'nopreset.preset'))

    @patch('paramiko.SFTPClient')
    @patch('paramiko.Transport')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.listdir')
    @patch('os.getcwd')
    def test_upload_preset_dir(self, mock_getcwd, mock_listdir, mock_isfile, mock_exists, mock_transport_connect, MockSFTPClient):
        mock_getcwd.return_value = '/home/arthur/projects/work/py_presets'
        mock_listdir.return_value = [
            'my_preset.preset', 'preset1.preset', 'preset2.preset']
        mock_isfile.side_effect = lambda filepath: filepath.endswith('.preset')
        mock_exists.return_value = True
        # mock_transport = mock_transport_connect.return_value
        mock_sftp = MockSFTPClient.from_transport.return_value

        # Test successful directory upload
        mock_sftp.put.return_value = None
        with patch('builtins.input', return_value='y'):
            self.assertTrue(upload_preset_dir('presets', 'qx-022160'))

        # Test skipping non-preset files
        with patch('builtins.input', return_value='y'):
            self.assertTrue(upload_preset_dir('presets', 'qx-022160'))

        # Test directory not found
        with patch('builtins.input', return_value='n'):
            self.assertTrue(upload_preset_dir(
                '/home/arthur/projects/work/py_presets/nonexistent/dir', 'qx-022160'))


if __name__ == '__main__':
    unittest.main()
