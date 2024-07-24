"""\
Hello World. Create a Qx object and discover it's software version etc. This is not a test as it doesn't do anything
with the information (although from running this we do know that the Qx is reachable and responding to REST calls).
"""

from autolib.models.qxseries.qx import Qx

test_qx = Qx('qx-020000.local')
print(test_qx.about)
