"""\
Provides class for detecting and configuring combined boot mode and configuring LLDP support.
"""
import logging
import requests

from autolib.models.capability import DeviceCapability
from autolib.coreexception import CoreException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class GeneratorOutput(DeviceCapability):
    """\
    An enumeration to represent the generator output mode with the Rest API values for the enum values.
    """
    SDI = "sdi"
    IP_2022_6 = "2022-6"
    IP_2110 = "2110"


class AnalyserInput(DeviceCapability):
    """\
    An enumeration to represent the analyser input with the Rest API values for the enum values.
    """
    SDI = "sdi"
    IP = "ip"


class System(APIWrapperBase,
             url_properties={
                 "system_analyser_input": {
                     "GET": "system/analyserInput",
                     "PUT": "system/analyserInput",
                     "DOC": "Get / Set the analyser input."
                 },
                 "system_generator_output": {
                     "GET": "system/generatorOutput",
                     "PUT": "system/generatorOutput",
                     "DOC": "Get / Set the generator output."
                 },
                 "lldp_config": {
                     "GET": "system/lldp/config",
                     "PUT": "system/lldp/config",
                     "DOC": "Get / Set the LLDP configuration."
                 },
                 "lldp_info": {
                     "GET": "system/lldp/info",
                     "PUT": "system/lldp/info",
                     "DOC": "Get / Set the LLDP configuration."
                 }
             },
             http_session=DEFAULT_SESSION
             ):
    """
    Get and set system-wide configuration settings (combined boot options and LLDP).
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)

    @property
    def combined_mode_capable(self) -> bool:
        """\
        Return Trus if the device runs in combined mode.
        """
        try:
            _ = self.system_analyser_input
            return True
        except CoreException:
            return False

    @property
    def analyser_input(self) -> AnalyserInput:
        """\
        Return the analyser input in combined mode (SDI or IP)
        """
        if not self.combined_mode_capable:
            raise CoreException("Analyser input switching is not available")

        return AnalyserInput.from_value(self.system_analyser_input.get("input"))

    @analyser_input.setter
    def analyser_input(self, source: AnalyserInput):
        """\
        Set the analyser input in combined mode to SDI or IP (joint 2022-6 / 2110 mode)
        """
        if not self.combined_mode_capable:
            raise CoreException("Anaylser input switching is not available")

        self.system_analyser_input = {'input': source.value}

    @property
    def generator_output(self) -> GeneratorOutput:
        """\
        Get the generator output mode in combined mode (SDI, 2022-6 or 2110 mode)
        """
        if not self.combined_mode_capable:
            raise CoreException("Generator output selection is not available")

        return GeneratorOutput.from_value(self.system_generator_output.get("output"))

    @generator_output.setter
    def generator_output(self, mode: GeneratorOutput):
        """\
        Set the generator output mode in combined mode to SDI, 2022-6 or 2110 mode
        """
        if not self.combined_mode_capable:
            raise CoreException("Generator output selection is not available")

        self.system_generator_output = {'output': mode.value}

    @property
    def lldp(self) -> bool:
        """\
        Return True if LLDP support is enabled.
        """
        return self.lldp_config['enabled']

    @lldp.setter
    def lldp(self, enabled):
        """\
        Set the configuration for LLDP feature.
        """
        print(f"Setting to {enabled}")
        self.lldp_config = {"enabled": enabled}
