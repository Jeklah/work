"""
Tests that validate the AES features of the Qx.

.. note:: The 2110 tests are currently disabled as AUD selection needs to be done manually as this is currently not 
          possible via API pending F1991.
          See https://phabrix.axosoft.com/viewitem?id=1991&type=feature&force_use_number=true

"""

import pytest
import logging
from typing import Generator, List, Tuple
from pprint import pformat
from autolib.factory import make_qx, Qx
from autolib.logconfig import autolib_log
from autolib.coreexception import CoreException
from autolib.testexception import TestException
from autolib.models.qxseries.operationmode import OperationMode

# Set up standard logging for autolib
log = logging.getLogger(autolib_log)

# Regex to match 400 and 415 status codes
STATUS_CODE_400_REGEX = r'(?P<precursor>.*)(status code: 400)(?P<endbit>.*)'
STATUS_CODE_415_REGEX = r'(?P<precursor>.*)(status code: 415)(?P<endbit>.*)'


def _set_get_aes_conf(generator_qx: Qx, aes_config: dict) -> dict:
    """
    Set AES configuration via REST API and then retrieve what configuration has been set.

    param: generator object
    param: aes_config json object

    returns: aes_config json object
    """
    generator_qx.aesio.set_aes_config(aes_config)
    return generator_qx.aesio.get_aes_config()


@pytest.fixture(scope="module")
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Create generator Qx object. Tears down configuration after test.

    param: test_generator_hostname string
    returns: qx object
    """
    gen_qx = make_qx(test_generator_hostname)
    log.info(f"FIXTURE: Qx {test_generator_hostname} generator setup complete.")
    log.info("Testing AES REST API configuration.")
    yield gen_qx

    # Turn off AES outputs after test
    aes_config = {f"aes{str(index)}": {"mode": "off"} for index in list(range(1, 5))}
    gen_qx.aesio.set_aes_config(aes_config)
    log.info(f"FIXTURE: QX {test_generator_hostname} AES outputs have been turned off.")
    log.info(f"FIXTURE: Qx {test_generator_hostname} generator teardown complete.")


@pytest.fixture(scope="module")
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Create analyser Qx object. Tears down configuration after test.

    param: test_analyser_hostname string
    returns: qx object
    """
    analyser_qx = make_qx(test_analyser_hostname)
    log.info(f"FIXTURE: Qx {test_analyser_hostname} analyser setup complete.")
    yield analyser_qx
    log.info("Testing AES REST API complete.")
    log.info(f"FIXTURE: Qx {test_analyser_hostname} analyser teardown complete.")


def generator_aes_2110():
    """
    Yield all combinations of AES output, channel pairs and AUD audio flows.

    returns: aes_config list
    """
    aes_list = list(range(1, 5))
    aes_ch = list(range(1, 17, 2))
    aud_flow = [1, 2]

    for aes in aes_list:
        for ch in aes_ch:
            for aud in aud_flow:
                yield aes, ch, aud


def generator_aes_2110_formatter(args):
    """Format test IDs for parameters supplied by generator_aes_2110()."""
    aes, ch, aud = args
    return f"AES{aes}-Channel{ch}-{ch+1}-AUD{aud}"


@pytest.mark.skip('Requires ticket f1991. Currently requires manual configuration.')
@pytest.mark.ip2110
@pytest.mark.parametrize("aes_2110_config", generator_aes_2110(), ids=generator_aes_2110_formatter)
def test_2110_aes_output(aes_2110_config: list, generator_qx: Qx, analyser_qx: Qx):
    """
    Validates that AES outputs can be selected correctly in 2110 mode.

    param: aes_2110_config list
    param: generator_qx qx object
    param: analyser_qx qx object
    """
    generator_qx.request_capability(OperationMode.IP_2110)
    analyser_qx.request_capability(OperationMode.IP_2110)

    aes, channel, aud = aes_2110_config
    aes_index = f"aes{str(aes)}"
    aud_index = f"AUD{str(aud)}"
    aes_out_data = {
        aes_index: {
            "mode": "transmit",
            "transmitSource": "analyser",
            "flow": aud_index,
            "leftChannel": channel,
            "rightChannel": channel + 1
        }
    }

    aes_2110_outputs = _set_get_aes_conf(generator_qx, aes_out_data)

    try:
        assert aes_2110_outputs[aes_index]["mode"] == "transmit"
    except KeyError as err:
        raise TestException(f"TestException occurred: {err}.\nInfo: aes_2110_output is:\n{pformat(aes_2110_outputs)}")  # Added more specific error information.


@pytest.mark.skip('Requires ticket f1991. Currently requires manual configuration.')
@pytest.mark.ip2110
@pytest.mark.parametrize("aes_2110_config", generator_aes_2110(), ids=generator_aes_2110_formatter)
def test_2110_aud_flow(aes_2110_config: list, generator_qx: Qx, analyser_qx: Qx):
    """
    Validates that AUD audio flows can be selected correctly in 2110 mode.

    param: aes_2110_config list
    param: generator_qx qx object
    param: analyser_qx qx object
    """
    generator_qx.request_capability(OperationMode.IP_2110)
    analyser_qx.request_capability(OperationMode.IP_2110)

    aes, channel, aud = aes_2110_config
    aes_index = f'aes{str(aes)}'
    aud_index = f'AUD{str(aud)}'
    aes_flow_data = {
        aes_index: {
            "mode": "transmit",
            "transmitSource": "analyser",
            "flow": aud_index,
            "leftChannel": channel,
            "rightChannel": channel + 1
        }
    }

    aes_2110_flow = _set_get_aes_conf(generator_qx, aes_flow_data)

    try:
        assert aes_2110_flow[aes_index]["flow"] == aud_index
    except KeyError as err:
        raise TestException(f"TestException occurred: {err}.\nInfo: aes_2110_flow is:\n{pformat(aes_2110_flow)}")


@pytest.mark.skip('Requires ticket f1991. Currently requires manual configuration.')
@pytest.mark.ip2110
@pytest.mark.parametrize("aes_2110_config", generator_aes_2110(), ids=generator_aes_2110_formatter)
def test_2110_channels(aes_2110_config: list, generator_qx: Qx, analyser_qx: Qx):
    """
    Validates that correct pairs of channels can be selected in 2110 mode.

    param: aes_2110_config list
    param: generator_qx qx object
    param: analyser_qx qx object
    """
    generator_qx.request_capability(OperationMode.IP_2110)
    analyser_qx.request_capability(OperationMode.IP_2110)

    aes, channel, aud = aes_2110_config
    aes_index = f"aes{str(aes)}"
    aud_index = f"AUD{str(aud)}"
    aes_ch_data = {
        aes_index: {
            "mode": "transmit",
            "transmitSource": "analyser",
            "flow": aud_index,
            "leftChannel": channel,
            "rightChannel": channel + 1
        }
    }

    aes_2110_channels = _set_get_aes_conf(generator_qx, aes_ch_data)

    try:
        assert aes_2110_channels["leftChannel"] == channel
        assert aes_2110_channels["rightChannel"] == channel + 1
    except KeyError as err:
        raise TestException(f"TestException has occurred: {err}.\nInfo: aes_2110_channels is:\n{pformat(aes_2110_channels)}")


def _generator_aes():
    """
    Yield all combinations of aes output, groups and pairs for aes.

    returns: aes_config list
    """
    aes_list = list(range(1, 5))
    pairs = list(range(1, 3))
    groups = list(range(1, 9))

    for aes in aes_list:
        for pair in pairs:
            for group in groups:
                yield pair, aes, group


def _generator_aes_formatter(args):
    """Format test IDs for parameters supplied by generator_aes()."""
    pair, aes, group = args
    return f"AES{aes}-Group{group}-Pair{pair}"


@pytest.mark.sdi
@pytest.mark.parametrize("aes_config", _generator_aes(), ids=_generator_aes_formatter)
def test_aes_sdi(aes_config: dict, generator_qx: Qx):
    """
    [Happy] Tests AES channel, pairs and groups are set correctly in SDI mode.

    param: aes_config json object
    param: generator_qx qx object
    """
    generator_qx.request_capability(OperationMode.SDI)
    generator_qx.block_until_ready()
    _test_aes(aes_config, generator_qx)


@pytest.mark.ip2022_6
@pytest.mark.parametrize("aes_config", _generator_aes(), ids=_generator_aes_formatter)
def test_aes_2022_6(aes_config: dict, generator_qx: Qx):
    """
    [Happy] Tests AES channel, pairs and groups are set correctly in 2022-6 mode.

    param: aes_config json object
    param: generator_qx qx object
    """
    generator_qx.request_capability(OperationMode.IP_2022_6)
    generator_qx.block_until_ready()
    _test_aes(aes_config, generator_qx)


def _sad_aes_generator() -> Generator[Tuple[int, int, int], None, None]:
    """
    [Sad] Yield all combinations of aes output, groups and pairs for aes. Includes invalid settings.

    returns: aes_config tuple
    """
    sad_aes = [0, 5, -1]
    pairs = list(range(1, 3))
    groups = list(range(1, 9))

    for aes in sad_aes:
        for pair in pairs:
            for group in groups:
                yield pair, aes, group


def _bad_aes_generator() -> Generator[Tuple[int, int, int], None, None]:
    """
    [Bad] Yield all combinations of aes output, groups and pairs for aes. Includes invalid settings.

    returns: aes_config tuple
    """
    # Tuples of (pair, aes, group) inputs with invalid settings
    tests = (
        (1, 0, 1),  # Bad AES channel
        (1, 5, 1),  # Bad AES channel
        (1, -1, 1),   # Bad AES channel
        (0, 1, 1),  # Bad pair
        (3, 1, 1),  # Bad pair
        (-1, 1, 1),  # Bad pair
        (1, 1, 0),  # Bad group
        (1, 1, 9),  # Bad group
        (1, 1, -1),  # Bad group
        (999, 999, 999),  # All invalid
    )

    for test in tests:
        yield test[0], test[1], test[2]


@pytest.mark.sdi
@pytest.mark.parametrize("aes_config", _sad_aes_generator(), ids=_generator_aes_formatter)
def test_aes_sdi_sad_inputs(aes_config: dict, generator_qx: Qx):
    """
    [Sad] Tests AES channel, pairs and groups are set correctly in SDI mode.

    param: aes_config json object
    param: generator_qx qx object
    """
    generator_qx.request_capability(OperationMode.SDI)
    generator_qx.block_until_ready()
    with pytest.raises(CoreException, match=STATUS_CODE_400_REGEX):
        _test_aes(aes_config, generator_qx)


@pytest.mark.ip2022_6
@pytest.mark.parametrize("aes_config", _sad_aes_generator(), ids=_generator_aes_formatter)
def test_aes_2022_6_sad_inputs(aes_config: dict, generator_qx: Qx):
    """
    [Sad] Tests AES channel, pairs and groups are set correctly in 2022-6 mode. w

    param: aes_config json object
    param: generator_qx qx objectq
    """
    generator_qx.request_capability(OperationMode.IP_2022_6)
    generator_qx.block_until_ready()
    with pytest.raises(CoreException, match=STATUS_CODE_400_REGEX):
        _test_aes(aes_config, generator_qx)


def _test_aes(aes_config: dict, generator_qx: Qx):
    """
    Perform the work for the tests for AES in SDI and 2022-06 modes.

    param: aes_config aes_config json object
    param: generator_qx qx object
    """
    pair, aes, group = aes_config
    aes_index = f'aes{str(aes)}'
    aes_input_data = {
        aes_index: {
            "group": group,
            "mode": "transmit",
            "pair": pair,
            "transmitSource": "generator"
        }
    }
    read_aes_config = _set_get_aes_conf(generator_qx, aes_input_data)
    try:
        assert read_aes_config[aes_index]['mode'] == 'transmit'
        assert read_aes_config[aes_index]['pair'] == pair
        assert read_aes_config[aes_index]['group'] == group
    except KeyError as err:
        raise TestException(f"TestException occurred: {err}.\nInfo: read_aes_config is:\n{pformat(read_aes_config)}")


@pytest.mark.sdi
def test_aes_sdi_bad_format(generator_qx: Qx):
    """
    [Bad] Tests AES channel, pairs and groups are set correctly in SDI mode.

    param: generator_qx qx object
    """
    generator_qx.request_capability(OperationMode.SDI)
    generator_qx.block_until_ready()
    _test_aes_bad(generator_qx)


@pytest.mark.sdi
@pytest.mark.parametrize("bad_aes_config", _bad_aes_generator(), ids=_generator_aes_formatter)
def test_aes_sdi_bad_inputs(generator_qx: Qx, bad_aes_config: dict):
    """
    [Bad] Tests AES channel, pairs and groups are set correctly in SDI mode.

    param: generator_qx qx object
    param: bad_aes_config json object
    """
    generator_qx.request_capability(OperationMode.SDI)
    generator_qx.block_until_ready()
    with pytest.raises(CoreException, match=STATUS_CODE_400_REGEX):
        _test_aes(bad_aes_config, generator_qx)


@pytest.mark.ip2022_6
@pytest.mark.parametrize("bad_aes_config", _bad_aes_generator(), ids=_generator_aes_formatter)
def test_aes_2022_6_bad_inputs(generator_qx: Qx, bad_aes_config: dict):
    """
    [Bad] Tests AES channel, pairs and groups are set correctly in 2022-6 mode.

    param: generator_qx qx object
    param: bad_aes_config json object
    """
    generator_qx.request_capability(OperationMode.IP_2022_6)
    generator_qx.block_until_ready()
    with pytest.raises(CoreException, match=STATUS_CODE_400_REGEX):
        _test_aes(bad_aes_config, generator_qx)


@pytest.mark.ip2022_6
def test_aes_2022_6_bad_format(generator_qx: Qx):
    """
    [Bad] Tests AES channel, pairs and groups are set correctly in 2022-6 mode.

    param: generator_qx qx object
    """
    generator_qx.request_capability(OperationMode.IP_2022_6)
    generator_qx.block_until_ready()
    _test_aes_bad(generator_qx)


def _test_aes_bad(generator_qx: Qx):
    """
    [Bad] Generates bad data to be sent for bad input tests.

    Send unexpected data to the AES config PUT API method. The Qx object exposes it's URL base through the
    path member. Use this to send non-schema compliant JSON and XML to the aesIO/config path using a PUT request.
    """
    with pytest.raises(CoreException) as exc:
        generator_qx.aesio.aes_io_config = {
        "some": "completely",
        "unexpected": "data",
        "in": ["A", "form that the API", "should reject"],
        "some_value": 123
    }

        response = exc.value.args[0].get("response", None)
        assert response is not None
        assert response.status_code == 400  # Should return Bad Request client error status
    
        generator_qx.aesio.aes_io_config = {
     """\
        <?xml version="1.0" encoding="UTF-8" ?>
        <root>
          <some>completely</some>
          <unexpected>data</unexpected>
          <in>A</in>
          <in>form that the API</in>
          <in>should reject</in>
          <some_value>123</some_value>
        </root>
    """
    }

        response = exc.value.args[0].get("response", None)
        assert response is not None
        assert response.status_code == 415  # Should return Unsupported Media Type client error status

        generator_qx.aesio.aes_io_config = {
           b"VGhpcyBpcyBhIHJlYWxseSBsb25nIHN0cmluZyBvZiBhYnNvbHV0ZSBnYXJiYWdlIG1hc3F1ZXJhZGluZyBhcyBKU09OIGluIGEgYm"\
           b"FkIGh0dHAgUFVUIHJlcXVlc3QuIFRoaXMgc2hvdWxkIGJlIHJlamVjdGVkIHdpdGhvdXQgbGVhdmluZyB0aGUgdW5pdCBpbiBhIGJh"\
           b"ZCBzdGF0ZS4gSXQgc2hvdWxkIGNlcnRhaW5seSBub3QgbGVhdmUgdGhlIHVuaXQgaW4gYW4gdW5yZWNvdmVyYWJsZSBzdGF0ZS4gSS"\
           b"B3b25kZXIgaWYgYW55b25lIHdpbGwgdHdpZyB0aGF0IHRoaXMgaXMgQkFTRTY0IGVuY29kZWQ/IElmIHRoZXJlJ3MgYSB0cmFpbGlu"\
           b"ZyAnPScgaXQgbWF5IGJlIGEgZ2l2ZWF3YXkgOik="
    }

        response = exc.value.args[0].get("response", None)
        assert response is not None
        assert response.status_code == 415  # Should return Unsupported Media Type client error status
