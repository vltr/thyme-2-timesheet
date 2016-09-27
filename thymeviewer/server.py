# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime

from flask import Flask, render_template, jsonify, request
# from flask.ext.triangle import Triangle
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates, column_property
from sqlalchemy import func, sql, select, event

from dtutils import get_month_barrier, get_day_barrier, get_week_barrier

import pendulum

###############################################################################
#                                  _       _     _
#                 __   ____ _ _ __(_) __ _| |__ | | ___  ___
#                 \ \ / / _` | '__| |/ _` | '_ \| |/ _ \/ __|
#                  \ V / (_| | |  | | (_| | |_) | |  __/\__ \
#                   \_/ \__,_|_|  |_|\__,_|_.__/|_|\___||___/
#
#
###############################################################################

DB_PATH = "/home/richard/storage/.daily-logs/data.db"
DATA_FILES_PATTERN = "/home/richard/storage/.daily-logs/data/thyme.json.*"

TIMESPAN = [
    'month',
    'week',
    'day'
]

###############################################################################
#                __ _           _               _
#               / _| | __ _ ___| | __  ___  ___| |_ _   _ _ __
#              | |_| |/ _` / __| |/ / / __|/ _ \ __| | | | '_ \
#              |  _| | (_| \__ \   <  \__ \  __/ |_| |_| | |_) |
#              |_| |_|\__,_|___/_|\_\ |___/\___|\__|\__,_| .__/
#                                                        |_|
#
###############################################################################

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % DB_PATH
db = SQLAlchemy(app)
# Triangle(app)

jinja_options = app.jinja_options.copy()

jinja_options.update(dict(
    block_start_string='<%',
    block_end_string='%>',
    variable_start_string='%%',
    variable_end_string='%%',
    comment_start_string='<#',
    comment_end_string='#>'
))
app.jinja_options = jinja_options

###############################################################################
#                                          _      _
#                      _ __ ___   ___   __| | ___| |___
#                     | '_ ` _ \ / _ \ / _` |/ _ \ / __|
#                     | | | | | | (_) | (_| |  __/ \__ \
#                     |_| |_| |_|\___/ \__,_|\___|_|___/
#
#
###############################################################################


billable_ranges = db.Table('billable_ranges',
    db.Column('entry_id', db.Integer, db.ForeignKey('entry.entry_id')),
    db.Column('customer_id', db.Integer, db.ForeignKey('customer.customer_id'))
)


class DataSource(db.Model):
    source_id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), unique=True)
    sha512sum = db.Column(db.String(128), nullable=False)
    parsed_on = db.Column(db.DateTime, nullable=False, default=pendulum.now())
    last_updated_on = db.Column(db.DateTime, nullable=False, default=pendulum.now())

    entries = db.relationship('Entry', backref='data_source')


@event.listens_for(DataSource, 'before_update', propagate=False)
def last_updated_on_before_update(mapper, connection, target):
    target.last_updated_on = pendulum.now()


class Entry(db.Model):
    entry_id = db.Column(db.Integer, primary_key=True)
    window_id = db.Column(db.Integer)
    label = db.Column(db.String(120))
    first_timestamp = db.Column(db.DateTime, nullable=False)
    last_timestamp = db.Column(db.DateTime, nullable=False)
    sha512sum = db.Column(db.String(128), nullable=False)
    is_valid = db.Column(db.Boolean, nullable=False, default=True)
    source_id = db.Column(db.Integer, db.ForeignKey('data_source.source_id'))

    def __init__(self, window_id):
        self.window_id = window_id

    @hybrid_property  # instance level
    def timedelta(self):
        delta = self.last_timestamp - self.first_timestamp
        return float(delta.total_seconds()) / 60. / 60.

    @timedelta.expression
    def timedelta(cls):
        return func.cast((func.julianday(Entry.last_timestamp) -
            func.julianday(Entry.first_timestamp)) * 24., db.Float)

    # @timedelta.setter
    # def timedelta(self, value):
    #     pass

    @validates('first_timestamp')
    def validate_first_timestamp(self, key, value):
        if isinstance(value, basestring):
            return pendulum.parse(value)
        elif isinstance(value, datetime):
            return value
        else:
            return pendulum.now()

    @validates('last_timestamp')
    def validate_last_timestamp(self, key, value):
        if isinstance(value, basestring):
            return pendulum.parse(value)
        elif isinstance(value, datetime):
            return value
        else:
            return pendulum.now()


class Customer(db.Model):
    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))

    billable = db.relationship('Entry', secondary=billable_ranges,
        backref=db.backref('customer', lazy='dynamic'))


###############################################################################
#                                        _
#                        _ __ ___  _   _| |_ ___  ___
#                       | '__/ _ \| | | | __/ _ \/ __|
#                       | | | (_) | |_| | ||  __/\__ \
#                       |_|  \___/ \__,_|\__\___||___/
#
#
###############################################################################


@app.route('/')
def main_index():
    return render_template('index.html')


@app.route('/entries/')
@app.route('/entries/<timespan>')
def get_entries(timespan=None):
    filters = [Entry.is_valid == sql.true(),]

    if timespan is not None and timespan in TIMESPAN:
        if timespan == 'day':
            fn = get_day_barrier
        elif timespan == 'week':
            fn = get_week_barrier
        elif timespan == 'month':
            fn = get_month_barrier

        filters.append(Entry.first_timestamp.between(fn(),
                                                     fn(None, False)))

    records = db.session.query(func.min(Entry.entry_id).label('min_entry_id'),
                               Entry.window_id, Entry.label,
                               func.sum(Entry.timedelta).label('time_spent')) \
        .filter(*filters) \
        .group_by(Entry.window_id, Entry.label) \
        .order_by(Entry.window_id, Entry.label).all()

    return jsonify(dict(total=len(records),
                        result=map(lambda r: r._asdict(), records)))


@app.route('/entry/', methods=["GET", "POST"])
def del_entry():
    if request.method == "POST":
        # print(request)
        # print(dir(request))
        # print(request.data)
        # print(request.values)
        # print(request.form)
        # print(request.json)
        entry_id = int(request.json.get('entry_id'))
        entry = db.session.query(Entry).filter(Entry.entry_id == entry_id).one()
        siblings = db.session.query(Entry).filter(
            Entry.window_id == entry.window_id,
            Entry.label == entry.label,
            Entry.first_timestamp.between(
                get_day_barrier(entry.first_timestamp),
                get_day_barrier(entry.first_timestamp, False))).all()

        for s in siblings:
            s.is_valid = sql.false()
        db.session.commit()
        return jsonify(dict(success=1))
    else:
        return jsonify(dict(success=0))
