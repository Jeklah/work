from abc import ABCMeta, abstractmethod


class DeviceController(metaclass=ABCMeta):
    """\
    This abstract class defines the base common interface that all device controller classes must support.
    """

    @abstractmethod
    def request_capability(self, capability):
        """\
        Request that the unit reconfigure itself to make a named capability available.

        :param capability: Some named capability (e.g. operating mode) to make available
        """
        pass

    @abstractmethod
    def query_capability(self, capability) -> bool:
        """\
        Determine if a named capability is currently available.

        :param capability: Some named capability (e.g. operating mode)
        :return: Boolean indicating availability
        """
        pass

    @abstractmethod
    def reboot(self, block_until_ready: bool = True):
        """\
        Reboot the unit and optionally block until the unit is in a suitable state to be controlled.

        :param block_until_ready: True will block until the device is ready to automate or a timeout is met.
        """
        pass

    @abstractmethod
    def upgrade(self, **kwargs):
        """\
        Provide a means to upgrade the software running on the device. The parameters here are implementation specific
        keyword arguments.

        @DUNC This too is not nice.
        """
        pass

    @abstractmethod
    def restore_initial_state(self):
        """\
        Restore the device to a 'known-good' initial state. This will potentially clear any installed configuration
        or settings files.
        """
        pass
