"""
Login Dialog für AILinux Client
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap
import aiohttp
import asyncio
import json
from pathlib import Path


class AuthWorker(QThread):
    """Background Worker für Auth-Requests"""
    login_success = pyqtSignal(dict)  # user_data
    login_failed = pyqtSignal(str)    # error message

    def __init__(self, email: str, server_url: str,
                 api_user: str = None, api_password: str = None,
                 client_id: str = None, user_id: str = None):
        super().__init__()
        self.email = email
        self.server_url = server_url
        self.api_user = api_user
        self.api_password = api_password
        self.client_id = client_id
        self.user_id = user_id

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._login())
        except Exception as e:
            self.login_failed.emit(str(e))
        finally:
            loop.close()

    async def _login(self):
        """Login via API mit Basic Auth"""
        # Basic Auth Setup
        auth = None
        if self.api_user and self.api_password:
            auth = aiohttp.BasicAuth(self.api_user, self.api_password)

        async with aiohttp.ClientSession(auth=auth) as session:
            # Versuche Tier-Info abzurufen (verifiziert Auth und holt User-Daten)
            try:
                async with session.get(
                    f"{self.server_url}/v1/tiers/user/{self.email}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tier = data.get("tier", "free")
                        tier_names = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}
                        user_data = {
                            "email": self.email,
                            "user_id": self.user_id or self.email,
                            "tier": tier,
                            "tier_name": tier_names.get(tier, data.get("name", tier.title())),
                            "token": f"basic_auth_{self.email}",
                            "quota": data.get("features", [])
                        }
                        self.login_success.emit(user_data)
                        return
                    elif resp.status == 401:
                        self.login_failed.emit("Ungültige API-Credentials")
                        return
            except aiohttp.ClientError as e:
                pass  # Fallback versuchen

            # Offline/Demo-Mode
            user_data = {
                "email": self.email,
                "user_id": self.user_id or self.email,
                "tier": "free",
                "tier_name": "Free (Offline)",
                "token": f"offline_{self.email}",
                "offline": True
            }
            self.login_success.emit(user_data)


class LoginDialog(QDialog):
    """Login Dialog"""

    login_successful = pyqtSignal(dict)  # Emittiert User-Daten bei Erfolg

    def __init__(self, parent=None):
        super().__init__(parent)
        self._load_config()
        self.session_file = Path.home() / ".config" / "ailinux" / "session.json"
        self.worker = None
        self.setup_ui()
        self.load_saved_session()

    def _load_config(self):
        """Lade Konfiguration aus .env"""
        import os
        from dotenv import load_dotenv

        # Standard-Pfade für .env
        for p in [Path("config/.env"), Path.home() / ".config/ailinux/.env"]:
            if p.exists():
                load_dotenv(p)
                break

        self.server_url = os.getenv("AILINUX_SERVER", "https://api.ailinux.me")
        # API Auth
        self.api_user = os.getenv("AILINUX_API_USER", "")
        self.api_password = os.getenv("AILINUX_API_PASSWORD", "")
        # Client Info
        self.client_id = os.getenv("AILINUX_CLIENT_ID", "")
        self.client_secret = os.getenv("AILINUX_CLIENT_SECRET", "")
        self.default_email = os.getenv("AILINUX_USER_EMAIL", "")
        self.user_id = os.getenv("AILINUX_USER_ID", "")
    
    def setup_ui(self):
        self.setWindowTitle("AILinux Login")
        self.setFixedSize(400, 300)
        self.setModal(True)
        
        # Dark Theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
            }
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            QCheckBox {
                color: #cdd6f4;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo/Title
        title = QLabel("🚀 AILinux Client")
        title.setFont(QFont("", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #89b4fa;")
        layout.addWidget(title)
        
        subtitle = QLabel("Melde dich an für Zugriff auf 300+ KI-Modelle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(10)
        
        # Email
        email_label = QLabel("📧 Email")
        layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("deine@email.de")
        if self.default_email:
            self.email_input.setText(self.default_email)
        layout.addWidget(self.email_input)
        
        # Auth-Status anzeigen
        if self.api_user and self.api_password:
            auth_status = QLabel("Authentifizierung via API-Credentials")
            auth_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            auth_status.setStyleSheet("color: #a6e3a1; font-size: 11px;")
            layout.addWidget(auth_status)

        # Email-Eingabe mit Enter verbinden
        self.email_input.returnPressed.connect(self.do_login)
        
        # Remember Me
        self.remember_checkbox = QCheckBox("Angemeldet bleiben")
        self.remember_checkbox.setChecked(True)
        layout.addWidget(self.remember_checkbox)
        
        layout.addSpacing(10)
        
        # Login Button
        self.login_btn = QPushButton("Anmelden")
        self.login_btn.clicked.connect(self.do_login)
        layout.addWidget(self.login_btn)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # Register Link
        register_label = QLabel("Noch kein Konto? <a href='https://ailinux.me/register' style='color: #89b4fa;'>Registrieren</a>")
        register_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_label.setOpenExternalLinks(True)
        layout.addWidget(register_label)
        
        layout.addStretch()
    
    def load_saved_session(self):
        """Lade gespeicherte Session"""
        if self.session_file.exists():
            try:
                data = json.loads(self.session_file.read_text())
                if data.get("remember"):
                    self.email_input.setText(data.get("email", ""))
                    # Auto-Login wenn Token vorhanden
                    if data.get("token"):
                        self.login_successful.emit(data)
                        self.accept()
            except:
                pass
    
    def save_session(self, user_data: dict):
        """Speichere Session"""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
        session_data = {
            "email": user_data.get("email"),
            "user_id": user_data.get("user_id"),
            "tier": user_data.get("tier"),
            "tier_name": user_data.get("tier_name"),
            "token": user_data.get("token"),
            "remember": self.remember_checkbox.isChecked()
        }
        
        self.session_file.write_text(json.dumps(session_data, indent=2))
        self.session_file.chmod(0o600)
    
    def clear_session(self):
        """Lösche Session"""
        if self.session_file.exists():
            self.session_file.unlink()
    
    def do_login(self):
        """Login starten"""
        import re
        email = self.email_input.text().strip()

        if not email:
            self.status_label.setText("Bitte Email eingeben")
            return

        # Email-Format validieren
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            self.status_label.setText("Ungültiges Email-Format")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Anmelden...")
        self.status_label.setText("")

        self.worker = AuthWorker(
            email=email,
            server_url=self.server_url,
            api_user=self.api_user,
            api_password=self.api_password,
            client_id=self.client_id,
            user_id=self.user_id
        )
        self.worker.login_success.connect(self.on_login_success)
        self.worker.login_failed.connect(self.on_login_failed)
        self.worker.start()
    
    def on_login_success(self, user_data: dict):
        """Login erfolgreich"""
        if self.remember_checkbox.isChecked():
            self.save_session(user_data)
        
        self.login_successful.emit(user_data)
        self.accept()
    
    def on_login_failed(self, error: str):
        """Login fehlgeschlagen"""
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Anmelden")
        self.status_label.setText(f"{error}")


class SessionManager:
    """Session-Verwaltung"""
    
    def __init__(self):
        self.session_file = Path.home() / ".config" / "ailinux" / "session.json"
        self.current_user = None
        self.load()
    
    def load(self):
        """Lade Session"""
        if self.session_file.exists():
            try:
                self.current_user = json.loads(self.session_file.read_text())
            except:
                self.current_user = None
    
    def save(self, user_data: dict):
        """Speichere Session"""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_user = user_data
        self.session_file.write_text(json.dumps(user_data, indent=2))
        self.session_file.chmod(0o600)
    
    def clear(self):
        """Logout"""
        self.current_user = None
        if self.session_file.exists():
            self.session_file.unlink()
    
    def is_logged_in(self) -> bool:
        """Prüfe ob eingeloggt"""
        return self.current_user is not None and self.current_user.get("email")
    
    def get_user_id(self) -> str:
        """Hole User-ID"""
        if self.current_user:
            return self.current_user.get("user_id") or self.current_user.get("email") or "anonymous"
        return "anonymous"
    
    def get_email(self) -> str:
        """Hole Email"""
        if self.current_user:
            return self.current_user.get("email", "")
        return ""
    
    def get_tier(self) -> str:
        """Hole Tier"""
        if self.current_user:
            return self.current_user.get("tier", "free")
        return "free"
    
    def get_tier_name(self) -> str:
        """Hole Tier-Name"""
        if self.current_user:
            return self.current_user.get("tier_name", "Free")
        return "Free"
