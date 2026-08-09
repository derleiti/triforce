#!/bin/bash
set -Eeuo pipefail
name=ailinux-qss-verify
iso=/home/zombie/AILinuX-Distro/output/ailinux-26.04-amd64-20260801T054030Z.iso
disk=/tmp/ailinux-qss-verify.qcow2
virsh -c qemu:///system destroy "$name" >/dev/null 2>&1 || true
virsh -c qemu:///system undefine "$name" --nvram >/dev/null 2>&1 || virsh -c qemu:///system undefine "$name" >/dev/null 2>&1 || true
rm -f "$disk"
qemu-img create -f qcow2 "$disk" 25G
virt-install --connect qemu:///system --name "$name" --memory 4096 --vcpus 2 --cpu host-passthrough --machine q35 \
  --disk path="$disk",format=qcow2,bus=virtio \
  --disk path="$iso",device=cdrom,bus=sata,readonly=on \
  --network network=default,model=virtio \
  --graphics spice,listen=127.0.0.1 --video virtio \
  --channel unix,target_type=virtio,name=org.qemu.guest_agent.0 \
  --osinfo detect=on,require=off --boot cdrom,hd --noautoconsole
for i in $(seq 1 120); do
  if virsh -c qemu:///system qemu-agent-command "$name" '{"execute":"guest-ping"}' >/dev/null 2>&1; then
    echo "AGENT_READY_AT=$i"
    exit 0
  fi
  sleep 2
done
echo AGENT_TIMEOUT
exit 1
