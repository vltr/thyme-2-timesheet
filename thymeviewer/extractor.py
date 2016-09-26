# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import glob
import json
import hashlib
import pendulum

from sqlalchemy import func

from server import db, Entry


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
    db.create_all()
    for src in glob.glob(DATA_FILES_PATTERN):
        last_active = None
        snapshots = json.loads(readfile(src)).get('Snapshots')
        for snap in snapshots:
            active = snap.get('Active', 0)
            if active > 0:
                window = filter(lambda w: w.get('ID') == active, snap.get('Windows'))
                if window:
                    w = window[0]
                    if not last_active:
                        last_active = Entry(active)
                        last_active.label = w.get('Name')
                        last_active.first_timestamp = snap.get('Time')
                        continue


                    sig = get_sha512(active, w.get('Name'), snap)
                    sig_exists = db.session.query(func.count(Entry.entry_id)).filter(Entry.sha512sum == sig).scalar()
                    if sig_exists:
                        continue

                    if last_active.window_id == active and last_active.label != w.get('Name'):
                        last_active.last_timestamp = snap.get('Time')
                        last_active.sha512sum = sig
                        db.session.add(last_active)
                        db.session.commit()
                        last_active = Entry(active)
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
                        last_active.label = w.get('Name')
                        last_active.first_timestamp = snap.get('Time')

if __name__ == '__main__':
    main()
