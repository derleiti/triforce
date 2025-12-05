# Integration Notes

- Brave/Leo base URL checks now succeed: `GET /v1` issues a temporary redirect to `/v1/`, and the trailing-slash endpoint returns the OpenAI-compatible metadata payload. 
- Health probes at `/health` respond with `{"status":"ok"}` and are hidden from Swagger, keeping the schema concise.
- The API CORS policy allows `https://ailinux.me`, `https://www.ailinux.me`, `https://api.ailinux.me`, and local testing origins so browser clients can call `/v1` resources without errors.
