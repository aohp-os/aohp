---
name: aohp-file
description: Locate recent files, show paths in the AOHP File Bridge UI, and open Android sharing via the aohp CLI.
metadata: {"openclaw":{"emoji":"📁","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP file bridge

Use this skill when a GUI action may have saved, downloaded, exported, or generated a file on the Android device.

## Best workflow

1. Run the GUI action with file-path reporting enabled: `aohp act ... -F`.
2. Read `files.detected`.
3. If `files.detected` is `true`, use `files.best.devicePath` as the path for follow-up commands.
4. Use `aohp file show-in-folder --path <devicePath> --display <displayId>` to open the containing folder and highlight the path on a chosen screen.
5. Use `aohp file share --path <devicePath> --display <displayId>` to open Android sharing, then continue with `aohp act ...` UI operations.

## CLI examples

```bash
# Tap a node and ask AOHP to report any newly saved file path.
aohp act tap-node -d 2 -i 17 -F

# Long press at a node (context menus, etc.) with file-path reporting.
aohp act long-tap-node -d 2 -i 17 -F

# Tune the scan scope when needed.
aohp act tap-node -d 2 -i 17 -F \
  --file-path-roots downloads,pictures,dcim,documents,screenshots \
  --file-path-mime image/* \
  --file-path-window 30s \
  --file-path-settle 1200ms \
  --file-path-retry-delay 1000ms

# Find recent images independently.
aohp file recent --mime image/* --roots downloads,pictures,dcim --since 30s

# Open the containing folder and highlight the file.
aohp file show-in-folder --path /sdcard/Download/AOHP/example.png --display 2

# Open Android sharing UI.
aohp file share --path /sdcard/Download/AOHP/example.png --display 2
```

## Return shape

When `-F` / `filePathReport` is enabled, `act.*` results include `files`:

```json
{
  "files": {
    "detected": true,
    "best": {
      "devicePath": "/sdcard/Download/example.png",
      "contentUri": "content://media/external/images/media/123",
      "mimeType": "image/png"
    },
    "candidates": []
  }
}
```

If nothing is detected, check `files.reason`, commonly `no_change_in_window`, `partial_timeout`, or `file_bridge_unavailable`.
