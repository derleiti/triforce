"""
Browser Widget - Integrierter Webbrowser mit Tabs, Lesezeichen und KI-Features
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QMenu, QProgressBar, QTabWidget, QTabBar,
    QDialog, QListWidget, QListWidgetItem, QLabel, QInputDialog,
    QMessageBox, QToolButton, QSizePolicy
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QAction, QIcon
import json
from pathlib import Path


class BookmarkManager:
    """Verwaltet Lesezeichen persistent"""

    def __init__(self):
        self.bookmarks_file = Path.home() / ".config" / "ailinux" / "bookmarks.json"
        self.bookmarks = []
        self.load()

    def load(self):
        """Lade Lesezeichen aus Datei"""
        if self.bookmarks_file.exists():
            try:
                self.bookmarks = json.loads(self.bookmarks_file.read_text())
            except:
                self.bookmarks = []
        else:
            # Standard-Lesezeichen
            self.bookmarks = [
                {"title": "AILinux Search", "url": "https://search.ailinux.me"},
                {"title": "DuckDuckGo", "url": "https://duckduckgo.com"},
                {"title": "GitHub", "url": "https://github.com"},
            ]
            self.save()

    def save(self):
        """Speichere Lesezeichen"""
        self.bookmarks_file.parent.mkdir(parents=True, exist_ok=True)
        self.bookmarks_file.write_text(json.dumps(self.bookmarks, indent=2))

    def add(self, title: str, url: str):
        """Lesezeichen hinzufügen"""
        # Duplikate vermeiden
        for b in self.bookmarks:
            if b["url"] == url:
                return False
        self.bookmarks.append({"title": title, "url": url})
        self.save()
        return True

    def remove(self, url: str):
        """Lesezeichen entfernen"""
        self.bookmarks = [b for b in self.bookmarks if b["url"] != url]
        self.save()

    def is_bookmarked(self, url: str) -> bool:
        """Prüfe ob URL bereits gespeichert"""
        return any(b["url"] == url for b in self.bookmarks)

    def get_all(self) -> list:
        """Alle Lesezeichen abrufen"""
        return self.bookmarks.copy()


class BookmarkDialog(QDialog):
    """Dialog zur Lesezeichen-Verwaltung"""

    bookmark_selected = pyqtSignal(str)  # URL

    def __init__(self, bookmark_manager: BookmarkManager, parent=None):
        super().__init__(parent)
        self.bookmark_manager = bookmark_manager
        self.setup_ui()
        self.load_bookmarks()

    def setup_ui(self):
        self.setWindowTitle("⭐ Lesezeichen")
        self.setMinimumSize(400, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QListWidget {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #45475a;
            }
            QListWidget::item:hover {
                background-color: #45475a;
            }
            QListWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton#deleteBtn {
                background-color: #f38ba8;
            }
            QPushButton#deleteBtn:hover {
                background-color: #eba0ac;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel("⭐ Deine Lesezeichen")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)

        # Liste
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.open_bookmark)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()

        open_btn = QPushButton("🔗 Öffnen")
        open_btn.clicked.connect(self.open_selected)
        btn_layout.addWidget(open_btn)

        delete_btn = QPushButton("🗑️ Löschen")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(delete_btn)

        close_btn = QPushButton("✖ Schließen")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def load_bookmarks(self):
        """Lade Lesezeichen in Liste"""
        self.list_widget.clear()
        for bookmark in self.bookmark_manager.get_all():
            item = QListWidgetItem(f"⭐ {bookmark['title']}\n   {bookmark['url']}")
            item.setData(Qt.ItemDataRole.UserRole, bookmark["url"])
            self.list_widget.addItem(item)

    def open_bookmark(self, item):
        """Lesezeichen öffnen"""
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.bookmark_selected.emit(url)
            self.accept()

    def open_selected(self):
        """Ausgewähltes Lesezeichen öffnen"""
        item = self.list_widget.currentItem()
        if item:
            self.open_bookmark(item)

    def delete_selected(self):
        """Ausgewähltes Lesezeichen löschen"""
        item = self.list_widget.currentItem()
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            self.bookmark_manager.remove(url)
            self.load_bookmarks()


class BrowserTab(QWidget):
    """Einzelner Browser-Tab"""

    text_selected = pyqtSignal(str)
    title_changed = pyqtSignal(str)
    url_changed = pyqtSignal(str)
    loading_progress = pyqtSignal(int)
    new_tab_requested = pyqtSignal(str)  # URL für neuen Tab

    def __init__(self, url: str = "https://search.ailinux.me", parent=None):
        super().__init__(parent)
        self.setup_ui(url)

    def setup_ui(self, url: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl(url))

        # Context Menu für Text-Selektion
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.web_view.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.web_view)

        # Signals verbinden
        self.web_view.titleChanged.connect(self.title_changed.emit)
        self.web_view.urlChanged.connect(lambda u: self.url_changed.emit(u.toString()))
        self.web_view.loadProgress.connect(self.loading_progress.emit)

        # Link in neuem Tab öffnen
        self.web_view.page().newWindowRequested.connect(self.handle_new_window)

    def handle_new_window(self, request):
        """Neue Fenster/Links als Tab öffnen"""
        self.new_tab_requested.emit(request.requestedUrl().toString())
        request.openIn(self.web_view.page())

    def navigate(self, url: str):
        """Zu URL navigieren"""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.web_view.setUrl(QUrl(url))

    def show_context_menu(self, position):
        """Kontextmenü mit KI-Optionen"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)

        # Standard-Aktionen
        back_action = menu.addAction("◀ Zurück")
        back_action.triggered.connect(lambda: self.web_view.back())

        forward_action = menu.addAction("▶ Vorwärts")
        forward_action.triggered.connect(lambda: self.web_view.forward())

        reload_action = menu.addAction("🔄 Neu laden")
        reload_action.triggered.connect(lambda: self.web_view.reload())

        menu.addSeparator()

        # KI-Aktionen
        ai_menu = menu.addMenu("🤖 KI-Aktionen")

        # Auf markierten Text
        explain_action = ai_menu.addAction("💡 Erkläre markierten Text")
        explain_action.triggered.connect(lambda: self.ai_action("explain"))

        translate_action = ai_menu.addAction("🌍 Übersetzen")
        translate_action.triggered.connect(lambda: self.ai_action("translate"))

        summarize_action = ai_menu.addAction("📝 Zusammenfassen")
        summarize_action.triggered.connect(lambda: self.ai_action("summarize"))

        ai_menu.addSeparator()

        # Auf ganze Seite
        page_summarize = ai_menu.addAction("📄 Seite zusammenfassen")
        page_summarize.triggered.connect(lambda: self.ai_page_action("summarize"))

        page_extract = ai_menu.addAction("📋 Wichtiges extrahieren")
        page_extract.triggered.connect(lambda: self.ai_page_action("extract"))

        page_questions = ai_menu.addAction("❓ FAQ generieren")
        page_questions.triggered.connect(lambda: self.ai_page_action("questions"))

        menu.exec(self.web_view.mapToGlobal(position))

    def ai_action(self, action: str):
        """KI-Aktion auf selektierten Text"""
        self.web_view.page().runJavaScript(
            "window.getSelection().toString()",
            lambda text: self.text_selected.emit(f"{action}:{text}") if text else None
        )

    def ai_page_action(self, action: str):
        """KI-Aktion auf gesamte Seite"""
        # Extrahiere Text-Inhalt der Seite
        js_code = """
        (function() {
            var body = document.body;
            var clone = body.cloneNode(true);
            var scripts = clone.getElementsByTagName('script');
            var styles = clone.getElementsByTagName('style');
            while(scripts.length > 0) scripts[0].remove();
            while(styles.length > 0) styles[0].remove();
            return clone.innerText || clone.textContent;
        })();
        """
        url = self.web_view.url().toString()
        self.web_view.page().runJavaScript(
            js_code,
            lambda text: self.text_selected.emit(f"page_{action}:{url}|{text[:10000]}") if text else None
        )

    def get_url(self) -> str:
        """Aktuelle URL abrufen"""
        return self.web_view.url().toString()

    def get_title(self) -> str:
        """Aktueller Titel abrufen"""
        return self.web_view.title() or "Neuer Tab"


class ClosableTabBar(QTabBar):
    """Tab-Bar mit Close-Button und Neuer-Tab-Button"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setExpanding(False)
        self.setStyleSheet("""
            QTabBar {
                background-color: #181825;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                max-width: 200px;
            }
            QTabBar::tab:selected {
                background-color: #45475a;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3b3d4f;
            }
            QTabBar::close-button {
                image: none;
                background: transparent;
                border: none;
            }
            QTabBar::close-button:hover {
                background: #f38ba8;
                border-radius: 4px;
            }
        """)


class BrowserWidget(QWidget):
    """Integrierter Browser mit Tabs, Lesezeichen und KI-Integration"""

    text_selected = pyqtSignal(str)  # Für KI-Analyse von Text
    url_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bookmark_manager = BookmarkManager()
        self.tabs = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Navigation Bar
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(5, 5, 5, 5)
        nav_layout.setSpacing(5)

        # Navigation Buttons Style
        btn_style = """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """

        self.back_btn = QPushButton("◀")
        self.back_btn.setFixedSize(32, 28)
        self.back_btn.setStyleSheet(btn_style)
        self.back_btn.setToolTip("Zurück")
        self.back_btn.clicked.connect(self.go_back)
        nav_layout.addWidget(self.back_btn)

        self.forward_btn = QPushButton("▶")
        self.forward_btn.setFixedSize(32, 28)
        self.forward_btn.setStyleSheet(btn_style)
        self.forward_btn.setToolTip("Vorwärts")
        self.forward_btn.clicked.connect(self.go_forward)
        nav_layout.addWidget(self.forward_btn)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(32, 28)
        self.refresh_btn.setStyleSheet(btn_style)
        self.refresh_btn.setToolTip("Aktualisieren")
        self.refresh_btn.clicked.connect(self.refresh)
        nav_layout.addWidget(self.refresh_btn)

        self.home_btn = QPushButton("🏠")
        self.home_btn.setFixedSize(32, 28)
        self.home_btn.setStyleSheet(btn_style)
        self.home_btn.setToolTip("Startseite")
        self.home_btn.clicked.connect(lambda: self.navigate("https://search.ailinux.me"))
        nav_layout.addWidget(self.home_btn)

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("URL eingeben oder suchen...")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        self.url_bar.returnPressed.connect(self.navigate_from_bar)
        nav_layout.addWidget(self.url_bar)

        # Bookmark-Button (Star)
        self.bookmark_btn = QPushButton("☆")
        self.bookmark_btn.setFixedSize(32, 28)
        self.bookmark_btn.setStyleSheet(btn_style)
        self.bookmark_btn.setToolTip("Lesezeichen hinzufügen")
        self.bookmark_btn.clicked.connect(self.toggle_bookmark)
        nav_layout.addWidget(self.bookmark_btn)

        # Bookmarks-Manager Button
        self.bookmarks_btn = QPushButton("📚")
        self.bookmarks_btn.setFixedSize(32, 28)
        self.bookmarks_btn.setStyleSheet(btn_style)
        self.bookmarks_btn.setToolTip("Lesezeichen verwalten")
        self.bookmarks_btn.clicked.connect(self.show_bookmarks)
        nav_layout.addWidget(self.bookmarks_btn)

        # Neuer Tab Button
        self.new_tab_btn = QPushButton("➕")
        self.new_tab_btn.setFixedSize(32, 28)
        self.new_tab_btn.setStyleSheet(btn_style)
        self.new_tab_btn.setToolTip("Neuer Tab (Ctrl+T)")
        self.new_tab_btn.clicked.connect(lambda: self.add_tab())
        nav_layout.addWidget(self.new_tab_btn)

        layout.addLayout(nav_layout)

        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(2)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e2e;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
            }
        """)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Lesezeichen-Schnellzugriffsleiste
        self.bookmark_bar = QWidget()
        self.bookmark_bar_layout = QHBoxLayout(self.bookmark_bar)
        self.bookmark_bar_layout.setContentsMargins(5, 2, 5, 2)
        self.bookmark_bar_layout.setSpacing(4)
        self.bookmark_bar.setStyleSheet("background-color: #181825;")
        self.update_bookmark_bar()
        layout.addWidget(self.bookmark_bar)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabBar(ClosableTabBar())
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e2e;
            }
        """)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tab_widget)

        # Ersten Tab hinzufügen
        self.add_tab("https://search.ailinux.me")

    def add_tab(self, url: str = "https://search.ailinux.me"):
        """Neuen Tab hinzufügen"""
        tab = BrowserTab(url)
        tab.text_selected.connect(self.text_selected.emit)
        tab.title_changed.connect(lambda title: self.update_tab_title(tab, title))
        tab.url_changed.connect(self.on_url_changed)
        tab.loading_progress.connect(self.on_loading_progress)
        tab.new_tab_requested.connect(self.add_tab)

        index = self.tab_widget.addTab(tab, "🌐 Laden...")
        self.tab_widget.setCurrentIndex(index)
        self.tabs.append(tab)
        return tab

    def close_tab(self, index: int):
        """Tab schließen"""
        if self.tab_widget.count() > 1:
            tab = self.tab_widget.widget(index)
            self.tab_widget.removeTab(index)
            if tab in self.tabs:
                self.tabs.remove(tab)
            tab.deleteLater()
        else:
            # Letzter Tab: Zur Startseite navigieren
            self.navigate("https://search.ailinux.me")

    def current_tab(self) -> BrowserTab:
        """Aktuellen Tab abrufen"""
        return self.tab_widget.currentWidget()

    def update_tab_title(self, tab: BrowserTab, title: str):
        """Tab-Titel aktualisieren"""
        index = self.tab_widget.indexOf(tab)
        if index >= 0:
            # Titel kürzen wenn zu lang
            short_title = title[:25] + "..." if len(title) > 25 else title
            self.tab_widget.setTabText(index, short_title)
            self.tab_widget.setTabToolTip(index, title)

    def on_tab_changed(self, index: int):
        """Tab gewechselt"""
        tab = self.tab_widget.widget(index)
        if tab:
            url = tab.get_url()
            self.url_bar.setText(url)
            self.update_bookmark_button(url)

    def on_url_changed(self, url: str):
        """URL im aktuellen Tab geändert"""
        if self.tab_widget.currentWidget():
            current_url = self.current_tab().get_url()
            self.url_bar.setText(current_url)
            self.url_changed.emit(current_url)
            self.update_bookmark_button(current_url)

    def on_loading_progress(self, progress: int):
        """Lade-Fortschritt"""
        if progress < 100:
            self.progress.show()
            self.progress.setValue(progress)
        else:
            self.progress.hide()

    def update_bookmark_button(self, url: str):
        """Bookmark-Button Status aktualisieren"""
        if self.bookmark_manager.is_bookmarked(url):
            self.bookmark_btn.setText("⭐")
            self.bookmark_btn.setToolTip("Lesezeichen entfernen")
        else:
            self.bookmark_btn.setText("☆")
            self.bookmark_btn.setToolTip("Lesezeichen hinzufügen")

    def toggle_bookmark(self):
        """Lesezeichen hinzufügen/entfernen"""
        tab = self.current_tab()
        if not tab:
            return

        url = tab.get_url()
        title = tab.get_title()

        if self.bookmark_manager.is_bookmarked(url):
            self.bookmark_manager.remove(url)
            self.bookmark_btn.setText("☆")
            self.bookmark_btn.setToolTip("Lesezeichen hinzufügen")
        else:
            # Titel bearbeiten?
            new_title, ok = QInputDialog.getText(
                self, "Lesezeichen hinzufügen",
                "Titel:", text=title
            )
            if ok:
                self.bookmark_manager.add(new_title or title, url)
                self.bookmark_btn.setText("⭐")
                self.bookmark_btn.setToolTip("Lesezeichen entfernen")

        # Lesezeichen-Leiste aktualisieren
        self.update_bookmark_bar()

    def show_bookmarks(self):
        """Lesezeichen-Dialog anzeigen"""
        dialog = BookmarkDialog(self.bookmark_manager, self)
        dialog.bookmark_selected.connect(self.navigate)
        dialog.exec()
        # Lesezeichen-Leiste aktualisieren (falls Lesezeichen gelöscht wurden)
        self.update_bookmark_bar()

    def navigate(self, url: str):
        """Im aktuellen Tab navigieren"""
        tab = self.current_tab()
        if tab:
            tab.navigate(url)

    def navigate_from_bar(self):
        """Navigation aus URL-Bar"""
        url = self.url_bar.text().strip()
        if url:
            # Prüfen ob Suche oder URL
            if " " in url or "." not in url:
                # Suche
                url = f"https://duckduckgo.com/?q={url}"
            self.navigate(url)

    def go_back(self):
        """Zurück navigieren"""
        tab = self.current_tab()
        if tab:
            tab.web_view.back()

    def go_forward(self):
        """Vorwärts navigieren"""
        tab = self.current_tab()
        if tab:
            tab.web_view.forward()

    def refresh(self):
        """Seite neu laden"""
        tab = self.current_tab()
        if tab:
            tab.web_view.reload()

    def update_bookmark_bar(self):
        """Lesezeichen-Schnellzugriffsleiste aktualisieren"""
        # Alte Buttons entfernen
        while self.bookmark_bar_layout.count():
            item = self.bookmark_bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        btn_style = """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """

        # Lesezeichen-Buttons (max 8)
        for bookmark in self.bookmark_manager.get_all()[:8]:
            btn = QPushButton(f"⭐ {bookmark['title'][:15]}")
            btn.setStyleSheet(btn_style)
            btn.setToolTip(bookmark['url'])
            btn.clicked.connect(lambda checked, url=bookmark['url']: self.navigate(url))
            self.bookmark_bar_layout.addWidget(btn)

        # Stretch am Ende
        self.bookmark_bar_layout.addStretch()
