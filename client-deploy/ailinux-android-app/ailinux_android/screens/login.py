"""
Login Screen with Registration
===============================
Fixed Tab UI: Login | Register
"""
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.segmentedbutton import MDSegmentedButton, MDSegmentedButtonItem
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
import threading


class LoginScreen(MDScreen):
    """Login screen with email/password and registration tabs"""
    
    api_client = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "login"
        self.is_register_mode = False
        Clock.schedule_once(lambda dt: self._build_ui(), 0)
    
    def _build_ui(self):
        """Build login UI"""
        # Main container with gradient background
        main_box = MDBoxLayout(
            orientation="vertical",
            padding=dp(20),
        )
        
        # Card container
        card = MDCard(
            orientation="vertical",
            padding=dp(25),
            spacing=dp(12),
            size_hint=(0.92, None),
            height=dp(580),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            elevation=4,
            radius=[dp(20)],
            md_bg_color=(0.07, 0.07, 0.1, 1),  # Dark background
        )
        
        # Robot Logo
        logo_label = MDLabel(
            text="🤖",
            font_style="H2",
            halign="center",
            size_hint_y=None,
            height=dp(60),
        )
        card.add_widget(logo_label)
        
        # Title
        title = MDLabel(
            text="AILinux",
            font_style="H4",
            halign="center",
            theme_text_color="Custom",
            text_color=(0.35, 0.55, 0.95, 1),  # Blue
            size_hint_y=None,
            height=dp(40),
        )
        card.add_widget(title)
        
        # Subtitle
        subtitle = MDLabel(
            text="TriForce AI Platform",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(25),
        )
        card.add_widget(subtitle)
        
        # Tab buttons container
        tab_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(5),
            padding=[dp(5), 0, dp(5), 0],
        )
        
        # Login Tab
        self.login_tab = MDRaisedButton(
            text="Login",
            size_hint_x=0.5,
            md_bg_color=(0.35, 0.55, 0.95, 1),
            on_release=lambda x: self._switch_mode(False),
        )
        tab_box.add_widget(self.login_tab)
        
        # Register Tab
        self.register_tab = MDFlatButton(
            text="Register",
            size_hint_x=0.5,
            on_release=lambda x: self._switch_mode(True),
        )
        tab_box.add_widget(self.register_tab)
        
        card.add_widget(tab_box)
        
        # Email field
        self.email_field = MDTextField(
            hint_text="E-MAIL",
            mode="rectangle",
            size_hint_y=None,
            height=dp(48),
        )
        # Set placeholder text style
        self.email_field.text = ""
        self.email_field.hint_text = "your@email.de"
        card.add_widget(self.email_field)
        
        # Password field
        self.password_field = MDTextField(
            hint_text="PASSWORD",
            mode="rectangle",
            password=True,
            size_hint_y=None,
            height=dp(48),
        )
        card.add_widget(self.password_field)
        
        # Name field (for registration, hidden initially)
        self.name_field = MDTextField(
            hint_text="NAME (optional)",
            mode="rectangle",
            size_hint_y=None,
            height=dp(48),
            opacity=0,
            disabled=True,
        )
        card.add_widget(self.name_field)
        
        # Beta code field (for registration, hidden initially)
        self.beta_code_field = MDTextField(
            hint_text="BETA-CODE (optional für Pro)",
            mode="rectangle",
            size_hint_y=None,
            height=dp(48),
            opacity=0,
            disabled=True,
        )
        card.add_widget(self.beta_code_field)
        
        # Status/Error label
        self.status_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Error",
            size_hint_y=None,
            height=dp(30),
        )
        card.add_widget(self.status_label)
        
        # Action button
        self.action_btn = MDRaisedButton(
            text="Login",
            pos_hint={"center_x": 0.5},
            size_hint_x=1,
            size_hint_y=None,
            height=dp(50),
            md_bg_color=(0.35, 0.55, 0.95, 1),
            on_release=self._on_action,
        )
        card.add_widget(self.action_btn)
        
        # Divider with "or"
        divider_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
            spacing=dp(10),
        )
        divider_box.add_widget(MDLabel(text=""))  # Spacer
        divider_box.add_widget(MDLabel(
            text="or",
            halign="center",
            theme_text_color="Hint",
            size_hint_x=None,
            width=dp(30),
        ))
        divider_box.add_widget(MDLabel(text=""))  # Spacer
        card.add_widget(divider_box)
        
        # Back/Toggle link
        self.back_btn = MDFlatButton(
            text="← Back",
            pos_hint={"center_x": 0.5},
            theme_text_color="Custom",
            text_color=(0.35, 0.55, 0.95, 1),
            on_release=lambda x: self._switch_mode(not self.is_register_mode),
        )
        card.add_widget(self.back_btn)
        
        # Version info
        version_label = MDLabel(
            text="v1.0.0 • Beta-Code: AILINUX2026",
            halign="center",
            theme_text_color="Hint",
            font_style="Caption",
            size_hint_y=None,
            height=dp(20),
        )
        card.add_widget(version_label)
        
        main_box.add_widget(card)
        self.add_widget(main_box)
    
    def _switch_mode(self, register_mode: bool):
        """Switch between login and register mode"""
        self.is_register_mode = register_mode
        
        if register_mode:
            # Register mode
            self.login_tab.md_bg_color = (0.2, 0.2, 0.25, 1)
            self.register_tab.md_bg_color = (0.35, 0.55, 0.95, 1)
            self.action_btn.text = "Register"
            self.name_field.opacity = 1
            self.name_field.disabled = False
            self.beta_code_field.opacity = 1
            self.beta_code_field.disabled = False
            self.status_label.text = "🎉 Beta: Alle Accounts bekommen PRO!"
            self.status_label.theme_text_color = "Primary"
            self.back_btn.text = "← Back to Login"
        else:
            # Login mode
            self.login_tab.md_bg_color = (0.35, 0.55, 0.95, 1)
            self.register_tab.md_bg_color = (0.2, 0.2, 0.25, 1)
            self.action_btn.text = "Login"
            self.name_field.opacity = 0
            self.name_field.disabled = True
            self.beta_code_field.opacity = 0
            self.beta_code_field.disabled = True
            self.status_label.text = ""
            self.back_btn.text = "Need an account? Register"
    
    def _on_action(self, *args):
        """Handle login/register button press"""
        email = self.email_field.text.strip()
        password = self.password_field.text.strip()
        
        if not email or not password:
            self.status_label.text = "Bitte Email und Passwort eingeben"
            self.status_label.theme_text_color = "Error"
            return
        
        if len(password) < 6:
            self.status_label.text = "Passwort zu kurz (min. 6 Zeichen)"
            self.status_label.theme_text_color = "Error"
            return
        
        if "@" not in email or "." not in email:
            self.status_label.text = "Ungültige Email-Adresse"
            self.status_label.theme_text_color = "Error"
            return
        
        self.status_label.text = "Verbinde..."
        self.status_label.theme_text_color = "Primary"
        self.action_btn.disabled = True
        
        name = self.name_field.text.strip() if self.is_register_mode else None
        beta_code = self.beta_code_field.text.strip() if self.is_register_mode else None
        
        def do_auth():
            if self.is_register_mode:
                result = self.api_client.register(email, password, name, beta_code)
                success = result if isinstance(result, bool) else result.get("success", False)
                error = result.get("error", "") if isinstance(result, dict) else ""
            else:
                success = self.api_client.login(email, password)
                error = ""
            Clock.schedule_once(lambda dt: self._auth_complete(success, error))
        
        threading.Thread(target=do_auth, daemon=True).start()
    
    def _auth_complete(self, success: bool, error: str = ""):
        """Handle auth result"""
        self.action_btn.disabled = False
        
        if success:
            tier = getattr(self.api_client, 'tier', 'free')
            self.status_label.text = f"✓ Erfolgreich! Tier: {tier.upper()}"
            self.status_label.theme_text_color = "Primary"
            
            # Clear fields
            self.email_field.text = ""
            self.password_field.text = ""
            self.name_field.text = ""
            self.beta_code_field.text = ""
            
            # Navigate to chat
            Clock.schedule_once(lambda dt: self._goto_chat(), 0.5)
        else:
            msg = error if error else ("Registrierung fehlgeschlagen" if self.is_register_mode else "Login fehlgeschlagen")
            self.status_label.text = msg
            self.status_label.theme_text_color = "Error"
    
    def _goto_chat(self):
        """Navigate to chat screen"""
        if self.manager:
            self.manager.current = "chat"
