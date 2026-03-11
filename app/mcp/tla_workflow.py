"""
TLA+ Workflow Engine v1.0
==========================
Integriert formale Verifikation in den KI-Workflow-Zyklus.

Konzept:
  Plan (TLA+ Spec) → Verify → Execute (MCP) → Monitor → Repair

MCP Tools:
  tla_plan     - Neue Aufgabe formal spezifizieren (Phasen, Invarianten)
  tla_verify   - Spec auf Konsistenz prüfen (TLC-ähnlich, vereinfacht)
  tla_status   - Aktiven Workflow-Status abfragen
  tla_advance  - Phase manuell/automatisch vorwärts schieben
  tla_abort    - Workflow abbrechen + Rollback-Hinweis

MCP-Command System (für Modelle im System-Prompt):
  Modelle können via !mcp <tool> <json> Commands direkt im Chat auslösen.
  Der MCP-Server parst dies, führt aus, gibt Output zurück.
"""

import json
import os
import tempfile
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("ailinux.mcp.tla")

STORE_FILE = Path("/var/lib/triforce/tla_workflows.json")

# ── Workflow-State-Machine ────────────────────────────────────────────────────
# Phasen: PLAN → VERIFY → EXECUTE → MONITOR → DONE / FAILED
VALID_TRANSITIONS = {
    "PLAN":    ["VERIFY", "ABORT"],
    "VERIFY":  ["EXECUTE", "PLAN", "ABORT"],   # Zurück wenn Spec fehlerhaft
    "EXECUTE": ["MONITOR", "ABORT"],
    "MONITOR": ["DONE", "EXECUTE", "ABORT"],   # Retry → zurück zu EXECUTE
    "DONE":    [],
    "ABORT":   [],
    "FAILED":  [],
}

# ── TLA+ Vereinfachte Verifikation ────────────────────────────────────────────

def _verify_spec(spec: Dict) -> List[str]:
    """
    Prüft TLA+ Spec auf strukturelle Konsistenz.
    Gibt Liste von Fehlern zurück (leer = OK).
    
    Echte TLC-Verifikation wäre: subprocess TLC JAR ausführen.
    Hier: strukturelle + semantische Plausibilitätsprüfung.
    """
    errors = []
    
    # Pflichtfelder
    for field in ["title", "phases", "invariants"]:
        if field not in spec:
            errors.append(f"Fehlendes Pflichtfeld: {field}")
    
    phases = spec.get("phases", [])
    if not phases:
        errors.append("Mindestens eine Phase erforderlich")
    
    # Phasen-Validierung
    for i, phase in enumerate(phases):
        if "name" not in phase:
            errors.append(f"Phase {i}: fehlt 'name'")
        if "actions" not in phase:
            errors.append(f"Phase {i} ({phase.get('name','?')}): fehlt 'actions'")
        if "postcondition" not in phase:
            errors.append(f"Phase {i} ({phase.get('name','?')}): fehlt 'postcondition'")
    
    # Invarianten
    invariants = spec.get("invariants", [])
    if not invariants:
        errors.append("Mindestens eine Invariante erforderlich (Safety-Property)")
    
    # Deadlock-Check: letzte Phase muss enden
    if phases:
        last = phases[-1]
        if last.get("name") not in ("DONE", "COMPLETE", "FINISH") and \
           "terminal" not in last:
            errors.append(f"Letzte Phase '{last.get('name')}' nicht als terminal markiert")
    
    return errors


# ── Storage ───────────────────────────────────────────────────────────────────

def _load() -> Dict:
    try:
        STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STORE_FILE.exists():
            return json.loads(STORE_FILE.read_text())
        return {"workflows": {}}
    except:
        return {"workflows": {}}

def _save(data: Dict):
    try:
        STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write — verhindert korrupte JSON bei Crash
        _tmp = STORE_FILE.with_suffix(".tmp")
        _tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        os.replace(_tmp, STORE_FILE)
    except Exception as e:
        log.error(f"TLA save error: {e}")


# ── MCP Tool Handlers ─────────────────────────────────────────────────────────

async def handle_tla_plan(params: Dict[str, Any]) -> Dict:
    """
    Erstellt einen neuen formalen Workflow-Plan (TLA+ Spec).
    
    params:
      title       (str)   - Aufgaben-Titel
      description (str)   - Was soll erreicht werden
      phases      (list)  - Liste von Phasen:
                            [{name, description, actions:[str], 
                              postcondition:str, mcp_tools:[str]}]
      invariants  (list)  - Safety-Eigenschaften die immer gelten müssen
      agent       (str)   - Zuständiger Agent (gemini-mcp|claude-mcp|codex-mcp)
      timeout_min (int)   - Max Laufzeit in Minuten (default: 60)
    
    Beispiel TLA+-Spec:
      title: "Redis-Reconnect Fix"
      phases:
        - name: DIAGNOSE
          actions: ["logs_errors", "service_status"]
          postcondition: "Redis-Fehler identifiziert"
        - name: FIX
          actions: ["code_edit", "service_restart"]  
          postcondition: "Service läuft ohne Fehler"
          terminal: true
      invariants:
        - "triforce.service bleibt während Fix erreichbar"
        - "Kein Datenverlust in /var/tristar/memory"
    """
    try:
        spec = {
            "title": params.get("title", "Unbenannter Workflow"),
            "description": params.get("description", ""),
            "phases": params.get("phases", []),
            "invariants": params.get("invariants", []),
            "agent": params.get("agent", "gemini-mcp"),
            "timeout_min": params.get("timeout_min", 60),
        }
        
        errors = _verify_spec(spec)
        
        wf_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        
        workflow = {
            "id": wf_id,
            "spec": spec,
            "state": "PLAN" if not errors else "PLAN_INVALID",
            "current_phase": 0,
            "verify_errors": errors,
            "created_at": now,
            "updated_at": now,
            "history": [{"ts": now, "event": "created", "state": "PLAN"}],
            "results": {},
        }
        
        data = _load()
        data["workflows"][wf_id] = workflow
        _save(data)
        
        return {
            "workflow_id": wf_id,
            "state": workflow["state"],
            "verify_errors": errors,
            "next_step": "tla_verify" if not errors else "Fix spec errors then tla_verify",
            "phases": [p["name"] for p in spec["phases"]],
        }
    except Exception as e:
        return {"error": str(e)}


async def handle_tla_verify(params: Dict[str, Any]) -> Dict:
    """
    Verifiziert den Plan und wechselt zu VERIFY→EXECUTE wenn OK.
    
    params:
      id (str) - Workflow-ID
    """
    try:
        wf_id = params.get("id", "")
        data = _load()
        wf = data["workflows"].get(wf_id)
        if not wf:
            return {"error": f"Workflow {wf_id} nicht gefunden"}
        
        errors = _verify_spec(wf["spec"])
        now = datetime.now(timezone.utc).isoformat()
        
        if errors:
            wf["verify_errors"] = errors
            wf["state"] = "PLAN"
            wf["history"].append({"ts": now, "event": "verify_failed", "errors": errors})
            _save(data)
            return {"ok": False, "errors": errors, "state": "PLAN", 
                    "message": "Spec hat Fehler — bitte korrigieren"}
        
        wf["state"] = "VERIFY"
        wf["verify_errors"] = []
        wf["history"].append({"ts": now, "event": "verified_ok", "state": "VERIFY"})
        wf["updated_at"] = now
        _save(data)
        
        return {
            "ok": True,
            "state": "VERIFY",
            "invariants": wf["spec"]["invariants"],
            "phases": [p["name"] for p in wf["spec"]["phases"]],
            "next_step": f"tla_advance(id={wf_id}) um EXECUTE zu starten",
        }
    except Exception as e:
        return {"error": str(e)}


async def handle_tla_status(params: Dict[str, Any]) -> Dict:
    """
    Gibt Status aller oder eines spezifischen Workflows zurück.
    
    params:
      id    (str)  - Spezifischer Workflow (optional)
      all   (bool) - Alle anzeigen inkl. DONE/ABORT (default: false)
    """
    try:
        data = _load()
        wf_id = params.get("id")
        
        if wf_id:
            wf = data["workflows"].get(wf_id)
            if not wf:
                return {"error": f"Workflow {wf_id} nicht gefunden"}
            return {
                "id": wf_id,
                "title": wf["spec"]["title"],
                "state": wf["state"],
                "phase": wf["current_phase"],
                "phase_name": wf["spec"]["phases"][wf["current_phase"]]["name"] if wf["spec"]["phases"] else "none",
                "agent": wf["spec"]["agent"],
                "invariants": wf["spec"]["invariants"],
                "history": wf["history"][-5:],
                "results": wf["results"],
            }
        
        show_all = params.get("all", False)
        active_states = {"PLAN", "VERIFY", "EXECUTE", "MONITOR"}
        
        result = []
        for wid, wf in data["workflows"].items():
            if not show_all and wf["state"] not in active_states:
                continue
            result.append({
                "id": wid,
                "title": wf["spec"]["title"],
                "state": wf["state"],
                "agent": wf["spec"]["agent"],
                "created": wf["created_at"][:16],
            })
        
        return {"count": len(result), "workflows": result}
    except Exception as e:
        return {"error": str(e)}


async def handle_tla_advance(params: Dict[str, Any]) -> Dict:
    """
    Schiebt Workflow zur nächsten Phase vor.
    
    params:
      id      (str)  - Workflow-ID
      result  (str)  - Ergebnis der aktuellen Phase (optional)
      success (bool) - War die Phase erfolgreich? (default: true)
    """
    try:
        wf_id = params.get("id", "")
        data = _load()
        wf = data["workflows"].get(wf_id)
        if not wf:
            return {"error": f"Workflow {wf_id} nicht gefunden"}
        
        current_state = wf["state"]
        now = datetime.now(timezone.utc).isoformat()
        success = params.get("success", True)
        result_text = params.get("result", "")
        
        # State-Machine
        if current_state == "VERIFY":
            wf["state"] = "EXECUTE"
        elif current_state == "EXECUTE":
            wf["state"] = "MONITOR" if success else "ABORT"
        elif current_state == "MONITOR":
            phases = wf["spec"]["phases"]
            next_phase_idx = wf["current_phase"] + 1
            if not success:
                wf["state"] = "EXECUTE"  # Retry
            elif next_phase_idx >= len(phases) or phases[wf["current_phase"]].get("terminal"):
                wf["state"] = "DONE"
            else:
                wf["current_phase"] = next_phase_idx
                wf["state"] = "EXECUTE"
        else:
            return {"error": f"Kann von {current_state} nicht weiter"}
        
        if result_text:
            wf["results"][f"phase_{wf['current_phase']}"] = result_text
        
        wf["history"].append({
            "ts": now, "event": "advanced",
            "from": current_state, "to": wf["state"],
            "success": success,
        })
        wf["updated_at"] = now
        _save(data)
        
        return {
            "workflow_id": wf_id,
            "previous_state": current_state,
            "new_state": wf["state"],
            "phase": wf["current_phase"],
        }
    except Exception as e:
        return {"error": str(e)}


async def handle_tla_abort(params: Dict[str, Any]) -> Dict:
    """
    Bricht Workflow ab.
    
    params:
      id     (str) - Workflow-ID
      reason (str) - Abbruchgrund
    """
    try:
        wf_id = params.get("id", "")
        data = _load()
        wf = data["workflows"].get(wf_id)
        if not wf:
            return {"error": f"Workflow {wf_id} nicht gefunden"}
        
        now = datetime.now(timezone.utc).isoformat()
        reason = params.get("reason", "Manuell abgebrochen")
        wf["state"] = "ABORT"
        wf["history"].append({"ts": now, "event": "aborted", "reason": reason})
        wf["updated_at"] = now
        _save(data)
        
        return {"ok": True, "workflow_id": wf_id, "state": "ABORT", "reason": reason}
    except Exception as e:
        return {"error": str(e)}


# ── Handler Registry ──────────────────────────────────────────────────────────

TLA_TOOL_HANDLERS = {
    "tla_plan":    handle_tla_plan,
    "tla_verify":  handle_tla_verify,
    "tla_status":  handle_tla_status,
    "tla_advance": handle_tla_advance,
    "tla_abort":   handle_tla_abort,
}

TLA_TOOL_NAMES = list(TLA_TOOL_HANDLERS.keys())
