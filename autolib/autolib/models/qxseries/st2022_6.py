"""\
Provides classes for st2022-6 analysis on Qx family devices.
"""

import logging
import requests

from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class ST2022_6(APIWrapperBase,
               url_properties={
                   "flow_list": {
                       "GET": "2022-6/receive/flowList",
                       "DOC": "TBD"
                   },
                   "flow_select": {
                       "GET": "2022-6/receive/flowSelect",
                       "PUT": "2022-6/receive/flowSelect",
                       "DOC": "TBD"
                   },
                   "multicast_requests": {
                       "GET": "2022-6/receive/multicastRequests",
                       "PUT": "2022-6/receive/multicastRequests",
                       "DOC": "Get all posts"
                   },
                   "ip_transmit_config": {
                       "GET": "ipTransmit/config",
                       "PUT": "ipTransmit/config",
                       "DOC": "TBD"
                   },
                   "ip_transmit_distribution": {
                       "GET": "ipTransmit/distribution",
                       "PUT": "ipTransmit/distribution",
                       "DOC": "TBD"
                   }
               },
               http_session=DEFAULT_SESSION
               ):

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
