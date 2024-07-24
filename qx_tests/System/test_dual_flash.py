"""
Tests that are specific to the Qx (not the QxL) that validate the fast switching feature added to the Qx
that stores two FPGA bit streams in flash and provides the ability to switch between them quickly. The QxL has a single
unified FPGA image that contains all modes so this facility does not need to exist on that platform.
"""    

import datetime
import logging
import tempfile
import urllib
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import pytest

from autolib.logconfig import autolib_log
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qx import Qx

log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def qx(test_qx_hostname):
    """
    Creates qx object for use in test case.
    """
    # These tests are Qx specific so we don't need to use the factory function make_qx
    qx = Qx(hostname=test_qx_hostname)
    original_operation_mode = qx.operation_mode
    log.info(f"FIXTURE: Qx {qx.hostname} setup complete")
    yield qx
    qx.operation_mode = original_operation_mode
    log.info(f"FIXTURE: Qx {qx.hostname} teardown complete")


@pytest.fixture
def operation_mode_list(qx):
    """
    Generates list of operation modes depending on whether SDI and SDI stress have been
    put into one mode.
    """
    log.info(
        f"Qx software version: {qx.about.get('Software_version', 'Unknown')}.{qx.about.get('Build_number', 'Unknown')}")
    if qx.comparable_version() < qx.COMBINED_SDI_VERSION:
        log.info('Pre-combined SDI mode version - SDI, SDI_STRESS, IP_2110, IP_2022_6')
        yield [OperationMode.SDI, OperationMode.SDI_STRESS, OperationMode.IP_2110, OperationMode.IP_2022_6]
    else:
        log.info('Combined SDI mode version - SDI, IP_2110, IP_2022_6')
        yield [OperationMode.SDI, OperationMode.IP_2110, OperationMode.IP_2022_6]


@pytest.fixture
def config():
    """
    Yields config json regarding maximum time limits upgrades should take.
    """
    yield {
        # The maximum time for flash_upgrade.sh to take with nothing to do
        'no_op_time': 10,

        # The maximum time for flash_upgrade.sh to take when just switching active partition time
        'fast_switch_time': 10,

        # The maximum time for flash_upgrade.sh to take with nothing to do
        'single_flash_program_time': 300,
    }


@pytest.mark.system
class TestDualFlashSuite:

    def test_empty_flash_boot_via_script(self, qx, config):
        """
        Test `flash_upgrade.sh <no parameters>`

        Confirm that with an empty flash store, flash_upgrade.sh with no parameters programs the 'expected' two designs.
        - Manually clear the FPGA design flash
        - Verify that the flash_upgrade.sh script correctly reprograms the flash partitions with
          what it considers should be in the two slots default values (SDI, IP 2110)
          - (Active: ???, Inactive: ???)
        - Verify that the active design is in the first position in the flash.
        """
        if type(qx) is not Qx:
            pytest.skip("This test is only appropriate for Qx devices.")

        # This method will assert if there is a problem with clearing the metadata and then flashing the default designs
        self._initialise_metadata(qx)

    def test_no_param_call_retains_current_good_state(self, qx, config):
        """
        Test `flash_upgrade.sh <no parameters>`

        Confirm  that with an empty flash store, flash_upgrade.sh with no parameters programs the 'expected' two designs.
        - Manually clear the FPGA design flash
        - Verify that the flash_upgrade.sh script correctly reprograms the flash partitions with
          what it considers should be in the two slots default values (SDI, IP 2110)
          - (Active: ???, Inactive: ???)
        - Verify that the unit retains current state after flash upgrade with no parameters.
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        log.info("Set the initial state (*active* SDI, *inactive* 2110)")
        self._initialise_metadata(qx)

        log.info("Program 2022-6 to backup and switch (*inactive* SDI, *active* 2022-6)")
        qx.set_operating_mode(OperationMode.IP_2022_6)
        assert (OperationMode.IP_2022_6, OperationMode.SDI) == qx.get_fpga_designs()
        assert (OperationMode.SDI, OperationMode.IP_2022_6) == qx.get_fpga_design_flash_order()

        log.info("Run flash_upgrade.sh with no parameters - should remain unchanged (*inactive* SDI, *active* 2022-6)")
        qx.set_operating_mode()
        assert (OperationMode.IP_2022_6, OperationMode.SDI) == qx.get_fpga_designs()
        assert (OperationMode.SDI, OperationMode.IP_2022_6) == qx.get_fpga_design_flash_order()

    @pytest.mark.slow
    def test_dual_design_into_flash(self, qx, operation_mode_list, config):
        """
        Test `flash_upgrade.sh boot_design backup_design`

        Iterate through all possible design combinations that can be stored in flash and verify unit status after
        running the flash_upgrade.sh script. No reboot.
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        self._initialise_metadata(qx)

        for boot_mode, backup_mode in self._operation_mode_combinations(operation_mode_list):
            log.info(f'Testing flash combination: Boot: {boot_mode} Backup: {backup_mode}')

            # Run script to load designs into flash and verify return True
            assert qx.set_operating_mode(boot_mode, backup_mode)

            # Verify that the unit reports current loads as loaded into flash
            assert (boot_mode, backup_mode) == qx.get_fpga_designs()

    def test_single_design_program(self, qx, operation_mode_list, config):
        """
        Test `flash_upgrade.sh boot_design`

        Confirm that the single parameter form of flash_upgrade.sh works as expected:

         - If the specified design is in the active slot, do nothing. [< 5s]
         - If the specified design is in the inactive slot, patch the bitstream to switch the active partition [< 10s]
         - If the specified design is not in either slot [< 300s]
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        self._initialise_metadata(qx)

        log.info("Switching to SDI (current active) - flash_upgrade.sh script should not change anything and exit quickly")
        start_timer = datetime.datetime.now()
        assert qx.set_operating_mode(OperationMode.SDI)
        assert (OperationMode.SDI, OperationMode.IP_2110) == qx.get_fpga_designs()
        assert (OperationMode.SDI, OperationMode.IP_2110) == qx.get_fpga_design_flash_order()
        end_timer = datetime.datetime.now()
        log.info(f'Switching to SDI (no-op) took {end_timer-start_timer}s')
        assert abs(end_timer-start_timer) < datetime.timedelta(seconds=config['no_op_time'])

        log.info("Switching to ST2110 (current backup) - flash_upgrade.sh script should not change anything and exit quickly")
        start_timer = datetime.datetime.now()
        assert qx.set_operating_mode(OperationMode.IP_2110)
        assert (OperationMode.IP_2110, OperationMode.SDI) == qx.get_fpga_designs()
        assert (OperationMode.SDI, OperationMode.IP_2110) == qx.get_fpga_design_flash_order()
        end_timer = datetime.datetime.now()
        assert abs(end_timer-start_timer) < datetime.timedelta(seconds=config['fast_switch_time'])
        log.info(f'Switching to IP 2110 (active partition switch) took {end_timer-start_timer}s')

        start_timer = datetime.datetime.now()
        assert qx.set_operating_mode(OperationMode.IP_2022_6)
        assert (OperationMode.IP_2022_6, OperationMode.IP_2110) == qx.get_fpga_designs()
        assert (OperationMode.IP_2022_6, OperationMode.IP_2110) == qx.get_fpga_design_flash_order()
        end_timer = datetime.datetime.now()
        log.info(f'Switching to 2022-6 (reprogram and active partition switch) took {end_timer-start_timer}s')
        assert abs(end_timer-start_timer) < datetime.timedelta(seconds=config['single_flash_program_time'])

    @pytest.mark.slow
    def test_single_design_into_boot_part(self, qx, operation_mode_list, config):
        """
        Test `flash_upgrade.sh boot_design`

        Test will cycle through all designs, programming each design into flash boot partition one at a time.
        Verify that the 2 designs are in the correct flash partition location after each execution of the script
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        self._initialise_metadata(qx)

        for new_mode in operation_mode_list:
            initial_boot, initial_backup = qx.get_fpga_designs()
            log.info(f'{qx.hostname} - Current flash state - Boot: {initial_boot} Backup: {initial_backup}')

            if new_mode == initial_boot:
                log.info(f'{qx.hostname} - Test param is currently stored in boot partition, no change needed')

                # Execute flash_upgrade.sh script using single argument
                assert qx.set_operating_mode(new_mode)
                assert (new_mode, initial_backup) == qx.get_fpga_designs()

            elif new_mode == initial_backup:
                log.info(f'{qx.hostname} - Test param is currently stored in backup partition, designs will swap')

                # Execute flash_upgrade.sh script using single argument
                assert qx.set_operating_mode(new_mode)
                assert (new_mode, initial_boot) == qx.get_fpga_designs()

            else:
                log.info(f'{qx.hostname} - Flashing {new_mode} FPGA design using single param script execution')

                # Execute flash_upgrade.sh script using single argument
                assert qx.set_operating_mode(new_mode)
                assert (new_mode, initial_boot) == qx.get_fpga_designs()

            new_boot, new_backup = qx.get_fpga_designs()
            # The flash memory should never include two copies of the same design
            assert (new_boot != new_backup)

    @pytest.mark.slow
    def test_swap_designs_in_flash_w_reboot(self, qx, config):
        """
        Test `flash_upgrade.sh boot_design backup_design`

        Get data for the current stored designs in flash and run script to swap boot > backup (and vice versa),
        verify that the designs are correctly swapped within a given time (configured in .ini file)
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        self._initialise_metadata(qx)

        # From the initial default setup switch mode to 2110 from SDI
        start_timer = datetime.datetime.now()
        assert qx.set_operating_mode(OperationMode.IP_2110, OperationMode.SDI)
        end_timer = datetime.datetime.now()
        log.info(f'{qx.hostname} - Script executed in {end_timer - start_timer}')
        assert abs(end_timer-start_timer) < datetime.timedelta(seconds=config['fast_switch_time'])
        assert (OperationMode.IP_2110, OperationMode.SDI) == qx.get_fpga_designs()

        # Reboot unit and wait
        qx.reboot()

        # Check the flash_state and running mode after reboot
        assert (OperationMode.IP_2110, OperationMode.SDI) == qx.get_fpga_designs()
        assert Qx.RestOperationModeMap[qx.about["firmware_mode"]] == OperationMode.IP_2110

        # Switch mode to SDI from 2110
        start_timer = datetime.datetime.now()
        assert qx.set_operating_mode(OperationMode.SDI, OperationMode.IP_2110)
        end_timer = datetime.datetime.now()
        log.info(f'{qx.hostname} - Script executed in {end_timer - start_timer}')
        assert abs(end_timer-start_timer) < datetime.timedelta(seconds=config['fast_switch_time'])
        assert (OperationMode.SDI, OperationMode.IP_2110) == qx.get_fpga_designs()

        # Reboot unit and wait
        qx.reboot()

        # Check the flash_state and running mode after reboot
        assert (OperationMode.SDI, OperationMode.IP_2110) == qx.get_fpga_designs()
        assert Qx.RestOperationModeMap[qx.about["firmware_mode"]] == OperationMode.SDI

    def test_rapid_switch(self, qx, config):
        """
        Test `flash_upgrade.sh boot_design`

        Switch between the two designs in flash making sure that it happens within the expected time each iteration.
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        self._initialise_metadata(qx)

        for boot, backup in ((OperationMode.IP_2110, OperationMode.SDI), (OperationMode.SDI, OperationMode.IP_2110)) * 10:
            start_timer = datetime.datetime.now()
            assert qx.set_operating_mode(boot)
            end_timer = datetime.datetime.now()

            assert abs(end_timer-start_timer) < datetime.timedelta(seconds=config['fast_switch_time'])
            assert (boot, backup) == qx.get_fpga_designs()

    def test_empty_flash_w_reboot(self, qx, config):
        """
        Test `flash_upgrade.sh <no parameters>`

        Confirm that with an empty flash store, flash_upgrade.sh with no parameters programs the 'expected' two designs.
        - Manually clear the FPGA design flash
        - Verify that the flash_upgrade.sh script correctly reprograms the flash partitions with
          what it considers should be in the two slots default values (SDI, IP 2110)
          - (Active: ???, Inactive: ???)
        - Verify that the active design is in the first position in the flash.
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        log.info(f"Before clear_fpga_designs, FPGA designs are: {qx.get_fpga_designs()}")
        log.info(f"Before clear_fpga_designs, FPGA design flash order is - {qx.get_fpga_design_flash_order()}")

        # Clear the MTD1 partition to reset the flash boot partitions
        assert qx.clear_fpga_designs()

        log.info(f"After clear_fpga_designs, FPGA designs are: {qx.get_fpga_designs()}")
        log.info(f"After clear_fpga_designs, FPGA design flash order is - {qx.get_fpga_design_flash_order()}")

        qx.reboot()

        active, inactive = qx.get_fpga_designs()
        first, second = qx.get_fpga_design_flash_order()

        log.info(f"After set_operating_mode, FPGA designs are - active: {active} inactive: {inactive}")
        log.info(f"After set_operating_mode, FPGA design flash order is - first: {first}, second: {second}")

        # Verify that the script has reprogrammed the empty flash partitions with default FPGA designs
        assert (OperationMode.SDI, OperationMode.IP_2110) == (active, inactive)

        # Verify that the active design is in the first slot.
        assert (active, inactive) == (first, second)

    @pytest.mark.skip(reason="Incomplete")
    def test_single_design_into_flash_w_reboot(self, qx, operation_mode_list, config):
        """
        Test `flash_upgrade.sh boot_design`

        For each FPGA design (operation mode):

        - Run flash_upgrade.sh script on unit w/ single argument to program FPGA design into flash boot partition
        - Reboot the unit via "reboot" shell command and wait for x seconds (configure via .ini file)
        - After reboot, verify that the flash store data is same as before
        - Verify that the unit is running in the correct mode
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        for operation_mode in operation_mode_list:

            flash_boot, flash_backup = qx.get_fpga_designs()
            log.info(f'{qx.hostname} - Current flash state - Boot: {flash_boot} Backup: {flash_backup}.')

            # Run script on unit with current design as single argument
            log.info(f'Testing single FPGA design program into flash: {operation_mode} ({operation_mode.fpga_design})')
            assert qx.set_operating_mode(operation_mode)

            # Get FPGA design store data from unit
            flash_state_boot, flash_state_backup = qx.get_fpga_designs()

            # Verify that the desired FPGA design has been programmed into the boot partition of the unit
            assert operation_mode.fpga_design == flash_state_boot

            log.info(f'{qx.hostname} + Current flash state: {flash_state_boot} - {flash_state_backup}. Rebooting the unit...')

            # Reboot unit and wait
            qx.reboot()

            # Get the new flash_state and running mode after reboot
            new_flash_state = qx.get_fpga_designs()
            new_running_mode = qx.about["firmware_mode"]
            log.info(f'Unit is running in {new_running_mode} mode. Current flash state is {new_flash_state}')

            # Query the unit for the FPGA designs loaded in flash and compare the to value programmed prior to reboot.
            assert (flash_state_boot, flash_state_backup) == new_flash_state

            # Verify the unit is running in the desired FPGA mode
            assert OperationMode.from_fpga_design(operation_mode) == new_running_mode

    @pytest.mark.slow
    def test_mode_after_upgrade(self, qx, config, operation_mode_list):
        """
        Test to ensure that when a Qx is upgraded that it boots into the mode that it was in prior to the upgrade.
        """
        if type(qx) != Qx:
            pytest.mark.skip("This test is only appropriate for Qx devices.")

        # We're going to test using the latest build from the release branch builder. We'll cache the file though
        # to make sure that the build at the url doesn't get updated halfway through the test.
        url = "http://jenkins:8080/job/GitLab%20Qx%20Linux%20Release%20Branch%20Build/lastSuccessfulBuild/artifact/sw/phab_qx_upgrade.bin"

        with tempfile.TemporaryDirectory() as temp_dir:
            filename = Path(urlparse(url).path).name
            downloaded_file, _ = urllib.request.urlretrieve(url, f"{temp_dir}/{filename}")
            upgrade_filename = Path(downloaded_file)

            qx.upgrade(file=upgrade_filename.as_posix(), force_name=True)

            for operation_mode in operation_mode_list:
                qx.operation_mode = operation_mode
                qx.reboot()
                assert operation_mode == qx.operation_mode
                qx.upgrade(file=upgrade_filename.as_posix(), force_name=True)
                assert operation_mode == qx.operation_mode

    def _operation_mode_combinations(self, mode_list):
        """
        Iterate through all valid combinations of boot and backup firmware operation modes.
        """
        for boot in mode_list:
            for backup in mode_list:
                if boot != backup:
                    yield boot, backup

    def _initialise_metadata(self, test_unit):
        """
        Clear the FPGA flash metadata and run the flash_upgrade.sh script with no parameters to program the
        default pair or designs into the flash (*active* SDI, *inactive* 2110)
        """
        log.info("Clearing the FGPA metadata and restoring default FPGA designs (First: SDI, Second: 2110, Active: SDI")

        log.info(f"Before clear_fpga_designs, FPGA designs are: {test_unit.get_fpga_designs()}")
        log.info(f"Before clear_fpga_designs, FPGA design flash order is - {test_unit.get_fpga_design_flash_order()}")

        # Clear the MTD1 partition to reset the flash boot partitions
        assert test_unit.clear_fpga_designs()
        log.info(f"After clear_fpga_designs, FPGA designs are: {test_unit.get_fpga_designs()}")
        log.info(f"After clear_fpga_designs, FPGA design flash order is - {test_unit.get_fpga_design_flash_order()}")

        # Calling set_operating_mode with default arguments will run the flash_upgrade.sh script as it would during Qx
        # unit boot process
        assert test_unit.set_operating_mode()
        active, inactive = test_unit.get_fpga_designs(debug=True)
        first, second = test_unit.get_fpga_design_flash_order(debug=True)
        log.info(f"After set_operating_mode, FPGA designs are - active: {active} inactive: {inactive}")
        log.info(f"After set_operating_mode, FPGA design flash order is - first: {first}, second: {second}")

        # Verify that the script has reprogrammed the empty flash partitions with default FPGA designs
        assert (OperationMode.SDI, OperationMode.IP_2110) == (active, inactive)

        # Verify that the active design is in the first slot.
        assert (active, inactive) == (first, second)

        return active, inactive, first, second
