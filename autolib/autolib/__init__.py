import os
import logging
from autolib.logconfig import log_handler, autolib_log

args = {}

if os.environ.get("AUTOLIB_LOG_STDOUT", ""):
    args['log_to_stdout'] = True

if os.environ.get("AUTOLIB_LOG_DEBUG", ""):
    args['log_level'] = logging.DEBUG

filename = os.environ.get("AUTOLIB_LOG_FILENAME", "")
if filename:
    args['log_filename'] = filename

global_logger = log_handler(**args)
