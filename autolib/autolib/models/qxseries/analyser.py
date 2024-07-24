"""
Provides classes for interacting with the signal analyser on Qx family devices.
"""

import datetime
import enum
import logging
import re
import time
import urllib.parse
import warnings
from dataclasses import dataclass, field
from typing import List, Dict, Union

import requests

from autolib.coreexception import CoreException
from autolib.extendedenum import ExtendedEnum
from autolib.models.qxseries.prbs import PRBSMode, PRBSResponse
from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.input_output import SDIInputOutput
from autolib.models.qxseries.session import DEFAULT_SESSION


class AnalyserException(QxException):
    """
    An Exception subclass that represents some Analyser specific failure.
    """
    pass


@enum.unique
class AudioData(ExtendedEnum):
    """\
    Audio data type enumeration used to select information in various audio methods.
    """
    LEVEL = 'audioLevels'
    PHASE = 'audioPhase'
    BALLISTICS = 'ballistics'


@enum.unique
class AudioMeter(ExtendedEnum):
    """\
    Audio metering methods.
    """
    PPM_TYPE_I = 'PPM Type I'
    PPM_TYPE_II = 'PPM Type II'
    VU = 'Vu'
    VUFR = 'VuFr'
    FAST = 'Fast'


@enum.unique
class FrameType(ExtendedEnum):
    """\
    Frame type (interlaced, progressive, PSF)
    """
    INTERLACED = 'i'
    PROGRESSIVE = 'p'
    PSF = 'psf'


@dataclass
class Resolution:
    """\
    Active picture area resolution in pixels.
    """
    width: int = 0
    height: int = 0


@dataclass
class PixelComponent:
    """\
    Pixel component type - used for representing (for example) Y in YCbCr. YCbCr:422 would be represented as
    three Pixel Component objects, PixelComponent('Y', 4), PixelComponent('Cb', 2), PixelComponent('Cr', 2)
    """
    component: str = ''
    samples: int = 0


@dataclass
class PixelFormat:
    """\
    Pixel channel and bit depth info
    """
    depth: int
    components: list = field(default_factory=list)

    def __repr__(self):
        return f"{''.join([x.component for x in self.components])}:{''.join([str(x.samples) for x in self.components])}:{str(self.depth)}"


@dataclass
class ParsedStandard:
    """\
    A dataclass that provides a convenient means to extract all of the details from the string provided in the response
    from the analyser/status API call.
    """
    data_rate: float = 0.0
    format: Union[str, None] = None
    gamut: str = ''
    links: int = 0
    level: Union[str, None] = None
    colorimetry: Union[str, None] = None
    pixel_format: PixelFormat = PixelFormat(0, [])
    resolution: Resolution = Resolution(0, 0)
    frame_type: FrameType = FrameType.PROGRESSIVE
    frame_rate: float = 0.0

    def __init__(self, standard: str):
        """\
        Take the output of `analyser/status` and configure the class members to reflect the various attributes.

        :param standard: Output of `analyser/status` dictionary
        """

        if not standard:
            raise CoreException(f'Empty string or None supplied to ParsedStandard: {standard}')

        standard_components = standard.split(" ")
        resolution, colour, gamut = standard_components[0], urllib.parse.unquote(standard_components[1]), "_".join(
            standard_components[2:])
        self._original_resolution = standard_components[0]
        self._original_colour = standard_components[1]
        self._original_gamut = " ".join(standard_components[2:])
        self._status_repr = standard

        res_regex = r'(?P<width>\d{3,4})x(?P<height>\d{3,4})(?P<frame>psf|i|p)(?P<rate>(\d|\.)+)'
        match = re.search(res_regex, resolution)
        if match:
            self.resolution = Resolution(width=int(match.group('width')), height=int(match.group('height')))
            self.frame_type = FrameType.PROGRESSIVE if match.group(
                'frame') == 'p' else FrameType.INTERLACED if match.group('frame') == 'i' else FrameType.PSF
            self.frame_rate = float(match.group('rate'))

        format_regex = r'(?P<components>[A-Za-z]+)\:(?P<samples>\d{3,4})\:(?P<bit_depth>\d{1,2})'
        match = re.search(format_regex, colour)
        if match:
            self.pixel_format.depth = int(match.group('bit_depth'))
            self.pixel_format.components = []
            comp_match = re.findall(r'[A-Z][a-z]*', match.group('components'))
            if comp_match:
                for component, samples in zip(comp_match, match.group('samples')):
                    self.pixel_format.components.append(PixelComponent(component=component, samples=int(samples)))

        re_links = r'((?P<links>(QL|DL))_)*'
        re_rate = r'((?P<data_rate>[0-9\.]+)G)_'
        re_level = r'((?P<level>(A|B))_)*'
        re_format = r'((?P<format>(SQ|2\-SI))_)*'
        re_colorimetry = r'((?P<colorimetry>(HLG|PQ|SDR-TV|S-Log3))_)*'
        re_gamut = r'(?P<gamut>Rec\.709|Rec\.2020)'
        gamut_regex = f'{re_links}{re_rate}{re_level}{re_format}{re_colorimetry}{re_gamut}'
        match = re.search(gamut_regex, gamut)

        if match:
            self.data_rate = float(match.group('data_rate'))
            self.format = match.group('format')
            self.gamut = match.group('gamut')
            self.links = 4 if match.group('links') == 'QL' else 2 if match.group('links') == 'DL' else 1
            self.level = match.group('level')
            self.colorimetry = match.group('colorimetry') or "SDR"

    @property
    def api_resolution(self):
        """\
        Returns the original 'resolution' field of a standard as per the Qx Rest API.
        """
        return self._original_resolution

    @property
    def api_colour(self):
        """\
        Returns the original 'colour' field of a standard as per the Qx Rest API.
        """
        return self._original_colour

    @property
    def api_gamut(self):
        """\
        Returns the original 'gamut' field of a standard as per the Qx Rest API.
        """
        return self._original_gamut

    @property
    def status_repr(self):
        """\
        Give the Qx Rest API representation of the standard.
        """
        return self._status_repr


class Analyser(APIWrapperBase,
               url_properties={
                   "ancillary_inspector": {
                       "GET": "analyser/ancillaryInspector",
                       "PUT": "analyser/ancillaryInspector",
                       "DOC": "Get / Set the ancillary Inspector configuration"
                   },
                   "ancillary_status": {
                       "GET": "analyser/ancillaryStatus",
                       "PUT": "analyser/ancillaryStatus",
                       "DOC": "Get / Configure the ancillary status"
                   },
                   "audio_meter": {
                       "GET": "analyser/audioMeter",
                       "PUT": "analyser/audioMeter",
                       "DOC": "Get / Configure the Audio meter status"
                   }
               },
               http_session=DEFAULT_SESSION
               ):
    """\
    Provides access to the Analyser features on the Qx series that are shared between operation modes.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session, sdi_io: SDIInputOutput):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._sdi_io = sdi_io
        self._st2110 = ST2110Analyser(base_url, logger, hostname, http_session)
        self._sdi = SdiAnalyser(base_url, logger, hostname, http_session, sdi_io)
        self._st2022_6 = ST20226Analyser(base_url, logger, hostname, http_session)

    @property
    def st2110(self):
        """\
        Get a reference to the SMPTE 2110 API wrapper class.
        """
        return self._st2110

    @property
    def sdi(self):
        """\
        Get a reference to the SDI API wrapper class.
        """
        return self._sdi

    @property
    def st2022_6(self):
        """\
        Get a reference to the ST2022-6 API wrapper class
        """
        return self._st2022_6

    @property
    def max_audio_groups(self) -> int:
        """
        Calculate the maximum number of audio groups allowed for the current generated standard on unit

        :return: Maximum number of audio group
        """
        standard = ParsedStandard(self.sdi.analyser_status.get('standard', None))

        max_channels = 16 if standard.data_rate == 1.5 else 32

        if standard.resolution.width in ["4096", "2048"]:
            if standard.frame_rate in [30, 29.97, 60, 59.94]:
                max_channels = max_channels // 2
            if standard.level == "B":
                max_channels = max_channels // 2

        return max_channels // 4

    def get_audio(self, data: AudioData, channel_number: int = None) -> dict:
        """
        Return information on incoming audio.

        :param data: AudioData value indicating the type of information to return.
        :param channel_number: Integer to specify the target channel number to return data for. If None, all channels are returned
        :return: Dictionary containing <level> or <phase> information for target (all) incoming audio channels
        """

        try:
            audio_data = self.audio_meter
        except CoreException as e:
            response = e.args[0].get("response", None)
            if response:
                raise AnalyserException(
                    f'{self._hostname}: {response.status_code} - {response.error_message}')
            else:
                raise AnalyserException(f'{self._hostname}: No response from request to obtain audio status.')

        audio_ret = audio_data[data.value]

        if not channel_number:
            self.log.warning(
                f'{self._hostname} - No channel number supplied, returning audio meter data for all active channels')
            return audio_ret
        else:
            for channel_data in audio_ret:
                try:
                    current_channel = [int(channel_data["channel"])]
                except ValueError:
                    current_channel = [int(x) for x in channel_data["channel"].split("-")]

                if int(channel_number) in current_channel:
                    self.log.info(f'{self._hostname} - Returning {data} data for channel {channel_number}')
                    return channel_data


@enum.unique
class CableType(ExtendedEnum):
    """\
    Enumeration of the various cable types supported by the Qx cable length algorithms
    """
    BELDEN_8281 = 'belden_8281'
    BELDEN_1505 = 'belden_1505'
    BELDEN_1694A = 'belden_1694a'
    BELDEN_1855A = 'belden_1855a'
    CANARE_L5CFB = 'canare_l5cfb'
    IMAGE_1000 = 'image_1000'


class SdiAnalyser(APIWrapperBase,
                  url_properties={
                      "analyser_status": {
                          "GET": "analyser/status",
                          "DOC": "Get the SDI analyser status"
                      },
                      "analyser_detail": {
                          "GET": "analyser/detail",
                          "DOC": "Get the SDI analyser detail endpoint"
                      },
                      "cable_length": {
                          "GET": "analyser/cableLength", "PUT": "analyser/cableLength",
                          "DOC": "Get / Configure the SDI Cable length analysis"
                      },
                      "crc_summary": {
                          "GET": "analyser/crcSummary",
                          "PUT": "analyser/crcSummary",
                          "DOC": "Get the SDI CRC Summary"
                      },
                      "cursors_active_picture_cursor": {
                          "GET": "analyser/cursors/activePictureCursor",
                          "PUT": "analyser/cursors/activePictureCursor",
                          "DOC": "Get / Set the posision of the SDI active picture cursor"
                      },
                      "dataview": {
                          "GET": "analyser/dataview",
                          "DOC": "Get the current SDI dataview"
                      },
                      "prbs": {
                          "GET": "analyser/prbs",
                          "PUT": "analyser/prbs",
                          "DOC": "Get the current PRBS analysis information"
                      }
                  },
                  url_methods={
                      "level_b_sub_image_crc": {
                          "GET": ("analyser/detail/link{link}/subImage{index}/crc", "Get the frame CRC for a multi link Level B standard for link A or B subimage 1 - 4")
                      },
                      "level_a_sub_image_crc": {
                          "GET": ("analyser/detail/subImage{index}/crc", "Get the frame CRC for a multi link Level A standard for subimage 1 - 4")
                      }
                  },
                  http_session=DEFAULT_SESSION
                  ):
    """\
    Provides access to the Analyser features on the Qx series.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session, io: SDIInputOutput):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._io = io

    def get_analyser_datarate(self) -> float:
        """
        Returns the data rate of the standard currently being received by the unit

        :return: Float representation of the currently received standard's data rate
        """
        return ParsedStandard(self.analyser_status.get('standard', '')).data_rate

    def get_analyser_status(self):
        """\
        Get the current analysed standard in the legacy form. New code should use `ParsedStandard(self.analyserStatus)`.
        """
        warnings.warn("New code should use `ParsedStandard(self.analyserStatus)`. Do not use in new code.",
                      DeprecationWarning)

        standard = self.analyser_status.get('standard', '')
        split_standard = standard.split(' ')

        if len(split_standard) >= 3:
            return split_standard[0], urllib.parse.unquote(split_standard[1]), "_".join(split_standard[2:])
        else:
            raise AnalyserException(f'Unexpected standard data: {standard}')

    def get_analyser_dataview(self) -> dict:
        """
        Return values from the dataview windows at the active cursor postiton. Use with :func:
        `move_active_picture_cursor` to reposition the active cursor

        :return: Dictionary object containing dataview data
        """
        dataview = self.dataview
        data = {}
        for content in dataview.get("samples", None):
            content_dict = {content["content"]: content["data"]}
            data.update(content_dict)
        return data

    def move_active_picture_cursor(self, line: int, pixel: int):
        """
        Convenience method to set active picture cursor to specified coordinates.

        :param line: Set the source line value
        :param pixel: Set the source position pixel
        """

        current_position = self.cursors_active_picture_cursor
        current_line = current_position["activePictureLine"]
        current_pixel = current_position["activePicturePixel"]
        self.log.info(f'{self._hostname} - Old cursor location: line: {current_line} pixel: {current_pixel}')

        cursor_data = {
            "sourcePositionLine": 0,
            "sourcePositionPixel": 0,
            "activePictureLine": line,
            "activePicturePixel": pixel
        }

        try:
            self.cursors_active_picture_cursor = cursor_data
            self.log.info(f'{self._hostname} - New cursor location: line: {current_line} pixel: {current_pixel}')
        except CoreException as e:
            raise AnalyserException(f'Failed to set active picture cursor to line {line}, pixel {pixel}. {e}')

    def expected_video_analyser(self, exp_aspect: str, exp_colour: str, exp_format: str) -> bool:
        """
        Determine if the current standard matches the provided expected values.

        :param exp_aspect: The resolution and frame rate (e.g. '3840x2160p50')
        :param exp_colour: The pixel format and bit depth (e.g. 'YCbCr:422:10')
        :param exp_format: The data rate, picture format and colorimetry (e.g. '12G_2-SI_Rec.709')
        """
        try:
            analyser_status = self.analyser_status
        except CoreException as e:
            response = e.args[0].get("response", None)
            if response:
                raise AnalyserException(
                    f'{self._hostname}: {response.status_code} - {response.error_message}')
            else:
                raise AnalyserException(f'{self._hostname}: No response from request to obtain analyser status.')

        standard_data = analyser_status.get("standard", None)
        if not standard_data:
            raise AnalyserException(
                f'{self._hostname} - Could not get standard data from analyser status: {analyser_status}')

        try:
            result = str(standard_data).split(" ")
            actual_aspect = result[0]
            actual_colour = result[1]
            actual_format = "_".join(result[2:])
        except IndexError as err:
            raise AnalyserException(
                f"{self._hostname} - Analyser input is not formatted correctly. Is the analyser receiving an input? - {str(err)}")

        if actual_aspect != exp_aspect:
            self.log.warning(
                f'{self._hostname} - Expected aspect does not match. Expected: {exp_aspect} Actual: {actual_aspect}')
            return False
        elif actual_colour != exp_colour:
            self.log.warning(
                f'{self._hostname} - Expected colour code does not match. Expected: {exp_colour} Actual: {actual_colour}')
            return False
        elif actual_format != exp_format:
            self.log.warning(
                f'{self._hostname} - Expected format does not match. Expected: {exp_format} Actual: {actual_format}')
            return False
        else:
            self.log.info(f'{self._hostname} - Analyser read: {actual_aspect}, {actual_colour}, {actual_format}')
            return True

    def set_cable_type(self, cable: CableType = CableType.BELDEN_8281):
        """
        Set the cable type.

        :param cable: Cable type identifier string
        """
        try:
            self.cable_length = {"cableType": cable.value}
        except CoreException as e:
            response = e.args[0].get("response", None)
            if response:
                raise AnalyserException(
                    f'{self._hostname}: {response.status_code} - {response.error_message} - Failed to set cable type.')
            else:
                raise AnalyserException(f'{self._hostname}: No response from request to set cable type')

    def get_link_and_subimage_crcs(self) -> list:
        """\
        Convenience method to get the CRC data back for all relevant subimages from the Rest API in a single call as
        a list.
        """
        crc_detail_url = f"{self._base_url}/analyser/detail"
        crcs = []
        self._get_crc_data(crc_detail_url, crcs)
        return crcs

    def _get_crc_data(self, url: str, crc_list: list, path_name: str = ""):
        response = requests.get(url)
        if response.status_code == 200:
            links = response.json()
            for link in links.get("links", []):
                rel = link.get("rel", None)
                if rel == 'self':
                    pass
                elif rel == 'crc':
                    crc_response = requests.get(link.get("href", None))
                    if crc_response.status_code == 200:
                        crc_list.append(crc_response.json())
                else:
                    self._get_crc_data(link.get("href", None), crc_list)

    def get_link_and_subimage_crcs_dict(self) -> dict:
        """\
        Convenience method to get the CRC data back for all relevant subimages from the Rest API in a single call as
        a dictionary of CRCs. The dictionary keys identify the individual CRCs for single links, dual and quad link
        standards and standard with multiple sub images:

            {"single": {}}
            {"linkA": {}}
            {"linkB": {}}
            {"linkA/subImage1": {}}
            etc.
        """
        crc_detail_url = f"{self._base_url}/analyser/detail"
        crc_head = {}
        crc_head['links'] = set()
        crc_head['link_subimages'] = set()
        crc_leaf = crc_head
        self._get_crc_data_dict(crc_detail_url, crc_head, crc_leaf)
        return crc_head

    def _get_crc_data_dict(self, url: str, crc_head: dict, crc_leaf: dict):
        response = requests.get(url)
        if response.status_code == 200:
            links = response.json()
            for link in links.get("links", []):
                rel = link.get("rel", None)
                if rel == 'self':
                    pass
                elif rel == 'crc':
                    crc_response = requests.get(link.get("href", None))
                    if crc_response.status_code == 200:
                        crc_leaf['crc'] = crc_response.json()
                elif rel.startswith('link'):
                    crc_head['links'].add(rel)
                    crc_leaf[rel] = {}
                    self._get_crc_data_dict(link.get("href", None), crc_head, crc_leaf[rel])
                elif rel.startswith('subImage'):
                    crc_head['link_subimages'].add(rel)
                    crc_leaf[rel] = {}
                    self._get_crc_data_dict(link.get("href", None), crc_head, crc_leaf[rel])


    def get_crc_analyser(self) -> List[Dict]:
        """\
        Convenience method to get the CRC data back for all relevant subimages from the Rest API in a single call.
        """
        warnings.warn("New code should use get_link_and_subimage_crcs(). Do not use in new code.",
                      DeprecationWarning)

        try:
            detail = self.analyser_detail
        except CoreException as e:
            response = e.args[0].get('response', None)
            if response and response.status_code == 204:
                raise AnalyserException(
                    f'No content in the GET to analyser/detail (status code 204). The analyser may not be receiving an input')
            else:
                raise AnalyserException(
                    f'Could not GET analyser/detail: status {response.status_code}: {response.text}:  {response.json().get("message", "No message")}')

        crc = []
        multilink_crc = []

        # Iterate through subimages
        for link in detail["links"][1:]:
            # Reset flag to != "crc" for each entry at stub root level
            flag = ""

            while flag != "crc":
                # Set flag variable to current "rel". Could be "linkA/B", "subImage1/2/3/4", or "crc"
                flag = link["rel"]
                # If flag is anything other than "crc", make the request to next level of detail stub
                # We will use the requests Session instance provided by the class (this may be a mock!).
                resp = self._http_session.get(link["href"]).json()

                try:
                    # Iterate through next level of stub links
                    for link in resp["links"][1:]:
                        # Set flag to current "rel" value. Could be "subImage1/2/3/4" or "crc"
                        flag = link["rel"]

                        # If flag is not "crc". Current standard is B level
                        if flag != "crc":
                            resp = self._http_session.get(link["href"]).json()

                            flag = resp["links"][1]["rel"]

                            link = resp["links"][1]
                            multilink_crc.append(self._http_session.get(link["href"]).json())
                except KeyError:
                    print('Link: %s\t Flag: %s\t Resp: %s' % (str(link), str(flag), str(resp)))

            if len(multilink_crc) > 1:
                crc = multilink_crc
            else:
                crc.append(self._http_session.get(link["href"]).json())

        return crc

    def reset_crc(self):
        """
        Reset CRC error counters and timers
        """
        try:
            self.crc_summary = {"action": "reset", "ignoreCrcOnSwitchLines": "enable"}
        except CoreException as e:
            response = e.args[0].get("response", None)
            if response:
                raise AnalyserException(
                    f'{self._hostname}: {response.status_code} - {response.error_message} - Failed to reset CRC counters.')
            else:
                raise AnalyserException(f'{self._hostname}: No response from request to reset CRC counters')

    def get_crc_last_input_failure(self) -> int:
        """
        Get the time since the last input failure.
        """
        response_data = self.crc_summary
        if response_data:
            time_since_failure = response_data.get("timeSinceInputFailure", None)
            return int(time_since_failure)
        else:
            raise AnalyserException(
                f'{self._hostname} - No response body returned from analyser/crcSummary')

    def validate_crc(self) -> bool:
        """
        Does the CRC analyser indicate any problems?
        """
        crc_data = self.get_crc_analyser()
        pass_flag = True

        for img_crc in crc_data:
            # Get the name of current subimage
            name = img_crc["links"][0]["href"].split("/")[-2:][0]

            if name == "detail":
                name = "video stream"

            if img_crc["ancErrorCountYPos"] or img_crc["ancErrorCountCPos"] > 0:
                pass_flag = False
                self.log.error(f'{self._hostname} - Detected ANC error(s) on {name}')
                self.log.error(f'{self._hostname} - ANC Y Pos: {img_crc["ancErrorCountYPos"]} ANC C Pos: {img_crc["ancErrorCountCPos"]}')
                self.log.error(f'{self._hostname} - Time since error: {float(img_crc["okTime_ms"]/1000)}s')

            if img_crc["errorCountYPos"] or img_crc["errorCountCPos"] > 0:
                pass_flag = False
                self.log.error(f'{self._hostname} - Detected error(s) on {name}')
                self.log.error(f'{self._hostname} - Y Pos err: {img_crc["errorCountYPos"]} ANC C Pos err: {img_crc["errorCountCPos"]}')
                self.log.error(f'{self._hostname} - Time since error: {float(img_crc["okTime_ms"]/1000)}s')

        return pass_flag

    def get_prbs(self, mode: PRBSMode = PRBSMode.DISABLE, reset: bool = False) -> PRBSResponse:
        """
        Return available data related to the PRBS analysis tool

        :param mode: PRBS mode to use during analysis.
        :param reset: Optional. If True, reset the PRBS analysis counters

        """
        warnings.warn("The get_prbs method of Analyser is going to be rewritten. Do not use.",
                      DeprecationWarning)

        if reset:
            self.log.info(f'{self._hostname} - Resetting PRBS analysis counters')
            self.prbs = {"action": "reset"}
            time.sleep(1)

        analyser_prbs_data = self.prbs

        # Validate current state of PRBS analysis
        if analyser_prbs_data.get("receiveMode", "") != mode.value:
            self.log.info(f'{self._hostname} - PRBS mode does not match [{mode.value}]. Changing from {analyser_prbs_data["receiveMode"]} to {mode.value}')
            self.prbs = {"receiveMode": mode.value}
            time.sleep(1)
            analyser_prbs_data = self.prbs

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
        spigot_analysis = {
            key: value for key, value in analyser_prbs_data.items() if key in ["sdiInA", "sdiInB", "sdiInC", "sdiInD"]
        }

        return PRBSResponse(state=PRBSMode.from_value(analyser_prbs_data.get('receiveMode', '')),
                            analysis_time=analysis_time or None,
                            spigots=spigot_analysis
                            )

    def verify_clock_divisor(self, threshold: float = 0.2) -> bool:
        """\
        Confirm that the SDI input spigot is utilising the correct clock divisor for the incoming standard's data rate

        :param threshold: Optional value allowing the data rate offset to be out by. Default = 0.2
        :return: True if the spigot is configured correctly
        """

        parsed_standard = ParsedStandard(self.analyser_status.get('standard', None))
        io_data = self._io.status

        # Verify the analysed data rate is within threshold for all spigots
        data_rate_fail_flag = False
        for spigot, _ in io_data["sdiIn"]["clockFrequency"].items():
            analysed_data_rate = round(float(io_data["sdiIn"]["dataRate"][spigot].split("G")[0]), 2)
            data_rate_offset = parsed_standard.data_rate - analysed_data_rate

            # Verify the analysed data rate is correct for current standard on all SDI inputs
            if -threshold <= data_rate_offset <= threshold:
                self.log.info(f'{self._hostname} - {spigot} data rate ({analysed_data_rate} GHz) is within threshold of +/-{threshold} of analysed standard ({parsed_standard.data_rate})')
            else:
                self.log.error(f'{self._hostname} - {spigot} data rate ({analysed_data_rate} GHz) is NOT within threshold of +/-{threshold} of analysed standard ({parsed_standard.data_rate})')
                data_rate_fail_flag = True

        # Verify clock divisor for all spigots
        clock_divisor_fail_flag = False
        for spigot, _ in io_data["sdiIn"]["dataRate"].items():
            clock_divisor = float(io_data["sdiIn"]["clockFrequency"][spigot])

            match = []
            for x in FrameType:
                if parsed_standard.frame_type == x and x not in match:
                    match.append(x)

            if len(match) > 1:
                self.log.warning(f'{self._hostname} - Frame type has multiple matches... probably psf standard')

            if parsed_standard.frame_rate % 1 != 0:
                expected_divisor = 1.001
            else:
                expected_divisor = 1.000

            if clock_divisor == expected_divisor:
                self.log.info(f'{self._hostname} - Clock divisor ({clock_divisor}) is correct for the current frame rate ({parsed_standard.frame_rate})')
            else:
                self.log.error(f'{self._hostname} - Clock divisor ({clock_divisor}) is incorrect for current frame rate ({parsed_standard.frame_rate})')
                clock_divisor_fail_flag = True

        if data_rate_fail_flag or clock_divisor_fail_flag:
            return False
        else:
            return True


class ST2110Analyser(APIWrapperBase,
                     url_properties={
                         "st2110_21_config": {
                             "GET": "analyser/2110-21/config",
                             "PUT": "analyser/2110-21/config",
                             "DOC": "ST2110-21 configuration"
                         },
                         "st2110_21_info": {
                             "GET": "analyser/2110-21/info",
                             "DOC": "ST2110-21 info"
                         }
                     },
                     http_session=DEFAULT_SESSION
                     ):
    """\
    Provides access to the 2110 Analyser features on the Qx series.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        self._meta_initialise(base_url, http_session)
        super().__init__(logger, hostname)


class ST20226Analyser(APIWrapperBase,
                      url_properties={},
                      url_methods={},
                      http_session=DEFAULT_SESSION
                      ):
    """\
    Provides access to the 2022-6 Analyser features on the Qx series.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        self._meta_initialise(base_url, http_session)
        super().__init__(logger, hostname)
