# AOHP 开发指南

本文档介绍如何搭建 AOHP 开发环境、编译并在 Cuttlefish 虚拟机上运行系统，以及如何提交代码贡献。

[English](DEVELOPMENT.md) | [返回项目主页](README.zh-CN.md)

---

## 目录

- [前置要求](#前置要求)
- [1. 初始化](#1-初始化)
  - [下载统一的开发框架](#下载统一的开发框架)
  - [初始化 AOSP 源码](#初始化-aosp-源码)
- [2. 编译与运行 Cuttlefish](#2-编译与运行-cuttlefish)
  - [编译代码](#编译代码)
  - [启动镜像](#启动镜像)
  - [多实例与端口](#多实例与端口)
  - [沙盒环境（高配置）](#沙盒环境高配置)
- [3. 虚拟机网络配置](#3-虚拟机网络配置)
- [4. 修改与提交代码](#4-修改与提交代码)
  - [检查本地修改](#检查本地修改)
  - [非首次提交（已有 aohp-os 仓库）](#非首次提交已有-aohp-os-仓库)
  - [首次提交新 project](#首次提交新-project)
  - [同步上游最新代码](#同步上游最新代码)

---

## 前置要求

- **操作系统**：推荐 Linux（Cuttlefish 官方支持环境）
- **磁盘空间**：完整 AOSP 同步与编译需要数百 GB 可用空间
- **网络**：可访问 Google 源；也可使用清华镜像（见下文）
- **权限**：启动 Cuttlefish 需要 `sudo`

---

## 1. 初始化

### 下载统一的开发框架

```bash
git clone git@github.com:aohp-os/aohp.git
cd aohp
```

如需定制 [AOHPAgentDriver](https://github.com/aohp-os/AOHPAgentDriverApp)，可将其 clone 到 `aohp-app/` 目录下。

### 初始化 AOSP 源码

> **重要**：必须完整同步全部源码，否则后续编译会失败。

在 `aohp` 目录下进入 `AOSP/`，选择以下任一方式初始化 manifest。

#### 方式 A：Google 官方源

需要配置可访问 Google 源的代理。

```bash
cd AOSP

# 初始化 manifest（会从 Google 源 clone）
repo init -b android-latest-release

# 加载 AOHP 的 local_manifests
cd .repo
git clone git@github.com:aohp-os/local_manifests.git
cd ..

# 开始同步（-j4 表示 4 线程，可按 CPU 核数调整）
repo sync -j4
```

#### 方式 B：清华 AOSP 镜像

大部分仓库走清华源，少量 AOHP 定制仓库仍从 GitHub `aohp-os` 拉取，需为代理配置相应规则。

```bash
cd AOSP

repo init -b android-latest-release \
  -u https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/manifest

cd .repo
git clone git@github.com:aohp-os/local_manifests.git
cd ..

# 清华源有并发限制，推荐 -j4
repo sync -j4
```

同步成功时终端输出类似：

```bash
$ repo sync -j4
Syncing: 100% (1011/1011), done in 5h54m50.146s
repo sync has finished successfully.
```

### 下载 AOHP Agent Driver

```bash
cd aohp-app
git clone git@github.com:aohp-os/AOHPAgentDriverApp.git
```

通过 Android Studio 编译 AOHP Agent Driver，并将安装包放置在：`AOSP/packages/apps/AOHPAgentDriver/AOHPAgentDriver.apk`。

---

## 2. 编译与运行 Cuttlefish

### 编译代码

若更新了 AOHP Agent Driver，需先在 Android Studio 中 build 出 APK，并替换到：

`AOSP/packages/apps/AOHPAgentDriver/AOHPAgentDriver.apk`

然后执行编译：

```bash
# 在 aohp 根目录
bash scripts/build.sh
```

### 启动镜像

> 若同一台主机需启动多个虚拟机，请通过**实例号**区分，避免端口冲突。

#### 激活环境与选择机型

```bash
cd AOSP

source build/envsetup.sh
lunch aosp_cf_x86_64_phone_aohp-trunk_staging-userdebug
```

#### 关闭已有虚拟机（再次启动前）

```bash
# 仅关闭当前实例
"$ANDROID_HOST_OUT"/bin/stop_cvd

# 确认已停止（无输出表示已关闭）
ps -u "$USER" -f | grep -E '[c]rosvm|[r]un_cvd'
```

#### 启动 Cuttlefish

**默认实例（实例号 1）：**

```bash
sudo -E bash -c 'ulimit -n 65536; '"$ANDROID_HOST_OUT"'/bin/launch_cvd --report_anonymous_usage_stats=n' &
```

**指定实例号（如 2）：**

```bash
sudo -E bash -c 'export CUTTLEFISH_INSTANCE=2; ulimit -n 65536; '"$ANDROID_HOST_OUT"'/bin/launch_cvd --report_anonymous_usage_stats=n' &
```

### 多实例与端口

不同实例号对应不同 Web 控制台端口，规则为：

`sig_server_port = 8443 + instance_num - 1`


| 实例号 | 访问地址                                               |
| --- | -------------------------------------------------- |
| 1   | [https://localhost:8443/](https://localhost:8443/) |
| 2   | [https://localhost:8444/](https://localhost:8444/) |


### 沙盒环境（高配置）

若需使用沙盒环境，建议为虚拟机分配更高 CPU / 内存 / 数据分区：

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

实例号 2 时加上 `export CUTTLEFISH_INSTANCE=2;`。

若需每次冷启动（不恢复上次状态），增加 `--resume=false`：

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

## 3. 虚拟机网络配置

> 虚拟机内已配置可通过主机访问网络的接口。

首先，需要将 `./scripts/bridge_network.sh` 中的 WAN 修改为本机网卡名。

然后，在 `aohp` 根目录执行：

```bash
# 默认实例号 1
./scripts/bridge_network.sh

# 指定实例号（如 2）
./scripts/bridge_network.sh setup 2

# 指定网卡（多网卡、有线/VPN、或更换 Linux 主机时）
./scripts/bridge_network.sh setup wlp10s0 2
```

---

## 4. 修改与提交代码

### 检查本地修改

查看所有 git 子仓库的脏状态：

```bash
bash scripts/check_dirty_repos.sh
```

### 非首次提交（已有 aohp-os 仓库）

若对应 project 已在 `aohp-os` 组织中创建，且本地已关联远程仓库，直接向对应仓库提交 Pull Request 即可。

### 首次提交新 project

以修改 `build/make/core/build_id.mk`为例：

**1. 在 aohp-os 组织创建仓库**

外部开发者无法直接在组织中创建仓库。请在 [local_manifests Issues](https://github.com/aohp-os/local_manifests/issues) 提出申请，由组织成员创建对应 repo。

**2. 推送修改到 aohp-os 远程**

```bash
cd build/make/

git remote -v
git remote add aohp git@github.com:aohp-os/build_make.git

git switch -c main
git add core/build_id.mk
git commit -m "Update build_id to AOHP-1.0"
git push -u aohp main
```

**3. 更新 local_manifests**

在 [local_manifests](https://github.com/aohp-os/local_manifests) 的 `aohp.xml` 中添加对应的 `<project>` / `<remove-project>` 条目；若有 `linkfile` 也需一并迁移，然后 push 到远程。

### 同步上游最新代码

将某个 repo 的最新代码同步到本地工作区，针对该 project 使用 `repo sync`，或进入对应子目录执行 `git pull`。

---

## 相关仓库


| 仓库                                                            | 说明               |
| ------------------------------------------------------------- | ---------------- |
| [local_manifests](https://github.com/aohp-os/local_manifests) | AOHP 定制 manifest |

