"""\
Provides classes for st2110 analysis and PTP on Qx family devices.
"""

import logging
import requests
import enum
from typing import Union

from urllib.parse import urlparse
from autolib.models.devicecontroller import DeviceController
from autolib.extendedenum import ExtendedEnum
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION
from autolib.models.qxseries.sfp import SFPManagement


@enum.unique
class ST2110Protocol(ExtendedEnum):
    Dash20 = '2110-20'
    Dash30 = '2110-30'
    Dash31 = '2110-31'
    Dash40 = '2110-40'


@enum.unique
class MediaTransmit(ExtendedEnum):
    VID = 'vid'
    AUD1 = 'aud1'
    AUD2 = 'aud2'
    AUD3 = 'aud3'
    AUD4 = 'aud4'
    ANC = 'anc1'


@enum.unique
class MonitorTransmit(ExtendedEnum):
    VIDMON = 'vid'
    AUDMON = 'aud1'


class IPTransmit(APIWrapperBase,
                 url_properties={
                     "config": {
                         "GET": "ipTransmitter/config",
                         "PUT": "ipTransmitter/config",
                         "DOC": "Get or set the configuration for 2110 IP Transmit."
                     },
                     "info": {
                         "GET": "ipTransmitter/info",
                         "DOC": "Get the current IP Transmitter status info."
                     }
                 },
                 http_session=DEFAULT_SESSION
                 ):
    """\
    Provides access to the 2110 IP Transmit features on the Qx series.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)

    def enable(self, output_list: list[Union[MonitorTransmit, MediaTransmit]], enable_val: bool = True):
        """\
        Enable a list of IP Transmitter flows.

        Note::
          Use with caution! Please ensure that you have configured the flow multicast address and port for
          the flows that you are enabling else problems may be encountered (especially if Source-specific multicast
          is not in use.
        """
        config_data = {}
        for output in output_list:
            if output in [MonitorTransmit.VIDMON, MonitorTransmit.AUDMON]:
                if not config_data.get('monitor', None):
                    config_data['monitor'] = {}
                config_data['monitor'][output.value] = {'enabled': enable_val}
            else:
                if not config_data.get('media', None):
                    config_data['media'] = {}
                config_data['media'][output.value] = {'enabled': enable_val}

        self.config = config_data

    def disable(self, output_list: list[Union[MonitorTransmit, MediaTransmit]]):
        """\
        Disable a list of IP Transmitter flows.
        """
        self.enable(output_list, False)

    def enable_all(self, enable_val: bool = True):
        """\
        Enable all available IP Transmitter flows (Media and Monitor).

        Note::
          Use with caution! Please ensure that you have configured the flow multicast address and port for
          the flows that you are enabling else problems may be encountered (especially if Source-specific multicast
          is not in use.
        """
        all_flows = [flow for flow in MediaTransmit] + [flow for flow in MonitorTransmit]
        self.enable(all_flows, enable_val)

    def disable_all(self):
        """\
        Disable all available IP Transmitter flows (Media and Monitor).
        """
        self.enable_all(enable_val=False)

    def enable_state(self) -> dict[str, bool]:
        """\
        Return a dictionary of the enable / disable state of each Tx flow
        """
        enable_dict = {}
        complete_state = self.config

        for media, val in complete_state['media'].items():
            enable_dict[MediaTransmit.from_value(media)] = val['enabled']

        for monitor, val in complete_state['monitor'].items():
            enable_dict[MonitorTransmit.from_value(monitor)] = val['enabled']

        return enable_dict

    @property
    def vid(self):
        return self.config['media'][MediaTransmit.VID.value]

    @vid.setter
    def vid(self, data: dict):
        self.config = {'media': {MediaTransmit.VID.value: data}}

    @property
    def aud1(self):
        return self.config['media'][MediaTransmit.AUD1.value]

    @aud1.setter
    def aud1(self, data: dict):
        self.config = {'media': {MediaTransmit.AUD1.value: data}}

    @property
    def aud2(self):
        return self.config['media'][MediaTransmit.AUD2.value]

    @aud2.setter
    def aud2(self, data: dict):
        self.config = {'media': {MediaTransmit.AUD2.value: data}}

    @property
    def aud3(self):
        return self.config['media'][MediaTransmit.AUD3.value]

    @aud3.setter
    def aud3(self, data: dict):
        self.config = {'media': {MediaTransmit.AUD3.value: data}}

    @property
    def aud4(self):
        return self.config['media'][MediaTransmit.AUD4.value]

    @aud4.setter
    def aud4(self, data: dict):
        self.config = {'media': {MediaTransmit.AUD4.value: data}}

    @property
    def anc(self):
        return self.config['media'][MediaTransmit.ANC.value]

    @anc.setter
    def anc(self, data: dict):
        self.config = {'media': {MediaTransmit.ANC.value: data}}

    @property
    def vidmon(self):
        return self.config['media'][MonitorTransmit.VIDMON.value]

    @vidmon.setter
    def vidmon(self, data: dict):
        self.config = {'media': {MonitorTransmit.VIDMON.value: data}}

    @property
    def audmon(self):
        return self.config['media'][MonitorTransmit.AUDMON.value]

    @audmon.setter
    def audmon(self, data: dict):
        self.config = {'media': {MonitorTransmit.AUDMON.value: data}}


class ST2110(APIWrapperBase,
             url_properties={
                 "analyser_mode": {
                     "GET": "2110/receive/analyserMode",
                     "PUT": "2110/receive/analyserMode",
                     "DOC": "TBD"
                 },
                 "flow_list": {
                     "GET": "2110/receive/flowList",
                     "DOC": "TBD"
                 },
                 "flow_select": {
                     "GET": "2110/receive/flowSelect",
                     "PUT": "2110/receive/flowSelect",
                     "DOC": "TBD"
                 },
                 "multicast_requests": {
                     "GET": "2110/receive/multicastRequests",
                     "PUT": "2110/receive/multicastRequests",
                     "DOC": "Get all posts"
                 },
                 "selected_flows_config": {
                     "GET": "2110/receive/selectedFlowsConfig",
                     "PUT": "2110/receive/selectedFlowsConfig",
                     "DOC": "Get all posts"
                 },
             },
             http_session=DEFAULT_SESSION
             ):

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, sfp: SFPManagement,
                 parent: DeviceController, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._ip_transmit = IPTransmit(base_url, logger, hostname, http_session)
        self._parent = parent
        self._sfp = sfp

    @property
    def ip_transmit(self):
        """\
        Property to access the 2110 IP transmit API object
        """
        return self._ip_transmit
