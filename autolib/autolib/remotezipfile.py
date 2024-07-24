"""\
Tools for interacting with ZIP files on a remote device.
"""

import shutil
import tempfile

from pathlib import Path

from autolib.ssh import SSHTools


class RemoteZipFile:
    """\
    Provides a means to easily examine the content of a ZIP file from a remote server (by absolute SFTP path) locally.

    This class is a context manager that downloads a ZIP file from a remote server to a temporary directory, unzips it,
    removes the temporary archive and when __exit__ is called, removes the temporary directory and all of it's
    content.
    """
    def __init__(self, filepath, logger, hostname, username, password):
        self._filepath = filepath
        self._hostname = hostname
        self._username = username
        self._password = password
        self._log = logger
        self._ssh = SSHTools(logger, hostname)
        self._tempdir = None

    @property
    def filename(self) -> str:
        """\
        Get the filename portion of the requested remote ZIP file path
        """
        return Path(self._filepath).name

    @property
    def filestem(self) -> str:
        """\
        Get the filename stem portion of the requested remote ZIP file path (the filename minus it's extension).
        """
        return Path(self._filepath).stem

    @property
    def name(self) -> str:
        """\
        Get the name of the folder containing the ZIP file and a folder 'content' in which the Zip file has been
        extracted to.
        """
        return self._tempdir.name

    def __enter__(self):
        self._tempdir = tempfile.TemporaryDirectory(prefix='zip_file_content_')
        loudness_zipfile = Path(self._tempdir.name) / self.filename
        self._ssh.download_via_sftp(self._filepath, loudness_zipfile)
        unpack_target_dir = Path(self._tempdir.name) / 'content'
        shutil.unpack_archive(loudness_zipfile, unpack_target_dir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self._tempdir
