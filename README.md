<p align="center">
  <img src="figures/overview.png" alt="AOHP Architecture Overview" width="90%"/>
</p>

<h1 align="center">AOHP: Android Open Harness Project</h1>

<p align="center">
  <strong>An Open Fork of Android for Agent-Native System Redesign</strong>
</p>

<p align="center">
  <a href="https://github.com/aohp-os/"><img src="https://img.shields.io/badge/Project-AOHP--OS-blue" alt="Project"></a>
  <a href="#"><img src="https://img.shields.io/badge/License-TBD-lightgrey" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Android%20(AOSP)-green" alt="Platform"></a>
  <a href="#"><img src="https://img.shields.io/badge/Paper-Technical%20Report-orange" alt="Paper"></a>
  <a href="https://github.com/aohp-os/"><img src="https://img.shields.io/badge/Institute-AIR%2C%20Tsinghua-purple" alt="Institute"></a>
</p>

---

## Why AOHP?

AI agents are becoming active operators of personal computing systems — invoking tools, manipulating applications, and completing multi-step tasks on behalf of users. However, existing operating systems still assume **humans** are the primary users, creating fundamental mismatches in efficiency and safety when agents become long-running system tenants.

**AOHP** addresses this by redesigning Android as an **agent-native operating environment**. Rather than replacing the existing app ecosystem, AOHP keeps Android's hardware support, open-source framework, and app compatibility while adding system mechanisms that make services callable, composable, personalized, efficient, and auditable for OS-level agents.

---

## Key Design Principles

| Dimension | Stock Android | AOHP |
|-----------|--------------|------|
| **Primary User** | Human operators with a single visual attention stream | AI agents as first-class system tenants alongside humans |
| **Interaction Surface** | Fixed, app-defined GUIs rendered for human perception | Personalized service entrances; APIs, CLIs, and structured UIs |
| **Execution Model** | Single-tenant foreground execution bound to physical displays | Parallel background interaction decoupled from the screen |
| **System Memory** | Fragmented and locked inside individual applications | OS-managed cross-app memory for task personalization |
| **Security & Privacy** | Coarse-grained app permissions; opaque data flows | Fine-grained data-flow taint tracking and sandboxed sensitive values |

---

## Three Core Capabilities

### 1. Personalized User Interaction

AOHP lets the OS generate and operate **personalized service entrances** for each user. Instead of manually switching among multiple apps, AOHP exposes task-level interfaces that aggregate capabilities across apps and services.

- **Generated Service Entrances** — Task-oriented shells backed by OS-managed service composition
- **Capability Discovery** — Cross-app service composition through API, CLI, and GUI channels
- **Cross-Service Personalization** — OS-level memory that survives app boundaries

### 2. Efficient Agent Interfaces

AOHP decouples agent execution from hardware constraints and bridges the semantic gap between system states and model comprehension.

- **Parallel Background Interaction** — Lightweight virtual displays for concurrent multi-app execution
- **Agent-Aware UI Enhancement** — Structured UI representations with reduced redundancy and richer semantics
- **Native Sandbox Runtime** — OS-managed execution substrate for code, data processing, and long-running services
- **Unified File Management** — Files as first-class task objects at the OS boundary
- **Event Stream Abstraction** — Unified subscription interface for transient notifications and sensor data

### 3. Secure Information Flow

AOHP minimizes unnecessary plaintext exposure while preserving the agent's ability to complete legitimate tasks.

- **Policy Enforcement** — Runtime data-flow-based policies with fine-grained semantic context
- **Sensitive Source Sanitization** — Default protection via typed placeholders (e.g., `<payment-card: uuid>`)
- **Trusted Vault & Execution** — Sensitive operations mediated by a trusted executor without agent plaintext access
- **Data-Flow Taint Tracking** — End-to-end taint propagation with enforcement at system boundaries

---

## Architecture

<p align="center">
  <img src="pic/overview.png" alt="AOHP System Architecture" width="85%"/>
</p>

A task in AOHP proceeds through five stages:

1. **Intent Expression** — User expresses intent through a generated entrance, existing app, or system command
2. **Capability Resolution** — OS agent resolves intent into service capabilities using descriptors and system memory
3. **Execution Path Selection** — API/CLI invocation, structured UI operation, or rendered GUI fallback
4. **Policy Mediation** — All sensitive inputs and state-changing actions pass through the policy and trace layer
5. **Memory & Audit** — Task traces and outcomes are stored as system-level memory for personalization and auditing

---

## Evaluation Highlights

We evaluate AOHP using [OpenClaw](https://github.com/openclaw/openclaw) agents against stock Android on 10 representative mobile tasks:

| Metric | Improvement |
|--------|-------------|
| Task Completion Rate | **90.0%** vs. 43.3% on stock Android |
| Tool Calls | **−65.6%** |
| Duration | **−72.2%** |
| Token Consumption | **−73.9%** |
| LLM Requests | **−68.5%** |

---

## Getting Started

> Coming soon — AOHP is currently under active development. Stay tuned for build instructions and device images.

```bash
# Clone the repository
git clone https://github.com/aohp-os/aohp.git

# Build instructions (coming soon)
```

---

## Project Structure

```
aohp/
├── frameworks/        # Modified AOSP framework with AOHP security and agent services
├── packages/          # System apps and agent-oriented UI components
├── cli/               # AOHP command-line interface for agent interaction
├── skills/            # Built-in agent skills
├── android/           # SDK, demo apps, and developer tools
├── contrib/           # Reference bridges and integration guides
├── testcases/         # Security and functionality test suites
└── docs/              # Documentation and design references
```

---

## Contributing

We welcome contributions from the community. Please see [doc/CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

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

## Acknowledgments

AOHP is developed at the [Institute for AI Industry Research (AIR)](https://air.tsinghua.edu.cn/), Tsinghua University.

---

<p align="center">
  <i>The OS is no longer only a substrate for human-operated applications — it becomes the environment in which agents perceive, plan, act, and enforce user intent.</i>
</p>
