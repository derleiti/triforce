#!/usr/bin/env bash
set -euo pipefail
OUT="chatgpt_web_fallback_state_$(date +%F_%H-%M-%S).txt"
{
  echo "==== DATE ===="
  date -Is
  echo
  echo "==== PY_COMPILE ===="
  python3 -m py_compile app/routes/mcp.py && echo OK
  echo
  echo "==== TESTS ===="
  python3 -m unittest -v tests.test_chatgpt_web_fallback_unittest || true
  echo
  echo "==== GREP HELPERS ===="
  grep -n "ChatGPT Web write fallback helpers" -n app/routes/mcp.py || true
  grep -n "_filter_tools_for_client" app/routes/mcp.py || true
  grep -n "_maybe_block_write_tool" app/routes/mcp.py || true
  echo
  echo "==== CURL VERIFY ===="
  ./verify_chatgpt_web_fallback.sh || true
} > "$OUT" 2>&1
echo "$OUT"
