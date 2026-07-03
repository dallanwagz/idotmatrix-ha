#!/usr/bin/env bash
# One-time Raspberry Pi setup for driving iDotMatrix panels. Safe to re-run (idempotent).
# Installs the Bluetooth stack + a Python venv with the two libraries the scripts need.
set -e

echo "== iDotMatrix Pi setup =="

if command -v apt-get >/dev/null 2>&1; then
  echo "-- installing bluetooth + python (sudo may prompt) --"
  sudo apt-get update -qq
  sudo apt-get install -y bluetooth bluez python3 python3-venv python3-pip libopenjp2-7
  echo "-- making sure the bluetooth service is up --"
  sudo systemctl enable --now bluetooth || true
else
  echo "!! apt-get not found — install bluez + python3-venv with your package manager, then re-run."
fi

VENV="$HOME/.idm-venv"
if [ ! -d "$VENV" ]; then
  echo "-- creating venv at $VENV --"
  python3 -m venv "$VENV"
fi
echo "-- installing bleak + pillow --"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet bleak pillow

echo
echo "DONE. Use this python for all the scripts here:"
echo "    $VENV/bin/python scan.py"
echo
echo "Quick check that Bluetooth sees anything at all:"
echo "    bluetoothctl --timeout 5 scan on   # should list some devices"
echo
echo "Next: $VENV/bin/python scan.py    (find your panels)"
