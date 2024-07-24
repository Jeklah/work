import platform
import subprocess

from autolib.coreexception import CoreException


def ping(host: str, verbose: bool = False) -> int:
    """
    Ping in an OS-agnostic way to determine the presence of a host.

    :param host: Hostname or IPv4 address
    :param verbose: Request more verbosity from ping
    :return: 0 if ping succeeded, a non-null value otherwise
    """
    # We'll support more OSes when we'll need them. CW, 20240417
    if (os_name := platform.system().lower()) not in ('windows', 'linux'):
        raise CoreException(f"Unsupported OS: {os_name}")
    count_param = '-n' if os_name == 'windows' else '-c'

    # On Windows, one cannot rely on the code returned by ping: if the target
    # host is found unreachable, Windows' ping return 0, i.e. 0% loss. So, we
    # need to analyse the display on stdout. Analysing ping's stdout consists in
    # analysing the first response from the target host, if any. That response
    # should contain the data of the round-trip the request executed.
    # CW, 20240417
    process_output = subprocess.run(('ping', f'{count_param}', '1', f'{host}'),
                                    text=True, stdout=subprocess.PIPE)
    if verbose:
        # Emulates what the Python 2.7 would do when subprocess.call() is
        # called and stdout is not redirected. The other solution is to
        # remove the support of a "verbose" option. CW, 20240417
        print(process_output.stdout)
    match os_name:
        case 'windows':
            ping_output = process_output.stdout.split('\n')
            if len(ping_output) < 3:
                return 1
            round_trip_data = ping_output[2]
            match round_trip_data.split(': '):
                case _, data:
                    return 0 if data.startswith('bytes=') else 1
                case _:
                    return 1
        case 'linux':
            return process_output.returncode

