#!/bin/sh
nohup python3 -m http.server 8766 --directory /tmp >/tmp/ailinux-shot-http-8766.log 2>&1 </dev/null &
sleep 1
curl -I --max-time 3 http://127.0.0.1:8766/qss-safe-nav-2.png
