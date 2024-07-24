"""\
Provides classes for st2022-6 analysis on Qx family devices.
"""

import copy
import logging
import requests

from autolib.coreexception import CoreException
from autolib.models.devicecontroller import DeviceController
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION
from autolib.models.qxseries.network_interfaces import Interface
from autolib.models.qxseries.sfp import SFPManagement


class ST20226(APIWrapperBase,
              url_properties={
                  "flow_list": {
                      "GET": "2022-6/receive/flowList",
                      "DOC": "Get the current flow list"
                  },
                  "flow_select": {
                      "GET": "2022-6/receive/flowSelect",
                      "PUT": "2022-6/receive/flowSelect",
                      "DOC": "Get or configure the selected flows"
                  },
                  "multicast_requests": {
                      "GET": "2022-6/receive/multicastRequests",
                      "PUT": "2022-6/receive/multicastRequests",
                      "DOC": "Get all posts"
                  },
                  "ip_transmit_config": {
                      "GET": "ipTransmit/config",
                      "PUT": "ipTransmit/config",
                      "DOC": "Get or set the 2022-6 transmitter configuration"
                  },
                  "ip_transmit_distribution": {
                      "GET": "ipTransmit/distribution",
                      "PUT": "ipTransmit/distribution",
                      "DOC": "Get or set the distribution of 2022-6 packets packets"
                  }
              },
              http_session=DEFAULT_SESSION
              ):

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, sfp: SFPManagement,
                 parent: DeviceController, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._parent = parent
        self._sfp = sfp
        self._meta_initialise(base_url, http_session)

    def _set_transmit(self, enabled: bool, transmit_config: dict) -> None:
        """\
        Switches on or off the transmission of the 2022-6 flow defined in
        TRANSMIT CONFIG. If ENABLED is True, the transmission is switched on;
        otherwise, it's switched off.
        """
        _cfg = copy.deepcopy(self.ip_transmit_config if transmit_config is None else transmit_config)
        _cfg['transmit'] = 'on' if enabled is True else 'off'
        if enabled is True:
            _cfg['destinationMacAddressingMode'] = 'Automatic'
        self.ip_transmit_config = _cfg

    def transmit_on(self, config: dict = None) -> None:
        """\
        Switches on the transmission of the 2022-6 flow defined in CONFIG. If
        CONFIG is None, the 2022-6 flow switched on is the flow currently
        defined in the Ip Transmit configuration on the unit. Otherwise, CONFIG is
        loaded on the unit.

        :param config: 2022-6 IP Transmit configuration (default: None)
        """
        self._set_transmit(True, config)

    def transmit_off(self, config: dict = None) -> None:
        """\
        Switches off the transmission of the 2022-6 flow defined in CONFIG. If
        CONFIG is None, the 2022-6 flow switched on is the flow currently
        defined in the Ip Transmit configuration on the unit. Otherwise, CONFIG is
        loaded on the unit.

        :param config: 2022-6 IP Transmit configuration (default: None)
        """
        self._set_transmit(False, config)

    def enable_flow(self, ip_address: str = None, dst_udp_port: int = None,
                    pkt_distribution: dict = None) -> None:
        """\
        Enable a 2022-6 flow. If IP ADDRESS is provided, it'll be used to set
        the flow's multicast address; otherwise, the multicast address is
        automatically computed. Similarly, with DST UDP PORT.

        PKT DISTRIBUTION allows to specify the distribution of packets to
        use while transmitting the flow. PKT DISTRIBUTION is a dictionary
        stating the distribution type and clock range.

        :param ip_address: multicast IP address to use (default: None)
        :param dst_udp_port: the multicast UDP port number (default: None)
        :param pkt_distribution: the packet distribution to use with
        the flow to enable (default: None). See self.ip_transmit_distribution
        for the relevant fields.
        """
        def host_serial_number():
            match self._hostname.split('qx-'):
                case _, tail:
                    return int(tail) if tail.isnumeric() else None
                case _:
                    return None

        _cfg = copy.deepcopy(self.ip_transmit_config)
        if ip_address is None:
            # An IP address is required because relying on the system default
            # leads to a multicast Mac address shared w/ all other Qx in the
            # world. Here, we just change the leftmost byte of the second media
            # interface addr.

            config = self._sfp.get_ip_config(Interface.MEDIA1)
            interface_rest_name = Interface.MEDIA1.value.sfp_name[self._parent.type_name]

            match config:
                case {'ipAddress': addr, **rest}:
                    first, *rest = addr.split('.')
                    _cfg['destinationIpAddress'] = '225.' + '.'.join(rest)
                case _:
                    raise CoreException(f"Unable to get IP address for second media interface ({interface_rest_name}). "
                                        f"Request resp.: {config}") from None
        else:
            # the IP address needs validation: left byte is to be in [224-239];
            # see QX-7282:
            try:
                address_bytes = ip_address.split('.')
                assert len(address_bytes) == 4 and 224 <= int(address_bytes[0]) <= 239
                _cfg['destinationIpAddress'] = ip_address
            except Exception:
                raise CoreException(
                    f'Invalid multicast IP address: {ip_address!r}')

        if dst_udp_port is None:
            # Aiming for unicity of the multicast: Take the leftmost 5 digits
            # from the host's name if it is of the form "qx-#####", leading 0
            # discarded. Otherwise, keep the default port number.
            if (serial_number := host_serial_number()) is not None:
                _cfg['destinationUdpPort'] = serial_number
        else:
            _cfg['destinationUdpPort'] = dst_udp_port

        self.transmit_on(_cfg)

        if pkt_distribution is not None:
            self.ip_transmit_distribution = pkt_distribution
