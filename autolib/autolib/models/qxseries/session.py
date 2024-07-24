import functools
import requests

# We want to set the analyser requests timeout to 30s
DEFAULT_SESSION = requests.Session()
DEFAULT_SESSION.request = functools.partial(DEFAULT_SESSION.request, timeout=30)
