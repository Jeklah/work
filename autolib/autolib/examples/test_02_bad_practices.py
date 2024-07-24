"""\
A PyTest module that does more than the previous tests but contains a number of bad practices to avoid.
"""

import time

from autolib.models.qxseries.qx import Qx
from autolib.models.qxseries.operationmode import OperationMode


def test_operation_mode_is_sdi():
    """
    Test that when a Qx is switched to SDI Stress mode and assuming SDI outs are looped to SDI ins, for each standard
    generated, the analyser reports the same values.

    Critically, this will fail on the first failure. Generally it is a better idea when looping through inputs in a
    test to use pytest.mark.parametrize to instead generate one test per standard. Otherwise the developer is
    responsible for handling the failures gracefully in a way that will make sense in jUnit test reports.
    """

    # There's a few problems here:
    # (1) String literal for hostname - unless this is always the unit you are to run the test on, this will not work.
    # (2) qx-020008.local may be a QxL - use the make_qx factory method instead.
    # (3) Use a fixture instead (more about that later)
    qx_unit = Qx('qx-020000.local')
    qx_unit.request_capability(OperationMode.SDI)

    # Use of print in tests is not prohibited, but it's important to understand when it's appropriate. Anything that's
    # print()ed will appear in the generated jUnit file for a test. It can be useful to put critical information here,
    # but it's important to use the logging class too if the information is needed in both places.
    # Also, prefer f-strings (e.g. f"This is the {value}") over string concatenation.
    print(qx_unit.hostname + " is in SDI Stress mode")

    # This is very bad. The Qx SDI generator supports well over 5,000 different standards so this will take a long time.
    # A better approach is needed, for example create a subset that matches a set of rules to select only the standards
    # that are needed by the test.
    for standard in qx_unit.generator.standards_generator():

        # The tuple we get back from the standards_generator has the data rate as the first param - slice everything
        # else into a new tuple
        new_standard = standard[1:]

        # This makes an assumption that '100% Bars' is available for all standards. It's better to choose a test pattern
        # that's available for a given standard.
        qx_unit.generator.set_generator(*new_standard, "100% Bars")

        # Whilst sometimes unavoidable, fixed pauses should be a last resort. Avoid assuming that we are ready to
        # continue, look for conditions that indicate we are. In this instance let's assume that > 5s constitutes a
        # test failure.
        time.sleep(5)

        assert qx_unit.analyser.sdi.get_analyser_status() == new_standard

