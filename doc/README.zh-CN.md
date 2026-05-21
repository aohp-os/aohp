<p align="center">
  <img src="../pic/comparison.png" alt="AOHP vs Android" width="85%"/>
</p>

<h1 align="center">AOHP：Android Open Harness Project</h1>

<p align="center">
  <strong>面向智能体原生系统重设计的 Android 开放分支</strong>
</p>

<p align="center">
  <a href="https://github.com/aohp-os/"><img src="https://img.shields.io/badge/Project-AOHP--OS-blue" alt="Project"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Android%20(AOSP)-green" alt="Platform"></a>
  <a href="#"><img src="https://img.shields.io/badge/Paper-Technical%20Report-orange" alt="Paper"></a>
  <a href="https://github.com/aohp-os/"><img src="https://img.shields.io/badge/Institute-AIR%2C%20Tsinghua-purple" alt="Institute"></a>
</p>

<p align="center">
  <a href="../README.md">English</a>
</p>

---

## 为什么需要 AOHP？

AI 智能体正在成为个人计算系统中的主动操作者——调用工具、操控应用、代表用户完成多步任务。然而，现有操作系统仍默认**人类**是主要使用者；当智能体作为长期运行的系统租户时，在效率与安全上会出现根本性错配。

**AOHP** 通过将 Android 重设计为**智能体原生（agent-native）运行环境**来应对这一问题。AOHP 并不取代既有应用生态，而是在保留 Android 硬件支持、开源框架与应用兼容性的同时，增加使服务可被系统级智能体**调用、组合、个性化、高效执行并可审计**的系统机制。

---

## 核心设计原则

| 维度 | 原生 Android | AOHP |
|------|-------------|------|
| **主要用户** | 占据单一视觉注意流的人类操作者 | 与人类并列的智能体，作为一等系统租户 |
| **交互界面** | 为人类感知渲染的、应用定义的固定 GUI | 个性化服务入口；API、CLI 与结构化 UI |
| **执行模型** | 绑定物理屏幕的单租户前台执行 | 与屏幕解耦的并行后台交互 |
| **系统记忆** | 碎片化、锁死在各应用内部 | 由 OS 管理的跨应用记忆，支撑任务个性化 |
| **安全与隐私** | 粗粒度应用权限；不透明数据流 | 细粒度数据流污点追踪与敏感值沙箱 |

---

## 三大核心能力

### 1. 个性化用户交互

AOHP 允许操作系统为每位用户生成并运行**个性化服务入口**。用户无需在多个应用间手动切换，即可通过任务级界面聚合跨应用、跨服务的能力。

- **生成式服务入口** — 由 OS 管理服务组合支撑的任务导向外壳
- **能力发现** — 通过 API、CLI 与 GUI 通道实现跨应用服务组合
- **跨服务个性化** — 跨越应用边界的 OS 级记忆

### 2. 高效智能体接口

AOHP 将智能体执行与硬件约束解耦，并弥合系统状态与模型理解之间的语义鸿沟。

- **并行后台交互** — 轻量虚拟显示，支持多应用并发执行
- **智能体感知 UI 增强** — 结构化 UI 表示，降低冗余、丰富语义
- **原生沙箱运行时** — OS 管理的代码执行、数据处理与长驻服务载体
- **统一文件管理** — 在 OS 边界将文件作为一等任务对象
- **事件流抽象** — 对瞬时通知与传感器数据的统一订阅接口

### 3. 安全信息流

AOHP 在尽量减少不必要明文暴露的同时，保留智能体完成合法任务的能力。

- **策略执行** — 基于运行时数据流、带细粒度语义上下文的策略
- **敏感源净化** — 默认通过类型化占位符保护（如 `<payment-card: uuid>`）
- **可信保险库与执行** — 由可信执行器中介敏感操作，智能体不接触明文
- **数据流污点追踪** — 端到端污点传播，在系统边界强制策略

---

## 系统架构

<p align="center">
  <img src="../pic/overview.png" alt="AOHP 系统架构" width="85%"/>
</p>

AOHP 中的任务通常经历五个阶段：

1. **意图表达** — 用户通过生成入口、既有应用或系统命令表达意图
2. **能力解析** — OS 智能体结合描述符与系统记忆，将意图解析为服务能力
3. **执行路径选择** — API/CLI 调用、结构化 UI 操作，或渲染 GUI 回退
4. **策略中介** — 所有敏感输入与状态变更操作经策略与追踪层
5. **记忆与审计** — 任务轨迹与结果作为系统级记忆，用于个性化与审计

---

## 评测亮点

我们使用 [OpenClaw](https://github.com/openclaw/openclaw) 智能体，在 10 项代表性移动任务上对比 AOHP 与原生 Android：

| 指标 | 提升 |
|------|------|
| 任务完成率 | **90.0%**（原生 Android 为 43.3%） |
| 工具调用次数 | **−65.6%** |
| 耗时 | **−72.2%** |
| Token 消耗 | **−73.9%** |
| LLM 请求次数 | **−68.5%** |

---

## 快速开始

AOHP 正在积极开发中。**源码、构建说明与设备镜像尚未公开**，将在准备就绪后于本仓库发布。

你仍可克隆本仓库以阅读文档并关注项目进展：

```bash
git clone https://github.com/aohp-os/aohp.git
```

源码开放后，构建与刷机说明将补充在本节。

---


## 许可证

AOHP 采用 [Apache License, Version 2.0](../LICENSE) 发布。

---


## 引用

```bibtex
@techreport{aohp2026,
  title={AOHP: An Open Fork of Android for Agent-Native System Redesign},
  author={TBD},
  institution={Institute for AI Industry Research (AIR), Tsinghua University},
  year={2026}
}
```

---

## 致谢

AOHP 由清华大学 [人工智能产业研究院（AIR）](https://air.tsinghua.edu.cn/) 开发。

---

<p align="center">
  <i>操作系统不再只是人类操作应用的底座——它成为智能体感知、规划、行动并落实用户意图的环境。</i>
</p>
