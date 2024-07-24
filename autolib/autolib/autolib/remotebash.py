"""\
A utility class that uploads a shell script to a device via sftp, executes it and then removes it when complete.
"""

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from autolib.models.qxseries.qxexception import QxException
from autolib.ssh import SSHTools


class TemporaryRemoteScript:
    """
    Context manager that will upload a bytearray to a temporary path on a Qx, make it executable and allow easy execution
    via SSH.
    """

    def __init__(self, logger: logging.Logger, hostname: str, username: str = "root", password: str = "PragmaticPhantastic", script: str = "", folder: str = "/tmp"):
        self.log = logger
        self._hostname = hostname
        self._ssh = SSHTools(logger, hostname)
        self._username = username
        self._password = password
        self._script = script
        self._remote_script_name = None
        self._folder = folder

    def __enter__(self):
        self.upload()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._remote_script_name:
            self.remove()

    def upload(self):
        """
        Upload the bash script to the device in /tmp and make it executable.

        """
        with NamedTemporaryFile(mode="w+t") as bash_script:
            bash_script.write(self._script)
            bash_script.flush()
            bash_script_filename = Path(bash_script.name).name

            self._remote_script_name = f'{self._folder}/{bash_script_filename}.sh'
            self._ssh.upload_via_sftp(bash_script.name, self._remote_script_name, self._username, self._password)
            self.log.info(f'Uploaded temporary script to {self._remote_script_name}')
            self._ssh.chmod_via_sftp(self._remote_script_name, 0o755, self._username, self._password)
            self.log.info(f'Changed file permissions of {self._remote_script_name} to 755')

    def remove(self):
        """\
        Remove the temporary script from the target device.
        """
        self._ssh.remove_via_sftp(self._remote_script_name, self._username, self._password)
        self.log.info(f'Removed temporary script {self._remote_script_name}')

    def execute(self, args="", timeout=30, **kwargs):
        """
        Call the remote script by invoking bash via ssh
        """
        debug = kwargs.get('debug', False)

        if not self._remote_script_name:
            raise QxException('Cannot execute remote bash script as upload was not successful')

        if debug:
            cmdline = f'bash -x {self._remote_script_name} {args}'
        else:
            cmdline = f'{self._remote_script_name} {args}'

        self.log.info(f'Running remote script: {cmdline}')
        return self._ssh.execute(cmdline, timeout)
