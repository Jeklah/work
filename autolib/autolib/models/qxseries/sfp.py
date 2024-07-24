"""\
Provides classes for interacting with SFP interfaces on Qx family devices.
"""

import logging
import re
import requests

from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.ssh import SSHTools
from autolib.models.qxseries.session import DEFAULT_SESSION
from autolib.models.qxseries.network_interfaces import Interface


class SFPManagement(APIWrapperBase,
                    url_methods={
                        "info": {
                            "GET": ("sfpInfo/{interface}", "SFP information")
                        },
                        "ip_network": {
                            "GET": ("sfpIpNetwork/{interface}", "SFP IP network information"),
                            "PUT": ("sfpIpNetwork/{interface}", "Configure SFP IP network information")
                        },
                    },
                    http_session=DEFAULT_SESSION
                    ):
    """\
    Provides access to PTP information from the Qx (and some limited configuration).

    Note that this takes a reference to the parent as it's final parameter. The type annotation it a PEP-484 Forward
    Reference (https://peps.python.org/pep-0484/#forward-references) to avoid cyclic imports.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session, parent: 'DeviceController'):
        super().__init__(logger, hostname)
        self._parent = parent
        self._parent_type_name = type(parent).__name__
        self._meta_initialise(base_url, http_session)
        self._ssh = SSHTools(logger, hostname)

    def up(self, sfp: Interface) -> bool:
        """\
        Determine if an interface is up or not (in the conventional Linux kernel sense)
        :param sfp: Interface enumeration
        :return True if link is reported UP by "ip link show" otherwise False
        """
        exit_status, out, err = self._ssh.execute(f'ip link show {sfp.value.name}')
        if (link := re.search('<([^>]+)>', str(out.split(b'\n')[0], 'UTF-8'))) and exit_status == 0:
            attributes, = link.groups()
            return 'UP' in attributes.split(",")

        raise QxException(f"{self._hostname} - Could not get the status of {sfp.value.log_name} ({sfp.value.name}).")

    def interface_up(self, sfp: Interface, state: bool):
        """\
        Bring specified SFP up or down using ifconfig
        :param sfp: Network interface to set up or down (e.g. Interface.MGMT or Interface.MEDIA0)
        :param state: Boolean True for "up", False for "down"
        """
        up_down = "up" if state else "down"

        exit_status, _, _ = self._ssh.execute(f'ip link set {sfp.value.name} {up_down}')
        if exit_status != 0:
            raise QxException(f"Could not set the status of {sfp.value.log_name} ({sfp.value.name}).")
