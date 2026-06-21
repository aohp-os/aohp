---
name: aohp-perception
description: Screenshots and UI hierarchy (windows/nodes) on a logical display via the aohp CLI.
metadata: {"openclaw":{"emoji":"📸","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP perception

Capture **JPEG** screenshots and read **UI hierarchy** on a **logical display** (`displayId`: integer). The default hierarchy is compact HTML-like text with useful node attributes (`id`, `bounds`, text/desc/resourceId, action states); use **`-o`** only when you need the origin JSON.

Requires **`aohp`** on `PATH` (how it reaches the device is already set in the packaged **`aohp`** you run).

## When to use

- Screenshot the whole display, a rectangle, or a single node’s bounds: **`aohp shot full`**, **`aohp shot region`**, **`aohp shot node`**.
- Read or filter the UI tree: **`aohp ui tree`**, **`aohp ui find`**.
- Prefer the subcommands above. Use **`aohp call <method> '<json>'`** only if you need JSON fields the high-level commands do not expose; method names look like **`<area>.<action>`** (e.g. **`ui.tree`**, **`shot.full`**).

## Workflow

- **UI hierarchy:** run **`aohp ui tree -d <displayId>`** whenever you need node **`id`**, **`bounds`**, text, description, resource id, or action states. Default output is compact HTML; add **`-o` / `--origin`** only when you need the full origin JSON. **`aohp ui find`** matches nodes by text / description / resource-id when that is enough.
- **Screenshots:** run **`aohp shot …`** whenever you need pixels. By default each shot writes a JPEG under **`$TMPDIR`** and prints a **short** JSON wrapper (see below)—use that path for vision tools.
- Quote arguments that contain spaces or shell metacharacters when the command runs inside **`exec`**.

## Commands (summary)

| Goal | CLI |
|------|-----|
| Full-screen JPEG | **`aohp shot full -d <id> [-q 1-100]`** — default save under **`$TMPDIR`** as **`aohp_shot_full_<timestamp>.jpg`**; **`-O`** sets the local path; **`--inline`** alone does **not** write or retain a local JPEG—pixels appear in stdout as a single **`type: "image"`** block; **`-O` + `--inline`** writes the file **and** adds **`type: "image"`** after the save-path text |
| Cropped JPEG | **`aohp shot region …`** — same modes (default prefix **`aohp_shot_region_`**) |
| Node bounds JPEG | **`aohp shot node …`** — same modes (default prefix **`aohp_shot_node_`**) |
| UI tree | **`aohp ui tree -d <id> [-f flags]`** — compact HTML; **`-o` / `--origin`** returns the full origin JSON |
| Filter nodes | **`aohp ui find -d <id> [--raw] [-s text] [-D desc] [-R resource-id]`** |
| Stubs | **`aohp ui focused`**, **`aohp ui input-text`** (may be placeholders on some agents) |

Alias: **`aohp ui-tree`** → **`aohp ui tree`**.

## Output shape for **`aohp shot …`** (success)

Stdout is **one JSON object** with **`content`** (array) and **`details`** (object). When a local file is written, the first **`content`** item is **`type: "text"`** (includes **`Saved image bytes to …`** plus a short completion line). With **`--inline`** and no **`-O`**, **`content`** contains only the **`type: "image"`** block.

| Invocation | Local JPEG file | **`type: "image"`** in **`content`** |
|--------------|-----------------|---------------------------------------|
| Default or **`-O`** only | Yes (default under **`$TMPDIR`** or your **`-O`** path) | **No** — keeps **`exec`** output small |
| **`--inline`** only | **No** | **Yes** — the only content block; raw base64 in **`data`**, **`mimeType`** set |
| **`-O`** and **`--inline`** together | Yes, at your **`-O`** path | **Yes** — second block after save-path text |

**`details`**: fields from the agent reply **except** the duplicated huge **`base64`** string; **`details.path`** (when present) is the **device-side** capture path, not necessarily the path where you saved bytes locally—the local path is only in the **`text`** line above.

**`aohp call …`** for shot-related methods returns the **plain agent JSON** (not this wrapper), which is useful for automation but different from **`aohp shot …`** stdout.

## Examples

```bash
aohp ui tree -d 0
aohp ui tree -d 0 -o
aohp shot full -d 0 -q 85
aohp shot full -d 0 -O /tmp/cap.jpg
aohp shot full -d 0 --inline
aohp shot full -d 0 -O /tmp/cap.jpg --inline
```
