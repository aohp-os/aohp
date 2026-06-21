# AOHP OpenClaw skills

This directory holds **AgentSkills**-compatible `SKILL.md` folders (OpenClaw-style skill layout) for driving automation on AOHP images via the **`aohp` CLI** (often used from an Alpine chroot; the shipped binary already points at the right service).

## Layout

| Skill folder | Focus |
|--------------|--------|
| `aohp-ui-actions/` | Taps, swipes, keys, text, node-based UI actions |
| `aohp-perception/` | Screenshots and UI trees |
| `aohp-display/` | Virtual display list / create / destroy / launcher / focus |
| `aohp-app-launch/` | Package listing and launch |
| `aohp-sandbox/` | Linux chroot sandboxes |
| `aohp-sys/` | Clipboard, notification shade, outbound SMS, device snippets, wake/sleep/unlock |
| `aohp-event-stream/` | Buffered Toast and notification event stream |
| `aohp-sensor/` | Hardware camera still capture |
| `aohp-uda/` | Generate personalized HTML apps (UDAGen) — idea or structured input |
| `uda-app/` | Install, pin, and launch generated UDA apps |

## Using with OpenClaw

1. Build the CLI and image so **`/usr/local/bin/aohp`** exists in the sandbox.
2. Copy or symlink this folder into OpenClaw’s skills directory, or set **`skills.load.extraDirs`** to point here.
3. Ensure the agent environment exposes the **`aohp`** binary (**`metadata.openclaw.requires.bins`** in each **`SKILL.md`**).

Persistent OpenClaw config/state can live under **`/data/aohp/shared/openclaw-dev`** (bind-mounted into the chroot as **`/opt/openclaw-dev`**) when your image is set up that way.

## CLI surface

The **`aohp`** binary is the automation front-end (transport is built into the build you ship). Common global flags: **`-p/--pretty`**, **`-v/--version`**. Subcommand groups:

| Group | Purpose |
|-------|---------|
| `call`, `connect`, `version` | Arbitrary method call, agent version check, CLI vs agent version |
| `display` | Virtual displays (aliases: `display-list`, `display-create`, `display-destroy`) |
| `app` | Packages and apps (alias: `app-list`) |
| `act` | Gestures and input (aliases: `act-tap`; `act-key` / `act-back` / `act-home` / `act-recents`) |
| `ui` | UI hierarchy (alias: `ui-tree` → `ui tree`) |
| `shot` | Screenshots |
| `sys` | Clipboard, notifications, dumpsys-style snippets, wake/sleep/unlock |
| `sms` | Send outbound SMS (`sms send`) |
| `event` | Register/drain/unregister Toast and notification event streams |
| `sensor` | Hardware sensors (camera still capture) |
| `sandbox` | Sandboxes (aliases: `sandbox-list`, `sandbox-exec`) |

Anything not exposed as a subcommand can still be invoked with **`aohp call <method> '<json>'`**.
