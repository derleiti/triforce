#!/usr/bin/env bash
set -euo pipefail
OUT="mcp_analytics_fix2_state_$(date +%F_%H-%M-%S).txt"
{
  echo "==== DATE ===="
  date -Is
  echo
  echo "==== PY_COMPILE ===="
  python3 -m py_compile app/routes/mcp.py && echo OK
  echo
  echo "==== TESTS ===="
  python3 -m unittest -v tests.test_mcp_analytics_fix2_unittest || true
  echo
  echo "==== VERIFY ===="
  ./verify_mcp_analytics_fix2.sh || true
} > "$OUT" 2>&1
echo "$OUT"
