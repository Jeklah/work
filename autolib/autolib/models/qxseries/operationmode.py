import enum
from dataclasses import dataclass


@dataclass
class OperationModeEntry:
    """\
    Represents an operation mode's FPGA identity and associated system mode.
    """
    fpga_design: int
    system_mode: int


@enum.unique
class OperationMode(enum.Enum):
    """
    Enumeration representing the operation modes supported by the Qx / QxL including a special value 'CURRENT' that
    is used to indicate that for some operations the firmware version is not to be changed. OperationMode provides
    fpga_design and system_mode methods to allow easy translation. The system_mode value is as defined in the new
    C++ enum::

        enum SystemMode : unsigned int
        {
            SystemModeNone,
            SystemModeSdi,
            SystemModeSdiStress,
            SystemModeIp2110,
            SystemModeIp2022_6
        };

    """
    NONE = OperationModeEntry(0, 0)
    SDI = OperationModeEntry(1, 1)
    SELF_TEST = OperationModeEntry(2, 0)
    SDI_STRESS = OperationModeEntry(7, 2)
    IP_2110 = OperationModeEntry(8, 3)
    IP_2022_6 = OperationModeEntry(5, 4)
    COMBINED_SDI_QXL = OperationModeEntry(13, 5)
    CURRENT = OperationModeEntry(999, 0)

    @property
    def fpga_design(self):
        """\
        Obtain the device's current operation mode's FPGA identity value.
        """
        return self._value_.fpga_design

    @property
    def system_mode(self):
        """\
        Obtain the device's current operation mode's system mode value.
        """
        return self._value_.system_mode

    @classmethod
    def from_fpga_design(cls, req_value):
        """
        Return an OperationMode object from an FPGA design value.
        """
        for enum_item in cls:
            if req_value == enum_item.value.fpga_design:
                return enum_item
        return None

    @classmethod
    def from_system_mode(cls, req_value):
        """
        Return an OperationMode object from a system_mode value.
        """
        for enum_item in cls:
            if req_value == enum_item.value.system_mode:
                return enum_item
        return None

    @classmethod
    def from_name(cls, req_value):
        """
        Return the OperationMode based on a given string.
        """
        for enum_item in cls:
            if req_value == enum_item.name:
                return enum_item
        return None
