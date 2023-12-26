# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import re
from datetime import date, datetime, time as dt_time, timedelta
from importlib import import_module
from sys import modules

from ..exceptions import KodionException


now = datetime.now

__RE_MATCH_TIME_ONLY__ = re.compile(r'^(?P<hour>[0-9]{2})(:?(?P<minute>[0-9]{2})(:?(?P<second>[0-9]{2}))?)?$')
__RE_MATCH_DATE_ONLY__ = re.compile(r'^(?P<year>[0-9]{4})[-/.]?(?P<month>[0-9]{2})[-/.]?(?P<day>[0-9]{2})$')
__RE_MATCH_DATETIME__ = re.compile(r'^(?P<year>[0-9]{4})[-/.]?(?P<month>[0-9]{2})[-/.]?(?P<day>[0-9]{2})["T ](?P<hour>[0-9]{2}):?(?P<minute>[0-9]{2}):?(?P<second>[0-9]{2})')
__RE_MATCH_PERIOD__ = re.compile(r'P((?P<years>\d+)Y)?((?P<months>\d+)M)?((?P<days>\d+)D)?(T((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?)?')
__RE_MATCH_ABBREVIATED__ = re.compile(r'(\w+), (?P<day>\d+) (?P<month>\w+) (?P<year>\d+) (?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)')

__LOCAL_OFFSET__ = now() - datetime.utcnow()

__EPOCH_DT__ = datetime.fromtimestamp(0)


def parse(datetime_string, as_utc=True):
    offset = 0 if as_utc else None

    def _to_int(value):
        if value is None:
            return 0
        return int(value)

    # match time only '00:45:10'
    time_only_match = __RE_MATCH_TIME_ONLY__.match(datetime_string)
    if time_only_match:
        return utc_to_local(
            dt=datetime.combine(
                date.today(),
                dt_time(hour=_to_int(time_only_match.group('hour')),
                        minute=_to_int(time_only_match.group('minute')),
                        second=_to_int(time_only_match.group('second')))
            ),
            offset=offset
        ).time()

    # match date only '2014-11-08'
    date_only_match = __RE_MATCH_DATE_ONLY__.match(datetime_string)
    if date_only_match:
        return utc_to_local(
            dt=datetime(_to_int(date_only_match.group('year')),
                        _to_int(date_only_match.group('month')),
                        _to_int(date_only_match.group('day'))),
            offset=offset
        )

    # full date time
    date_time_match = __RE_MATCH_DATETIME__.match(datetime_string)
    if date_time_match:
        return utc_to_local(
            dt=datetime(_to_int(date_time_match.group('year')),
                        _to_int(date_time_match.group('month')),
                        _to_int(date_time_match.group('day')),
                        _to_int(date_time_match.group('hour')),
                        _to_int(date_time_match.group('minute')),
                        _to_int(date_time_match.group('second'))),
            offset=offset
        )

    # period - at the moment we support only hours, minutes and seconds
    # e.g. videos and audio
    period_match = __RE_MATCH_PERIOD__.match(datetime_string)
    if period_match:
        return timedelta(hours=_to_int(period_match.group('hours')),
                         minutes=_to_int(period_match.group('minutes')),
                         seconds=_to_int(period_match.group('seconds')))

    # abbreviated match
    abbreviated_match = __RE_MATCH_ABBREVIATED__.match(datetime_string)
    if abbreviated_match:
        month = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'June': 6,
                 'Jun': 6, 'July': 7, 'Jul': 7, 'Aug': 8, 'Sept': 9, 'Sep': 9,
                 'Oct': 10, 'Nov': 11, 'Dec': 12}
        return utc_to_local(
            dt=datetime(year=_to_int(abbreviated_match.group('year')),
                        month=month[abbreviated_match.group('month')],
                        day=_to_int(abbreviated_match.group('day')),
                        hour=_to_int(abbreviated_match.group('hour')),
                        minute=_to_int(abbreviated_match.group('minute')),
                        second=_to_int(abbreviated_match.group('second'))),
            offset=offset
        )

    raise KodionException('Could not parse |{datetime}| as ISO 8601'
                          .format(datetime=datetime_string))


def get_scheduled_start(context, datetime_object, local=True):
    _now = now() if local else datetime.utcnow()
    if datetime_object.date() == _now:
        return '@ {start_time}'.format(
            start_time=context.format_time(datetime_object.time())
        )
    return '@ {start_date}, {start_time}'.format(
        start_time=context.format_time(datetime_object.time()),
        start_date=context.format_date_short(datetime_object.date())
    )


def utc_to_local(dt, offset=None):
    offset = __LOCAL_OFFSET__ if offset is None else timedelta(hours=offset)
    return dt + offset


def datetime_to_since(context, dt):
    _now = now()
    diff = _now - dt
    yesterday = _now - timedelta(days=1)
    yyesterday = _now - timedelta(days=2)
    use_yesterday = (_now - yesterday).total_seconds() > 10800
    today = _now.date()
    tomorrow = today + timedelta(days=1)
    seconds = diff.total_seconds()

    if seconds > 0:
        if seconds < 60:
            return context.localize('datetime.just_now')
        if 60 <= seconds < 120:
            return context.localize('datetime.a_minute_ago')
        if 120 <= seconds < 3600:
            return context.localize('datetime.recently')
        if 3600 <= seconds < 7200:
            return context.localize('datetime.an_hour_ago')
        if 7200 <= seconds < 10800:
            return context.localize('datetime.two_hours_ago')
        if 10800 <= seconds < 14400:
            return context.localize('datetime.three_hours_ago')
        if use_yesterday and dt.date() == yesterday.date():
            return ' '.join((context.localize('datetime.yesterday_at'),
                             context.format_time(dt)))
        if dt.date() == yyesterday.date():
            return context.localize('datetime.two_days_ago')
        if 5400 <= seconds < 86400:
            return ' '.join((context.localize('datetime.today_at'),
                             context.format_time(dt)))
        if 86400 <= seconds < 172800:
            return ' '.join((context.localize('datetime.yesterday_at'),
                             context.format_time(dt)))
    else:
        seconds *= -1
        if seconds < 60:
            return context.localize('datetime.airing_now')
        if 60 <= seconds < 120:
            return context.localize('datetime.in_a_minute')
        if 120 <= seconds < 3600:
            return context.localize('datetime.airing_soon')
        if 3600 <= seconds < 7200:
            return context.localize('datetime.in_over_an_hour')
        if 7200 <= seconds < 10800:
            return context.localize('datetime.in_over_two_hours')
        if dt.date() == today:
            return ' '.join((context.localize('datetime.airing_today_at'),
                             context.format_time(dt)))
        if dt.date() == tomorrow:
            return ' '.join((context.localize('datetime.tomorrow_at'),
                             context.format_time(dt)))

    return ' '.join((context.format_date_short(dt), context.format_time(dt)))


def strptime(datetime_str, fmt='%Y-%m-%dT%H:%M:%S'):
    if '.' in datetime_str[-5:]:
        fmt.replace('%S', '%S.%f')
    else:
        fmt.replace('%S.%f', '%S')

    if not datetime.strptime:
        if '_strptime' in modules:
            del modules['_strptime']
        modules['_strptime'] = import_module('_strptime')

    return datetime.strptime(datetime_str, fmt)


def since_epoch(dt_object):
    return (dt_object - __EPOCH_DT__).total_seconds()
