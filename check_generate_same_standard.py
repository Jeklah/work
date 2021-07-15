"""
This is a simple test to check that the Qx does not lock up upon requesting the same standard to be generated twice in a row.
"""
import time
import logging

from test_system.factory import make_qx
from test_system.logconfig import test_system_log

log = logging.getLogger(test_system_log)
hname = 'qx-020507.local'
qx = make_qx(hostname = hname)

standard_data = {
    "resolution": "2048x1080p50",
    "colour" : "YCbCr:422:10",
    "gamut" : "3G_A_Rec.709",
    "test_pattern" : "100% Bars"
}
print('Sending first generation request...')
qx.generator.set_generator('2048x1080p50', 'YCbCr:422:10', '3G_A_Rec.709', '100% Bars')

if qx.generator.is_generating_standard(standard_data["resolution"], standard_data["colour"], standard_data["gamut"], standard_data["test_pattern"]):
    print('First generation request completed.')
    print('Sending second generation request...')
    qx.generator.set_generator(standard_data["resolution"], standard_data["colour"], standard_data["gamut"], standard_data["test_pattern"])
    time.sleep(10)
    if not qx.generator.is_generating_standard(standard_data["resolution"], standard_data["colour"], standard_data["gamut"], standard_data["test_pattern"]):
        print('Second generation request failed.')
        exit()
    else:
        print('Second generation request completed.')

else:
    print('First generation attempt failed.')
    exit()

