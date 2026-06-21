---
name: aohp-display
description: List, create, destroy, and focus AOHP virtual displays via the aohp CLI (no MediaProjection).
metadata: {"openclaw":{"emoji":"🖥️","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP display management

Manage **AOHP virtual displays**: list IDs, create or tear down a display, open the launcher on one, or move input focus to an app.

## When to use

- You need a **new logical display** for an agent, or to **tear down** / **inspect** one you no longer need.

## Commands

| Goal | CLI |
|------|-----|
| List displays | **`aohp display list`** — alias **`aohp display-list`** |
| Create virtual display | **`aohp display create [-w <w>] [-h <h>] [-G <dpi>] [-n name] [-f flags]`** — alias **`display-create`**. Long options: **`--width`**, **`--height`**, **`--density`**, **`--name`**, **`--flags`**. Omit **`-w` / `-h` / `-G`** to copy the built-in panel’s size and DPI. |
| Destroy a display | **`aohp display destroy -i <displayId>`** — alias **`display-destroy`** (use **`--id`** on the alias form). |
| Open launcher on a display | **`aohp display launcher -d <displayId> -P <package>`** |
| Focus an app | **`aohp display focus -P <package>`** |

## Examples

```bash
aohp display list
aohp display create -n agent-vd
aohp display create -w 720 -h 1280 -G 320 -n agent-vd
aohp display destroy -i 12
```

## Notes

- Creation uses the system **virtual display** API (no MediaProjection screen-capture prompt). The device image must include AOHP framework support and the permissions bundled for **`aohp`** automation.
