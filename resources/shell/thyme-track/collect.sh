#!/bin/sh
_LOCK_FILE=/scratch/.thymer-lock
if [ "$(busctl --user call org.gnome.ScreenSaver /org/gnome/ScreenSaver org.gnome.ScreenSaver GetActive)" = "b false" ]; then
    if [ -f "$_LOCK_FILE" ]; then
        rm -f "$_LOCK_FILE"
    fi
  TODAY=`date +%Y%m%d`
  /home/richard/work/thyme/bin/thyme track -o "/home/richard/storage/.daily-logs/data/thyme.json.$TODAY"
else
    if [ ! -f $_LOCK_FILE ]; then
        touch $_LOCK_FILE
        gnome-terminal -x /bin/bash -c 'sleep 1; wmctrl -r :ACTIVE: -N "Screensaver"; while [ -f "/scratch/.thymer-lock" ]; do sleep 1; done;'
    fi
fi

