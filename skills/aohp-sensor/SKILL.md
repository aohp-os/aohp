---
name: aohp-sensor
description: Capture still photos with the device camera hardware via the aohp CLI (no Camera app UI required).
metadata: {"openclaw":{"emoji":"📷","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP sensor (camera)

Use this skill when a task needs a **real camera photo** saved on the device.

## When to use

- Capture a still photo programmatically without fragile UI automation.

## Commands

| Goal | CLI |
|------|-----|
| Take photo (default back camera) | **`aohp sensor camera capture`** |
| Save to a specific device path | **`aohp sensor camera capture -O /sdcard/Pictures/photo.jpg`** |
| Front camera | **`aohp sensor camera capture -f 1`** |
| Adjust JPEG quality | **`aohp sensor camera capture -q 85`** |

## Default save location

- **`aohp sensor camera capture`** writes to **`/sdcard/DCIM/Camera/IMG_<timestamp>.jpg`** (same folder the stock Camera app uses on AOHP images).
- On success, stdout JSON includes the device path (via **`success` / `stdout`** fields from the agent).

## Examples

```bash
aohp sensor camera capture
aohp sensor camera capture -O /sdcard/Pictures/photo.jpg -q 85
aohp sensor camera capture -f 1
```

## Optional: raw JSON form

```bash
aohp call sensor.camera.capture '{}'
aohp call sensor.camera.capture '{"path":"/sdcard/Pictures/photo.jpg","facing":0,"quality":90}'
```

## Notes

- This is **not** a display screenshot — use **`aohp-perception`** / **`aohp shot full`** for pixels of the current screen.
