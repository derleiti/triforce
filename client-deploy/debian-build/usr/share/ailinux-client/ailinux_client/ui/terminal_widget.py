"""
AILinux Terminal Widget
=======================

Proper VT100 terminal emulator using pyte for ANSI/escape code handling.
Provides full color support and terminal features (vim, htop, etc.).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPlainTextEdit, QToolButton, QPushButton, QSizePolicy, QLabel, QScrollBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QProcess, QSettings
from PyQt6.QtGui import (
    QFont, QTextCursor, QColor, QKeyEvent, QTextCharFormat,
    QPainter, QFontMetrics, QPalette, QTextOption
)
import os
import sys
import pty
import fcntl
import struct
import termios
import select
import signal
import shutil
import logging
from pathlib import Path
from typing import Optional

# VT100 Emulator
try:
    import pyte
    HAS_PYTE = True
except ImportError:
    HAS_PYTE = False

logger = logging.getLogger("ailinux.terminal_widget")


# ============================================================================
# External Terminal Embedding (Konsole/xterm)
# ============================================================================

class EmbeddedTerminal(QWidget):
    """
    Embeds an external terminal (konsole, xfce4-terminal, xterm) into Qt widget.
    Provides full color support, proper ANSI handling, and native terminal features.
    """

    finished = pyqtSignal(int)

    # Terminal preference order - system default first
    TERMINALS = [
        # System default terminals (detected from OS config)
        ("x-terminal-emulator", ["x-terminal-emulator", "-e"]),  # Debian/Ubuntu default
        ("sensible-terminal", ["sensible-terminal", "-e"]),      # Alternative default
        # Common terminals as fallback
        ("konsole", ["konsole", "--nofork", "-e"]),
        ("xfce4-terminal", ["xfce4-terminal", "--disable-server", "-e"]),
        ("gnome-terminal", ["gnome-terminal", "--wait", "--"]),
        ("alacritty", ["alacritty", "-e"]),
        ("kitty", ["kitty", "-e"]),
        ("tilix", ["tilix", "-e"]),
        ("terminator", ["terminator", "-x"]),
        ("xterm", ["xterm", "-e"]),
    ]

    def __init__(self, working_dir: str = None, startup_command: str = None, parent=None):
        super().__init__(parent)
        self.working_dir = working_dir or str(Path.home())
        self.startup_command = startup_command
        self.process: Optional[QProcess] = None
        self.terminal_name = None

        self._setup_ui()
        QTimer.singleShot(100, self._start_terminal)

    def _setup_ui(self):
        """Setup container widget"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container for embedded window
        self.container = QWidget()
        self.container.setStyleSheet("background: #0d1117;")
        self.container.setMinimumSize(400, 200)
        layout.addWidget(self.container, 1)

        # Status label (shown while loading)
        self.status_label = QLabel("Terminal wird gestartet...")
        self.status_label.setStyleSheet("color: #58a6ff; padding: 20px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def _find_terminal(self) -> tuple:
        """Find available terminal emulator - prefers system default"""
        # Check $TERMINAL environment variable first
        env_terminal = os.environ.get("TERMINAL")
        if env_terminal and shutil.which(env_terminal):
            logger.info(f"Using $TERMINAL: {env_terminal}")
            return env_terminal, [env_terminal, "-e"]

        # Then try configured terminals in order
        for name, cmd in self.TERMINALS:
            if shutil.which(name):
                logger.info(f"Found terminal: {name}")
                return name, cmd
        return None, None

    def _start_terminal(self):
        """Start external terminal"""
        self.terminal_name, base_cmd = self._find_terminal()

        if not self.terminal_name:
            self.status_label.setText("Kein Terminal gefunden!\nBitte installieren: konsole, xfce4-terminal, oder xterm")
            self.status_label.setStyleSheet("color: #f85149; padding: 20px;")
            return

        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.working_dir)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        # Build command
        if self.startup_command:
            # Run command in shell
            shell_cmd = f'cd "{self.working_dir}" && {self.startup_command}; exec bash'
            cmd = base_cmd + ["bash", "-c", shell_cmd]
        else:
            # Just open shell
            cmd = base_cmd + ["bash", "--login"]

        # Set environment
        from PyQt6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        env.insert("TERM", "xterm-256color")
        env.insert("AILINUX_TERMINAL", "1")
        self.process.setProcessEnvironment(env)

        logger.info(f"Starting terminal: {' '.join(cmd)}")

        # Special handling for different terminals
        if self.terminal_name == "konsole":
            self._start_konsole()
        elif self.terminal_name == "xterm":
            self._start_xterm()
        else:
            # Generic start
            self.process.start(cmd[0], cmd[1:])

        self.status_label.hide()

    def _start_konsole(self):
        """Start Konsole with embedding"""
        cmd = ["konsole", "--nofork"]

        if self.startup_command:
            shell_cmd = f'cd "{self.working_dir}" && {self.startup_command}; exec bash'
            cmd.extend(["-e", "bash", "-c", shell_cmd])
        else:
            cmd.extend(["-e", "bash", "--login"])

        self.process.setWorkingDirectory(self.working_dir)
        self.process.start(cmd[0], cmd[1:])

    def _start_xterm(self):
        """Start xterm with better settings"""
        cmd = [
            "xterm",
            "-fa", "Monospace",
            "-fs", "11",
            "-bg", "#0d1117",
            "-fg", "#c9d1d9",
            "-geometry", "100x30",
        ]

        if self.startup_command:
            shell_cmd = f'cd "{self.working_dir}" && {self.startup_command}; exec bash'
            cmd.extend(["-e", "bash", "-c", shell_cmd])
        else:
            cmd.extend(["-e", "bash", "--login"])

        self.process.setWorkingDirectory(self.working_dir)
        self.process.start(cmd[0], cmd[1:])

    def _on_finished(self, exit_code: int, exit_status):
        """Terminal process finished"""
        logger.info(f"Terminal finished: exit_code={exit_code}")
        self.finished.emit(exit_code)
        self.status_label.setText(f"Terminal beendet (Code: {exit_code})")
        self.status_label.setStyleSheet("color: #8b949e; padding: 20px;")
        self.status_label.show()

    def _on_error(self, error):
        """Process error occurred"""
        error_msg = {
            QProcess.ProcessError.FailedToStart: "Start fehlgeschlagen",
            QProcess.ProcessError.Crashed: "Abgestürzt",
            QProcess.ProcessError.Timedout: "Timeout",
            QProcess.ProcessError.WriteError: "Schreibfehler",
            QProcess.ProcessError.ReadError: "Lesefehler",
        }.get(error, "Unbekannter Fehler")

        logger.error(f"Terminal error: {error_msg}")
        self.status_label.setText(f"Terminal Fehler: {error_msg}")
        self.status_label.setStyleSheet("color: #f85149; padding: 20px;")
        self.status_label.show()

    def send_text(self, text: str):
        """Send text to terminal (not supported for external terminals)"""
        logger.warning("send_text not supported for external terminals")

    def focus(self):
        """Focus the terminal"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.setFocus()

    def close_terminal(self):
        """Close terminal"""
        if self.process:
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                self.process.kill()


# ============================================================================
# Pyte-based VT100 Terminal (Full terminal emulation)
# ============================================================================

class PTYReader(QThread):
    """Thread for reading PTY output"""
    data_ready = pyqtSignal(bytes)
    finished = pyqtSignal()

    def __init__(self, fd):
        super().__init__()
        self.fd = fd
        self.running = True

    def run(self):
        while self.running:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.01)
                if r:
                    try:
                        data = os.read(self.fd, 65536)
                        if data:
                            self.data_ready.emit(data)
                        else:
                            break
                    except OSError:
                        break
            except Exception as e:
                logger.error(f"PTY read error: {e}")
                break
        self.finished.emit()

    def stop(self):
        self.running = False


class TerminalDisplay(QWidget):
    """
    Custom widget that renders the pyte screen with proper colors.
    Supports customizable colors and fonts via QSettings.
    """

    # 256-color palette (standard + extended)
    COLORS_16 = {
        "black": "#0d1117", "red": "#f85149", "green": "#3fb950", "yellow": "#d29922",
        "blue": "#58a6ff", "magenta": "#bc8cff", "cyan": "#39c5cf", "white": "#c9d1d9",
        "brightblack": "#484f58", "brightred": "#ff7b72", "brightgreen": "#56d364",
        "brightyellow": "#e3b341", "brightblue": "#79c0ff", "brightmagenta": "#d2a8ff",
        "brightcyan": "#56d4dd", "brightwhite": "#ffffff", "default": "#c9d1d9",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("AILinux", "Client")
        self.screen = None
        self.char_width = 0
        self.char_height = 0

        # Load settings
        self._load_settings()
        self._update_font_metrics()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)

        # Allow widget to shrink and expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 100)

        self._update_palette()

        # Cursor blink
        self.cursor_visible = True
        self.cursor_timer = QTimer()
        self.cursor_timer.timeout.connect(self._blink_cursor)
        if self.cursor_blink:
            self.cursor_timer.start(500)

        # Mouse selection
        self.selection_start = None  # (col, row)
        self.selection_end = None    # (col, row)
        self.selecting = False
        self.setMouseTracking(True)

        # Scroll offset (for history display)
        self.scroll_offset = 0
        self.terminal = None

    def _load_settings(self):
        """Load terminal settings"""
        # Colors
        self.bg_color = self.settings.value("term_bg_color", "#1e1e1e")
        self.fg_color = self.settings.value("term_fg_color", "#e0e0e0")
        self.cursor_color = self.settings.value("term_cursor_color", "#3b82f6")
        self.selection_color = self.settings.value("term_selection_color", "#3b82f6")

        # Font
        font_family = self.settings.value("term_font_family", "Monospace")
        font_size = self.settings.value("term_font_size", 12, type=int)
        self.font = QFont(font_family, font_size)
        self.font.setStyleHint(QFont.StyleHint.Monospace)

        # Behavior
        self.cursor_blink = self.settings.value("term_cursor_blink", True, type=bool)

        # Update color palette for default
        self.COLORS_16["default"] = self.fg_color
        self.COLORS_16["black"] = self.bg_color

    def _update_palette(self):
        """Update background palette"""
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(self.bg_color))
        self.setPalette(palette)

    def apply_settings(self):
        """Apply settings from QSettings (called when settings change)"""
        self._load_settings()
        self._update_font_metrics()
        self._update_palette()

        # Update cursor blink
        if self.cursor_blink and not self.cursor_timer.isActive():
            self.cursor_timer.start(500)
        elif not self.cursor_blink and self.cursor_timer.isActive():
            self.cursor_timer.stop()
            self.cursor_visible = True

        self.update()

    def _update_font_metrics(self):
        fm = QFontMetrics(self.font)
        self.char_width = fm.horizontalAdvance('M')
        self.char_height = fm.height()

    def set_screen(self, screen):
        self.screen = screen

    def set_terminal(self, terminal):
        """Set parent terminal for scroll callbacks"""
        self.terminal = terminal

    def wheelEvent(self, event):
        """Handle mouse wheel for scrolling"""
        if hasattr(self, 'terminal') and self.terminal:
            delta = event.angleDelta().y()
            lines = 3  # Scroll 3 lines at a time
            if delta > 0:
                self.terminal.scroll_up(lines)
            elif delta < 0:
                self.terminal.scroll_down(lines)
        event.accept()

    def _blink_cursor(self):
        self.cursor_visible = not self.cursor_visible
        self.update()

    def _pos_to_cell(self, pos):
        """Convert pixel position to (col, row)"""
        if self.char_width <= 0 or self.char_height <= 0:
            return (0, 0)
        col = max(0, pos.x() // self.char_width)
        row = max(0, pos.y() // self.char_height)
        if self.screen:
            col = min(col, self.screen.columns - 1)
            row = min(row, self.screen.lines - 1)
        return (col, row)

    def mousePressEvent(self, event):
        """Start selection on mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.selection_start = self._pos_to_cell(event.pos())
            self.selection_end = self.selection_start
            self.selecting = True
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Update selection on mouse move"""
        if self.selecting:
            self.selection_end = self._pos_to_cell(event.pos())
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End selection on mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.selecting = False
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """Show context menu on right-click"""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background: #3b82f6;
            }
        """)

        copy_action = menu.addAction("Kopieren (Ctrl+Shift+C)")
        copy_action.triggered.connect(self.copy_selection)

        paste_action = menu.addAction("Einfügen (Ctrl+Shift+V)")
        paste_action.triggered.connect(self.paste_clipboard)

        menu.addSeparator()

        select_all_action = menu.addAction("Alles auswählen")
        select_all_action.triggered.connect(self.select_all)

        clear_selection_action = menu.addAction("Auswahl aufheben")
        clear_selection_action.triggered.connect(self.clear_selection)

        menu.exec(event.globalPos())

    def get_selected_text(self) -> str:
        """Get currently selected text"""
        if not self.screen or not self.selection_start or not self.selection_end:
            return ""

        start = self.selection_start
        end = self.selection_end

        # Normalize selection (start before end)
        if (start[1] > end[1]) or (start[1] == end[1] and start[0] > end[0]):
            start, end = end, start

        lines = []
        for row in range(start[1], end[1] + 1):
            if row >= len(self.screen.display):
                break
            line = self.screen.display[row]

            if row == start[1] and row == end[1]:
                # Single line selection
                text = line[start[0]:end[0] + 1]
            elif row == start[1]:
                # First line
                text = line[start[0]:]
            elif row == end[1]:
                # Last line
                text = line[:end[0] + 1]
            else:
                # Middle line
                text = line

            lines.append(text.rstrip())

        return '\n'.join(lines)

    def copy_selection(self):
        """Copy selected text to clipboard"""
        from PyQt6.QtWidgets import QApplication
        text = self.get_selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def paste_clipboard(self):
        """Paste from clipboard - emits signal to parent"""
        from PyQt6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        if text and self.parent():
            # Find PyteTerminal parent
            parent = self.parent()
            while parent and not isinstance(parent, PyteTerminal):
                parent = parent.parent()
            if parent:
                parent._write(text)

    def select_all(self):
        """Select all text"""
        if self.screen:
            self.selection_start = (0, 0)
            self.selection_end = (self.screen.columns - 1, self.screen.lines - 1)
            self.update()

    def clear_selection(self):
        """Clear selection"""
        self.selection_start = None
        self.selection_end = None
        self.update()

    def _is_selected(self, col, row) -> bool:
        """Check if cell is in selection"""
        if not self.selection_start or not self.selection_end:
            return False

        start = self.selection_start
        end = self.selection_end

        # Normalize
        if (start[1] > end[1]) or (start[1] == end[1] and start[0] > end[0]):
            start, end = end, start

        if row < start[1] or row > end[1]:
            return False
        if row == start[1] and row == end[1]:
            return start[0] <= col <= end[0]
        if row == start[1]:
            return col >= start[0]
        if row == end[1]:
            return col <= end[0]
        return True

    def _get_color(self, color, default="#c9d1d9"):
        """Convert pyte color to QColor"""
        if color == "default" or color is None:
            return QColor(default)
        if isinstance(color, str):
            return QColor(self.COLORS_16.get(color, default))
        # 256-color or RGB
        if isinstance(color, int):
            # Standard 256-color palette
            if color < 16:
                names = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
                         "brightblack", "brightred", "brightgreen", "brightyellow",
                         "brightblue", "brightmagenta", "brightcyan", "brightwhite"]
                return QColor(self.COLORS_16.get(names[color], default))
            elif color < 232:
                # 216 colors (6x6x6 cube)
                color -= 16
                r = (color // 36) * 51
                g = ((color // 6) % 6) * 51
                b = (color % 6) * 51
                return QColor(r, g, b)
            else:
                # 24 grayscale
                gray = (color - 232) * 10 + 8
                return QColor(gray, gray, gray)
        return QColor(default)

    def paintEvent(self, event):
        if not self.screen:
            return

        painter = QPainter(self)
        painter.setFont(self.font)

        # Background
        painter.fillRect(self.rect(), QColor(self.bg_color))

        # Get history lines if scrolled
        history_lines = []
        if self.scroll_offset > 0 and hasattr(self.screen, 'history'):
            history_lines = list(self.screen.history.top)

        # Draw each row
        for y in range(self.screen.lines):
            # Determine which line to show based on scroll offset
            history_idx = len(history_lines) - self.scroll_offset + y

            if self.scroll_offset > 0 and history_idx < len(history_lines) and history_idx >= 0:
                # Show history line
                line = history_lines[history_idx]
                for x, char_data in enumerate(line):
                    if x >= self.screen.columns:
                        break
                    char = char_data.data if hasattr(char_data, 'data') else str(char_data)
                    fg = self._get_color(getattr(char_data, 'fg', 'default'), "#c9d1d9")
                    bg = self._get_color(getattr(char_data, 'bg', 'default'), "#0d1117")
                    bold = getattr(char_data, 'bold', False)
                    reverse = getattr(char_data, 'reverse', False)

                    if reverse:
                        fg, bg = bg, fg

                    if self._is_selected(x, y):
                        bg = QColor(self.selection_color)
                        fg = QColor("#ffffff")

                    px = x * self.char_width
                    py = y * self.char_height

                    if self._is_selected(x, y) or bg != QColor("#0d1117"):
                        painter.fillRect(px, py, self.char_width, self.char_height, bg)

                    if char and char != ' ':
                        font = QFont(self.font)
                        if bold:
                            font.setBold(True)
                        painter.setFont(font)
                        painter.setPen(fg)
                        painter.drawText(px, py + self.char_height - 3, char)
            else:
                # Show current screen line
                screen_y = y - max(0, self.scroll_offset - len(history_lines)) if self.scroll_offset > len(history_lines) else y
                if screen_y < 0 or screen_y >= len(self.screen.display):
                    continue

                line = self.screen.display[screen_y]
                for x, char in enumerate(line):
                    try:
                        char_data = self.screen.buffer[screen_y][x]
                        fg = self._get_color(char_data.fg, "#c9d1d9")
                        bg = self._get_color(char_data.bg, "#0d1117")
                        bold = char_data.bold
                        reverse = char_data.reverse
                    except (KeyError, IndexError):
                        fg = QColor("#c9d1d9")
                        bg = QColor("#0d1117")
                        bold = False
                        reverse = False

                    if reverse:
                        fg, bg = bg, fg

                    if self._is_selected(x, y):
                        bg = QColor(self.selection_color)
                        fg = QColor("#ffffff")

                    px = x * self.char_width
                    py = y * self.char_height

                    if self._is_selected(x, y) or bg != QColor("#0d1117"):
                        painter.fillRect(px, py, self.char_width, self.char_height, bg)

                    if char and char != ' ':
                        font = QFont(self.font)
                        if bold:
                            font.setBold(True)
                        painter.setFont(font)
                        painter.setPen(fg)
                        painter.drawText(px, py + self.char_height - 3, char)

        # Draw cursor only when at bottom (not scrolled)
        if self.scroll_offset == 0 and self.cursor_visible and self.hasFocus():
            cx = self.screen.cursor.x * self.char_width
            cy = self.screen.cursor.y * self.char_height
            painter.fillRect(cx, cy, self.char_width, self.char_height, QColor(self.cursor_color))

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        # Return reasonable default size
        return QSize(800, 400)

    def minimumSizeHint(self):
        from PyQt6.QtCore import QSize
        # Allow shrinking to small size
        return QSize(200, 100)


class PyteTerminal(QWidget):
    """
    Full VT100 terminal emulator using pyte.
    Supports colors, cursor positioning, vim, htop, etc.
    """

    finished = pyqtSignal(int)

    def __init__(self, working_dir: str = None, startup_command: str = None,
                 cols: int = 120, rows: int = 30, parent=None):
        super().__init__(parent)
        self.working_dir = working_dir or str(Path.home())
        self.startup_command = startup_command
        self.cols = cols
        self.rows = rows

        self.master_fd = None
        self.pid = None
        self.reader = None

        # Pyte screen with history (scrollback buffer)
        self.screen = pyte.HistoryScreen(cols, rows, history=10000)
        self.screen.set_mode(pyte.modes.LNM)  # Line feed mode
        self.stream = pyte.Stream(self.screen)

        # Scroll position (0 = bottom/current, positive = scrolled up)
        self.scroll_offset = 0

        self._setup_ui()
        self._start_pty()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # Allow terminal to shrink and expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 100)

        # Horizontal layout for display + scrollbar
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        self.display = TerminalDisplay()
        self.display.set_screen(self.screen)
        self.display.set_terminal(self)  # For scrolling callbacks
        h_layout.addWidget(self.display, 1)

        # Scrollbar
        self.scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.scrollbar.setStyleSheet("""
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                min-height: 20px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5a5a5a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.scrollbar.valueChanged.connect(self._on_scroll)
        h_layout.addWidget(self.scrollbar)

        layout.addLayout(h_layout)

    def _start_pty(self):
        """Start PTY with shell"""
        try:
            self.master_fd, slave_fd = pty.openpty()

            # Set terminal size
            winsize = struct.pack('HHHH', self.rows, self.cols, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

            self.pid = os.fork()

            if self.pid == 0:
                # Child process
                os.close(self.master_fd)
                os.setsid()

                # Set controlling terminal
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                if slave_fd > 2:
                    os.close(slave_fd)

                os.chdir(self.working_dir)

                env = os.environ.copy()
                env['TERM'] = 'xterm-256color'
                env['COLORTERM'] = 'truecolor'
                env['COLUMNS'] = str(self.cols)
                env['LINES'] = str(self.rows)

                shell = os.environ.get('SHELL', '/bin/bash')
                os.execvpe(shell, [shell, '--login', '-i'], env)
            else:
                # Parent
                os.close(slave_fd)

                # Non-blocking
                flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

                # Start reader thread
                self.reader = PTYReader(self.master_fd)
                self.reader.data_ready.connect(self._on_data)
                self.reader.finished.connect(self._on_finished)
                self.reader.start()

                # Send startup command
                if self.startup_command:
                    QTimer.singleShot(500, lambda: self._write(self.startup_command + '\n'))

        except Exception as e:
            logger.error(f"Failed to start PTY: {e}")

    def _on_data(self, data: bytes):
        """Process PTY output through pyte"""
        try:
            text = data.decode('utf-8', errors='replace')
            self.stream.feed(text)
            self._update_scrollbar()
            # Auto-scroll to bottom on new output (if already at bottom)
            if self.scroll_offset == 0:
                self.display.update()
            else:
                self.display.update()
        except Exception as e:
            logger.error(f"Error processing data: {e}")

    def _update_scrollbar(self):
        """Update scrollbar range based on history"""
        history_size = len(self.screen.history.top) if hasattr(self.screen, 'history') else 0
        self.scrollbar.blockSignals(True)
        self.scrollbar.setRange(0, history_size)
        self.scrollbar.setValue(history_size - self.scroll_offset)
        self.scrollbar.setPageStep(self.rows)
        self.scrollbar.blockSignals(False)

    def _on_scroll(self, value):
        """Handle scrollbar value change"""
        history_size = len(self.screen.history.top) if hasattr(self.screen, 'history') else 0
        self.scroll_offset = max(0, history_size - value)
        self.display.scroll_offset = self.scroll_offset
        self.display.update()

    def scroll_up(self, lines: int = 1):
        """Scroll up (show older content)"""
        history_size = len(self.screen.history.top) if hasattr(self.screen, 'history') else 0
        self.scroll_offset = min(history_size, self.scroll_offset + lines)
        self.display.scroll_offset = self.scroll_offset
        self._update_scrollbar()
        self.display.update()

    def scroll_down(self, lines: int = 1):
        """Scroll down (show newer content)"""
        self.scroll_offset = max(0, self.scroll_offset - lines)
        self.display.scroll_offset = self.scroll_offset
        self._update_scrollbar()
        self.display.update()

    def scroll_to_bottom(self):
        """Scroll to bottom (current output)"""
        self.scroll_offset = 0
        self.display.scroll_offset = 0
        self._update_scrollbar()
        self.display.update()

    def _write(self, text: str):
        """Write to PTY"""
        if self.master_fd:
            # Auto-scroll to bottom when typing
            if self.scroll_offset > 0:
                self.scroll_to_bottom()
            try:
                os.write(self.master_fd, text.encode('utf-8'))
            except OSError as e:
                logger.error(f"Write error: {e}")

    def _write_bytes(self, data: bytes):
        """Write raw bytes to PTY"""
        if self.master_fd:
            try:
                os.write(self.master_fd, data)
            except OSError as e:
                logger.error(f"Write error: {e}")

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input"""
        key = event.key()
        mods = event.modifiers()
        text = event.text()

        # Ctrl+Shift+C = Copy
        if (mods & Qt.KeyboardModifier.ControlModifier and
            mods & Qt.KeyboardModifier.ShiftModifier and
            key == Qt.Key.Key_C):
            self.display.copy_selection()
            return

        # Ctrl+Shift+V = Paste
        if (mods & Qt.KeyboardModifier.ControlModifier and
            mods & Qt.KeyboardModifier.ShiftModifier and
            key == Qt.Key.Key_V):
            from PyQt6.QtWidgets import QApplication
            text = QApplication.clipboard().text()
            if text:
                self._write(text)
            return

        # Special keys
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._write('\r')
        elif key == Qt.Key.Key_Backspace:
            self._write_bytes(b'\x7f')
        elif key == Qt.Key.Key_Tab:
            self._write('\t')
        elif key == Qt.Key.Key_Escape:
            self._write_bytes(b'\x1b')
        elif key == Qt.Key.Key_Up:
            self._write_bytes(b'\x1b[A')
        elif key == Qt.Key.Key_Down:
            self._write_bytes(b'\x1b[B')
        elif key == Qt.Key.Key_Right:
            if mods & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Right: move forward one word
                self._write_bytes(b'\x1bf')
            else:
                self._write_bytes(b'\x1b[C')
        elif key == Qt.Key.Key_Left:
            if mods & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Left: move back one word
                self._write_bytes(b'\x1bb')
            else:
                self._write_bytes(b'\x1b[D')
        elif key == Qt.Key.Key_Home:
            self._write_bytes(b'\x1b[H')
        elif key == Qt.Key.Key_End:
            self._write_bytes(b'\x1b[F')
        elif key == Qt.Key.Key_PageUp:
            if mods & Qt.KeyboardModifier.ShiftModifier:
                # Shift+PageUp: scroll history up
                self.scroll_up(self.rows - 1)
            else:
                self._write_bytes(b'\x1b[5~')
        elif key == Qt.Key.Key_PageDown:
            if mods & Qt.KeyboardModifier.ShiftModifier:
                # Shift+PageDown: scroll history down
                self.scroll_down(self.rows - 1)
            else:
                self._write_bytes(b'\x1b[6~')
        elif key == Qt.Key.Key_Insert:
            self._write_bytes(b'\x1b[2~')
        elif key == Qt.Key.Key_Delete:
            self._write_bytes(b'\x1b[3~')
        elif key >= Qt.Key.Key_F1 and key <= Qt.Key.Key_F12:
            fn = key - Qt.Key.Key_F1 + 1
            codes = {1: b'\x1bOP', 2: b'\x1bOQ', 3: b'\x1bOR', 4: b'\x1bOS',
                     5: b'\x1b[15~', 6: b'\x1b[17~', 7: b'\x1b[18~', 8: b'\x1b[19~',
                     9: b'\x1b[20~', 10: b'\x1b[21~', 11: b'\x1b[23~', 12: b'\x1b[24~'}
            self._write_bytes(codes.get(fn, b''))
        elif mods & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                self._write_bytes(b'\x03')
            elif key == Qt.Key.Key_D:
                self._write_bytes(b'\x04')
            elif key == Qt.Key.Key_Z:
                self._write_bytes(b'\x1a')
            elif key == Qt.Key.Key_L:
                self._write_bytes(b'\x0c')
            elif key == Qt.Key.Key_A:
                self._write_bytes(b'\x01')
            elif key == Qt.Key.Key_E:
                self._write_bytes(b'\x05')
            elif key == Qt.Key.Key_K:
                self._write_bytes(b'\x0b')
            elif key == Qt.Key.Key_U:
                self._write_bytes(b'\x15')
            elif key == Qt.Key.Key_W:
                self._write_bytes(b'\x17')
            elif text:
                self._write(text)
        elif text:
            self._write(text)

    def _on_finished(self):
        """PTY process finished"""
        if self.pid:
            try:
                _, status = os.waitpid(self.pid, os.WNOHANG)
                exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                self.finished.emit(exit_code)
            except:
                self.finished.emit(-1)

    def send_text(self, text: str):
        """Public method to send text"""
        self._write(text)

    def focus(self):
        """Focus terminal"""
        self.display.setFocus()

    def close_terminal(self):
        """Cleanup"""
        if self.reader:
            self.reader.stop()
            self.reader.wait(1000)

        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, 0)
            except:
                pass

        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass

    def resizeEvent(self, event):
        """Handle resize - update PTY size"""
        super().resizeEvent(event)
        if self.master_fd and self.display.char_width > 0:
            new_cols = max(40, self.width() // self.display.char_width)
            new_rows = max(10, self.height() // self.display.char_height)

            if new_cols != self.cols or new_rows != self.rows:
                self.cols = new_cols
                self.rows = new_rows

                # Resize pyte screen
                self.screen.resize(new_rows, new_cols)

                # Resize PTY
                try:
                    winsize = struct.pack('HHHH', new_rows, new_cols, 0, 0)
                    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
                except:
                    pass


# ============================================================================
# Terminal Tab (Uses PyteTerminal for embedded VT100 emulation)
# ============================================================================

class TerminalTab(QWidget):
    """
    Terminal tab mit eingebettetem VT100-Terminal.
    Nutzt pyte für vollständige Terminal-Emulation (vim, htop, Farben, etc.)
    """

    finished = pyqtSignal(int)

    def __init__(self, working_dir: str = None, startup_command: str = None, parent=None):
        super().__init__(parent)
        self.working_dir = working_dir or str(Path.home())
        self.startup_command = startup_command
        self.terminal = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup embedded terminal"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if HAS_PYTE:
            # Use pyte-based VT100 terminal (full features)
            self.terminal = PyteTerminal(
                working_dir=self.working_dir,
                startup_command=self.startup_command,
                parent=self
            )
            self.terminal.finished.connect(self.finished.emit)
            layout.addWidget(self.terminal, 1)
            logger.info("Using PyteTerminal (VT100 emulation)")
        else:
            # Fallback: Show error message
            error_label = QLabel("❌ Terminal nicht verfügbar\n\npyte nicht installiert.\nBitte installieren: pip install pyte")
            error_label.setStyleSheet("""
                QLabel {
                    color: #f85149;
                    font-size: 14px;
                    padding: 40px;
                    background: #0d1117;
                }
            """)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label, 1)
            logger.error("pyte not installed - terminal unavailable")

    def send_text(self, text: str):
        """Send text to terminal"""
        if self.terminal:
            self.terminal.send_text(text)

    def focus(self):
        """Focus terminal"""
        if self.terminal:
            self.terminal.focus()

    def close_terminal(self):
        """Close terminal"""
        if self.terminal:
            self.terminal.close_terminal()


# ============================================================================
# Terminal Widget (Tabbed container)
# ============================================================================

class TerminalWidget(QWidget):
    """
    Tabbed terminal widget with native terminal support.

    Features:
    - Multiple terminal tabs
    - Full color and ANSI support via Konsole/xterm
    - CLI agent integration
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("AILinux", "Client")
        self._setup_ui()
        self._apply_theme_colors()

    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #21262d;
                color: #c9d1d9;
                padding: 6px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #0d1117;
            }
            QTabBar::tab:hover {
                background: #30363d;
            }
        """)
        layout.addWidget(self.tabs, 1)

        # Add initial tab
        self.add_tab()

        # New tab button
        new_tab_btn = QToolButton()
        new_tab_btn.setText("+")
        new_tab_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: #58a6ff;
                font-size: 16px;
                font-weight: bold;
                border: none;
                padding: 4px 8px;
            }
            QToolButton:hover {
                background: #30363d;
                border-radius: 4px;
            }
        """)
        new_tab_btn.clicked.connect(lambda: self.add_tab())
        self.tabs.setCornerWidget(new_tab_btn, Qt.Corner.TopRightCorner)

    def add_tab(self, working_dir: str = None, title: str = None, startup_command: str = None) -> TerminalTab:
        """Add new terminal tab"""
        terminal = TerminalTab(working_dir, startup_command)
        terminal.finished.connect(lambda: self._on_terminal_finished(terminal))

        tab_title = title or f"Terminal {self.tabs.count() + 1}"
        idx = self.tabs.addTab(terminal, tab_title)
        self.tabs.setCurrentIndex(idx)

        terminal.focus()
        return terminal

    def _close_tab(self, index: int):
        """Close tab"""
        if self.tabs.count() <= 1:
            return

        terminal = self.tabs.widget(index)
        if isinstance(terminal, TerminalTab):
            terminal.close_terminal()

        self.tabs.removeTab(index)

    def _on_terminal_finished(self, terminal: TerminalTab):
        """Terminal process finished"""
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) == terminal:
                self.tabs.setTabText(i, f"{self.tabs.tabText(i)} ✗")
                break

    def focus_current(self):
        """Focus current terminal"""
        terminal = self.tabs.currentWidget()
        if isinstance(terminal, TerminalTab):
            terminal.focus()

    def send_to_current(self, text: str):
        """Send text to current terminal"""
        terminal = self.tabs.currentWidget()
        if isinstance(terminal, TerminalTab):
            terminal.send_text(text)

    def apply_settings(self):
        """Apply settings to all terminal tabs"""
        for i in range(self.tabs.count()):
            terminal = self.tabs.widget(i)
            if isinstance(terminal, TerminalTab) and terminal.terminal:
                if hasattr(terminal.terminal, 'display'):
                    terminal.terminal.display.apply_settings()
        # Apply theme colors
        self._apply_theme_colors()

    def _apply_theme_colors(self):
        """
        Apply theme colors from settings to terminal UI.
        Follows WCAG contrast guidelines for visibility.
        """
        # Read theme colors from settings
        primary = self.settings.value("theme_color_primary", "#3b82f6")
        secondary = self.settings.value("theme_color_secondary", "#6366f1")
        surface = self.settings.value("theme_color_surface", "#1a1a2e")
        text_color = self.settings.value("theme_color_text", "#e0e0e0")
        border_radius = self.settings.value("widget_border_radius", 10, type=int)
        transparency = self.settings.value("widget_transparency", 85, type=int) / 100.0

        # Helper: Convert hex to rgba
        def hex_to_rgba(hex_color, alpha):
            hex_color = hex_color.lstrip("#")
            if len(hex_color) >= 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return f"rgba({r}, {g}, {b}, {alpha:.2f})"
            return f"rgba(30, 30, 50, {alpha:.2f})"

        # Helper: Ensure minimum contrast (WCAG)
        def ensure_contrast(bg_hex, fg_hex):
            """Ensure text is readable - return adjusted text color if needed"""
            def luminance(hex_c):
                hex_c = hex_c.lstrip("#")
                if len(hex_c) < 6:
                    return 0.5
                r, g, b = int(hex_c[0:2], 16)/255, int(hex_c[2:4], 16)/255, int(hex_c[4:6], 16)/255
                r = r/12.92 if r <= 0.03928 else ((r+0.055)/1.055)**2.4
                g = g/12.92 if g <= 0.03928 else ((g+0.055)/1.055)**2.4
                b = b/12.92 if b <= 0.03928 else ((b+0.055)/1.055)**2.4
                return 0.2126*r + 0.7152*g + 0.0722*b

            bg_lum = luminance(bg_hex)
            fg_lum = luminance(fg_hex)
            lighter = max(bg_lum, fg_lum)
            darker = min(bg_lum, fg_lum)
            ratio = (lighter + 0.05) / (darker + 0.05)

            # WCAG AA requires 4.5:1 for normal text
            if ratio >= 4.5:
                return fg_hex
            return "#ffffff" if bg_lum < 0.5 else "#1a1a1a"

        # Ensure text contrast
        text_color = ensure_contrast(surface, text_color)

        surface_rgba = hex_to_rgba(surface, transparency)
        surface_lighter = hex_to_rgba(surface, min(1.0, transparency - 0.1))

        # Tab widget styling
        if hasattr(self, 'tabs'):
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: none;
                    background: {surface_rgba};
                    border-radius: {border_radius}px;
                }}
                QTabBar::tab {{
                    background: {surface_lighter};
                    color: {text_color};
                    padding: 8px 16px;
                    border-top-left-radius: {border_radius - 4}px;
                    border-top-right-radius: {border_radius - 4}px;
                    margin-right: 2px;
                    border: 1px solid transparent;
                    border-bottom: none;
                }}
                QTabBar::tab:selected {{
                    background: {surface_rgba};
                    color: white;
                    border-color: {primary};
                }}
                QTabBar::tab:hover {{
                    background: {primary};
                    color: white;
                }}
            """)
