"""\
IP methods shared between ST2110 and ST2022-6 protocols are in this class and this class provides access
to the protocol specific classes (currently for ST2110 and ST2022-6).
"""

from autolib.models.devicecontroller import DeviceController
from autolib.models.qxseries.st2110 import ST2110
from autolib.models.qxseries.st20226 import ST20226
from autolib.models.qxseries.sfp import SFPManagement
from autolib.ssh import SSHTools
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class IPNetworking(APIWrapperBase,
                   http_session=DEFAULT_SESSION
                   ):
    """
    Base shared ip functionality used by both 2022-6 and 2110 classes
    """
    def __init__(self, base_url, logger, hostname, sfp: SFPManagement, parent: DeviceController, http_session=None):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._ssh = SSHTools(logger, hostname)
        self._parent = parent
        self._sfp = sfp

        # For the ST21110 and ST20226 classes, make their parent the DeviceController that's the parent to this class
        self._st2110 = ST2110(base_url, logger, hostname, self._sfp, self._parent, http_session)
        self._st2022_6 = ST20226(base_url, logger, hostname, self._sfp, self._parent, http_session)

    @property
    def st2110(self):
        return self._st2110

    @property
    def st2022_6(self):
        return self._st2022_6
