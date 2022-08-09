"""\
Tests to validate configuration of the loudness controls.
"""
import time
import pytest
import logging
from typing import Generator
from test_system.factory import make_qx, Qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode


# Set up logging for test_system
log = logging.getLogger(test_system_log)


def make_SDI_unit(host: str) -> Qx:
    """
    Abstraction function for creating Qx object that supports SDI,
    depending on licences.

    :param host: Hostname of test unit.
    :return: Qx object that supports SDI.
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates Qx generator object using test_generator_hostname env var.

    :param test_generator_hostname: string
    :return: Generator object to be used with Qx object for generators.
    """
    generator_qx = make_SDI_unit(test_generator_hostname)
    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f'FIXTURE: Qx {generator_qx.hostname} setup complete')
    yield generator_qx
    log.info(f'FIXTURE: Qx {generator_qx.hostname} teardown complete.')


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx object and configures it to be used as the analyser.

    :param test_analyser_hostname: string
    :return: Generator object to be used with Qx object for analysers.
    """
    analyser_qx = make_SDI_unit(test_analyser_hostname)
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} setup complete')
    yield analyser_qx
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} teardown complete')


def generate_channel_name() -> Generator[str, None, None]:
    """
    Yields possible valid values for channel name to enumerate though.

    :yield: Valid value for channel names.
    """
    yield from ['centre', 'left', 'leftSurround', 'lfe', 'right', 'rightSurround']


def generate_5_1_channel_stream() -> Generator[list, None, None]:
    """
    Yields possible valid values for the channel stream to enumerate through.

    :yield: A list containing all the possible values that a channel stream can be set to in a 5.1 setup.
    """
    channel_stream_values = [
        'group1Pair1Left',
        'group1Pair1Right',
        'group1Pair2Left',
        'group1Pair2Right',
        'group2Pair1Left',
        'group2Pair1Right',
        'group2Pair2Left',
        'group2Pair2Right',
        'group3Pair1Left',
        'group3Pair1Right',
        'group3Pair2Left',
        'group3Pair2Right',
        'group4Pair1Left',
        'group4Pair1Right',
        'group4Pair2Left',
        'group4Pair2Right',
        'group5Pair1Left',
        'group5Pair1Right',
        'group5Pair2Left',
        'group5Pair2Right',
        'group6Pair1Left',
        'group6Pair1Right',
        'group6Pair2Left',
        'group6Pair2Right',
        'group7Pair1Left',
        'group7Pair1Right',
        'group7Pair2Left',
        'group7Pair2Right',
        'group8Pair1Left',
        'group8Pair1Right',
        'group8Pair2Left',
        'group8Pair2Right',
    ]
    stream_conf = []
    for i in range(len(channel_stream_values)):
        stream_conf = channel_stream_values[i:i + 6:]
        if len(stream_conf) < 6:
            print('5.1 length too short')
            print(stream_conf)
            break
        else:
            yield stream_conf
        stream_conf = []


def generate_stereo_channel_stream() -> Generator[list, None, None]:
    """
    Yields possible valid values for the channel stream to enumerate through.

    :yield: A list of all possible valid values for channel stream for Stereo setup.
    """
    channel_stream_values = [
        'group1Pair1Left',
        'group1Pair1Right',
        'group1Pair2Left',
        'group1Pair2Right',
        'group2Pair1Left',
        'group2Pair1Right',
        'group2Pair2Left',
        'group2Pair2Right',
        'group3Pair1Left',
        'group3Pair1Right',
        'group3Pair2Left',
        'group3Pair2Right',
        'group4Pair1Left',
        'group4Pair1Right',
        'group4Pair2Left',
        'group4Pair2Right',
        'group5Pair1Left',
        'group5Pair1Right',
        'group5Pair2Left',
        'group5Pair2Right',
        'group6Pair1Left',
        'group6Pair1Right',
        'group6Pair2Left',
        'group6Pair2Right',
        'group7Pair1Left',
        'group7Pair1Right',
        'group7Pair2Left',
        'group7Pair2Right',
        'group8Pair1Left',
        'group8Pair1Right',
        'group8Pair2Left',
        'group8Pair2Right',
    ]
    stream_conf = []
    for i in range(len(channel_stream_values)):
        stream_conf = channel_stream_values[i:i + 2:]
        if len(stream_conf) < 2:
            print('stereo length too short')
            print(stream_conf)
            break
        else:
            yield stream_conf
        stream_conf = []


def generate_subimage_index() -> Generator[int, None, None]:
    """
    Yields all possible valid entries for subimage index.

    :yield: A generator that will provide valid values for the subimage index.
    """
    yield from [1, 2, 3, 4]


def _generator_5_1_channel_stream_formatter(args: list) -> str:
    """
    Format test IDs for test_5_1_channel_stream.

    :param: Arguments to be fed into test_5_1_channel_stream.
    """
    # to be discussed in MR:
    # I've left this arguably pointless statement because I feel it gives the code more readability.
    # args being passed to a bunch of stuff and then having it returned without really saying what it
    # is or should be feels very arbitrary, so I would prefer to name it accordingly, at the cost of 1 line of code.
    # If this is deemed unecessary/args is acceptable readability, I don't mind taking it out, although would rather
    # keep arbitrary code to a minimum.
    # Same goes for similar code in the below methods.
    channel_stream = args
    return f'5.1 Channel Stream: {channel_stream}'


def _generator_stereo_channel_stream_formatter(args: list) -> str:
    """
    Format test IDs for test_stereo_channel_stream.

    :param: list containing values to be fed into test_stereo_channel_stream.
    """
    stereo_channel_stream = args
    return f'Stereo Channel Stream: {stereo_channel_stream}'


def _generator_subimage_index_formatter(args: int) -> str:
    """
    Format test IDs for the subimage_index parameter for tests.

    :param: Integer representing the index of the subimage to be used.
    """
    subimage_index = args
    return f'Subimage: {subimage_index}'


@pytest.mark.parametrize('subimage_index', generate_subimage_index(), ids=_generator_subimage_index_formatter)
@pytest.mark.parametrize('channel_5_1_stream_val', generate_5_1_channel_stream(), ids=_generator_5_1_channel_stream_formatter)
def test_5_1_channel_stream(analyser_qx: Qx, channel_5_1_stream_val: list, subimage_index: int) -> None:
    """
    Set the channel settings for audio assignment for loudness monitor.

    :param channel_name_val: str
    :param channel_stream_val: list that stores valid values for the channel stream for 5.1
    :param subimage_index: int. Value used to identify subimages.
    """
    if analyser_qx.analyser.loudness_config['audioAssignment']['audioMode'] == 'stereo':
        tmp_conf = analyser_qx.analyser.loudness_config
        tmp_conf['audioAssignment']['audioMode'] = '5.1'
        analyser_qx.analyser.loudness_config = tmp_conf

    else:
        expected_result = {'audioAssignment': {
                           'audioMode': '5.1',
                           'channelAssignment': {
                               'centre': {
                                   'channel': channel_5_1_stream_val[0],
                                   'subimage': subimage_index,
                               },
                               'left': {
                                   'channel': channel_5_1_stream_val[1],
                                   'subimage': subimage_index,
                               },
                               'leftSurround': {
                                   'channel': channel_5_1_stream_val[2],
                                   'subimage': subimage_index,
                               },
                               'lfe': {
                                   'channel': channel_5_1_stream_val[3],
                                   'subimage': subimage_index,
                               },
                               'right': {
                                   'channel': channel_5_1_stream_val[4],
                                   'subimage': subimage_index,
                               },
                               'rightSurround': {
                                   'channel': channel_5_1_stream_val[5],
                                   'subimage': subimage_index,
                               }
                           }}}

        analyser_qx.analyser.loudness_config = expected_result
        conf = analyser_qx.analyser.loudness_config['audioAssignment']
        time.sleep(0.5)
        assert conf == expected_result['audioAssignment']


@pytest.mark.parametrize('subimage_index', generate_subimage_index(), ids=_generator_subimage_index_formatter)
@pytest.mark.parametrize('channel_stereo_stream_val', generate_stereo_channel_stream(), ids=_generator_stereo_channel_stream_formatter)
def test_stereo_channel_stream(analyser_qx: Qx, channel_stereo_stream_val: list, subimage_index: int) -> None:
    """
    Tests that the channel streams for stereo mode for loudness monitoring is set
    correctly.

    :param analyser_qx: object
    :param channel_stream_val: List used to store valid values for the channel stream.
    :param subimage_index: int. Value used to identify subimages.
    """
    if analyser_qx.analyser.loudness_config['audioAssignment']['audioMode'] == '5.1':
        tmp_conf = analyser_qx.analyser.loudness_config
        tmp_conf['audioAssignment']['audioMode'] = 'stereo'
        tmp_conf['audioAssignment']['channelAssignment'] = {
            'left': {'channel': 'group1Pair1Left', 'subimage': 1},
            'right': {'channel': 'group1Pair1Right', 'subimage': 1}
        }
        analyser_qx.analyser.loudness_config = tmp_conf

    else:
        expected_result = {'audioAssignment': {
                           'audioMode': 'stereo',
                           'channelAssignment': {
                               'left': {
                                   'channel': channel_stereo_stream_val[0],
                                   'subimage': subimage_index,
                               },
                               'right': {
                                   'channel': channel_stereo_stream_val[1],
                                   'subimage': subimage_index
                               }
                           }}}

        analyser_qx.analyser.loudness_config = expected_result
        conf = analyser_qx.analyser.loudness_config['audioAssignment']
        assert conf == expected_result['audioAssignment']
