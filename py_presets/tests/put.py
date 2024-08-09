import subprocess

# Define the command to be run
command = ['curl',
           '-X',
           'PUT',
           '-H',
           'Content-Type: application/json',
           '-d',
           '{"action": "load"}',
           'http://qx-022160:8080/api/v1/presets/userPresets/my_preset']

subprocess.call(command)
