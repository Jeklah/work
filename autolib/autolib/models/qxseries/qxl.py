"""\
The QxL module provides a QxL object used to access to various external interfaces on the Phabrix QxL (the REST API, SSH,
SFTP etc.) through methods and properties. This is not just a thin wrapper to API calls, much support code exists to
make the process of controlling, configuring and inspecting the state of the Qx trivial.
"""

from typing import Dict, Union, Tuple

from autolib.models.qxseries.qx import Qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qxexception import QxException


class QxL(Qx):
    """
    This class can be used to configure, control and inspect a QxL. It differs from a Qx only where necessary.

    Once an instance of this class is created, controlling functions can be used to perform various test related actions
    and query the device for measurements statistics.
    """

    @property
    def state_presets(self) -> Dict[OperationMode, str]:
        """\
        Returns a list of preset filenames that represent the 'current' state in each operation mode.
        """
        return {OperationMode.IP_2110: 'lastKnownState_ip2110_79',
                OperationMode.SDI: 'lastKnownState_sdi_79',
                OperationMode.IP_2022_6: 'lastKnownState_ip2022-6_79'}

    def request_capability(self, capability: Union[OperationMode]):
        """
        Request that the Qx based device make a specified capability available (implicit configuration). This should
        be used to request features instead of setting the operation_mode directly (certain capabilities may require
        additional configuration changes.

        IMPORTANT: This is a simple monolithic method at the moment but eventually will be te entry point into a more
        modular mechanism for associating capabilities with configuration. This will mean being able to take multiple
        capabilities and resolve problems when mutually exclusive capabilities are requested.

        Supported capabilities::

            OperationMode.SDI - Request base SDI features
            OperationMode.SDI_STRESS - Request SDI stress features
            OperationMode.IP_2110 - Request 2110 support
            OperationMode.IP_2022_6 - Request 2022-6 support

        """
        version = self.comparable_version()

        if version >= self.COMBINED_SDI_VERSION:
            if capability in (OperationMode.SDI, OperationMode.SDI_STRESS):
                self.operation_mode = OperationMode.COMBINED_SDI_QXL
            elif capability in (OperationMode.IP_2110, OperationMode.IP_2022_6):
                self.operation_mode = capability
        else:
            if capability in OperationMode:
                self.operation_mode = capability
            else:
                raise QxException(f"Requested unknown capability: {capability}")

    @property
    def operation_mode(self) -> OperationMode:
        """
        The current Qx operation mode. Requires SSH access to the device. This will attempt to get the system_mode from
        a marker file in /home on 4.x versions of software and then will fall back on the FPGA design number returned
        by the /usr/bin/fpgaver tool for older Qx units. The OperationMode object returned has properties to obtain the
        FPGA design index and the system mode index (new as of v4.x).
        """
        fpga_design = self._get_fpga_design()
        system_mode = self._get_system_mode()

        # Any FPGA design other than 13 on QxL is invalid (the single combined FPGA supports all modes)
        if fpga_design == 13:
            if system_mode:
                return OperationMode.from_system_mode(system_mode)
            else:
                self.log.warning(f'FGPA Design indicates the common QxL FPGA but /home/system_mode is not set. Assuming default (2110 mode)')
                return OperationMode.IP_2110
        else:
            raise QxException(f"Cannot determine the current operation mode from the Qx from /home/system_mode or using fpgaver.")

    @operation_mode.setter
    def operation_mode(self, op_mode: OperationMode):
        """
        Change the operation mode
        :param op_mode: Change to this OperationMode. If this is CURRENT or the operation mode is the one specified,
                        no changes will be made to the Qx. Requires SSH access to the device
        """
        # Make sure we can communicate with the device before trying to switch mode. We need to be able to reliably
        # restore operation mode after a test has completed in the fixture that yields the Qx object to avoid
        # breaking test runs.
        self.block_until_ready()

        current_mode = self.operation_mode
        if current_mode != op_mode and op_mode != OperationMode.CURRENT:
            self.log.info(f"Operation mode is currently {current_mode}, changing to {op_mode}")
            self.set_operating_mode(op_mode)
            self.reboot()
        else:
            self.log.info(f"Requested operation mode is the current operation mode.")

    def set_operating_mode(self, mode: OperationMode = OperationMode.CURRENT, _: OperationMode = OperationMode.CURRENT) -> bool:
        """
        Function to run the FPGA flash script on QxL unit and set the operating mode. Please use the 'operating_mode'
        property in preference to this method as it will check that a change is needed before attempting a change.

        NOTE: This method (unlike the operation_mode property setter) does not check that the unit is available before
        attempting to set the mode. For this reason it's advised that the operation_mode property be used where possible
        rather than this method.

        :param mode: The OperationMode to switch the unit to.
        :param _: Unused.
        :return: bool
        """
        current_fw_mode = self.about["firmware_mode"]
        unit_sw_version = float(self.about["Software_version"][0:3])
        self.log.info(
            f'{self._hostname} - Unit is currently running v{unit_sw_version} in {current_fw_mode} mode')

        return self._set_operating_mode(current_fw_mode, mode)

    def _set_operating_mode(self, _, mode):
        """
        The QxL differs from the Qx in that it has a single unified FPGA firmware design that implements all modes. This
        means that we only ever call the flash_upgrade.sh file with a single parameter.
        """
        current_mode = OperationMode.from_system_mode(self._get_system_mode())

        if mode == current_mode or mode == OperationMode.CURRENT:
            self.log.info(f"Requested firmware mode {mode} is currently active, no change needed.")
        else:
            self.log.info(f"Switching to firmware mode {mode}.")
            command_line = f"echo {str(mode.value.system_mode)} > /home/system_mode"
            self.log.info(f"SSH command line: {command_line}")
            exit_status, stdout, stderr = self.ssh.execute(command_line, 300)

            if exit_status == 0:
                self.log.info("File /home/system_mode has been updated.")
                return True
            else:
                self.log.info(f"Attempt to write the new system mode to /home/system_mode failed with exit code: {exit_status}")
                return False

    def clear_fpga_designs(self) -> bool:
        """
        This method is a no-op on the QxL as there is no FPGA flash storage to clear.
        """
        return True

    def get_fpga_designs(self) -> Tuple[int, int]:
        """
        The QxL does not store two FPGA designs in flash.
        """
        return 13, 0

    def get_fpga_design_flash_order(self):
        raise QxException(
            "get_fpga_design_flash_order() is not implemented for QxL - QxL does not store FPGA designs in flash module.")
