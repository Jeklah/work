import http.client

# Define the target host and endpoint
host = 'qx-022160'
port = 8080
endpoint = '/api/v1/presets/userPresets/my_preset'

# Define headers and data
headers = {
    'Content-Type': 'application/json'
}
data = '{"action": "load"}'

# Convert the data dictionary to a JSON string
# json_data = json.dumps(data)

# Create a connection to the host
conn = http.client.HTTPConnection(host, port)

try:
    # Send the PUT request
    conn.request('PUT', endpoint, body=data, headers=headers)

    # Get the response
    response = conn.getresponse()
    status = response.status
    response_data = response.read().decode()

    print(f'Status Code: {status}')
    print(f'Response Data: {response_data}')

    if response_data.startswith('{') and response_data.endswith('}'):
        print('Response data is valid JSON')
        print(f'Response JSON: {response_data}')
    # try:
    #     response_json = json.loads(response_data)
    #     print(f'Response JSON: {response_json}')
    # except json.JSONDecodeError:
    #     print('Response data is not valid JSON')
finally:
    # Close the connection
    conn.close()
