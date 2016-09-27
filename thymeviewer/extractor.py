# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import glob
import json
import hashlib

from sqlalchemy import func

from server import db, Entry, DataSource, DB_PATH, DATA_FILES_PATTERN


def readfile(path):
    f = open(path, 'rb')
    c = f.read()
    f.close()
    return c


def get_sha512(active, label, snap):
    sig = hashlib.sha512(unicode(active))
    sig.update(label.encode('utf-8'))
    sig.update(snap.get('Time'))
    return sig.hexdigest()


def main():
    if not os.path.isfile(DB_PATH):
        db.create_all()

    for src in glob.glob(DATA_FILES_PATTERN):
        last_active = None
        data_src = None
        fname = os.path.basename(src)
        content = readfile(src)
        content_sha512 = hashlib.sha512(content).hexdigest()

        if db.session.query(func.count(DataSource.source_id)).filter(DataSource.filename == fname).scalar() == 1:
            data_src = db.session.query(DataSource).filter(DataSource.filename == fname).one()
            if data_src.sha512sum == content_sha512:
                continue
            data_src.sha512sum = content_sha512
            db.session.commit()
        else:
            data_src = DataSource()
            data_src.filename = fname
            data_src.sha512sum = content_sha512
            db.session.add(data_src)
            db.session.commit()

        snapshots = json.loads(content).get('Snapshots')
        for snap in snapshots:
            active = snap.get('Active', 0)
            if active > 0:
                window = filter(lambda w: w.get('ID') == active, snap.get('Windows'))
                if window:
                    w = window[0]
                    sig = get_sha512(active, w.get('Name'), snap)
                    sig_exists = db.session.query(func.count(Entry.entry_id)).filter(Entry.sha512sum == sig).scalar()
                    if sig_exists:
                        continue

                    if not last_active:
                        last_active = Entry(active)
                        last_active.source_id = data_src.source_id
                        last_active.label = w.get('Name')
                        last_active.first_timestamp = snap.get('Time')
                        continue

                    if last_active.window_id == active and last_active.label != w.get('Name'):
                        last_active.last_timestamp = snap.get('Time')
                        last_active.sha512sum = sig
                        db.session.add(last_active)
                        db.session.commit()
                        last_active = Entry(active)
                        last_active.source_id = data_src.source_id
                        last_active.label = w.get('Name')
                        last_active.first_timestamp = snap.get('Time')
                    elif last_active.window_id == active:
                        last_active.last_timestamp = snap.get('Time')
                    else:
                        last_active.last_timestamp = snap.get('Time')
                        last_active.sha512sum = sig
                        db.session.add(last_active)
                        db.session.commit()
                        last_active = Entry(active)
                        last_active.source_id = data_src.source_id
                        last_active.label = w.get('Name')
                        last_active.first_timestamp = snap.get('Time')

if __name__ == '__main__':
    main()
