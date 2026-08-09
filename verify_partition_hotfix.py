import base64, json, subprocess, time
from pathlib import Path
from PIL import Image
D='ailinux-qss-verify'
CONF=Path('/home/zombie/AILinuX-Distro/config/includes.chroot/etc/calamares/modules/partition.conf').read_bytes()

def virsh(*args):
 p=subprocess.run(['virsh','-c','qemu:///system',*args],text=True,capture_output=True)
 if p.returncode: raise RuntimeError(p.stderr or p.stdout)
 return p.stdout

def qga(payload): return json.loads(virsh('qemu-agent-command',D,json.dumps(payload)))['return']
qga({'execute':'guest-ping'})
# Close welcome app and old Calamares.
for cmd in [
 "pkill -f 'plasma-welcome|kde-welcome' || true",
 "pkill -x calamares || true",
 "rm -f /root/.cache/calamares/session.log",
]:
 r=qga({'execute':'guest-exec','arguments':{'path':'/bin/bash','arg':['-lc',cmd],'capture-output':True}})
 time.sleep(.5)
# Replace partition config.
h=qga({'execute':'guest-file-open','arguments':{'path':'/etc/calamares/modules/partition.conf','mode':'w'}})
qga({'execute':'guest-file-write','arguments':{'handle':h,'buf-b64':base64.b64encode(CONF).decode()}})
qga({'execute':'guest-file-flush','arguments':{'handle':h}}); qga({'execute':'guest-file-close','arguments':{'handle':h}})
# Launch Calamares.
qga({'execute':'guest-exec','arguments':{'path':'/usr/bin/env','arg':['HOME=/root','DISPLAY=:0','WAYLAND_DISPLAY=wayland-0','XDG_RUNTIME_DIR=/run/user/1000','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus','QT_QPA_PLATFORM=wayland','/usr/bin/calamares','-d'],'capture-output':False}})
time.sleep(7)
for _ in range(3):
 virsh('send-key',D,'KEY_LEFTALT','KEY_W'); time.sleep(4)
virsh('screenshot',D,'/tmp/partition-hotfix-final.png')
# Query logs.
cmd="grep -nEi 'restriction|partition|stylesheet|qml|error|invalid' /root/.cache/calamares/session.log | tail -n 220"
r=qga({'execute':'guest-exec','arguments':{'path':'/bin/bash','arg':['-lc',cmd],'capture-output':True}}); pid=r['pid']
for _ in range(100):
 s=qga({'execute':'guest-exec-status','arguments':{'pid':pid}})
 if s.get('exited'):
  print(base64.b64decode(s.get('out-data','')).decode('utf-8','replace')); break
 time.sleep(.1)
im=Image.open('/tmp/partition-hotfix-final.png').convert('RGB'); w,h=im.size
for name,box in {'content':(w//4,0,w,h),'content_top':(w//4,0,w,h//2)}.items():
 c=im.crop(box).resize((200,120)); vals=[sum(p)/3 for p in c.getdata()]
 print(name,'bright_pct',round(sum(v>220 for v in vals)/len(vals)*100,1),'dark_pct',round(sum(v<45 for v in vals)/len(vals)*100,1))
