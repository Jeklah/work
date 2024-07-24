import platform
import subprocess


def ping(host: str, verbose: bool = False) -> int:
    """
    Ping in an OS-agnostic way to determine the presence of a host.

    :param host: Hostname or IPv4 address
    :param verbose: Request more verbosity from ping
    :return: The exit code from ping
    """
    if platform.system().lower() == 'windows':
        count_param = '-n'
        null_redirect = '> NUL'
    else:
        count_param = '-c'
        null_redirect = '> /dev/null 2>&1'

    ping_command = f'ping {count_param} 1 {host}'
    if not verbose:
        ping_command += f' {null_redirect}'

    return subprocess.call(ping_command, shell=True)
