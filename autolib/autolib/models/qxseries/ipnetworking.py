"""\
IP methods shared between ST2110 and ST2022-6 protocols are in this class and this class provides access
to the protocol specific classes (currently for ST2110 and ST2022-6).
"""

import requests

from autolib.models.qxseries.st2110 import ST2110
from autolib.models.qxseries.st2022_6 import ST2022_6

from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.operationmode import OperationMode
from autolib.ssh import SSHTools

from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class IPNetworking(APIWrapperBase,
                   http_session=DEFAULT_SESSION
                   ):
    """
    Base shared ip functionality used by both 2022-6 and 2110 classes
    """
    def __init__(self, base_url, logger, hostname, http_session=None):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._ssh = SSHTools(logger, hostname)

        self._st2110 = ST2110(base_url, logger, hostname, http_session)
        self._st2022_6 = ST2022_6(base_url, logger, hostname, http_session)

    @property
    def st2110(self):
        return self._st2110

    @property
    def st2022_6(self):
        return self._st2022_6
