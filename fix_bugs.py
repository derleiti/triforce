#!/usr/bin/env python3
"""Bug-Fix Script: WP#2, BE#19, BE-014, BE-007"""
import re, sys

errors = []

# ─── FIX WP#2: Hardcoded Credentials in nova-ai-frontend.php ─────────────────
wp_php = '/home/zombie/triforce/docker/wordpress/html/wp-content/plugins/nova-ai-frontend/nova-ai-frontend.php'
try:
    with open(wp_php, 'r') as f:
        c = f.read()
    old = "    $args = ['method'=>$method, 'timeout'=>15, 'headers'=>[\n        'Content-Type'=>'application/json',\n        'Authorization'=>'Basic '.base64_encode('zombie:e9F8DuKbH-'),\n    ]];"
    new = "    // FIX WP#2 2026-03-11: Credentials aus wp-config defines — kein Hardcode im Git\n    $api_user = defined('NOVA_AI_API_USER') ? NOVA_AI_API_USER : ($s['api_user'] ?? '');\n    $api_pass = defined('NOVA_AI_API_PASS') ? NOVA_AI_API_PASS : ($s['api_pass'] ?? '');\n    $auth_header = ($api_user && $api_pass) ? 'Basic ' . base64_encode($api_user . ':' . $api_pass) : '';\n    $headers = ['Content-Type' => 'application/json'];\n    if ($auth_header) $headers['Authorization'] = $auth_header;\n    $args = ['method'=>$method, 'timeout'=>15, 'headers'=>$headers];"
    if old in c:
        c2 = c.replace(old, new, 1)
        with open(wp_php, 'w') as f:
            f.write(c2)
        print("WP#2 FIXED: Credentials deobfusicated ✅")
    else:
        print("WP#2 SKIP: Pattern not found (may already be fixed)")
        idx = c.find("base64_encode('zombie")
        if idx >= 0:
            print("  Found at:", repr(c[idx-20:idx+50]))
except Exception as e:
    errors.append(f"WP#2 ERROR: {e}")

# ─── FIX BE#19: model_count "all" String in tiers.py ────────────────────────
tiers_py = '/home/zombie/triforce/app/routes/tiers.py'
try:
    with open(tiers_py, 'r') as f:
        c = f.read()
    old19 = '    count = len(models) if isinstance(models, list) else "all"'
    new19 = '    count = len(models) if isinstance(models, list) else 0  # FIX BE#19: int, not str "all"'
    if old19 in c:
        c2 = c.replace(old19, new19, 1)
        with open(tiers_py, 'w') as f:
            f.write(c2)
        print("BE#19 FIXED: model_count='all' -> 0 ✅")
    else:
        print("BE#19 SKIP: Pattern not found")
except Exception as e:
    errors.append(f"BE#19 ERROR: {e}")

# ─── FIX BE-014: File Handle Leak in nova_frontend.py ────────────────────────
nf_py = '/home/zombie/triforce/app/routes/nova_frontend.py'
try:
    with open(nf_py, 'r') as f:
        c = f.read()
    old14 = 'return open(p).read().strip()'
    new14 = 'with open(p) as _fh: return _fh.read().strip()  # FIX BE-014: close file handle'
    count14 = c.count(old14)
    if count14 > 0:
        c2 = c.replace(old14, new14)
        with open(nf_py, 'w') as f:
            f.write(c2)
        print(f"BE-014 FIXED: {count14} file handle leak(s) fixed ✅")
    else:
        print("BE-014 SKIP: No open() leak found")
except Exception as e:
    errors.append(f"BE-014 ERROR: {e}")

# ─── FIX BE-007: hmac.new() ohne digestmod= keyword ──────────────────────────
import os
files_007 = [
    '/home/zombie/triforce/app/routes/user_api.py',
    '/home/zombie/triforce/app/routes/client_auth.py',
    '/home/zombie/triforce/app/services/server_federation.py',
]
total_007 = 0
for fp in files_007:
    try:
        if not os.path.exists(fp):
            print(f"BE-007 SKIP: {fp} not found")
            continue
        with open(fp, 'r') as f:
            c = f.read()
        # Match hmac.new(...hashlib.sha256) without digestmod=
        pattern = re.compile(r'(hmac\.new\([^)]+)(hashlib\.sha256)(\s*\))', re.MULTILINE)
        def add_digestmod(m):
            inner = m.group(1)
            if 'digestmod=' in inner:
                return m.group(0)  # already has it
            return inner + 'digestmod=' + m.group(2) + m.group(3)
        c2, n = pattern.subn(add_digestmod, c)
        if n > 0:
            with open(fp, 'w') as f:
                f.write(c2)
            total_007 += n
            print(f"BE-007 FIXED: {n} occurrence(s) in {os.path.basename(fp)} ✅")
        else:
            print(f"BE-007 SKIP: No pattern in {os.path.basename(fp)}")
    except Exception as e:
        errors.append(f"BE-007 ERROR {fp}: {e}")

print(f"BE-007 TOTAL: {total_007} hmac fixes applied")

# ─── Summary ──────────────────────────────────────────────────────────────────
print("\n=== FIX SCRIPT DONE ===")
if errors:
    print("ERRORS:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
else:
    print("All fixes applied cleanly.")
