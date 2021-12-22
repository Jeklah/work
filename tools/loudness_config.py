import requests
import json

url = "http://qx-020507.local:8080/api/v1/analyser/loudness/config"
headers = {
    'Content-Type': 'application/json'
}

payload = json.dumps({
    "audioAssignment": {
        ## 5.1 Configuration for Loudness
        # "audioMode": "5.1",
        # "channelAssignment": {
        #     "centre": {
        #         "channel": "group1Pair2Left",
        #         "subimage": 1
        #     },
        #     "left": {
        #         "channel": "group1Pair1Left",
        #         "subimage": 1
        #     },
        #     "leftSurround": {
        #         "channel": "group2Pair1Left",
        #         "subimage": 1
        #     },
        #     "lfe": {
        #         "channel": "group1Pair2Right",
        #         "subimage": 1
        #     },
        #     "right": {
        #         "channel": "group1Pair1Right",
        #         "subimage": 1
        #     },
        #     "rightSurround": {
        #         "channel": "group2Pair1Right",
        #         "subimage": 1
        #     }
        # }

        ## Stereo Configuration for Loudness

        "audioMode": "stereo",
        "channelAssignment": {
            "left": {
                "channel": "group1Pair1Left",
                "subimage": 1
            },
            "right": {
                "channel": "group1Pair1Right",
                "subimage": 1
            }
        }
    },
    "control": "start",
    "logDuration_mins": 30,
    "logFilename": "loudness",
    "logLifetime_days": 7,
    "message": "",
    "meterTarget": {
        "integrated": -23,
        "momentary": -23,
        "shortTerm":-23
    },
    "meterTolerance": {
        "integrated": 0.5,
        "momentary": 0.5,
        "shortTerm": 0.5
    },
    "standard": "ebuLufs",
    "truePeakAlarm": 0
})

response = requests.request('PUT', url, headers=headers, data=payload)

print(response.text)
