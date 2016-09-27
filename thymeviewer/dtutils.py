# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime

import pendulum


def _pend_parse(dt):
    if dt is None:
        return pendulum.now()
    else:
        if isinstance(dt, datetime):
            return pendulum.instance(dt)
        return pendulum.parse(dt)


def get_month_barrier(dt=None, lower=True):
    p = _pend_parse(dt)
    if lower:
        return p.start_of('month').subtract(microseconds=1)
    else:
        return p.start_of('month').add(months=1)


def get_day_barrier(dt=None, lower=True):
    p = _pend_parse(dt)
    if lower:
        return p.start_of('day').subtract(microseconds=1)
    else:
        return p.start_of('day').add(days=1)


def get_week_barrier(dt=None, lower=True):
    p = _pend_parse(dt)
    if lower:
        return p.start_of('week').subtract(microseconds=1)
    else:
        return p.start_of('week').add(weeks=1)
