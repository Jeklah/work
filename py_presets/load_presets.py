#!/usr/bin/env python3
"""
A script that can be used by customers to upload a preset file or a directory
containing preset files to a unit using SFTP.

Author: Arthur Bowers
Company: Leader Electronics Ltd (Europe)
Date: 29/07/2024
"""
import sys
import os
import paramiko
import argparse

# User credentials
USER: str = 'qxuser'
PASSW: str = 'phabrixqx'
LXP500_USER: str = 'root'  # 'leader'
LXP500_PASS: str = 'PragmaticPhantastic'  # 'PictureWFMAnalyze'


def does_file_exist(file_name: str, sftp_conn: paramiko.SFTPClient) -> bool:
    """
    Check if a file exists.

    :param file_name: Name of the file to check
    :param sftp_conn: SFTP connection object
    :return: True if the file exists, False otherwise
    """
    try:
        print(f"cwd: {sftp_conn.getcwd()}")
        sftp_conn.stat(path=file_name)
        return True
    except FileNotFoundError:
        print(f"Error: File '{file_name}' not found")
        return False


def transport_connect(hostname: str, user: str, password: str) -> paramiko.Transport:
    """
    Create a transport object and connect to the remote server.

    :param hostname: Hostname of the remote server
    :param user: Username for the connection
    :param password: Password for the connection
    :return: A transport object
    """
    transport = paramiko.Transport((hostname, 22))
    transport.connect(username=user, password=password)
    return transport


def sftp_upload(hostname: str, preset: str) -> bool:
    """
    Connect to the remote server using SFTP.

    :param hostname: Hostname of the remote server
    :param preset: Name of the preset file to upload
    :return: True if the upload was successful, False otherwise
    """
    model = hostname[:2]
    if model == 'qx':
        transport = transport_connect(hostname, USER, PASSW)
        remote_dir = '/transfer/presets'
    else:
        transport = transport_connect(hostname, LXP500_USER, LXP500_PASS)
        #  'leader/transfer/presets' is the path for the leader user on the LPX500
        remote_dir = '/home/sftp/leader/transfer/presets'

    try:
        sftp = paramiko.SFTPClient.from_transport(transport)
        print(f"remote_dir: {remote_dir}")
        sftp.chdir(remote_dir)  # type: ignore
        file_name = preset if preset.endswith(
            '.preset') else f'{preset}.preset'
        local_path = os.path.join(os.getcwd(), file_name)
        remote_path = os.path.join(remote_dir, file_name)

        if does_file_exist(remote_path, sftp):  # type: ignore
            overwrite = input(
                f"File '{file_name}' exists on {hostname}. Overwrite? (y/n)")
            if overwrite != 'y':
                print("Upload cancelled.")
                return False
        sftp.put(localpath=local_path, remotepath=remote_path)  # type: ignore
        print(f"SFTP upload success: {local_path} to {hostname}:{remote_path}")
        return True
    except paramiko.AuthenticationException:
        print("SFTP Authentication failed")
        return False
    except Exception as error:
        print(f"An SFTP error occurred: {error}")
        return False
    finally:
        sftp.close()  # type: ignore
        transport.close()


def sftp_connect(hostname: str, preset: str) -> bool:
    """
    Upload a preset file using SFTP.

    :param hostname: Hostname of the remote server
    :param preset: Name of the preset file to upload
    :return: True if the upload was successful, False otherwise
    """
    # File details
    file_name: str = ''
    if type(file_name) is None:
        print("Error: Please provide a preset name")
        return False
    if preset is None:
        return False  # Code is reachable despite what pyright says
    file_name = preset if preset.endswith('.preset') else f'{preset}.preset'
    local_path: str = os.path.join(os.getcwd(), file_name)

    # Check if the file exists
    if not os.path.exists(local_path) or type(file_name) is None:
        print(f"Error: File '{file_name}' not found")
        return False

    # SFTP connection details
    try:
        return sftp_upload(hostname, preset)
    except paramiko.AuthenticationException:
        print("SFTP Authentication failed")
        return False
    except Exception as error:
        print(f"sftp-connect::An SFTP error occurred: : {error}")
        return False


def upload_preset_dir(preset_dir: str, hostname: str) -> bool:
    """
    Upload all preset files in a directory to a remote server.

    :param preset_dir: Name of the directory containing the preset files
    :param hostname: Hostname of the remote server
    :return: True if the upload was successful, False otherwise
    """

    # Check if the directory exists
    if not os.path.exists(preset_dir):
        print(f"Error: Directory '{preset_dir}' not found")
        return False

    model = hostname[:2]
    if model == 'qx':
        transport = transport_connect(hostname, USER, PASSW)
        remote_dir = '/transfer/presets'
    else:
        transport = transport_connect(hostname, LXP500_USER, LXP500_PASS)
        remote_dir = '/home/sftp/leader/transfer/presets'
    # Change to the directory and iterate through the files
    try:
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.chdir(remote_dir)  # type: ignore

        for file_name in os.listdir(preset_dir):
            local_path = f'{os.getcwd()}/{os.path.join(preset_dir, file_name)}'
            if not os.path.isfile(local_path):
                continue

            remote_path = os.path.join(remote_dir, file_name)

            # Check if the file is already uploaded
            if does_file_exist(remote_dir, sftp):  # type: ignore
                overwrite = input(
                    f"File '{file_name}' exists on {hostname}. Overwrite? (y/n)")
                if overwrite.lower() != 'y':
                    print("Skipping upload.")
                    continue

            sftp.put(localpath=local_path,  # type: ignore
                     remotepath=remote_path)  # type: ignore
            print(f"Uploaded {file_name} to {hostname}:{remote_path}")
        return True
    except paramiko.AuthenticationException:
        print("SFTP Authentication failed")
        return False
    except Exception as error:
        print(f"An SFTP error occurred: {error}")
        return False
    finally:
        sftp.close()  # type: ignore
        transport.close()


def main():
    parser = argparse.ArgumentParser(
        description='Upload a file via SFTP for Qx or LPX500')
    parser.add_argument('--hostname', type=str,
                        help='hostname of the remote server')
    parser.add_argument('--preset', type=str,
                        help='Name of the preset file to upload')
    parser.add_argument('--presetdir', type=str,
                        help='Name of the directory containing preset files to upload')
    args = parser.parse_args()

    if not args.preset and not args.presetdir:
        print("Error: Please provide a preset file or directory.")
        sys.exit(1)

    if args.preset:
        success = sftp_connect(args.hostname, args.preset)
    else:
        success = upload_preset_dir(args.presetdir, args.hostname)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
