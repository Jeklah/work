"""\
Precision Time Protocol configuration and inspection class.
"""

import enum
import logging
import requests

from typing import List, Union

from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class Ptp(APIWrapperBase,
          url_properties={
              "node_self": {"GET": "timing/reference",
                            "PUT": "timing/reference",
                            "DOC": "Details of the current timing reference."},
          },
          url_methods={
              "config": {
                  "GET": ("timing/ptp/{interface}/config", "PTP configuration settings"),
                  "PUT": ("timing/ptp/{interface}/config", "Set PTP configuration settings")
              },
              "info": {
                  "GET": ("timing/ptp/{interface}/info", "PTP status information."),
                  "PUT": ("timing/ptp/{interface}/info", "Reset PTP status counters.")
              },
          },
          http_session=DEFAULT_SESSION
          ):
    """\
    Provides access to PTP information from the Qx (and some limited configuration).
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._MAX_IGMP_VERSION = 3

    def is_locked(self, interface: enum.Enum) -> bool:
        """\
        Returns a bool for PTP lock status

        :param interface: The interface to query
        """
        info = self.get_info(interface.value)
        return info.get("ptpLocked", False)

    def get_driftfile(self) -> List[str]:
        """\
        Get the content of the PTP drift file from the unit.
        """
        exit_status, stdout, stderr = self._ssh.execute("cat /home/tempDrift.drift")
        if exit_status != 0:
            raise QxException("Unable to read PTP drift file from the unit.")

        try:
            output = stdout.decode().splitlines()
        except IndexError:
            raise QxException('Could not read PTP tempDrift content.')

        return output

    def set_domain(self, domain: int, interface: enum.Enum):
        """\
        Configure the PTP domain for the specified interface.

        :param domain: The PTP domain value to set
        :param interface: The interface to configure
        """
        self.put_config(interface.value, {"domain": domain})

    def set_igmp_max(self, version: int, interface: enum.Enum):
        """
        Set the maximum IGMP protocol revision.
        """
        if version > self._MAX_IGMP_VERSION:
            raise QxException(f'{self._hostname} - IGMP version supplied is out of bounds (version supplied is {version})')

        self.put_config(interface.value, {"igmpMaxVersion": version})
