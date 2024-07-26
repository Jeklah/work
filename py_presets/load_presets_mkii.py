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


def sftp_upload(hostnamename: str, preset_name: str, unit_type: str) -> bool:
    """
    Upload a preset file using SFTP.

    :param hostnamename: Hostname of the remote server
    :param preset_name: Name of the preset file to upload
    :param unit_type: Type of the unit (qx or lpx500)
    """

    # File details
    file_name: str = f'{preset_name}.preset'
    local_path: str = os.path.join(os.getcwd(), file_name)

    # Check if the file exists
    if not os.path.exists(local_path):
        print(f"Error: File '{file_name}' not found")
        return False

    # SFTP connection details
    hostname = f'{hostnamename}'
    try:
        return sftp_connect(hostname, preset_name, unit_type)
    except paramiko.AuthenticationException:
        print("SFTP Authentication failed")
        return False
    except Exception as error:
        print(f"An SFTP error occurred: : {error}")
        return False


def sftp_connect(hostname: str, preset_name: str, unit_type: str) -> bool:
    """
    Connect to the remote server using SFTP.

    :param hostname: Hostname of the remote server
    :param preset_name: Name of the preset file to upload
    :param unit_type: Type of the unit (qx or lpx500)
    """
    if unit_type == 'qx':
        transport = transport_connect(hostname, USER, PASSW)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.chdir('transfer/presets')  # type: ignore
    elif unit_type == 'lpx500':
        transport = transport_connect(hostname, LXP500_USER, LXP500_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)
        #  'leader/transfer/presets' is the path for the leader user on the LPX500
        sftp.chdir('/home/sftp/leader/transfer/presets')  # type: ignore
    else:
        print("Error: Invalid unit type")
        return False
    file_name = f'{preset_name}.preset'
    remote_path = f'transfer/presets/{file_name}'
    local_path = os.path.join(os.getcwd(), file_name)
    sftp.put(localpath=local_path, remotepath=file_name)  # type: ignore
    sftp.close()  # type: ignore
    transport.close()
    print(
        f"SFTP upload success: {local_path} to {hostname}:{remote_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Upload a file via SFTP and failback to SCP on authentication failure')
    parser.add_argument('hostnamename', type=str,
                        help='hostnamename of the remote server')
    parser.add_argument('preset_name', type=str,
                        help='Name of the preset file to upload')
    parser.add_argument('unit_type', type=str, choices=['qx', 'lpx500'],
                        help='Type of the unit (qx or lpx500)')
    args = parser.parse_args()

    if not sftp_upload(args.hostnamename, args.preset_name, 'qx'):
        print("Could not connect using usual credentials. Assuming Leader LPX500")
        sftp_upload(args.hostnamename, args.preset_name, 'lpx500')


if __name__ == '__main__':
    main()
