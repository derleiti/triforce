#!/bin/bash
# Ensure venv exists and deps are installed
VENV="/opt/triforce/.venv"
if [ ! -f "$VENV/bin/python3" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip
    "$VENV/bin/pip" install -r /opt/triforce/requirements.txt
fi
