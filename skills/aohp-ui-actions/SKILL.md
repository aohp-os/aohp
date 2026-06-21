---
name: aohp-ui-actions
description: Tap, swipe, keys, text, node-targeted actions, and node progress updates on a logical display via the aohp CLI (UI-level injection; not app launch, files, or shell).
metadata: {"openclaw":{"emoji":"👆","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP UI actions

## When to use

- Drive **taps**, **swipes**, **keys**, **text entry**, **node-based** actions, and **node progress updates** on a **logical display** (`displayId`), including virtual displays created for the agent.
- Use `**aohp act tap-node`** / `**aohp act long-tap-node**` / `**aohp act input-node**` when you already have a node `**id**` from `**aohp ui tree**` (integer `**id**` on each node).
- Use `**aohp act set-node-progress**` for a **SeekBar** / slider: **`--value` / `-V`** sets a **concrete raw value** in the widget's own range (for example brightness **-100..100**). **`--percent` / `-P`** sets **where you are along the full span** as **0–100** (not that raw number); once you know **`rangeMin`** and **`rangeMax`**, the implied raw value is approximately **`rangeMin + (rangeMax - rangeMin) * (P / 100)`** (same as **`(rangeMax - rangeMin) * (P / 100) + rangeMin`**).

## Text input: `act.input` / `act.input_node`

Both commands focus a field (already focused for `**aohp act input**`, or tap-then-type for `**aohp act input-node**`), then apply **`--mode` / JSON `inputMode`**:

| Mode | Behavior |
|------|----------|
| **`replace`** (default) | Clears the field, then commits text. **`-N` / JSON `clearCount`** is ignored (kept for compatibility). |
| **`append`** | Send **MOVE_END**, then commit text (appends after existing content). |
| **`prepend`** | Send **MOVE_HOME**, then commit text (inserts before existing content). |

To clear without typing: **`aohp act clear -d <displayId>`** → **`act.clear`** (clears the **focused** editable; optional **`-f` / `flags`** for the accessibility dump path). To clear a specific node's field: **`aohp act clear-node -d <id> -i <nodeId>`** → **`act.clear_node`** (tap node, then **ACTION_SET_TEXT** on that **nodeId**).

## Workflow

1. **`aohp ui tree -d <displayId> [-f]`** (or **`aohp ui-tree …`**) to read node **`id`**, **`bounds`**, text/description/resource-id, and action states from the compact HTML output. Add **`-o` / `--origin`** only when you need the full origin JSON.
2. Run `**aohp act …**` with the **same** `**-d` / `--display`**.
3. Fetch the tree again after navigation or large UI changes.

**Compared to screen coordinates** (e.g. bottom-right FAB), prefer **`aohp act tap-node`** / **`act input-node`** with ids from a fresh tree.

## Examples (copy-paste CLI)

```bash
# Tap (-t = press duration in ms)
aohp act tap -d 0 -x 540 -y 960 -t 50

# Type into the focused field (default: replace = clear then type)
aohp act input -d 0 -t "hello"
aohp act input -d 0 -t "suffix" -m append
aohp act input -d 0 -t "prefix" -m prepend
aohp act clear -d 0

# Tap by node id from ui tree (-f is a tree flag bitmask; 0 is usually enough)
aohp act tap-node -d 0 -i 42 -f 0

# Long press at node center (-t = hold duration in ms, same as act long-tap)
aohp act long-tap-node -d 0 -i 42 -f 0 -t 800

# Add -F / --file-path-report when the action may save/download/export a file.
# The result then includes files.detected and, when found, files.best.devicePath.
aohp act tap-node -d 0 -i 42 -F
aohp act long-tap-node -d 0 -i 42 -F

# Type into a specific node (default: replace; -m append | prepend)
aohp act input-node -d 0 -i 42 -t "hello" -f 0
aohp act input-node -d 0 -i 42 -t "more" -m append -f 0
aohp act clear-node -d 0 -i 42 -f 0

# Swipe / drag (same subcommand); endpoints -x1/-y1/-x2/-y2, duration -t
aohp act swipe -d 0 -x1 100 -y1 500 -x2 100 -y2 200 -t 300
aohp act swipe -d 0 -x1 100 -y1 200 -x2 100 -y2 500 -t 300

# Set a SeekBar / slider to a concrete raw value (native ACTION_SET_PROGRESS).
# Useful when the range is not 0–100, e.g. brightness -100..100. Without
# --range-min/--range-max, the CLI probes the node range first.
aohp act set-node-progress -d 0 -i 42 -V -25.0

# If you already know the range, pass it to avoid the extra probe action:
aohp act set-node-progress -d 0 -i 42 -V -25.0 --range-min -100 --range-max 100

# Set by position along the span: -P is 0–100 (not the raw SeekBar number).
# Implied raw ≈ rangeMin + (rangeMax - rangeMin) * (P/100) when min/max are known.
aohp act set-node-progress -d 0 -i 42 -P 75.0

# Raw JSON-RPC only carries percent (0–100 along the span); same mapping as -P.
aohp call act.set_node_progress '{"displayId":0,"nodeId":42,"percent":75.0}'

# System keys (aliases: act-back, act-home, act-recents)
aohp act back -d 0
aohp act home -d 0
aohp act recents -d 0
# Decimal key code like adb input keyevent; or -K with a name (HOME, APP_SWITCH, VOLUME_UP, …)
aohp act key -d 0 -k 4
aohp act key -d 0 -K HOME
```

## Optional: raw JSON form

Same parameters as the CLI, as JSON:

```bash
aohp call act.tap '{"displayId":0,"x":540,"y":960,"duration":50}'
aohp call act.input '{"displayId":0,"text":"hello","inputMode":"replace","clearCount":512}'
aohp call act.input '{"displayId":0,"text":"x","inputMode":"append"}'
aohp call act.clear '{"displayId":0,"count":40}'
aohp call act.tap_node '{"displayId":0,"nodeId":42,"flags":0}'
aohp call act.long_tap_node '{"displayId":0,"nodeId":42,"flags":0,"duration":800}'
aohp call act.input_node '{"displayId":0,"nodeId":42,"text":"hello","flags":0,"inputMode":"replace"}'
aohp call act.clear_node '{"displayId":0,"nodeId":42,"flags":0,"count":40}'
aohp call act.key '{"displayId":0,"back":true}'
aohp call act.key '{"displayId":0,"keyCode":187}'
aohp call act.key '{"displayId":0,"keyName":"APP_SWITCH"}'
```

## Notes

- Virtual-display workflows depend on AOHP's virtual-display stack on the device; prefer virtual displays you created with `**aohp display create …**`.
- Node-based commands need a fresh `**aohp ui tree**`; if the tree cannot be dumped, the command may fail with an error mentioning virtual display availability—use `**aohp ui tree**` first to confirm.
- Use `**-F` / `--file-path-report**` on `aohp act …` commands when you expect the GUI action to create a file. Do not confuse this with node commands' `**-f` / `--flags**`, which controls UI tree dump flags.

