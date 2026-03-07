cd /home/zombie/triforce

# optional: kaputtes config.py sichern
cp -av app/config.py "app/config.py.BAD.$(date +%Y%m%d_%H%M%S)" || true

cfg_bak="$(
  find .patch-bak -type f -path '*/app/config.py' -printf '%T@ %p\n' \
  | sort -nr | head -n1 | cut -d' ' -f2-
)"

echo "Using backup: $cfg_bak"
test -n "$cfg_bak" && test -f "$cfg_bak" || { echo "ERROR: no backup config.py found"; exit 1; }

cp -av "$cfg_bak" app/config.py

/home/zombie/triforce/.venv/bin/python -m compileall -q app || exit 1
sudo systemctl restart triforce
sudo journalctl -u triforce -n 80 --no-pager
