"""
Protocol message objects for communicating with a HyperDeck series SDI / HDMI recorder.
"""

import enum
import logging
import re
from abc import ABCMeta

from autolib.logconfig import autolib_log
from autolib.models.blackmagic.exceptions import HyperDeckException

# This is the output from the HyperDeck Studio Pro 'commands' command.
#
# 212 commands:
# <?xml version="1.0" encoding="UTF-8"?>
# <commands>
#     <command name="help"/>
#     <command name="commands"/>
#     <command name="device info"/>
#     <command name="disk list"><parameter name="slot id"/></command>
#     <command name="quit"/>
#     <command name="ping"/>
#     <command name="preview"><parameter name="enable"/></command>
#     <command name="play"><parameter name="speed"/><parameter name="loop"/><parameter name="single clip"/></command>
#     <command name="playrange set"><parameter name="clip id"/><parameter name="in"/><parameter name="out"/></command>
#     <command name="playrange clear"/>
#     <command name="record"><parameter name="name"/></command>
#     <command name="stop"/>
#     <command name="clips count"/>
#     <command name="clips get"><parameter name="clip id"/><parameter name="count"/></command>
#     <command name="clips add"><parameter name="name"/></command>
#     <command name="clips clear"/>
#     <command name="transport info"/>
#     <command name="slot info"><parameter name="slot id"/></command>
#     <command name="slot select"><parameter name="slot id"/><parameter name="video format"/></command>
#     <command name="notify"><parameter name="remote"/><parameter name="transport"/><parameter name="slot"/><parameter name="configuration"/><parameter name="dropped frames"/></command>
#     <command name="goto"><parameter name="clip id"/><parameter name="clip"/><parameter name="timeline"/><parameter name="timecode"/><parameter name="slot id"/></command>
#     <command name="jog"><parameter name="timecode"/></command>
#     <command name="shuttle"><parameter name="speed"/></command>
#     <command name="remote"><parameter name="enable"/><parameter name="override"/></command>
#     <command name="configuration"><parameter name="video input"/><parameter name="audio input"/><parameter name="file format"/></command>
#     <command name="uptime"/>
#     <command name="format"><parameter name="prepare"/><parameter name="confirm"/></command>
# 	   <command name="identify"><parameter name="enable"/></command>
#     <command name="watchdog"><parameter name="period"/></command>
# </commands>


class ProtocolEnum(enum.Enum):
    """
    Enum with __bytes__ configured to return the value as a bytes object.
    """
    def __bytes__(self):
        return bytes(self.value)


@enum.unique
class ProtocolCommand(ProtocolEnum):
    QUIT = b'quit'
    PING = b'ping'
    PLAY = b'play'
    RECORD = b'record'
    STOP = b'stop'
    CLIPS_GET = b'clips get'
    NOTIFY = b'notify'
    REMOTE = b'remote'
    CONFIG = b'configuration'
    DEVICE_INFO = b'device info'
    TRANSPORT_INFO = b'transport info'
    SLOT_INFO = b'slot info'
    SLOT_SELECT = b'slot select'
    GOTO = b'goto'


@enum.unique
class VideoInput(ProtocolEnum):
    SDI = b'SDI'
    HDMI = b'HDMI'
    COMPONENT = b'component'


@enum.unique
class AudioInput(ProtocolEnum):
    EMBEDDED = b'embedded'
    XLR = b'XLR'
    RCA = b'RCA'


@enum.unique
class Codec(ProtocolEnum):
    QT_UNCOMPRESSED = b"QuickTimeUncompressed"
    QT_PRORESHQ = b"QuickTimeProResHQ"
    QT_PRORES = b"QuickTimeProRes"
    QT_PRORESLT = b"QuickTimeProResLT"
    QT_PRORESPROXY = b"QuickTimeProResProxy"
    QT_DNXHD220 = b"QuickTimeDNxHD220"
    DNXHD220 = b"DNxHD220"


@enum.unique
class VideoFormat(ProtocolEnum):
    NTSC = b'NTSC'
    PAL = b'PAL'
    NTSCP = b'NTSCp'
    PALP = b'PALp'
    HD720P50 = b'720p50'
    HD720P5994 = b'720p5994'
    HD720P60 = b'720p60'
    HD1080P23976 = b'1080p23976'
    HD1080P24 = b'1080p24'
    HD1080P25 = b'1080p25'
    HD1080P2997 = b'1080p2997'
    HD1080P30 = b'1080p30'
    HD1080I50 = b'1080i50'
    HD1080I5994 = b'1080i5994'
    HD1080I60 = b'1080i60'
    UHD4KP23976 = b'4Kp23976'
    UHD4KP24 = b'4Kp24'
    UHD4KP25 = b'4Kp25'
    UHD4KP2997 = b'4Kp2997'
    UHD4KP30 = b'4Kp30'


REPLY_SIZE = 1024

hyperdeck_response = b'^(?P<code>\d{3})\s*(?P<message>[^:\r\n]+):*\s*[\r\n]{1,2}|' \
                     b'(?P<clipid>[\d]+):\s*(?P<clipname>[\S]+)\s+\d\d:\d\d:\d\d:\d\d\s+\d\d:\d\d:\d\d:\d\d\s*[\r\n]+|' \
                     b'(?P<tckey>[^:\r\n]+):\s*(?P<timecode>\d\d:\d\d:\d\d:\d\d)\s+|' \
                     b'(?P<key>[^:\r\n]+):\s*(?P<val>[^:\r\n]+)[\r\n]+'


class HyperDeckResponse:
    """
    Extracts the various information fields from a Hyperdeck response message. This class is intended to be immutable
    once constructed.
    """
    def __init__(self, bytes_in):
        self._code = b""
        self._message = b""
        self._params = {}
        self._hyper_re = re.compile(hyperdeck_response)
        self.from_bytes(bytes_in)
        self._log = logging.getLogger(autolib_log)

    def from_bytes(self, bytes_in):
        """
        Using a regular expression, convert the incoming bytes into the code and message fields and create
        a dictionary params containing the various response parameters.

        :param bytes_in: Byte array read from the transport layer.
        """
        if bytes_in is not None:
            for match in self._hyper_re.finditer(bytes_in):
                reply_dict = match.groupdict()
                if reply_dict.get('code', None) is not None:
                    self._code = int(reply_dict['code'].decode())
                    self._message = reply_dict['message'].decode()
                elif reply_dict.get('key', None):
                    self._params[reply_dict['key'].decode()] = reply_dict['val'].decode()
                elif reply_dict.get('tckey', None):
                    self._params[reply_dict['tckey'].decode()] = reply_dict['timecode'].decode()
                else:
                    self._params[int(reply_dict['clipid'].decode())] = reply_dict['clipname'].decode()
        else:
            raise HyperDeckException("Cannot construct from None")

    @property
    def code(self):
        """The response code. Errors are within the 100-199 range, responses in the 200-500 range."""
        return self._code

    @property
    def message(self):
        """The response message (useful for logging)."""
        return self._message

    @property
    def params(self):
        """Returns the dictionary containing the response parameters. This property is immutable."""
        return self._params

    def __repr__(self):
        """
        Return a unicode representation of the response.
        """
        if self._params:
            return f"[HyperDeck: {str(self.code)} : {self.message} : {self._params}]"
        else:
            return f"[HyperDeck: {str(self.code)} : {self.message}]"


class HyperDeckCommand(metaclass=ABCMeta):
    """
    Abstract base class for all Hyperdeck command messages.
    """

    def __init__(self, command):
        """
        Create a command message object that can be sent to a HyperDeckMessageConnection.

        :param command: A ProtocolCommand containing the protocol command string (e.g. b'play')
        """
        self._log = logging.getLogger(autolib_log)
        self._params = {}
        self._expects = 200
        if command in ProtocolCommand:
            self._command = command.value
        else:
            raise HyperDeckException("Invalid HyperDeck command requested")

    def _add_and_validate_param_enum(self, kw_item, protocol_name, valid_list, default_val, **kw_args):
        """
        Convert a keyword parameter to the object's constructor into a validated protocol parameter key / value pair.
        This enum variant validates that the supplied byte string value is present in a supplied list.

        :param kw_item: A keyword name within kw_args that to use (a unicode string e.g. 'clip_id')
        :param protocol_name: The byte string representation of the keyword in the protocol (e.g. b'clip id')
        :param valid_list: A list of valid byte strings.
        :param default_val: The default value to send if an invalid value for kw_item is given.
        """
        item = kw_args.get(kw_item, None)
        if item is not None:
            if item in valid_list:
                self._params[protocol_name] = item
            else:
                self._log.warning(f"Invalid value for {protocol_name.decode()} chosen. Setting to default ({default_val.decode()}).")
                self._params[protocol_name] = default_val

    def _add_and_validate_param_string(self, kw_item, protocol_name, default_val, **kw_args):
        """
        Convert a keyword parameter to the object's constructor into a validated protocol parameter key / value pair.
        This string variant validates that the supplied byte string value is not empty.

        :param kw_item: A keyword name within kw_args that to use (a unicode string e.g. 'clip_id')
        :param protocol_name: The byte string representation of the keyword in the protocol (e.g. b'clip id')
        :param default_val: The default value to send if an invalid value for kw_item is given.
        """

        item = kw_args.get(kw_item, None)
        if item is not None:
            if item != b"":
                self._params[protocol_name] = item
            else:
                self._log.warning(f"Invalid value for {protocol_name.decode()} chosen. Setting to default ({default_val.decode()}).")
                self._params[protocol_name] = default_val

    def _add_and_validate_param_int(self, kw_item, protocol_name, lower_limit, upper_limit, default_val, **kw_args):
        """
        Convert a keyword parameter to the object's constructor into a validated protocol parameter key / value pair.
        This int variant validates that the supplied integer value is within a given range.

        :param kw_item: A keyword name within kw_args that to use (a unicode string e.g. 'clip_id')
        :param protocol_name: The byte string representation of the keyword in the protocol (e.g. b'clip id')
        :param lower_limit: The lowest value that kw_args[kw_item] may be.
        :param upper_limit: The greatest value that kw_args[kw_item] may be.
        :param default_val: The default int to send if kw_args[kw_item] is out of range.
        """
        value = kw_args.get(kw_item, None)
        if value is not None:
            if lower_limit <= value <= upper_limit:
                self._params[protocol_name] = str(value).encode()
            else:
                self._log.warning(f"Invalid value for {protocol_name.decode()} chosen. Setting to default ({default_val.decode()}).")
                self._params[protocol_name] = str(default_val).encode()

    def _add_and_validate_param_boolean(self, kw_item, protocol_name, default_val, **kw_args):
        """
        Convert a keyword parameter to the object's constructor into a validated protocol parameter key / value pair.
        This boolean variant validates that the supplied boolean value is not None.

        :param kw_item: A keyword name within kw_args that to use (a unicode string e.g. 'clip_id')
        :param protocol_name: The byte string representation of the keyword in the protocol (e.g. b'clip id')
        :param default_val: The default value to send if kw_args[kw_item] is None.
        """
        value = kw_args.get(kw_item, None)
        if value is not None:
            if type(value) == bool:
                self._params[protocol_name] = b'true' if value else b'false'
            else:
                self._log.warning(f"Invalid value for {protocol_name.decode()} chosen. Setting to default ({default_val.decode()}).")
                if default_val:
                    self._params[protocol_name] = b'true' if value else b'false'

    def __bytes__(self):
        """
        Explicit byte array conversion operator. Returns the byte array representation of the command object
        that will be sent to the transport layer by the connection.

        :return: Byte array containing protocol message.
        """
        if self._params:
            reply = self._command + b":"
            for key, val in self._params.items():
                if type(val) == int:
                    new_value = str(val).encode()
                elif type(val) == str:
                    new_value = val.decode()
                else:
                    new_value = val
                reply = bytes(reply) + b" " + bytes(key) + b": " + bytes(new_value)
            return bytes(reply) + b"\r\n"
        else:
            return self._command + b"\r\n"

    def __repr__(self):
        """
        Returns a log friendly representation of the command object.

        :return: Unicode string representation of the command including it's parameters.
        """
        if self._params:
            return f"[ {self._command.decode()} : {str(self._params)} ]"
        else:
            return f"[ {self._command.decode()} ]"

    @property
    def content(self):
        """
        Obtain a tuple containing the command string and the command's parameter dictionary. This is to be used
        by the connection validation / mutation mechanism.
        """
        return self._command, self._params

    @content.setter
    def content(self, command=b''):
        """
        Set the command string and / or the command's parameter dictionary. This is to be used
        by the connection validation / mutation mechanism.
        """
        self.__init__(command)

    @property
    def expects(self):
        """
        Return the response ID that we would expect if this command is executed correctly on the device.
        """
        return self._expects


class play(HyperDeckCommand):
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

    """
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.PLAY)
        self._add_and_validate_param_int('speed', b'speed', 1, 200, 100, **kwargs)
        self._add_and_validate_param_boolean('loop', b'loop', False, **kwargs)
        self._add_and_validate_param_boolean('single', b'single clip', False, **kwargs)


class stop(HyperDeckCommand):
    """Ask the HyperDeck to stop playing."""
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.STOP)


class ping(HyperDeckCommand):
    """Ask the HyperDeck to respond with a 200 ok message."""
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.PING)


class quit_session(HyperDeckCommand):
    """Quit the socket session with the Hyperdeck."""
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.QUIT)


class transportinfo(HyperDeckCommand):
    """Enquire about the current transport state."""
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.TRANSPORT_INFO)
        self._expects = 208  # Override the default 200


class deviceinfo(HyperDeckCommand):
    """Enquire about the device information (model and protocol revision)."""
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.DEVICE_INFO)
        self._expects = 204  # Override the default 200


class slotinfo(HyperDeckCommand):
    """
    Enquire about the state of the currently selected slot.

    Optional keyword parameters are:

    ========= ============ ============================== =============
    Parameter Valid range  Description                    Protocol name
    ========= ============ ============================== =============
    slot_id   1-2          The slot number to query.      slot id
    ========= ============ ============================== =============

    """
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.SLOT_INFO)
        self._add_and_validate_param_int('slot_id', b'slot id', 1, 2, 1, **kwargs)
        self._expects = 202  # Override the default 200


class clipsget(HyperDeckCommand):
    """Update the list of clips available on the device stored in the connection."""
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.CLIPS_GET)
        self._expects = 205  # Override the default 200


class configuration(HyperDeckCommand):
    """
    Obtain the current input / output configuration.

    Optional keyword parameters are:

    =========== =============== ============================== =============
    Parameter   Valid range     Description                    Protocol name
    =========== =============== ============================== =============
    video_in    See definitions Select the video source.       video input
    audio_in    See definitions Select the audio source.       audio input
    file_format See definitions Select a compression codec.    file format
    =========== =============== ============================== =============

    """
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.CONFIG)
        self._add_and_validate_param_enum('video_in', b'video input', VideoInput, VideoInput.SDI, **kwargs)
        self._add_and_validate_param_enum('audio_in', b'audio input', AudioInput, AudioInput.EMBEDDED, **kwargs)
        self._add_and_validate_param_enum('file_format', b'file format', Codec, Codec.QT_UNCOMPRESSED, **kwargs)

        if not kwargs:
            self._expects = 211  # This is a query not a set so override 200 default


class record(HyperDeckCommand):
    """
    Ask the HyperDeck to start recording.

    Optional keyword parameters are:

    =========== =============== ============================== =============
    Parameter   Valid range     Description                    Protocol name
    =========== =============== ============================== =============
    name        Filename chars  Filename prefix for recordings name
    =========== =============== ============================== =============
    """
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.RECORD)
        self._add_and_validate_param_string('name', b'name', b'testclip', **kwargs)


class notify(HyperDeckCommand):
    """
    Enable of disable unsolicited status change notifications.

    Optional keyword parameters are:

    ========= ============ ================================== =============
    Parameter Valid range  Description                        Protocol name
    ========= ============ ================================== =============
    speed     Boolean      Transport notifications            transport
    loop      Boolean      Slot event notifications           slot
    single    Boolean      Configuration change notifications configuration
    ========= ============ ================================== =============
    """
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.NOTIFY)
        self._add_and_validate_param_boolean('transport', b'transport', False, **kwargs)
        self._add_and_validate_param_boolean('slot', b'slot', False, **kwargs)
        self._add_and_validate_param_boolean('configuration', b'configuration', False, **kwargs)

        if not kwargs:
            self._expects = 209  # This is a query not a set so override 200 default


class remote(HyperDeckCommand):
    """
    Enable of disable remote control.

    Optional keyword parameters are:

    ========= ============ ================================== =============
    Parameter Valid range  Description                        Protocol name
    ========= ============ ================================== =============
    enable    Boolean      Enable remote control operation    enable
    override  Boolean      Override the enable setting        override
    ========= ============ ================================== =============
    """
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.REMOTE)
        self._add_and_validate_param_boolean('enable', b'enable', False, **kwargs)
        self._add_and_validate_param_boolean('override', b'override', False, **kwargs)

        if not kwargs:
            self._expects = 210  # This is a query not a set so override 200 default


class slotselect(HyperDeckCommand):
    """
    Select the currently active recording slot.

    Optional keyword parameters are:

    ============ =============== ============================================ =============
    Parameter    Valid range     Description                                  Protocol name
    ============ =============== ============================================ =============
    slot_id      1-2             The slot number to enable.                   slot id
    video_format See definitions Select the timeline for the specified format override
    ============ =============== ============================================ =============
    """
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.SLOT_SELECT)
        self._add_and_validate_param_int('slot_id', b'slot id', 1, 2, 1, **kwargs)
        self._add_and_validate_param_enum('video_format', b'video format', VideoFormat, VideoFormat.HD1080I50, **kwargs)


class goto(HyperDeckCommand):
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
    def __init__(self, **kwargs):
        super().__init__(ProtocolCommand.GOTO)
        if len(kwargs) > 1:
            raise HyperDeckException("Error: Only one keyword parameter may be specified for the goto command.")
        else:
            self._add_and_validate_param_string('clip_id', b'clip id', b'???', **kwargs)
            self._add_and_validate_param_string('clip_fwbw', b'clip id', b'+1', **kwargs)
            self._add_and_validate_param_string('clip', b'clip', b'end', **kwargs)
            self._add_and_validate_param_string('timeline', b'timeline', b'end', **kwargs)
            self._add_and_validate_param_string('timecode', b'timecode', b'00:00:00:00', **kwargs)
            self._add_and_validate_param_string('timecode_fwbw', b'timecode', b'+00:00:00:00', **kwargs)
