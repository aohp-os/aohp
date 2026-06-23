<h1 align="center">AOHP：Android Open Harness Project</h1>

<p align="center">
  <strong>让操作系统借助智能体式 AI 适应每一位用户。</strong>
</p>


<p align="center">
  <a href="#real-world-demos"><img src="https://img.shields.io/badge/Demos-Live_Recordings-green?style=for-the-badge" alt="Demos"></a>
  <a href="#evaluation-highlights"><img src="https://img.shields.io/badge/Benchmark-75.56%25_Completion-brightgreen?style=for-the-badge" alt="Benchmark"></a>
  <a href="https://arxiv.org/abs/2606.23449"><img src="https://img.shields.io/badge/Paper-Technical%20Report-orange?style=for-the-badge" alt="Paper"></a>
  <a href="../LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-yellow?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="DEVELOPMENT.md">Development Guide</a> ·
  <a href="DEVELOPMENT.zh-CN.md">开发指南</a>
</p>
**🎬 [观看演示视频](#real-world-demos)**：了解 AOHP 如何生成个性化的用户定义应用，并完成跨应用任务。

---

## 为什么需要 AOHP？

传统操作系统以应用为中心。用户需要在**开发者定义的应用界面**中完成所有操作，过程往往繁琐且容易分散注意力。

AOHP 让操作系统走向更深度的个性化。
它引入**用户定义应用（user-defined apps）**，这类应用根据用户的实际需求生成，并由底层 AI 智能体提供支撑。
智能体在后台调用系统 API、CLI 以及 GUI 应用，组合出真正可用的服务。

为了让这种体验**可行、高效且安全**，系统层与框架层的许多组件需要重新设计，但并非全部。因此我们推出 AOHP，一个操作系统级智能体承载框架（agent harness），用于实现个性化、高效且安全的交互。

<p align="center">
  <img src="../images/comparison.png" alt="传统 Android 与 AOHP 架构对比" width="95%"/>
</p>


> [!IMPORTANT]
> **AOHP 是一个早期阶段的研究原型**。
> 它尚未准备好用于生产部署或安全关键工作负载。
>
> 我们将持续改进可靠性、兼容性与安全覆盖范围。
> 欢迎反馈与贡献。

---

## 设计

AOHP 提供一组高效的智能体接口，并引入安全的信息流追踪机制，二者共同支撑个性化服务组合这一核心能力。系统架构如下：

<p align="center">
  <img src="../images/overview.png" alt="AOHP 系统架构" width="95%"/>
</p>

AOHP 与原生 Android 的对比：

| 维度 | 原生 Android | AOHP |
| ----------------------- | ------------------------------------------------------------- | ------------------------------------------------------------- |
| **交互模型** | 用户直接操作应用定义的工作流 | 智能体作为操作系统中的原生执行主体，根据用户意图行动 |
| **交互界面** | 开发者定义的固定应用 GUI | 由智能体协调的个性化服务入口 |
| **进程执行** | 受物理屏幕约束的单租户前台执行 | 与屏幕解耦的并行后台交互 |
| **系统记忆** | 碎片化、封闭在各个应用内部 | 由操作系统管理的跨应用记忆，用于任务个性化 |
| **安全与隐私** | 粗粒度应用权限与不透明数据流 | 细粒度数据流追踪与敏感值沙箱化 |


---

<a id="real-world-demos"></a>

## 🎬 演示

AOHP 以可运行的 AOSP 分支形式交付。
以下录屏来自编译后的系统镜像。

### 用户定义应用

给定自然语言提示，AOHP 即可生成一个功能完整的应用，包括前端 UI 以及由智能体支撑的后台逻辑。

<table align="center">
<tr>
<td align="center" width="33%"><strong>Health Hub</strong><br><sub>统一的健身与睡眠看板</sub></td>
<td align="center" width="33%"><strong>Gift Picker</strong><br><sub>520 奢侈品礼物推荐</sub></td>
<td align="center" width="33%"><strong>Python Learning Assistant</strong><br><sub>适合儿童的编程辅导</sub></td>
</tr>
<tr>
<td align="center"><a href="../demos/uda/health_hub_demo.mp4"><img src="../demos/uda/health_hub_demo.gif" alt="Health Hub 演示" width="250"/></a></td>
<td align="center"><a href="../demos/uda/gift_picker_demo.mp4"><img src="../demos/uda/gift_picker_demo.gif" alt="Gift Picker 演示" width="250"/></a></td>
<td align="center"><a href="../demos/uda/python_learning_assistant_demo.mp4"><img src="../demos/uda/python_learning_assistant_demo.gif" alt="Python Learning Assistant 演示" width="250"/></a></td>
</tr>
<tr>
<td align="center"><sub>将不同应用中的健身、睡眠与体重记录聚合到统一的健康管理应用中。</sub></td>
<td align="center"><sub>为 520 纪念日生成一个奢侈品礼物挑选应用，并从各类购物应用中查找礼物信息。</sub></td>
<td align="center"><sub>为孩子生成 Python 学习应用，包含课程与练习，追踪进度并每天通过消息向我汇报。</sub></td>
</tr>
</table>

### 智能体执行

AOHP 借助 AI 智能体编排 API、CLI、GUI、记忆、技能等能力，提供个性化服务。

<table align="center">
<tr>
<td align="center" width="33%"><strong>UI 微操作</strong></td>
<td align="center" width="33%"><strong>文件处理</strong></td>
<td align="center" width="33%"><strong>事件捕获</strong></td>
</tr>
<tr>
<td align="center"><a href="../demos/agent/gallery_brightness.mp4"><img src="../demos/agent/gallery_brightness.gif" alt="UI 微操作演示" width="250"/></a></td>
<td align="center"><a href="../demos/agent/cloud_file_markor.mp4"><img src="../demos/agent/cloud_file_markor.gif" alt="文件处理演示" width="250"/></a></td>
<td align="center"><a href="../demos/agent/taskdriver_calendar.mp4"><img src="../demos/agent/taskdriver_calendar.gif" alt="事件捕获演示" width="250"/></a></td>
</tr>
</table>

---

<a id="evaluation-highlights"></a>

## 评测亮点

我们使用 [OpenClaw](https://github.com/openclaw/openclaw) 在 AOHP 与原生 Android 上进行评测。
该基准包含 30 项真实移动端任务，覆盖 GUI 操作、非 GUI 操作、事件捕获、多源信息检索、记忆管理与混合工作流。

### 任务完成率

每项任务按客观检查点评分，部分完成的任务仍可获得部分分数。

| 配置 | 完成率 | 完全解决 | 部分完成 |
| ------- | --------------- | ------------ | ------------------- |
| 原生 Android 上的 OpenClaw | 54.44% | 13 / 30 | 7 / 30 |
| AOHP 上的 OpenClaw | **75.56%** | **20 / 30** | 5 / 30 |
| 提升 | **+21.12%** | **+7 项任务** | - |


### 执行成本

为了公平比较成本，我们报告两个系统都能完整完成的 11 项任务。

| 配置 | 工具调用 | 耗时 | Token 数 | LLM 请求 |
| ------- | ---------- | -------- | ------ | ------------ |
| 原生 Android 上的 OpenClaw | 233 | 33.94 分钟 | 7.10M | 273 |
| AOHP 上的 OpenClaw | **129** | **18.93 分钟** | **3.44M** | **143** |
| 降幅 | **44.64%** | **44.21%** | **51.55%** | **47.62%** |

### 信息流安全

AOHP 也通过面向安全的测试用例进行评测。
系统在全部五项策略用例上均通过：

| 安全检查 | 结果 |
| -------------- | ------ |
| 敏感信息显示使用保险箱引用，而非明文显示 | 通过 |
| 普通的非敏感操作无需额外审批即可执行 | 通过 |
| 敏感转账和付款确认必须获得用户同意 | 通过 |
| 不支持的访问请求默认拒绝 | 通过 |
| 敏感事件会被脱敏处理，并保留污点元数据 | 通过 |

---

## 快速开始

AOHP 基于 AOSP 构建。本仓库托管项目文档与统一的开发框架。
源码位于 `aohp-os` GitHub 组织，通过 [local_manifests](https://github.com/aohp-os/local_manifests) 拉取。

### 快速上手

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

在浏览器中打开 **https://localhost:8443/** 访问虚拟机。

### 完整开发指南

环境搭建、网络配置、多实例 Cuttlefish、沙盒选项与贡献流程详见 **[开发指南](DEVELOPMENT.zh-CN.md)**。

也可以克隆本仓库，阅读项目概览并关注后续更新：

```bash
git clone https://github.com/aohp-os/aohp.git
```

---

## 许可证

AOHP 采用 [Apache License, Version 2.0](../LICENSE) 发布。

---

## 引用

```bibtex
@misc{zhao2026aohp,
      title={AOHP: An Open-Source OS-Level Agent Harness for Personalized, Efficient and Secure Interaction}, 
      author={Shanhui Zhao and Jiacheng Liu and Guohong Liu and Jichao Yan and Jialei Ye and Yuhao Yang and Hao Wen and Shizuo Tian and Yizhen Yuan and Yuxuan Chen and Yunxin Liu and Ju Ren and Ya-Qin Zhang and Chao Huang and Yao Guo and Yuanchun Li},
      year={2026},
      eprint={2606.23449},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2606.23449}, 
}
```

---

<p align="center">
  <i>操作系统不再只是承载人类操作应用的底座——它将成为智能体感知、规划、行动并落实用户意图的环境。</i>
</p>
