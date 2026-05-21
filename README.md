<h1 align="center">AOHP: An Open Fork of Android for Agent-Native System Redesign</h1>

<p align="center">
  <strong>Android Open Harness Project</strong>
</p>

<p align="center">
  <a href="https://github.com/aohp-os/"><img src="https://img.shields.io/badge/Project-AOHP--OS-blue" alt="Project"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Android%20(AOSP)-green" alt="Platform"></a>
  <a href="#"><img src="https://img.shields.io/badge/Paper-Technical%20Report-orange" alt="Paper"></a>
</p>

<p align="center">
  <a href="doc/README.zh-CN.md">中文文档</a>
</p>


---

## Why AOHP?

AI agents are becoming active operators of personal computing systems: invoking tools, manipulating applications, and completing multi-step tasks on behalf of users. Yet existing operating systems still assume that **humans** are the primary users, creating fundamental mismatches in efficiency, safety, and accountability when agents become long-running system tenants.

**AOHP** addresses this by redesigning Android as an **agent-native operating environment**. Rather than replacing the existing app ecosystem, AOHP preserves Android's hardware support, open-source framework, and application compatibility while adding system mechanisms that make services callable, composable, personalized, efficient, and auditable for OS-level agents.

### Traditional Android vs. AOHP

Stock Android keeps the human at the center: manual navigation across **isolated app silos**, sequential interaction, and a human-oriented OS substrate. AOHP introduces **user-defined task apps**, an **OS agent** that understands, plans, orchestrates, executes, and monitors tasks, multi-interface invocation (API, CLI, structured UI, and rendered GUI), and **cross-app service composition**. The result is a shift from an app-first model to an agent-native, service-oriented system.

<p align="center">
  <img src="./pic/comparison.png" alt="Traditional Android vs AOHP architecture" width="90%"/>
</p>


### Example: one shopping task, two experiences

Consider the intent *"Find me the best running shoes under $80."* On stock Android, the user must move sequentially across Amazon, Temu, eBay, the browser, and Notes, performing repeated GUI operations, copy-paste steps, and app switches. On AOHP, a **personalized shopping entrance** exposes a single task-level interface: the OS agent understands the intent, composes services in **parallel**, applies policy checks, and returns the result.

<p align="center">
  <img src="./pic/demo.png" alt="Stock Android vs AOHP for a shopping task" width="90%"/>
</p>

---

## Key Design Principles

| Dimension | Stock Android | AOHP |
|-----------|--------------|------|
| **Primary User** | Human operators with a single visual attention stream | AI agents as first-class system tenants alongside humans |
| **Interaction Surface** | Fixed, app-defined GUIs rendered for human perception | Personalized service entrances; APIs, CLIs, and structured UIs for agent operation |
| **Execution Model** | Single-tenant foreground execution bound to physical displays | Parallel background interaction decoupled from the screen |
| **System Memory** | Fragmented and locked inside individual applications | OS-managed cross-app memory for task personalization |
| **Security & Privacy** | Coarse-grained app permissions; opaque data flows | Fine-grained data-flow taint tracking and sandboxed sensitive values |

---

## Three Core Capabilities

### 1. Personalized User Interaction

AOHP enables the OS to generate and operate **personalized service entrances** for each user. Instead of manually switching among multiple apps, users interact with task-level interfaces that aggregate capabilities across apps and services.

- **Generated Service Entrances** — Task-oriented interfaces backed by OS-managed service composition
- **Capability Discovery** — Cross-app service composition through API, CLI, and GUI channels
- **Cross-Service Personalization** — OS-level memory that survives app boundaries

### 2. Efficient Agent Interfaces

AOHP decouples agent execution from hardware constraints and narrows the semantic gap between system state and model understanding.

- **Parallel Background Interaction** — Lightweight virtual displays for concurrent multi-app execution
- **Agent-Aware UI Enhancement** — Structured UI representations with reduced redundancy and richer semantics
- **Native Sandbox Runtime** — OS-managed execution substrate for code, data processing, and long-running services
- **Unified File Management** — Files treated as first-class task objects at the OS boundary
- **Event Stream Abstraction** — Unified subscription interface for transient notifications and sensor data

### 3. Secure Information Flow

AOHP reduces unnecessary plaintext exposure while preserving the agent's ability to complete legitimate tasks.

- **Policy Enforcement** — Runtime data-flow-based policies with fine-grained semantic context
- **Sensitive Source Sanitization** — Default protection via typed placeholders (e.g., `<payment-card: uuid>`)
- **Trusted Vault & Execution** — Sensitive operations mediated by a trusted executor without exposing plaintext to the agent
- **Data-Flow Taint Tracking** — End-to-end taint propagation with enforcement at system boundaries

---

## Architecture

<p align="center">
  <img src="./pic/overview.png" alt="AOHP System Architecture" width="85%"/>
</p>

A task in AOHP proceeds through five stages:

1. **Intent Expression** — The user expresses intent through a generated entrance, existing app, or system command
2. **Capability Resolution** — The OS agent resolves intent into service capabilities using descriptors and system memory
3. **Execution Path Selection** — API/CLI invocation, structured UI operation, or rendered GUI fallback
4. **Policy Mediation** — All sensitive inputs and state-changing actions pass through the policy and trace layer
5. **Memory & Audit** — Task traces and outcomes are stored as system-level memory for personalization and auditing

---

## Evaluation Highlights

We evaluate AOHP with [OpenClaw](https://github.com/openclaw/openclaw) agents against stock Android on 10 representative mobile tasks:

| Metric | Improvement |
|--------|-------------|
| Task Completion Rate | **90.0%** vs. 43.3% on stock Android |
| Tool Calls | **−65.6%** |
| Duration | **−72.2%** |
| Token Consumption | **−73.9%** |
| LLM Requests | **−68.5%** |

---

## Getting Started

AOHP is under active development. **Source code, build instructions, and device images are not yet public** and will be published in this repository when ready.

You can clone this repository today to read the documentation and follow project updates:

```bash
git clone https://github.com/aohp-os/aohp.git
```

Build and flashing instructions will be added here once the codebase is released.

---



## License

AOHP is licensed under the [Apache License, Version 2.0](LICENSE).

---


## Citation

```bibtex
@techreport{aohp2026,
  title={AOHP: An Open Fork of Android for Agent-Native System Redesign},
  author={TBD},
  institution={Institute for AI Industry Research (AIR), Tsinghua University},
  year={2026}
}
```

---


<p align="center">
  <i>The OS is no longer only a substrate for human-operated applications — it becomes the environment in which agents perceive, plan, act, and enforce user intent.</i>
</p>
