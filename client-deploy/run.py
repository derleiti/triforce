#!/usr/bin/env python3
"""Starter Script für AILinux Client"""
import sys
from pathlib import Path

# Projektpfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent))

from ailinux_client.main import main

if __name__ == "__main__":
    main()
