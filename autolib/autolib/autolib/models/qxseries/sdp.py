from typing import Generator

from sdp_transform import parse, parseParams, write
from easydict import EasyDict


class FmtpDict(EasyDict):
    """\
    Wrapper around EasyDict to make determining the state of unary fmtp entries referred to in the 2110-20 specification
    as standalone declarations (e.g. interlace) easier in tests. The sdp-transform library inserts a key for unary items
    with a value None so to see if that option is enabled you have to look in the keys to see if it's present, not
    examine its value. If a standalone declaration is present then it will have the value None (not ideal in assertions)
    and if it's not present an AttributeError will be raised. In regular Python code this needs:

        try:
            val = True if sdp.fmtp(0).interlace is None else False
        except AttributeError:
            val = False

    In Pytest you could use with pytest.raises() which is also really messy.

    Dictionary style access is a little better but still not ideal:

        if 'interlace' in sdp.fmtp(0).keys():
            ...

    Instead, this dict treats attribute requests for standalone declartions in the format parameters differently
    returning True if present else False. e.g.

        if sdp.fmtp(0).interlace:
            ...

    Note that the dictionary remains unchanged so dictionary style access will remain as before (if a unary item is
    present in the fmtp there will be a key value pair 'item': None in the dictionary else there will be no key present.

    ST2110-20(2017) specifies standalone declarations in the format parameters ('interlace' and 'segmented') in section
    7.3 Media Type Parameters with default values. The -10, -30, -31 and -40 specs do not define any currently.

    """

    def __getattribute__(self, item):
        if item in ['interlace', 'segmented']:
            if item not in self.__dict__:
                return False
            else:
                return True
        else:
            return super().__getattribute__(item)


class SDPDescriptor:
    """\
    Used for providing access to the top level SDP entries in an SDP class (instead of properties which are a little
    cumbersome for this task).
    """
    def __init__(self, mapping_name):
        self._mapping_name = mapping_name

    def __get__(self, obj, objtype=None):
        return obj.data.get(self._mapping_name, None)

    def __set__(self, obj, value):
        obj.data[self._mapping_name] = value


class SDP:
    """\
    The SDP class uses EasyDict objects to present a parsed SDP for examinination or modification. The top level items
    are exposed through SDPDescriptors and all sub-objects (E.g. the origin property) are returned as EasyDicts that
    can be accessed using attribute notation.

      with open("st2110-20.sdp") as sdp_file:
        sdp = SDP(sdp_file.read())
        print(sdp.origin)   # {'username': '-', 'sessionId': 123456, 'sessionVersion': 11, 'netType': 'IN', 'ipVer': 4, 'address': '192.168.100.2'}
        print(sdp.media[0])  # {'rtp': [{'payload': 112, 'codec': 'raw', 'rate': 90000}], 'fmtp': [{'payload': 112, 'config': 'sampling=YCbCr-4:2:2; width=1280; height=720; interlace; exactframerate=60000/1001; depth=10; TCS=SDR; colorimetry=BT709; PM=2110GPM; SSN=ST2110-20:2017;'}], 'type': 'video', 'port': 50000, 'protocol': 'RTP/AVP', 'payloads': 112, 'connection': {'version': 4, 'ip': '239.100.9.10/32'}, 'sourceFilter': {'filterMode': 'incl', 'netType': 'IN', 'addressTypes': 'IP4', 'destAddress': '239.100.9.10', 'srcList': '192.168.100.2'}, 'tsRefClocks': [{'clksrc': 'ptp', 'clksrcExt': 'IEEE1588-2008:39-A7-94-FF-FE-07-CB-D0:37'}], 'mediaClk': {'mediaClockName': 'direct', 'mediaClockValue': 0}, 'mid': 'primary'}
        print(sdp.fmtp(0).depth)  # 10
        print(sdp.as_string())  # SDP reconstituted as a string

    """

    version = SDPDescriptor("version")
    origin = SDPDescriptor("origin")
    name = SDPDescriptor("name")
    description = SDPDescriptor("description")
    timing = SDPDescriptor("timing")
    direction = SDPDescriptor("direction")
    groups = SDPDescriptor("groups")
    media = SDPDescriptor("media")

    def __init__(self, sdp_string: str):
        self.data = EasyDict(parse(sdp_string))

    def fmtp(self, index: int) -> dict:
        """\
        Get a single set of parsed format parameters FmtpDict based on the media index to which they apply to.
        """
        video = self.data.media[index]
        return FmtpDict(parseParams(video.fmtp[0].config))

    @property
    def fmtps(self) -> Generator[FmtpDict, None, None]:
        """\
        Generator that provides each set of parsed format parameters as FmtpDicts in the same order as the media
        entries that they apply to.
        """
        for media in self.data.media:
            yield FmtpDict(parseParams(media.fmtp[0].config))

    def as_string(self) -> str:
        """\
        Convert the parsed SDP back into RFC 8866 format as a string.
        """
        return write(self.data)

    def from_string(self, sdp_string: str):
        """\
        Parsed a new SDP from a string and replace the current object's data.
        """
        self.data = EasyDict(parse(sdp_string))
