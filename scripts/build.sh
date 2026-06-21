#!/usr/bin/env bash
# Do not use `set -u` here: AOSP build/envsetup.sh references $TOP before it is set
# (line ~21), which aborts under nounset.
set -eo pipefail

# Run from AOHP repo root (directory that contains AOSP/, scripts/, cli/).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Requesting sudo privileges up front..."
sudo -v
(
  while true; do
    sudo -n -v
    sleep 60
  done
) &
SUDO_KEEPALIVE_PID=$!
trap 'kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true' EXIT

cd "$ROOT/AOSP"

# Activate AOSP build env
source build/envsetup.sh

# Target
lunch aosp_cf_x86_64_phone_aohp-trunk_staging-userdebug

# 1) Host-build AOHP CLI (esbuild single file)
bash "$ROOT/scripts/build-cli.sh"

# 2) Repack Alpine rootfs template (embeds /usr/local/bin/aohp + node)
pushd "$ROOT/AOSP/packages/apps/AOHPAgentDriver/rootfs" >/dev/null
./prepare_rootfs.sh x86_64
popd >/dev/null

# 3) If you changed AOHPAgentDriver Java/resources in Android Studio, copy APK before m:
#    cp "$ROOT/aohp-app/AOHPAgentDriver/app/build/outputs/apk/debug/"*.apk \
#       "$ROOT/AOSP/packages/apps/AOHPAgentDriver/AOHPAgentDriver.apk"

# 4) Incremental platform build
m -j10
