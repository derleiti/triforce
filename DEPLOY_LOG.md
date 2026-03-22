# Discuss with AI Fix — 2026-03-22
# Deployed directly to Docker containers (wordpress_fpm)
# Files: ailinux-nova-dark/assets/js/app.js + dist/app.js
# Also: ailinux-nova-dark-dev same files
# Bug #16: 3 HTML ID mismatches + missing fallback model list
# IDs fixed: ai-send→ai-discuss-send, ai-input→ai-discuss-input, ai-output→ai-discuss-chat
# Default model: llama4:latest → gpt-oss:120b-cloud
# 14 fallback models added for when /v1/models fails
