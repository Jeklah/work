"""\
Provides classes for interacting with the Eye features on Qx family devices.
"""

import logging
import requests
from typing import Tuple

from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class Eye(APIWrapperBase,
          url_properties={
              "eye_status": {"GET": "eye/status", "DOC": "Get the eye analyser status"},
              "eye_analysis_parameters": {"GET": "eye/analysisParameters",
                                          "PUT": "eye/analysisParameters",
                                          "DOC": "Get / set eye analysis parameters"},
              "devtools_eye_histogram": {"GET": "devtools/eyeHistogram?devtools=access",
                                         "PUT": "devtools/eyeHistogram?devtools=access",
                                         "DOC": "[Devtools Feature] Get / set eye histogram configuration."},

          },
          http_session=DEFAULT_SESSION
          ):
    """
    Get and set Eye settings on devices supporting the Qx REST API.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)

    def get_eye_dc_offset(self) -> Tuple[float, float, float]:
        """
        Returns a tuple containing eye min_voltage, max_voltage, dc_offset
        """
        eye_resp = self.eye_status
        max_voltage = eye_resp["maxVoltage_mV"] / 1000
        min_voltage = eye_resp["minVoltage_mV"] / 1000
        dc_offset = max_voltage + min_voltage
        return min_voltage, max_voltage, dc_offset

    def get_eye_rise_fall_times(self) -> Tuple[float, float, float]:
        """
        Returns a list containing eye rise, fall and delta times
        """
        eye_resp = self.eye_status
        rise_time = eye_resp["riseTime_ps"]
        fall_time = eye_resp["fallTime_ps"]
        delta = rise_time - fall_time
        return rise_time, fall_time, delta

    def get_eye_histogram_width(self) -> int:
        """
        Returns the eye histogram width
        """
        hist_width = self.devtools_eye_histogram
        return int(hist_width["eyeHistogramWidth"])

    def set_eye_number(self, number):
        """
        Set the number of eyes in the eye analyser histogram.
        :param: Number of eyes
        """
        self.devtools_eye_histogram = {
            "action": "setNumberOfEyes",
            "number": number
        }

    def set_jitter_comp_filter(self, enable):
        """\
        Enable / Disable the Jitter Eye Compensation Filter
        """
        self.devtools_eye_histogram = {
            "action": "setEyeJitterCompensationFilter",
            "enabled": "true" if enable else "false"
        }

    def set_jitter_filter(self, frequency):
        """
        Configure the Jitter Eye filter frequency
        """

        if frequency == 10:
            frequency = "10hz"
        elif frequency == 100:
            frequency = "100hz"
        elif frequency == 1000:
            frequency = "1khz"
        elif frequency == 10000:
            frequency = "10khz"
        elif frequency == 100000:
            frequency = "100khz"
        else:
            raise QxException(f'{self._hostname} - Invalid frequency value supplied: {frequency}')

        self.devtools_eye_histogram = {
            "action": "setJitterWindowFilterFrequency",
            "frequency": frequency
        }
