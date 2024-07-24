"""\
Our first PyTest test module. This contains one PyTest-discoverable function which (again) creates a Qx object and
prints it's details to stdout which will be captured by PyTest. The test clearly defines it's purpose.
"""

from pprint import pprint
from autolib.models.qxseries.qx import Qx


def test_about():
    """\
    Test that a Qx / Qxl is running and responding to REST calls.
    """
    qx = Qx('qx-020000.local')
    pprint(qx.about)
