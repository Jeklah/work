"""\
Provides classes for interacting with the AES I/O features on Qx family devices.
"""
import logging
from copy import deepcopy
import requests

from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class AESInputOutput(APIWrapperBase,
                     url_properties={
                         "aes_io_config": {
                             "GET": "aesIO/config",
                             "PUT": "aesIO/config",
                             "DOC": "Get / Set the AES Input Output configuration"
                         },
                         "aes_io_info": {
                             "GET": "aesIO/info",
                             "DOC": "Get the AES Input Output status information"
                         },
                     },
                     http_session=DEFAULT_SESSION
                     ):
    """
    Get and set AES I/O settings on devices supporting the Qx REST API.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)

    def get_aes_config(self):
        """
        Get a dict containing the AES IO configuration
        """
        return self.strip_api_fields(self.aes_io_config)

    def set_aes_config(self, channel_configs, **kwargs):
        """
        Configure the AES Input / Output of the assigned device.

        :arg channel_configs:	Dictionary of AES channels to configure
        :keywords passthrough:	Assign the source for outputs assigned as "passthrough"
        """
        data = deepcopy(channel_configs)
        if passthrough := kwargs.get('passthrough', None):
            data['passthrough'] = passthrough
        self.aes_io_config = data

    def get_aes_info(self):
        """
        Get a dict containing the AES IO power status
        """
        return self.strip_api_fields(self.aes_io_info)
