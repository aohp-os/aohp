---
name: aohp-app-launch
description: List installed packages and start, stop, or inspect apps on a logical display via the aohp CLI.
metadata: {"openclaw":{"emoji":"📲","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP app launch

List packages and start or kill apps on a chosen **logical display** (`displayId`). Package name is always **`-P` / `--package`** (the global **`-p`** flag means **pretty** JSON, not package).

## When to use

- Enumerate packages, query one package, start or kill an app, read foreground package, or list running processes—all through **`aohp app …`**.

## Commands

| Goal | CLI |
|------|-----|
| List all packages | **`aohp app list`** (similar idea to **`pm list packages`**) |
| List third-party packages only | **`aohp app list -3`** or **`aohp app list --third-party`** (similar idea to **`pm list packages -3`**) |
| Package details | **`aohp app info -P <package>`** |
| Start app launcher activity | **`aohp app start -P <package> [-d <displayId>]`** |
| Start with an Android intent | **`aohp call app.start '{"packageName":"<pkg>","action":"<action>","data":"<uri>","mimeType":"<type>"}'`** (omit `action`/`data` to launch launcher only) |
| Force-stop app | **`aohp app kill -P <package> [-d <displayId>]`** |
| Foreground package | **`aohp app foreground [-d <displayId>]`** |
| Running snapshot | **`aohp app running`** |

Alias: **`aohp app-list`** → **`aohp app list`**.

## Examples

```bash
aohp app list -3
aohp app start -P com.android.chrome -d 2
aohp app start -P com.android.camera2 -d 0   # opens launcher activity only

# Open content in a specific app via intent (not the same as launcher start)
aohp call app.start '{"packageName":"<pkg>","action":"android.intent.action.VIEW","data":"file:///path/to/file","mimeType":"<mime>"}'
```

## Notes

- **`aohp app start -P`** and **`app.start` without `action`/`data`** only launch the app's **launcher activity** (same idea as `monkey -p` / default launch intent).
- To open a **URI** (file, deep link, etc.) in a chosen package, pass **`action`**, **`data`** (or **`dataUri`**), and optionally **`mimeType`** / **`type`** on **`app.start`**.

## Optional: raw JSON form

If you must bypass the subcommand layer:

```bash
aohp call app.start '{"displayId":2,"packageName":"com.android.chrome"}'
```

Method names look like **`app.list`**, **`app.start`**, **`app.info`**, etc.
