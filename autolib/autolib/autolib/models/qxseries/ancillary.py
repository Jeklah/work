"""\
Provides classes for interacting with the Ancillary Inspector on Qx family devices.
"""

import requests
import logging
import warnings

from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class AncillaryInspector(APIWrapperBase,
                         url_properties={
                             "ancillary_status": {"GET": "analyser/ancillaryStatus",
                                                  "PUT": "analyser/ancillaryStatus",
                                                  "DOC": "Get / Set ancillary status"},
                             "ancillary_inspector": {"GET": "analyser/ancillaryInspector",
                                                     "PUT": "analyser/ancillaryInspector",
                                                     "DOC": "Get / Set ancillary inspector config"},
                         },
                         http_session=DEFAULT_SESSION
                         ):
    """
    Get and set ancillary inspector settings on devices supporting the Qx REST API.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)

    @property
    def status(self):
        """
        Return a dictionary containing current and historic ANC information, spit into currently + previously detected
        :return: Dictionary object containing "currently_detected" and "previously_detected" ANC information
        """
        r = self.ancillary_status
        anc_status_ret = {"currently_detected": [], "previously_detected": []}

        for data in r['ancStatus']:
            try:
                is_present = data["C-Pos"]["presence"]["present"]
            except KeyError:
                is_present = data["Y-Pos"]["presence"]["present"]

            if is_present:
                anc_status_ret["currently_detected"].append(data)
            else:
                anc_status_ret["previously_detected"].append(data)

        return anc_status_ret

    @property
    def trigger_only_on_errors(self):
        """
        Is the Ancillary Inspector set to only trigger on error conditions?
        """
        config = self.ancillary_inspector
        if config:
            try:
                return config["configData"]["errorTriggers"]["triggerOnlyOnErrors"]
            except KeyError:
                raise QxException(f"Could not obtain trigger on error status from Qx rest response")

    @trigger_only_on_errors.setter
    def trigger_only_on_errors(self, enable):
        """
        Enable or disable the trigger on errors only
        """
        self.ancillary_inspector = {"triggerOnlyOnErrors": enable}

    def setup_inspector(self, **kwargs):
        """
        Configure the ANC inspector for triggering and capture of specified ANC data
        Function will return True / False to indicate configuration success.

        Function can take a dictionary containing configuration data for the ANC inspector::

            config={
                trigger_only_on_errors: bool
                checksum_errors: bool
                dbn_errors: bool
                parity_errors: bool
                anc_gap_errors: bool

                hanc_vanc= "hanc" / "vanc" / "Both"
                identifier=(<identifier string ("custom" / "all")>, <sdid int>, <did int>)
                range=(<range_select string ("any" / "inside" / "outside")>,  <first_line int>, <last_line int>)
            }

        :param trigger_only_on_errors: Bool
        :param checksum_errors: Bool
        :param dbn_errors: Bool
        :param parity_errors: Bool
        :param anc_gap_errors: Bool
        :param hanc_vanc: String ("hanc", "vanc", "both")
        :param identifier: Tuple ((<identifier string ("custom" / "all")>, <sdid int>, <did int>))
        :param range: Tuple ((<range_select string ("any" / "inside" / "outside")>,  <first_line int>, <last_line int>))
        :param position: string ("yPos", "cPos", "both")
        :return:
        """
        warnings.warn("This method is deprecated, please do not use it in new developments.")

        config_body = {}

        # Configure triggers
        for param, value in kwargs.items():

            if param == "identifier":
                config_body.update({
                    "sdid": value[1],
                    "did": value[2],
                    "identifierSelect": value[0]
                })

            if param == "range":
                config_body.update({
                    "firstLine": value[1],
                    "lastLine": value[2],
                    "rangeSelect": value[0]  # "any" / "inside" / "outside"
                })

            if param == "trigger_only_on_errors":
                config_body["triggerOnlyOnErrors"] = value
            elif param == "checksum_errors":
                config_body["searchChecksumErrors"] = value
            elif param == "dbn_errors":
                config_body["searchDBNErrors"] = value
            elif param == "parity_errors":
                config_body["searchParityErrors"] = value
            elif param == "anc_gap_errors":
                config_body["searchAncGapErrors"] = value
            elif param == "hanc_vanc":
                config_body["hancVancSelect"] = value
            elif param == "position":
                config_body["yPosCPosSelect"] = value
            elif param == "subimage":
                config_body["subImageSearch"] = value

        self.ancillary_inspector = config_body

    def inspect(self, **kwargs):
        """
        Retrieve information for the ANC inspector. Kwargs are supplied to indicate the type of ANC data to return.
        ANC inspector info will be returned as a list containing each data type requested as individual element.

        :param captured_data: Bool
        :param raw_data: Bool
        :param found_in: Bool
        """
        warnings.warn("This method is deprecated, please do not use it in new developments.")

        current_config = self.ancillary_inspector
        return_list = []

        for param, value in kwargs.items():
            if param == "captured_data" and value is True:
                try:
                    return_list.append(current_config["capturedData"])
                except KeyError:
                    raise QxException(self._hostname + " - No captured data for identifier")

            elif param == "raw_data" and value is True:
                try:
                    return_list.append(current_config["capturedRawData"])
                except KeyError:
                    raise QxException(f'{self._hostname} - No raw data for identifier {current_config}')

            elif param == "found_in" and value is True:
                try:
                    return_list.append(current_config["foundIn"])
                except KeyError:
                    raise QxException(f'{self._hostname} - No found in data for identifier')
            else:
                raise QxException(f"{self._hostname} - data_type identifier used ({param}) is not recognised")

        return return_list

    def reset(self):
        """
        Reset the ANC inspector status
        """
        self.ancillary_status = {"reset": True}
