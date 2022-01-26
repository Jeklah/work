"""\
Provides classes for interacting with the signal analyser on Qx family devices.
"""

import datetime
import json
import time
import urllib.parse
import warnings

import jsonpointer
import requests

from test_system.models.qxseries.qxexception import QxException


class AnalyserException(QxException):
    """
    Failure to perform analysis of an incoming SDI video signal.
    """
    pass


class Analyser:
    """
    Get and set signal analyser settings on devices supporting the Qx REST API.
    """
    def __init__(self, baseurl, logger, hostname, http_session=None):
        self._baseurl = baseurl
        self.log = logger
        self.hostname = hostname

        # If a session is passed in use it, else don't use a session
        if http_session:
            self._http_session = http_session
        else:
            self._http_session = requests

    def get_analyser_status(self) -> tuple:
        """
        Return standard information for the analysed input on the Qx unit

        :return: List containing analysed standard information. False if no RX signal on the unit
        """
        response = requests.get(self._baseurl + "analyser/status")

        if response.status_code == 200:
            analyser_status = response.json()
            standard_data = analyser_status.get("standard", None)
            if standard_data:
                standard = standard_data.split(" ")
                return standard[0], urllib.parse.unquote(standard[1]), "_".join(standard[2:])
            else:
                raise AnalyserException(f'{self.hostname} - [Check wiring] Could not get standard data: {response.status_code}: {response.json().get("message", "No message")}')
        else:
            raise AnalyserException(f'{self.hostname} - [Check wiring] Could not get analyser status: {response.status_code}: {response.json().get("message", "No message")}')

    def get_analyser_datarate(self) -> float:
        """
        Returns the data rate of the standard currently being received by the unit

        :return: Float representation of the currently received standard's data rate
        """
        current_res, current_mapping, current_format = self.get_analyser_status()

        # @DUNC More cheese vicar? For now this will stay but it's a really bad way to use exceptions!
        # I also don't like the way that this is being fundamentally done. A regex would be better.
        try:
            standard_data_rate = float(current_format.split("_")[0].strip("G"))
        except ValueError:
            standard_data_rate = float(current_format.split("_")[1].strip("G"))

        return standard_data_rate

    def get_analyser_dataview(self):
        """
        Return values from the dataview windows at the active cursor postiton. Use with :func:
        `move_active_picture_cursor` to reposition the active cursor

        :return: Dictionary object containing dataview data
        """
        response = requests.get(self._baseurl + "analyser/dataview")

        if response.status_code == 200:
            dataview = response.json()
            data = {}
            for content in dataview["samples"]:
                content_dict = {content["content"]: content["data"]}
                data.update(content_dict)
            return data
        else:
            raise AnalyserException(f'{self.hostname} - Could not get the analyser dataview: {response.status_code}: {response.json().get("message", "No message")}')

    def verify_clock_divisor(self, **kwargs):
        """
        Return a boolean object used to verify if the SDI input spigot is utilising the correct clock divisor for the
        incoming standard's data rate

        :key threshold: Optional value allowing the data rate offset to be out by. Default = 0.2
        :return: Boolean value indicating success / failure
        """

        offset_threshold = kwargs.get("threshold", None)
        if not offset_threshold:
            self.log.warning(self.hostname + " - No offset threshold supplied, using default (+/- 0.2)")
            offset_threshold = 0.2

        current_aspect, current_colour, current_format = self.get_analyser_status()

        # @DUNC Potential race condition here - the datarate could change after the get_analyser_status call
        standard_data_rate = self.get_analyser_datarate()

        response = self._http_session.get(self._baseurl + "inputOutput/status")
        if response.status_code != 200:
            raise AnalyserException(f'{self.hostname} - Could not get inputOutput status : {response.status_code}: {response.json().get("message", "No message")}')

        io_data = response.json()

        # Verify the analysed data rate is within threshold for all spigots
        data_rate_fail_flag = False
        for spigot, _ in io_data["sdiIn"]["clockFrequency"].items():
            analysed_data_rate = round(float(io_data["sdiIn"]["dataRate"][spigot].split("G")[0]), 2)
            data_rate_offset = standard_data_rate - analysed_data_rate

            # Verify the analysed data rate is correct for current standard on all SDI inputs
            if -offset_threshold <= data_rate_offset <= offset_threshold:
                self.log.info(f'{self.hostname} - {spigot} data rate ({analysed_data_rate} GHz) is within threshold of +/-{offset_threshold} of analysed standard ({standard_data_rate})')
            else:
                self.log.error(f'{self.hostname} - {spigot} data rate ({analysed_data_rate} GHz) is NOT within threshold of +/-{offset_threshold} of analysed standard ({standard_data_rate})')
                data_rate_fail_flag = True

        # Verify clock divisor for all spigots
        clock_divisor_fail_flag = False
        for spigot, _ in io_data["sdiIn"]["dataRate"].items():
            clock_divisor = float(io_data["sdiIn"]["clockFrequency"][spigot])

            match = []
            for x in ["psf", "p", "i"]:
                if x in current_aspect and x not in match:
                    match.append(x)
            if len(match) > 1:
                self.log.warning(f'{self.hostname} - Frame type has multiple matches... probably psf standard')

            frame_type = match[0]

            frame_rate = float(current_aspect.split(frame_type)[1])

            if frame_rate % 1 != 0:
                expected_divisor = 1.001
            else:
                expected_divisor = 1.000

            if clock_divisor == expected_divisor:
                self.log.info(f'{self.hostname} - Clock divisor ({clock_divisor}) is correct for the current frame rate ({frame_rate})')
            else:
                self.log.error(f'{self.hostname} - Clock divisor ({clock_divisor}) is incorrect for current frame rate ({frame_rate})')
                clock_divisor_fail_flag = True

        if data_rate_fail_flag or clock_divisor_fail_flag:
            return False
        else:
            return True

    def move_active_picture_cursor(self, **kwargs):
        """
        Set active picture cursor to specified coordinates (using line and pixel keyword argument) or use increments
        (using the incr keyword argument)

        :key line: Set the source line value, int - Note: pixel must also be specified
        :key pixel: Set the source position pixel, int - Note: line must also be specified
        :key incr: Tuple object containing start and finish position of x / y coordinates - No not specify line or pixel
        :return: bool
        """
        if kwargs.get("incr"):
            increment = kwargs.get("incr")
            for i in range(increment[0], increment[1]):
                self.move_active_picture_cursor(line=i, pixel=i)
                time.sleep(1)
            return True

        source_line = kwargs.get("line", None)
        source_pixel = kwargs.get("pixel", None)
        if not source_line and not source_pixel:
            raise AnalyserException('If incr keyword argument is not specified, line and pixel must be.')

        # Get the current cursor position
        response = self._http_session.get(self._baseurl + "analyser/cursors/activePictureCursor")
        if response.status_code != 200:
            raise AnalyserException(f'{self.hostname} - Could not get activePictureCursor status : {response.status_code}: {response.json().get("message", "No message")}')

        current_position = response.json()
        current_line = current_position["activePictureLine"]
        current_pixel = current_position["activePicturePixel"]
        self.log.info(f'{self.hostname} - Current cursor location: line: {current_line} pixel: {current_pixel}')

        cursor_data = {
            "sourcePositionLine": 0,
            "sourcePositionPixel": 0,
            "activePictureLine": source_line,
            "activePicturePixel": source_pixel
        }

        response = self._http_session.put(self._baseurl + "analyser/cursors/activePictureCursor", json=cursor_data)
        if response.status_code == 200:
            self.log.info(f'{self.hostname} - New cursor location: line: {current_line} pixel: {current_pixel}')
            return True
        else:
            return False

    @property
    def max_audio_groups(self):
        """
        Calculate the maximum number of audio groups allowed for the current generated standard on unit
        :return Int:
        """
        current_standard = self.parse_analyser_status(self.get_analyser_status())

        if current_standard["type"]["data_rate_Gb"] == 1.5:
            max_channels = 16
        else:
            max_channels = 32

        if current_standard["resolution"][0] in ["4096", "2048"]:
            if current_standard["frame_rate"]["value"] in [30, 29.97, 60, 59.94]:
                max_channels = max_channels / 2
            if current_standard["type"]["level"] == "B":
                max_channels = max_channels / 2

        return int(max_channels / 4)

    def get_audio(self, data, channel_number=None):
        """
        Return data on incoming audio

        :param data: String indicating the type of information to return. <"level"> or <"phase">
        :param channel_number: Integer to specify the target channel number to return data for. If None, all channels are returned
        :return: Dictionary object containing <level> or <phase> information for target (all) incoming audio channels
        """
        response = self._http_session.get(self._baseurl + "analyser/audioMeter")

        if response.status_code == 200:
            audio_data = response.json()

            if data == "level":
                audio_ret = audio_data["audioLevels"]
            elif data == "phase":
                audio_ret = audio_data["audioPhase"]
            else:
                raise QxException(f'{self.hostname} - No data type indicator supplied. Cannot parse audio data.')

            if not channel_number:
                self.log.warning(
                    f'{self.hostname} - No channel number supplied, returning audio meter data for all active channels')
                return audio_ret
            elif channel_number:
                for channel_data in audio_ret:
                    try:
                        current_channel = [int(channel_data["channel"])]
                    except ValueError:
                        current_channel = [int(x) for x in channel_data["channel"].split("-")]

                    if int(channel_number) in current_channel:
                        self.log.info(f'{self.hostname} - Returning {data} data for channel {channel_number}')
                        return channel_data
        else:
            raise AnalyserException(f'{self.hostname} - Could not access audio meters: {response.status_code}: {response.json().get("message", "No message")}')

    def expected_video_analyser(self, exp_aspect, exp_colour, exp_format):
        """

        """
        response = self._http_session.get(self._baseurl + "analyser/status")
        if response.status_code != 200:
            raise AnalyserException(
                f'{self.hostname} - Could not get analyser status: {response.status_code}: {response.json().get("message", "No message")}')

        analyser_status = response.json()
        standard_data = analyser_status.get("standard", None)

        if not standard_data:
            raise AnalyserException(
                f'{self.hostname} - Could not get standard data from analyser status: {response.status_code}: {response.json().get("message", "No message")}')

        result = ""
        try:
            result = str(standard_data).split(" ")
            actual_aspect = result[0]
            actual_colour = result[1]
            actual_format = "_".join(result[2:])
        except IndexError as err:
            raise QxException(f"{self.hostname} - Analyser input is not formatted correctly... is the analyser receiving an input? - {str(err)}")

        if actual_aspect != exp_aspect:
            self.log.warning(f'{self.hostname} - Expected aspect does not match. Expected: {exp_aspect} Actual: {actual_aspect}')
            return False
        elif actual_colour != exp_colour:
            self.log.warning(f'{self.hostname} - Expected colour code does not match. Expected: {exp_colour} Actual: {actual_colour}')
            return False
        elif actual_format != exp_format:
            self.log.warning(f'{self.hostname} - Expected format does not match. Expected: {exp_format} Actual: {actual_format}')
            return False
        else:
            self.log.info(f'{self.hostname} - Analyser read: {actual_aspect}, {actual_colour}, {actual_format}')
            return True

    # @DUNC Lots of work to do here :(
    # TODO: Gamut data is not parsed correctly... make it so!
    def parse_analyser_status(self, standard):
        """
        Take the output of :func:`get_analyser_status` and output dictionary of parsed values.
        :param standard: Output of get_analyser_status
        .. Return dictionary format::

            {
                "resolution": [x (int), y (int)]
                "frame_rate": {
                    "value": int,
                    "unit": string
                },
                "colour": string,
                "bit_depth": [],
                "type": {
                    "data_rate_Gb": int,
                    "level": string
                    "link_number": int,
                    "gamut": string
                    "misc": []
                },
                "gamut": {
                    "value": int,
                    "decimator": None
                },
            }

        Usage example::

            unit_1 = make_qx(hostname="qx-020001")
            unit_1.parse_analyser_status(unit_1.get_analyser_status())
            # Which is the same as
            unit_1.parse_analyser_status(['3840x2160p50', 'YCbCr:422:10', 'DL_6G_2-SI_HLG_Rec.2020'])

        :param standard: List containing information on the currently received standard (Output of Qx.get_analyser_status)
        :return: Dictionary object containing parsed information of the standard currently being received

        """
        warnings.warn("The parse_analyser_status method of Analyser is going to be rewritten. Do not use.",
                      DeprecationWarning)

        # Return False if input is incorrect
        try:
            if not len(standard) == 3:
                print("Incorrectly formatted input.")
                print(standard)
                return False
        except TypeError:
            print('Incoming signal cannot be recognised on analyser unit')
            return False

        # Create return data type
        parsed_dict = {}

        # Get current analyser standard
        resolution, colour, gamut = standard
        split_gamut = gamut.split("_")
        # ========== Parse resolution + frame data
        match = []
        for x in ["psf", "p", "i"]:
            if x in resolution and x not in match:
                true_res = resolution.split(x)[0]

                parsed_dict["frame_rate"] = {
                    "value": float(resolution.split(x)[1]),
                    "unit": x
                }

                parsed_dict["resolution"] = true_res.split("x")

                break

        # ============ Parse gamut data
        try:
            parsed_dict["gamut"] = {
                "value": split_gamut.pop(-1),
                "decimator": "-" if split_gamut[-1] != "2-SI" or "SQ" else split_gamut.pop(-1)
            }
        except IndexError as err:
            print(err)
            return False
        # =========== Parse type data

        try:
            standard_data_rate = float(split_gamut[0].strip("G"))
            multilink_tag = 1
            # print("Removed %s from list" % split_gamut.pop(0))
        except ValueError:
            standard_data_rate = float(split_gamut[1].strip("G"))
            # print("Removed %s from list" % split_gamut.pop(1))
            multilink_tag = 4 if gamut.split("_")[0] == "QL" else 2
            # print("Removed %s from list" % split_gamut.pop(0))
        except IndexError as err:
            self.log.error(f"Got index error: {err}")
            self.log.error(f"Split gamut variable: {split_gamut}")
            self.log.error(f"Parsed dict: {parsed_dict}")
            self.log.error(f"All standard variables: {resolution}, {colour}, {gamut}")
            raise QxException("")

        parsed_dict["type"] = {
            "data_rate_Gb": standard_data_rate,
            "level": "B" if "B" in split_gamut else "A",
            "link_number": multilink_tag,
            "misc": [x for x in split_gamut]
        }

        # ======== Parse colour data

        colour_space, mapping_ratio, bit_depth = colour.split(":")

        parsed_dict["colour"] = colour_space
        parsed_dict["bit_depth"] = [mapping_ratio, bit_depth]

        return parsed_dict

    def get_prbs(self, mode=False, reset=False):
        """
        Return available data related to the PRBS analysis tool

        .. Return data structure::
            {
                state: str,
                analysis_time: datetime
                spigots: {
                    sdiInA: {
                        bitErrorRate: int,
                        clockRate: string,
                        okTime: string,
                        totalErrors: int,
                        totalRx_Gb: int
                    },
                    sdiInB: {...},
                    sdiInC: {...},
                    sdiInD: {...}
                }
            }

        Return object is not JSON serializable as it contains a datetime object, it can still be accessed as you would
        expect to access JSON / dict data.

        :param mode: PRBS mode to use during analysis. ["Disable", "PRBS-7", "PRBS-9", "PRBS-15", "PRBS-23", "PRBS-31"]
        :param reset: Optional. If True, reset the PRBS analysis counters

        """
        warnings.warn("The get_prbs method of Analyser is going to be rewritten. Do not use.",
                      DeprecationWarning)

        analyser_prbs_path = self._baseurl + "analyser/prbs"

        if reset:
            self.log.info(f'{self.hostname} - Resetting PRBS analysis counters')
            response = self._http_session.put(analyser_prbs_path, json={"action": "reset"})
            if response.status_code != 200:
                raise AnalyserException(
                    f'{self.hostname} - Failed to reset PRBS counters: {response.status_code}: {response.json().get("message", "No message")}')

        response = self._http_session.get(analyser_prbs_path)
        if response.status_code != 200:
            raise AnalyserException(
                f'{self.hostname} - Failed to get PRBS status: {response.status_code}: {response.json().get("message", "No message")}')

        analyser_prbs_data = response.json()

        # Validate current state of PRBS analysis
        if analyser_prbs_data["receiveMode"] != mode:
            self.log.info(f'{self.hostname} - PRBS mode does not match [{mode}]. Changing from {analyser_prbs_data["receiveMode"]} to {mode}')
            response = self._http_session.put(analyser_prbs_path, json={"receiveMode": mode})
            if response.status_code != 200:
                raise AnalyserException(
                    f'{self.hostname} - Failed to set PRBS mode: {response.status_code}: {response.json().get("message", "No message")}')

            time.sleep(1)
            response = self._http_session.get(analyser_prbs_path)
            if response.status_code != 200:
                raise AnalyserException(
                    f'{self.hostname} - Failed to get PRBS status: {response.status_code}: {response.json().get("message", "No message")}')

            analyser_prbs_data = response.json()

        # Convert analysis time data to datetime object
        # Get raw data (API returns string format)
        analysis_time_raw = analyser_prbs_data["analyserTime"]

        # Convert the sting time representation into datetime object
        # Split data into H:M:s format
        analysis_time_raw = analysis_time_raw.split(" ")

        no_of_hrs, no_of_min, no_of_sec = 0, 0, 0
        for x in analysis_time_raw:
            if x.endswith("h"):
                no_of_hrs = int(x.split("h")[0])
            if x.endswith("m"):
                no_of_min = int(x.split("m")[0])
            if x.endswith("s"):
                no_of_sec = int(x.split("s")[0])

        analysis_time = datetime.time(hour=no_of_hrs, minute=no_of_min, second=no_of_sec)

        # Append any spigot data to the return dict
        spigot_analysis = {}
        for key in analyser_prbs_data.keys():
            if key in ["sdiInA", "sdiInB", "sdiInC", "sdiInD"]:
                spigot_analysis.update({key: analyser_prbs_data[key]})

        return {
            "state": analyser_prbs_data["receiveMode"],
            "analysis_time": analysis_time if analysis_time else None,
            "spigots": spigot_analysis
        }

    # TODO: Needs logic comments... show your working!!
    def get_crc_analyser(self):
        """
        @DUNC This is an original method that not only gets the analyser/detail endpoint but performs some processing
              on it - which to my mind would need this to be broken up in two methods with the response processing in
              a method whose name describes it's purpose.
        """
        warnings.warn("The get_crc_analyser method of Analyser is going to be rewritten. Do not use.",
                      DeprecationWarning)

        response = None
        try:
            response = requests.get(self._baseurl + "analyser/detail")
            crc_resp = response.json()
        except json.decoder.JSONDecodeError:
            if response and response.status_code == 204:
                raise QxException(f'No content in the GET to URL {self._baseurl + "analyser/detail"}. The analyser may not be receiving an input')
            else:
                response_message = response.content.strip("\n")
                raise QxException(f'Could not GET analyser/detail: status {response.status_code} - {response_message}')

        if crc_resp["status"] != 200:
            self.log.error(f'{self.hostname} - Unable to retrieve CRC analysis: {format(crc_resp["status"])} - {crc_resp["message"]}')
        else:
            crc = []
            multilink_crc = []

            # Iterate through subimages
            for link in crc_resp["links"][1:]:
                # Reset flag to != "crc" for each entry at stub root level
                flag = ""

                while flag != "crc":
                    # Set flag variable to current "rel". Could be "linkA/B", "subImage1/2/3/4", or "crc"
                    flag = link["rel"]
                    # If flag is anything other than "crc", make the request to next level of detail stub
                    resp = requests.get(link["href"]).json()

                    try:
                        # Iterate through next level of stub links
                        for link in resp["links"][1:]:
                            # Set flag to current "rel" value. Could be "subImage1/2/3/4" or "crc"
                            flag = link["rel"]

                            # If flag is not "crc". Current standard is B level
                            if flag != "crc":
                                resp = requests.get(link["href"]).json()

                                flag = resp["links"][1]["rel"]

                                link = resp["links"][1]
                                multilink_crc.append(requests.get(link["href"]).json())
                    except KeyError:
                        print('Link: %s\t Flag: %s\t Resp: %s' % (str(link), str(flag), str(resp)))

                if len(multilink_crc) > 1:
                    crc = multilink_crc
                else:
                    crc.append(requests.get(link["href"]).json())

            return crc

    def validate_crc(self):
        """
        Does the CRC analyser indicate any problems?
        @DUNC This is another leftover which to my mind is too specific.
        """
        warnings.warn("The validate_crc method of Analyser is going to be rewritten. Do not use.",
                      DeprecationWarning)

        crc_data = self.get_crc_analyser()
        pass_flag = True

        for img_crc in crc_data:
            print(json.dumps(img_crc, indent=4))

            # Get the name of current subimage
            name = img_crc["links"][0]["href"].split("/")[-2:][0]

            if name == "detail":
                name = "video stream"

            if img_crc["ancErrorCountYPos"] or img_crc["ancErrorCountCPos"] > 0:
                pass_flag = False
                self.log.error(self.hostname + " - Detected ANC error(s) on {}".format(name))
                self.log.error(self.hostname + " - ANC Y Pos: {} ANC C Pos: {}".format(img_crc["ancErrorCountYPos"],
                                                                                       img_crc["ancErrorCountCPos"]))
                self.log.error(self.hostname + " - Time since error: {}s".format(float(img_crc["okTime_ms"]/1000)))

            if img_crc["errorCountYPos"] or img_crc["errorCountCPos"] > 0:
                pass_flag = False
                self.log.error(self.hostname + " - Detected error(s) on {}".format(name))
                self.log.error(self.hostname + " - Y Pos err: {} ANC C Pos err: {}".format(img_crc["errorCountYPos"],
                                                                                           img_crc["errorCountCPos"]))
                self.log.error(self.hostname + " - Time since error: {}s".format(float(img_crc["okTime_ms"]/1000)))

        return pass_flag

    def reset_crc(self):
        """
        Reset CRC error counters and timers
        """
        reset_crc = {
            "action": "reset",
            "ignoreCrcOnSwitchLines": "enable"
        }

        response = requests.put(self._baseurl + "analyser/crcSummary", json=reset_crc)
        if response.status_code == 200:
            self.log.info(f'{self.hostname} - CRC error counter has been reset')
        else:
            raise AnalyserException(f'{self.hostname} - Unable to reset CRC counter": {response.status_code}: {response.json().get("message", "No message")}')

    def get_crc_summary(self):
        """
        Get a dictionary containing the current CRC analyser summary
        """
        response = requests.get(self._baseurl + "analyser/crcSummary")
        if response.status_code == 200:
            return response.json()
        else:
            raise QxException(f'{self.hostname} - Could not get CRC summary: {response.status_code}: {response.json().get("message", "No message")}')

    def get_crc_last_input_failure(self):
        """
        Get the time since the last input failure.
        """
        response_data = self.get_crc_summary()
        if response_data:
            time_since_failure = response_data.get("timeSinceInputFailure", None)
            return time_since_failure if time_since_failure else False
        else:
            raise QxException(
                f'{self.hostname} - No response body returned from analyser/crcSummary')

    @property
    def cable_length(self):
        """
        Obtain the measured cable length values as a dictionary
        """
        response = requests.get(self._baseurl + "analyser/cableLength")

        if response.status_code == 200:
            return response.json()
        else:
            raise QxException(f'{self.hostname} - Could not get cable length: {response.status_code}: {response.json().get("message", "No message")}')

    def cable_type(self, cable: str="belden_8281"):
        """
        Set the cable type
        :param cable: Cable type string
        :return: True if successfully configured else False
        """
        data = {"cableType": cable}
        response = requests.put(self._baseurl + "analyser/cableLength", json=data)

        if response.status_code == 200:
            self.log.info(f"{self.hostname} - Cable type successfully set to {cable}")
        else:
            raise QxException(f'{self.hostname} - Unable to set cable type to {cable}: {response.status_code}: {response.json().get("message", "No message")}')

    @property
    def loudness(self):
        """
        Return the loudness configuration as a dictionary.
        :return dictionary
        """
        response = requests.get(f'{self._baseurl}/analyser/loudness/config')

        if response.status_code == 200:
            return response.json()
        else:
            raise QxException(f'{self.hostname} - Could not get loudness configuration: {response.stauts_code}: {response.json().get("message", "No message")}')

    @loudness.setter
    def loudness(self, loudness_config):
        """
        Sets the configuration for loudness monitoring.
        :param loudness_config: Dictionary containing the configuration for loudness monitor.
        """
        if loudness_config.keys() == self.loudness.keys():
            response = requests.put(f'{self._baseurl}/analyser/loudness/config', json=loudness_config)
            if response.status_code == 200:
                self.log.info(f'{self.hostname} - Set Loudness Monitor Configuration.')
                self.log.info(f'{self.hostname}: Loudness Monitor configuration set {loudness_config}')
            else:
                raise QxException(f'{self.hostname} - Failed to set Loudness Monitor Configuration')
        else:
            raise QxException(f'{self.hostname} - Loudness Monitor Key Check failed: {loudness_config.keys()} does not match {self.loudness.keys()}')

