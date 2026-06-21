---
name: uda-app
description: Install and launch user-defined HTML apps (UDA) generated on AOHP devices.
metadata:
  openclaw:
    requires:
      bins:
        - aohp
---

# UDA app launcher

Use after **`aohp-uda`** / `uda.generate` completes (`uda.status` shows `hasApp: true`).

## Install to home screen

```bash
aohp uda install -j <jobId> --pin
```

Registers the app and pins a launcher shortcut on the AOHP home screen.

## Launch without AgentDriver UI

```bash
aohp uda launch -j <jobId>
```

Opens `UdaAppActivity` (WebView + asset loader). Deep link: `aohp-uda://app/<jobId>`.

## Other commands

| Command | RPC |
|---------|-----|
| `aohp uda pin -j <id>` | `uda.pin` |
| `aohp uda uninstall -j <id>` | `uda.uninstall` |
| `aohp uda preview -j <id>` | `uda.preview` (dev HTTP preview) |

Public install registry (for system Launcher integrations): `/data/aohp/shared/uda/registry.json`.
