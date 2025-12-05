# Smoke Tests - Quick Verification Commands

Use these commands to quickly verify the backend is running correctly after deployment.

## Prerequisites

- Backend running on port 9100 (internal)
- NGINX reverse proxy on port 9000 (external)
- Redis and Ollama services running

## Quick Health Check

```bash
# Internal backend health check
curl -sS http://127.0.0.1:9100/health

# Expected output:
# {"status":"ok"}

# External (through NGINX) health check
curl -sS http://127.0.0.1:9000/health
```

## List Available Models

```bash
# List all available models
curl -sS http://127.0.0.1:9000/v1/models | jq

# Expected output: JSON array with models from Ollama, GPT-OSS, etc.
# [
#   {"id": "ollama/llama2", "provider": "ollama", "capabilities": ["chat"]},
#   {"id": "gpt-oss:cloud/120b", "provider": "gpt-oss", "capabilities": ["chat"]},
#   ...
# ]
```

## Chat Endpoint Tests

### Non-Streaming Chat

```bash
# Test non-streaming chat (main endpoint)
curl -sS -X POST http://127.0.0.1:9000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-oss:cloud/120b",
    "messages": [{"role": "user", "content": "Hello! Say hi back."}],
    "stream": false
  }' | jq

# Expected output:
# {
#   "text": "Hi! How can I help you today?"
# }
```

### Streaming Chat

```bash
# Test streaming chat (should output tokens progressively)
curl -N -X POST http://127.0.0.1:9000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-oss:cloud/120b",
    "messages": [{"role": "user", "content": "Tell me a short joke"}],
    "stream": true
  }'

# Expected: Text streaming in real-time (text/plain)
```

### Chat Completions Alias (Backwards Compatibility)

```bash
# Test /v1/chat/completions alias
curl -sS -X POST http://127.0.0.1:9000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-oss:cloud/120b",
    "messages": [{"role": "user", "content": "Test"}],
    "stream": false
  }' | jq

# Expected: Same response format as /v1/chat
```

## Vision Endpoint Test

```bash
# Test vision chat with image URL
curl -sS -X POST http://127.0.0.1:9000/v1/vision/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "ollama/llava",
    "messages": [{"role": "user", "content": "What is in this image?"}],
    "image_url": "https://example.com/image.jpg",
    "stream": false
  }' | jq
```

## Image Generation Test

```bash
# Test Stable Diffusion image generation
curl -sS -X POST http://127.0.0.1:9000/v1/images/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg_scale": 7.5,
    "model": "sd_xl_base_1.0.safetensors"
  }' | jq

# Expected output: {"images": ["data:image/png;base64,..."]}
# Note: May return {"images": []} if GPU memory insufficient (SDXL requires >12GB VRAM)
```

## Web Crawler Tests

### Create Crawl Job

```bash
# Start a web crawl job
curl -sS -X POST http://127.0.0.1:9000/v1/crawler/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "keywords": ["ai", "machine learning"],
    "seeds": ["https://example.com"],
    "max_depth": 2,
    "max_pages": 10
  }' | jq

# Expected output:
# {
#   "id": "job-12345",
#   "status": "queued",
#   "created_at": "2025-10-02T..."
# }
```

### Check Crawl Job Status

```bash
# Replace JOB_ID with actual job ID from previous command
JOB_ID="job-12345"

curl -sS http://127.0.0.1:9000/v1/crawler/jobs/${JOB_ID}/status | jq

# Expected output:
# {
#   "id": "job-12345",
#   "status": "completed",
#   "pages_crawled": 10,
#   "results_count": 8
# }
```

### Search Crawl Results

```bash
# Search crawled content
curl -sS -X POST http://127.0.0.1:9000/v1/crawler/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "machine learning",
    "limit": 5,
    "min_score": 0.3
  }' | jq

# Expected: Top-K relevant crawl results with scores
```

## CORS Verification

```bash
# Test CORS preflight request
curl -X OPTIONS http://127.0.0.1:9000/v1/models \
  -H "Origin: https://ailinux.me" \
  -H "Access-Control-Request-Method: POST" \
  -v 2>&1 | grep -i "access-control"

# Expected headers:
# Access-Control-Allow-Origin: https://ailinux.me
# Access-Control-Allow-Methods: *
# Access-Control-Allow-Credentials: true
```

## Rate Limiting Test

```bash
# Test rate limiting (should allow 5 requests in 10 seconds)
for i in {1..6}; do
  echo "Request $i:"
  curl -sS -X POST http://127.0.0.1:9000/v1/chat \
    -H 'Content-Type: application/json' \
    -d '{"model":"gpt-oss:cloud/120b","messages":[{"role":"user","content":"Hi"}],"stream":false}' \
    | jq -r '.text // .error.message'
  sleep 1
done

# Expected: First 5 succeed, 6th returns rate limit error (429)
```

## Error Handling Tests

### 404 - Model Not Found

```bash
# Test with non-existent model
curl -sS -X POST http://127.0.0.1:9000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "nonexistent-model",
    "messages": [{"role": "user", "content": "Test"}],
    "stream": false
  }' | jq

# Expected:
# {
#   "error": {
#     "message": "Requested model does not support chat",
#     "code": "model_not_found"
#   }
# }
```

### 422 - Validation Error

```bash
# Test with missing messages
curl -sS -X POST http://127.0.0.1:9000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-oss:cloud/120b",
    "messages": [],
    "stream": false
  }' | jq

# Expected:
# {
#   "error": {
#     "message": "At least one message is required",
#     "code": "missing_messages"
#   }
# }
```

### 503 - Service Unavailable

```bash
# Test WordPress without credentials
curl -sS -X POST http://127.0.0.1:9000/v1/posts/create \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Test Post",
    "content": "Test content"
  }' | jq

# Expected (if WordPress not configured):
# {
#   "error": {
#     "message": "WordPress credentials/url are not configured",
#     "code": "wordpress_unavailable"
#   }
# }
```

## Full Smoke Test Script

Create a file `smoke-test.sh`:

```bash
#!/bin/bash

set -e

BASE_URL="${BASE_URL:-http://127.0.0.1:9000}"
echo "Running smoke tests against: $BASE_URL"

# 1. Health Check
echo -e "\n=== Health Check ==="
curl -sS $BASE_URL/health | jq

# 2. List Models
echo -e "\n=== List Models ==="
curl -sS $BASE_URL/v1/models | jq -r '.[].id' | head -5

# 3. Chat (Non-Streaming)
echo -e "\n=== Chat Non-Streaming ==="
curl -sS -X POST $BASE_URL/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-oss:cloud/120b","messages":[{"role":"user","content":"Hi"}],"stream":false}' \
  | jq -r '.text'

# 4. Chat Completions Alias
echo -e "\n=== Chat Completions Alias ==="
curl -sS -X POST $BASE_URL/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-oss:cloud/120b","messages":[{"role":"user","content":"Test"}],"stream":false}' \
  | jq -r '.text'

echo -e "\n✅ All smoke tests passed!"
```

Make it executable:

```bash
chmod +x smoke-test.sh
./smoke-test.sh
```

## Troubleshooting

If any test fails:

1. **Health check fails**: Backend not running on port 9100
2. **Models list empty**: Ollama not running or not accessible
3. **Chat fails**: Check logs with `journalctl -u ailinux-backend -n 50`
4. **CORS errors**: Add origin to `CORS_ALLOWED_ORIGINS` in .env
5. **Rate limit always triggers**: Redis not connected (check `REDIS_URL`)
6. **404 on /v1/chat**: NGINX not proxying correctly, check config
