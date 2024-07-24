"""
Automation object for controlling, configuring and inspecting the state of HyperDeck series SDI / HDMI recorders.
"""

import logging
import socket
import time

from autolib.models.devicecontroller import DeviceController
import autolib.models.blackmagic.protocol as protocol
from autolib.logconfig import autolib_log
from autolib.models.blackmagic.connection import HyperDeckConnection
from autolib.models.blackmagic.exceptions import HyperDeckException


class HyperDeckStudio(DeviceController):
    """
    HyperDeckStudio device class.
    """

    def request_capability(self, capability):
        raise NotImplementedError

    def query_capability(self, capability) -> bool:
        raise NotImplementedError

    def reboot(self, block_until_ready: bool = True):
        raise NotImplementedError

    def upgrade(self, **kwargs):
        raise NotImplementedError

    def restore_initial_state(self):
        raise NotImplementedError

    def __init__(self, hostname):
        """
        Create a HyperDeckStudio for recording / playing content.
        """
        self.log = logging.getLogger(autolib_log)
        self._ip_address = None
        self._hostname = hostname

        retry_count = 5
        while self._ip_address is None and retry_count > 0:
            try:
                self._ip_address = socket.gethostbyname(self._hostname)
            except socket.gaierror as err:
                self.log.error(f"Could not resolve hostname for {self._hostname}: {err}... retrying.")
                time.sleep(3)
                retry_count -= 1

        if retry_count == 0:
            raise HyperDeckException(f"Failed to obtain an IP address for Hostname: {self._hostname}. IP address is required.")

        self._connection = HyperDeckConnection(self._ip_address)

        if self._connection:
            self._connection.connect()
            if not self._connection.connected:
                raise HyperDeckException(f"Could not connect to Blackmagic HyperDeck Studio {self._hostname} at {self._ip_address}")

    def restart(self, mode, timeout):
        """
        Restart the unit. Currently unimplemented on this device.
        """
        raise NotImplementedError

    def play(self, **kwargs):
        """
        Ask the HyperDeck to play.

        Optional keyword parameters are:

        ========= ============ ============================== =============
        Parameter Valid range  Description                    Protocol name
        ========= ============ ============================== =============
        speed     1 - 200      % of the normal playback speed speed
        loop      Boolean                                     loop
        single    Boolean                                     single clip
        ========= ============ ============================== =============

        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        return self._connection.send_message(protocol.play(**kwargs))

    def record(self, **kwargs):
        """
        Ask the HyperDeck to start recording.

        Optional keyword parameters are:

        =========== =============== ============================== =============
        Parameter   Valid range     Description                    Protocol name
        =========== =============== ============================== =============
        name        Filename chars  Filename prefix for recordings name
        =========== =============== ============================== =============

        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        return self._connection.send_message(protocol.record(**kwargs))

    def stop(self):
        """
        Ask the HyperDeck to stop playing or recording.

        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        return self._connection.send_message(protocol.stop())

    def getclips(self):
        """
        Ask the HyperDeck to send a list of the clips available on the current SSD. The list is then retrievable through
        the clips property.

        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        return self._connection.send_message(protocol.clipsget())

    def set_video_input(self, video_in_name):
        """
        Select the video input source on the HyperDeck.

        :param video_in_name: A byte string containing the name of the input (see the definitions module for valid values).
        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        return self._connection.send_message(protocol.configuration(video_in=video_in_name))

    def set_audio_input(self, audio_in_name):
        """
        Select the audio input source on the HyperDeck.

        :param audio_in_name: A byte string containing the name of the input (see the definitions module for
                              valid values).
        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        return self._connection.send_message(protocol.configuration(audio_in=audio_in_name))

    def set_file_format(self, codec_name):
        """
        Select the recording codec on the HyperDeck.

        :param codec_name: A byte string containing the name of the recording codec (see the definitions module
                          for valid values).
        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        return self._connection.send_message(protocol.configuration(file_format=codec_name))

    @property
    def current_slot(self):
        """
        Returns the number of the currently active SSD slot.

        :return: Integer containing the slot index.
        """
        return self._connection.config.get('configuration')['slot', -1]

    def set_slot(self, **kwargs):
        """
        Select the currently active SSD slot. Please note that details of the current slot can be found in the
        configuration property dictionary in the key 'slot-info'. If the slot is selection is correctly made, then
        the clips dictionary will be updated.

        Optional keyword parameters are:

        ============ =============== ============================================ =============
        Parameter    Valid range     Description                                  Protocol name
        ============ =============== ============================================ =============
        slot_id      1-2             The slot number to enable.                   slot id
        video_format See definitions Select the timeline for the specified format override
        ============ =============== ============================================ =============

        :return: Tuple containing a boolean to indicate that the response is as expected and the response from the unit.
        """
        expected, response = self._connection.send_message(protocol.slotselect(**kwargs))

        if expected:
            self.getclips()

        return expected, response

    def goto(self, **kwargs):
        """
        Move to a position within the timeline.

        Optional keyword parameters are:

        ============= ========================== ================================================ =============
        Parameter     Valid range                Description                                      Protocol name
        ============= ========================== ================================================ =============
        clip_id       ???                        Goto the clip with the id ???                    clip id
        clip_fwbw     {b"+",b"-"} {count}        Go forward or back {count} clips                 clip id
        clip          {b"start", b"end"}         Go to the start or end of the current clip       clip
        timeline      {b"start", b"end"}         Go to the start or end of the current timeline   timeline
        timecode      b"hh:mm:ss:ff"             Go to the specified timecode                     timecode
        timecode_fwbw {b"+",b"-"} b"hh:mm:ss:ff" Go forward or backward by the specified timecode timecode
        ============= ========================== ================================================ =============
        """
        return self._connection.send_message(protocol.goto(**kwargs))

    @property
    def configuration(self):
        """
        Return a reference to a dictionary containing device configuration settings.
        """
        return self._connection.config

    @property
    def clips(self):
        """
        Return a reference to a dictionary containing details of the clips available on the current SSD.
        """
        return self.getclips()
