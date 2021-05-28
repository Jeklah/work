"""
Small test app to test the behaviour of temporary named files.
"""
import os
import tempfile
import paramiko

def main():
    tempFile = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    localpath = os.path.abspath(str(tempFile.name))
    print('temp file made: ' + localpath)

    ssh_client=paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect('localhost', password='', username='')
    print('connection made to qx: ' + str(ssh_client))

    ftp_client = ssh_client.open_sftp()
    print('ftp client made.' + str(ftp_client))
    #tempFile.close()
    print(f'transferring {tempFile.name}')
    ftp_client.put(localpath, f'/transfer/presets/{tempFile.name}')
    #tempFile.close()

if __name__ == '__main__':
    main()
