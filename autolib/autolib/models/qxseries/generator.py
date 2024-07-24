"""
Provides classes for interacting with the SDI / ST2022-6 signal generator on Qx family devices.

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
GENERATOR_SESSION = requests.Session()
GENERATOR_SESSION.request = functools.partial(GENERATOR_SESSION.request, timeout=120)


class GeneratorException(QxException):
    """
    Failure to generate a given standard or configure generator settings will raise a GeneratorException.
    """
    pass


class Generator(APIWrapperBase,
                url_properties={
                    "audio": {
                        "GET": "generator/audio", "PUT": "generator/audio",
                        "DOC": "Get / set SDI audio generator configuration."
                    },
                    "generator_bouncing_box": {
                        "GET": "generator/bouncingBox", "PUT": "generator/bouncingBox",
                        "DOC": "Get bouncing box state or enable / disable it."
                    },
                    "generator_jitter_insertion": {
                        "GET": "generator/jitterInsertion",
                        "PUT": "generator/jitterInsertion",
                        "DOC": "Get / set SDI jitter insertion settings."
                    },
                    "generator_output_copy": {
                        "GET": "generator/outputCopy", "PUT": "generator/outputCopy",
                        "DOC": "Get output copy state or enable / disable it."
                    },
                    "prbs": {
                        "GET": "generator/prbs", "PUT": "generator/prbs",
                        "DOC": "Get / set the PRBS generator status"
                    },
                    "sdi_driver_gain": {
                        "GET": "generator/sdiDriverGain", "PUT": "generator/sdiDriverGain",
                        "DOC": "Get / set SDI driver gain settings."
                    },
                    "sdi_driver_preemphasis": {
                        "GET": "generator/sdiDriverPreEmphasis",
                        "PUT": "generator/sdiDriverPreEmphasis",
                        "DOC": "Get / set SDI driver pre-emphasis settings."
                    },
                    "sdi_output_mute": {
                        "GET": "generator/sdiOutputMute", "PUT": "generator/sdiOutputMute",
                        "DOC": "Get / set SDI output mute settings."
                    },
                    "sdi_scrambler": {
                        "GET": "generator/sdiScrambler", "PUT": "generator/sdiScrambler",
                        "DOC": "Get / set SDI scrambler settings."
                    },
                    "generator_status": {
                        "GET": "generator/status", "DOC": "Get the generator status."
                    },
                    "sync_bit_inserter": {
                        "GET": "generator/syncBitInserter", "PUT": "generator/syncBitInserter",
                        "DOC": "Get / set sync bit inserter settings."
                    },
                },
                url_methods={
                    "standard": {
                        "GET": ("generator/standards/{resolution}/{pixel_format}/{gamut_colorimetry}/{test_pattern}",
                                "Query the generator to see if it is generating the specified standard and test pattern."),
                        "PUT": ("generator/standards/{resolution}/{pixel_format}/{gamut_colorimetry}/{test_pattern}",
                                "Configure the generator to generate the specified standard and test pattern.")
                    },
                    "resolutions": {
                        "GET": ("generator/standards",
                                "Get a list of generator resolutions / frame types / frame rates."),
                    },
                    "pixel_formats": {
                        "GET": ("generator/standards/{resolution}",
                                "Get a list of generator pixel formats for the specified resolutions."),
                    },
                    "gamuts": {
                        "GET": ("generator/standards/{resolution}/{pixel_format}",
                                "Get a list of generator gamuts / colorimetries / etc. for the specified resolution and pixel format."),
                    },
                    "supported_test_patterns": {
                        "GET": ("generator/standards/{resolution}/{pixel_format}/{gamut_colorimetry}",
                                "Obtain a list of test patterns for the specified standard"),
                    },
                },
                http_session=GENERATOR_SESSION
                ):
    """
    Get and set signal generator settings on devices supporting the Qx REST API.
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
    def output_copy(self):
        """
        Property that returns the enabled state of output copy
        """
        return self.generator_output_copy['enabled']

    @output_copy.setter
    def output_copy(self, enable):
        """
        Enable / disable output copy on generated stream
        :param enable: Bool value to enable or disable the copy to all SDI outputs
        """
        self.generator_output_copy = {"enabled": enable}

    @property
    def audio_custom_config(self) -> dict:
        """
        Property that returns the custom config field from the audio meters
        configuration.
        """
        return self.audio.get('customConfig', None)

    @audio_custom_config.setter
    def audio_custom_config(self, custom_config_data):
        """
        Allows you to set the customConfig parameter for Audio Generation.
        Use: generator_qx.generator.audio_cust_config(custom_config_data)
        custom_config_data takes the form:

        {'channels':
            [{'channel': 0, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 1, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 2, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 3, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 4, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 5, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 6, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 7, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 8, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 9, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 10, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 11, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 12, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 13, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 14, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 15, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 16, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 17, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 18, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 19, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 20, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 21, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 22, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 23, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 24, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 25, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 26, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 27, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 28, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 29, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 30, 'frequency_Hz': 261, 'gain_dBFS': -18},
             {'channel': 31, 'frequency_Hz': 261, 'gain_dBFS': -18}],
         'numGroups': 4}

        Parameters
            * custom_config_data dict
        """
        self.audio = {"customConfig": custom_config_data}

    @property
    def audio_quick_config(self) -> dict:
        """
        Property that returns the value of the 'quickConfig' in the audio generation configuration.
        """
        return self.audio.get('quickConfig', None)

    @audio_quick_config.setter
    def audio_quick_config(self, quick_config_data):
        """
        Allows the quick_config field of the Audio configuration to be set.

        quick_config_data takes the form:
            {'gainType': 'Fixed Levels', 'gain_dBFS': -18, 'pitch': 'C 4'}

        Parameters
            * quick_config_data dict
        """
        self.audio = {"quickConfig": quick_config_data}

    @property
    def audio_group(self) -> dict:
        """
        Retrieves the value of the audio_groups configuration for Audio generation.
        """
        return self.audio.get('audioGroup', None)

    @audio_group.setter
    def audio_group(self, audio_group_data):
        """
        Enable / disable selected audio group on generated stream.

        Parameters

        audio_group_data dict
        """
        self.audio = {"audioGroup": audio_group_data}

    def mute_sdi_outputs(self, sdi_mute_toggle):
        """
        Take tuple of 4 bool values mapping to SDI outs A, B, C, D (True = Mute / False = Unmute)

        :param sdi_mute_toggle: Tuple object containing 4 x Bool values
        """
        self.sdi_output_mute = {
            "sdiOutputMuteA": sdi_mute_toggle[0],
            "sdiOutputMuteB": sdi_mute_toggle[1],
            "sdiOutputMuteC": sdi_mute_toggle[2],
            "sdiOutputMuteD": sdi_mute_toggle[3]
        }

    def sdi_output_mute_state(self):
        """
        Get the mute state of the four SDI outputs as a tuple of four bools for A, B, C and D
        """
        data = self.sdi_output_mute
        if all(x in list(data.keys()) for x in ('sdiOutputMuteA', 'sdiOutputMuteB', 'sdiOutputMuteC', 'sdiOutputMuteD')):
            return data['sdiOutputMuteA'], data['sdiOutputMuteB'], data['sdiOutputMuteC'], data['sdiOutputMuteD']
        else:
            raise QxException(f'{self._hostname} - list of SDI outputs is incomplete {pformat(data)}')

    def get_test_patterns(self, res_rate, colspace, rate_gamut):
        """
        Return a list of the test patterns supported by the standard specified.

        :param res_rate: The resolution and rate in the format used by the REST API e.g. 1920x1080i50
        :param colspace: The pixel format in the format used by the REST API e.g. YCbCr:422:10
        :param rate_gamut: The SDI data rate and colour gamut in the format used by the REST API e.g. 1.5G_Rec.709
        """
        data = self.get_supported_test_patterns(res_rate, colspace, rate_gamut)
        pattern_list = data.get('links', None)
        if not pattern_list:
            raise QxException(
                f'{self._hostname} - Could not get test pattern list for {res_rate} {colspace} {rate_gamut}: Response body contains no links key.')
        return [urllib.parse.unquote(x.get('rel', None)) for x in pattern_list if x.get('rel', None) != 'self']

    def get_matching_standards(self, data_rates, re_resolutions, re_colour_spaces, re_gamuts, standards_list=None):
        """
        Return a list of valid video standards in the form (data rate, resolution, colourspace, gamut) that match
        the given criteria in the form of the following parameters:

        :param data_rates: List of floating point data rate values [1.5, 3.0, 6.0, 12.0]
        :param re_resolutions: A regular expression to select resolutions. e.g. r'1920\w*|1280\w*' or r'\d+x\d+p\d+'
        :param re_colour_spaces: A regular expression to select colour spaces e.g. r'YCbCr:422:10' or r'YCbCr\w*'
        :param re_gamuts: A regular expression to select gamuts e.g. r'1.5G_PQ\w*|6G_2-SI_HLG_Rec.2020'
        :param standards_list: Optional dictionary of supported standards instead of querying Qx (used for cached lists)
        """
        standards = standards_list if standards_list else self.get_standards()
        matching_standards = []

        for data_rate, vid_formats in standards.items():
            if data_rate in data_rates:
                for res, colspaces in vid_formats.items():
                    if re.search(re_resolutions, res):
                        for colspace, gamuts in colspaces.items():
                            if re.search(re_colour_spaces, colspace):
                                for gamut in gamuts:
                                    if re.search(re_gamuts, gamut):
                                        matching_standards.append((data_rate, res, colspace, gamut))

        return matching_standards

    def get_standards(self, rate=False, filename=None, **kwargs):
        """
        Returns a dictionary of video standards supported by the unit (in its current operating state). Resulting
        standards are formatted as follows::

            {
                <data rate>: {
                    <resolution>: {
                        <colour / mapping>: [
                            <gamut>
                            ...
                        ]
                    }
                }
                ... {
                }
            }

        Can write the resultant dictionary to a .json file if <filename> argument is supplied

        Note: This can be called with an optional keyword argument 'standard_params' which will instead return a
        dictionary of the form with the full standards dictionary along with sets containing the lists of
        resolutions, colour spaces and gamut values (the main three path parameters required by the rest API::

            {
                "standards_dict": standards_dict,
                "resolutions": resolution_set,
                "colour_spaces": colour_space_set,
                "gamuts": gamut_set
            }

        :param rate: A floating point representation of desired data rate (1.5, 3.0, 6.0, 12.0). If supplied, only
                     standards meeting supplied data rate will be returned
        :param filename: Optional filename can be provided to write the resultant dictionary out to a .json file

        """
        standard_params = kwargs.get("standard_params", False)

        self.log.info(f'{self._hostname} - Building device video standards list')

        # Create dict to store all standards info in
        standards_dict = {
            1.5: {},
            3.0: {},
            6.0: {},
            12.0: {}
        }

        resolution_set = set()
        colour_space_set = set()
        gamut_set = set()

        # Obtain URL for all resolutions
        resolution_dict = self.get_resolutions()

        try:
            # Work with 1 x resolution at a time
            for standard in resolution_dict["links"][1:]:
                resolution_set.add(standard.get("rel", None))

                # Create list containing all available colour spaces for the current resolution
                available_colour_space = [x for x in self.get_pixel_formats(standard['rel'])["links"][1:]]

                for colour in available_colour_space:
                    formatted_colour = urllib.parse.unquote(colour["rel"])
                    colour_space_set.add(formatted_colour)

                    # Create list containing all available gamut options for current colour space
                    gamut_list = self.get_gamuts(standard['rel'], colour['rel'])["links"][1:]

                    for current_gamut in gamut_list:
                        try:
                            data_rate = float(current_gamut["rel"].split("_")[0].strip("G"))
                        except ValueError:
                            data_rate = float(current_gamut["rel"].split("_")[1].strip("G"))
                            link_number = 2 if current_gamut["rel"].split("_")[0] == "DL" else 4
                            data_rate = data_rate * link_number

                        gamut_set.add(current_gamut.get("rel", None))

                        # Update the main dictionary with temp dict for current standard
                        try:
                            standards_dict[data_rate][standard["rel"]][formatted_colour].append(current_gamut["rel"])
                        except KeyError:
                            try:
                                standards_dict[data_rate][standard["rel"]].update({formatted_colour: []})
                            except KeyError:
                                standards_dict[data_rate].update({standard["rel"]: {formatted_colour: []}})

                            standards_dict[data_rate][standard["rel"]][formatted_colour].append(current_gamut["rel"])
        except KeyError:
            raise GeneratorException(f'{self._hostname} - Cannot find REST endpoint for standards generator. Can the'
                                     'unit currently generate?')

        ret = {float(rate): standards_dict[rate]} if rate else standards_dict

        standards_count = 0
        for data_rate, res in ret.items():
            for colmap in res.values():
                for gam in colmap.values():
                    standards_count += len(gam)

        # Write standards dict out to file
        if filename:
            with open(filename + ".json", "w") as f:
                f.write(json.dumps(standards_dict, indent=4))
            self.log.info(f'{self._hostname} - Written {standards_count} new standards to {filename}')

        if standard_params:
            return {"standards_dict": standards_dict, "resolutions": resolution_set, "colour_spaces": colour_space_set, "gamuts": gamut_set}
        else:
            return ret

    def standards_generator(self, rate=None, **kwargs) -> tuple:
        """
        [Deprecated]

        A generator object which will yield all available / specified standards

        Data rate can be supplied as float which will return only specified data rate standards
        Kwarg "quick_test=<int>" can be supplied to return a cut down selection of standards

        Example usage to generate 50 x 1.5G standards on a unit::

            for data_rate, resolution, mapping, gamut in unit.generator.standards_generator(1.5, quick_test=50):
                unit.generate_standard(resolution, mapping, gamut, "100% Bars")

        :param rate: float indicating the desired data rate of the standards to return
        :key quick_test: int specifying how many standards to yield as part of the generator
        """

        warnings.warn("This method is deprecated, please do not use it in new developments.")

        # Build a dictionary of all available standard that the assigned generator unit can generate
        standards_dict = self.get_standards(rate)

        # Use standard dict to build a list of lists for all available combination of standard generation
        all_standards = [[data_rate, res, colour_map, gam] for data_rate in standards_dict for res in standards_dict[data_rate]
                         for colour_map in standards_dict[data_rate][res] for gam in standards_dict[data_rate][res][colour_map]]

        if not kwargs.get("quick_test"):
            for standard in all_standards:
                yield tuple(standard)
        else:
            return_standards = []
            for i in range(int(kwargs.get("quick_test", 0))):

                # Populate the list of data rates to return as specified in the config file
                if len(return_standards) == 0:
                    if rate:
                        return_standards = [rate]
                    else:
                        return_standards = [1.5, 3.0, 6.0, 12.0]
                else:
                    self.log.debug(self._hostname + " - Current return standards list: %s" % return_standards)

                # Assign a random standard contained in "all_standards" variable as "yield candidate"
                try:
                    yield_candidate = all_standards[random.randrange(0, len(all_standards))]
                except ValueError:
                    self.log.warning(self._hostname + " - All standards meeting supplied critera have been yielded, "
                                                      "if you are using 'quick_test', you have supplied a number "
                                                      "larger than the number of available standards")
                    break

                # If the "yield candidate" data rate matches user specified, yield the standard data
                if yield_candidate[0] in return_standards:
                    # self.log.debug("Yielding: %s" % yield_candidate)
                    yield tuple(yield_candidate)
                    all_standards.remove(yield_candidate)
                    i += 1
                else:
                    self.log.warning(self._hostname + " - Data rate already yielded or FPGA mode does not support rate")

                    try:
                        return_standards.remove(yield_candidate[0])
                    except ValueError:
                        self.log.warning(self._hostname + " - Data rate already removed from list")

    def set_generator(self, resolution, colour, gamut=None, test_pattern=None, **kwargs):
        """
        Configure the generator to generate a specified standard

        Expected arguments are in the same format as the output of :func: `get_standards` or :func: `standards_generator`
        and should be used together to iterate over multiple standards.

        Optional <pathological> information can be supplied as a dictionary to insert pathological data on generation

        :param resolution: String representation of the desired standard resolution + frame rate (eg "1920x1080p23.98")
        :param colour: String representation of the colouremitry + bit mapping of desired standard (eg "YCbCr:422:10")
        :param gamut: [Optional] String representation of desired gamut data (eg "1.5_Rec.709"). If not supplied, unit
                      will generate the first available standard that meets the other criteria.
        :param test_pattern: [Optional] String specifying the desired test pattern to use. If not supplied, unit will
                             generate standard with the first available test pattern for the standard
        :key pathological: [Optional] Dictionary containing pathological data to insert upon generation
                           {"type": "CheckField, "pairs": 200}

        An example used to generate a desired standard and insert pathological data::

            unit.generator.set_generator("1920x1080p24",
                               "YCbCr:422:10",
                               "1.5G_S-Log3_Rec.2020",
                               "100% Bars",
                               pathological={"type": "CheckField", "pairs": 1000})

        """
        if gamut is None:
            gamut_resp = self.get_gamuts(urllib.parse.quote(resolution), urllib.parse.quote(colour))
            gamut = gamut_resp["links"][1]["rel"]
            self.log.warning(f'{self._hostname} - No gamut supplied, using first available value: {gamut}')

        if test_pattern is None:
            self.log.warning(f'{self._hostname} - No test pattern supplied, using first available test pattern for standard')

            # Query unit for available test patterns
            available_patterns = self.get_supported_test_patterns(urllib.parse.quote(resolution), urllib.parse.quote(colour), urllib.parse.quote(gamut))

            # Assign the first valid pattern as the target to use for standard generation
            test_pattern = urllib.parse.unquote(available_patterns['links'][1]['rel'])

        pathological_args = kwargs.get("pathological") if kwargs.get("pathological") else {"pairs": 0, "type": "Eq"}

        standard_data = {
            "action": "start",
            "pathological": {
                "pairs": pathological_args["pairs"],
                "type": pathological_args["type"]
            }
        }

        self.put_standard(urllib.parse.quote(resolution), urllib.parse.quote(colour), urllib.parse.quote(gamut), urllib.parse.quote(test_pattern), standard_data)
        self.log.info(f"{self._hostname} - Generator set: {resolution} / {colour} / {gamut} / {test_pattern}")

    def is_generating_standard(self, resolution, colour, gamut, test_pattern):
        """
        Used to verify that the unit is currently generating an expected standard. Provide the detail of an expected
        standard, function will return a bool value to indicate that the unit is (or is not) generating the provided
        standard.

        :param resolution: String representation of the desired standard resolution + frame rate (eg "1920x1080p23.98")
        :param colour: String representation of the colouremitry + bit mapping of desired standard (eg "YCbCr:422:10")
        :param gamut: String representation of desired gamut data (eg "1.5_Rec.709")
        :param test_pattern:  String specifying the desired test pattern to use
        :return: True if specified standard is being generated

        """
        try:
            is_generating = self.get_standard(resolution, colour, gamut, test_pattern)
            return is_generating.get("generating", False)
        except CoreException:
            return False

    # @DUNC Still required?
    def set_audio(self, **kwargs):
        """
        Configure audio generation

        :key default: Bool value. If True, sets all frequency and amplitude values to default.
        :key enable_groups: List of integers indicating available audio groups to enable (Zero based offset)
        :key disable_groups: List of integers indicating available audio groups to disable (Zero based offset)
        :key channel_config: List of tuple objects. Tuples should contain [(<zero based channel number>, <frequency>, <gain>)]"
        """
        audio_body = self.audio

        if kwargs.get("default"):
            default_freq = 261
            default_amp = -18

            channel_data = audio_body["customConfig"]
            del channel_data["numGroups"]

            for channel in channel_data["channels"]:
                self.log.debug(f'Setting channel {channel["channel"]} to defaults')
                channel["frequency_Hz"] = default_freq
                channel["gain_dBFS"] = default_amp

            self.audio = {"customConfig": channel_data}

        if kwargs.get("enable_groups") or kwargs.get("disable_groups"):
            # Get the current state of audio groups
            group_current_status = audio_body["audioGroup"]
            groups_to_enable = kwargs.get("enable_groups")
            groups_to_disable = kwargs.get("disable_groups")

            # Iterate through audio groups and set enable = True / False according to user input
            i = 0
            for k, v in sorted(group_current_status.items()):
                try:
                    if i in groups_to_enable:
                        group_current_status[k] = True
                except TypeError:
                    pass

                try:
                    if i in groups_to_disable:
                        group_current_status[k] = False
                except TypeError:
                    pass

                i += 1

            self.log.info(f'{self._hostname} - Enabling audio groups {groups_to_enable}')
            self.log.info(f'{self._hostname} - Disabling audio group {groups_to_disable}')

            self.audio = {"audioGroup": group_current_status}
            time.sleep(1)
            return

        if kwargs.get("channel_config"):
            # Get current config for untouched data so configuration is not changed
            channel_data = audio_body["customConfig"]
            # Remove unused (but still valid) "numGroups" key as this can override "enable_groups"
            del channel_data["numGroups"]

            # Iterate over user supplied target channels for configuration
            # If the active channel is a target, apply settings and update the configuration JSON body.
            for target_channel in kwargs.get("channel_config"):
                for active_channel in channel_data["channels"]:
                    if active_channel["channel"] == target_channel[0]:
                        active_channel["frequency_Hz"] = target_channel[1]
                        active_channel["gain_dBFS"] = target_channel[2]
                        channel_data.update(active_channel)

            # Send the updated configuration body back to the unit.
            self.audio = {"customConfig": channel_data}

    def set_prbs(self, mode: PRBSMode, invert=False):
        """
        Set the PRBS generation mode.

        :param mode: Set the PRBS generation mode.
        :param invert: Bool. If True will invert the generated PRBS stream
        """
        self.prbs = {
            "invert": False if not invert else True,
            "mode": mode.value
        }

    def jitter_insertion(self, mode, amp, freq):
        """
        Insert SDI jitter into the SDI A output stream

        Limits =
            Amplitude : 0.01    -   4.00        (UI)
            Frequency : 10      -   10000000    (Hz)
            Mode :      Sine / Disabled
        """
        self.generator_jitter_insertion = {
            "AmplitudePeakToPeak_ui": float(amp),
            "frequency_Hz": float(freq),
            "mode": mode
        }

        jitter_ins_resp = self.generator_jitter_insertion
        try:
            self.log.info(f'{self._hostname} - Jitter insertion has been set to: {jitter_ins_resp["mode"]} / {str(jitter_ins_resp["AmplitudePeakToPeak_ui"])} / {str(jitter_ins_resp["frequency_Hz"])}')
        except KeyError as e:
            raise GeneratorException(f'{self._hostname} - Expected field missing from prbs response: {e} - {pformat(jitter_ins_resp)}')

    def configure_audio_groups(self, groups: List[int], enabled: bool):
        """\
        Enable or disable a list of audio groups
        """
        audio_body = self.audio
        audio_groups = audio_body["audioGroup"]
        for group_name, _ in audio_groups.items():
            if int(group_name.lstrip('audioGroup')) in groups:
                audio_groups[group_name] = enabled

        del audio_body["customConfig"]["numGroups"]
        self.audio = audio_body
