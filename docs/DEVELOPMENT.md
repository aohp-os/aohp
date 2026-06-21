# AOHP Development Guide

This guide covers setting up the AOHP development environment, building and running the system on Cuttlefish, and contributing code changes.

[中文](DEVELOPMENT.zh-CN.md) | [Back to project home](../README.md)

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [1. Initialization](#1-initialization)
  - [Clone the dev framework](#clone-the-dev-framework)
  - [Initialize AOSP sources](#initialize-aosp-sources)
  - [Download AOHP Agent Driver](#download-aohp-agent-driver)
- [2. Build & Run Cuttlefish](#2-build--run-cuttlefish)
  - [Build](#build)
  - [Launch the image](#launch-the-image)
  - [Multiple instances & ports](#multiple-instances--ports)
  - [Sandbox mode (high resources)](#sandbox-mode-high-resources)
- [3. VM networking](#3-vm-networking)
- [4. Modify & submit code](#4-modify--submit-code)
  - [Check local changes](#check-local-changes)
  - [Submit to an existing aohp-os repo](#submit-to-an-existing-aohp-os-repo)
  - [First-time submission for a new project](#first-time-submission-for-a-new-project)
  - [Sync upstream changes](#sync-upstream-changes)

---

## Prerequisites

- **OS**: Linux recommended (Cuttlefish's supported host environment)
- **Disk**: Hundreds of GB free for a full AOSP sync and build
- **Network**: Access to Google sources, or use the Tsinghua mirror (below)
- **Privileges**: `sudo` required to launch Cuttlefish

---

## 1. Initialization

### Clone the dev framework

```bash
git clone git@github.com:aohp-os/aohp.git
cd aohp
```

To customize [AOHPAgentDriver](https://github.com/aohp-os/AOHPAgentDriverApp), clone it into the `aohp-app/` directory.

### Initialize AOSP sources

> **Important**: A full sync is required; partial checkouts will cause build failures.

From `aohp`, enter `AOSP/` and choose one manifest source.

#### Option A: Google official source

```bash
cd AOSP

repo init -b android-latest-release

cd .repo
git clone git@github.com:aohp-os/local_manifests.git
cd ..

repo sync -j4
```

#### Option B: Tsinghua AOSP mirror

Most repos use the Tsinghua mirror; a small set of AOHP-specific repos still come from GitHub `aohp-os`.

```bash
cd AOSP

repo init -b android-latest-release \
  -u https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/manifest

cd .repo
git clone git@github.com:aohp-os/local_manifests.git
cd ..

# Tsinghua mirror limits concurrency; -j4 is recommended
repo sync -j4
```

Successful sync looks like:

```bash
$ repo sync -j4
Syncing: 100% (1011/1011), done in 5h54m50.146s
repo sync has finished successfully.
```

### Download AOHP Agent Driver

```bash
cd aohp-app
git clone git@github.com:aohp-os/AOHPAgentDriverApp.git
```

Build AOHP Agent Driver in Android Studio and place the APK at: `AOSP/packages/apps/AOHPAgentDriver/AOHPAgentDriver.apk`.

---

## 2. Build & Run Cuttlefish

### Build

If you updated AOHP Agent Driver, build the APK in Android Studio and replace:

`AOSP/packages/apps/AOHPAgentDriver/AOHPAgentDriver.apk`

Then compile:

```bash
# from aohp root
bash scripts/build.sh
```

### Launch the image

> To run multiple VMs on one host, assign distinct **instance numbers** to avoid port conflicts.

#### Environment & lunch target

```bash
cd AOSP

source build/envsetup.sh
lunch aosp_cf_x86_64_phone_aohp-trunk_staging-userdebug
```

#### Stop an existing VM (before relaunch)

```bash
"$ANDROID_HOST_OUT"/bin/stop_cvd

# No output means the VM has stopped
ps -u "$USER" -f | grep -E '[c]rosvm|[r]un_cvd'
```

#### Start Cuttlefish

**Default instance (instance 1):**

```bash
sudo -E bash -c 'ulimit -n 65536; '"$ANDROID_HOST_OUT"'/bin/launch_cvd --report_anonymous_usage_stats=n' &
```

**Instance 2:**

```bash
sudo -E bash -c 'export CUTTLEFISH_INSTANCE=2; ulimit -n 65536; '"$ANDROID_HOST_OUT"'/bin/launch_cvd --report_anonymous_usage_stats=n' &
```

### Multiple instances & ports

Web console port: `sig_server_port = 8443 + instance_num - 1`


| Instance | URL                                                |
| -------- | -------------------------------------------------- |
| 1        | [https://localhost:8443/](https://localhost:8443/) |
| 2        | [https://localhost:8444/](https://localhost:8444/) |


### Sandbox mode (high resources)

For sandbox workloads, allocate more CPU, memory, and data partition:

```bash
sudo -E bash -c 'ulimit -n 65536; '"$ANDROID_HOST_OUT"'/bin/launch_cvd \
  --report_anonymous_usage_stats=n \
  --cpus=12 \
  --memory_mb=12288 \
  --blank_data_image_mb=20480 \
  --data_policy=resize_up_to \
  --setupwizard_mode=DISABLED \
  --guest_enforce_security=false \
  --daemon'
```

For instance 2, prefix with `export CUTTLEFISH_INSTANCE=2;`.

For a cold boot (no resume), add `--resume=false`:

```bash
sudo -E bash -c 'ulimit -n 65536; '"$ANDROID_HOST_OUT"'/bin/launch_cvd \
  --report_anonymous_usage_stats=n \
  --cpus=12 \
  --memory_mb=12288 \
  --blank_data_image_mb=20480 \
  --setupwizard_mode=DISABLED \
  --guest_enforce_security=false \
  --resume=false \
  --daemon'
```

---

## 3. VM networking

> The guest is preconfigured to reach the network via the host.

First, change WAN in `./scripts/bridge_network.sh` to your local network interface name.

Then, from `aohp` root:

```bash
# default instance 1
./scripts/bridge_network.sh

# instance 2
./scripts/bridge_network.sh setup 2

# specify NIC (multiple interfaces, wired/VPN, or new host)
./scripts/bridge_network.sh setup wlp10s0 2
```

---

## 4. Modify & submit code

### Check local changes

```bash
bash scripts/check_dirty_repos.sh
```

### Submit to an existing aohp-os repo

If the project already exists under `aohp-os` and your local tree tracks it, open a Pull Request against that repository.

### First-time submission for a new project

Example: modifying `build/make/core/build_id.mk`.

**1. Create the repo under aohp-os**

External contributors cannot create org repos directly. File a request at [local_manifests Issues](https://github.com/aohp-os/local_manifests/issues).

**2. Push your branch**

```bash
cd build/make/

git remote -v
git remote add aohp git@github.com:aohp-os/build_make.git

git switch -c main
git add core/build_id.mk
git commit -m "Update build_id to AOHP-1.0"
git push -u aohp main
```

**3. Update local_manifests**

Add the matching `<project>` / `<remove-project>` entries in [local_manifests](https://github.com/aohp-os/local_manifests) `aohp.xml`, including any `linkfile` entries, then push.

### Sync upstream changes

To sync the latest upstream code for a project into your local tree, use `repo sync` for that project, or run `git pull` inside the corresponding subdirectory.

---

## Related repositories


| Repository                                                    | Description                       |
| ------------------------------------------------------------- | --------------------------------- |
| [local_manifests](https://github.com/aohp-os/local_manifests) | AOHP custom manifests             |
