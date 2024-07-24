"""\
Provides classes for interacting with the timing features on Qx family devices.
"""

import logging
import requests
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION
from autolib.models.qxseries.eye import Eye


class Timing(APIWrapperBase,
             url_properties={
                 "reference": {"GET": "timing/reference",
                               "PUT": "timing/reference",
                               "DOC": "Get / set timing reference configuration."},
                 "devtools_input_timing": {"GET": "devtools/inputTiming?devtools=access",
                                           "PUT": "devtools/inputTiming?devtools=access",
                                           "DOC": "[Devtools Feature] Get / set input timing configuration."}
             },
             http_session=DEFAULT_SESSION
             ):
    """
    Get and set timing settings on devices supporting the Qx REST API.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, eye: Eye, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._eye = eye

    def configure(self, input_command, line_offset, offset_type, pixel_offset, timing_meter_range, reference_type):
        """
        inputCommand, lineOffset, offsetType, pixelOffset, timingMeterRange, referenceType
        """
        self._eye.devtools_eye_histogram = {
            'inputCommand': input_command,
            'inputMeasurementLineOffset': line_offset,
            'inputMeasurementOffsetType': offset_type,
            'inputMeasurementPixelOffset': pixel_offset,
            'referenceTimingMeterRange': timing_meter_range,
            'systemReferenceType': reference_type
        }
