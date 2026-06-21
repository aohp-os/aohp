---
name: aohp-uda
description: Generate personalized HTML apps via UDAGen on AOHP — idea-only or with structured input (requirements, OpenAPI, schemas).
metadata: {"openclaw":{"emoji":"✨","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP User Defined App (UDAGen)

Use this skill when the user wants a **personalized mini-app** (UDA / PUI) generated on the AOHP device.

Pair with **`uda-app`** after generation completes (`hasApp: true`) to install, pin, and launch.

## Prerequisites

1. LLM credentials on device (not baked into the image):
   ```bash
   aohp uda config-set \
     --api-key "$UDA_API_KEY" \
     --model "doubao-seed-2-0-pro-260215" \
     --base-url "https://ark.cn-beijing.volces.com/api/v3" \
     --provider openai
   ```
2. The `uda` Alpine container is created automatically on first run.

## Choose a workflow

### A. Idea-only (fastest)

No custom input files. UDAGen auto-drafts mock API docs from `--idea`.

```bash
aohp uda generate \
  --app-name "Google Search" \
  --idea "Google Search mini-app: search arbitrary keywords on a single mobile page; show Google results after submit"
```

Note the returned `jobId`, then poll `aohp uda status -j <jobId>` until `status: completed` and `hasApp: true`.

### B. Structured input (richer apps)

Stage per-job input **before** `uda.generate`. When `/opt/udagen/workspace/<jobId>/input/` contains supported files, generation uses that tree instead of the empty template.

**1. Allocate input scaffold**

```bash
aohp uda input init
# → { "jobId": "job-1710000000000", "containerInputDir": "...", "hostInputDir": "..." }
```

**2. Write input files** (repeat as needed)

```bash
JOB=job-1710000000000

aohp uda input write -j "$JOB" --path requirements/idea.md --content "$(cat <<'EOF'
# Google Search App
Single search field; submit runs a Google search for arbitrary keywords.
Mobile-first; pin-friendly launcher name: Google Search.
EOF
)"

aohp uda input write -j "$JOB" --path app/manifest.json --content '{
  "name": "Google Search",
  "short_name": "Search",
  "theme_color": "#4285F4",
  "background_color": "#FFFFFF",
  "description": "Search Google with any keyword"
}'

aohp uda input write -j "$JOB" --path mock_docs/openapi.yaml --content "$(cat <<'EOF'
openapi: 3.0.3
info:
  title: Google Search Proxy
  version: 1.0.0
paths:
  /search:
    get:
      summary: Search by keyword
      parameters:
        - name: q
          in: query
          required: true
          schema: { type: string }
      responses:
        "200":
          description: Redirect or embed URL for Google results
EOF
)"
```

**3. Generate with the same job id**

```bash
aohp uda generate -j "$JOB" \
  --app-name "Google Search" \
  --idea "Google Search: arbitrary keywords"
```

**Alternative:** edit files via sandbox:

```bash
aohp sandbox exec uda -- ls /opt/udagen/workspace/$JOB/input/
```

Host bind path: `/data/aohp/shared/uda/<jobId>/input/`

## After generation

```bash
aohp uda status -j <jobId>    # poll until hasApp
aohp uda install -j <jobId> --pin
aohp uda launch -j <jobId>
```

See skill **`uda-app`** for install/launch details.

## Input bundle reference

Supported extensions: `.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.csv`, `.tsv`

| Path | Role |
|------|------|
| `requirements/*.md` | Product brief / user stories |
| `app/manifest.json` | Launcher name, theme, icon hint |
| `mock_docs/openapi.yaml` | API contract for mock backend |
| `mock_docs/assumptions.json` | Personas, layout, action mapping |
| `mock_docs/schemas/*.json` | Entity JSON Schemas |

Baked template (device): `/opt/udagen/template-input/`  
Per-job input: `/opt/udagen/workspace/<jobId>/input/`

## RPC mapping

| CLI | JSON-RPC |
|-----|----------|
| `aohp uda config-get` | `uda.config.get` |
| `aohp uda config-set` | `uda.config.set` |
| `aohp uda input init` | `uda.input.init` |
| `aohp uda input write` | `uda.input.write` |
| `aohp uda generate` | `uda.generate` |
| `aohp uda status` | `uda.status` |
| `aohp uda list` | `uda.list` |
| `aohp uda delete` | `uda.delete` |
| `aohp uda preview` | `uda.preview` |

`uda.generate` optional params: `jobId`, `appName`, `idea`, `inputDir` (container path override).

## Output layout

`/data/aohp/shared/uda/<jobId>/` (container: `/opt/udagen/workspace/<jobId>/`):

- `app/index.html` — WebView app
- `mock/server.py` — local API on `127.0.0.1:8787`
- `prd.json`, `design_spec.json`, `udagen.log` — pipeline artifacts

## Tips

- Generation runs in the background inside `uda`; poll `uda.status` (minutes).
- Do not commit API keys into the image; use `uda config-set`.
- For idea-only tasks, workflow **A** is enough; use **B** when the user supplies API shapes, data samples, or detailed requirements files.
