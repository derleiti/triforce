# TODO – Prompt / Init / MCP↔FastAPI / WordPress

1. Prompt-Hierarchie zentralisieren
   - runtime prompt
   - /var/tristar/prompts/<agent>.txt
   - reflect_resume_debug_prompt.txt / reflect_prompt.txt
   - /home/zombie/triforce/triforce/prompts/*
   - model-init prompt
   - default init prompt

2. Init-Endpunkte auf gemeinsame Promptquelle umstellen
   - app/services/init_service.py
   - app/routes/mcp.py

3. Operativen Fallback-Resolver einbauen
   - MCP primär
   - bei MCP-Fehler API/OpenAI-kompatibler FastAPI-Pfad
   - bei Agent-Bedarf Agent-Autostart + Retry
   - response metadata: fallback_used, fallback_reason, primary_path

4. WordPress TLS/CA-Fallback sauber einbauen
   - primär verify=true
   - optional konfigurierbarer CA-Bundle-Pfad
   - optional expliziter verify=false Fallback nur per Config

5. End-to-End-Validierung
   - MCP success
   - MCP fail -> API fallback
   - API fail -> MCP fallback
   - Agent down -> start -> retry
   - WordPress normal / TLS fallback
