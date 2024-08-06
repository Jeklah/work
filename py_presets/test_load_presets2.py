import os
import paramiko
import pytest

from load_presets import sftp_connect, upload_preset_dir, does_file_exist, transport_connect, sftp_upload

# Mocking user credentials
USER = 'qxuser'
PASSW = 'phabrixqx'
LXP500_USER = 'root'
LXP500_PASS = 'PragmaticPhantastic'


def pytest_addoption(parser):
    parser.addoption("--hostname", action="store",
                     default="qx-022160", help="Hostname for the SFTP server")


@pytest.fixture
def hostname(request):
    return request.config.getoption("--hostname")


def test_does_file_exist(hostname, USER, PASSW):
    transport = transport_connect(hostname, USER, PASSW)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print(type(sftp))
    assert does_file_exist('presets/my_preset.preset', sftp)


def test_transport_connect():
    transport = transport_connect('qx-022160', USER, PASSW)
    assert transport is not None


def test_sftp_upload():
    os.chdir('presets')

    result = sftp_upload('qx-022160', 'my_preset.preset')
    assert result


def test_sftp_connect():
    print('Testing existing files.')
    result = sftp_connect('qx-022160', 'my_preset.preset')
    assert result
    print('Testing non-existing files.')
    result = sftp_connect('qx-022160', 'non_existing_file.preset')
    assert not result


def test_upload_preset_dir():
    # Test with actual directory upload here
    print('Testing with actual directory upload')
    result = upload_preset_dir('presets', 'qx-022160')
    assert result

    # Test with non-existing directory
    print('Testing with non-existing directory')
    result = upload_preset_dir('non_existing_dir', 'qx-022160')
    assert not result
