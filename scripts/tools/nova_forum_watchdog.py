#!/usr/bin/env python3
"""
Nova forum assistant watchdog.

Checks the minimum runtime path needed by the Nova Flarum assistant:
- local TriForce backend health
- public Flarum API read path
- optional local/internal Flarum API read path
- systemd service liveness for nova-flarum-bot.service

No write calls are performed. No secrets are printed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class CheckResult:
    name: str
    ok: bool
    latency_ms: float | None = None
    detail: str = ""


def http_json(name: str, url: str, timeout: float) -> CheckResult:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(512_000).decode("utf-8", "replace")
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            if resp.status >= 400:
                return CheckResult(name, False, latency_ms, f"HTTP {resp.status}")
            try:
                data: Any = json.loads(body)
            except json.JSONDecodeError:
                return CheckResult(name, False, latency_ms, "response is not JSON")
            if isinstance(data, dict) and data.get("errors"):
                return CheckResult(name, False, latency_ms, "JSON API returned errors")
            return CheckResult(name, True, latency_ms, "ok")
    except urllib.error.HTTPError as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return CheckResult(name, False, latency_ms, f"HTTP {exc.code}")
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return CheckResult(name, False, latency_ms, f"{type(exc).__name__}: {exc}")


def systemd_is_active(service: str, timeout: float) -> CheckResult:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", service],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        state = proc.stdout.strip() or proc.stderr.strip() or f"exit={proc.returncode}"
        return CheckResult(f"systemd:{service}", proc.returncode == 0 and state == "active", latency_ms, state)
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return CheckResult(f"systemd:{service}", False, latency_ms, f"{type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only watchdog for the Nova forum assistant path.")
    parser.add_argument("--backend-health", default="http://127.0.0.1:9000/health")
    parser.add_argument("--forum-public", default="https://forum.ailinux.me/api/discussions?sort=-lastPostedAt&page%5Blimit%5D=1")
    parser.add_argument("--forum-internal", default="http://172.19.0.4:8888/api/discussions?sort=-lastPostedAt&page%5Blimit%5D=1")
    parser.add_argument("--service", default="nova-flarum-bot.service")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--skip-internal", action="store_true", help="Skip Docker/internal Flarum API probe.")
    args = parser.parse_args()

    checks = [
        http_json("backend_health", args.backend_health, args.timeout),
        http_json("forum_public_api", args.forum_public, args.timeout),
        systemd_is_active(args.service, args.timeout),
    ]
    if not args.skip_internal:
        checks.insert(2, http_json("forum_internal_api", args.forum_internal, args.timeout))

    ok = all(c.ok for c in checks)
    print(json.dumps({"ok": ok, "checks": [asdict(c) for c in checks]}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
