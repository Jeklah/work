"""\
Wrapper class for the Qx inputOutput portion of the Qx series API.
"""

from enum import unique
from typing import Tuple, Dict
import logging
import requests

from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION
from autolib.extendedenum import ExtendedEnum


class SDIInputOutputException(QxException):
    """
    Some inputOutput specific failure
    """
    pass


@unique
class SDIIOType(ExtendedEnum):
    """
    An enumeration of the valid SDI input / output types.
    """
    BNC = 'bnc'
    SFP = 'sfp'


@unique
class SDIOutputSource(ExtendedEnum):
    """
    An enumeration of the valid SDI input / output types.
    """
    OFF = "off"
    LOOPSDIIN = "loopSdiIn"
    GENERATOR = "generator"


class SDIInputOutput(APIWrapperBase,
                     url_properties={
                         "input_output": {"GET": "inputOutput", "DOC": "Get a list of input output categories"},
                         "sdi_in_io": {"GET": "inputOutput/sdiIn", "DOC": "Get a list of SDI input categories"},
                         "sdi_in_type": {
                             "GET": "inputOutput/sdiIn/inputType",
                             "PUT": "inputOutput/sdiIn/inputType",
                             "DOC": "Get a list of SDI input categories"},
                         "sdi_out_io": {"GET": "inputOutput/sdiOut", "DOC": "Get a list of SDI output categories"},
                         "sdi_out_bnc": {"GET": "inputOutput/sdiOut/bnc", "DOC": "Get a list of SDI BNC settings"},
                         "sdi_out_bnc_loop_bnc_in": {
                             "GET": "inputOutput/sdiOut/bnc/loopSdiBncIn",
                             "PUT": "inputOutput/sdiOut/bnc/loopSdiBncIn",
                             "DOC": "SDI BNC output loop in configuration"},
                         "sdi_out_type": {
                             "GET": "inputOutput/sdiOut/outputType",
                             "PUT": "inputOutput/sdiOut/outputType",
                             "DOC": "SDI output configuration. BNC or SFP IO can be configured here."},
                         "sdi_out_sfp": {"GET": "inputOutput/sdiOut/sfp", "DOC": "Get a list of SDI SFP settings"},
                         "status": {"GET": "inputOutput/status", "DOC": "Get the current input output status"}
                     },
                     url_methods={
                         "sdi_output_setting": {
                             "GET": ("inputOutput/sdiOut/{output_type}/sdiOutputSetting",
                                     "Set the output settings for the specified output type."),
                             "PUT": ("inputOutput/sdiOut/{output_type}/sdiOutputSetting",
                                     "Get the output settings for the specified output type."),
                         },
                         "generator_output_copy": {
                             "GET": ("inputOutput/sdiOut/{output_type}/generatorOutputCopy",
                                     "Set the generator output copy settings for the specified output type."),
                             "PUT": ("inputOutput/sdiOut/{output_type}/generatorOutputCopy",
                                     "Get the generator output copy settings for the specified output type."),
                         }
                     },
                     http_session=DEFAULT_SESSION
                     ):
    """\
    Provides access to the inputOutput API on the unit.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)

    @property
    def sdi_input(self) -> SDIIOType:
        """
        Get the input source used for analysis tools
        """
        return SDIIOType.from_value(self.sdi_in_type.get('type', None))

    @sdi_input.setter
    def sdi_input(self, source: SDIIOType):
        """
        Set the input source used for analysis tools
        :param source: SDIIOType representing the required input source
        """
        self.sdi_in_type = {"type": source.value}

    @property
    def sdi_output(self) -> SDIIOType:
        """
        Get the output destination used for analysis tools
        """
        return SDIIOType.from_value(self.sdi_out_type.get('type', None))

    @sdi_output.setter
    def sdi_output(self, source: SDIIOType):
        """
        Set the output destination used for analysis tools
        :param source: SDIIOType representing the required output source
        """
        self.sdi_out_type = {"type": source.value}

    def get_status(self):
        """\
        Get the current SDI IO status
        """
        return self.strip_api_fields(self.status)

    def get_sdi_output_source(self, output_connectors: SDIIOType) -> Dict[str, SDIOutputSource]:
        """\
        Get the current SDI output configuration for the specified connector type.

        :param output_connectors: The type of SDI output connector to examine (BNC or SFP)
        """
        return {k: SDIOutputSource.from_value(v) for k, v in self.strip_api_fields(self.get_sdi_output_setting(output_connectors.value)).items()}

    def set_sdi_output_source(self, output_connectors: SDIIOType, sdi_out_conf: Tuple[SDIOutputSource, ...]):
        """
        Configure the behaviour of SDI output spigots (Off / Generator / Loop SDI in)

        Supply a tuple containing 4 strings mapping to SDI out A, B, C, D to set SDI output function. Available options
        are "off" / "generator" / "loopSdiIn"

        :param output_connectors: The type of SDI output connector to configure (BNC or SFP)
        :param sdi_out_conf: Tuple containing 4 x SDIOutputSource objects. Must match the valid arguments noted above
        """
        if len(sdi_out_conf) != 4:
            raise SDIInputOutputException(f'When setting the SDI output source, four entries are required but {len(sdi_out_conf)} given.')

        sdi_output_body = {
            "sdiOutputA": sdi_out_conf[0].value,
            "sdiOutputB": sdi_out_conf[1].value,
            "sdiOutputC": sdi_out_conf[2].value,
            "sdiOutputD": sdi_out_conf[3].value
        }

        self.put_sdi_output_setting(output_connectors.value, sdi_output_body)

    def get_generator_output_copy_enabled(self, output_connectors: SDIIOType) -> bool:
        """\
        Get the generator output copy state for the specified connector type. Translate the Qx REST response into a
        boolean result.

        :param output_connectors: The connectors to configure
        """
        state = self.strip_api_fields(self.get_generator_output_copy(output_connectors.value)).get('enabled', None)
        if state is None:
            raise SDIInputOutputException(f'Attempt to get the generator output state for {output_connectors.value} connectors failed. State output was {str(state)}')
        return state

    def set_generator_output_copy_enabled(self, output_connectors: SDIIOType, state: bool):
        """\
        Set the generator output copy state for the specified connector type.

        :param output_connectors: The connectors to configure
        :param state: The state to set
        """
        self.put_generator_output_copy(output_connectors.value, {'enabled': state})
