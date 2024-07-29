import argparse
import paramiko
import os


USER: str = 'qxuser'
PASSW: str = 'phabrixqx'
LXP500_USER: str = 'root'  # 'leader'
LXP500_PASS: str = 'PragmaticPhantastic'  # 'PictureWFMAnalyze'


def transport_connect(hostname: str, user: str, password: str) -> paramiko.Transport:
    """
    Create a transport object and connect to the remote server.

    :param hostname: Hostname of the remote server
    :param user: Username for the connection
    :param password: Password for the connection
    """
    transport = paramiko.Transport((hostname, 22))
    transport.connect(username=user, password=password)
    return transport


def sftp_connect(hostname: str, preset: str, unit_type: str) -> bool:
    """
    Upload a preset file using SFTP.

    :param hostnamename: Hostname of the remote server
    :param preset: Name of the preset file to upload
    :param unit_type: Type of the unit (qx or lpx500)
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
        return sftp_upload(hostname, preset, unit_type)
    except paramiko.AuthenticationException:
        print("SFTP Authentication failed")
        return False
    except Exception as error:
        print(f"An SFTP error occurred: : {error}")
        return False


def sftp_upload(hostname: str, preset: str, unit_type: str) -> bool:
    """
    Connect to the remote server using SFTP.

    :param hostname: Hostname of the remote server
    :param preset: Name of the preset file to upload
    :param unit_type: Type of the unit (qx or lpx500)
    """
    if unit_type == 'lpx500':
        transport = transport_connect(hostname, LXP500_USER, LXP500_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)
        #  'leader/transfer/presets' is the path for the leader user on the LPX500
        sftp.chdir('/home/sftp/leader/transfer/presets')  # type: ignore
    elif unit_type == 'qx':
        transport = transport_connect(hostname, USER, PASSW)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.chdir('transfer/presets')  # type: ignore
    else:
        print("Error: Invalid unit type")
        return False
    file_name = preset if preset.endswith('.preset') else f'{preset}.preset'
    remote_path = f'transfer/presets/{file_name}'
    local_path = os.path.join(os.getcwd(), file_name)
    sftp.put(localpath=local_path, remotepath=file_name)  # type: ignore
    sftp.close()  # type: ignore
    transport.close()
    print(
        f"SFTP upload success: {local_path} to {hostname}:{remote_path} 1")
    return True


def upload_preset_dir(preset_dir: str, hostname: str) -> bool:
    """
    Upload all preset files in a directory to a remote server.

    :param preset_dir: Name of the directory containing the preset files
    :param hostname: Hostname of the remote server
    """
    if not os.path.exists(preset_dir):
        print(f"Error: Directory '{preset_dir}' not found")
        return False

    os.chdir(preset_dir)
    for file_name in os.listdir(os.getcwd()):
        # if not file_name.endswith('.preset'):
        # continue
        cwd = os.getcwd()
        local_path = os.path.join(cwd, file_name)
        if not os.path.exists(local_path):
            print(f"Error: File '{file_name}' not found")
            return False

        # SFTP connection details
        try:
            if not sftp_connect(hostname, file_name, 'qx'):
                print("Could not connect using QxL credentials. Assuming Leader LPX500")
                if not sftp_connect(hostname, file_name, 'lpx500'):
                    print(f"Error: Upload failed for file '{file_name}'")
                    return False
        except Exception as error:
            print(f"An error occurred: {error}")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Upload a file via SFTP and failback to SCP on authentication failure')
    parser.add_argument('--hostname', type=str,
                        help='hostname of the remote server')
    parser.add_argument('--preset', type=str,
                        help='Name of the preset file to upload')
    parser.add_argument('--unit-type', type=str, choices=['qx', 'lpx500'], required=True,
                        help='Type of the unit (qx or lpx500)')
    parser.add_argument('--presetdir', type=str,
                        help='Name of the directory containing preset files to upload')
    args = parser.parse_args()

    if not args.preset and not args.presetdir:
        print("Error: Please provide a preset name or directory")
    elif args.preset:
        if args.unit_type == 'qx':
            sftp_connect(args.hostname, args.preset, 'qx')
        else:
            sftp_connect(args.hostname, args.preset, 'lpx500')
    else:
        upload_preset_dir(args.presetdir, args.hostname)


if __name__ == '__main__':
    main()
