<h1 align="center">AOHP：Android Open Harness Project</h1>

<p align="center">
  <strong>面向个性化、高效与安全交互的开源 OS 级智能体基座</strong>
</p>

<p align="center">
  <strong>当今操作系统服务于人类 👨‍💻。明日的用户将是智能体 🤖。</strong>
</p>

**🎬 [观看演示](#real-world-demos)**：仅需一句自然语言意图即可生成用户定义应用（UDA）；亦可观看 OpenClaw 智能体通过 AOHP 的 CLI、结构化 UI 与虚拟显示服务完成真实移动任务——附带实时执行悬浮窗录屏。

<p align="center">
  <a href="https://github.com/aohp-os/"><img src="https://img.shields.io/badge/Organization-AOHP--OS-blue?style=for-the-badge" alt="Organization"></a>
  <a href="#real-world-demos"><img src="https://img.shields.io/badge/Demos-6_Live_Recordings-green?style=for-the-badge" alt="Demos"></a>
  <a href="#evaluation-highlights"><img src="https://img.shields.io/badge/Benchmark-90%25_Task_Success-brightgreen?style=for-the-badge" alt="Benchmark"></a>
  <a href="#"><img src="https://img.shields.io/badge/Paper-Technical%20Report-orange?style=for-the-badge" alt="Paper"></a>
  <a href="../LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-yellow?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="https://source.android.com/"><img src="https://img.shields.io/badge/Platform-Android%20(AOSP)-green" alt="Platform"></a>
  <a href="https://github.com/openclaw/openclaw"><img src="https://img.shields.io/badge/Agent-OpenClaw-purple" alt="Agent"></a>
</p>

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="DEVELOPMENT.zh-CN.md">开发指南</a> ·
  <a href="DEVELOPMENT.md">Development Guide</a>
</p>

<p align="center">
  <img src="../pic/cartoon_comic.png" alt="AOHP 漫画概览：从人类操作的 Android 到智能体原生操作系统" width="90%"/>
</p>

---

## 为什么需要 AOHP？

AI 智能体正在成为个人计算系统中的主动操作者：调用工具、操控应用、代表用户完成多步任务。然而，现有操作系统仍默认**人类**是主要操作者；当智能体作为长期运行的系统租户时，在效率、安全性与可追责性上都会出现根本性错配。

**AOHP** 通过将 Android 重设计为**智能体原生（agent-native）运行环境**来应对这一问题。AOHP 并不取代既有应用生态，而是在保留 Android 硬件支持、开源框架与应用兼容性的同时，增加一组系统机制，使服务能够被系统级智能体**调用、组合、个性化、高效执行并接受审计**。

### 传统 Android 与 AOHP 对比

原生 Android 以人为中心：用户在**孤立的应用孤岛**间手动导航、串行交互，底层是面向人类操作的 OS 基座。AOHP 引入**用户定义的任务型应用**、负责理解、规划、编排、执行与监控的 **OS 智能体**，以及 API、CLI、结构化 UI、渲染 GUI 等多接口调用能力和**跨应用服务组合**机制，将系统从「应用优先」转向「智能体原生、面向服务」。

<p align="center">
  <img src="../pic/comparison.png" alt="传统 Android 与 AOHP 架构对比" width="90%"/>
</p>

### 示例：同一购物任务，两种体验

以用户意图 *「帮我找一双 80 美元以内最好的跑鞋」* 为例：在原生 Android 上，用户需要依次打开 Amazon、Temu、eBay、浏览器和备忘录，反复切换应用、操作 GUI、复制粘贴；流程串行、碎片化且容易出错。在 AOHP 上，系统提供**个性化购物入口**，用户面对单一任务界面；OS 智能体理解意图、**并行**编排电商、优惠与配送等服务，在完成策略检查后返回结果。

<p align="center">
  <img src="../pic/demo.png" alt="原生 Android 与 AOHP 购物任务对比" width="90%"/>
</p>

---

## 核心设计原则

| 维度 | 原生 Android | AOHP |
|------|-------------|------|
| **主要用户** | 占据单一视觉注意流的人类操作者 | 与人类并列的一等系统租户：AI 智能体 |
| **交互界面** | 为人类感知渲染的、应用定义的固定 GUI | 个性化服务入口、API、CLI 与结构化 UI |
| **执行模型** | 绑定物理屏幕的单租户前台执行 | 与屏幕解耦的并行后台交互 |
| **系统记忆** | 碎片化、锁死在各应用内部 | 由 OS 管理的跨应用记忆，支撑任务个性化 |
| **安全与隐私** | 粗粒度应用权限；不透明数据流 | 细粒度数据流污点追踪与敏感值沙箱 |

---

## 三大核心能力

### 1. 个性化用户交互

AOHP 使操作系统能够为每位用户生成并运行**个性化服务入口**。用户无需在多个应用间手动切换，即可通过任务级界面聚合跨应用、跨服务的能力。

- **生成式服务入口** — 由 OS 管理的服务组合支撑的任务导向界面
- **能力发现** — 通过 API、CLI 与 GUI 通道实现跨应用服务组合
- **跨服务个性化** — 跨越应用边界的 OS 级记忆

### 2. 高效智能体接口

AOHP 将智能体执行与硬件约束解耦，并缩小系统状态与模型理解之间的语义鸿沟。

- **并行后台交互** — 轻量虚拟显示，支持多应用并发执行
- **智能体感知 UI 增强** — 结构化 UI 表示，降低冗余、丰富语义
- **原生沙箱运行时** — OS 管理的代码执行、数据处理与长驻服务载体
- **统一文件快捷方式** — 在 OS 边界将文件作为一等任务对象处理
- **事件流抽象** — 对瞬时通知与传感器数据的统一订阅接口

### 3. 安全信息流

AOHP 减少不必要的明文暴露，同时保留智能体完成合法任务的能力。

- **策略执行** — 基于运行时数据流、带细粒度语义上下文的策略
- **敏感源净化** — 默认通过类型化占位符保护（如 `<payment-card: uuid>`）
- **可信保险库与执行** — 由可信执行器中介敏感操作，避免向智能体暴露明文
- **数据流污点追踪** — 端到端污点传播，在系统边界强制策略

---

## 系统架构

<p align="center">
  <img src="../pic/overview.png" alt="AOHP 系统架构" width="85%"/>
</p>

AOHP 中的任务通常经历五个阶段：

1. **意图表达** — 用户通过生成入口、既有应用或系统命令表达意图
2. **能力解析** — OS 智能体结合描述符与系统记忆，将意图解析为可用服务能力
3. **执行路径选择** — API/CLI 调用、结构化 UI 操作，或渲染 GUI 回退
4. **策略中介** — 所有敏感输入与状态变更操作经策略与追踪层
5. **记忆与审计** — 任务轨迹与结果作为系统级记忆，用于个性化与审计

---

<a id="real-world-demos"></a>

## 🎬 真实系统演示

AOHP 不仅是设计方案——它以可运行的 AOSP 分支形式落地，内置 **AOHPAgentDriver**、**OpenClaw**、**skills** 以及**用户定义应用（UDA）**生成器。以下为真实系统录屏。

### 用户定义应用 — 从意图到可安装应用

向 AOHP 提供自然语言意图，即可生成完整应用——PRD、设计规格、前端与后端——并可直接安装到设备上。

<table align="center">
<tr>
<td align="center" width="33%"><strong>Health Hub</strong><br><sub>统一健身与睡眠看板</sub></td>
<td align="center" width="33%"><strong>Gift Picker</strong><br><sub>520 奢侈品礼物推荐</sub></td>
<td align="center" width="33%"><strong>Python Learning Assistant</strong><br><sub>少儿编程学习助手</sub></td>
</tr>
<tr>
<td align="center"><a href="../demos/uda/health_hub_demo.mp4"><img src="../demos/uda/health_hub_demo.gif" alt="Health Hub 演示" width="260"/></a></td>
<td align="center"><a href="../demos/uda/gift_picker_demo.mp4"><img src="../demos/uda/gift_picker_demo.gif" alt="Gift Picker 演示" width="260"/></a></td>
<td align="center"><a href="../demos/uda/python_learning_assistant_demo.mp4"><img src="../demos/uda/python_learning_assistant_demo.gif" alt="Python Learning Assistant 演示" width="260"/></a></td>
</tr>
<tr>
<td align="center"><sub>Aggregate fitness and sleep records from Huawei Health, and weight data from Mi Fitness, to generate a unified health management app. The app should be in English and support both portrait and landscape layouts.</sub></td>
<td align="center"><sub>A gift selection app for romantic occasions like 520, helping users choose luxury items (Chanel/Gucci perfumes, Dior bags, Tiffany/VCA necklaces) for their girlfriends, featuring both portrait and landscape responsive layouts.</sub></td>
<td align="center"><sub>My son recently started primary school, and I want him to learn programming (Python). Please help me generate a Python learning App, including knowledge point explanations, exercises, interactive practice, and learning progress. Please use English for the app generation, and it can include both landscape and portrait versions.</sub></td>
</tr>
</table>

### 智能体执行 — AOHP 上的 OpenClaw

基准测试通过 **AOHPAgentDriver** 调起 **OpenClaw**，将 AOHP 服务封装为 **skills**。以下录屏展示智能体在真实 AOHP 设备上的执行过程。

<table align="center">
<tr>
<td align="center" width="33%"><strong>UI 微操作</strong></td>
<td align="center" width="33%"><strong>文件处理</strong></td>
<td align="center" width="33%"><strong>事件捕获</strong></td>
</tr>
<tr>
<td align="center"><a href="../demos/agent/gallery_brightness.mp4"><img src="../demos/agent/gallery_brightness.gif" alt="UI 微操作演示" width="260"/></a></td>
<td align="center"><a href="../demos/agent/cloud_file_markor.mp4"><img src="../demos/agent/cloud_file_markor.gif" alt="文件处理演示" width="260"/></a></td>
<td align="center"><a href="../demos/agent/taskdriver_calendar.mp4"><img src="../demos/agent/taskdriver_calendar.gif" alt="事件捕获演示" width="260"/></a></td>
</tr>
</table>

---

<a id="evaluation-highlights"></a>

## 评测亮点

我们使用 [OpenClaw](https://github.com/openclaw/openclaw) 智能体，在 10 项代表性任务上对比 AOHP 与原生 Android：

| 指标 | 提升 |
|------|------|
| 任务完成率 | **↑46.7%** |
| 工具调用次数 | **↓65.6%** |
| 耗时 | **↓72.2%** |
| Token 消耗 | **↓73.9%** |
| LLM 请求次数 | **↓68.5%** |

---

## 快速开始

AOHP 基于 AOSP 构建，通过统一的 **[aohp](https://github.com/aohp-os/aohp)** 开发框架进行开发与编译。本仓库为项目文档主页；源码分布在 `aohp-os` GitHub 组织下，经 [local_manifests](https://github.com/aohp-os/local_manifests) 注入到 AOSP 树中。

### 简要流程

```bash
# 1. 克隆开发框架
git clone git@github.com:aohp-os/aohp.git
cd aohp

# 2. 初始化 AOSP + AOHP manifest（镜像/代理选项见开发指南）
cd AOSP && repo init -b android-latest-release
cd .repo && git clone git@github.com:aohp-os/local_manifests.git && cd ..
repo sync -j4

# 3. 编译
bash scripts/build.sh

# 4. 启动 Cuttlefish（需先 envsetup + lunch）
source AOSP/build/envsetup.sh
lunch aosp_cf_x86_64_phone_aohp-trunk_staging-userdebug
sudo -E bash -c 'ulimit -n 65536; '"$ANDROID_HOST_OUT"'/bin/launch_cvd --report_anonymous_usage_stats=n' &
```

在浏览器打开 **https://localhost:8443/** 访问虚拟机（实例号 1）。

### 完整开发教程

环境搭建、网络配置、多实例 Cuttlefish、沙盒模式与代码提交流程详见：

| 文档 | 说明 |
|------|------|
| **[开发指南](DEVELOPMENT.zh-CN.md)** | 完整中文开发教程 |
| **[Development Guide](DEVELOPMENT.md)** | Complete English tutorial |

也可克隆本仓库以阅读项目介绍并关注进展：

```bash
git clone https://github.com/aohp-os/aohp.git
```

---

## 许可证

AOHP 采用 [Apache License, Version 2.0](../LICENSE) 发布。

---

## 引用

```bibtex
@techreport{aohp2026,
  title={AOHP: An Agent-Native Open Fork of Android},
  author={TBD},
  institution={Institute for AI Industry Research (AIR), Tsinghua University},
  year={2026}
}
```

---

<p align="center">
  <i>操作系统不再只是人类操作应用的底座——它成为智能体感知、规划、行动并落实用户意图的环境。</i>
</p>
