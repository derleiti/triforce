#!/bin/bash
set -Eeuo pipefail
project=/home/zombie/AILinuX-Distro
builder=/home/zombie/.cache/ailinux-distro-builder/resolute-rootfs
cd "$project"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
name="ailinux-26.04-amd64-${stamp}.iso"
iso="$project/output/$name"
log="$project/output/repack-qss-${stamp}.log"
exec > >(tee "$log") 2>&1

rm -f binary/casper/filesystem.squashfs.new
unshare --user --map-root-user --map-auto --mount --pid --fork --mount-proc \
  bash -Eeuo pipefail -c '
    cd /home/zombie/AILinuX-Distro
    mksquashfs chroot binary/casper/filesystem.squashfs.new \
      -noappend -comp gzip -b 131072 -one-file-system -processors "$(nproc)"
  '

unsquashfs -cat binary/casper/filesystem.squashfs.new etc/calamares/branding/ailinux/stylesheet.qss | grep -Fq 'background-color: #0e1116;'
unsquashfs -cat binary/casper/filesystem.squashfs.new etc/calamares/modules/partition.conf | grep -Fq 'userSwapChoices: [ file ]'
unsquashfs -cat binary/casper/filesystem.squashfs.new etc/calamares/modules/bootloader.conf | grep -Fq 'efiBootLoader: "grub"'
mv -f binary/casper/filesystem.squashfs.new binary/casper/filesystem.squashfs

dpkg-query --admindir=chroot/var/lib/dpkg -W -f='${Package} ${Version}\n' | LC_ALL=C sort > binary/casper/filesystem.manifest
printf '%s\n' calamares live-boot live-config live-config-systemd > binary/casper/filesystem.manifest-remove
unshare --user --map-root-user --map-auto --mount --pid --fork --mount-proc \
  bash -Eeuo pipefail -c 'cd /home/zombie/AILinuX-Distro; du -sx --block-size=1 chroot | awk "{print \$1}" > binary/casper/filesystem.size'

(
  cd binary
  rm -f SHA256SUMS md5sum.txt
  find . -type f ! -name SHA256SUMS ! -name md5sum.txt -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > SHA256SUMS
  find . -type f ! -name SHA256SUMS ! -name md5sum.txt -print0 | LC_ALL=C sort -z | xargs -0 md5sum > md5sum.txt
  sha256sum -c --quiet SHA256SUMS
  md5sum -c --quiet md5sum.txt
)

rm -f "$iso"
unshare --user --map-root-user --map-auto --mount --pid --fork --mount-proc \
  bash -Eeuo pipefail -c '
    builder=$1
    project=$2
    name=$3
    mkdir -p "$builder/workspace" "$builder/dev" "$builder/proc" "$builder/sys"
    mount --bind "$project" "$builder/workspace"
    mount --rbind /dev "$builder/dev"
    mount --make-rslave "$builder/dev"
    mount -t proc proc "$builder/proc"
    mount --rbind /sys "$builder/sys"
    mount --make-rslave "$builder/sys"
    cleanup() {
      umount -R "$builder/sys" 2>/dev/null || true
      umount "$builder/proc" 2>/dev/null || true
      umount -R "$builder/dev" 2>/dev/null || true
      umount "$builder/workspace" 2>/dev/null || true
    }
    trap cleanup EXIT HUP INT TERM
    chroot "$builder" /bin/bash -Eeuo pipefail -c "cd /workspace; rm -f binary/boot/grub/grub_eltorito; grub-mkrescue -o output/$name binary -- -volid AILINUX_2604"
  ' bash "$builder" "$project" "$name"

sha256sum "$iso" > "$iso.sha256"
sha256sum -c "$iso.sha256"
file "$iso"
printf 'NEW_ISO=%s\nLOG=%s\n' "$iso" "$log"
