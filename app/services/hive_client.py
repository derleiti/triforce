"""
app/services/hive_client.py
============================
Sicherer Client fuer Hive/Hyve.

Designprinzipien:
  - Keine API-Keys oder Authorization-Header werden geloggt.
  - status() liefert ausschliesslich Bool/Strings ohne Secret-Material.
  - Beide Schreibweisen (HIVE_*, HYVE_*) werden ueber app.config aufgeloest.
  - request() ist absichtlich konservativ: nur bei gesetzter base_url.

Public API:
    HiveClient()
    HiveClient.configured -> bool
    HiveClient.status()    -> dict (sicher, ohne Secrets)
    HiveClient.request(method, path, json=None, timeout=None) -> dict
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger("ailinux.hive")


def _safe_error(exc: BaseException) -> str:
    """Fehler-String ohne Secrets/Header."""
    msg = str(exc).strip() or exc.__class__.__name__
    # Defensive Filter: Authorization-Header oder Bearer-Tokens niemals weiterreichen
    if "authorization" in msg.lower() or "bearer" in msg.lower():
        return f"{exc.__class__.__name__} (sanitized)"
    # Lange opake Strings sind verdaechtig
    if len(msg) > 280:
        msg = msg[:280] + "..."
    return msg


class HiveClient:
    """Lese/Schreib-Client fuer den Hive/Hyve-Endpunkt."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def configured(self) -> bool:
        """True, wenn ein API-Key (HIVE oder HYVE) gesetzt ist."""
        return bool(self._settings.effective_hive_key)

    @property
    def base_url(self) -> Optional[str]:
        """Effektive Base-URL (HIVE_BASE_URL > HYVE_BASE_URL)."""
        url = self._settings.effective_hive_base_url
        if not url:
            return None
        return url.rstrip("/")

    @property
    def key_source(self) -> Optional[str]:
        """Name der Env-Variable, aus der der Key stammt (HIVE_API_KEY/HYVE_API_KEY)."""
        return self._settings.effective_hive_key_source

    @property
    def timeout_seconds(self) -> float:
        return max(1.0, float(self._settings.hive_timeout_ms) / 1000.0)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    async def reachability_probe(self) -> Optional[bool]:
        """
        Optionaler GET / oder HEAD auf base_url, um Erreichbarkeit zu pruefen.
        Schickt KEINEN Authorization-Header, weil die Probe oeffentlich sein soll.
        Returns:
            True  -> HTTP-Antwort < 500
            False -> Connection/Timeout/HTTP 5xx
            None  -> base_url nicht gesetzt (nicht pruefbar)
        """
        url = self.base_url
        if not url:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(url)
                return resp.status_code < 500
        except Exception as exc:  # noqa: BLE001
            logger.debug("Hive reachability probe failed: %s", _safe_error(exc))
            return False

    def status(self) -> Dict[str, Any]:
        """
        Rein synchroner Status ohne Reachability-Check.
        Liefert nur sichere Daten - niemals den Key oder Praefixe davon.
        """
        return {
            "configured": self.configured,
            "base_url_configured": bool(self.base_url),
            "key_source": self.key_source,
            "reachable": None,  # Nur ueber async-Probe ermittelt
            "error": None,
        }

    async def status_async(self, *, probe: bool = False) -> Dict[str, Any]:
        """Async Status. Mit probe=True wird die Erreichbarkeit getestet."""
        result = self.status()
        if probe:
            try:
                result["reachable"] = await self.reachability_probe()
            except Exception as exc:  # noqa: BLE001
                result["reachable"] = False
                result["error"] = _safe_error(exc)
        return result

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------
    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Sendet einen Request gegen die Hive-API.

        Wirft ValueError, wenn nichts konfiguriert ist. Authorization-Header
        wird ausschliesslich aus self._settings.effective_hive_key gesetzt
        und nirgendwo geloggt.

        Returns:
            {
              "ok": bool,
              "status": int,
              "data": <decoded body | str | None>,
              "error": <safe string | None>
            }
        """
        if not self.configured:
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "error": "hive_not_configured",
            }
        if not self.base_url:
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "error": "hive_base_url_missing",
            }
        if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "error": "unsupported_method",
            }

        # Pfad sanitisieren - keine arbitrary URLs zulassen
        if path.startswith("http://") or path.startswith("https://"):
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "error": "absolute_url_not_allowed",
            }
        if not path.startswith("/"):
            path = "/" + path

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._settings.effective_hive_key}",
            "Accept": "application/json",
            "User-Agent": "TriForce-HiveClient/1.0",
        }
        eff_timeout = float(timeout) if timeout else self.timeout_seconds

        try:
            async with httpx.AsyncClient(timeout=eff_timeout) as client:
                resp = await client.request(
                    method.upper(),
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )
                # NIE Header oder Body voller Ausgabe, nur das Noetigste
                ctype = resp.headers.get("content-type", "")
                if "application/json" in ctype:
                    try:
                        data: Any = resp.json()
                    except Exception:  # noqa: BLE001
                        data = None
                else:
                    text = resp.text
                    data = text if len(text) < 8192 else text[:8192] + "...[truncated]"
                return {
                    "ok": resp.is_success,
                    "status": resp.status_code,
                    "data": data,
                    "error": None if resp.is_success else f"http_{resp.status_code}",
                }
        except httpx.TimeoutException as exc:
            return {"ok": False, "status": 0, "data": None, "error": "timeout"}
        except httpx.RequestError as exc:
            return {"ok": False, "status": 0, "data": None, "error": _safe_error(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "status": 0, "data": None, "error": _safe_error(exc)}


# Singleton-Instanz
_hive_client: Optional[HiveClient] = None


def get_hive_client() -> HiveClient:
    global _hive_client
    if _hive_client is None:
        _hive_client = HiveClient()
    return _hive_client


__all__ = ["HiveClient", "get_hive_client"]
