import enum
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Union

from autolib.coreexception import CoreException
from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.extendedenum import ExtendedEnum
from autolib.remotezipfile import RemoteZipFile
from autolib.ssh import SSHTools
from autolib.models.qxseries.session import DEFAULT_SESSION

LOG_FILE_PATH = '/transfer/log/loudness'


class LoudnessException(QxException):
    """
    An Exception subclass that represents some Analyser specific failure.
    """
    pass


@enum.unique
class LoudnessReset(ExtendedEnum):
    """\
    Reset operation types for the Loudness analyser feature.
    """
    LOUDNESSMONITORING = 'loudnessMonitoringReset'
    TRUEPEAKVALUE = 'truePeakValueReset'
    ERRORCOUNTS = 'errorCountsReset'


@enum.unique
class LoudnessControl(ExtendedEnum):
    """\
    Control actions for the loudness analyser.
    """
    START = 'start'
    STOP = 'stop'


class LoudnessLog:
    """\
    Provides access to loudness log archives from a Qx series device.
    """
    username: str = 'qxuser'
    password: str = 'phabrixqx'

    def __init__(self, baseurl, logger, hostname):
        self._baseurl = baseurl
        self.log = logger
        self.hostname = hostname
        self._ssh = SSHTools(logger, hostname)

    @property
    def latest_log(self) -> Union[str, None]:
        """\
        Get the filename of the most recently named loudness log file
        """
        file_list = self._ssh.remote_file_list(LOG_FILE_PATH)
        loudness_files = [x.rstrip() for x in file_list if x.startswith('loudness_') and x.endswith('.zip')]
        if loudness_files:
            loudness_files.sort()
            return loudness_files[-1]
        return None

    def latest(self) -> RemoteZipFile:
        """\
        Obtain a context manager that provides the most recently named loudness log file
        """
        log_file_path = Path(LOG_FILE_PATH) / self.latest_log
        return RemoteZipFile(log_file_path, self.log, self.hostname, LoudnessLog.username, LoudnessLog.password)

    def datetime(self, date_time: datetime) -> RemoteZipFile:
        """\
        Obtain a context manager that provides the loudness log file specified by the provided datetime

        :param date_time: The date and time of the logfile to access
        """
        latest_logfile_name = f'loudness_{date_time.strftime("%Y%m%d_%H%M%S")}.zip'
        log_file_path = Path(LOG_FILE_PATH) / latest_logfile_name
        return RemoteZipFile(log_file_path, self.log, self.hostname, LoudnessLog.username, LoudnessLog.password)


class Loudness(APIWrapperBase,
               url_properties={
                   "loudness_config": {"GET": "analyser/loudness/config", "PUT": "analyser/loudness/config",
                                       "DOC": "Get / Set the loudness analyser configuration"},
                   "loudness_info": {"GET": "analyser/loudness/info", "DOC": "Get the loudness info"}
               },
               http_session=DEFAULT_SESSION
               ):
    """\
    Access loudness features on a Qx series device.
    """
    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._ssh = SSHTools(logger, hostname)
        self._loudness_log = LoudnessLog(base_url, logger, hostname)

    @property
    def logs(self) -> LoudnessLog:
        """
        Access the loudness log methods and properties
        """
        return self._loudness_log

    @property
    def loudness_control(self) -> dict:
        """
        Returns the current status of the loudness monitor control field.

        :return: dict containing the current startus of the control field for the loudness monitor.
        """
        return self.loudness_config.get('control', {})

    @loudness_control.setter
    def loudness_control(self, control: LoudnessControl) -> None:
        """
        Sets the control field of the loudness monitor.

        :param control: Must be either LoudnessControl.START or LoudnessControl.STOP.
        """
        try:
            self.loudness_control = {'control': control.value}
        except CoreException as e:
            response = e.args[0].get("response", None)
            if response:
                raise LoudnessException(
                    f'{self._hostname}: {response.status_code} - {response.error_message} - Failed to carry out {control.value}.')
            else:
                raise LoudnessException(f'{self._hostname}: No response from request to reset loudness analyser')

    def loudness_reset(self, type_of_reset: LoudnessReset):
        """
        Method to enable the resetting of loudness monitor, true peak values and error count.

        :param type_of_reset: The reset operation to carry out.
        """
        try:
            self.loudness_config = {"action": type_of_reset.value}
        except CoreException as e:
            response = e.args[0].get("response", None)
            if response:
                raise LoudnessException(
                    f'{self._hostname}: {response.status_code} - {response.error_message} - Failed to carry out {type_of_reset.value}.')
            else:
                raise LoudnessException(f'{self._hostname}: No response from request to reset loudness analyser')
