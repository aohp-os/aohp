---
name: aohp-sandbox
description: Create, run commands in, reset, or manage services inside AOHP Linux chroot sandboxes via the aohp CLI.
metadata: {"openclaw":{"emoji":"🐧","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP Linux sandbox

Run **isolated Linux environments** (chroot sandboxes) on the device: create or delete them, run shell commands, reset state, or manage long-running background **services** inside a sandbox.

## When to use

- You need a **named environment** (e.g. **`env-1`**) to run **`exec`** commands, inspect logs, or keep a background process alive inside the sandbox.

## Commands

| Goal | CLI |
|------|-----|
| List sandboxes | **`aohp sandbox list`** — alias **`sandbox-list`** |
| Create | **`aohp sandbox create -n <name> [-t <template>]`** |
| Destroy / reset | **`aohp sandbox destroy -n <name>`** / **`aohp sandbox reset -n <name>`** |
| Run a command | **`aohp sandbox exec <name> [cmd…] [-T <ms>]`** — timeout **`-T` / `--timeout`** — alias **`sandbox-exec`** |
| Start background service | **`aohp sandbox svc-start -n <name> -i <serviceId> -C '<command>'`** |
| Stop service | **`aohp sandbox svc-stop -n <name> -i <serviceId>`** |
| List services | **`aohp sandbox svc-list -n <name>`** |
| Service log tail | **`aohp sandbox svc-log -n <name> -i <id> [-B <bytes>]`** (long form **`--tail-bytes`**) |
| Diagnostics | **`aohp sandbox diag -n <name>`** |

## Examples

```bash
aohp sandbox list
aohp sandbox exec env-1 ls /
aohp sandbox-exec env-1 echo ok
```

## Optional: raw JSON form

```bash
aohp call sandbox.exec '{"name":"env-1","command":"uname -a","timeoutMs":5000}'
```

## Networking

Sandboxes share the device’s network namespace; **`aohp`** inside the chroot uses the same preconfigured connection as on the host in a normal image.
