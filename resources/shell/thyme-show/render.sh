#!/bin/bash

_REPORTS=/home/richard/storage/.daily-logs/reports
_DATA=/home/richard/storage/.daily-logs/data
_SHASUM=/home/richard/storage/.daily-logs/sha256sums

for src in $(find $_DATA -type f | grep "thyme.json"); do
  lasthash=
  togen="${src:50}"
  # check hash
  if [ -f "$_SHASUM/$togen" ]; then
    lasthash=$(/bin/cat "$_SHASUM/$togen")
  fi
  # register hash
  /usr/bin/sha256sum "$src" > "$_SHASUM/$togen"
  curhash=$(/bin/cat "$_SHASUM/$togen")
  if [ ! -f "$_REPORTS/$togen.html" ] || [ "$lasthash" != "$curhash" ]; then
    /home/richard/work/thyme/bin/thyme show -i "$src" -w stats > "$_REPORTS/$togen.html"
  fi
done

