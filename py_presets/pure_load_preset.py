import sys
import os
import ftplib
import http.client
import argparse
import json

# User credentials
USER: str = 'qxuser'
PASSW: str = 'phabrixqx'
LXP500_USER: str = 'root'  # 'leader'
LXP500_PASS: str = 'PragmaticPhantastic'  # 'PictureWFMAnalyze'

load_preset_file = 'my_preset'


def load_preset(hostname: str, preset: str) -> bool:
    """
    Load a preset file to a unit using the REST API.

    :param hostname: Hostname of the unit
    :param preset: Name of the preset file to load
    :return: True if the load was successful, False otherwise
    """
    if preset.endswith('.preset'):
        print("Error: Please provide a preset file without the .preset extension")
        return False

    url = f'/api/v1/presets/userPresets/{preset}'
    headers = {"Content-Type": "application/json"}
    data = {"action": "load"}

    # Create a connection to the unit
    conn = http.client.HTTPConnection(hostname, 8080)

    try:
        # Prepare the request headers and body
        conn.request('PUT', url, body=json.dumps(data), headers=headers)

        # Get the response
        response = conn.getresponse()

        # Check the response status
        if response.status == 200:
            print(f"Preset '{preset}' loaded successfully")
            return True
        else:
            print(f"Error: Failed to load preset '{preset}'")
            return False
    except Exception as error:
        print(f"An error occurred: {error}")
        return False
    finally:
        conn.close()


def ftp_upload(hostname: str, username: str, password: str, local_path: str, remote_dir: str) -> bool:
    """
    Upload a file using FTP.

    :param hostname: Hostname of the FTP server.
    :param username: Username for authentication.
    :param password: Password for authentication.
    :param local_path: Path to the local file.
    :param remote_dir: Remote directory to upload the file to.
    :return: True if the upload was successful, False otherwise.
    """
    try:
        with ftplib.FTP(hostname) as ftp:
            ftp.login(user=username, passwd=password)
            ftp.cwd(remote_dir)

            with open(local_path, 'rb') as file:
                ftp.storbinary(f'STOR {os.path.basename(local_path)}', file)

            print(
                f"FTP upload success: {local_path} to {hostname}:{remote_dir}")
            return True
    except ftplib.all_errors as error:
        print(f"FTP upload failed: {error}")
    return False


def upload_preset_file(hostname: str, preset: str) -> bool:
    """
    Upload a preset file using FTP.

    :param hostname: Hostname of the unit.
    :param preset: Name of the preset file to upload,
    :return: True if the upload was successful, False, otherwise.
    """
    if not preset.endswith('.preset'):
        upload_anyway = input(
            f"Warning: The file '{preset}' does not have a .preset extension. Would you still like to upload? (y/n)")
        if upload_anyway.lower() != 'y':
            print("Upload cancelled.")
            return False
    model = hostname[:2]
    if model == 'qx':
        username = USER
        password = PASSW
        remote_dir = '/transfer/presets'
    else:
        username = LXP500_USER
        password = LXP500_PASS
        remote_dir = '/home/leader/transfer/presets'

    local_path = os.path.join(os.getcwd(), preset)
    return ftp_upload(hostname, username, password, local_path, remote_dir)
