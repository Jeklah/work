"""\
Common functionality base class for Qx API wrapper classes built from the RestBoilerPlate metaclass to configure
the logger, hostname and SSH support class.
"""

from copy import deepcopy
import logging
from autolib.ssh import SSHTools
from autolib.restboilerplate import RestBoilerPlate


class APIWrapperBase(metaclass=RestBoilerPlate):
    """\
    Base functionality required by all Qx API wrapper classes to configure logging, the device hostname and SSH
    functions.

    :param logger: A logging.Logger instance that will be used by logging commands.
    :param hostname: The device hostname (used by logging, SSH etc.)
    """
    def __init__(self, logger: logging.Logger, hostname: str):
        self.log = logger
        self._hostname = hostname
        self._ssh = SSHTools(logger, hostname)

    def strip_api_fields(self, data: dict) -> dict:
        """\
        Remove the fields in the response from the Qx which are intended to be used by the trawler and have no
        bearing on the actual state.
        """
        new_dict = deepcopy(dict(data))
        for entry in ['links', 'message', 'status']:
            new_dict.pop(entry, None)
        return new_dict
