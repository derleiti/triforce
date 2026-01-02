"""
Settings Screen
===============
"""
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivymd.uix.scrollview import MDScrollView
from kivy.properties import ObjectProperty
from kivy.metrics import dp


class SettingsScreen(MDScreen):
    """Settings and info screen"""
    
    api_client = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self._build_ui()
    
    def _build_ui(self):
        """Build settings UI"""
        main_layout = MDBoxLayout(orientation="vertical")
        
        # Top bar
        toolbar = MDTopAppBar(
            title="Settings",
            left_action_items=[["arrow-left", lambda x: self._go_back()]],
            elevation=4,
        )
        main_layout.add_widget(toolbar)
        
        # Scrollable content
        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(16),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))
        
        # Account info
        account_label = MDLabel(
            text="Account",
            font_style="H6",
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(account_label)
        
        self.user_info = TwoLineListItem(
            text="User ID",
            secondary_text="-",
        )
        content.add_widget(self.user_info)
        
        self.tier_info = TwoLineListItem(
            text="Tier",
            secondary_text="-",
        )
        content.add_widget(self.tier_info)
        
        # App info
        app_label = MDLabel(
            text="About",
            font_style="H6",
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(app_label)
        
        version_item = TwoLineListItem(
            text="Version",
            secondary_text="1.0.0",
        )
        content.add_widget(version_item)
        
        server_item = TwoLineListItem(
            text="Server",
            secondary_text="api.ailinux.me",
        )
        content.add_widget(server_item)
        
        # Logout button
        logout_btn = MDRaisedButton(
            text="Logout",
            pos_hint={"center_x": 0.5},
            on_release=self._logout,
        )
        content.add_widget(logout_btn)
        
        scroll.add_widget(content)
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)
    
    def on_enter(self):
        """Update info when screen shown"""
        if self.api_client:
            self.user_info.secondary_text = self.api_client.user_id or "-"
            self.tier_info.secondary_text = self.api_client.tier or "free"
    
    def _go_back(self):
        """Go back to chat"""
        self.manager.current = "chat"
    
    def _logout(self, *args):
        """Logout"""
        if self.api_client:
            self.api_client.logout()
        self.manager.current = "login"
