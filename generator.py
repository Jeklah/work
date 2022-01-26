"""\
Provides classes for interacting with the signal generator on Qx family devices.
"""

import json
import random
import re
import requests
import time
import urllib.parse
from pprint import pformat
from test_system.models.qxseries.qxexception import QxException


class GeneratorException(QxException):
    """
    Failure to generate a given standard or configure generator settings will raise a GeneratorException.
    """
    pass


class Generator:
    """
    Get and set signal generator settings on devices supporting the Qx REST API.
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

    @property
    def generator_status(self):
        """
        Generator status returned as a dict
        """
        response = requests.get(self._baseurl + "generator/status")
        if response.status_code == 200:
            return response.json()
        else:
            raise QxException(f'{self.hostname} - Attempt to obtain generator status failed. Response status: {response.status_code}: {response.json().get("message", "No message")}')

    @property
    def bouncing_box(self):
        """
        Enabled state of the bouncing box
        """
        response = requests.get(self._baseurl + "generator/bouncingBox")
        if response.status_code == 200:
            return response.json().get("enabled", False)
        else:
            raise QxException(f'{self.hostname} - Attempt to obtain bouncing box state failed. Response status: {response.status_code}: {response.json().get("message", "No message")}')

    @bouncing_box.setter
    def bouncing_box(self, enable):
        """
        Enable / disable bouncing box on generated stream
        :param enable: Bool value to enable or disable the box
        """
        data = {"enabled": enable}
        response = requests.put(self._baseurl + "generator/bouncingBox", json=data)
        if response.status_code == 200:
            self.log.info(f'{self.hostname} - Set bouncing box enable to: {enable}')
        else:
            raise QxException(f'{self.hostname} - Failed to set bouncing ball state by rest API. Response status: {response.status_code}: {response.json().get("message", "No message")}')

    @property
    def output_copy(self):
        """
        Property that returns the enabled state of output copy
        """
        response = requests.get(self._baseurl + "generator/outputCopy")
        if response.status_code == 200:
            return response.json().get("enabled", False)
        else:
            raise QxException(f'{self.hostname} - Attempt to obtain output copy state failed with status: Response status: {response.status_code}: {response.json().get("message", "No message")}')

    @output_copy.setter
    def output_copy(self, enable):
        """
        Enable / disable output copy on generated stream
        :param enable: Bool value to enable or disable the copy to all SDI outputs
        """
        data = {"enabled": enable}
        response = requests.put(self._baseurl + "generator/outputCopy", json=data)
        if response.status_code == 200:
            self.log.info(f'{self.hostname} - Set output copy to: {enable}')
        else:
            raise QxException(f'{self.hostname} - Failed to set output copy state by rest API. Response status: {response.status_code}: {response.json().get("message", "No message")}')

    @property
    def audio_group(self):
        """
        Property that returns the state of the audio groups in regard to whether it is enabled or disabled.
        """
        response = requests.get(f'{self._baseurl}generator/audio')
        if response.status_code == 200:
            return response.json().get('audioGroup', None)
        else:
            raise QxException(f'{self.hostname} - Attempt to obtain audioGroup state by ReST API failed with status: Response status: {response.status_code}: {response.json().get("message", "No message")}')

    @audio_group.setter
    def audio_group(self, audio_group_data):
        """
        Enable / disable selected audio group on generated stream.
        :param audio_group_data dict: Dictionary with the desired values for audio groups to be set to.
        """
        if audio_group_data.keys() == self.audio_group.keys():
            response = requests.put(f'{self._baseurl}generator/audio', json={"audioGroup":audio_group_data})
            if response.status_code == 200:
                self.log.info(f'{self.hostname} - Set Audio Group configuration.')
                self.log.info(f'{self.hostname}: AudioGroup configuration {audio_group_data}')
            else:
                raise QxException(f'{self.hostname} - Failed to set Audio Group configuration. Response status: {response.status_code}: {response.json().get("message", "No message")}')
        else:
            raise QxException(f'{self.hostname} - Audio Group Key Check Failed: {audio_group_data.keys()} does not match {self.audio_group.keys()}')

    def mute_sdi_outputs(self, sdi_mute_toggle):
        """
        Take tuple of 4 bool values mapping to SDI outs A, B, C, D (True = Mute / False = Unmute)

        :param sdi_mute_toggle: Tuple object containing 4 x Bool values
        """
        mute_sdi_path = self._baseurl + "generator/sdiOutputMute"

        mute_body = {
            "sdiOutputMuteA": sdi_mute_toggle[0],
            "sdiOutputMuteB": sdi_mute_toggle[1],
            "sdiOutputMuteC": sdi_mute_toggle[2],
            "sdiOutputMuteD": sdi_mute_toggle[3]
        }

        response = self._http_session.put(mute_sdi_path, json=mute_body)
        if response.status_code == 200:
            self.log.info(f'{self.hostname} - Set SDI output mute to: {str(sdi_mute_toggle)}')
        else:
            raise QxException(
                f'{self.hostname} - Error when muting outputs {response.status_code}: {response.json().get("message", "No message")}')

    def sdi_output_mute_state(self):
        """
        Get the mute state of the four SDI outputs as a tuple of four bools for A, B, C and D
        """
        mute_sdi_path = self._baseurl + "generator/sdiOutputMute"
        response = self._http_session.get(mute_sdi_path)
        if response.status_code == 200:
            data = response.json()
            if all(x in list(data.keys()) for x in ('sdiOutputMuteA', 'sdiOutputMuteB', 'sdiOutputMuteC', 'sdiOutputMuteD')):
                return data['sdiOutputMuteA'], data['sdiOutputMuteB'], data['sdiOutputMuteC'], data['sdiOutputMuteD']
            else:
                raise QxException(f'{self.hostname} - list of SDI outputs is incomplete {pformat(data)}')
        else:
            raise QxException(
                f'{self.hostname} - Error retrieving SDI output mute state {response.status_code}: {response.json().get("message", "No message")}')

    def get_test_patterns(self, res_rate, colspace, rate_gamut):
        """
        Return a list of the test patterns supported by the standard specified.

        :param res_rate: The resolution and rate in the format used by the REST API e.g. 1920x1080i50
        :param colspace: The pixel format in the format used by the REST API e.g. YCbCr:422:10
        :param rate_gamut: The SDI data rate and colour gamut in the format used by the REST API e.g. 1.5G_Rec.709
        """
        standards_path = self._baseurl + f"generator/standards/{urllib.parse.quote(res_rate)}/{urllib.parse.quote(colspace)}/{urllib.parse.quote(rate_gamut)}"
        response = self._http_session.get(standards_path)

        if response.status_code == 200:
            pattern_list = response.json().get('links', None)
            if not pattern_list:
                raise QxException(
                    f'{self.hostname} - Could not get test pattern list for {res_rate} {colspace} {rate_gamut}: Response body contains no links key.')
            return [urllib.parse.unquote(x.get('rel', None)) for x in pattern_list if x.get('rel', None) != 'self']
        else:
            raise QxException(
                f'{self.hostname} - Could not get test pattern list for {res_rate} {colspace} {rate_gamut}: {response.status_code}: {response.json().get("message", "No message")}')

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

        :param rate: A floating point representation of desired data rate (1.5, 3.0, 6.0, 12.0). If supplied, only
        standards meeting supplied data rate will be returned
        :param filename: Optional filename can be provided to write the resultant dictionary out to a .json file

        Note: This can be called with an optional keyword argument 'standard_params' which will instead return a
        dictionary of the form with the full standards dictionary along with sets containing the lists of
        resolutions, colour spaces and gamut values (the main three path parameters required by the rest API:

            {
                "standards_dict": standards_dict,
                "resolutions": resolution_set,
                "colour_spaces": colour_space_set,
                "gamuts": gamut_set
            }

        """
        standard_params = kwargs.get("standard_params", False)

        self.log.info(f'{self.hostname} - Building device video standards list')
        standards_path = self._baseurl + "generator/standards/"

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
        resolution_dict = self._http_session.get(standards_path).json()

        try:
            # Work with 1 x resolution at a time
            for standard in resolution_dict["links"][1:]:
                resolution_set.add(standard.get("rel", None))

                # Create list containing all available colour spaces for the current resolution
                available_colour_space = [x for x in self._http_session.get(standard["href"]).json()["links"][1:]]

                for colour in available_colour_space:
                    formatted_colour = urllib.parse.unquote(colour["rel"])
                    colour_space_set.add(formatted_colour)

                    # Create list containing all available gamut options for current colour space
                    gamut_list = self._http_session.get(colour["href"]).json()["links"][1:]

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
                            # standards_dict[data_rate][standard["rel"]][formatted_colour].append(current_gamut)
                            standards_dict[data_rate][standard["rel"]][formatted_colour].append(current_gamut["rel"])
                        except KeyError:
                            try:
                                standards_dict[data_rate][standard["rel"]].update({formatted_colour: []})
                            except KeyError:
                                standards_dict[data_rate].update({standard["rel"]: {formatted_colour: []}})

                            standards_dict[data_rate][standard["rel"]][formatted_colour].append(current_gamut["rel"])
        except KeyError:
            raise GeneratorException(f'{self.hostname} - Cannot find REST endpoint for standards generator. Can the'
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
            self.log.info(f'{self.hostname} - Written {standards_count} new standards to {filename}')

        if standard_params:
            return {"standards_dict": standards_dict, "resolutions": resolution_set, "colour_spaces": colour_space_set, "gamuts": gamut_set}
        else:
            return ret

    # @DUNC This whole area is not really good enough. Random testing has it's place but not in regression testing.
    # I propose that the majority of this be removed once usages have been updated to use get_standards() and
    # get_matching_standards() instead.
    def standards_generator(self, rate=None, **kwargs) -> tuple:
        """
        A generator object which will yield all available / specified standards

        Data rate can be supplied as float which will return only specified data rate standards
        Kwarg "quick_test=<int>" can be supplied to return a cut down selection of standards

        Example usage to generate 50 x 1.5G standards on a unit::

            for data_rate, resolution, mapping, gamut in unit.generator.standards_generator(1.5, quick_test=50):
                unit.generate_standard(resolution, mapping, gamut, "100% Bars")

        :param rate: float indicating the desired data rate of the standards to return
        :key quick_test: int specifying how many standards to yield as part of the generator
        """

        # Build a dictionary of all available standard that the assigned generator unit can generate
        standards_dict = self.get_standards(rate)

        # Use standard dict to build a list of lists for all available combination of standard generation
        all_standards = [[data_rate, res, colour_map, gam] for data_rate in standards_dict for res in standards_dict[data_rate]
                         for colour_map in standards_dict[data_rate][res] for gam in standards_dict[data_rate][res][colour_map]]

        if not kwargs.get("quick_test"):
            for standard in all_standards:
                yield tuple(standard)
        else:
            i = 0
            return_standards = []
            while i < kwargs.get("quick_test"):

                # Populate the list of data rates to return as specified in the config file
                if len(return_standards) == 0:
                    if rate:
                        return_standards = [rate]
                    else:
                        return_standards = [1.5, 3.0, 6.0, 12.0]
                else:
                    self.log.debug(self.hostname + " - Current return standards list: %s" % return_standards)

                # Assign a random standard contained in "all_standards" variable as "yield candidate"
                try:
                    yield_candidate = all_standards[random.randrange(0, len(all_standards))]
                except ValueError:
                    self.log.warning(self.hostname + " - All standards meeting supplied critera have been yielded, "
                                                     "if you are using \"quick_test\", you have supplied a number "
                                                     "larger than the number of available standards")
                    break

                # If the "yield candidate" data rate matches user specified, yield the standard data
                if yield_candidate[0] in return_standards:
                    # self.log.debug("Yielding: %s" % yield_candidate)
                    yield tuple(yield_candidate)
                    all_standards.remove(yield_candidate)
                    i += 1
                else:
                    self.log.warning(self.hostname + " - Data rate already yielded or FPGA mode does not support rate")

                    try:
                        return_standards.remove(yield_candidate[0])
                    except ValueError:
                        self.log.warning(self.hostname + " - Data rate already removed from list")

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
            response = self._http_session.get(f'{self._baseurl}generator/standards/{urllib.parse.quote(resolution)}/{urllib.parse.quote(colour)}')
            if response.status_code == 200:
                gamut_resp = response.json()
                gamut = gamut_resp["links"][1]["rel"]
                self.log.warning(f'{self.hostname} - No gamut supplied, using first available value: {gamut}')
            else:
                raise GeneratorException(
                    f'Could not obtain a default gamut to use - {response.status_code} - {pformat(response.json())}')

        if test_pattern is None:
            self.log.warning(f'{self.hostname} - No test pattern supplied, using first available test pattern for standard')

            # Query unit for available test patterns
            response = requests.get(f'{self._baseurl}generator/standards/{urllib.parse.quote(resolution)}/{urllib.parse.quote(colour)}/{urllib.parse.quote(gamut)}')

            if response.status_code == 200:
                available_patterns = response.json()
                # Assign the first valid pattern as the target to use for standard generation
                test_pattern = urllib.parse.unquote(available_patterns['links'][1]['rel'])
            else:
                raise GeneratorException(
                    f'Could not obtain a default test pattern to use - {response.status_code} - {pformat(response.json())}')

        pathological_args = kwargs.get("pathological") if kwargs.get("pathological") else {"pairs": 0, "type": "Eq"}

        standard_data = {
            "action": "start",
            "pathological": {
                "pairs": pathological_args["pairs"],
                "type": pathological_args["type"]
            }
        }

        standard_path = f'generator/standards/{urllib.parse.quote(resolution)}/{urllib.parse.quote(colour)}/{urllib.parse.quote(gamut)}/{urllib.parse.quote(test_pattern)}'
        response = self._http_session.put(self._baseurl + standard_path, json=standard_data, timeout=120)

        if response.status_code == 200:
            self.log.info(f"{self.hostname} - Generator set: {resolution} / {colour} / {gamut} / {test_pattern}")
        else:
            set_gen_resp = response.json()
            self.log.error(f'{self.hostname} - Bad response: {str(set_gen_resp.get("status", "Unknown"))} - {str(set_gen_resp.get("message", "Unknown"))}')
            self.log.error(f'{self.hostname} - Bad response: {self._baseurl}generator/standards/{resolution}/{urllib.parse.quote(colour)}/{gamut}/{urllib.parse.quote(test_pattern)}')
            self.log.error(f'{self.hostname} - Bad response: {str(set_gen_resp.get("status", "Unknown"))}')
            self.log.debug(json.dumps(standard_data, indent=4))
            raise GeneratorException(
                f'{self.hostname} - Bad response when attempting to set generator - {response.status_code} - {response.json()}')

    def is_generating_standard(self, resolution, colour, gamut, test_pattern):
        """
        Used to verify that the unit is currently generating an expected standard. Provide the detail of an expected
        standard, function will return a bool value to indicate that the unit is (or is not) generating the provided
        standard.

        :param resolution: String representation of the desired standard resolution + frame rate (eg "1920x1080p23.98")
        :param colour: String representation of the colouremitry + bit mapping of desired standard (eg "YCbCr:422:10")
        :param gamut: String representation of desired gamut data (eg "1.5_Rec.709")
        :param test_pattern:  String specifying the desired test pattern to use
        :return Bool
        """

        response = self._http_session.get(f'{self._baseurl}generator/standards/{urllib.parse.quote(resolution)}/{urllib.parse.quote(colour)}/{urllib.parse.quote(gamut)}/{urllib.parse.quote(test_pattern)}')

        if response.status_code == 200:
            standard_data = response.json()
            return standard_data.get("generating", False)

        return False

    def set_audio(self, **kwargs):
        """
        Configure audio generation

        :key default: Bool value. If True, sets all frequency and amplitude values to default.
        :key enable_groups: List of integers indicating available audio groups to enable (Zero based offset)
        :key disable_groups: List of integers indicating available audio groups to disable (Zero based offset)
        :key channel_config: List of tuple objects. Tuples should contain [(<zero based channel number>, <frequency>, <gain>)]"
        """
        response = requests.get(self._baseurl + "generator/audio")
        if response.status_code != 200:
            raise GeneratorException(
                f'{self.hostname} - Could not configure audio generator settings - {response.status_code} - {response.json()}')

        audio_body = response.json()

        if kwargs.get("default"):
            default_freq = 261
            default_amp = -18

            channel_data = audio_body["customConfig"]
            del channel_data["numGroups"]

            for channel in channel_data["channels"]:
                self.log.debug(f'Setting channel {channel["channel"]} to defaults')
                channel["frequency_Hz"] = default_freq
                channel["gain_dBFS"] = default_amp

            response = self._http_session.put(self._baseurl + "generator/audio", json={"customConfig": channel_data})
            if response.status_code == 200:
                self.log.info(
                    f'{self.hostname} - All audio groups have been defaulted to - Frequency: {default_freq} Amplitude: {default_amp}')
            else:
                raise GeneratorException(
                    f'{self.hostname} - Could not restore audio generator settings to defaults - {response.status_code} - {response.json()}')

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

            self.log.info(f'{self.hostname} - Enabling audio groups {groups_to_enable}')
            self.log.info(f'{self.hostname} - Disabling audio group {groups_to_disable}')

            response = self._http_session.put(self._baseurl + "generator/audio", json={"audioGroup": group_current_status})
            if response.status_code == 200:
                # Wait until returning as re-configuring audio can cause the generated signal to flap as we could be
                # inserting half an audio packet. This has impacted testing in the past causing false negatives,
                # allowing a 1 second sleep here works around it
                time.sleep(1)
                return
            else:
                raise GeneratorException(
                    f'{self.hostname} - Failed to enable / disable specified audio groups - {response.status_code} - {pformat(response.json())}')

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
            response = self._http_session.put(self._baseurl + "generator/audio", json={"customConfig": channel_data})
            if response.status_code == 200:
                return
            else:
                raise GeneratorException(
                    f'{self.hostname} - Failed to configure audio channel configuration - {response.status_code} - {pformat(response.json())}')

    def set_prbs(self, mode, invert=False):
        """
        Set the PRBS generation mode. PRBS analysis should also be configured using the function :func: `get_prbs`

        :param mode: Set the PRBS generation mode. Can be one of ["Disabled", "PRBS-7", "PRBS-9", "PRBS-15", "PRBS-23", "PRBS-31"]
        :param invert: Bool. If True will invert the generated PRBS stream
        """
        prbs_modes = ["Disabled", "PRBS-7", "PRBS-9", "PRBS-15", "PRBS-23", "PRBS-31"]

        if mode not in prbs_modes:
            raise GeneratorException(
                f'{self.hostname} - mode {mode} supplied for PRBS generation does not match expected PRBS modes')

        prbs_data = {
            "invert": False if not invert else True,
            "mode": mode
        }

        response = self._http_session.put(self._baseurl + "generator/prbs", json=prbs_data)
        if response.status_code == 200:
            self.log.info(f'{self.hostname} - PRBS generation has been set to: {pformat(prbs_data)}')
        else:
            raise GeneratorException(
                f'{self.hostname} - Sending PRBS data was not successful: {response.status_code}: {response.json().get("message", "No message")}')

    def jitter_insertion(self, mode, amp, freq):
        """
        Insert SDI jitter into the SDI A output stream

        Limits =
            Amplitude : 0.01    -   4.00        (UI)
            Frequency : 10      -   10000000    (Hz)
            Mode :      Sine / Disabled
        """
        jitter_insertion_data = {
            "AmplitudePeakToPeak_ui": float(amp),
            "frequency_Hz": float(freq),
            "mode": mode
        }

        response = requests.put(self._baseurl + "generator/jitterInsertion", json=jitter_insertion_data)
        if response.status_code != 200:
            raise GeneratorException(
                f'{self.hostname} - Sending PRBS data was not successful: {response.status_code}: {response.json().get("message", "No message")}')

        jitter_ins_resp = response.json()
        try:
            self.log.info(f'{self.hostname} - Jitter insertion has been set to: {jitter_ins_resp["mode"]} / {str(jitter_ins_resp["AmplitudePeakToPeak_ui"])} / {str(jitter_ins_resp["frequency_Hz"])}')
        except KeyError as e:
            raise GeneratorException(f'{self.hostname} - Expected field missing from prbs response: {e} - {pformat(jitter_ins_resp)}')
