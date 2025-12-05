## Mirror Sync & Sign Workflow

1. **Prep environment**
   - Ensure `docker compose up -d` already started the `apt-mirror` service.
   - Confirm enough free disk space with `./monitor-indexes.sh --disk`.

2. **Update mirror contents**
   - Run `./update-mirror.sh` (optionally append `--dry-run` first).
   - Wait for the apt-mirror job to finish; check progress with `docker compose logs --tail 100 apt-mirror`.

3. **Rebuild metadata**
   - Execute `./generate-index.sh` for DEP-11/AppStream and `./maintain.sh --health-only` to verify indexes.

4. **Resign repositories**
   - Invoke `./sign-repos.sh` to refresh Release files.
   - Review `mirror-sign.log` for signature or checksum issues.

5. **Final validation**
   - Run `./health.sh` followed by `./repo-health.sh` when routing or metadata changed.
   - Spot-check a critical i386 package with `curl -I https://repo.ailinux.me:8443/mirror/archive.ubuntu.com/ubuntu/dists/noble/main/binary-i386/Packages.gz`.

Follow the steps in order after every mirror list change so all amd64+i386 suites stay consistent.
