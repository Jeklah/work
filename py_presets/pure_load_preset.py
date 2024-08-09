import sys
import os
import subprocess
import requests
import argparse
import json

USER: str = 'qxuser'
PASSW: str = 'phabrixqx'
LXP500_USER: str = 'root'
LXP500_PASSW: str = 'PragmaticPhantastic'


def load_preset(hostname: str, preset: str) -> bool:
    """
    Load a preset file to a unit using the REST API

    :param hostname: Hostname of the unit
    :param preset: Name of the preset file to load
    :return: True if successful, False otherwise
    """
    preset = preset.removesuffix('.preset')   # type: ignore
    url = f'http://{hostname}:8080/api/v1/presets/userPresets/{preset}'
    headers = {"Content-Type": "application/json"}
    data = {"action": "load"}
    print("Loading preset...")
    try:
        response = requests.put(url, headers=headers,
                                data=json.dumps(data), verify=False)
        if response.status_code == 200:
            print(f"Preset '{preset}' loaded successfully")
            return True
        else:
            print(
                f"Error Failed to load preset '{preset}'. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f'Error: {e}')
        return False


def sftp_upload(hostname: str, preset: str) -> bool:
    """
    Connect to the remote server using SFTP and upload a preset file.

    :param hostname: Hostname of the unit
    :param preset: Name of the preset file to upload
    :return: True if successful, False otherwise
    """
    if not preset.endswith('.preset'):
        upload_anyway = input(
            f"Warning: The file '{preset}' does not have the .preset extension. Do you want to upload it anyway? (y/n): ")
        if upload_anyway.lower() != 'y':
            print('Upload cancelled')
            return False

    model = hostname[:2]
    if model == 'qx':
        username = USER
        password = PASSW
        remote_dir = '/transfer/presets'
    else:
        username = LXP500_USER
        password = LXP500_PASSW
        remote_dir = '/home/sftp/leader/transfer/presets'

    try:
        file_name = preset if preset.endswith(
            '.preset') else f'{preset}.preset'
        local_path = os.path.join(os.getcwd(), file_name)
        remote_path = os.path.join(remote_dir, file_name)

        command = f'echo "{password}" | sftp -oBatchMode=no -b - {username}@{hostname} <<EOF\nput {local_path} {remote_path}\nEOF'
        result = subprocess.run(command, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            print(
                f"SFTP upload success: {local_path} to {hostname}:{remote_path}")
            return True
        else:
            print(f"SFTP upload failed with code {result.returncode}")
            print(f"Error: {result.stderr.decode()}")
            return False
    except Exception as e:
        print(f'Error: {e}')
        return False


def upload_preset_dir(preset_dir: str, hostname: str) -> bool:
    """
    Upload all preset files in a directory to a remote server using SFTP.

    :param preset_dir: Directory containing the preset files
    :param hostname: Hostname of the unit
    :return: True if successful, False otherwise
    """
    if not os.path.exists(preset_dir):
        print(f"Error: Directory '{preset_dir}' does not exist")
        return False

    model = hostname[:2]
    if model == 'qx':
        username = USER
        password = PASSW
        remote_dir = '/transfer/presets'
    else:
        username = LXP500_USER
        password = LXP500_PASSW
        remote_dir = '/home/sftp/leader/transfer/presets'

    success = True
    for file_name in os.listdir(preset_dir):
        local_path = os.path.join(preset_dir, file_name)
        if not os.path.isfile(local_path):
            continue

        command = f'echo "{password}" | sftp -oBatchMode=no -b - {username}@{hostname} <<EOF\nput {local_path} {remote_dir}\nEOF'
        result = subprocess.run(command, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            print(
                f"SFTP upload failed for {local_path} with code {result.returncode}")
            print(f"Error: {result.stderr.decode()}")
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(
        description='Load a preset file to a unit using the REST API')
    parser.add_argument('--hostname', help='Hostname of the unit')
    parser.add_argument('--preset', help='Name of the preset file to load')
    parser.add_argument(
        '-d', '--dir', help='Directory containing the preset files to upload')
    args = parser.parse_args()

    if not args.hostname and not args.preset and not args.dir:
        parser.print_help()
        sys.exit()
    if args.dir:
        success = upload_preset_dir(args.dir, args.hostname)
    elif success := sftp_upload(args.hostname, args.preset):
        success = load_preset(args.hostname, args.preset)


if __name__ == '__main__':
    main()
