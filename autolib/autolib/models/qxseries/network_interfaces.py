from dataclasses import dataclass
from typing import Dict, Optional, Type

from autolib.extendedenum import ExtendedEnum


@dataclass
class InterfaceDetails:
    log_name: str
    name: str
    sfp_name: Optional[Dict[str, str]]


class Interface(ExtendedEnum):
    MGMT = InterfaceDetails("management interface", "eth0", None)
    MEDIA0 = InterfaceDetails("media interface 0", "phabEth0", {'Qx': 'sfpA', 'QxL': 'sfpE', 'QxP': 'sfpE'})
    MEDIA1 = InterfaceDetails("media interface 1", "phabEth1", {'Qx': 'sfpB', 'QxL': 'sfpF', 'QxP': 'sfpF'})
