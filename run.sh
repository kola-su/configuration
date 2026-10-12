#!/bin/sh
cd "$(dirname "$0")" || exit 1
python emulator.py "$@"
