"""\
Unit tests for the ParsedStandard class which turns the values returned from the SDI portion of the Qx
RestAPI into the various attributes of a standard.
"""

from dataclasses import dataclass, asdict
import pytest

from typing import Union
from autolib.models.qxseries.analyser import ParsedStandard, PixelFormat, PixelComponent, Resolution, FrameType


@dataclass
class ExpectedValues:
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


@pytest.mark.parametrize("resolution,colour,pixel_format,expected_values",
                         (
                                 ("1920x1080i59.94", "YCbCrA%3A4224%3A12", "3G_B_Rec.709",
                                  ExpectedValues(
                                      3.0,
                                      None,
                                      'Rec.709',
                                      1,
                                      'B',
                                      'SDR',
                                      PixelFormat(
                                          12,
                                          [
                                              PixelComponent('Y', 4),
                                              PixelComponent('Cb', 2),
                                              PixelComponent('Cr', 2),
                                              PixelComponent('A', 4)
                                          ]),
                                      Resolution(1920, 1080),
                                      FrameType.INTERLACED,
                                      59.94)
                                  ),
                                 ("1920x1080i59.94", "YCbCrA:4444:10", "3G_A_HLG_Rec.2020",
                                  ExpectedValues(
                                      3.0,
                                      None,
                                      'Rec.2020',
                                      1,
                                      'A',
                                      'HLG',
                                      PixelFormat(
                                          10,
                                          [
                                              PixelComponent('Y', 4),
                                              PixelComponent('Cb', 4),
                                              PixelComponent('Cr', 4),
                                              PixelComponent('A', 4)
                                          ]),
                                      Resolution(1920, 1080),
                                      FrameType.INTERLACED,
                                      59.94)
                                  ),
                                 ("1280x720p29.97", "YCbCr%3A422%3A10", "1.5G_Rec.709",
                                  ExpectedValues(
                                      1.5,
                                      None,
                                      'Rec.709',
                                      1,
                                      None,
                                      'SDR',
                                      PixelFormat(
                                          10,
                                          [
                                              PixelComponent('Y', 4),
                                              PixelComponent('Cb', 2),
                                              PixelComponent('Cr', 2)
                                          ]),
                                      Resolution(1280, 720),
                                      FrameType.PROGRESSIVE,
                                      29.97)
                                  ),
                                 ("3840x2160p59.94", "YCbCr%3A422%3A10", "DL_6G_2-SI_S-Log3_Rec.2020",
                                  ExpectedValues(
                                      6.0,
                                      '2-SI',
                                      'Rec.2020',
                                      2,
                                      None,
                                      'S-Log3',
                                      PixelFormat(
                                          10,
                                          [
                                              PixelComponent('Y', 4),
                                              PixelComponent('Cb', 2),
                                              PixelComponent('Cr', 2)
                                          ]),
                                      Resolution(3840, 2160),
                                      FrameType.PROGRESSIVE,
                                      59.94)
                                  ),
                                 ("3840x2160p59.94", "YCbCr%3A422%3A10", "QL_3G_B_SQ_HLG_Rec.2020",
                                  ExpectedValues(
                                      3.0,
                                      'SQ',
                                      'Rec.2020',
                                      4,
                                      'B',
                                      'HLG',
                                      PixelFormat(
                                          10,
                                          [
                                              PixelComponent('Y', 4),
                                              PixelComponent('Cb', 2),
                                              PixelComponent('Cr', 2)
                                          ]),
                                      Resolution(3840, 2160),
                                      FrameType.PROGRESSIVE,
                                      59.94)
                                  ),
                                 ("3840x2160p59.94", "YCbCr%3A422%3A10", "12G_2-SI_S-Log3_Rec.2020",
                                  ExpectedValues(
                                      12.0,
                                      '2-SI',
                                      'Rec.2020',
                                      1,
                                      None,
                                      'S-Log3',
                                      PixelFormat(
                                          10,
                                          [
                                              PixelComponent('Y', 4),
                                              PixelComponent('Cb', 2),
                                              PixelComponent('Cr', 2)
                                          ]),
                                      Resolution(3840, 2160),
                                      FrameType.PROGRESSIVE,
                                      59.94)
                                  )
                         ))
def test_basic_parsing(resolution, colour, pixel_format, expected_values):
    """\
    Test basic parsing using a sample set of values obtained from the Qx Rest API
    """
    parsed = ParsedStandard(" ".join((resolution, colour, pixel_format)))
    parsed_standard = asdict(parsed)
    expected = asdict(expected_values)
    assert expected.items() <= parsed_standard.items()
