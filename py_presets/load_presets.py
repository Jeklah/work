"""
A script that can be used by customers to upload preset files to a Phabrix Qx unit via SFTP.
Author: Arthur Bowers
Company: Leader Electronics (Europe) Ltd
Date: 23/07/2024
"""

import argparse
import os
import paramiko
from paramiko.ssh_exception import AuthenticationException


def sftp_upload(unit_name: str, preset_name: str) -> None:
    """
    Uploads a preset file to a Phabrix Qx unit via SFTP

    :param unit_name: The name of the Phabrix Qx unit
    :param preset_name: The name of the preset file to upload
    """
    # SFTP connection details
    host: str = f'{unit_name}'
    port: int = 22
    user: str = 'qxuser'
    passw: str = 'phabrixqx'

    # File details
    file_name: str = f'{preset_name}.preset'
    local_path: str = os.path.join(os.getcwd(), file_name)

    # Check if the file exists
    if not os.path.exists(local_path):
        print(f"Error: File '{file_name}' not found")
        return

    # Connect to the SFTP server
    transport = paramiko.Transport((host, port))
    try:
        transport.connect(username=user, password=passw)
    except AuthenticationException as auth_err:
        print(f'Authentication Error: {auth_err}')
        return
    sftp = paramiko.SFTPClient.from_transport(transport)

    try:
        # Change to the presets directory
        sftp.chdir('transfer/presets')  # type: ignore

        # Upload the preset file
        sftp.put(localpath=local_path, remotepath=file_name)  # type: ignore
        print(f'Successfully uploaded {file_name} to {unit_name}')

    except FileNotFoundError:
        print(f'Error: File {file_name} not found')

    finally:
        # Close the SFTP connection
        sftp.close()  # type: ignore
        transport.close()


if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='SFTP Upload Preset File to a give Unit')
    parser.add_argument('unit_name', type=str,
                        help='The name of the Phabrix Qx unit')
    parser.add_argument('preset_name', type=str,
                        help='The name of the preset file to upload (without extension)')
    args = parser.parse_args()

    # Call the SFTP upload function
    sftp_upload(args.unit_name, args.preset_name)
