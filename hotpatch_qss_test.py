import base64, json, subprocess, time
from pathlib import Path
D='ailinux-installer-test'
QSS=Path('/home/zombie/AILinuX-Distro/config/includes.chroot/etc/calamares/branding/ailinux/stylesheet.qss').read_bytes()

def virsh(*args):
    p=subprocess.run(['virsh','-c','qemu:///system',*args],text=True,capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def qga(payload):
    return json.loads(virsh('qemu-agent-command',D,json.dumps(payload)))['return']

qga({'execute':'guest-ping'})
# Stop Calamares.
try:
    qga({'execute':'guest-exec','arguments':{'path':'/usr/bin/pkill','arg':['-x','calamares'],'capture-output':True}})
except Exception:
    pass
time.sleep(2)
# Write stylesheet.
h=qga({'execute':'guest-file-open','arguments':{'path':'/etc/calamares/branding/ailinux/stylesheet.qss','mode':'w'}})
for pos in range(0,len(QSS),48*1024):
    qga({'execute':'guest-file-write','arguments':{'handle':h,'buf-b64':base64.b64encode(QSS[pos:pos+48*1024]).decode()}})
qga({'execute':'guest-file-flush','arguments':{'handle':h}})
qga({'execute':'guest-file-close','arguments':{'handle':h}})
# Clear old log and restart.
qga({'execute':'guest-exec','arguments':{'path':'/bin/rm','arg':['-f','/root/.cache/calamares/session.log'],'capture-output':True}})
r=qga({'execute':'guest-exec','arguments':{
    'path':'/usr/bin/env',
    'arg':['HOME=/root','DISPLAY=:0','WAYLAND_DISPLAY=wayland-0','XDG_RUNTIME_DIR=/run/user/1000','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus','QT_QPA_PLATFORM=wayland','/usr/bin/calamares','-d'],
    'capture-output':False}})
print('PID',r.get('pid'))
time.sleep(7)
virsh('screenshot',D,'/tmp/qss-safe-welcome.png')
print('READY')
