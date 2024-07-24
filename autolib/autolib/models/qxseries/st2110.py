"""\
Provides classes for st2110 analysis and PTP on Qx family devices.
"""

import logging
import requests
import enum

from urllib.parse import urlparse

from autolib.extendedenum import ExtendedEnum
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


@enum.unique
class ST2110Protocol(ExtendedEnum):
    Dash20 = "2110-20"
    Dash30 = "2110-30"
    Dash31 = "2110-31"
    Dash40 = "2110-40"


class Generator(APIWrapperBase,
                url_properties={
                    "bouncing_box": {
                        "GET": "generator/bouncingBox",
                        "PUT": "generator/bouncingBox",
                        "DOC": "Enable / disable the bouncing box"
                    },
                    "standard": {
                        "GET": "generator/standard",
                        "PUT": "generator/standard",
                        "DOC": "Configure or query the generated standard"
                    },
                    "status": {
                        "GET": "generator/status",
                        "DOC": "Get the ST2110 generator status"
                    },
                    "test_pattern": {
                        "GET": "generator/testPattern",
                        "PUT": "generator/testPattern",
                        "DOC": "Query or set the generator's test pattern"
                    },
                    "timecode": {
                        "GET": "generator/timecode",
                        "PUT": "generator/timecode",
                        "DOC": "Query or configure the timecode display in the generated signal"
                    }
                },
                http_session=DEFAULT_SESSION
                ):
    """\
    Provides access to the Analyser features on the Qx series.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)


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

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        base_url_v2 = urlparse(base_url)._replace(path="/api/v2/").geturl()
        self._generator = Generator(base_url_v2, logger, hostname, http_session)

    @property
    def generator(self):
        """\
        Property to access the 2110 generator API object
        """
        return self._generator
