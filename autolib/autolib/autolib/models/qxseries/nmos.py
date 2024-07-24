"""\
Provides properties and methods for interacting with NMOS on the Qx family of devices.
"""
import dataclasses
import enum
import logging
import requests
import time
from typing import Union, Optional

from autolib.coreexception import CoreException
from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION
from autolib.extendedenum import ExtendedEnum
from autolib.models.qxseries.sdp import SDP


class NmosException(QxException):
    """
    Some Nmos specific failure
    """
    pass


class InterfaceType(ExtendedEnum):
    """\
    Represents dual or single interface mode.
    """
    Single = 'singleInterface'
    Dual = 'dualInterface'


@enum.unique
class DualRx(ExtendedEnum):
    VID = {'Qx': "SFP A+B Rx:VID", 'QxL': "SFP E+F Rx:VID", 'QxP': "SFP E+F Rx:VID"}
    AUD1 = {'Qx': "SFP A+B Rx:AUD 1", 'QxL': "SFP E+F Rx:AUD 1", 'QxP': "SFP E+F Rx:AUD 1"}
    AUD2 = {'Qx': "SFP A+B Rx:AUD 2", 'QxL': "SFP E+F Rx:AUD 2", 'QxP': "SFP E+F Rx:AUD 2"}
    AUD3 = {'Qx': "SFP A+B Rx:AUD 3", 'QxL': "SFP E+F Rx:AUD 3", 'QxP': "SFP E+F Rx:AUD 3"}
    AUD4 = {'Qx': "SFP A+B Rx:AUD 4", 'QxL': "SFP E+F Rx:AUD 4", 'QxP': "SFP E+F Rx:AUD 4"}
    ANC = {'Qx': "SFP A+B Rx:ANC", 'QxL': "SFP E+F Rx:ANC", 'QxP': "SFP E+F Rx:ANC"}


@enum.unique
class SingleRx(ExtendedEnum):
    VID_1 = {'Qx': "SFP A Rx:VID", 'QxL': "SFP E Rx:VID", 'QxP': "SFP E Rx:VID"}
    AUD1_1 = {'Qx': "SFP A Rx:AUD 1", 'QxL': "SFP E Rx:AUD 1", 'QxP': "SFP E Rx:AUD 1"}
    AUD2_1 = {'Qx': "SFP A Rx:AUD 2", 'QxL': "SFP E Rx:AUD 2", 'QxP': "SFP E Rx:AUD 2"}
    AUD3_1 = {'Qx': "SFP A Rx:AUD 3", 'QxL': "SFP E Rx:AUD 3", 'QxP': "SFP E Rx:AUD 3"}
    AUD4_1 = {'Qx': "SFP A Rx:AUD 4", 'QxL': "SFP E Rx:AUD 4", 'QxP': "SFP E Rx:AUD 4"}
    ANC_1 = {'Qx': "SFP A Rx:ANC", 'QxL': "SFP E Rx:ANC", 'QxP': "SFP E Rx:ANC"}
    VID_2 = {'Qx': "SFP B Rx:VID", 'QxL': "SFP F Rx:VID", 'QxP': "SFP F Rx:VID"}
    AUD1_2 = {'Qx': "SFP B Rx:AUD 1", 'QxL': "SFP F Rx:AUD 1", 'QxP': "SFP F Rx:AUD 1"}
    AUD2_2 = {'Qx': "SFP B Rx:AUD 2", 'QxL': "SFP F Rx:AUD 2", 'QxP': "SFP F Rx:AUD 2"}
    AUD3_2 = {'Qx': "SFP B Rx:AUD 3", 'QxL': "SFP F Rx:AUD 3", 'QxP': "SFP F Rx:AUD 3"}
    AUD4_2 = {'Qx': "SFP B Rx:AUD 4", 'QxL': "SFP F Rx:AUD 4", 'QxP': "SFP F Rx:AUD 4"}
    ANC_2 = {'Qx': "SFP B Rx:ANC", 'QxL': "SFP F Rx:ANC", 'QxP': "SFP F Rx:ANC"}


@enum.unique
class DualTx(ExtendedEnum):
    VID = {'Qx': "SFP A+B Tx:VID", 'QxL': "SFP E+F Tx:VID", 'QxP': "SFP E+F Tx:VID"}
    AUD1 = {'Qx': "SFP A+B Tx:AUD 1", 'QxL': "SFP E+F Tx:AUD 1", 'QxP': "SFP E+F Tx:AUD 1"}
    AUD2 = {'Qx': "SFP A+B Tx:AUD 2", 'QxL': "SFP E+F Tx:AUD 2", 'QxP': "SFP E+F Tx:AUD 2"}
    AUD3 = {'Qx': "SFP A+B Tx:AUD 3", 'QxL': "SFP E+F Tx:AUD 3", 'QxP': "SFP E+F Tx:AUD 3"}
    AUD4 = {'Qx': "SFP A+B Tx:AUD 4", 'QxL': "SFP E+F Tx:AUD 4", 'QxP': "SFP E+F Tx:AUD 4"}
    ANC = {'Qx': "SFP A+B Tx:ANC", 'QxL': "SFP E+F Tx:ANC", 'QxP': "SFP E+F Tx:ANC"}


@enum.unique
class SingleTx(ExtendedEnum):
    VID_1 = {'Qx': "SFP A Tx:VID", 'QxL': "SFP E Tx:VID", 'QxP': "SFP E Tx:VID"}
    AUD1_1 = {'Qx': "SFP A Tx:AUD 1", 'QxL': "SFP E Tx:AUD 1", 'QxP': "SFP E Tx:AUD 1"}
    AUD2_1 = {'Qx': "SFP A Tx:AUD 2", 'QxL': "SFP E Tx:AUD 2", 'QxP': "SFP E Tx:AUD 2"}
    AUD3_1 = {'Qx': "SFP A Tx:AUD 3", 'QxL': "SFP E Tx:AUD 3", 'QxP': "SFP E Tx:AUD 3"}
    AUD4_1 = {'Qx': "SFP A Tx:AUD 4", 'QxL': "SFP E Tx:AUD 4", 'QxP': "SFP E Tx:AUD 4"}
    ANC_1 = {'Qx': "SFP A Tx:ANC", 'QxL': "SFP E Tx:ANC", 'QxP': "SFP E Tx:ANC"}
    VID_2 = {'Qx': "SFP B Tx:VID", 'QxL': "SFP F Tx:VID", 'QxP': "SFP F Tx:VID"}
    AUD1_2 = {'Qx': "SFP B Tx:AUD 1", 'QxL': "SFP F Tx:AUD 1", 'QxP': "SFP F Tx:AUD 1"}
    AUD2_2 = {'Qx': "SFP B Tx:AUD 2", 'QxL': "SFP F Tx:AUD 2", 'QxP': "SFP F Tx:AUD 2"}
    AUD3_2 = {'Qx': "SFP B Tx:AUD 3", 'QxL': "SFP F Tx:AUD 3", 'QxP': "SFP F Tx:AUD 3"}
    AUD4_2 = {'Qx': "SFP B Tx:AUD 4", 'QxL': "SFP F Tx:AUD 4", 'QxP': "SFP F Tx:AUD 4"}
    ANC_2 = {'Qx': "SFP B Tx:ANC", 'QxL': "SFP F Tx:ANC", 'QxP': "SFP F Tx:ANC"}


class Node(APIWrapperBase,
           url_properties={
               "node_self": {"GET": "self",
                             "DOC": "Details of the Node self resource - this cannot be called self in Python"},
               "devices": {"GET": "devices", "DOC": "A list of the Devices provided by the Node"},
               "senders": {"GET": "senders", "DOC": "A list of the senders provided by the Node"},
               "receivers": {"GET": "receivers", "DOC": "A list of the receivers provided by the Node"},
               "flows": {"GET": "flows", "DOC": "A list of the flows provided by the Node"},
               "sources": {"GET": "sources", "DOC": "A list of the sources provided by the Node"}},
           url_methods={
               "sender": {"GET": ("senders/{nmosid}", "IS-04 Sender information")},
               "receiver": {"GET": ("receivers/{nmosid}", "IS-04 Receiver information")}
           },
           http_session=DEFAULT_SESSION
           ):
    """\
    Provides access to the IS-04 Node API on the unit.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(f'{base_url.rstrip("/")}/x-nmos/node/v1.3', http_session)


class Connection(APIWrapperBase,
                 url_properties={
                     "senders": {
                         "GET": "single/senders", "DOC": "Obtain a list of sender IDs"
                     },
                     "receivers": {
                         "GET": "single/receivers", "DOC": "Obtain a list of receiver IDs"
                     },
                     "bulk_senders": {
                         "POST": "bulk/senders", "DOC": "Configure a salvo of sender activations"
                     },
                     "bulk_receivers": {
                         "POST": "bulk/receivers", "DOC": "Configure a salvo of receiver activations"
                     }
                 },
                 url_methods={
                     "sender": {
                         "GET": ("single/senders/{nmosid}/{endpoint}", "Obtain IS-05 Sender state information"),
                         "PATCH": ("single/senders/{nmosid}/staged", "Set IS-05 Sender staged state")
                     },
                     "sender_sdp": {
                         "GETTEXT": ("single/senders/{nmosid}/transportfile", "Obtain IS-05 Sender state information")
                     },
                     "receiver": {
                         "GET": ("single/receivers/{nmosid}/{endpoint}", "Obtain IS-05 Receiver state information"),
                         "PATCH": ("single/receivers/{nmosid}/staged", "Set IS-05 Receiver staged state")
                     }
                 },
                 http_session=DEFAULT_SESSION
                 ):
    """\
    Provides access to the IS-05 Connection API on the unit.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(f'{base_url.rstrip("/")}/x-nmos/connection/v1.1', http_session)


class Settings(APIWrapperBase,
               url_properties={
                   "all": {"GET": "settings/all", "PATCH": "settings/all", "DOC": "nmos-cpp settings"}
               },
               http_session=DEFAULT_SESSION
               ):
    """\
    Provides access to the Settings API on the unit provided by nmos-cpp.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(f'{base_url.rstrip("/")}', http_session)


class APIVersion(ExtendedEnum):
    """\
    Enum to represent NMOS API version numbers
    """
    V1_0 = "v1.0"
    V1_1 = "v1.1"
    V1_2 = "v1.2"
    V1_3 = "v1.3"


@dataclasses.dataclass
class RegistrationDiscovery:
    """\
    Dataclass containing the configuration settings for a manually configured IS-04 Registration API.
    """
    automatic: bool
    hostname: str
    port: int
    api_version: APIVersion


class NmosClient(APIWrapperBase,
                 url_properties={
                     "config": {"GET": "nmos/config", "PUT": "nmos/config",
                                "DOC": "NMOS client configuration settings"},
                     "info": {"GET": "nmos/info", "DOC": "NMOS client status"}
                 },
                 http_session=DEFAULT_SESSION
                 ):
    """\
    Provides properties and methods for examining the state of and configuring the NMOS Client app and through various
    properties, the various NMOS APIs provided by nmos-cpp.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, parent: str, http_session: requests.Session = None):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._node = Node(f"http://{hostname}:3000", logger, hostname, http_session)
        self._connection = Connection(f"http://{hostname}:3000", logger, hostname, http_session)
        self._parent = parent
        self._settings = Settings(f"http://{hostname}:3000", logger, hostname, http_session)
        self._NMOS_RESTART = 4  # This should be enough time for the NMOS engine to restart but a better alternative is in development.

    @property
    def node(self) -> Node:
        """\
        Access the Node API object
        :return: Node object instance
        """
        return self._node

    @property
    def connection(self) -> Connection:
        """\
        Access the Connection API object
        :return: Connection object instance
        """
        return self._connection

    @property
    def settings(self) -> Settings:
        """\
        Access the Settings API object
        :return: Settings object instance
        """
        return self._settings

    @property
    def dual_interface_sender(self) -> bool:
        """\
        Return true if the NMOS Senders are in dual interface (2022-7) mode
        """
        if (sender_mode := self.config.get("senderMode", None)) is None:
            raise CoreException("Could not find senderMode key in NMOS client configuration")

        return True if sender_mode == "dualInterface" else False

    @dual_interface_sender.setter
    def dual_interface_sender(self, state: bool):
        """\
        Configure the NMOS Senders mode (true for dual interface, false for single interface)
        """
        self.config = {'senderMode': 'dualInterface' if state else 'singleInterface'}
        time.sleep(self._NMOS_RESTART)   # Trying to determine a reliable replacement for this (the NMOS engine needs to restart)

    @property
    def dual_interface_receiver(self) -> bool:
        """\
        Return true if the NMOS Receivers are in dual interface (2022-7) mode
        """
        if (receiver_mode := self.config.get("receiverMode", None)) is None:
            raise CoreException("Could not find receiverMode key in NMOS client configuration")

        return True if receiver_mode == "dualInterface" else False

    @dual_interface_receiver.setter
    def dual_interface_receiver(self, state: bool):
        """\
        Configure the NMOS Receivers mode (true for dual interface, false for single interface)
        """
        self.config = {"receiverMode": 'dualInterface' if state else 'singleInterface'}
        time.sleep(self._NMOS_RESTART)  # Trying to determine a reliable replacement for this (the NMOS engine needs to restart)

    @property
    def use_resource_prefix(self) -> bool:
        """\
        Determine if a custom resource prefix is used for the NMOS resources.
        """
        return True if self.config.get('useCustomResourcePrefix', None) == "enabled" else False

    @use_resource_prefix.setter
    def use_resource_prefix(self, enabled: bool):
        """\
        Set the NMOS resource prefix name
        """
        self.config = {'useCustomResourcePrefix': 'enabled' if enabled else 'disabled'}
        time.sleep(self._NMOS_RESTART)  # Trying to determine a reliable replacement for this (the NMOS engine needs to restart)

    @property
    def resource_prefix(self) -> str:
        """\
        Get or set the current customer resource prefix string.
        """
        return self.config['customResourcePrefix']

    @resource_prefix.setter
    def resource_prefix(self, prefix: str):
        """\
        Get or set the current customer resource prefix string.
        """
        self.config = {'customResourcePrefix': prefix}
        time.sleep(self._NMOS_RESTART)  # Trying to determine a reliable replacement for this (the NMOS engine needs to restart)

    @property
    def domain(self) -> str:
        """\
        Get the primary search domain setting. Setting a search domain enabled Unicast DNS operation.
        """
        return self.config['dnsSearchDomain']

    @domain.setter
    def domain(self, domain: str):
        """\
        Set the primary search domain setting. Setting a search domain enabled Unicast DNS operation.
        """
        self.config = {'dnsSearchDomain': domain}
        time.sleep(self._NMOS_RESTART)  # Trying to determine a reliable replacement for this (the NMOS engine needs to restart)

    @property
    def is09_config(self) -> bool:
        """\
        Determine if the NMOS engine is configured by IS-09
        """
        return True if self.config["getSystemConfigFromIS09"] == "enabled" else False

    @is09_config.setter
    def is09_config(self, enabled: bool):
        """\
        Determine if the NMOS engine is configured by IS-09
        """
        self.config = {'getSystemConfigFromIS09': "enabled" if enabled else "disabled"}

    @property
    def enabled(self):
        """\
        Determine if the NMOS engine is enabled
        """
        return True if self.config.get("nmosNode", None) == "enabled" else False

    def enable(self):
        """\
        Enable the NMOS engine
        """
        self.config = {"nmosNode": "enabled"}
        time.sleep(self._NMOS_RESTART)  # Trying to determine a reliable replacement for this (the NMOS engine needs to restart)

    def disable(self):
        """\
        Disable the NMOS engine
        """
        self.config = {"nmosNode": "disabled"}

    def restart(self):
        """\
        Restart the NMOS engine
        """
        self.disable()
        self.enable()

    def auto_registration(self, enabled: bool):
        """\
        Enable / disable automatic registration
        """
        self.config = {'autoRegistryDiscovery': 'enabled' if enabled else 'disabled'}

    @property
    def registration_discovery(self) -> RegistrationDiscovery:
        """\
        Get manual registration settings.
        """
        return RegistrationDiscovery(automatic=True if self.config['autoRegistryDiscovery'] == 'enabled' else False,
                                     hostname=self.config['registrationServiceAddress'],
                                     port=self.config['registrationServicePort'],
                                     api_version=APIVersion.from_value(self.config['registrationAPIVersion']))

    @registration_discovery.setter
    def registration_discovery(self, config: RegistrationDiscovery):
        """\
        Set the configuration for manually specifying an NMOS Registration endpoint API and disable automatic
        registry discovery.
        """
        self.config = {
            'autoRegistryDiscovery': 'enabled' if config.automatic else 'disabled',
            'registrationServiceAddress': config.hostname,
            'registrationServicePort': config.port,
            'registrationAPIVersion': config.api_version.value
        }
        time.sleep(self._NMOS_RESTART)  # Trying to determine a reliable replacement for this (the NMOS engine needs to restart)

    def get_receiver_id_from_name(self, tag_name: Union[DualRx, SingleRx]) -> Optional[str]:
        """\
        Obtain the NMOS ID UUID for a receiver whose tag matches that specified.
        """
        for receiver in self.node.receivers:
            receiver_tags = receiver.get('tags', {}).get('urn:x-nmos:tag:grouphint/v1.0', None)
            if tag_name.value.get(self._parent) in receiver_tags:
                return receiver.get('id', None)
        raise CoreException(f"Could not find a receiver for {tag_name.name}")

    def get_sender_id_from_name(self, tag_name: Union[DualTx, SingleTx]) -> Optional[str]:
        """\
        Obtain the NMOS ID UUID for a receiver whose tag matches that specified.
        """
        for sender in self.node.senders:
            sender_tags = sender.get('tags', {}).get('urn:x-nmos:tag:grouphint/v1.0', None)
            if tag_name.value.get(self._parent) in sender_tags:
                return sender.get('id', None)
        raise CoreException(f"Could not find a sender for {tag_name.name}")

    def get_sender_sdp(self, nmos_id: str) -> SDP:
        """\
        Obtain a parsed SPD object containing a sender's currently active data (senders can only have an active SDP
        accessed through their transportfile endpoint) where the sender is chosen by NMOS ID.
        """
        sdp_text, encoding = self.connection.get_sender_sdp(nmos_id)
        return SDP(sdp_text)

    def get_sender_sdp_by_name(self, tag_name: Union[DualTx, SingleTx]) -> SDP:
        """\
        Obtain a parsed SPD object containing a sender's currently active data (senders can only have an active SDP
        accessed through their transportfile endpoint) where the sender is chosen by the SingleTx and DualTx
        enumerations (that in turn use the BCP-002-01 grouphint tags).
        """
        sdp_text, encoding = self.connection.get_sender_sdp(self.get_sender_id_from_name(tag_name))
        return SDP(sdp_text)
