"""\
Provides classes for interacting with the jitter features on Qx family devices.
"""

import requests
import logging
from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION
from autolib.models.qxseries.eye import Eye


class Jitter(APIWrapperBase,
             url_properties={
                 "jitter_status": {"GET": "jitter/status",
                                   "DOC": "Get the jitter analyser status"},
             },
             http_session=DEFAULT_SESSION
             ):
    """
    Get and set jitter analysis settings on devices supporting the Qx REST API.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, eye: Eye, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._eye = eye

    def is_jitter_lock(self):
        """
        Returns bool indicating analyser jitter lock
        """
        jitter_status = self.jitter_status
        locked = jitter_status.get("jitterLocked", False)
        if locked is not None:
            return locked
        raise QxException(f'{self._hostname} - Could not get jitter lock status. The response contained no jitterLocked key.')

    def get_jitter_values(self):
        """
        Return all Jitter reading values as dict
        """
        jitter_status = self.jitter_status
        jitter_value_dict = {}
        for key in sorted(jitter_status.keys()):
            if str(key).endswith("_Hz"):
                jitter_value_dict.update({key: jitter_status[key]})

        jitter_value_dict["jitterLocked"] = jitter_status.get("jitterLocked", False)
        return jitter_value_dict

