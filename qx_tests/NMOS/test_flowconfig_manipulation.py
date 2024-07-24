"""
Tests that validate the behaviour of the new non-manual FlowConfig discarding code.

IMPORTANT: These tests require autolib rather than autolib. Hopefully autolib will be retired before this
goes live.
"""

import json
import logging
import tempfile
from typing import Callable
from pathlib import Path
from typing import Union, Dict
from uuid import uuid4

import pytest
import time

from dual_activations import connections_dual, disable_connections_dual
from receiver_mappings import SingleMapping, DualMapping
from single_activations import connections_single, disable_connections_single
from autolib.factory import make_qx
from autolib.logconfig import autolib_log
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qx import Qx, TemporaryPreset, StateSnapshot
from autolib.models.qxseries.st2110 import ST2110Protocol
from autolib.testexception import TestException

log = logging.getLogger(autolib_log)

FILLER_VALUE = 'FILLERVALUE'
FLOW_LISTS = {ST2110Protocol.Dash20: 'configs211020', ST2110Protocol.Dash30: 'configs211030',
              ST2110Protocol.Dash31: 'configs211031', ST2110Protocol.Dash40: 'configs211040'}


class ConnectionMaker:
    """\
    The ConnectionMaker class is responsible for making NMOS connections to a specified device
    by determining the appropriate receivers to use for different activations using the receiver tags.
    Activation details (the body of the staged endpoint requests) are defined in single_activations
    and dual_activations. The receiver tag mappings are defined in receiver_mappings.
    """
    def __init__(self, qx: Qx, dual_receivers: bool):
        self._qx = qx
        self._dual_rx = dual_receivers

    def get_receiver_id_from_tag(self, tag_name: str) -> Union[str, None]:
        """\
        Obtain the NMOS ID UUID for a receiver whose tag matches that specified.
        """
        receivers = self._qx.nmos.node.receivers
        for receiver in receivers:
            receiver_tags = receiver.get('tags', {}).get('urn:x-nmos:tag:grouphint/v1.0', None)
            if tag_name in receiver_tags:
                return receiver.get('id', None)
        raise TestException(f"Could not find a receiver with tag {tag_name}. Are your unit's receivers configured as Dual Interface?")

    def send_requests(self, connection_data: Dict[Union[DualMapping, SingleMapping], Dict], protocol: ST2110Protocol):
        """\
        Iterate through the specified connection_data (see dual_activations and single_activations) making
        a connection for each.
        """
        for flow_type, payload in connection_data.items():
            try:
                tag_name = flow_type.value[type(self._qx).__name__]
                receiver_id = self.get_receiver_id_from_tag(tag_name)
                log.info(f'PATCHing receiver: {receiver_id} ({tag_name})')
                self._qx.nmos.connection.patch_receiver(receiver_id, payload)
            except TestException:
                log.info(f'Skipping attempt to PATCH receiver {tag_name}')
                raise


@pytest.fixture(scope='module')
def qx(test_qx_hostname: str):
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname global fixture.
    """
    qx = make_qx(test_qx_hostname)
    qx.request_capability(OperationMode.IP_2110)
    old_nmos_mode = qx.nmos.enabled
    qx.nmos.enable()
    yield qx
    if not old_nmos_mode:
        qx.nmos.disable()


def _add_50_nmos_flow_configs(*args, **kwargs) -> dict:
    """\
    Add a specified number of non-manual FlowConfig entries to the provided preset dict to the specified
    FlowConfigList (default 50 items).
    """
    json_data, = args
    protocol = kwargs['protocol']
    flow_config_list = FLOW_LISTS[protocol]
    count = 50

    flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_configs == FILLER_VALUE:
        # If the only item in the config list is the FILLERVALUE entry it comes to use as a string. We need
        # to convert this into a list containing the string so that we can append items to the list.
        json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = [FILLER_VALUE]
        flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    for ip_octet in range(count):
        new_entry = f'100,192.168.200.{ip_octet},239.200.229.{ip_octet},5500,5500,0,,0+1|475|false'
        flow_configs.append(new_entry)

    return json_data


def _add_50_manual_flow_configs(*args, **kwargs) -> dict:
    """\
    Add a specified number of manual FlowConfig entries to the provided preset dict to the specified
    FlowConfigList (default 50 items).
    """
    json_data, = args
    protocol = kwargs['protocol']
    flow_config_list = FLOW_LISTS[protocol]
    count = 50

    flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_configs == FILLER_VALUE:
        # If the only item in the config list is the FILLERVALUE entry it comes to use as a string. We need
        # to convert this into a list containing the string so that we can append items to the list.
        json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = [FILLER_VALUE]
        flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    for ip_octet in range(count):
        new_entry = f'100,192.168.200.{ip_octet},239.200.229.{ip_octet},5500,5500,0,,0+1|475|true'
        flow_configs.append(new_entry)

    return json_data


def reset_test_unit(qx: Qx, dual_interface: bool):
    """\
    Restore defaults and configure NMOS
    """
    # Default the unit's settings (maybe we should take a copy of the pre-test lastKnownState in the qx fixture)
    log.info("Resetting unit to default settings")
    qx.restore_initial_state()

    # Enable NMOS and set the receiver interface binding after the unit was set to defaults
    qx.nmos.enable()
    qx.nmos.dual_interface_receiver = dual_interface

    # Allow time for the new resources to be built and the lastKnownPreset to be written
    time.sleep(40)


def _generalised_nmos_test(qx: Qx,
                           protocol: ST2110Protocol,
                           dual_interface: bool,
                           setup_state_callback: Callable,
                           work_callback: Callable,
                           validate_state_callback: Callable):

    """\
    Generalised test body which makes callbacks to set the initial state of the unit (potentially through the
    manipulation of a preset which is then re-uploaded), perform some work on the unit (e.g. to make some NMOS
    connections) and then perform some validation steps.
    """
    # Restore defaults and configure NMOS

    reset_test_unit(qx, dual_interface)

    with StateSnapshot(qx) as state_to_modify:

        # Apply changes to the preset dict before it's re-applied
        new_state = setup_state_callback(state_to_modify.state, **locals())
        if not new_state:
            raise TestException("Failed to modify the device's initial state")

        log.info("Write the new modified preset to a file")
        with tempfile.TemporaryDirectory() as temp_dir:
            modified_preset = str(uuid4())
            modified_preset_filename = f'{modified_preset}.preset'
            with open(Path(temp_dir) / modified_preset_filename, 'wt') as munged_preset_file:
                json.dump(new_state, munged_preset_file)

            log.info("Load the modified preset to the unit using the TemporaryPreset context manager")
            with TemporaryPreset(qx, Path(temp_dir) / modified_preset_filename, modified_preset):

                # Do something
                work_callback(new_state, **locals())

                # Count the number of FlowConfigs in the FlowConfigList under test
                # by waiting for the lastKnown preset to be written to the unit and
                # downloading and parsing it.
                with StateSnapshot(qx) as post_work:
                    validate_state_callback(post_work.state, **locals())


@pytest.mark.ip2110
@pytest.mark.parametrize("protocol,dual_interface,expected,preset_callback", [
    pytest.param(ST2110Protocol.Dash20, True, 3, _add_50_nmos_flow_configs, id="2110-20_50_NMOS_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 5, _add_50_nmos_flow_configs, id="2110-30_50_NMOS_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 5, _add_50_nmos_flow_configs, id="2110-31_50_NMOS_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 3, _add_50_nmos_flow_configs, id="2110-40_50_NMOS_FlowConfigs_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, True, 53, _add_50_manual_flow_configs, id="2110-20_50_Manual_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 55, _add_50_manual_flow_configs, id="2110-30_50_Manual_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 55, _add_50_manual_flow_configs, id="2110-31_50_Manual_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 53, _add_50_manual_flow_configs, id="2110-40_50_Manual_FlowConfigs_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 3, _add_50_nmos_flow_configs, id="2110-20_50_NMOS_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 5, _add_50_nmos_flow_configs, id="2110-30_50_NMOS_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 5, _add_50_nmos_flow_configs, id="2110-31_50_NMOS_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 3, _add_50_nmos_flow_configs, id="2110-40_50_NMOS_FlowConfigs_single_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 53, _add_50_manual_flow_configs, id="2110-20_50_Manual_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 55, _add_50_manual_flow_configs, id="2110-30_50_Manual_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 55, _add_50_manual_flow_configs, id="2110-31_50_Manual_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 53, _add_50_manual_flow_configs, id="2110-40_50_Manual_FlowConfigs_single_rx"),
])
def test_nmos_flow_config_list_handling(qx: Qx,
                                        protocol: ST2110Protocol,
                                        dual_interface: bool,
                                        expected: int,
                                        preset_callback: Callable[[dict, str], dict]):
    """\
    Get the current state preset, modify it via a callback and then perform activations on all receivers then check
    the number of FlowConfigs after the purging code has run. Note that the expected FlowConfigList
    sizes should take into account the presence of the initial FILLERVALUE entry.

    :param qx: A Qx series DeviceController that supports NMOS
    :param protocol: The FlowConfigList protocol that we are testing
    :param dual_interface: A boolean that specifies if the Qx is configured with dual or single interface receivers.
    :param expected:
    :param preset_callback: A callable that takes a preset as a dict and a string naming the flow config list in the
                            preset to modify (the same as parameter 'flow_config_list'). This is called by the test
                            to modify the specified FlowConfig list by manipulating the current state preset.

    """

    def setup(*args, **kwargs):
        log.info(f"-- Setup stage: Calling {preset_callback.__name__}")
        return preset_callback(*args, **kwargs)

    def work(*args, **kwargs):
        log.info("-- Work stage: Trigger activations on all receivers")
        to_send = connections_dual if dual_interface else connections_single
        maker = ConnectionMaker(qx, dual_interface)
        maker.send_requests(to_send, protocol)

    def validate(*args, **kwargs):
        """\
        Check that the end state of the device is as expected.
        """
        state_dict, = args
        protocol = kwargs['protocol']
        flow_configs = state_dict['Datacore']['configCoreRouter']['ipFlowConfig'][FLOW_LISTS[protocol]]['data']

        log.info(f"-- Validation stage: Looking to see if we have the expected number of FlowConfigs in {FLOW_LISTS[protocol]}")

        # Check that the FlowConfigList is not empty
        assert flow_configs != FILLER_VALUE

        log.info(f"*** Flow Configs - {FLOW_LISTS[protocol]} *****************")
        for flow_config in flow_configs:
            log.info(flow_config)
        log.info("***************************************************")

        flow_config_count = len(flow_configs)
        log.info(f"Validate the size post-deactivation of the FlowConfigList under test. Found {flow_config_count}, expecting {expected}")
        assert flow_config_count == expected
        assert FILLER_VALUE in flow_configs

    _generalised_nmos_test(qx, protocol, dual_interface, setup, work, validate)


def _add_matching_manual_flow_configs(*args, **kwargs) -> dict:
    """\
    """
    json_data, = args
    protocol = kwargs['protocol']
    flow_config_list = FLOW_LISTS[protocol]

    flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_configs == FILLER_VALUE:
        # If the only item in the config list is the FILLERVALUE entry it comes to use as a string. We need
        # to convert this into a list containing the string so that we can append items to the list.
        json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = [FILLER_VALUE]
        flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_config_list == 'configs211020':
        flow_configs.append(f'96,192.168.10.4,239.4.20.1,20000,20000,0,,0+1|475|true')
        flow_configs.append(f'96,192.168.10.4,239.4.20.2,20000,20000,0,,1+1|475|true')
    elif flow_config_list == 'configs211030':
        flow_configs.append(f'97,192.168.10.4,239.4.30.1,20000,20000,0,,0+2|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.30.2,20000,20000,0,,1+2|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.30.3,20000,20000,0,,0+2|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.30.4,20000,20000,0,,1+2|475|true')
    elif flow_config_list == 'configs211031':
        flow_configs.append(f'97,192.168.10.4,239.4.31.1,20000,20000,0,,0+3|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.31.2,20000,20000,0,,1+3|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.31.3,20000,20000,0,,0+3|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.31.4,20000,20000,0,,1+3|475|true')
    else:
        flow_configs.append(f'100,192.168.10.4,239.4.40.1,20000,20000,0,,0+4|475|true')
        flow_configs.append(f'100,192.168.10.4,239.4.40.2,20000,20000,0,,1+4|475|true')

    return json_data


def _no_pre_existing_flow_configs(*args, **kwargs) -> dict:
    """\
    """
    json_data, = args
    protocol = kwargs['protocol']
    flow_config_list = FLOW_LISTS[protocol]

    json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = FILLER_VALUE
    return json_data


def _add_non_matching_manual_flow_configs(*args, **kwargs) -> dict:
    """\
    """
    json_data, = args
    protocol = kwargs['protocol']
    flow_config_list = FLOW_LISTS[protocol]

    flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_configs == FILLER_VALUE:
        # If the only item in the config list is the FILLERVALUE entry it comes to use as a string. We need
        # to convert this into a list containing the string so that we can append items to the list.
        json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = [FILLER_VALUE]
        flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_config_list == 'configs211020':
        flow_configs.append(f'96,192.168.10.4,239.4.20.1,5500,5500,0,,0+1|475|true')
        flow_configs.append(f'96,192.168.10.4,239.4.20.2,5500,5500,0,,1+1|475|true')
    elif flow_config_list == 'configs211030':
        flow_configs.append(f'97,192.168.10.4,239.4.30.1,5500,5500,0,,0+2|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.30.2,5500,5500,0,,1+2|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.30.3,5500,5500,0,,0+2|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.30.4,5500,5500,0,,1+2|475|true')
    elif flow_config_list == 'configs211031':
        flow_configs.append(f'97,192.168.10.4,239.4.31.1,5500,5500,0,,0+3|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.31.2,5500,5500,0,,1+3|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.31.3,5500,5500,0,,0+3|475|true')
        flow_configs.append(f'97,192.168.10.4,239.4.31.4,5500,5500,0,,1+3|475|true')
    else:
        flow_configs.append(f'100,192.168.10.4,239.4.40.1,5500,5500,0,,0+4|475|true')
        flow_configs.append(f'100,192.168.10.4,239.4.40.2,5500,5500,0,,1+4|475|true')

    return json_data


def _add_matching_non_manual_flow_configs(*args, **kwargs) -> dict:
    """\
    Simulates the state where a number of NMOS-created FlowConfigs exist in the FlowConfigList.

    Add FlowConfigs to the FlowConfigLists that match the fundamental set of 'real' flows but are NMOS-instigated.
    This should only be called when the FlowConfigList under test has been cleared of flows.

    When NMOS activations are triggered with the same flow details, no duplicate entries should exist in the list
    at the end of the test.
    """
    json_data, = args
    protocol = kwargs['protocol']
    flow_config_list = FLOW_LISTS[protocol]

    flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_configs == FILLER_VALUE:
        # If the only item in the config list is the FILLERVALUE entry it comes to use as a string. We need
        # to convert this into a list containing the string so that we can append items to the list.
        json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = [FILLER_VALUE]
        flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_config_list == 'configs211020':
        flow_configs.append(f'96,192.168.10.4,239.4.20.1,20000,20000,0,,0+1|475|false')
        flow_configs.append(f'96,192.168.10.4,239.4.20.2,20000,20000,0,,1+1|475|false')
    elif flow_config_list == 'configs211030':
        flow_configs.append(f'97,192.168.10.4,239.4.30.1,20000,20000,0,,0+2|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.30.2,20000,20000,0,,1+2|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.30.3,20000,20000,0,,0+2|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.30.4,20000,20000,0,,1+2|475|false')
    elif flow_config_list == 'configs211031':
        flow_configs.append(f'97,192.168.10.4,239.4.31.1,20000,20000,0,,0+3|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.31.2,20000,20000,0,,1+3|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.31.3,20000,20000,0,,0+3|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.31.4,20000,20000,0,,1+3|475|false')
    else:
        flow_configs.append(f'100,192.168.10.4,239.4.40.1,20000,20000,0,,0+4|475|false')
        flow_configs.append(f'100,192.168.10.4,239.4.40.2,20000,20000,0,,1+4|475|false')

    return json_data


def _add_non_matching_non_manual_flow_configs(*args, **kwargs) -> dict:
    """\
    """
    json_data, = args
    protocol = kwargs['protocol']
    flow_config_list = FLOW_LISTS[protocol]

    flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_configs == FILLER_VALUE:
        # If the only item in the config list is the FILLERVALUE entry it comes to use as a string. We need
        # to convert this into a list containing the string so that we can append items to the list.
        json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = [FILLER_VALUE]
        flow_configs = json_data['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

    if flow_config_list == 'configs211020':
        flow_configs.append(f'96,192.168.10.4,239.4.20.1,5500,5500,0,,0+1|475|false')
        flow_configs.append(f'96,192.168.10.4,239.4.20.2,5500,5500,0,,1+1|475|false')
    elif flow_config_list == 'configs211030':
        flow_configs.append(f'97,192.168.10.4,239.4.30.1,5500,5500,0,,0+2|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.30.2,5500,5500,0,,1+2|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.30.3,5500,5500,0,,0+2|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.30.4,5500,5500,0,,1+2|475|false')
    elif flow_config_list == 'configs211031':
        flow_configs.append(f'97,192.168.10.4,239.4.31.1,5500,5500,0,,0+3|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.31.2,5500,5500,0,,1+3|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.31.3,5500,5500,0,,0+3|475|false')
        flow_configs.append(f'97,192.168.10.4,239.4.31.4,5500,5500,0,,1+3|475|false')
    else:
        flow_configs.append(f'100,192.168.10.4,239.4.40.1,5500,5500,0,,0+4|475|false')
        flow_configs.append(f'100,192.168.10.4,239.4.40.2,5500,5500,0,,1+4|475|false')

    return json_data


@pytest.mark.ip2110
@pytest.mark.parametrize("protocol,dual_interface,expected,preset_callback,final_expected", [
    pytest.param(ST2110Protocol.Dash20, True, 3, _no_pre_existing_flow_configs, 3, id="2110-20_no_prexisting_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 5, _no_pre_existing_flow_configs, 5, id="2110-30_no_prexisting_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 5, _no_pre_existing_flow_configs, 5, id="2110-31_no_prexisting_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 3, _no_pre_existing_flow_configs, 3, id="2110-40_no_prexisting_FlowConfigs_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, True, 3, _add_matching_manual_flow_configs, 3, id="2110-20_manual_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 5, _add_matching_manual_flow_configs, 5, id="2110-30_manual_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 5, _add_matching_manual_flow_configs, 5, id="2110-31_manual_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 3, _add_matching_manual_flow_configs, 3, id="2110-40_manual_matching_FlowConfigs_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, True, 5, _add_non_matching_manual_flow_configs, 5, id="2110-20_manual_non_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 9, _add_non_matching_manual_flow_configs, 9, id="2110-30_manual_non_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 9, _add_non_matching_manual_flow_configs, 9, id="2110-31_manual_non_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 5, _add_non_matching_manual_flow_configs, 5, id="2110-40_manual_non_matching_FlowConfigs_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, True, 3, _add_matching_non_manual_flow_configs, 3, id="2110-20_non_manual_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 5, _add_matching_non_manual_flow_configs, 5, id="2110-30_non_manual_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 5, _add_matching_non_manual_flow_configs, 5, id="2110-31_non_manual_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 3, _add_matching_non_manual_flow_configs, 3, id="2110-40_non_manual_matching_FlowConfigs_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, True, 3, _add_non_matching_non_manual_flow_configs, 3, id="2110-20_non_manual_non_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 5, _add_non_matching_non_manual_flow_configs, 5, id="2110-30_non_manual_non_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 5, _add_non_matching_non_manual_flow_configs, 5, id="2110-31_non_manual_non_matching_FlowConfigs_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 3, _add_non_matching_non_manual_flow_configs, 3, id="2110-40_non_manual_non_matching_FlowConfigs_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 3, _no_pre_existing_flow_configs, 3, id="2110-20_no_prexisting_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 5, _no_pre_existing_flow_configs, 5, id="2110-30_no_prexisting_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 5, _no_pre_existing_flow_configs, 5, id="2110-31_no_prexisting_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 3, _no_pre_existing_flow_configs, 3, id="2110-40_no_prexisting_FlowConfigs_single_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 3, _add_matching_manual_flow_configs, 3, id="2110-20_manual_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 5, _add_matching_manual_flow_configs, 5, id="2110-30_manual_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 5, _add_matching_manual_flow_configs, 5, id="2110-31_manual_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 3, _add_matching_manual_flow_configs, 3, id="2110-40_manual_matching_FlowConfigs_single_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 5, _add_non_matching_manual_flow_configs, 5, id="2110-20_manual_non_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 9, _add_non_matching_manual_flow_configs, 9, id="2110-30_manual_non_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 9, _add_non_matching_manual_flow_configs, 9, id="2110-31_manual_non_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 5, _add_non_matching_manual_flow_configs, 5, id="2110-40_manual_non_matching_FlowConfigs_single_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 3, _add_matching_non_manual_flow_configs, 3, id="2110-20_non_manual_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 5, _add_matching_non_manual_flow_configs, 5, id="2110-30_non_manual_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 5, _add_matching_non_manual_flow_configs, 5, id="2110-31_non_manual_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 3, _add_matching_non_manual_flow_configs, 3, id="2110-40_non_manual_matching_FlowConfigs_single_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 3, _add_non_matching_non_manual_flow_configs, 3, id="2110-20_non_manual_non_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 5, _add_non_matching_non_manual_flow_configs, 5, id="2110-30_non_manual_non_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 5, _add_non_matching_non_manual_flow_configs, 5, id="2110-31_non_manual_non_matching_FlowConfigs_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 3, _add_non_matching_non_manual_flow_configs, 3, id="2110-40_non_manual_non_matching_FlowConfigs_single_rx"),
])
def test_nmos_replace_manual_flow_configs(qx: Qx,
                                          protocol: ST2110Protocol,
                                          dual_interface: bool,
                                          expected: int,
                                          preset_callback: Callable[[dict, str], dict],
                                          final_expected):
    """\
    Get the current state preset, modify it via a callback and then perform activations on all receivers then check
    the number of FlowConfigs after the purging code has run. Note that the expected FlowConfigList
    sizes should take into account the presence of the initial FILLERVALUE entry. Then deactivate all receivers and
    check that there are the expected number of FlowConfigs remaining.

    NOTE: The Qx currently only prunes unused NMOS made connections when new ones are added, not when a deactivation
    occurs (which is complicated and unnecessary). This should be taken into account when calculating the number
    of expected flows in the FlowConfigList following deactivations.

    :param qx: A Qx series DeviceController that supports NMOS
    :param protocol: The FlowConfigList protocol that we are testing
    :param dual_interface: A boolean that specifies if the Qx is configured with dual or single interface receivers.
    :param expected:
    :param preset_callback: A callable that takes a preset as a dict and a string naming the flow config list in the
                            preset to modify (the same as parameter 'flow_config_list'). This is called by the test
                            to modify the specified FlowConfig list by manipulating the current state preset.

    """

    # Start out by running the code from the test_nmos_flow_config_list_handling test to get to the point
    # where were are ready to deactivate all the receivers and re-examine the FlowConfigLists
    test_nmos_flow_config_list_handling(qx, protocol, dual_interface, expected, preset_callback)

    log.info("Trigger deactivations on all receivers")
    to_send = disable_connections_dual if dual_interface else disable_connections_single
    maker = ConnectionMaker(qx, dual_interface)
    maker.send_requests(to_send, protocol)

    log.info("Create a new preset to get the state from")
    with tempfile.TemporaryDirectory() as temp_dir:
        with StateSnapshot(qx) as snapshot:
            new_state_dict = snapshot.state

            flow_configs = new_state_dict['Datacore']['configCoreRouter']['ipFlowConfig'][FLOW_LISTS[protocol]]['data']

            # Check that the FlowConfigList is not empty
            assert flow_configs != FILLER_VALUE

            log.info(f"*** Flow Configs post deactivation- {FLOW_LISTS[protocol]} *****************")
            for flow_config in flow_configs:
                log.info(flow_config)
            log.info("***************************************************")

            flow_config_count = len(flow_configs)
            log.info(f"Validate the size post-deactivation of the FlowConfigList under test. Found {flow_config_count}, expecting {expected}")
            assert flow_config_count == final_expected
            assert FILLER_VALUE in flow_configs


@pytest.mark.ip2110
@pytest.mark.parametrize("protocol,dual_interface,expected,final_expected", [
    pytest.param(ST2110Protocol.Dash20, True, 5, 5, id="2110-20_lots_of_nmos_connections_dual_rx"),
    pytest.param(ST2110Protocol.Dash30, True, 9, 9, id="2110-30_lots_of_nmos_connections_dual_rx"),
    pytest.param(ST2110Protocol.Dash31, True, 9, 9, id="2110-31_lots_of_nmos_connections_dual_rx"),
    pytest.param(ST2110Protocol.Dash40, True, 5, 5, id="2110-40_lots_of_nmos_connections_dual_rx"),

    pytest.param(ST2110Protocol.Dash20, False, 5, 5, id="2110-20_lots_of_nmos_connections_single_rx"),
    pytest.param(ST2110Protocol.Dash30, False, 9, 9, id="2110-30_lots_of_nmos_connections_single_rx"),
    pytest.param(ST2110Protocol.Dash31, False, 9, 9, id="2110-31_lots_of_nmos_connections_single_rx"),
    pytest.param(ST2110Protocol.Dash40, False, 5, 5, id="2110-40_lots_of_nmos_connections_single_rx"),
])
def test_nmos_lots_of_nmos_connections(qx: Qx,
                                       protocol: ST2110Protocol,
                                       dual_interface: bool,
                                       expected: int,
                                       final_expected: int):
    """\
    Get the current state preset, modify it via a callback and then perform activations on all receivers then check
    the number of FlowConfigs after the purging code has run. Note that the expected FlowConfigList
    sizes should take into account the presence of the initial FILLERVALUE entry. Next, make 20 NMOS activations and
    then check that the FlowConfigLists are not growing.

    :param qx: A Qx series DeviceController that supports NMOS
    :param protocol: The FlowConfigList protocol that we are testing
    :param dual_interface: A boolean that specifies if the Qx is configured with dual or single interface receivers.
    :param expected:
    :param preset_callback: A callable that takes a preset as a dict and a string naming the flow config list in the
                            preset to modify (the same as parameter 'flow_config_list'). This is called by the test
                            to modify the specified FlowConfig list by manipulating the current state preset.

    """

    # Create some setup, work and validate callables which we'll pass to the generalised test and then perform
    # our own test-specific post ops and validation.

    def setup(*args, **kwargs):
        """\
        Add some manual flow configurations to the FlowConfigList specified by protocol.
        """
        state_dict, = args
        protocol = kwargs['protocol']
        flow_config_list = FLOW_LISTS[protocol]
        flow_configs = state_dict['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

        if flow_configs == FILLER_VALUE:
            # If the only item in the config list is the FILLERVALUE entry it comes to use as a string. We need
            # to convert this into a list containing the string so that we can append items to the list.
            state_dict['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data'] = [FILLER_VALUE]
            flow_configs = state_dict['Datacore']['configCoreRouter']['ipFlowConfig'][flow_config_list]['data']

        log.info("-- Setup stage: Adding some manual FlowConfigs")

        if flow_config_list == 'configs211020':
            flow_configs.append(f'96,192.168.10.4,239.4.20.1,20000,20000,0,,0+1|475|true')
            flow_configs.append(f'96,192.168.10.4,239.4.20.2,20000,20000,0,,1+1|475|true')
        elif flow_config_list == 'configs211030':
            flow_configs.append(f'97,192.168.10.4,239.4.30.1,20000,20000,0,,0+2|475|true')
            flow_configs.append(f'97,192.168.10.4,239.4.30.2,20000,20000,0,,1+2|475|true')
            flow_configs.append(f'97,192.168.10.4,239.4.30.3,20000,20000,0,,0+2|475|true')
            flow_configs.append(f'97,192.168.10.4,239.4.30.4,20000,20000,0,,1+2|475|true')
        elif flow_config_list == 'configs211031':
            flow_configs.append(f'97,192.168.10.4,239.4.31.1,20000,20000,0,,0+3|475|true')
            flow_configs.append(f'97,192.168.10.4,239.4.31.2,20000,20000,0,,1+3|475|true')
            flow_configs.append(f'97,192.168.10.4,239.4.31.3,20000,20000,0,,0+3|475|true')
            flow_configs.append(f'97,192.168.10.4,239.4.31.4,20000,20000,0,,1+3|475|true')
        else:
            flow_configs.append(f'100,192.168.10.4,239.4.40.1,20000,20000,0,,0+4|475|true')
            flow_configs.append(f'100,192.168.10.4,239.4.40.2,20000,20000,0,,1+4|475|true')

        return state_dict

    def work(*args, **kwargs):
        """\
        Make 20 NMOS connections to the receiver under test.
        """
        state_dict, = args
        qx = kwargs['qx']
        log.info("-- Work stage: Start making connections on all receivers")
        for index in range(20):
            to_send = connections_dual if dual_interface else connections_single

            for _, data in to_send.items():
                for transport_params in data["transport_params"]:
                    transport_params["destination_port"] = 20000 + index
                data['transport_file']['data'].replace("20000", str(20000 + index))

            maker = ConnectionMaker(qx, dual_interface)
            maker.send_requests(to_send, protocol)

    def validate(*args, **kwargs):
        """\
        Check that the end state of the device is as expected.
        """
        state_dict, = args
        protocol = kwargs['protocol']
        flow_configs = state_dict['Datacore']['configCoreRouter']['ipFlowConfig'][FLOW_LISTS[protocol]]['data']

        log.info(f"-- Validation stage: Looking to see if we have the expected number of FlowConfigs in {FLOW_LISTS[protocol]}")

        # Check that the FlowConfigList is not empty
        assert flow_configs != FILLER_VALUE

        log.info(f"*** Flow Configs - {FLOW_LISTS[protocol]} *****************")
        for flow_config in flow_configs:
            log.info(flow_config)
        log.info("***************************************************")

        flow_config_count = len(flow_configs)
        log.info(f"Validate the size post-deactivation of the FlowConfigList under test. Found {flow_config_count}, expecting {expected}")
        assert flow_config_count == final_expected
        assert FILLER_VALUE in flow_configs

    _generalised_nmos_test(qx, protocol, dual_interface, setup, work, validate)
