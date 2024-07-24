"""
Set of utility functions for manipulating log files created by Event Logging.

Note: in the eventLogging files, only the date is in Julian date format. The
"msecsSinceStartOfDay" field is merely the number of milliseconds since the
start of the date, not the Julian date's fractional part.
"""

import datetime
import copy
import functools
import gzip
import json
import time

from autolib.coreexception import CoreException  # type: ignore
from json.decoder import JSONDecodeError
from typing import cast, Literal, NamedTuple, Optional, Tuple


DateTuple = tuple[int, int, int]
TimeTuple = tuple[int, int, int, int]
EventLogEntry = dict[str, str|int|float]
EventLogDict = dict[str, list[EventLogEntry]]
EventClass = str
EventData = tuple[str, str | int | float]
FlatLogData = tuple[EventClass] | tuple[EventClass, tuple[EventData, ...]]

def julian_to_gregorian(julian_date: int) -> DateTuple:
    """\
    Returns a triple (year, month, day) represented the Gregorian date
    corresponding to the JULIAN DATE.

    Note: when converting a Gregorian date to a Julian date, a site like
    https://aa.usno.navy.mil/data/JulianDate may return a real value. That
    value needs to be first rounded up before being submitted to the current
    function.
    """
    # Warning: this is all integer arithmetic (as indicated by the FORTRAN code
    # given at https://aa.usno.navy.mil/faq/JD_formula)
    m = julian_date + 68569
    n = 4 * int(m/146097)
    m = m - int((146097 * n + 3)/4)
    yr = int(4000 * (m + 1)/1461001)
    m = m - int((1461 * yr)/4) + 31
    mo = int((80 * m)/2447)
    dy = m - int((2447 * mo)/80)
    m = int(mo/11)
    mo = mo + 2 - 12 * m
    yr = 100 * (n - 49) + yr + m
    return yr, mo, dy

def seconds_to_time(msecs: int) -> TimeTuple:
    """\
    Converts MSECS, a number of milliseconds since the start of the day, in a
    tuple of ints (hours, mins, secs, microseconds).

    Note the MSECS is truncated to a number of seconds prior to calculate how
    many hours, minutes and seconds they represents (in UTC).
    """
    seconds = int(msecs / 1000)
    # microsecs will be required by datetime.time. So, we return microsecs
    # instead of milliseconds. CW, 20240710
    tm_musecs = 1000 * (msecs - (1000 * seconds))
    tstruct = time.gmtime(seconds)
    return tstruct.tm_hour, tstruct.tm_min, tstruct.tm_sec, tm_musecs

def load_event_log_file(filename: str) -> EventLogDict:
    """\
    Loads the eventLogging log file FILENAME and returns the corresponding
    dictionary.
    """
    if filename.endswith('.gz'):
        reader = functools.partial(gzip.open, mode='rb')
    else:
        reader = functools.partial(open, mode='r')  # type: ignore
    with reader(filename) as fp:
        return json.load(fp)  # type: ignore

def convert_datetime(log_entry: EventLogEntry) -> EventLogEntry:
    """\
    Returns a copy of LOG ENTRY where the "julianDate" and
    "msecsSinceStartOfDay" values have been converted to strings representing
    these date and time in Gregorian terms. The string formats are "Y/M/D" (for
    the "julianDate" field) and "h:m:s.musecs" (for the "msecsSinceStartOfDay"
    field), where "musecs" is a number of microseconds.

    LOG ENTRY is expected a dictionary as found in eventLogging's log files.
    """
    data = copy.deepcopy(log_entry)
    # casts inform static type checkers of the exact type. CW, 20240710
    data['julianDate'] = "%s/%s/%s" % (
        julian_to_gregorian(cast(int, data['julianDate'])))
    data['msecsSinceStartOfDay'] = "%s:%s:%s.%s" % (
        seconds_to_time(cast(int, data['msecsSinceStartOfDay'])))
    return data

def convert_log_file_datetimes(filename: str) -> EventLogDict:
    """\
    Returns the content of the eventLogging log file FILENAME with Julian dates
    replaced with Gregorian dates and millisecondsSinceStartOfDay converted to
    hours, minutes, seconds and microseconds. The converted values are strings
    in the format "Y/M/D" (for the "julianDate" field) and "h:m:s.musecs" (for
    the "msecsSinceStartOfDay" field).

    Note that the field names, "julianDate" and "msecsSinceStartOfDay", are not
    changed.
    """
    return {'logs': [d for d in map(convert_datetime,
                                    load_event_log_file(filename)['logs'])]}


class FlatLogEntry(NamedTuple):
    date: datetime.date
    time: datetime.time
    data: FlatLogData

    
class TimestampedLogEntry(NamedTuple):
    timestamp: str
    data: FlatLogData


def flatten_log_entry(entry: EventLogEntry) -> FlatLogEntry:
    """\
    Flattens ENTRY into a named tuple. The result contains, in that order:
    - a "date" value
    - a "time" value
    - a "data" value which contains the information in ENTRY which does not
      relate to date or time.

    The date and time values are converted from Julian date and a number of
    msecs into a Gregorian date and a breakdown in hours, minutes, seconds and
    microseconds, resp.

    The "data" value is a tuple listing keys (found in ENTRY) and associated
    values where they exist.
    """
    entry_type = len(entry)
    data = copy.deepcopy(entry)
    # inform static type checkers of the exact type. CW, 20240710
    julian_date = cast(int, data.pop('julianDate'))
    msecs = cast(int, data.pop('msecsSinceStartOfDay'))
    date_ = datetime.date(*julian_to_gregorian(julian_date))
    time_ = datetime.time(*seconds_to_time(msecs))
    klass = data.pop('Class')
    event: FlatLogData
    match entry_type:
        case 3: event = (klass,)  # type: ignore
        case 4: event = (tuple(data.values())[0],)  # type: ignore
        case _: event = (klass, tuple(data.items()))  # type: ignore
    return FlatLogEntry(date_, time_, event)

def timestamp_entry(log_entry: FlatLogEntry,
                    format_spec: Optional[str] = None) -> TimestampedLogEntry:
    """\
    Returns a named tuple where the date and time values found in LOG ENTRY are
    aggregated into a timestamp value. The timestamp value is a string.

    If FORMAT SPEC is not specified, datetime.datetime's isoformat() is called
    with the default args. Otherwise, FORMAT SPEC is passed to
    datetime.datetime's strftime() to format the timestamp.

    The resulting value contains a "timestamp" value and a "data" value, the
    "data" value being that found in LOG ENTRY.
    """
    if format_spec:
        tstmp =  datetime.datetime.combine(
            log_entry.date, log_entry.time).strftime(format_spec)
    else:
        tstmp = datetime.datetime.combine(
                log_entry.date, log_entry.time).isoformat()
    return TimestampedLogEntry(tstmp, log_entry.data)

def log_file_as_tuples(filename: str) -> Tuple[FlatLogEntry, ...]:
    """\
    Returns a flattened version of the "logs" list found in the eventLogging's
    log file FILENAME. The log file can be in gzip format.

    The result is a tuple of named tuples containing a date value, a time value
    and a data value.

    The date value is the conversion in Gregorian date of the Julian date stored
    in the log file. The time value is the conversion in a breakdown of hours,
    minutes, seconds and microseconds of the millisecs found in the log
    file.

    The data value is a tuple collecting a descriptor of the record followed by,
    if any, a tuple of key/value pairs representing the data associated with the
    logged record.  NOTE: the "Class" field found in the log file is usually
    removed from the result---but read below.

    When no event is available in a logged record, the record's "Class" value is
    used instead.

    """
    try:
        return tuple(map(flatten_log_entry,
                         load_event_log_file(filename)['logs']))
    except JSONDecodeError:
        raise CoreException('JSON file %r invalid or contains no data' %
                            filename) from None

def flatten_log_file(filename:str) -> Tuple[TimestampedLogEntry, ...]:
    """\
    Function similar to log_file_as_tuples but returns the time information in a
    timestamp format. FILENAME is the name of a eventLogging log file, possibly
    compressed in gzip format.

    The result is a tuple of named tuples containing a timestamp value and a
    data value. The timestamp format is "YYYY/mm/dd HH:MM:SS.ssssss". The date
    in this timestamp is the Gregorian date corresponding to the Julian date
    stored in the log file. The time part of the timestamp corresponds to the
    milliseconds stored in the log file.

    The data value is a tuple collecting a descriptor of the record followed by,
    if any, a tuple of key/value pairs representing the data associated with the
    logged record.  NOTE: the "Class" field found in the log file is usually
    removed from the result---but read below.

    When no event is available in a logged record, the record's "Class" value is
    used instead.
    """
    try:
        return tuple(
            map(timestamp_entry,
                map(flatten_log_entry,
                         load_event_log_file(filename)['logs'])))
    except JSONDecodeError:
        raise CoreException('JSON file %s invalid or contains no data' %
                            filename) from None
