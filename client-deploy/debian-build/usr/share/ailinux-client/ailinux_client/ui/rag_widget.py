"""
AILinux RAG Widget
==================

Small project-aware RAG panel for indexing and querying local project folders
through the TriForce /v1/rag API.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QSpinBox,
)

from ..core.api_client import APIClient


class RagWorker(QThread):
    """Run blocking RAG API calls outside the UI thread."""

    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, api_client: APIClient, action: str, payload: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.action = action
        self.payload = payload

    def run(self):
        try:
            if self.action == "health":
                result = self.api_client.rag_health()
            elif self.action == "index":
                result = self.api_client.rag_index(**self.payload)
            elif self.action == "query":
                result = self.api_client.rag_query(**self.payload)
            else:
                raise ValueError(f"Unknown RAG action: {self.action}")
            self.finished_ok.emit(result or {})
        except Exception as exc:  # noqa: BLE001 - UI boundary should surface all failures
            self.failed.emit(str(exc))


class RagWidget(QWidget):
    """Minimal RAG UI: project path, index button, query field, result list."""

    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._worker: Optional[RagWorker] = None
        self._last_hits: List[Dict[str, Any]] = []
        self._setup_ui()
        self.refresh_health()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        title = QLabel("Project RAG")
        title.setStyleSheet("font-weight: bold; color: #e0e0e0; font-size: 13px;")
        root.addWidget(title)

        self.status_label = QLabel("Status: checking…")
        self.status_label.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        root.addWidget(self.status_label)

        project_row = QHBoxLayout()
        self.project_input = QLineEdit("triforce")
        self.project_input.setPlaceholderText("Project name")
        project_row.addWidget(self.project_input, 1)

        self.top_k = QSpinBox()
        self.top_k.setRange(1, 20)
        self.top_k.setValue(8)
        self.top_k.setToolTip("Number of query results")
        project_row.addWidget(self.top_k)
        root.addLayout(project_row)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit(str(Path.home()))
        self.path_input.setPlaceholderText("Project folder path")
        path_row.addWidget(self.path_input, 1)

        browse_btn = QPushButton("…")
        browse_btn.setToolTip("Choose folder")
        browse_btn.clicked.connect(self.choose_folder)
        path_row.addWidget(browse_btn)
        root.addLayout(path_row)

        action_row = QHBoxLayout()
        self.index_btn = QPushButton("Index")
        self.index_btn.clicked.connect(self.index_project)
        action_row.addWidget(self.index_btn)

        self.health_btn = QPushButton("Health")
        self.health_btn.clicked.connect(self.refresh_health)
        action_row.addWidget(self.health_btn)
        root.addLayout(action_row)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask this project…")
        self.query_input.returnPressed.connect(self.query_project)
        root.addWidget(self.query_input)

        self.query_btn = QPushButton("Query")
        self.query_btn.clicked.connect(self.query_project)
        root.addWidget(self.query_btn)

        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self._open_result)
        root.addWidget(self.results, 1)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Selected result snippet…")
        self.preview.setMinimumHeight(120)
        root.addWidget(self.preview)

        self.results.currentRowChanged.connect(self._show_result_preview)

        self.setStyleSheet(
            """
            QWidget { color: #e0e0e0; }
            QLineEdit, QTextEdit, QListWidget {
                background: rgba(15, 15, 25, 0.88);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton {
                background: rgba(59, 130, 246, 0.35);
                color: #ffffff;
                border: 1px solid rgba(59, 130, 246, 0.55);
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover { background: rgba(59, 130, 246, 0.55); }
            QPushButton:disabled { background: rgba(80, 80, 80, 0.35); color: #888; }
            """
        )

    def set_project_path(self, path: str):
        """Update path from FileBrowser directory changes."""
        if path and os.path.isdir(path):
            self.path_input.setText(path)
            name = Path(path).name.strip() or "project"
            if not self.project_input.text().strip() or self.project_input.text().strip() == "triforce":
                self.project_input.setText(name)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose project folder", self.path_input.text())
        if folder:
            self.set_project_path(folder)

    def refresh_health(self):
        self._run_worker("health", {})

    def index_project(self):
        project = self.project_input.text().strip() or "project"
        path = self.path_input.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, "RAG", "Please choose a valid project folder.")
            return

        payload = {
            "project": project,
            "path": path,
            "exclude_dirs": [
                ".git",
                ".venv",
                "node_modules",
                "__pycache__",
                "data",
                "docker",
                "logs",
                "backup",
                "backups",
                "dist",
                "build",
            ],
        }
        self.status_label.setText("Status: indexing…")
        self._run_worker("index", payload)

    def query_project(self):
        project = self.project_input.text().strip() or "project"
        query = self.query_input.text().strip()
        if not query:
            return
        self.status_label.setText("Status: querying…")
        self._run_worker("query", {"project": project, "query": query, "top_k": self.top_k.value()})

    def _run_worker(self, action: str, payload: Dict[str, Any]):
        self._set_busy(True)
        self._worker = RagWorker(self.api_client, action, payload, self)
        self._worker.finished_ok.connect(lambda result, a=action: self._handle_success(a, result))
        self._worker.failed.connect(self._handle_error)
        self._worker.finished.connect(lambda: self._set_busy(False))
        self._worker.start()

    def _set_busy(self, busy: bool):
        self.index_btn.setDisabled(busy)
        self.query_btn.setDisabled(busy)
        self.health_btn.setDisabled(busy)

    def _handle_success(self, action: str, result: Dict[str, Any]):
        if action == "health":
            projects = result.get("projects", [])
            self.status_label.setText(f"Status: {result.get('backend', 'RAG')} | projects: {len(projects)}")
            return

        if action == "index":
            chunks = result.get("chunks", 0)
            files = result.get("files_seen", 0)
            self.status_label.setText(f"Indexed {files} files / {chunks} chunks")
            return

        if action == "query":
            hits = result.get("hits", [])
            self._last_hits = hits
            self.results.clear()
            self.preview.clear()
            for hit in hits:
                label = f"{hit.get('score', 0):.2f}  {hit.get('rel_path') or hit.get('path')}"
                item = QListWidgetItem(label)
                item.setToolTip(hit.get("path", ""))
                self.results.addItem(item)
            self.status_label.setText(f"Query returned {len(hits)} hits")
            if hits:
                self.results.setCurrentRow(0)

    def _handle_error(self, message: str):
        self.status_label.setText("Status: error")
        QMessageBox.warning(self, "RAG Error", message)

    def _show_result_preview(self, row: int):
        if row < 0 or row >= len(self._last_hits):
            self.preview.clear()
            return
        hit = self._last_hits[row]
        path = hit.get("rel_path") or hit.get("path", "")
        score = hit.get("score", 0)
        terms = ", ".join(hit.get("matched_terms", []))
        snippet = hit.get("snippet", "")
        self.preview.setPlainText(f"{path}\nScore: {score}\nTerms: {terms}\n\n{snippet}")

    def _open_result(self, item: QListWidgetItem):
        row = self.results.row(item)
        if row < 0 or row >= len(self._last_hits):
            return
        path = self._last_hits[row].get("path")
        if path and os.path.exists(path):
            QFileDialog.getOpenFileName(self, "Result file", str(Path(path).parent))
