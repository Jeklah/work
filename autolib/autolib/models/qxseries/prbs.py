import datetime
import enum
from dataclasses import dataclass
from typing import Union

from autolib.extendedenum import ExtendedEnum


@enum.unique
class PRBSMode(ExtendedEnum):
    """\
    Pseudo-Random Byte Stream mode.
    """
    DISABLE = "Disabled"
    PRBS_7 = "PRBS-7"
    PRBS_9 = "PRBS-9"
    PRBS_15 = "PRBS-15"
    PRBS_23 = "PRBS-23"
    PRBS_31 = "PRBS-31"


@dataclass
class PRBSResponse:
    """\
    PRBS analysis data
    """
    analysis_time: Union[datetime.time, None]
    spigots: dict
    state: PRBSMode
