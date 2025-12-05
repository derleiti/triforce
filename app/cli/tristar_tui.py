#!/usr/bin/env python3
"""
TriStar Terminal UI (TUI) - Interactive Control Center

Navigation:
    F1  - Prompting (Chat mit Agents)
    F2  - Agent-Ausgaben
    F3  - Live Logs
    ESC - Zurück zum Hauptmenü
    Ctrl+X - Beenden

Usage:
    tristar          # Startet TUI
    tristar --gui    # Startet TUI explizit
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Center
from textual.widgets import (
    Header, Footer, Static, Input, Button,
    Label, Select, RichLog, OptionList, Placeholder
)
from textual.widgets.option_list import Option
from textual.screen import Screen
from textual.reactive import reactive
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# API Configuration
API_BASE = "http://localhost:9100"
TIMEOUT = 120


class MainMenuScreen(Screen):
    """Hauptmenü mit F-Tasten Navigation"""

    BINDINGS = [
        Binding("f1", "goto_prompting", "F1 Prompting", show=True),
        Binding("f2", "goto_agents", "F2 Agents", show=True),
        Binding("f3", "goto_logs", "F3 Logs", show=True),
        Binding("f4", "goto_status", "F4 Status", show=True),
        Binding("ctrl+x", "quit_app", "^X Beenden", show=True),
    ]

    CSS = """
    #shortcut-bar {
        dock: bottom;
        height: 1;
        background: $primary-darken-3;
        color: $text;
        text-align: center;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Center(
                Static(Panel(
                    "[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]\n"
                    "[bold cyan]║[/bold cyan]     [bold white]TriStar Kontrollzentrum[/bold white]            [bold cyan]║[/bold cyan]\n"
                    "[bold cyan]║[/bold cyan]     [dim]Multi-LLM Chain Orchestration[/dim]       [bold cyan]║[/bold cyan]\n"
                    "[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]\n\n"
                    "[bold yellow]Navigation:[/bold yellow]\n\n"
                    "  [bold green]F1[/bold green]  💬 Prompting     - Chat mit CLI-Agents\n"
                    "  [bold green]F2[/bold green]  📤 Agent-Ausgaben - Letzte Responses\n"
                    "  [bold green]F3[/bold green]  📋 Live Logs      - System-Logs\n"
                    "  [bold green]F4[/bold green]  📊 Status         - System-Info\n\n"
                    "[bold cyan]Agents:[/bold cyan]\n"
                    "  🌟 Gemini  - Lead Agent\n"
                    "  🔶 Claude  - Code Expert\n"
                    "  🟢 Codex   - OpenAI\n"
                    "  🟣 OpenCode - Alternative",
                    title="🌟 TriStar v2.80",
                    border_style="cyan",
                    width=50,
                ), id="menu-panel"),
            ),
            id="menu-container"
        )
        yield Static(
            "[bold reverse] F1 [/bold reverse] Prompting  "
            "[bold reverse] F2 [/bold reverse] Agents  "
            "[bold reverse] F3 [/bold reverse] Logs  "
            "[bold reverse] F4 [/bold reverse] Status  "
            "[bold reverse] ^X [/bold reverse] Beenden",
            id="shortcut-bar"
        )
        yield Footer()

    def action_goto_prompting(self) -> None:
        self.app.push_screen(PromptingScreen())

    def action_goto_agents(self) -> None:
        self.app.push_screen(AgentOutputScreen())

    def action_goto_logs(self) -> None:
        self.app.push_screen(LogsScreen())

    def action_goto_status(self) -> None:
        self.app.push_screen(StatusScreen())

    def action_quit_app(self) -> None:
        self.app.exit()


class PromptingScreen(Screen):
    """F1 - Prompting Screen für Chat mit Agents"""

    BINDINGS = [
        Binding("escape", "go_back", "ESC Zurück", show=True),
        Binding("ctrl+x", "quit_app", "^X Beenden", show=True),
        Binding("f1", "select_gemini", "F1 Gemini", show=True),
        Binding("f2", "select_claude", "F2 Claude", show=True),
        Binding("f3", "select_codex", "F3 Codex", show=True),
        Binding("f4", "select_opencode", "F4 OpenCode", show=True),
        Binding("f5", "send_all", "F5 Alle", show=True),
    ]

    CSS = """
    #prompt-container {
        height: 100%;
        padding: 1;
    }

    #chat-log {
        height: 1fr;
        border: solid $primary;
        background: $surface;
        margin-bottom: 1;
    }

    #input-row {
        height: 3;
    }

    #prompt-input {
        width: 1fr;
    }

    #send-btn {
        width: 12;
    }

    #agent-bar {
        height: 3;
        background: $panel;
        padding: 0 1;
    }

    .agent-label {
        padding: 0 2;
    }

    .selected-agent {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    #shortcut-bar {
        dock: bottom;
        height: 1;
        background: $primary-darken-3;
        color: $text;
        padding: 0 1;
    }
    """

    selected_agent = reactive("gemini-mcp")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            RichLog(id="chat-log", highlight=True, markup=True, wrap=True),
            Horizontal(
                Static("Agent: ", classes="agent-label"),
                Static("🌟[F1]Gemini", id="lbl-gemini", classes="agent-label selected-agent"),
                Static("🔶[F2]Claude", id="lbl-claude", classes="agent-label"),
                Static("🟢[F3]Codex", id="lbl-codex", classes="agent-label"),
                Static("🟣[F4]OpenCode", id="lbl-opencode", classes="agent-label"),
                Static("[F5]Alle", classes="agent-label"),
                id="agent-bar"
            ),
            Horizontal(
                Input(placeholder="Prompt eingeben... (Enter zum Senden)", id="prompt-input"),
                Button("Senden", id="send-btn", variant="primary"),
                id="input-row"
            ),
            id="prompt-container"
        )
        yield Static(
            "[bold reverse] F1 [/bold reverse] 🌟Gemini  "
            "[bold reverse] F2 [/bold reverse] 🔶Claude  "
            "[bold reverse] F3 [/bold reverse] 🟢Codex  "
            "[bold reverse] F4 [/bold reverse] 🟣OpenCode  "
            "[bold reverse] F5 [/bold reverse] Alle  "
            "[bold reverse] ESC [/bold reverse] Zurück  "
            "[bold reverse] ^X [/bold reverse] Beenden",
            id="shortcut-bar"
        )
        yield Footer()

    def on_mount(self) -> None:
        chat = self.query_one("#chat-log", RichLog)
        chat.write(Panel(
            "[bold]Prompting Modus[/bold]\n\n"
            "Wähle Agent mit F1-F4, dann Enter zum Senden.\n"
            "F5 sendet an alle Agents gleichzeitig.\n\n"
            "[dim]ESC = Zurück zum Menü[/dim]",
            title="💬 Prompting",
            border_style="green"
        ))
        self.query_one("#prompt-input").focus()

    def _update_agent_labels(self) -> None:
        """Update agent label highlighting"""
        agents = {
            "gemini-mcp": "lbl-gemini",
            "claude-mcp": "lbl-claude",
            "codex-mcp": "lbl-codex",
            "opencode-mcp": "lbl-opencode"
        }
        for agent_id, label_id in agents.items():
            label = self.query_one(f"#{label_id}", Static)
            if agent_id == self.selected_agent:
                label.add_class("selected-agent")
            else:
                label.remove_class("selected-agent")

    def action_select_gemini(self) -> None:
        self.selected_agent = "gemini-mcp"
        self._update_agent_labels()

    def action_select_claude(self) -> None:
        self.selected_agent = "claude-mcp"
        self._update_agent_labels()

    def action_select_codex(self) -> None:
        self.selected_agent = "codex-mcp"
        self._update_agent_labels()

    def action_select_opencode(self) -> None:
        self.selected_agent = "opencode-mcp"
        self._update_agent_labels()

    @on(Input.Submitted, "#prompt-input")
    @on(Button.Pressed, "#send-btn")
    async def send_prompt(self) -> None:
        """Send prompt to selected agent"""
        input_widget = self.query_one("#prompt-input", Input)
        prompt = input_widget.value.strip()
        if not prompt:
            return

        chat = self.query_one("#chat-log", RichLog)
        agent_id = self.selected_agent
        agent_name = agent_id.replace("-mcp", "").title()

        chat.write(f"\n[bold cyan]Du → {agent_name}:[/bold cyan] {prompt}")
        input_widget.value = ""

        chat.write(f"[dim]⏳ {agent_name} denkt nach...[/dim]")

        # Call API
        response = await self._call_agent(agent_id, prompt)

        icon = {"gemini": "🌟", "claude": "🔶", "codex": "🟢", "opencode": "🟣"}.get(
            agent_id.replace("-mcp", ""), "⚪"
        )
        chat.write(f"\n{icon} [bold green]{agent_name}:[/bold green]")

        for line in response.split("\n")[:30]:
            chat.write(f"  {line}")

        if response.count("\n") > 30:
            chat.write(f"  [dim]... ({response.count(chr(10)) - 30} weitere Zeilen)[/dim]")

        # Store in app for F2 screen
        self.app.last_responses[agent_id] = {
            "prompt": prompt,
            "response": response,
            "time": datetime.now().strftime("%H:%M:%S")
        }

    async def action_send_all(self) -> None:
        """Send to all agents"""
        input_widget = self.query_one("#prompt-input", Input)
        prompt = input_widget.value.strip()
        if not prompt:
            return

        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"\n[bold cyan]Du → ALLE:[/bold cyan] {prompt}")
        input_widget.value = ""

        for agent_id in ["gemini-mcp", "claude-mcp", "codex-mcp"]:
            agent_name = agent_id.replace("-mcp", "").title()
            icon = {"gemini": "🌟", "claude": "🔶", "codex": "🟢"}.get(
                agent_id.replace("-mcp", ""), "⚪"
            )

            chat.write(f"[dim]⏳ {agent_name}...[/dim]")
            response = await self._call_agent(agent_id, prompt)

            chat.write(f"\n{icon} [bold green]{agent_name}:[/bold green]")
            for line in response.split("\n")[:15]:
                chat.write(f"  {line}")

            self.app.last_responses[agent_id] = {
                "prompt": prompt,
                "response": response,
                "time": datetime.now().strftime("%H:%M:%S")
            }

    async def _call_agent(self, agent_id: str, prompt: str) -> str:
        """Call agent API"""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{API_BASE}/v1/tristar/cli-agents/{agent_id}/call",
                    json={"message": prompt, "timeout": 120}
                )
                data = response.json()
                return data.get("response", data.get("error", "Keine Antwort"))
        except Exception as e:
            return f"Fehler: {e}"

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()


class AgentOutputScreen(Screen):
    """F2 - Agent-Ausgaben Screen"""

    BINDINGS = [
        Binding("escape", "go_back", "ESC Zurück", show=True),
        Binding("ctrl+x", "quit_app", "^X Beenden", show=True),
        Binding("r", "refresh", "R Refresh", show=True),
    ]

    CSS = """
    #output-container {
        height: 100%;
        padding: 1;
    }

    #output-log {
        height: 1fr;
        border: solid $primary;
        background: $surface;
    }

    #shortcut-bar {
        dock: bottom;
        height: 1;
        background: $primary-darken-3;
        color: $text;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            RichLog(id="output-log", highlight=True, markup=True, wrap=True),
            id="output-container"
        )
        yield Static(
            "[bold reverse] R [/bold reverse] Refresh  "
            "[bold reverse] ESC [/bold reverse] Zurück  "
            "[bold reverse] ^X [/bold reverse] Beenden",
            id="shortcut-bar"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.load_outputs()

    def load_outputs(self) -> None:
        log = self.query_one("#output-log", RichLog)
        log.clear()

        log.write(Panel(
            "[bold]Agent-Ausgaben[/bold]\n\n"
            "Zeigt die letzten Responses aller Agents.\n"
            "[dim]R = Refresh, ESC = Zurück[/dim]",
            title="📤 Agent-Ausgaben",
            border_style="yellow"
        ))

        if not self.app.last_responses:
            log.write("\n[dim]Noch keine Agent-Responses. Nutze F1 Prompting.[/dim]")
            return

        for agent_id, data in self.app.last_responses.items():
            agent_name = agent_id.replace("-mcp", "").title()
            icon = {"gemini": "🌟", "claude": "🔶", "codex": "🟢", "opencode": "🟣"}.get(
                agent_id.replace("-mcp", ""), "⚪"
            )

            log.write(f"\n{icon} [bold cyan]{agent_name}[/bold cyan] [{data['time']}]")
            log.write(f"[dim]Prompt:[/dim] {data['prompt'][:80]}...")
            log.write("[dim]Response:[/dim]")

            for line in data["response"].split("\n")[:20]:
                log.write(f"  {line}")

            log.write("─" * 60)

    def action_refresh(self) -> None:
        self.load_outputs()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()


class LogsScreen(Screen):
    """F3 - Live Logs Screen"""

    BINDINGS = [
        Binding("escape", "go_back", "ESC Zurück", show=True),
        Binding("ctrl+x", "quit_app", "^X Beenden", show=True),
        Binding("c", "clear_logs", "C Clear", show=True),
        Binding("1", "filter_all", "1 Alle", show=True),
        Binding("2", "filter_info", "2 Info", show=True),
        Binding("3", "filter_error", "3 Error", show=True),
        Binding("4", "filter_llm", "4 LLM", show=True),
    ]

    CSS = """
    #logs-container {
        height: 100%;
        padding: 1;
    }

    #logs-log {
        height: 1fr;
        border: solid $primary;
        background: $surface;
    }

    #filter-bar {
        height: 3;
        dock: top;
        background: $panel;
        padding: 0 1;
    }

    #shortcut-bar {
        dock: bottom;
        height: 1;
        background: $primary-darken-3;
        color: $text;
        padding: 0 1;
    }
    """

    log_filter = reactive("all")
    _poll_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Static("Filter: ", classes="agent-label"),
                Static("[1]Alle", id="flt-all", classes="agent-label selected-agent"),
                Static("[2]Info", id="flt-info", classes="agent-label"),
                Static("[3]Error", id="flt-error", classes="agent-label"),
                Static("[4]LLM", id="flt-llm", classes="agent-label"),
                Static("  [C]lear", classes="agent-label"),
                id="filter-bar"
            ),
            RichLog(id="logs-log", highlight=True, markup=True, max_lines=500),
            id="logs-container"
        )
        yield Static(
            "[bold reverse] 1 [/bold reverse] Alle  "
            "[bold reverse] 2 [/bold reverse] Info  "
            "[bold reverse] 3 [/bold reverse] Error  "
            "[bold reverse] 4 [/bold reverse] LLM  "
            "[bold reverse] C [/bold reverse] Clear  "
            "[bold reverse] ESC [/bold reverse] Zurück  "
            "[bold reverse] ^X [/bold reverse] Beenden",
            id="shortcut-bar"
        )
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#logs-log", RichLog)
        log.write("[bold]Live Logs[/bold] - Polling alle 2 Sekunden...")
        self._poll_task = asyncio.create_task(self._poll_logs())

    def on_unmount(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()

    async def _poll_logs(self) -> None:
        log_widget = self.query_one("#logs-log", RichLog)
        seen = set()

        while True:
            try:
                url = f"{API_BASE}/v1/triforce/logs/recent?limit=30"
                if self.log_filter != "all":
                    url += f"&category={self.log_filter}"

                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url)
                    data = response.json()

                for entry in reversed(data.get("entries", [])):
                    ts = entry.get("timestamp", "")
                    if ts in seen:
                        continue
                    seen.add(ts)

                    time_str = ts.split("T")[1].split(".")[0] if "T" in ts else ts[:8]
                    cat = entry.get("category", "info")
                    msg = entry.get("message", "")[:100]

                    cat_color = {
                        "error": "red", "warning": "yellow", "info": "blue",
                        "debug": "dim", "llm_call": "magenta", "api_request": "cyan"
                    }.get(cat, "white")

                    log_widget.write(
                        f"[dim]{time_str}[/dim] [{cat_color}]{cat[:5].upper():5}[/{cat_color}] {msg}"
                    )

                    if len(seen) > 500:
                        seen = set(list(seen)[-250:])
            except Exception:
                pass

            await asyncio.sleep(2)

    def _update_filter_labels(self) -> None:
        filters = {"all": "flt-all", "info": "flt-info", "error": "flt-error", "llm_call": "flt-llm"}
        for flt, label_id in filters.items():
            label = self.query_one(f"#{label_id}", Static)
            if flt == self.log_filter:
                label.add_class("selected-agent")
            else:
                label.remove_class("selected-agent")

    def action_filter_all(self) -> None:
        self.log_filter = "all"
        self._update_filter_labels()
        self.query_one("#logs-log", RichLog).clear()

    def action_filter_info(self) -> None:
        self.log_filter = "info"
        self._update_filter_labels()
        self.query_one("#logs-log", RichLog).clear()

    def action_filter_error(self) -> None:
        self.log_filter = "error"
        self._update_filter_labels()
        self.query_one("#logs-log", RichLog).clear()

    def action_filter_llm(self) -> None:
        self.log_filter = "llm_call"
        self._update_filter_labels()
        self.query_one("#logs-log", RichLog).clear()

    def action_clear_logs(self) -> None:
        self.query_one("#logs-log", RichLog).clear()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()


class StatusScreen(Screen):
    """F4 - System Status Screen"""

    BINDINGS = [
        Binding("escape", "go_back", "ESC Zurück", show=True),
        Binding("ctrl+x", "quit_app", "^X Beenden", show=True),
        Binding("r", "refresh", "R Refresh", show=True),
    ]

    CSS = """
    #status-container {
        height: 100%;
        padding: 1;
    }

    #status-log {
        height: 1fr;
        border: solid $primary;
        background: $surface;
    }

    #shortcut-bar {
        dock: bottom;
        height: 1;
        background: $primary-darken-3;
        color: $text;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            RichLog(id="status-log", highlight=True, markup=True),
            id="status-container"
        )
        yield Static(
            "[bold reverse] R [/bold reverse] Refresh  "
            "[bold reverse] ESC [/bold reverse] Zurück  "
            "[bold reverse] ^X [/bold reverse] Beenden",
            id="shortcut-bar"
        )
        yield Footer()

    def on_mount(self) -> None:
        asyncio.create_task(self.load_status())

    async def load_status(self) -> None:
        log = self.query_one("#status-log", RichLog)
        log.clear()

        log.write(Panel("[bold]System Status[/bold]", title="📊 Status", border_style="blue"))

        # Health
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                health = await client.get(f"{API_BASE}/health")
                if health.status_code == 200:
                    log.write("[green]✓ Backend: Online[/green]")
                else:
                    log.write("[red]✗ Backend: Offline[/red]")
        except Exception:
            log.write("[red]✗ Backend: Nicht erreichbar[/red]")

        # Agents
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                agents = await client.get(f"{API_BASE}/v1/tristar/cli-agents")
                data = agents.json()

                log.write(f"\n[bold cyan]CLI Agents:[/bold cyan]")
                for agent in data.get("cli_agents", []):
                    icon = {"gemini": "🌟", "claude": "🔶", "codex": "🟢", "opencode": "🟣"}.get(
                        agent["agent_type"], "⚪"
                    )
                    status_color = {"running": "green", "stopped": "dim", "error": "red"}.get(
                        agent["status"], "white"
                    )
                    log.write(f"  {icon} {agent['agent_type'].title():10} [{status_color}]{agent['status']}[/{status_color}]")
        except Exception as e:
            log.write(f"[red]Fehler beim Laden der Agents: {e}[/red]")

        # Stats
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Logs
                logs_res = await client.get(f"{API_BASE}/v1/triforce/logs/stats")
                logs_data = logs_res.json()

                # Memory
                mem_res = await client.get(f"{API_BASE}/v1/tristar/memory/search?limit=1")
                mem_data = mem_res.json()

                # Models
                models_res = await client.get(f"{API_BASE}/v1/tristar/models")
                models_data = models_res.json()

                log.write(f"\n[bold cyan]Statistiken:[/bold cyan]")
                log.write(f"  Logs:    {logs_data.get('total_logged', 0)}")
                log.write(f"  Memory:  {mem_data.get('total', 0)} Einträge")
                log.write(f"  Models:  {len(models_data.get('models', []))} registriert")
        except Exception:
            pass

        log.write(f"\n[dim]R = Refresh, ESC = Zurück[/dim]")

    def action_refresh(self) -> None:
        asyncio.create_task(self.load_status())

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()


class TriStarTUI(App):
    """TriStar Terminal User Interface - Main App"""

    TITLE = "TriStar Kontrollzentrum"
    SUB_TITLE = "v2.80"

    CSS = """
    Screen {
        background: $surface;
    }

    #menu-container {
        height: 100%;
        align: center middle;
    }

    #menu-panel {
        width: auto;
        height: auto;
    }

    .selected-agent {
        background: $primary;
        text-style: bold;
    }

    .agent-label {
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+x", "quit", "Beenden"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_responses: Dict[str, Dict[str, Any]] = {}

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())


def run_tui():
    """Run the TUI application"""
    app = TriStarTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
