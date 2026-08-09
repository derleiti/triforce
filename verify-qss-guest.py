import base64, json, subprocess, time
from PIL import Image
D='ailinux-qss-verify'

def virsh(*args):
 p=subprocess.run(['virsh','-c','qemu:///system',*args],text=True,capture_output=True)
 if p.returncode: raise RuntimeError(p.stderr or p.stdout)
 return p.stdout

def qga(payload): return json.loads(virsh('qemu-agent-command',D,json.dumps(payload)))['return']
qga({'execute':'guest-ping'})
try: qga({'execute':'guest-exec','arguments':{'path':'/usr/bin/pkill','arg':['-x','calamares'],'capture-output':True}})
except Exception: pass
time.sleep(2)
qga({'execute':'guest-exec','arguments':{'path':'/bin/rm','arg':['-f','/root/.cache/calamares/session.log'],'capture-output':True}})
qga({'execute':'guest-exec','arguments':{'path':'/usr/bin/env','arg':['HOME=/root','DISPLAY=:0','WAYLAND_DISPLAY=wayland-0','XDG_RUNTIME_DIR=/run/user/1000','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus','QT_QPA_PLATFORM=wayland','/usr/bin/calamares','-d'],'capture-output':False}})
time.sleep(6)
for _ in range(3):
 virsh('send-key',D,'KEY_LEFTALT','KEY_W'); time.sleep(4)
virsh('screenshot',D,'/tmp/qss-final-iso-partition.png')
# Pull log through QGA.
cmd="grep -nEi 'stylesheet|style|partition|warning|error|invalid|qml' /root/.cache/calamares/session.log | tail -n 180"
r=qga({'execute':'guest-exec','arguments':{'path':'/bin/bash','arg':['-lc',cmd],'capture-output':True}}); pid=r['pid']
log=''
for _ in range(100):
 s=qga({'execute':'guest-exec-status','arguments':{'pid':pid}})
 if s.get('exited'):
  log=base64.b64decode(s.get('out-data','')).decode('utf-8','replace'); break
 time.sleep(.1)
print('LOG_MATCHES_BEGIN'); print(log,end=''); print('LOG_MATCHES_END')
im=Image.open('/tmp/qss-final-iso-partition.png').convert('RGB'); w,h=im.size
for name,box in {'content':(w//4,0,w,h),'content_top':(w//4,0,w,h//2)}.items():
 c=im.crop(box).resize((200,120)); vals=[sum(p)/3 for p in c.getdata()]
 print(name,'bright_pct',round(sum(v>220 for v in vals)/len(vals)*100,1),'dark_pct',round(sum(v<45 for v in vals)/len(vals)*100,1))
print('DONE')
