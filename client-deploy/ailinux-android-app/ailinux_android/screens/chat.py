"""
Chat Screen
===========

Main chat interface with message history.
"""
from kivy.uix.screenmanager import Screen
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.menu import MDDropdownMenu
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.clock import Clock
from kivy.metrics import dp
import threading


class MessageBubble(MDCard):
    """Chat message bubble"""
    
    def __init__(self, text: str, is_user: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(12)
        self.spacing = dp(4)
        self.size_hint_x = 0.85
        self.size_hint_y = None
        self.elevation = 1
        self.radius = [dp(12)]
        
        if is_user:
            self.pos_hint = {"right": 0.98}
            self.md_bg_color = (0.2, 0.4, 0.8, 1)  # Blue
        else:
            self.pos_hint = {"x": 0.02}
            self.md_bg_color = (0.2, 0.2, 0.2, 1)  # Dark gray
        
        label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
        )
        label.bind(texture_size=lambda i, s: setattr(label, 'height', s[1]))
        self.add_widget(label)
        
        # Auto-height
        self.bind(minimum_height=self.setter('height'))


class ChatScreen(MDScreen):
    """Main chat screen"""
    
    api_client = ObjectProperty(None)
    current_model = StringProperty("")
    models = ListProperty([])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "chat"
        self._build_ui()
    
    def _build_ui(self):
        """Build chat UI"""
        main_layout = MDBoxLayout(orientation="vertical")
        
        # Top bar
        self.toolbar = MDTopAppBar(
            title="AILinux Chat",
            left_action_items=[["menu", lambda x: self._open_menu()]],
            right_action_items=[
                ["cog", lambda x: self._goto_settings()],
                ["logout", lambda x: self._logout()],
            ],
            elevation=4,
        )
        main_layout.add_widget(self.toolbar)
        
        # Model selector
        model_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            padding=dp(8),
            spacing=dp(8),
        )
        
        model_label = MDLabel(
            text="Model:",
            size_hint_x=None,
            width=dp(60),
        )
        model_bar.add_widget(model_label)
        
        self.model_button = MDRaisedButton(
            text="Select Model",
            size_hint_x=1,
            on_release=self._show_model_menu,
        )
        model_bar.add_widget(self.model_button)
        
        main_layout.add_widget(model_bar)
        
        # Messages area
        self.scroll_view = MDScrollView()
        self.messages_list = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(10),
            size_hint_y=None,
        )
        self.messages_list.bind(minimum_height=self.messages_list.setter('height'))
        self.scroll_view.add_widget(self.messages_list)
        main_layout.add_widget(self.scroll_view)
        
        # Input area
        input_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            padding=dp(8),
            spacing=dp(8),
        )
        
        self.message_input = MDTextField(
            hint_text="Type your message...",
            mode="rectangle",
            size_hint_x=0.85,
            multiline=False,
        )
        self.message_input.bind(on_text_validate=self._send_message)
        input_layout.add_widget(self.message_input)
        
        send_btn = MDIconButton(
            icon="send",
            on_release=self._send_message,
        )
        input_layout.add_widget(send_btn)
        
        main_layout.add_widget(input_layout)
        
        self.add_widget(main_layout)
    
    def on_enter(self):
        """Called when screen is shown"""
        self._load_models()
    
    def _load_models(self):
        """Load available models"""
        def do_load():
            result = self.api_client.get_models()
            models = result.get("models", [])
            tier = result.get("tier", "free")
            Clock.schedule_once(lambda dt: self._update_models(models, tier))
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _update_models(self, models: list, tier: str):
        """Update model list"""
        self.models = models
        self.toolbar.title = f"AILinux ({tier})"
        
        if models and not self.current_model:
            self.current_model = models[0]
            self.model_button.text = self.current_model
    
    def _show_model_menu(self, *args):
        """Show model selection menu"""
        if not self.models:
            return
        
        menu_items = [
            {
                "text": model,
                "on_release": lambda x=model: self._select_model(x),
            }
            for model in self.models[:20]  # Limit to 20 models
        ]
        
        self.model_menu = MDDropdownMenu(
            caller=self.model_button,
            items=menu_items,
            width_mult=4,
        )
        self.model_menu.open()
    
    def _select_model(self, model: str):
        """Select a model"""
        self.current_model = model
        self.model_button.text = model
        self.model_menu.dismiss()
    
    def _send_message(self, *args):
        """Send message to API"""
        message = self.message_input.text.strip()
        if not message:
            return
        
        # Add user message
        self._add_message(message, is_user=True)
        self.message_input.text = ""
        
        # Send in background
        def do_send():
            try:
                result = self.api_client.chat(
                    message=message,
                    model=self.current_model or None,
                )
                response = result.get("response", "No response")
                Clock.schedule_once(lambda dt: self._add_message(response, is_user=False))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._add_message(f"Error: {e}", is_user=False))
        
        threading.Thread(target=do_send, daemon=True).start()
    
    def _add_message(self, text: str, is_user: bool):
        """Add message bubble"""
        bubble = MessageBubble(text, is_user=is_user)
        self.messages_list.add_widget(bubble)
        
        # Scroll to bottom
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.1)
    
    def _scroll_to_bottom(self):
        """Scroll to bottom of messages"""
        self.scroll_view.scroll_y = 0
    
    def _open_menu(self):
        """Open side menu"""
        pass  # TODO: Implement drawer
    
    def _goto_settings(self):
        """Go to settings screen"""
        self.manager.current = "settings"
    
    def _logout(self):
        """Logout and go to login screen"""
        self.api_client.logout()
        self.messages_list.clear_widgets()
        self.manager.current = "login"
