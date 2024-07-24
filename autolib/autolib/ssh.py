"""\
Provides a class with some SSH convenience methods.
"""

import logging
import socket
import paramiko
import time
from pathlib import Path
from autolib.models.qxseries.qxexception import QxException
from typing import List, Tuple


class SSHTools:
    """
    Provide SSH remote command execution support
    """
    def __init__(self, logger: logging.Logger, hostname: str, username: str = "root", password: str = "PragmaticPhantastic"):
        self.log = logger
        self._hostname = hostname
        self._username = username
        self._password = password
        self._client = paramiko.SSHClient()

    def __del__(self):
        self._client.close()

    def execute(self, command: str, timeout: int = 30, retries: int = 5) -> Tuple[int, bytes, bytes]:
        """
        Execute a command via SSH. This is useful for single command lines. If multiple commands are
        required, consider using the TemporaryRemoteScript object from the models.remotebash module.

        :param command: The command to pass to the shell on the remote device.
        :param timeout: The timeout duration in seconds after which the operation is cancelled.
        :param retries: The number of times to try to connect and execute the command.
        :return: Tuple of bytes objects containing exit status code, stdout and stderr.
        """
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy)

        for retry in range(retries):
            try:
                self._client.connect(self._hostname, port=22, username=self._username, password=self._password, banner_timeout=200)
                break
            except (socket.gaierror, ConnectionResetError) as e:
                self.log.info(f"Received exception {e} - waiting 2s then retrying")
                time.sleep(2)

        _, _stdout, _stderr = self._client.exec_command(command, -1, timeout)
        stdout = _stdout.read()
        stderr = _stderr.read()
        exit_status = _stdout.channel.recv_exit_status()
        self._client.close()
        return exit_status, stdout, stderr

    def upload_via_sftp(self, local_file: str, remote_file: str, username: str = "qxuser", password: str = "phabrixqx"):
        """
        Upload a local file to the Qx using the qxuser credentials (so this is the limited view the customer sees).
        This method ignores the credentials set in __init__, using the qxuser credentials (which may be overridden).

        :param local_file: The absolute path to a local file to upload
        :param remote_file: The absolute path and filename to upload to on the Qx
        :param username: Alternative username in place of the default 'qxuser'
        :param password: Alternative password in place of the default 'phabrixqx'
        """
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy)
        self._client.connect(self._hostname, 22, username=username, password=password)
        sftp = self._client.open_sftp()
        sftp.put(local_file, remote_file)
        sftp.close()

    def remove_via_sftp(self, remote_file: str, username: str = "qxuser", password: str = "phabrixqx"):
        """
        Remove a remote file from the Qx using the qxuser credentials (so this is the limited view the customer sees).
        This method ignores the credentials set in __init__, using the qxuser credentials (which may be overridden).

        :param remote_file: The absolute path and filename to upload to on the Qx
        :param username: Alternative username in place of the default 'qxuser'
        :param password: Alternative password in place of the default 'phabrixqx'
        """
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy)
        self._client.connect(self._hostname, 22, username=username, password=password)
        sftp = self._client.open_sftp()
        sftp.remove(remote_file)
        sftp.close()

    def download_via_sftp(self, remote_file: str, local_file: str, username: str = "qxuser", password: str = "phabrixqx", retries: int = 1, delay: int = 1):
        """
        Download a file from the Qx using specified credentials (by default the qxuser account, the limited view the
        customer sees). The retries and delay parameters may be used to wait until the supplied filename is found in
        remote directory.

        Usually the file will be present unless it's a file being generated on the Qx (for example a screenshot).
        This method ignores the credentials set in __init__, using the qxuser credentials (which may be overridden).

        :param remote_file: The absolute path and filename to upload to on the Qx
        :param local_file: The absolute path to a local file to upload
        :param username: Alternative username in place of the default 'qxuser'
        :param password: Alternative password in place of the default 'phabrixqx'
        :param retries: Number of retries
        :param delay: Delay between retries in seconds
        """
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy)
        self._client.connect(self._hostname, 22, username=username, password=password)

        # Rather annoyingly, the Paramiko sftp code doesn't appear to provide a context manager so ensure that
        # all exit paths from this method close the sftp connection explicitly.
        sftp = self._client.open_sftp()

        # Verify local directory for screenshots and if not create one
        local_file_folder = Path(local_file).parent
        if not local_file_folder.exists():
            raise QxException(f"Local file path does not exist - {local_file_folder}")

        remote_filename = Path(remote_file).name
        remote_path = Path(remote_file).parent

        try:
            found = False
            for _ in range(retries):
                if remote_filename in sftp.listdir(str(remote_path)):
                    self.log.info(f"Found file {remote_filename} in remote folder {remote_path}")
                    found = True
                    break
                else:
                    time.sleep(delay)
        except AttributeError:
            sftp.close()
            raise QxException(f'sFTP is not enabled on this client.')

        if found:
            try:
                sftp.get(str(remote_file), str(local_file))
                self.log.info(f"Remote file '{remote_filename}' has been copied to {local_file}")
                return True
            except FileNotFoundError as err:
                raise QxException(str(err))
            finally:
                sftp.close()
        else:
            sftp.close()
            raise QxException(f"Could not find {remote_file} on unit {self._hostname}")

    def chmod_via_sftp(self, remote_file: str, mode: int, username: str = "qxuser", password: str = "phabrixqx"):
        """
        Change the mode of the specified file on the remote device..

        :param remote_file: The absolute path and filename to upload to on the Qx
        :param mode: The mode permissions value (see os.chmod documentation).
        :param username: Alternative username in place of the default 'qxuser'
        :param password: Alternative password in place of the default 'phabrixqx'
        """
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy)
        self._client.connect(self._hostname, 22, username=username, password=password)
        sftp = self._client.open_sftp()
        sftp.chmod(remote_file, mode)
        sftp.close()

    def remote_file_list(self, remote_path: str, username: str = "qxuser", password: str = "phabrixqx") -> List[str]:
        """\
        Retrieve a list of files and folders etc. from a remote sftp path.

        :param remote_path: The absolute path to examine on the Qx
        :param username: Alternative username in place of the default 'qxuser'
        :param password: Alternative password in place of the default 'phabrixqx'
        """
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy)
        self._client.connect(self._hostname, 22, username=username, password=password)
        sftp = self._client.open_sftp()
        sftp.chdir(remote_path)
        return sftp.listdir()
