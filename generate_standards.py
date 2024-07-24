import requests
import json
import getopt
import sys
# Script: generate_standards.py
# Description: This script is used to generate a subset of standards for basic
#              generator testing. The script will issue generate commands
#              to the PHABRIX QX generator API.
# Author: Arthur Bowers
# Company: PHABRIX Ltd.

BG_PASS = '\x1b[2;30;42m'
BG_FAIL = '\x1b[2;30;41m'
BG_RESET = '\x1b[0m'
BASE_URL = 'http://qx-022160.local:8080/api/v1/generator/standards/'
HEADERS = {'Content-Type': 'application/json'}
data = {'action': 'start'}
try:
    opts, args = getopt.getopt(sys.argv[1:], 'h', ['help'])
    unit = args[0]
    base_url = f'http://{unit}.local:8080/api/v1/generator/standards/'
except getopt.GetoptError:
    print('error')
    sys.exit(2)
check_standards = [
    # HD SDI format
    '1280x720p30/YCbCrA%3A4444%3A10/3G_A_Rec.709/100%25%20Bars',
    '1920x1080i50/YCbCr%3A444%3A10/3G_A_Rec.709/100%25%20Bars'   '1920x1080psf23.98/YCbCr%3A444%3A10/3G_A_Rec.709/100%25%20Bars',
    '1920x1080p60/YCbCr%3A422%3A10/3G_A_Rec.709/100%25%20Bars',

    # 3G-A SDI Standard Format
    '1920x1080p29.97/YCbCr%3A422%3A12/3G_A_Rec.709/100%25%20Bars',

    # 3G-B SDI Standard Format
    '1920x1080i50/YCbCr%3A444%3A10/3G_B_Rec.709/100%25%20Bars',

    # Dual Link SDI Standard Format
    '4096x2160p30/YCbCr%3A422%3A10FR/DL_3G_B_2-SI_Rec.709/100%25%20Bars',

    # Quad Link SDI Standard Format
    # 12G 4K SI (YCbCr-422-10) 50p
    '4096x2160p60/YCbCr%3A422%3A10FR/QL_3G_B_2-SI_Rec.709/100%25%20Bars',

    # DL HD 1080p YCbCr-422-12@25p
    '1920x1080p25/YCbCr%3A422%3A12FR/DL_1.5G_Rec.709/100%25%20Bars',

    # DL HD 1080p YCbCr-422-10@50p
    '1920x1080p50/YCbCr%3A422%3A10FR/DL_1.5G_Rec.2020/100%25%20Bars',

    # 4K DL-3GB SI (YCbCr-422-10) 25p
    # 6G-B 4K SI (YCbCr-422-10) 25p
    '4096x2160p25/YCbCr%3A422%3A10FR/DL_3G_B_2-SI_Rec.709/100%25%20Bars',

    # DL 6G-A 4K SI (YCbCr-422-10) 50p
    '4096x2160p50/YCbCr%3A422%3A10FR/DL_6G_2-SI_Rec.709/100%25%20Bars',

    # 6G-A 4K SI (YCbCr-422-10) 25p
    '4096x2160p25/YCbCr%3A422%3A10FR/6G_2-SI_Rec.709/100%25%20Bars',
]

for standard in check_standards:
    response = requests.put(
        BASE_URL + standard, headers=HEADERS, data=json.dumps(data))
    if response.status_code == 200:
        print(f"Generating: {BASE_URL + standard}.")
        print(f"Status: {response.status_code}")
        print(f"Test Result: {BG_PASS}PASS{BG_RESET}")
    else:
        print(f"Failed to generate: {BASE_URL + standard}.")
        print(f"Status: {response.status_code}")
        print(f"Test Result: {BG_FAIL}FAIL{BG_RESET}")
