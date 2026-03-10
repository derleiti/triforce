"""
AILinux Android Client
======================

Kivy-based Android app for AILinux.

Usage:
    python main.py                  # Desktop test
    buildozer android debug         # Build APK
"""
import os
import sys

# Kivy config BEFORE imports
os.environ['KIVY_LOG_LEVEL'] = 'info'

from kivy.config import Config
Config.set('kivy', 'log_level', 'info')
Config.set('graphics', 'multisamples', '0')  # Fix for some Android devices

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from ailinux_android.core import APIClient
from ailinux_android.screens import LoginScreen, ChatScreen, SettingsScreen


class AILinuxApp(MDApp):
    """Main AILinux Android App"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_client = APIClient()
    
    def build(self):
        """Build the app"""
        # Theme
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Teal"
        
        # Title
        self.title = "AILinux"
        
        # Screen manager
        self.sm = ScreenManager(transition=SlideTransition())
        
        # Create screens
        login_screen = LoginScreen(api_client=self.api_client)
        chat_screen = ChatScreen(api_client=self.api_client)
        settings_screen = SettingsScreen(api_client=self.api_client)
        
        self.sm.add_widget(login_screen)
        self.sm.add_widget(chat_screen)
        self.sm.add_widget(settings_screen)
        
        # Start on login or chat depending on auth status
        if self.api_client.is_authenticated():
            self.sm.current = "chat"
        else:
            self.sm.current = "login"
        
        # Handle back button on Android
        if platform == 'android':
            from android import activity
            activity.bind(on_new_intent=self._on_new_intent)
        
        Window.bind(on_keyboard=self._on_keyboard)
        
        return self.sm
    
    def _on_keyboard(self, window, key, *args):
        """Handle back button"""
        if key == 27:  # ESC / Back button
            if self.sm.current == "chat":
                # Don't exit, minimize
                if platform == 'android':
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    PythonActivity.mActivity.moveTaskToBack(True)
                return True
            elif self.sm.current in ("settings",):
                self.sm.current = "chat"
                return True
        return False
    
    def _on_new_intent(self, intent):
        """Handle Android intent"""
        pass
    
    def on_pause(self):
        """Called when app is paused"""
        return True
    
    def on_resume(self):
        """Called when app resumes"""
        pass


def main():
    """Entry point"""
    app = AILinuxApp()
    app.run()


if __name__ == "__main__":
    main()
