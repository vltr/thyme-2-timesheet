# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime

from flask import Flask, render_template, jsonify
from flask.ext.triangle import Triangle
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates, column_property
from sqlalchemy import func, sql, select, event

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
Triangle(app)

billable_ranges = db.Table('billable_ranges',
    db.Column('entry_id', db.Integer, db.ForeignKey('entry.entry_id')),
    db.Column('customer_id', db.Integer, db.ForeignKey('customer.customer_id'))
)


###############################################################################
#                                          _      _
#                      _ __ ___   ___   __| | ___| |___
#                     | '_ ` _ \ / _ \ / _` |/ _ \ / __|
#                     | | | | | | (_) | (_| |  __/ \__ \
#                     |_| |_| |_|\___/ \__,_|\___|_|___/
#
#
###############################################################################


class Entry(db.Model):
    entry_id = db.Column(db.Integer, primary_key=True)
    window_id = db.Column(db.Integer)
    label = db.Column(db.String(120))
    first_timestamp = db.Column(db.DateTime, nullable=False)
    last_timestamp = db.Column(db.DateTime, nullable=False)
    sha512sum = db.Column(db.String(128), nullable=False)
    is_valid = db.Column(db.Boolean, nullable=False, default=True)

    def __init__(self, window_id):
        self.window_id = window_id

    @hybrid_property  # instance level
    def timedelta(self):
        delta = self.last_timestamp - self.first_timestamp
        return float(delta.total_seconds()) / 60. / 60.

    @timedelta.expression
    def timedelta(cls):
        return func.cast((func.julianday(Entry.last_timestamp) - func.julianday(Entry.first_timestamp)) * 24., db.Float)

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


class DataSources(db.Model):
    source_id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128))
    sha512sum = db.Column(db.String(128), nullable=False)
    parsed_on = db.Column(db.DateTime, nullable=False, default=pendulum.now())
    last_updated_on = db.Column(db.DateTime, nullable=False, default=pendulum.now())

    billable = db.relationship('Entry', secondary=billable_ranges,
        backref=db.backref('customer', lazy='dynamic'))


@event.listens_for(DataSources, 'before_update', propagate=False)
def last_updated_on_before_update(mapper, connection, target):
    target.last_updated_on = pendulum.now()


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
def get_all_entries():
    records = db.session.query(Entry.window_id, Entry.label,
                               func.sum(Entry.timedelta).label('time_spent')) \
        .filter(Entry.is_valid == sql.true()) \
        .group_by(Entry.window_id, Entry.label) \
        .order_by(Entry.window_id, Entry.label).all()
    return jsonify(dict(total=len(records),
                        result=map(lambda r: r._asdict(), records)))
