#!/usr/bin/env python3
"""
AILinux Desktop - Schlanke Desktop-Umgebung für Ubuntu Server
Nutzt ailinux-client als Basis und fügt Desktop-Panel hinzu.
"""
import sys
import os

# ailinux-client muss installiert sein
try:
    from ailinux_client.ui.main_window import MainWindow
    from ailinux_client.core.api_client import APIClient
except ImportError:
    print("Error: ailinux-client muss zuerst installiert sein!")
    print("  pip install /path/to/ailinux-client")
    sys.exit(1)

from PyQt6.QtWidgets import QApplication
from .panel.desktop_panel import DesktopPanel


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AILinux Desktop")
    
    # Desktop Panel (Taskbar)
    panel = DesktopPanel()
    panel.show()
    
    # Optional: Main Window
    if "--with-client" in sys.argv:
        window = MainWindow()
        window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
