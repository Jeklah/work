"""
Provides classes for interacting with the new v2 Generator API (currently used in ST2110)

"""

import json
import functools
import random
import re
import warnings
import logging
import requests
import time
import urllib.parse
from pprint import pformat
from typing import List

from autolib.coreexception import CoreException
from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.prbs import PRBSMode

# The generator requests can often take longer to respond the most of the other API paths. We'll use a separate
# session for them.
GENERATOR_V2_SESSION = requests.Session()
GENERATOR_V2_SESSION.request = functools.partial(GENERATOR_V2_SESSION.request, timeout=120)


class GeneratorV2Exception(QxException):
    """
    Failure to generate a given standard or configure generator settings will raise a GeneratorException.
    """
    pass


class GeneratorV2(APIWrapperBase,
                  url_properties={
                      "generator_bouncing_box": {
                          "GET": "generator/bouncingBox",
                          "PUT": "generator/bouncingBox",
                          "DOC": "Get and set the state of the bouncing box."
                      },
                      "ident": {
                          "GET": "generator/ident",
                          "PUT": "generator/ident",
                          "DOC": "Get and set the state of the generator ident message."
                      },
                      "standard": {
                          "GET": "generator/standard",
                          "PUT": "generator/standard",
                          "DOC": "Get the generated standard or configure a new standard."
                      },
                      "status": {
                          "GET": "generator/status",
                          "DOC": "Get the current generator status."
                      },
                      "test_pattern": {
                          "GET": "generator/testPattern",
                          "PUT": "generator/testPattern",
                          "DOC": "Get and set the current generator test pattern."
                      },
                      "timecode": {
                          "GET": "generator/timecode",
                          "PUT": "generator/timecode",
                          "DOC": "Get and set the configuration of the timecode generator."
                      }
                  },
                  http_session=GENERATOR_V2_SESSION
                  ):
    """
    Get and set signal generator v2 settings on devices supporting the Qx REST API.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)

    @property
    def bouncing_box(self):
        """
        Enabled state of the bouncing box
        """
        return self.generator_bouncing_box['enabled']

    @bouncing_box.setter
    def bouncing_box(self, enable):
        """
        Enable / disable bouncing box on generated stream
        :param enable: Bool value to enable or disable the box
        """
        self.generator_bouncing_box = {"enabled": enable}

    @property
    def ident_enabled(self):
        """
        Enabled state of the bouncing box
        """
        return self.ident['enabled']

    @ident_enabled.setter
    def ident_enabled(self, enable):
        """
        Enable / disable bouncing box on generated stream
        :param enable: Bool value to enable or disable the box
        """
        self.ident = {"enabled": enable}
