import os 
import tempfile
import paramiko

def main():
	temp = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
	with open(temp.name, 'w') as writer:
		writer.write('test')

	print(f'temp file has been made: {temp.name}')

	with open(temp.name, 'r') as reader:
		content = reader.readlines()

	print(content)

	ssh_client = paramiko.SSHClient()
	ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	ssh_client.connect('qx-020020.phabrix.local', port=22, username='root', password='PragmaticPhantastic')
	if ssh_client.get_transport() is not None:
		ssh_client.get_transport().is_active()
		print(f'connection is active')
		ftp_client = ssh_client.open_sftp()
		
	if os.path.isfile(temp.name):
		print(f'transferring temp file: {temp.name}')
		ftp_client.put(temp.name, '/home/transfer/tmp.txt', confirm=True)
	else:
		raise IOError(f'Could not find local file. {temp.name}')
		
	#ssh_client.close()		

if __name__ == '__main__':
	main()