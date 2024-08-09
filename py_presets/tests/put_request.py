import requests
import json

# Define the URL
url = 'http://qx-022160:8080/api/v1/presets/userPresets/my_preset'
headers = {"Content-Type": "application/json"}
data = {"action": "load"}

# Make the PUT request
try:
    response = requests.put(url, headers=headers,
                            data=json.dumps(data), verify=False)
    # response = requests.put(url, headers=headers, json=data, verify=False)

    # Print the response
    print(f'Status code: {response.status_code}')
    print(f'Response Text: {response.text}')
    print(f'Response JSON: {response.json()}')
    if response.status_code == 200:
        print("Response JSON:", response.json())
except requests.exceptions.RequestException as e:
    print(f'Error: {e}')
