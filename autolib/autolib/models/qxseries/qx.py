"""\
The qx module provides a Qx object used to access to various external interfaces on the Phabrix Qx (the REST API, SSH,
SFTP etc.) through methods and properties. This is not just a thin wrapper to API calls, much support code exists to
make the process of controlling, configuring and inspecting the state of the Qx trivial.
"""

import logging
import json
import re
import socket
import tempfile
import textwrap
import time
import urllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict
from uuid import uuid4

import paramiko
import requests

from autolib.models.devicecontroller import DeviceController
from autolib.models.qxseries.aesio import AESInputOutput
from autolib.models.qxseries.analyser import Analyser
from autolib.models.qxseries.ancillary import AncillaryInspector
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.eye import Eye
from autolib.models.qxseries.generator import Generator
from autolib.models.qxseries.input_output import SDIInputOutput
from autolib.models.qxseries.jitter import Jitter
from autolib.models.qxseries.loudness import Loudness
from autolib.models.qxseries.presets import PresetManager
from autolib.models.qxseries.ptp import Ptp
from autolib.models.qxseries.nmos import NmosClient
from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.sfp import SFPManagement
from autolib.ssh import SSHTools
from autolib.models.qxseries.ipnetworking import IPNetworking
from autolib.models.qxseries.timing import Timing
from autolib.logconfig import autolib_log
from autolib.remotebash import TemporaryRemoteScript
from autolib.ping import ping
from autolib.models.qxseries.session import DEFAULT_SESSION


class Qx(DeviceController):
    """
    This class can be used to configure, control and inspect a Qx.

    Once an instance of this class is created, controlling functions can be used to perform various test related actions
    and query the device for measurements statistics.
    """

    RestOperationModeMap = {
        'SDI': OperationMode.SDI,
        'SDI Stress Toolset': OperationMode.SDI_STRESS,
        'IP 2110': OperationMode.IP_2110,
        'IP 2022-6': OperationMode.IP_2022_6
    }

    # Mezzanine board models numbers supported by Qx
    mezzanine_revisions = {
        0: "No Mezzanine fitted",
        1: "PH070-01",
        2: "PH070-02",
        3: "PH070-03",
        5: "PH070-05",
        6: "PH070-06",
        7: "PH070-04",
        8: "PH070-05A - No EYE & JITTER",
        9: "PH070-05A - No EYE & JITTER",
        10: "PH070-06",
        11: "PH070-06 - No EYE & JITTER",
        12: "PH070-07",
        13: "PH070-07 - No EYE & JITTER",
        14: "PH070-08",
        15: "PH070-08 - No EYE & JITTER"
    }

    def __init__(self, hostname: str, http_session: requests.Session = None):
        """
        Constructor for a Qx class instance.

        An instance of a Qx can be created using a unit's hostname, IP address or serial number as demonstrated in the
        examples below::

            unit_1 = Qx(hostname="qx-020001")

        :param hostname: Create an instance of a Qx unit using the specified hostname
        :param http_session: A requests session may be used in place of the default sessions for the various API classes
        """

        self.log = logging.getLogger(autolib_log)
        self._ip = None
        self._hostname = hostname

        self._http_session = DEFAULT_SESSION if http_session is None else http_session

        # Get the IP address of the unit based on the hostname or automatically generated hostname built
        # from the serial number
        retry_count = 5
        while self._ip is None and retry_count > 0:
            try:
                self._ip = socket.gethostbyname(self._hostname)
            except socket.gaierror as err:
                self.log.error(f"Could not resolve hostname for {self._hostname}: {err}... retrying.")
                time.sleep(3)
                retry_count -= 1

        if retry_count == 0:
            raise QxException(f"Failed to obtain an IP address for Hostname: {self._hostname}")

        # Set the base URL for Rest API calls
        self._base_url = f"http://{self._hostname}:8080/api/v1/"

        # Add support for SSH command execution
        self._ssh = SSHTools(self.log, self._hostname)

        # Set up the subclasses that implement the feature specific APIs
        self._anc = AncillaryInspector(self._base_url, self.log, self._hostname, http_session)
        self._generator = Generator(self._base_url, self.log, self._hostname, http_session)
        self._analyser = Analyser(self._base_url, self.log, self._hostname, http_session, SDIInputOutput(self._base_url, self.log, self._hostname, http_session))
        self._eye = Eye(self._base_url, self.log, self._hostname, http_session)
        self._jitter = Jitter(self._base_url, self.log, self._hostname, self.eye, http_session)
        self._timing = Timing(self._base_url, self.log, self._hostname, self.eye, http_session)
        self._sdi_io = SDIInputOutput(self._base_url, self.log, self._hostname, http_session)
        self._aesio = AESInputOutput(self._base_url, self.log, self._hostname, http_session)
        self._sfp = SFPManagement(self._base_url, self.log, self._hostname, http_session, self)
        self._ip_net = IPNetworking(self._base_url, self.log, self._hostname, http_session)
        self._preset = PresetManager(self._base_url, self.log, self._hostname, http_session)
        self._nmos = NmosClient(self._base_url, self.log, self._hostname, self.__class__.__name__, http_session)
        self._loudness = Loudness(self._base_url, self.log, self._hostname, http_session)
        self._ptp = Ptp(self._base_url, self.log, self._hostname, http_session)

        self.COMBINED_SDI_VERSION = self._convert_version(4, 3, 0, 239)

        self.log.info(f"Created instance of Qx (Ip: {self._ip} Hostname: {self._hostname})")

        # The reboot command will set the uboot var 'bootdelay' to -2 (no delay and no check for abort). If SSH
        # is unavailable after an error, it will remain at this value. When Qx / QxL object is created, reset
        # this to the default value of 2.
        self.ssh.execute("fw_setenv bootdelay 2")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass

    @property
    def hostname(self):
        return self._hostname

    @property
    def essential_processes(self):
        return 'qx_server', 'qx_client'

    # Properties for accessing feature specific APIs

    @property
    def state_presets(self) -> Dict[OperationMode, str]:
        """\
        Returns a list of preset filenames that represent the 'current' state in each operation mode.
        """
        return {OperationMode.IP_2110: 'lastKnownState_ip2110',
                OperationMode.SDI: 'lastKnownState_sdi',
                OperationMode.IP_2022_6: 'lastKnownState_ip2022-6'}

    @property
    def ssh(self) -> SSHTools:
        """
        Access the `SSHTools` methods and properties
        """
        return self._ssh

    @property
    def anc(self) -> AncillaryInspector:
        """
        Access the `AncillaryInspector` methods and properties.
        """
        return self._anc

    @property
    def generator(self) -> Generator:
        """
        Access the `Generator` methods and properties
        """
        return self._generator

    @property
    def analyser(self) -> Analyser:
        """
        Access the `Analyser` methods and properties
        """
        return self._analyser

    @property
    def eye(self) -> Eye:
        """
        Access the `Eye` methods and properties
        """
        return self._eye

    @property
    def jitter(self) -> Jitter:
        """
        Access the `Jitter` methods and properties
        """
        return self._jitter

    @property
    def timing(self) -> Timing:
        """
        Access the `Timing` methods and properties
        """
        return self._timing

    @property
    def io(self) -> SDIInputOutput:
        """
        Access the `SDIInputOutput` methods and properties
        """
        return self._sdi_io

    @property
    def aesio(self) -> AESInputOutput:
        """
        Access the `AESInputOutput` methods and properties
        """
        return self._aesio

    @property
    def sfp(self) -> SFPManagement:
        """
        Access the `SFPMgmt` methods and properties
        """
        return self._sfp

    @property
    def ip_net(self) -> IPNetworking:
        """
        Access the IP methods and properties
        """
        return self._ip_net

    @property
    def preset(self) -> PresetManager:
        """
        Access the `PresetManager` methods and properties
        """
        return self._preset

    @property
    def nmos(self) -> NmosClient:
        """
        Access the `NmosClient` methods and properties
        """
        return self._nmos

    @property
    def loudness(self) -> Loudness:
        """
        Access the loudness methods and properties
        """
        return self._loudness

    @property
    def ptp(self) -> Loudness:
        """
        Access the PTP methods and properties
        """
        return self._ptp

    # Global config / status properties

    @property
    def about(self) -> dict:
        """
        Important information about the unit. Requires rest API access.
        """
        about_info = self._http_session.get(self._base_url + "system/about").json()

        if about_info.get("status", None) == 200:
            return {
                "hostname": self._hostname,
                "IP": self._ip,
                "Software_version": about_info["softwareVersion"],
                "software_branch": about_info['softwareBranch'],
                "Build_number": about_info["softwareNumber"],
                "Image_version": about_info["imageVersion"],
                "FPGA_version": about_info["fpgaVersion"],
                "sha": about_info["sha"],
                "firmware_mode": about_info["currentFirmwareMode"],
                "main_pcb_rev": about_info["mainBoardRevision"],
                "mezzanine_rev": about_info["mezzanineBoardRevision"],
                "device": about_info.get("device", "Qx"),
                "all": about_info
            }
        else:
            # If we cannot get this information it's likely that this is a terminal condition (either the rest interface
            # is disabled or something worse so raise an Exception (which calling code can call if it needs to).
            raise QxException("Failed to obtain the device about information from the rest API")

    @property
    def vnc(self) -> bool:
        """
        Property that returns the enabled state of VNC
        """
        response_data = self._http_session.get(self._base_url + "devtools/vnc?devtools=access").json()
        status = response_data.get("status", None)
        if status != 200:
            raise QxException(f"Attempt to obtain vnc state failed with status: {status}")
        else:
            return response_data.get("enabled", False)

    @vnc.setter
    def vnc(self, enable: bool):
        """
        Toggle bouncing box on generated stream
        :param enable: Bool value to toggle bouncing box on (True) or off (False)
        """
        data = {"enabled": enable}
        headers = {'devtools': 'access', 'Content-Type': 'application/json'}
        response_data = self._http_session.put(self._base_url + "devtools/vnc?devtools=access",
                                               json=data,
                                               headers=headers).json()
        status = response_data["status"]
        if status != 200:
            raise QxException(f"Failed to set VNC state via rest API. Response status: {status}")

        if enable:
            # Wait until we can connect to the VNC port
            assert self._port_scan({'VNC': 5900}, 10, 0.5)
        else:
            # Wait until we cannot connect to the VNC port
            assert self._wait_until_port_closed(5900, 10, 0.5)

        # Double check that the rest API reports VNC status is as requested
        assert self.vnc == enable

        # This is really annoying. Even after the request to turn off VNC returns with a 200 status and we've
        # waited for the VNC port (5900) to stop allowing connections AND have checked the VNC status via REST
        # screenshots can *still* fail with a 503 (VNC needs to be disabled). So here's a *rubbish* sleep to
        # avoid this for now.
        time.sleep(2)

    def _get_fpga_design(self):
        """
        Get the current FPGA design via a call to /usr/bin/fpgaver on the unit.
        """
        exit_status, stdout, stderr = self.ssh.execute("/usr/bin/fpgaver")
        fpgaver_output = stdout.decode()
        match = re.search(r'fpga_design_id: (?P<fw_ver>\d+)', fpgaver_output)
        if match:
            fpga_design = int(match.group('fw_ver'))
            self.log.info(f'FPGA design from fpgaver is {fpga_design}')
            return fpga_design
        self.log.info('Could not obtain the current FPGA design from fpgaver')
        return None

    def _get_system_mode(self):
        """
        Attempt to get the system mode from the unit by examining the /home/system_mode file if it exists (note:
        this file exists on v4.x upwards only).
        """
        exit_status, stdout, stderr = self.ssh.execute("cat /home/system_mode")
        if exit_status == 0:
            system_mode = int(stdout)
            self.log.info(f'Found system_mode file. System mode is reported as: {system_mode}')
            return system_mode
        self.log.info(f'Cannot find system_mode file.')
        return None

    def _convert_version(self, major: int, minor: int, patch: int, build: int) -> int:
        """
        Create a single int that can be used in version number comparisons.
        """
        if major > 255 or minor > 255 or patch > 255:
            raise QxException(f"Requested version number has major, minor and/or patch field(s) that are greater than 255: {major}.{minor}.{patch}-{build}")
        return (major * (256 ** 8)) + (minor * (256 ** 7)) + (patch * (256 ** 6)) + build

    def comparable_version(self):
        """
        Return the current software version (major.minor.patch.build) as a comparable integer value.
        """
        if (version_main := self.about.get('Software_version', None)) is None:
            raise QxException(f"Cannot get Software_version field from about()")
        if (build_number := self.about.get('Build_number', None)) is None:
            raise QxException(f"Cannot get Build_number field from about()")
        if build_number == "DEV-BUILD":
            build_number = (256 ** 6) - 1  # For DEV-BUILD builds assume the highest possible build number.
        valid_version = re.search(r'^(?P<major>\d{1,2})\.(?P<minor>\d{1,2})\.(?P<patch>\d{1,2})$', version_main)
        if valid_version:
            try:
                version = self._convert_version(
                    int(valid_version.group('major')),
                    int(valid_version.group('minor')),
                    int(valid_version.group('patch')),
                    int(build_number))
            except (KeyError, ValueError):
                raise QxException(f"Version_number in about does not confirm to n[n].n[n].n[n]: {version_main}")
        else:
            raise QxException(f"Version_number in about does not confirm to n[n].n[n].n[n]: {version_main}")
        return version

    def request_capability(self, capability):
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
                self.operation_mode = OperationMode.SDI
            elif capability in (OperationMode.IP_2110, OperationMode.IP_2022_6):
                self.operation_mode = capability
        else:
            if capability in OperationMode:
                self.operation_mode = capability
            else:
                raise QxException(f"Requested unknown capability: {capability}")

    def query_capability(self, capability) -> bool:
        """
        Return a boolean to indicate if the unit is in a mode that supported the requested capability. This method
        requires the REST API to be up and running so avoid using in the reboot() method until we're sure that the
        REST API is up.
        """
        if capability not in OperationMode:
            self.log.warning(f"Requested capability query ({capability}) is invalid.")
            return False

        version = self.comparable_version()
        current_op_mode = self.operation_mode

        if version >= self.COMBINED_SDI_VERSION:
            if capability in (OperationMode.SDI, OperationMode.SDI_STRESS) and current_op_mode in (OperationMode.SDI, OperationMode.COMBINED_SDI_QXL):
                return True
            elif capability == current_op_mode == OperationMode.IP_2110:
                return True
            elif capability == current_op_mode == OperationMode.IP_2022_6:
                return True
        else:
            if capability in OperationMode:
                return current_op_mode == capability

        return False

    @property
    def operation_mode(self) -> OperationMode:
        """
        The current Qx operation mode. Requires SSH access to the device. This will attempt to get the system_mode from
        a marker file in /home on 4.x versions of software and then will fall back on the FPGA design number returned
        by the /usr/bin/fpgaver tool for older Qx units. The OperationMode object returned has properties to obtain the
        FPGA design index and the system mode index (new as of v4.x).
        """
        fpga_design = self._get_fpga_design()

        # Check that the FPGA design isn't reporting the combined QxL design
        if fpga_design and fpga_design != 13:
            return OperationMode.from_fpga_design(fpga_design)
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

    def reboot(self, block_until_ready: bool = True):
        """
        Reboot the Qx and optionally wait for the Qx to return to a 'usable' state.
        """

        try:
            self.ssh.execute("fw_setenv bootdelay -2")
            self.log.warning(f"Sending reboot command to Qx {self._hostname} - {self._ip}")
            self.ssh.execute("reboot")

            if block_until_ready:
                # Wait until we are actually rebooting
                self.block_until_unpingable()

                # Wait for reboot to complete
                self.block_until_ready()
        finally:
            self.ssh.execute("fw_setenv bootdelay 2")

    def restore_initial_state(self, *args, **kwargs):
        """\
        Restore the device to a 'known-good' initial state. This will potentially clear any installed configuration
        or settings files.

        :presets: list[str] List of preset filenames to delete (defaults to all lastKnown preset files for the current
                  device type.
        """
        presets_list = kwargs.get("presets", self.state_presets)
        for _, preset_file in presets_list.items():
            try:
                self.ssh.remove_via_sftp(f'/transfer/presets/{preset_file}.preset')
            except FileNotFoundError:
                self.log.warning(f"Failed to delete /transfer/presets/{preset_file} from unit as qxuser.")

        self.reboot()

    def take_screenshot(self) -> str:
        """
        Take a screenshot on the Qx. Note: This will disable VNC before the screenshot and then re-enable it afterwards.
        :returns: The name of the screenshot file on the Qx.
        """
        initial_vnc_state = self.vnc

        if initial_vnc_state:
            self.log.info("Disabling VNC to allow screenshot to be taken - will be re-enabled afterwards")
            self.vnc = False

        response = self._http_session.post(f'http://{self._hostname}:8080/api/v1/screenshots/images')
        if response.status_code == 200:
            # Decode the content of the response and load into JSON format
            content = response.json()
            try:
                # Return the filename of the saved image on the unit
                return content['filename']
            except AttributeError as err:
                raise QxException(f"Attempt to take screenshot failed - {err}")
            finally:
                if initial_vnc_state:
                    self.log.info("Re-enabling VNC")
                    time.sleep(2)
                    self.vnc = True
        else:
            self.log.error(f'Failed to take screenshot - {response.status_code} - {response.content}')
            if initial_vnc_state:
                self.log.info("Re-enabling VNC")
                time.sleep(2)
                self.vnc = True

    def clear_fpga_designs(self) -> bool:
        """
        Function will run bash commands on the unit to erase the MTD1 flash partition. Use to verify tests are
        performed from a clean slate.
        :return: Bool
        """
        script = """
            echo 1 > /sys/class/gpio/gpio175/value 
            flash -v -e -d /dev/mtd1 
            echo 0 > /sys/class/gpio/gpio175/value
        """

        with TemporaryRemoteScript(self.log, self._hostname, "root", "PragmaticPhantastic", textwrap.dedent(script)) as temp_script:
            exit_status, stdout, stderr = temp_script.execute()

            for line in stderr.decode().splitlines():
                self.log.info(f'[clear_fpga_designs]\t{line}')

            # Retry once a second - if 10s elapse without the required state, consider it a fail, else pass
            for retry in range(10):
                if self.get_fpga_designs() == (OperationMode.NONE, OperationMode.NONE):
                    return True
                time.sleep(1)
            return False

    def get_fpga_designs(self, **kwargs) -> tuple:
        """
        Function will execute a script on Qx device and return a list containing the 2 FPGA designs currently loaded
        into flash. The first item is the 'active' design, the second the 'inactive' one. Their order does not
        indicate their order in flash (the 'active' design may be in the first or second slot).

        :return: Tuple of 2 OperationMode enum values (active, inactive)
        """

        debug_enabled = kwargs.get('debug', False)

        exit_status, stdout, stderr = self.ssh.execute(f'bash {"-x " if debug_enabled else ""}/usr/bin/dump_stored_designs.sh')
        design_store = ()

        # Store the 2 fpga design values in list
        for line in stdout.decode().splitlines():
            self.log.info(f'[dump_stored_designs.sh]\t {line}')
            match = re.search(r'^(?P<boot>\d{1,2}) (?P<backup>\d{1,2})', line)
            if match:
                design_store = OperationMode.from_fpga_design(int(match.group('boot'))), OperationMode.from_fpga_design(int(match.group('backup')))
                break

        if len(design_store) == 2:
            self.log.info(f"{self._hostname} - Boot (Active): {design_store[0]} ({design_store[0].fpga_design}), Backup (Inactive): {design_store[1]} ({design_store[1].fpga_design})")

            if design_store[0] == design_store[1]:
                self.log.warning(f"{self._hostname} - Boot and backup design store values are identical")

            return design_store
        else:
            raise QxException(f"{self._hostname} - FPGA design list is invalid {design_store}")

    def get_fpga_design_flash_order(self, **kwargs) -> tuple:
        """
        Function will execute a script on Qx device and return a list containing the 2 FPGA designs currently loaded
        into flash in the order that they're programmed.

        :return: Tuple of 2 OperationMode enum values indicating the flash order

        """
        debug_enabled = kwargs.get('debug', False)

        unit_sw_version = float(self.about["Software_version"][0:3])

        if 3.2 < unit_sw_version < 4.0:
            script = """
                #!/bin/bash
                . /usr/bin/upgrade_functions.sh
                getDesigns
                echo "${storedFlashDesigns[0]} ${storedFlashDesigns[1]}"
            """
        elif unit_sw_version >= 4.0:
            script = """
                #!/bin/bash
                . /usr/bin/upgrade_functions.sh
                getDesigns ${fpgaInfoDev}
                echo "${storedDesigns[0]} ${storedDesigns[1]}"
            """
        else:
            raise QxException("Software version does not support multiple FPGA images in flash")

        with TemporaryRemoteScript(self.log, self._hostname, "root", "PragmaticPhantastic", textwrap.dedent(script)) as temp_script:
            firmware_entry = ()
            exit_status, stdout, stderr = temp_script.execute(debug=debug_enabled)

            for line in stdout.decode().splitlines():
                self.log.info(f'[get_fpga_design_flash_order]\t {line}')
                match = re.search(r'^(?P<boot>\d{1,2}) (?P<backup>\d{1,2})', line)
                if match:
                    firmware_entry = OperationMode.from_fpga_design(int(match.group('boot'))), OperationMode.from_fpga_design(int(match.group('backup')))
                    break

            if len(firmware_entry) == 2:
                self.log.info(f"{self._hostname} - First: {firmware_entry[0]} ({firmware_entry[0].value}), Second: {firmware_entry[1]} ({firmware_entry[1].value})")

                if firmware_entry[0] == firmware_entry[1]:
                    self.log.warning(f"{self._hostname} - First and second design store values are identical")

                return firmware_entry
            else:
                raise QxException(f"{self._hostname} - FPGA flash order is invalid {firmware_entry}")

    def set_operating_mode(self, boot: OperationMode = OperationMode.CURRENT, backup: OperationMode = OperationMode.CURRENT) -> bool:
        """
        Function to run the FPGA flash script on Qx unit and set the operating mode. Please use the 'operating_mode'
        property in preference to this method as it will check that a change is needed before attempting a change.

        Check the s/w version on the unit and run the appropriate FPGA flashing operation appropriate to
        the s/w.

        In v3.3 onwards, dual FPGA designs can be stored in flash memory allowing the user to switch between
        2 designs without having to re-flash. Prior to this version, only a single design can be stored in flash so
        requires legacy flashing method.

        When executing a dual flash (on units > v3.2), the function will output stdout of the Qx flash_upgrade.sh script.

        NOTE: This method (unlike the operation_mode property setter) does not check that the unit is available before
        attempting to set the mode. For this reason it's advised that the operation_mode property be used where possible
        rather than this method.

        :param boot: The FPGA design type that will be loaded as the booting design as an OperationMode
        :param backup: The FPGA design that will be loaded as the backup design, allowing faster switching to this mode
                       as an OperationMode.
        :return: bool
        """

        # Check the current running software on the unit. Can unit run dual flash fpga programming script?
        # if the sw version is <= 3.2, we need execute legacy flash programming script
        current_fw_mode = self.about["firmware_mode"]
        unit_sw_version = float(self.about["Software_version"][0:3])
        self.log.info(
            f'{self._hostname} - Unit is currently running v{unit_sw_version} in {current_fw_mode} mode')

        if unit_sw_version >= 3.2:
            return self._set_operating_mode_dual(current_fw_mode, boot, backup)
        else:
            return self._set_operating_mode_single(current_fw_mode, boot, backup)

    def _set_operating_mode_dual(self, _, boot, backup):
        """
        Qx 3.3 introduced a change to the way that FPGA designs are stored in flash (now 2 for quicker mode switching).
        This method should be used for 3.3 - 3.x (x>3) versions.
        """
        current_boot, current_backup = self.get_fpga_designs()
        self.log.info(f'Setting dual flash designs to {boot} & {backup}')
        self.log.info(f'FPGA designs in flash are currently {current_boot} & {current_backup}')
        # http://phabrixwiki/mediawiki/index.php/Qx_flash_upgrade_script
        # Runs the flash_upgrade script wit 2 args (1st = fpga to load / 2nd = fpga to load into flash)
        # If both boot and backup operation mode are 'current' (from the wiki page):
        #   flash_upgrade without any parameters will attempt to ensure that the FPGA designs it thinks should be
        #   programmed and working ARE programmed and working.
        if boot == OperationMode.CURRENT and backup == OperationMode.CURRENT:
            self.log.info("Running flash_upgrade.sh script w/o arguments. As s/w upgrade")
            command_line = "bash -x /usr/bin/flash_upgrade.sh"
            self.log.info(f"SSH command line: {command_line}")
            exit_status, stdout, stderr = self.ssh.execute(command_line, 300)

        else:
            # If boot is not current but backup is (from the wiki page):
            #   flash_upgrade with one parameter will attempt to make the FPGA design that matches that parameter
            #   (the design id) the booting, active design. If it's not within the flash somewhere, it will attempt
            #   to program it in a spare area and then make that active.
            if boot != OperationMode.CURRENT and backup == OperationMode.CURRENT:
                self.log.info(f"Store single FPGA design into flash (Using \"boot\" var ({str(boot.value.fpga_design)}))")
                command_line = f"/usr/bin/flash_upgrade.sh {str(boot.value.fpga_design)}"
                self.log.info(f"SSH command line: {command_line}")
                exit_status, stdout, stderr = self.ssh.execute(command_line, 300)

            # Finally if both are something other than current (from the wiki page):
            #  flash_upgrade with two parameters will attempt to ensure both designs are within flash and that the
            #  first listed will be booted.
            else:
                self.log.info("Store dual FPGA design into flash using current value for boot")
                target_boot = current_boot if boot == OperationMode.CURRENT else boot
                target_backup = current_backup if backup == OperationMode.CURRENT else backup
                command_line = f"/usr/bin/flash_upgrade.sh {str(target_boot.value.fpga_design)} {str(target_backup.value.fpga_design)}"
                self.log.info(f"SSH command line: {command_line}")
                exit_status, stdout, stderr = self.ssh.execute(command_line, 300)

        partition_order = []
        flash_boot_location = None

        self.log.info("---------- Start of flash_upgrade.sh output ----------")

        for line in stdout.decode().splitlines():            
            self.log.info(f'[flash_upgrade_script.sh]\t {line}')

            # Scrape some important info from stdout:
            #   - Address in flash to jump to
            #   - Flash partition order
            if "Writing address:" in line:
                flash_boot_location = line.split(" ")[-2:][0]

            # Multiple references to "partition" but all will throw IndexError except the one we want
            try:
                if "partition" in line:
                    partition_order.append(int(line.split(":")[1].strip("\n")))
            except IndexError:
                pass

        self.log.info("---------- End of flash_upgrade.sh output ----------")

        self.log.info(f'{self._hostname} set_operating_mode (dual firmware flash mode)')
        self.log.info(f'{self._hostname} \tFlash partition contents before: {current_boot} {current_backup}')
        self.log.info(f'{self._hostname} \tFlash partition contents after : {self.get_fpga_designs()}')
        self.log.info(f'{self._hostname} \tFlash partition order: {partition_order}')
        self.log.info(f'{self._hostname} \tFlash jump to: {flash_boot_location}')

        # If partition A is set as the flash jump to, verify flash boot is set correctly
        try:
            if partition_order[0] == 0:
                if not flash_boot_location == "0x00000000":
                    self.log.info("Partition 0 is boot but \"Jump to\" = {}".format(flash_boot_location))
                    return False
        except IndexError:
            self.log.info("Got index error with partition_order: {}".format(partition_order))
            pass
        return True

    def _set_operating_mode_single(self, current_fw_mode, boot, _):
        """
        The legacy FPGA switching that should be used if the unit reports a software version below 3.2
        """
        self.log.info(
            f"Execute OLD FGPA flash mechanism... Flashing FPGA with design assigned as \"active\": {str(boot.value.fpga_design)}")

        if self.RestOperationModeMap[current_fw_mode] == boot.value:
            self.log.info("Unit is already running as {}, nothing to do here.".format(current_fw_mode))
            return True

        remount_and_write_file = [
            "mount -o remount,rw,sync /mnt/board_storage",
            f"echo {str(boot.value.fpga_design)} > /mnt/board_storage/fpga_design",
        ]

        for cmd in remount_and_write_file:
            self.log.info("Executing:\t{}".format(cmd))

        # Check the contents of the "fpga_design" file for the desired fpga type number
        command_line = "cat /mnt/board_storage/fgpa_design"
        self.log.info(f"Executing:\t{command_line}")
        exit_status, stdout, stderr = self.ssh.execute(command_line)
        stdout = stdout.splitlines()[0]
        self.log.info(f"\t\tfpga_design file contents = {stdout}")

        # If the contents of the file matches desired fpga type number
        if int(stdout) == int(boot.value.fpga_design):

            cleanup_cmds = [
                "mount -o remount,ro,sync /mnt/board_storage"
            ]

            for cmd in cleanup_cmds:
                self.log.info(f'Executing:\t{cmd}')
                self.ssh.execute(cmd)
            return True
        else:
            self.log.info("could not execute cmd, fpga_design contents is not correct")
            return False

    def block_until_unpingable(self, retries: int = 10, delay: int = 10) -> bool:
        """
        Try pinging the unit with a specified delay for a specified number of times until
        the unit fails to respond. We will assume that if the unit cannot be pinged, it is rebooting
        or has failed.
        """
        for retry_count in range(retries):
            try:
                if not ping(self._hostname):
                    time.sleep(delay)
                    self.log.warning("Management interface responded to ping while waiting for reboot - retrying...")
                else:
                    self.log.info("Management interface stopped responding to pings while waiting for reboot")
                    return True
            except socket.gaierror as e:
                print(e)
            except requests.ConnectionError as e:
                print(e)
            except paramiko.ssh_exception.NoValidConnectionsError as e:
                print(e)
            except KeyboardInterrupt:
                break

        raise QxException(f"Management interface incorrectly responded to ping after {retries} attempts while waiting for reboot.")

    def block_until_ready(self, ping_count: int = 100, ping_delay: float = 15.0):
        """
        Block until the Qx is ready to be controlled. This is determined through a number of stages that
        are increasingly close to the operation of the Qx software / firmware (starting with basic ICMP
        pings). All the methods called here raise exceptions in the event of failures.
        """
        # Try pinging the unit 100 times every 15 seconds
        if not self.ping_mgmt_iface(ping_count, ping_delay):
            raise QxException(f"Management interface did not respond to ping after {ping_count} attempts.")
        self._wait_until_ssh_ready()
        self._wait_for_named_processes(self.essential_processes)
        self._rest_checks()

        protocol_ports = {
            'ssh': 22,
            'http': 80,
            'REST': 8080
        }

        if self.query_capability(OperationMode.IP_2110) and self.nmos.enabled:
            self._wait_for_named_processes(('qx_nmosclient', ))
            protocol_ports['NMOS'] = 3000

        if self.vnc:
            protocol_ports['VNC'] = 5900

        self._port_scan(protocol_ports)
        self._wait_until_getaddrinfo()
        self.log.info("Qx is now available, block_until_ready succeeded")

    def _wait_until_getaddrinfo(self, retries: int = 10, delay: int = 15) -> bool:
        """
        Call socket.getaddrinfo() with the unit's hostname and block until a successful response or retry count is met.

        :param retries: Number of times to attempt address lookup
        :param delay:
        """
        for retry_count in range(retries):
            try:
                address_info = socket.getaddrinfo(self._hostname, 0)
            except socket.gaierror as _:
                time.sleep(delay)
                continue

            if address_info:
                self.log.info(f'Device DNS / mDNS name lookup succeeded. getaddrinfo() returned {address_info}')
                return True

        raise QxException("Could not lookup IP address from hostname using getaddrinfo.")

    def ping_mgmt_iface(self, retries: int = 1, delay: float = 1.0) -> bool:
        """
        Try pinging the unit with a specified delay for a specified number of times until
        the unit responds. If it responds, return True otherwise False
        :param retries: Number of times to try pinging the management iface (1 or more)
        :param delay: Delay in seconds between retries (no effect if retries == 1)
        """
        retries = 1 if retries < 1 else retries
        for retry_count in range(retries):
            try:
                if not ping(self._hostname):
                    self.log.info(f"Management interface responded to ping after {retry_count+1} attempts.")
                    return True
                else:
                    time.sleep(delay)
                    self.log.warning(f"Management interface did not respond to ping after {retry_count+1} attempts - retrying...")
            except socket.gaierror as e:
                print(e)
            except requests.ConnectionError as e:
                print(e)
            except paramiko.ssh_exception.NoValidConnectionsError as e:
                print(e)
            except KeyboardInterrupt:
                break

        return False

    def _wait_until_ssh_ready(self, retries: int = 7, delay: int = 10) -> bool:
        """
        Try executing a command via ssh periodically until it succeeds of the test limits are
        reached.
        """
        for retry_count in range(retries):
            try:
                _, stdout, _ = self.ssh.execute(f'echo "alive"')
                if len(stdout) > 0:
                    self.log.info(f'SSH Ready after {retry_count} retries.')
                    return True
                else:
                    time.sleep(delay)
                    self.log.warning("Could not execute command via SSH - retrying...")
            except socket.gaierror as e:
                print(e)
            except requests.ConnectionError as e:
                print(e)
            except paramiko.ssh_exception.NoValidConnectionsError as e:
                print(e)
            except KeyboardInterrupt:
                break

        raise QxException(f"Could not execute command via SSH after {retries} attempts.")

    def _wait_for_named_processes(self, required_procs, retries: int = 10, delay: int = 10) -> bool:
        """
        Call pgrep on the unit to see if the critical system processes are running. For each
        process in turn examine the process table 10 times with a 10s delay between each test.
        """
        for proc in required_procs:
            for retry in range(retries):
                # pgrep (due to how it uses procfs) appears to truncate process names to 15 characters so truncate
                # the process name (we want an exact match so using a matching pattern is not appropriate).
                exit_status, stdout, stderr = self.ssh.execute(f"pgrep {proc[:15]}")
                stdout_response = stdout.decode().rstrip('\n')
                if len(stdout_response) != 0:
                    # The pgrep process reported at least one process id so move to the next
                    self.log.info(f"PID for process {proc} is {str(stdout_response)}")
                    break
                else:
                    if retry == retries - 1:
                        raise QxException(f"Failed to find process {proc} after {retries} attempts")
                    else:
                        self.log.warning(f"Failed to find process {proc}, retrying...")
                        time.sleep(delay)
        self.log.info(f'All critical processes are ready.')
        return True

    def _rest_checks(self, retries: int = 10, delay: int = 10) -> bool:
        """
        Check some critical rest API endpoints
        """
        from pprint import pformat

        for retry in range(retries):
            try:
                # At the moment let's just try and get the about information via the property
                _ = self.about
                break
            except (requests.exceptions.ConnectionError, QxException) as err:
                if retry == retries - 1:
                    raise QxException(f"Failed to to obtain system about info via rest API after {retries} attempts")
                else:
                    self.log.warning(f"Failed to to obtain system about info via rest API ({err}), retrying...")
                    time.sleep(delay)

        self.log.info(f"Rest API is responding")
        self.log.info(pformat(self.about))
        return True

    def _port_scan(self, protocol_ports, retries: int = 10, delay: float = 10) -> bool:
        """
        Attempt to connect to various critical ports on the Qx.
        """
        try:
            for protocol, port in protocol_ports.items():
                for retry in range(retries):
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        s.connect((self._hostname, port))
                        self.log.info(f"Successfully connected to port {port} for protocol {protocol}")
                        break

                    except ConnectionRefusedError:
                        if retry == retries - 1:
                            raise QxException(f"Failed to connect to port {port} for protocol {protocol} after {retries} attempts")
                        else:
                            self.log.warning(f"Failed to connect to port {port} for protocol {protocol} after {retry +1} attempts, retrying...")
                            time.sleep(delay)
                    finally:
                        s.close()
        except OSError:
            raise QxException(f"Cannot connect to unit: {self._hostname} ({self._ip})")

        self.log.info(f"All important ports are listening")
        return True

    def _wait_until_port_closed(self, port, retries: int = 10, delay: float = 10) -> bool:
        """
        Block until the specified port cannot be connected to or the max retries / delay are met
        """
        s = None

        try:
            for retry in range(retries):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect((self._hostname, port))
                    if retry == retries - 1:
                        raise QxException(f"Port {port} still accepting connections after {retries} attempts")
                    else:
                        self.log.warning(f"Port {port} still accepting connections after {retry + 1} attempts, retrying...")
                        time.sleep(delay)
                except ConnectionRefusedError:
                    self.log.info(f"Port {port} no longer accepting connections")
                    break

        except OSError:
            raise QxException(f"Cannot connect to unit: {self._hostname} ({self._ip})")

        finally:
            if s:
                s.close()

        return True

    def upgrade(self, **kwargs):
        """
        Upgrade the Qx software. Raises a QxException on failure.
        """
        force_name = kwargs.get('force_name', False)

        if 'url' in kwargs.keys() and 'file' in kwargs.keys():
            raise QxException("Upgrade requires either 'url' or 'file' keyword argument to be supplied, not both")
        elif 'url' in kwargs.keys():
            upgrade_url = kwargs.get('url', None)
            if upgrade_url:
                self._upgrade_from_url(upgrade_url, force_name)
        elif 'file' in kwargs.keys():
            upgrade_file = kwargs.get('file', None)
            if upgrade_file:
                self._upgrade_from_file(upgrade_file, force_name)
        else:
            raise QxException("Upgrade requires either 'url' or 'file' keyword argument to be supplied")

        self.log.info('Upgrade completed successfully')

    def _upgrade_from_file(self, filepath: str, force_name: bool = False):
        """
        Upgrade the Qx from a file name and path. Raises a QxException on failure.
        """
        # Check file exists
        file_path = Path(filepath)
        if not force_name:
            remote_filename = file_path.name
        else:
            remote_filename = "phab_qx_upgrade.bin"
        remote_file = Path('/transfer/upgrade') / remote_filename
        self.block_until_ready()
        if file_path.exists():
            self.log.info(f"Upgrading from file: {filepath}")
            self.ssh.upload_via_sftp(str(filepath), remote_file.as_posix())
            self.block_until_unpingable()
            self.block_until_ready()
        else:
            raise QxException(f"Upgrade file does not exist: {filepath}")

    def _upgrade_from_url(self, url: str, force_name: bool = False):
        """
        Download a Qx upgrade .bin file from an URL and upgrade the Qx with it. Raises a QxException on failure.
        :param url: An urlencoded string containing a valid URL
        :force_name: For the name of the upgraded file to 'phab_qx_upgrade.bin'
        """
        try:
            self.block_until_ready()
            with tempfile.TemporaryDirectory() as temp_dir:
                filename = Path(urlparse(url).path).name
                downloaded_file, _ = urllib.request.urlretrieve(url, f"{temp_dir}/{filename}")
                upgrade_filename = Path(downloaded_file)

                if not force_name:
                    remote_filename = upgrade_filename.name
                else:
                    remote_filename = "phab_qx_upgrade.bin"

                remote_file = Path('/transfer/upgrade') / remote_filename
                self.log.info(f"Upgrading from url: {url}")
                self.log.info(f"Uploading {upgrade_filename} to {remote_file} on Qx {self._hostname} - {self._ip}")
                self.ssh.upload_via_sftp(str(upgrade_filename), remote_file.as_posix())
                self.block_until_unpingable()
                self.block_until_ready()
        except urllib.error.URLError as err:
            raise QxException(f"Failed to download upgrade file at URL: {url} - Error was {err}")

    def get_sensor_dict(self) -> dict:
        """
        Get the details of all sensors via the REST API devtools/sensors
        """
        response = self._http_session.get(self._base_url + "devtools/sensors?devtools=access")

        if response.status_code != 200:
            raise QxException(f'Attempt to obtain sensor status dictionary failed with status: {response.status_code} : {response.json().get("message", "No message")}')
        else:
            return response.json()

    def get_sensor_temp(self) -> dict:
        """
        Return the output of command line tool 'sensors' in dict format
        """
        # TODO: Take temperature dict as argument, log any increase / decrease in sensor temp values (using DeepDiff)
        # TODO: Can be gleaned from rest: http://qx-020437:8080/api/v1/devtools/sensors

        exit_status, stdout, stderr = self.ssh.execute("sensors")
        stdoutput = stdout.decode().splitlines()

        temp_dict = {}
        current_key = None

        for line in stdoutput:
            split_line = line.split(":")

            # Determine dictionary keys (adapter names)
            if "\n" not in split_line and len(split_line) == 1 and split_line[0]:

                if len(split_line[0].split(" ")) != 1:
                    continue

                current_key = split_line[0].strip("\n")
                temp_dict.update({current_key: {}})

            # Determine dictionary values (adapter temp)
            elif len(split_line) == 2:

                value_key = split_line[0]
                value_value = split_line[1].strip("\n")

                temp_dict[current_key].update({value_key: value_value.strip(" ")})

        return temp_dict

    def verify_mezzanine_board(self):
        """
        Will return TRUE if the current mezzanine board on the unit is contained in the mezzanine_revisions dictionary,
        if not found, function will return FALSE
        """
        mezz_rev_no = int(self.about["mezzanine_rev"])
        self.log.info(self._hostname + " - Current mezzanine PCB rev is %s (%s)" % (hex(mezz_rev_no), Qx.mezzanine_revisions[mezz_rev_no]))
        return True if mezz_rev_no in Qx.mezzanine_revisions.keys() else False


class TemporaryPreset:
    """\
    Context manager that will upload and activate a preset on a Qx / QxL at the start of scope and then remove is
    at the end of scope for use in tests and test fixtures.
    """
    def __init__(self, qx, preset_file, preset_name):
        self._qx = qx
        self._preset_file = preset_file
        self._preset_name = preset_name

    def __enter__(self):
        self._qx.preset.upload(self._preset_file, self._preset_name)
        self._qx.preset.load(self._preset_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._qx.preset.delete(self._preset_name)


class StateSnapshot:
    """\
    Sometimes it's necessary to gain read-only access to a datacore that's not exposed by the Rest API. The only
    way to do this currently is to create a preset and download it and convert the JSON to a dict. This context
    manager makes this all a little easier by automating the process of creation, downloading, parsing and
    ultimately deletion of the temporary preset. e.g.:

      with StateSnapshot(qx) as snapshot:
          print(snapshot.state)

    """

    def __init__(self, qx):
        self._qx = qx   # The Qx that we want to create a state snapshot from
        self._temp_dir = None   # The local temp directory where we store the downloadedpreset
        self._state_preset_temp_name = None  # A generated temporary name for the new preset
        self._state_file = None  # A local temp file containing the preset
        self._state = None  # Holds a dict snapshot of the state obtained from the new device preset
        self.log = logging.getLogger(autolib_log)

    def __enter__(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self._state_preset_temp_name = str(uuid4())

        self.log.info(f"Creating a temporary StateSnapshot: {self._state_preset_temp_name}")

        remote_preset_filename = self._qx.preset.create(self._state_preset_temp_name)
        local_preset_filename = Path(self._temp_dir.name) / f'{remote_preset_filename}'
        self._qx.preset.download(self._state_preset_temp_name, local_preset_filename.as_posix())

        with open(local_preset_filename, "rt") as _state_file:
            self._state = json.load(_state_file)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log.info(f"Removing temporary StateSnapshot: {self._state_preset_temp_name}")
        self._temp_dir.cleanup()
        self._qx.preset.delete(self._state_preset_temp_name)

    @property
    def state(self):
        return self._state
