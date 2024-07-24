"""\
Provides classes for interacting with SFP interfaces on Qx family devices.
"""

import logging
import re
import requests
import time

from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.timeout import Timeout
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
            if 'UP' in attributes.split(","):
                exit_status, out, err = self._ssh.execute(f"ip -f inet addr show {sfp.value.name} | sed -En -e 's/.*inet ([0-9.]+).*/\\1/p'")
                return out != b''
            else:
                return False

        raise QxException(f"{self._hostname} - Could not get the status of {sfp.value.log_name} ({sfp.value.name}).")

    def interface_up(self, sfp: Interface, state: bool):
        """\
        Bring specified SFP up or down using the 'ip' tool.

        :param sfp: The interface to manipulate
        :param state: Boolean True for "up", False for "down"
        """
        up_down = "up" if state else "down"

        exit_status, _, _ = self._ssh.execute(f'ip link set {sfp.value.name} {up_down}')
        if exit_status != 0:
            raise QxException(f"Could not set the status of {sfp.value.log_name} ({sfp.value.name}).")

    def interface_up_blocking(self, sfp: Interface, state: bool, timeout: int = 60):
        """\
        This is a blocking version of interface_up that blocks until the required state is achieved or a timeout
        is reached. This returns if the required interface state is met within the timeout else a TimeoutError is
        thrown.

        Note:: This uses the Timeout context manager to enforce the timeout which currently only works on POSIX
        platforms.

        :param sfp: The interface to manipulate
        :param state: The required interface state (True is Up, False is Down)
        :param timeout: The timeout in seconds to wait for the required state to be met.
        """

        self.interface_up(sfp, state)

        with Timeout(timeout):
            while True:
                if state:
                    if self.up(sfp):
                        return
                else:
                    if not self.up(sfp):
                        return
                time.sleep(1)
                
    def get_ip_config(self, interface: Interface):
        """\
        Get IP networking information for a specified Interface. This takes an Interface enum
        as the interface parameter instead of requiring an SFP name like the wrapped 'ip_network'
        Rest API making it easier to write device-agnostic automation code.
        """
        interface_rest_name = interface.value.sfp_name[self._parent.type_name]
        return self.get_ip_network(interface_rest_name)
