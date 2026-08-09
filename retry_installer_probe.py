import base64, json, subprocess, time
D='ailinux-installer-test'

def run(cmd, timeout=60):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)

def virsh(*args):
    p=run(['virsh','-c','qemu:///system',*args])
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def qga(payload):
    return json.loads(virsh('qemu-agent-command',D,json.dumps(payload)))['return']

print('STATE',virsh('domstate',D).strip())
qga({'execute':'guest-ping'})
# Kill any stale installer, clear log, launch fresh in live Wayland session.
for command in [
    ['/usr/bin/pkill','-x','calamares'],
    ['/bin/rm','-f','/root/.cache/calamares/session.log'],
]:
    try:
        qga({'execute':'guest-exec','arguments':{'path':command[0],'arg':command[1:],'capture-output':True}})
    except Exception:
        pass
time.sleep(2)
ret=qga({'execute':'guest-exec','arguments':{
    'path':'/usr/bin/env',
    'arg':['HOME=/root','DISPLAY=:0','WAYLAND_DISPLAY=wayland-0','XDG_RUNTIME_DIR=/run/user/1000','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus','QT_QPA_PLATFORM=wayland','/usr/bin/calamares','-d'],
    'capture-output':False,
}})
print('CALAMARES_PID',ret.get('pid'))
time.sleep(8)
virsh('screenshot',D,'/tmp/ailinux-installer-retry.png')
print('SCREENSHOT=/tmp/ailinux-installer-retry.png')
# Fetch a compact log snapshot through QGA.
script="""set +e
printf '%s\n' '===== PROCESS ====='
ps auxww | grep '[c]alamares'
printf '%s\n' '===== ERRORS ====='
grep -nEi 'warning|error|invalid|missing|bootloader|swap|partition|qml|stylesheet' /root/.cache/calamares/session.log | tail -n 180
printf '%s\n' '===== TAIL ====='
tail -n 120 /root/.cache/calamares/session.log
"""
r=qga({'execute':'guest-exec','arguments':{'path':'/bin/bash','arg':['-lc',script],'capture-output':True}})
pid=r['pid']
for _ in range(120):
    s=qga({'execute':'guest-exec-status','arguments':{'pid':pid}})
    if s.get('exited'):
        print(base64.b64decode(s.get('out-data','')).decode('utf-8','replace'))
        err=base64.b64decode(s.get('err-data','')).decode('utf-8','replace')
        if err: print('STDERR',err)
        break
    time.sleep(.25)
