import { Command } from "commander";
import { attachActKeyOptions, buildActKeyParams, type ActKeyCliOpts } from "./act-key";
import { rpc } from "./client";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const DEF_URL = process.env.AOHP_WS_URL ?? "ws://127.0.0.1:6666";
const CLI_VERSION = "0.1.0";

const program = new Command();

function getOpts(): { url: string; pretty: boolean } {
  return program.opts() as { url: string; pretty: boolean };
}

type FilePathReportCliOpts = {
  filePathReport?: boolean;
  filePathRoots?: string;
  filePathMime?: string[];
  filePathWindow?: string;
  filePathSettle?: string;
  filePathRetryDelay?: string;
  filePathTimeout?: string;
};

const ENHANCED_UI_TREE_FLAGS = 0x7;

type UiTreeCliOpts = {
  display: number;
  flags?: string;
  enhanced?: boolean;
  origin?: boolean;
  raw?: boolean;
};

function collectOption(value: string, previous: string[] = []): string[] {
  previous.push(value);
  return previous;
}

function parseUiTreeFlags(value: string | undefined, fallback: number): number {
  if (value === undefined) {
    return fallback;
  }
  const flags = Number(String(value).trim());
  if (!Number.isFinite(flags)) {
    throw new Error(`Invalid UI tree flags: ${value}`);
  }
  return flags;
}

function buildUiTreeParams(opts: UiTreeCliOpts): Record<string, unknown> {
  const raw = !!opts.raw;
  return {
    displayId: opts.display,
    flags: parseUiTreeFlags(opts.flags, raw ? 0 : ENHANCED_UI_TREE_FLAGS),
    enhanced: !raw,
    origin: !!opts.origin || raw,
    ...(raw ? { raw: true } : {}),
  };
}

function parseDurationMs(value: string | undefined, fallback: number): number {
  if (!value) return fallback;
  const s = String(value).trim().toLowerCase();
  if (s.endsWith("ms")) return parseInt(s.slice(0, -2), 10);
  if (s.endsWith("s")) return parseFloat(s.slice(0, -1)) * 1000;
  return parseInt(s, 10);
}

function attachFilePathReportOptions<T extends Command>(cmd: T): T {
  return cmd
    .option("-F, --file-path-report", "include post-action saved-file path detection", false)
    .option("--file-path-roots <csv>", "filePathReport roots aliases/csv")
    .option("--file-path-mime <mime>", "filePathReport MIME filter; repeatable", collectOption, [])
    .option("--file-path-window <duration>", "filePathReport window, e.g. 30s")
    .option("--file-path-settle <duration>", "wait after action before scanning, e.g. 1200ms")
    .option("--file-path-retry-delay <duration>", "wait and rescan once after no match, e.g. 1000ms")
    .option("--file-path-timeout <duration>", "scan budget, e.g. 3000ms") as T;
}

function applyFilePathReport(
  params: Record<string, unknown>,
  opts: FilePathReportCliOpts,
): Record<string, unknown> {
  if (!opts.filePathReport) return params;
  const report: Record<string, unknown> = {
    roots: opts.filePathRoots
      ? opts.filePathRoots.split(",").map((s) => s.trim()).filter(Boolean)
      : ["downloads", "pictures", "dcim", "documents", "screenshots"],
    mimeTypes: opts.filePathMime && opts.filePathMime.length > 0 ? opts.filePathMime : [],
    windowMs: parseDurationMs(opts.filePathWindow, 30_000),
    settleMs: parseDurationMs(opts.filePathSettle, 1200),
    retryDelayMs: parseDurationMs(opts.filePathRetryDelay, 1000),
    mode: "recent",
    recursive: true,
    maxDepth: 4,
    maxFiles: 2000,
    timeoutMs: parseDurationMs(opts.filePathTimeout, 3000),
  };
  return { ...params, filePathReport: report };
}

function actResultFailed(result: unknown): boolean {
  if (result == null || typeof result !== "object") {
    return false;
  }
  const r = result as Record<string, unknown>;
  if (r.error === true) {
    return true;
  }
  if (r.success === false) {
    return true;
  }
  return false;
}

async function invoke(
  url: string,
  method: string,
  params: Record<string, unknown>,
  pretty: boolean,
) {
  const res = await rpc(url, method, params);
  if (!res.ok) {
    console.error(JSON.stringify(res.error ?? res, null, pretty ? 2 : undefined));
    process.exit(2);
  }
  if (method.startsWith("act.") && actResultFailed(res.result)) {
    console.error(JSON.stringify(res.result, null, pretty ? 2 : undefined));
    process.exit(2);
  }
  console.log(JSON.stringify(res.result, null, pretty ? 2 : undefined));
}

function failCli(message: string): never {
  console.error(JSON.stringify({ code: "bad_args", message }));
  process.exit(2);
}

function finiteNumber(name: string, value: number | undefined): number | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (!Number.isFinite(value)) {
    failCli(`Invalid ${name}: ${value}`);
  }
  return value;
}

function rangeFromSetProgressResult(result: unknown): { min: number; max: number } | undefined {
  if (result === null || typeof result !== "object") {
    return undefined;
  }
  const range = (result as Record<string, unknown>).range;
  if (range === null || typeof range !== "object") {
    return undefined;
  }
  const r = range as Record<string, unknown>;
  const min = typeof r.min === "number" ? r.min : Number(r.min);
  const max = typeof r.max === "number" ? r.max : Number(r.max);
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
    return undefined;
  }
  return { min, max };
}

function percentForRawProgressValue(value: number, min: number, max: number): number {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
    failCli(`Invalid progress range: min=${min}, max=${max}`);
  }
  const epsilon = 1e-6;
  if (value < min - epsilon || value > max + epsilon) {
    failCli(`Progress value ${value} is outside range ${min}..${max}`);
  }
  return ((Math.min(Math.max(value, min), max) - min) / (max - min)) * 100;
}

async function invokeSetNodeProgress(
  url: string,
  opts: {
    display: number;
    nodeId: number;
    percent?: number;
    value?: number;
    rangeMin?: number;
    rangeMax?: number;
    flags?: string;
  } & FilePathReportCliOpts,
  pretty: boolean,
) {
  const percent = finiteNumber("percent", opts.percent);
  const value = finiteNumber("value", opts.value);
  const rangeMin = finiteNumber("rangeMin", opts.rangeMin);
  const rangeMax = finiteNumber("rangeMax", opts.rangeMax);
  const flags = parseInt(String(opts.flags ?? "0"), 10);

  if (percent !== undefined && value !== undefined) {
    failCli("Use either --percent or --value, not both");
  }
  if (percent === undefined && value === undefined) {
    failCli("One of --percent or --value is required");
  }
  if ((rangeMin === undefined) !== (rangeMax === undefined)) {
    failCli("Use --range-min and --range-max together");
  }

  let targetPercent = percent;
  let probedRange: { min: number; max: number } | undefined;

  if (value !== undefined) {
    if (rangeMin !== undefined && rangeMax !== undefined) {
      probedRange = { min: rangeMin, max: rangeMax };
    } else {
      const probe = await rpc(url, "act.set_node_progress", {
        displayId: opts.display,
        nodeId: opts.nodeId,
        percent: 50,
        flags,
      });
      if (!probe.ok) {
        console.error(JSON.stringify(probe.error ?? probe, null, pretty ? 2 : undefined));
        process.exit(2);
      }
      probedRange = rangeFromSetProgressResult(probe.result);
      if (!probedRange) {
        failCli("AgentDriver did not return a usable progress range; pass --range-min and --range-max");
      }
    }
    targetPercent = percentForRawProgressValue(value, probedRange.min, probedRange.max);
  }

  const params = applyFilePathReport({
    displayId: opts.display,
    nodeId: opts.nodeId,
    percent: targetPercent,
    flags,
  }, opts);
  const res = await rpc(url, "act.set_node_progress", params);
  if (!res.ok) {
    console.error(JSON.stringify(res.error ?? res, null, pretty ? 2 : undefined));
    process.exit(2);
  }
  const result = res.result;
  if (value !== undefined && result !== null && typeof result === "object") {
    console.log(JSON.stringify({
      ...(result as Record<string, unknown>),
      requestedValue: value,
      requestedMode: "value",
      ...(probedRange ? { requestedRange: probedRange } : {}),
    }, null, pretty ? 2 : undefined));
    return;
  }
  console.log(JSON.stringify(result, null, pretty ? 2 : undefined));
}

/** If {@code result.tree} is a JSON string, parse it so pretty-print shows windows/nodes structure. */
function transformUiTreeResult(result: unknown): unknown {
  if (result === null || typeof result !== "object") {
    return result;
  }
  const r = result as Record<string, unknown>;
  const t = r.tree;
  if (typeof t === "string") {
    const s = t.trim();
    if (s.startsWith("{")) {
      try {
        return { ...r, tree: JSON.parse(s) as unknown };
      } catch {
        /* keep string */
      }
    }
  }
  return result;
}

/**
 * Strip optional `data:<mime>;base64,` prefix; return raw base64 payload + MIME type.
 * Matches Pi / OpenClaw tool image blocks (`data` + `mimeType`), not Anthropic `source`.
 */
function parseBase64ImageField(value: string): { data: string; mimeType: string } {
  const trimmed = value.trim();
  const m = /^data:([^;]+);base64,(.+)$/i.exec(trimmed);
  if (m) {
    return { mimeType: m[1].trim(), data: m[2].trim() };
  }
  return { mimeType: "image/jpeg", data: trimmed };
}

function shotResultDetailsWithoutBase64(result: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(result)) {
    if (k === "base64") {
      continue;
    }
    out[k] = v;
  }
  return out;
}

/** Sandbox-local JPEG path when `shot` subcommands save by default (no `-O`, no `--inline`). */
function defaultShotSavePath(prefix: string): string {
  return path.join(os.tmpdir(), `${prefix}_${Date.now()}.jpg`);
}

/**
 * Shape aligned with OpenClaw `AgentToolResult` / `imageResult` (see `imageResult` in openclaw `tools/common.ts`):
 * `{ content: [{ type: "text", text }?, { type: "image", data, mimeType }?], details }`.
 */
function buildOpenClawPiToolResult(params: {
  rpcMethod: string;
  result: Record<string, unknown>;
  imageBase64?: string;
  imageMimeType?: string;
  extraTextLines?: string[];
  omitDefaultText?: boolean;
}): { content: Array<Record<string, unknown>>; details: Record<string, unknown> } {
  const lines = [...(params.extraTextLines ?? [])];
  if (!params.omitDefaultText) {
    lines.push(`RPC ${params.rpcMethod} completed.`);
  }
  const text = lines.filter(Boolean).join("\n");
  const content: Array<Record<string, unknown>> = text ? [{ type: "text", text }] : [];
  if (params.imageBase64 && params.imageBase64.length > 0) {
    content.push({
      type: "image",
      data: params.imageBase64,
      mimeType: params.imageMimeType ?? "image/jpeg",
    });
  }
  return {
    content,
    details: { rpc: params.rpcMethod, ...shotResultDetailsWithoutBase64(params.result) },
  };
}

async function invokeShotWithLocalSave(
  url: string,
  method: string,
  params: Record<string, unknown>,
  localPath: string | undefined,
  pretty: boolean,
  shotOpts?: { includeImageInStdoutWhenSaving?: boolean },
) {
  const res = await rpc(url, method, params);
  if (!res.ok) {
    console.error(JSON.stringify(res.error ?? res, null, pretty ? 2 : undefined));
    process.exit(2);
  }
  const result = res.result as Record<string, unknown>;
  if (localPath !== undefined && typeof result.base64 === "string") {
    const { data, mimeType } = parseBase64ImageField(result.base64);
    const buf = Buffer.from(data, "base64");
    const deviceWrotePath = typeof params.path === "string" && (params.path as string).length > 0;
    const sameAsLocal =
      deviceWrotePath &&
      path.normalize(params.path as string) === path.normalize(localPath);
    if (!sameAsLocal) {
      const dir = path.dirname(path.resolve(localPath));
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(localPath, buf);
    }
    const payload = buildOpenClawPiToolResult({
      rpcMethod: method,
      result,
      ...(shotOpts?.includeImageInStdoutWhenSaving
        ? { imageBase64: data, imageMimeType: mimeType }
        : {}),
      extraTextLines: [`Saved image bytes to ${localPath}`],
    });
    console.log(JSON.stringify(payload, null, pretty ? 2 : undefined));
    return;
  }
  if (typeof result.base64 === "string") {
    const { data, mimeType } = parseBase64ImageField(result.base64);
    const payload = buildOpenClawPiToolResult({
      rpcMethod: method,
      result,
      imageBase64: data,
      imageMimeType: mimeType,
      omitDefaultText: true,
    });
    console.log(JSON.stringify(payload, null, pretty ? 2 : undefined));
    return;
  }
  const payload = buildOpenClawPiToolResult({
    rpcMethod: method,
    result,
  });
  console.log(JSON.stringify(payload, null, pretty ? 2 : undefined));
}

async function invokeUiTree(
  url: string,
  method: string,
  params: Record<string, unknown>,
  pretty: boolean,
  directTree: boolean = false,
) {
  const res = await rpc(url, method, params);
  if (!res.ok) {
    console.error(JSON.stringify(res.error ?? res, null, pretty ? 2 : undefined));
    process.exit(2);
  }
  if (directTree && res.result !== null && typeof res.result === "object") {
    const tree = (res.result as Record<string, unknown>).tree;
    if (typeof tree === "string" && !tree.trim().startsWith("{") && !tree.trim().startsWith("[")) {
      console.log(tree);
      return;
    }
  }
  console.log(JSON.stringify(transformUiTreeResult(res.result), null, pretty ? 2 : undefined));
}

program
  .name("aohp")
  .description("AOHP automation CLI — JSON-RPC over WebSocket")
  .version(CLI_VERSION, "-v, --version")
  .option("-u, --url <url>", "WebSocket URL", DEF_URL)
  .option("-p, --pretty", "pretty JSON", false);

program
  .command("call <method> [paramsJson]")
  .description('Invoke any RPC method, e.g. aohp call app.list \'{}\'')
  .action(async (method: string, paramsJson?: string) => {
    const o = getOpts();
    let params: Record<string, unknown> = {};
    if (paramsJson && paramsJson !== "{}") {
      params = JSON.parse(paramsJson) as Record<string, unknown>;
    }
    await invoke(o.url, method, params, !!o.pretty);
  });

program
  .command("connect")
  .description("Call meta.version on the Agent (same as RPC handshake check)")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "meta.version", {}, !!o.pretty);
  });

program
  .command("version")
  .description("Print CLI version; optionally query Agent over WebSocket")
  .option(
    "-c, --check-agent",
    "also call meta.version on the Agent WebSocket (requires AOHP AgentDriver listening, e.g. ws://127.0.0.1:6666)",
    false,
  )
  .action(async (cmdOpts: { checkAgent: boolean }) => {
    const o = getOpts();
    console.log(`aohp-cli ${CLI_VERSION}`);
    if (!cmdOpts.checkAgent) {
      return;
    }
    await invoke(o.url, "meta.version", {}, !!o.pretty);
  });

/* ---------- display.* ---------- */

const displayCmd = program
  .command("display")
  .description("Virtual displays (RPC methods display.*)");

displayCmd
  .command("list")
  .description("List displays → display.list")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "display.list", {}, !!o.pretty);
  });

displayCmd
  .command("create")
  .description(
    "Create a virtual display → display.create (omit -w/-h/-G to use host built-in display size / dpi)",
  )
  .option("-w, --width <n>", "width in pixels", (v) => parseInt(v, 10))
  .option("-h, --height <n>", "height in pixels", (v) => parseInt(v, 10))
  .option("-G, --density <n>", "dpi", (v) => parseInt(v, 10))
  .option("-n, --name <s>", "display name", "cli-vd")
  .option("-f, --flags <n>", "flags", "0")
  .action(async (opts: {
    width?: number;
    height?: number;
    density?: number;
    name?: string;
    flags?: string;
  }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {
      name: opts.name ?? "cli-vd",
      flags: parseInt(String(opts.flags ?? "0"), 10),
    };
    if (opts.width !== undefined && !Number.isNaN(opts.width)) {
      params.width = opts.width;
    }
    if (opts.height !== undefined && !Number.isNaN(opts.height)) {
      params.height = opts.height;
    }
    if (opts.density !== undefined && !Number.isNaN(opts.density)) {
      params.density = opts.density;
    }
    await invoke(o.url, "display.create", params, !!o.pretty);
  });

displayCmd
  .command("destroy")
  .description("Destroy a virtual display → display.destroy")
  .requiredOption("-i, --id <n>", "displayId", (v) => parseInt(v, 10))
  .action(async (opts: { id: number }) => {
    const o = getOpts();
    await invoke(o.url, "display.destroy", { displayId: opts.id }, !!o.pretty);
  });

displayCmd
  .command("launcher")
  .description("Start launcher / app on display → display.launcher")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-P, --package <pkg>", "package name")
  .action(async (opts: { display: number; package: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "display.launcher",
      { displayId: opts.display, packageName: opts.package },
      !!o.pretty,
    );
  });

displayCmd
  .command("focus")
  .description("Focus package → display.focus")
  .requiredOption("-P, --package <pkg>", "package name")
  .action(async (opts: { package: string }) => {
    const o = getOpts();
    await invoke(o.url, "display.focus", { packageName: opts.package }, !!o.pretty);
  });

/* Legacy hyphenated names (same as display <sub>) */
program
  .command("display-list")
  .description("Alias for: aohp display list")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "display.list", {}, !!o.pretty);
  });

program
  .command("display-create")
  .description("Alias for: aohp display create")
  .option("-w, --width <n>", "width in pixels", (v) => parseInt(v, 10))
  .option("-h, --height <n>", "height in pixels", (v) => parseInt(v, 10))
  .option("-G, --density <n>", "dpi", (v) => parseInt(v, 10))
  .option("-n, --name <s>", "cli-vd")
  .option("-f, --flags <n>", "0")
  .action(async (opts: {
    width?: number;
    height?: number;
    density?: number;
    name?: string;
    flags?: string;
  }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {
      name: opts.name ?? "cli-vd",
      flags: parseInt(String(opts.flags ?? "0"), 10),
    };
    if (opts.width !== undefined && !Number.isNaN(opts.width)) {
      params.width = opts.width;
    }
    if (opts.height !== undefined && !Number.isNaN(opts.height)) {
      params.height = opts.height;
    }
    if (opts.density !== undefined && !Number.isNaN(opts.density)) {
      params.density = opts.density;
    }
    await invoke(o.url, "display.create", params, !!o.pretty);
  });

program
  .command("display-destroy")
  .description("Alias for: aohp display destroy")
  .requiredOption("-i, --id <n>", "", (v) => parseInt(v, 10))
  .action(async (opts: { id: number }) => {
    const o = getOpts();
    await invoke(o.url, "display.destroy", { displayId: opts.id }, !!o.pretty);
  });

/* ---------- app.* ---------- */

const appCmd = program.command("app").description("Installed apps (RPC methods app.*)");

appCmd
  .command("list")
  .description("List packages → app.list")
  .option("-3, --third-party", "only third-party packages", false)
  .action(async (opts: { thirdParty: boolean }) => {
    const o = getOpts();
    await invoke(o.url, "app.list", { thirdParty: opts.thirdParty }, !!o.pretty);
  });

appCmd
  .command("info")
  .description("Main activity for package → app.info")
  .requiredOption("-P, --package <pkg>", "package name")
  .action(async (opts: { package: string }) => {
    const o = getOpts();
    await invoke(o.url, "app.info", { packageName: opts.package }, !!o.pretty);
  });

appCmd
  .command("start")
  .description("Launch app → app.start")
  .requiredOption("-P, --package <pkg>", "package name")
  .option("-d, --display <n>", "display id", (v) => parseInt(v, 10))
  .action(async (opts: { package: string; display?: number }) => {
    const o = getOpts();
    const params: Record<string, unknown> = { packageName: opts.package };
    if (opts.display !== undefined) {
      params.displayId = opts.display;
    }
    await invoke(o.url, "app.start", params, !!o.pretty);
  });

appCmd
  .command("kill")
  .description("Force-stop app → app.kill")
  .requiredOption("-P, --package <pkg>", "package name")
  .option("-d, --display <n>", "display id", (v) => parseInt(v, 10))
  .action(async (opts: { package: string; display?: number }) => {
    const o = getOpts();
    const params: Record<string, unknown> = { packageName: opts.package };
    if (opts.display !== undefined) {
      params.displayId = opts.display;
    }
    await invoke(o.url, "app.kill", params, !!o.pretty);
  });

appCmd
  .command("foreground")
  .description("Current foreground package → app.foreground")
  .option("-d, --display <n>", "display id (default display if omitted)", (v) =>
    parseInt(v, 10),
  )
  .action(async (opts: { display?: number }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {};
    if (opts.display !== undefined) {
      params.displayId = opts.display;
    }
    await invoke(o.url, "app.foreground", params, !!o.pretty);
  });

appCmd
  .command("running")
  .description("Running apps snapshot → app.running")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "app.running", {}, !!o.pretty);
  });

program
  .command("app-list")
  .description("Alias for: aohp app list")
  .option("-3, --third-party", "only third-party packages", false)
  .action(async (opts: { thirdParty: boolean }) => {
    const o = getOpts();
    await invoke(o.url, "app.list", { thirdParty: opts.thirdParty }, !!o.pretty);
  });

/* ---------- act.* ---------- */

const actCmd = program.command("act").description("Input / gestures / node progress (RPC methods act.*)");

function actTapOptions(cmd: Command) {
  return attachFilePathReportOptions(cmd)
    .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
    .requiredOption("-x <n>", "", (v) => parseInt(v, 10))
    .requiredOption("-y <n>", "", (v) => parseInt(v, 10));
}

actTapOptions(actCmd.command("tap"))
  .description("Tap → act.tap")
  .option("-t, --time <ms>", "tap duration (ms); RPC field: duration", "50")
  .action(async (opts: { display: number; x: number; y: number; time?: string } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.tap",
      applyFilePathReport({
        displayId: opts.display,
        x: opts.x,
        y: opts.y,
        duration: parseInt(String(opts.time ?? "50"), 10),
      }, opts),
      !!o.pretty,
    );
  });

actTapOptions(actCmd.command("long-tap"))
  .description("Long press → act.long_tap")
  .option("-t, --time <ms>", "hold duration (ms); RPC field: duration", "1000")
  .action(async (opts: { display: number; x: number; y: number; time?: string } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.long_tap",
      applyFilePathReport({
        displayId: opts.display,
        x: opts.x,
        y: opts.y,
        duration: parseInt(String(opts.time ?? "1000"), 10),
      }, opts),
      !!o.pretty,
    );
  });

function actSwipeBody(
  method: "act.swipe",
  opts: {
    display: number;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    time?: string;
  } & FilePathReportCliOpts,
  url: string,
  pretty: boolean,
) {
  return invoke(
    url,
    method,
    applyFilePathReport({
      displayId: opts.display,
      x1: opts.x1,
      y1: opts.y1,
      x2: opts.x2,
      y2: opts.y2,
      duration: parseInt(String(opts.time ?? "300"), 10),
    }, opts),
    pretty,
  );
}

attachFilePathReportOptions(actCmd
  .command("swipe")
  .description("Swipe / drag → act.swipe (alias act.drag)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-x1, --x1 <n>", "start x", (v) => parseInt(v, 10))
  .requiredOption("-y1, --y1 <n>", "start y", (v) => parseInt(v, 10))
  .requiredOption("-x2, --x2 <n>", "end x", (v) => parseInt(v, 10))
  .requiredOption("-y2, --y2 <n>", "end y", (v) => parseInt(v, 10))
  .option("-t, --time <ms>", "gesture duration (ms); RPC field: duration", "300"))
  .action(
    async (opts: {
      display: number;
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      time?: string;
    } & FilePathReportCliOpts) => {
      const o = getOpts();
      await actSwipeBody("act.swipe", opts, o.url, !!o.pretty);
    },
  );

attachFilePathReportOptions(actCmd
  .command("drag")
  .description("Alias of: aohp act swipe (act.drag)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-x1, --x1 <n>", "start x", (v) => parseInt(v, 10))
  .requiredOption("-y1, --y1 <n>", "start y", (v) => parseInt(v, 10))
  .requiredOption("-x2, --x2 <n>", "end x", (v) => parseInt(v, 10))
  .requiredOption("-y2, --y2 <n>", "end y", (v) => parseInt(v, 10))
  .option("-t, --time <ms>", "gesture duration (ms); RPC field: duration", "300"))
  .action(
    async (opts: {
      display: number;
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      time?: string;
    } & FilePathReportCliOpts) => {
      const o = getOpts();
      await actSwipeBody("act.swipe", opts, o.url, !!o.pretty);
    },
  );

attachFilePathReportOptions(actCmd
  .command("input")
  .description(
    "Type into focused field → act.input (default: clear then type; see --mode)",
  )
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-t, --text <s>", "text to input")
  .option("-m, --mode <mode>", "replace | append | prepend (default replace)", "replace")
  .option(
    "-N, --clear-count <n>",
    "ignored (legacy); replace clears the field then injects keystrokes (shell input fallback when Binder inject is blocked)",
    "512",
  ))
  .action(
    async (
      opts: {
        display: number;
        text: string;
        mode?: string;
        clearCount?: string;
      } & FilePathReportCliOpts,
    ) => {
      const mode = (opts.mode ?? "replace").toLowerCase();
      if (!["replace", "append", "prepend"].includes(mode)) {
        console.error(`Invalid --mode: ${opts.mode} (use replace, append, or prepend)`);
        process.exit(1);
      }
      const o = getOpts();
      const params: Record<string, unknown> = {
        displayId: opts.display,
        text: opts.text,
        inputMode: mode,
      };
      if (mode === "replace") {
        params.clearCount = parseInt(String(opts.clearCount ?? "512"), 10);
      }
      await invoke(o.url, "act.input", applyFilePathReport(params, opts), !!o.pretty);
    },
  );

attachFilePathReportOptions(attachActKeyOptions(actCmd.command("key")))
  .description(
    "Key event → act.key (numeric keyCode, named token like adb keyevent, or one shortcut flag)",
  )
  .action(async (opts: ActKeyCliOpts & FilePathReportCliOpts) => {
    const o = getOpts();
    const params = buildActKeyParams(opts);
    if ("error" in params) {
      console.error(params.error);
      process.exit(1);
    }
    await invoke(o.url, "act.key", applyFilePathReport(params, opts), !!o.pretty);
  });

attachFilePathReportOptions(actCmd
  .command("back")
  .description("System Back → act.key (--back shortcut)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10)))
  .action(async (opts: { display: number } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.key",
      applyFilePathReport({ displayId: opts.display, back: true }, opts),
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("home")
  .description("System Home → act.key (--home shortcut)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10)))
  .action(async (opts: { display: number } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.key",
      applyFilePathReport({ displayId: opts.display, home: true }, opts),
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("recents")
  .description("Overview / recents → act.key (--recents shortcut)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10)))
  .action(async (opts: { display: number } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.key",
      applyFilePathReport({ displayId: opts.display, recents: true }, opts),
      !!o.pretty,
    );
  });

actCmd
  .command("clear-text")
  .description("Clear focused editable (ACTION_SET_TEXT) → act.clear_text")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags for accessibility path (same bitmask as tap-node)",
    "0",
  )
  .action(async (opts: { display: number; flags?: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.clear_text",
      {
        displayId: opts.display,
        flags: parseInt(String(opts.flags ?? "0"), 10),
      },
      !!o.pretty,
    );
  });

actCmd
  .command("clear")
  .description("Clear focused editable → act.clear (same RPC params as clear-text)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags for accessibility path (same bitmask as tap-node)",
    "0",
  )
  .action(async (opts: { display: number; flags?: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.clear",
      {
        displayId: opts.display,
        flags: parseInt(String(opts.flags ?? "0"), 10),
      },
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("tap-node")
  .description("Tap by node id from ui.tree → act.tap_node")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-i, --node-id <n>", "node id from ui.tree (field id)", (v) => parseInt(v, 10))
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags when resolving node (0x1 decorative filter; 0x2 offscreen marks; 0x4 visual marks; 0x8 APPLICATION-only windows)",
    "0",
  ))
  .action(async (opts: { display: number; nodeId: number; flags?: string } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.tap_node",
      applyFilePathReport({
        displayId: opts.display,
        nodeId: opts.nodeId,
        flags: parseInt(String(opts.flags ?? "0"), 10),
      }, opts),
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("long-tap-node")
  .description("Long press by node id from ui.tree → act.long_tap_node")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-i, --node-id <n>", "node id from ui.tree (field id)", (v) => parseInt(v, 10))
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags when resolving node (same as tap-node)",
    "0",
  )
  .option("-t, --time <ms>", "hold duration (ms); RPC field: duration", "1000"))
  .action(async (opts: {
    display: number;
    nodeId: number;
    flags?: string;
    time?: string;
  } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.long_tap_node",
      applyFilePathReport({
        displayId: opts.display,
        nodeId: opts.nodeId,
        flags: parseInt(String(opts.flags ?? "0"), 10),
        duration: parseInt(String(opts.time ?? "1000"), 10),
      }, opts),
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("input-node")
  .description(
    "Tap node then type → act.input_node (default: clear field then type; see --mode)",
  )
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-i, --node-id <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-t, --text <s>", "text to input")
  .option("-m, --mode <mode>", "replace | append | prepend (default replace)", "replace")
  .option(
    "-N, --clear-count <n>",
    "ignored (legacy); replace clears via system ACTION_SET_TEXT on tapped node id",
    "512",
  )
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags when resolving node (same as tap-node)",
    "0",
  ))
  .action(async (opts: {
    display: number;
    nodeId: number;
    text: string;
    mode?: string;
    clearCount?: string;
    flags?: string;
  } & FilePathReportCliOpts) => {
    const mode = (opts.mode ?? "replace").toLowerCase();
    if (!["replace", "append", "prepend"].includes(mode)) {
      console.error(`Invalid --mode: ${opts.mode} (use replace, append, or prepend)`);
      process.exit(1);
    }
    const o = getOpts();
    const body: Record<string, unknown> = {
      displayId: opts.display,
      nodeId: opts.nodeId,
      text: opts.text,
      inputMode: mode,
      flags: parseInt(String(opts.flags ?? "0"), 10),
    };
    if (mode === "replace") {
      body.clearCount = parseInt(String(opts.clearCount ?? "512"), 10);
    }
    await invoke(
      o.url,
      "act.input_node",
      applyFilePathReport(body, opts),
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("clear-node")
  .description("Tap node then clear that field (ACTION_SET_TEXT) → act.clear_node")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-i, --node-id <n>", "node id from ui.tree (field id)", (v) => parseInt(v, 10))
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags when resolving node (same as tap-node)",
    "0",
  ))
  .action(async (opts: {
    display: number;
    nodeId: number;
    flags?: string;
  } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.clear_node",
      applyFilePathReport({
        displayId: opts.display,
        nodeId: opts.nodeId,
        flags: parseInt(String(opts.flags ?? "0"), 10),
      }, opts),
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("scroll-to-node")
  .description("Scroll toward node → act.scroll_to_node")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-i, --node-id <n>", "", (v) => parseInt(v, 10))
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags when resolving node (same as tap-node)",
    "0",
  ))
  .action(async (opts: { display: number; nodeId: number; flags?: string } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.scroll_to_node",
      applyFilePathReport({
        displayId: opts.display,
        nodeId: opts.nodeId,
        flags: parseInt(String(opts.flags ?? "0"), 10),
      }, opts),
      !!o.pretty,
    );
  });

attachFilePathReportOptions(actCmd
  .command("set-node-progress")
  .description(
    "Set a SeekBar / slider via ACTION_SET_PROGRESS → act.set_node_progress: -V is a concrete raw value; -P is 0–100% along the span (see option help)",
  )
  .requiredOption("-d, --display <n>", "displayId", (v) => parseInt(v, 10))
  .requiredOption("-i, --node-id <n>", "node id from ui.tree (field id)", (v) => parseInt(v, 10))
  .option(
    "-V, --value <n>",
    "set the SeekBar to a concrete raw value in the node's range (e.g. -100..100); not a 0–100 percentage",
    parseFloat,
  )
  .option(
    "-P, --percent <n>",
    "position along the full slider span as percentage 0–100 (float ok); not a raw range number. With rangeMin/rangeMax, implied raw ≈ rangeMin + (rangeMax - rangeMin) * (P / 100)",
    parseFloat,
  )
  .option("--range-min <n>", "raw value range min; avoids the probing ACTION_SET_PROGRESS call", parseFloat)
  .option("--range-max <n>", "raw value range max; avoids the probing ACTION_SET_PROGRESS call", parseFloat)
  .option(
    "-f, --flags <n>",
    "dumpUiTree flags when resolving node (same as tap-node)",
    "0",
  ))
  .action(async (opts: {
    display: number;
    nodeId: number;
    percent?: number;
    value?: number;
    rangeMin?: number;
    rangeMax?: number;
    flags?: string;
  } & FilePathReportCliOpts) => {
    const o = getOpts();
    await invokeSetNodeProgress(o.url, opts, !!o.pretty);
  });

attachFilePathReportOptions(attachActKeyOptions(program.command("act-key")))
  .description("Alias for: aohp act key")
  .action(async (opts: ActKeyCliOpts & FilePathReportCliOpts) => {
    const o = getOpts();
    const params = buildActKeyParams(opts);
    if ("error" in params) {
      console.error(params.error);
      process.exit(1);
    }
    await invoke(o.url, "act.key", applyFilePathReport(params, opts), !!o.pretty);
  });

program
  .command("act-back")
  .description("Alias for: aohp act back")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .action(async (opts: { display: number }) => {
    const o = getOpts();
    await invoke(o.url, "act.key", { displayId: opts.display, back: true }, !!o.pretty);
  });

program
  .command("act-home")
  .description("Alias for: aohp act home")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .action(async (opts: { display: number }) => {
    const o = getOpts();
    await invoke(o.url, "act.key", { displayId: opts.display, home: true }, !!o.pretty);
  });

program
  .command("act-recents")
  .description("Alias for: aohp act recents")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .action(async (opts: { display: number }) => {
    const o = getOpts();
    await invoke(o.url, "act.key", { displayId: opts.display, recents: true }, !!o.pretty);
  });

program
  .command("act-tap")
  .description("Alias for: aohp act tap")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-x <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-y <n>", "", (v) => parseInt(v, 10))
  .option("-t, --time <ms>", "tap duration (ms); RPC field: duration", "50")
  .action(async (opts: {
    display: number;
    x: number;
    y: number;
    time?: string;
  }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "act.tap",
      {
        displayId: opts.display,
        x: opts.x,
        y: opts.y,
        duration: parseInt(String(opts.time ?? "50"), 10),
      },
      !!o.pretty,
    );
  });

/* ---------- ui.* ---------- */

const uiCmd = program
  .command("ui")
  .description("UI tree via system_server dumpUiTree (RPC methods ui.*)");

uiCmd
  .command("tree")
  .description("Compact HTML view hierarchy → ui.tree (privileged dumpUiTree)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .option(
    "-f, --flags <n>",
    "enhanced tree flags (default 0x7; 0x1 decorative; 0x2 offscreen; 0x4 visual; 0x8 APPLICATION-only)",
  )
  .option("-o, --origin", "return original enhanced JSON tree instead of compact HTML", false)
  .option("-r, --raw", "deprecated: use original raw UI tree (flags default to 0)", false)
  .option("-e, --enhanced", "deprecated: enhanced tree is the default", false)
  .action(async (opts: UiTreeCliOpts) => {
    const o = getOpts();
    await invokeUiTree(o.url, "ui.tree", buildUiTreeParams(opts), !!o.pretty, !opts.origin && !opts.raw);
  });

uiCmd
  .command("find")
  .description("Filter nodes from ui.tree → ui.find")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .option("-f, --flags <n>", "enhanced tree flags (default 0x7)")
  .option("-r, --raw", "search original raw UI tree (flags default to 0)", false)
  .option("-e, --enhanced", "deprecated: enhanced tree is the default", false)
  .option("-s, --text <s>", "match exact node text")
  .option("-D, --desc <s>", "match exact content_desc")
  .option("-R, --resource-id <s>", "match exact resource_id")
  .action(
    async (opts: {
      display: number;
      flags?: string;
      enhanced?: boolean;
      raw?: boolean;
      origin?: boolean;
      text?: string;
      desc?: string;
      resourceId?: string;
    }) => {
      const o = getOpts();
      const params = buildUiTreeParams(opts);
      if (opts.text !== undefined) {
        params.text = opts.text;
      }
      if (opts.desc !== undefined) {
        params.desc = opts.desc;
      }
      if (opts.resourceId !== undefined) {
        params.resourceId = opts.resourceId;
      }
      await invokeUiTree(o.url, "ui.find", params, !!o.pretty);
    },
  );

uiCmd
  .command("focused")
  .description("Focused node (stub) → ui.focused")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "ui.focused", {}, !!o.pretty);
  });

uiCmd
  .command("input-text")
  .description("Focused field text → ui.input_text")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "ui.input_text", {}, !!o.pretty);
  });

program
  .command("ui-tree")
  .description("Alias for: aohp ui tree")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .option("-f, --flags <n>", "enhanced tree flags (default 0x7)")
  .option("-o, --origin", "return original enhanced JSON tree instead of compact HTML", false)
  .option("-r, --raw", "deprecated: use original raw UI tree (flags default to 0)", false)
  .option("-e, --enhanced", "deprecated: enhanced tree is the default", false)
  .action(async (opts: UiTreeCliOpts) => {
    const o = getOpts();
    await invokeUiTree(o.url, "ui.tree", buildUiTreeParams(opts), !!o.pretty, !opts.origin && !opts.raw);
  });

/* ---------- shot.* ---------- */

const shotCmd = program.command("shot").description("Screenshots (RPC methods shot.*)");

shotCmd
  .command("full")
  .description("Full display JPEG → shot.full (default: save under tmpdir; stdout text-only)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .option("-q, --quality <n>", "1–100", "85")
  .option(
    "-O, --path <path>",
    "save JPEG to this local path; with --inline also embeds type:image in stdout (very large)",
  )
  .option(
    "--inline",
    "include type:image (base64) in stdout; without -O does not write or keep a local JPEG (large stdout)",
    false,
  )
  .action(async (opts: { display: number; quality?: string; path?: string; inline?: boolean }) => {
    const o = getOpts();
    const explicitPath = opts.path !== undefined;
    const localPath =
      opts.inline && !explicitPath ? undefined : (opts.path ?? defaultShotSavePath("aohp_shot_full"));
    const params: Record<string, unknown> = {
      displayId: opts.display,
      quality: parseInt(String(opts.quality ?? "85"), 10),
      returnBase64: true,
    };
    if (explicitPath && localPath !== undefined) {
      params.path = localPath;
    }
    await invokeShotWithLocalSave(o.url, "shot.full", params, localPath, !!o.pretty, {
      includeImageInStdoutWhenSaving: !!(opts.inline && explicitPath),
    });
  });

shotCmd
  .command("region")
  .description("Crop region JPEG → shot.region (default: save under tmpdir; stdout text-only)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-l, --left <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-t, --top <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-r, --right <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-b, --bottom <n>", "", (v) => parseInt(v, 10))
  .option("-q, --quality <n>", "1–100", "85")
  .option(
    "-O, --path <path>",
    "save JPEG to this local path; with --inline also embeds type:image in stdout (very large)",
  )
  .option(
    "--inline",
    "include type:image (base64) in stdout; without -O does not write or keep a local JPEG (large stdout)",
    false,
  )
  .action(
    async (opts: {
      display: number;
      left: number;
      top: number;
      right: number;
      bottom: number;
      quality?: string;
      path?: string;
      inline?: boolean;
    }) => {
    const o = getOpts();
    const explicitPath = opts.path !== undefined;
    const localPath =
      opts.inline && !explicitPath ? undefined : (opts.path ?? defaultShotSavePath("aohp_shot_region"));
    const params: Record<string, unknown> = {
      displayId: opts.display,
      left: opts.left,
      top: opts.top,
      right: opts.right,
      bottom: opts.bottom,
      quality: parseInt(String(opts.quality ?? "85"), 10),
      returnBase64: true,
    };
    if (explicitPath && localPath !== undefined) {
      params.path = localPath;
    }
    await invokeShotWithLocalSave(o.url, "shot.region", params, localPath, !!o.pretty, {
        includeImageInStdoutWhenSaving: !!(opts.inline && explicitPath),
      });
    },
  );

shotCmd
  .command("node")
  .description("Node bounds JPEG → shot.node (default: save under tmpdir; stdout text-only)")
  .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
  .requiredOption("-i, --node-id <n>", "", (v) => parseInt(v, 10))
  .option("-f, --flags <n>", "0")
  .option("-q, --quality <n>", "85")
  .option(
    "-O, --path <path>",
    "save JPEG to this local path; with --inline also embeds type:image in stdout (very large)",
  )
  .option(
    "--inline",
    "include type:image (base64) in stdout; without -O does not write or keep a local JPEG (large stdout)",
    false,
  )
  .action(
    async (opts: {
      display: number;
      nodeId: number;
      flags?: string;
      quality?: string;
      path?: string;
      inline?: boolean;
    }) => {
    const o = getOpts();
    const explicitPath = opts.path !== undefined;
    const localPath =
      opts.inline && !explicitPath ? undefined : (opts.path ?? defaultShotSavePath("aohp_shot_node"));
    const params: Record<string, unknown> = {
      displayId: opts.display,
      nodeId: opts.nodeId,
      flags: parseInt(String(opts.flags ?? "0"), 10),
      quality: parseInt(String(opts.quality ?? "85"), 10),
      returnBase64: true,
    };
    if (explicitPath && localPath !== undefined) {
      params.path = localPath;
    }
    await invokeShotWithLocalSave(o.url, "shot.node", params, localPath, !!o.pretty, {
        includeImageInStdoutWhenSaving: !!(opts.inline && explicitPath),
      });
    },
  );

/* ---------- event.* ---------- */

const eventCmd = program
  .command("event")
  .description("AOHP notification/toast event stream (RPC methods event.*)");

eventCmd
  .command("register")
  .description("Register event stream capture → event.register")
  .option("-c, --client <id>", "client id", "aohp-cli")
  .option("--max <n>", "max buffered events", (v) => parseInt(v, 10))
  .option("--ttl <duration>", "event TTL, e.g. 10m is not supported; use ms or s", "600s")
  .option("--capture-screenshots", "capture event-time screenshots (default)", true)
  .option("--no-screenshots", "do not capture event-time display screenshots")
  .option("-q, --quality <n>", "screenshot JPEG quality", (v) => parseInt(v, 10), 75)
  .action(async (opts: {
    client: string;
    max?: number;
    ttl?: string;
    screenshots?: boolean;
    quality?: number;
  }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {
      clientId: opts.client,
      captureScreenshots: opts.screenshots !== false,
      screenshotQuality: opts.quality ?? 75,
      ttlMs: parseDurationMs(opts.ttl, 600_000),
    };
    if (opts.max !== undefined && !Number.isNaN(opts.max)) {
      params.maxEvents = opts.max;
    }
    await invoke(o.url, "event.register", params, !!o.pretty);
  });

eventCmd
  .command("drain")
  .description("Drain buffered events → event.drain")
  .requiredOption("-s, --session <id>", "session id from event register")
  .option("--screenshots", "include screenshot metadata in JSON", false)
  .option("--inline", "include base64 screenshots when available (large)", false)
  .option("--max <n>", "max events to drain", (v) => parseInt(v, 10))
  .option("--format <json|text>", "output format hint", "json")
  .action(async (opts: {
    session: string;
    screenshots?: boolean;
    inline?: boolean;
    max?: number;
    format?: string;
  }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {
      sessionId: opts.session,
      includeScreenshots: !!opts.screenshots,
      inlineScreenshots: !!opts.inline,
    };
    if (opts.max !== undefined && !Number.isNaN(opts.max)) {
      params.maxEvents = opts.max;
    }
    const res = await rpc(o.url, "event.drain", params);
    if (!res.ok) {
      console.error(JSON.stringify(res.error ?? res, null, o.pretty ? 2 : undefined));
      process.exit(2);
    }
    const result = res.result as Record<string, unknown>;
    if (opts.format === "text") {
      console.log(typeof result.summary === "string" ? result.summary : JSON.stringify(result));
      return;
    }
    console.log(JSON.stringify(result, null, o.pretty ? 2 : undefined));
  });

eventCmd
  .command("unregister")
  .description("Unregister event stream capture → event.unregister")
  .requiredOption("-s, --session <id>", "session id")
  .action(async (opts: { session: string }) => {
    const o = getOpts();
    await invoke(o.url, "event.unregister", { sessionId: opts.session }, !!o.pretty);
  });

eventCmd
  .command("status")
  .description("Show event stream status → event.status")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "event.status", {}, !!o.pretty);
  });

/* ---------- sensor.* ---------- */

const sensorCmd = program
  .command("sensor")
  .description("Device sensors (RPC methods sensor.*)");

const sensorCameraCmd = sensorCmd
  .command("camera")
  .description("Camera hardware capture (RPC methods sensor.camera.*)");

sensorCameraCmd
  .command("capture")
  .description("Take a still photo with the device camera → sensor.camera.capture")
  .option(
    "-O, --path <path>",
    `device save path (default: ${"/sdcard/DCIM/Camera/IMG_<timestamp>.jpg"})`,
  )
  .option("-f, --facing <n>", "0=back (default), 1=front", (v) => parseInt(v, 10), 0)
  .option("-q, --quality <n>", "JPEG quality 1–100", "90")
  .action(async (opts: { path?: string; facing: number; quality: string }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {
      facing: opts.facing,
      quality: parseInt(String(opts.quality), 10),
    };
    if (opts.path) {
      params.path = opts.path;
    }
    await invoke(o.url, "sensor.camera.capture", params, !!o.pretty);
  });

/* ---------- sys.* ---------- */

const sysCmd = program.command("sys").description("System helpers (RPC methods sys.*)");

sysCmd
  .command("clipboard")
  .description("Get/set clipboard → sys.clipboard")
  .option("-o, --op <get|set>", "operation", "get")
  .option("-s, --text <s>", "text for --op set")
  .action(async (opts: { op: string; text?: string }) => {
    const o = getOpts();
    const params: Record<string, unknown> = { op: opts.op };
    if (opts.op === "set") {
      if (opts.text === undefined) {
        console.error("sys clipboard set requires --text / -s");
        process.exit(2);
      }
      params.text = opts.text;
    }
    await invoke(o.url, "sys.clipboard", params, !!o.pretty);
  });

sysCmd
  .command("notifications")
  .description("Expand/collapse shade → sys.notifications")
  .option("-o, --op <expand|collapse>", "operation", "expand")
  .action(async (opts: { op: string }) => {
    const o = getOpts();
    await invoke(o.url, "sys.notifications", { op: opts.op }, !!o.pretty);
  });

sysCmd
  .command("device-info")
  .description("Shell one-liner → sys.device_info")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sys.device_info", {}, !!o.pretty);
  });

sysCmd
  .command("battery")
  .description("dumpsys battery → sys.battery")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sys.battery", {}, !!o.pretty);
  });

sysCmd
  .command("network")
  .description("Connectivity snippet → sys.network")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sys.network", {}, !!o.pretty);
  });

sysCmd
  .command("screen-info")
  .description("Display snippet → sys.screen_info")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sys.screen_info", {}, !!o.pretty);
  });

sysCmd
  .command("wake")
  .description("Wake screen → sys.wake")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sys.wake", {}, !!o.pretty);
  });

sysCmd
  .command("sleep")
  .description("Sleep screen → sys.sleep")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sys.sleep", {}, !!o.pretty);
  });

sysCmd
  .command("unlock")
  .description("Unlock screen → sys.unlock")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sys.unlock", {}, !!o.pretty);
  });

/* ---------- sms.* ---------- */

const smsCmd = program.command("sms").description("Send SMS (RPC method sms.send)");

smsCmd
  .command("send")
  .description("Send SMS → sms.send")
  .option("-t, --to <address>", "phone number or contact display name")
  .option("-n, --contact-name <name>", "contact display name (alias for --to when not a phone number)")
  .requiredOption("-m, --message <text>", "message body")
  .action(async (opts: { to?: string; contactName?: string; message: string }) => {
    const o = getOpts();
    const params: Record<string, unknown> = { body: opts.message };
    const target = (opts.contactName ?? opts.to ?? "").trim();
    if (!target) {
      console.error(JSON.stringify({ code: "bad_args", message: "sms send requires --to or --contact-name" }));
      process.exit(2);
    }
    if (/[0-9]{7,}/.test(target.replace(/\D/g, ""))) {
      params.address = target;
    } else {
      params.contactName = target;
    }
    await invoke(o.url, "sms.send", params, !!o.pretty);
  });

/* ---------- file.* ---------- */

const fileCmd = program.command("file").description("File Bridge helpers (RPC methods file.*)");

function fileScanOptions(cmd: Command) {
  return cmd
    .option("--roots <csv>", "root aliases or /sdcard paths")
    .option("--mime <mime>", "MIME filter; repeatable", collectOption, [])
    .option("--since <duration>", "recent window, e.g. 30s")
    .option("--max-depth <n>", "max recursive depth", (v) => parseInt(v, 10))
    .option("--max-files <n>", "max files to inspect", (v) => parseInt(v, 10));
}

function buildFileOptions(opts: {
  roots?: string;
  mime?: string[];
  since?: string;
  maxDepth?: number;
  maxFiles?: number;
}): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  if (opts.roots) params.roots = opts.roots.split(",").map((s) => s.trim()).filter(Boolean);
  if (opts.mime && opts.mime.length > 0) params.mimeTypes = opts.mime;
  if (opts.since) params.windowMs = parseDurationMs(opts.since, 30_000);
  if (opts.maxDepth !== undefined) params.maxDepth = opts.maxDepth;
  if (opts.maxFiles !== undefined) params.maxFiles = opts.maxFiles;
  return params;
}

fileScanOptions(fileCmd.command("recent"))
  .description("Find recent files → file.recent")
  .action(async (opts: {
    roots?: string;
    mime?: string[];
    since?: string;
    maxDepth?: number;
    maxFiles?: number;
  }) => {
    const o = getOpts();
    await invoke(o.url, "file.recent", buildFileOptions(opts), !!o.pretty);
  });

fileScanOptions(fileCmd.command("list <path>"))
  .description("List a /sdcard directory → file.list")
  .option("--sort <modified|name>", "client hint; server sorts candidates by confidence/modified", "modified")
  .action(async (pathArg: string, opts: {
    roots?: string;
    mime?: string[];
    since?: string;
    maxDepth?: number;
    maxFiles?: number;
    sort?: string;
  }) => {
    const o = getOpts();
    await invoke(o.url, "file.list", { path: pathArg, ...buildFileOptions(opts), sort: opts.sort }, !!o.pretty);
  });

fileCmd
  .command("stat <path>")
  .description("Stat one file/directory → file.stat")
  .action(async (pathArg: string) => {
    const o = getOpts();
    await invoke(o.url, "file.stat", { path: pathArg }, !!o.pretty);
  });

fileScanOptions(fileCmd.command("snapshot"))
  .description("Create a bounded file snapshot → file.snapshot")
  .action(async (opts: {
    roots?: string;
    mime?: string[];
    since?: string;
    maxDepth?: number;
    maxFiles?: number;
  }) => {
    const o = getOpts();
    await invoke(o.url, "file.snapshot", buildFileOptions(opts), !!o.pretty);
  });

fileCmd
  .command("diff")
  .description("Diff two snapshots → file.diff")
  .requiredOption("--before <id>", "before snapshot id")
  .requiredOption("--after <id>", "after snapshot id")
  .action(async (opts: { before: string; after: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "file.diff",
      { beforeSnapshotId: opts.before, afterSnapshotId: opts.after },
      !!o.pretty,
    );
  });

function showInFolder(
  method: "file.show_in_folder" | "file.reveal",
  opts: { path: string; display: number; settleMs?: number },
) {
  const o = getOpts();
  return invoke(o.url, method, {
    path: opts.path,
    displayId: opts.display,
    settleUiMs: opts.settleMs,
  }, !!o.pretty);
}

fileCmd
  .command("show-in-folder")
  .description("Open the containing folder and highlight a path in AOHP File Bridge UI → file.show_in_folder")
  .requiredOption("--path <path>", "device path")
  .requiredOption("-d, --display <n>", "target display id", (v) => parseInt(v, 10))
  .option("--settle-ms <n>", "UI settle hint", (v) => parseInt(v, 10))
  .action((opts: { path: string; display: number; settleMs?: number }) =>
    showInFolder("file.show_in_folder", opts));

fileCmd
  .command("reveal")
  .description("Compatibility alias for show-in-folder → file.reveal")
  .requiredOption("--path <path>", "device path")
  .requiredOption("-d, --display <n>", "target display id", (v) => parseInt(v, 10))
  .option("--settle-ms <n>", "UI settle hint", (v) => parseInt(v, 10))
  .action((opts: { path: string; display: number; settleMs?: number }) =>
    showInFolder("file.reveal", opts));

fileCmd
  .command("share")
  .description("Open Android share UI for a file → file.share")
  .requiredOption("--path <path>", "device path")
  .requiredOption("-d, --display <n>", "target display id", (v) => parseInt(v, 10))
  .option("-P, --package <pkg>", "optional target package")
  .option("--settle-ms <n>", "UI settle hint", (v) => parseInt(v, 10))
  .action(async (opts: { path: string; display: number; package?: string; settleMs?: number }) => {
    const o = getOpts();
    await invoke(o.url, "file.share", {
      path: opts.path,
      displayId: opts.display,
      packageName: opts.package,
      settleUiMs: opts.settleMs,
    }, !!o.pretty);
  });

/* ---------- sandbox.* ---------- */

const sandboxCmd = program
  .command("sandbox")
  .description("Linux sandboxes (RPC methods sandbox.*)");

sandboxCmd
  .command("list")
  .description("List container names → sandbox.list")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sandbox.list", {}, !!o.pretty);
  });

sandboxCmd
  .command("create")
  .description("Create container → sandbox.create")
  .requiredOption("-n, --name <n>", "container name")
  .option("-t, --template <t>", "template id", "alpine")
  .action(async (opts: { name: string; template: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "sandbox.create",
      { name: opts.name, template: opts.template },
      !!o.pretty,
    );
  });

sandboxCmd
  .command("destroy")
  .description("Destroy container → sandbox.destroy")
  .requiredOption("-n, --name <n>", "container name")
  .action(async (opts: { name: string }) => {
    const o = getOpts();
    await invoke(o.url, "sandbox.destroy", { name: opts.name }, !!o.pretty);
  });

sandboxCmd
  .command("reset")
  .description("Reset container → sandbox.reset")
  .requiredOption("-n, --name <n>", "container name")
  .action(async (opts: { name: string }) => {
    const o = getOpts();
    await invoke(o.url, "sandbox.reset", { name: opts.name }, !!o.pretty);
  });

sandboxCmd
  .command("exec")
  .description("Run command in container → sandbox.exec")
  .argument("<name>", "container name")
  .argument("[command...]", "shell command")
  .option("-T, --timeout <ms>", "30000")
  .action(async (name: string, commandParts: string[], opts: { timeout?: string }) => {
    const o = getOpts();
    const cmd = commandParts && commandParts.length > 0 ? commandParts.join(" ") : "echo ok";
    await invoke(
      o.url,
      "sandbox.exec",
      { name, command: cmd, timeoutMs: parseInt(opts.timeout ?? "30000", 10) },
      !!o.pretty,
    );
  });

sandboxCmd
  .command("svc-start")
  .description("Start background service → sandbox.svc_start")
  .requiredOption("-n, --name <n>", "container name")
  .requiredOption("-i, --id <s>", "service id")
  .requiredOption("-C, --command <cmd>", "command line")
  .action(async (opts: { name: string; id: string; command: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "sandbox.svc_start",
      { name: opts.name, serviceId: opts.id, command: opts.command },
      !!o.pretty,
    );
  });

sandboxCmd
  .command("svc-stop")
  .description("Stop background service → sandbox.svc_stop")
  .requiredOption("-n, --name <n>", "container name")
  .requiredOption("-i, --id <s>", "service id")
  .action(async (opts: { name: string; id: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "sandbox.svc_stop",
      { name: opts.name, serviceId: opts.id },
      !!o.pretty,
    );
  });

sandboxCmd
  .command("svc-list")
  .description("List services → sandbox.svc_list")
  .requiredOption("-n, --name <n>", "container name")
  .action(async (opts: { name: string }) => {
    const o = getOpts();
    await invoke(o.url, "sandbox.svc_list", { name: opts.name }, !!o.pretty);
  });

sandboxCmd
  .command("svc-log")
  .description("Service log → sandbox.svc_log")
  .requiredOption("-n, --name <n>", "container name")
  .requiredOption("-i, --id <s>", "service id")
  .option("-B, --tail-bytes <n>", "8192", (v) => parseInt(v, 10))
  .action(async (opts: { name: string; id: string; tailBytes?: number }) => {
    const o = getOpts();
    const params: Record<string, unknown> = { name: opts.name, serviceId: opts.id };
    if (opts.tailBytes !== undefined) {
      params.tailBytes = opts.tailBytes;
    }
    await invoke(o.url, "sandbox.svc_log", params, !!o.pretty);
  });

sandboxCmd
  .command("diag")
  .description("Diagnostics → sandbox.diag")
  .requiredOption("-n, --name <n>", "container name")
  .action(async (opts: { name: string }) => {
    const o = getOpts();
    await invoke(o.url, "sandbox.diag", { name: opts.name }, !!o.pretty);
  });

/* ---------- uda.* ---------- */

const udaCmd = program
  .command("uda")
  .description("User Defined App generator (RPC methods uda.*)");

udaCmd
  .command("config-get")
  .description("Read UDA LLM config (apiKey masked) → uda.config.get")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "uda.config.get", {}, !!o.pretty);
  });

udaCmd
  .command("config-set")
  .description("Save UDA LLM config → uda.config.set")
  .option("--api-key <key>", "LLM API key")
  .option("--model <model>", "LLM model id")
  .option("--base-url <url>", "LLM base URL")
  .option("--provider <p>", "LLM provider (e.g. openai)")
  .action(async (opts: { apiKey?: string; model?: string; baseUrl?: string; provider?: string }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {};
    if (opts.apiKey !== undefined) params.apiKey = opts.apiKey;
    if (opts.model !== undefined) params.model = opts.model;
    if (opts.baseUrl !== undefined) params.baseUrl = opts.baseUrl;
    if (opts.provider !== undefined) params.provider = opts.provider;
    await invoke(o.url, "uda.config.set", params, !!o.pretty);
  });

const udaInputCmd = udaCmd.command("input").description("Stage UDAGen input files before generate");

udaInputCmd
  .command("init")
  .description("Create per-job input dir (optionally seed from template) → uda.input.init")
  .option("-j, --job-id <id>", "Job id (auto-generated when omitted)")
  .option("--no-template", "Do not copy baked template-input scaffold")
  .action(async (opts: { jobId?: string; template?: boolean }) => {
    const o = getOpts();
    const params: Record<string, unknown> = { fromTemplate: opts.template !== false };
    if (opts.jobId !== undefined) params.jobId = opts.jobId;
    await invoke(o.url, "uda.input.init", params, !!o.pretty);
  });

udaInputCmd
  .command("write")
  .description("Write one UTF-8 input file under job input dir → uda.input.write")
  .requiredOption("-j, --job-id <id>", "Job id")
  .requiredOption("-p, --path <rel>", "Relative path under input/ (e.g. requirements/idea.md)")
  .requiredOption("-c, --content <text>", "File content")
  .action(async (opts: { jobId: string; path: string; content: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "uda.input.write",
      { jobId: opts.jobId, path: opts.path, content: opts.content },
      !!o.pretty,
    );
  });

udaCmd
  .command("generate")
  .description("Start UDA generation job → uda.generate")
  .requiredOption("--idea <text>", "Seed idea / requirements")
  .option("--app-name <name>", "App name hint", "User Defined App")
  .option("-j, --job-id <id>", "Optional job id (stage input under this id first)")
  .option(
    "-i, --input-dir <path>",
    "Container input dir override for udagen -i (default: per-job input or template-input)",
  )
  .action(
    async (opts: { idea: string; appName?: string; jobId?: string; inputDir?: string }) => {
      const o = getOpts();
      const params: Record<string, unknown> = {
        idea: opts.idea,
        appName: opts.appName ?? "User Defined App",
      };
      if (opts.jobId !== undefined) params.jobId = opts.jobId;
      if (opts.inputDir !== undefined) params.inputDir = opts.inputDir;
      await invoke(o.url, "uda.generate", params, !!o.pretty);
    },
  );

udaCmd
  .command("status")
  .description("Poll generation job → uda.status")
  .requiredOption("-j, --job-id <id>", "Job id")
  .action(async (opts: { jobId: string }) => {
    const o = getOpts();
    await invoke(o.url, "uda.status", { jobId: opts.jobId }, !!o.pretty);
  });

udaCmd
  .command("list")
  .description("List UDA jobs → uda.list")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "uda.list", {}, !!o.pretty);
  });

udaCmd
  .command("delete")
  .description("Delete UDA job and output → uda.delete")
  .requiredOption("-j, --job-id <id>", "Job id")
  .action(async (opts: { jobId: string }) => {
    const o = getOpts();
    await invoke(o.url, "uda.delete", { jobId: opts.jobId }, !!o.pretty);
  });

udaCmd
  .command("preview")
  .description("Open generated app preview on device → uda.preview")
  .requiredOption("-j, --job-id <id>", "Job id")
  .action(async (opts: { jobId: string }) => {
    const o = getOpts();
    await invoke(o.url, "uda.preview", { jobId: opts.jobId }, !!o.pretty);
  });

udaCmd
  .command("launch")
  .description("Launch UDA app runtime (WebView) → uda.launch")
  .requiredOption("-j, --job-id <id>", "Job id")
  .action(async (opts: { jobId: string }) => {
    const o = getOpts();
    await invoke(o.url, "uda.launch", { jobId: opts.jobId }, !!o.pretty);
  });

udaCmd
  .command("install")
  .description("Register UDA app install + optional pin → uda.install")
  .requiredOption("-j, --job-id <id>", "Job id")
  .option("--display-name <name>", "Launcher label override")
  .option("--pin", "Request pin shortcut on home screen")
  .action(async (opts: { jobId: string; displayName?: string; pin?: boolean }) => {
    const o = getOpts();
    const params: Record<string, unknown> = { jobId: opts.jobId };
    if (opts.displayName !== undefined) params.displayName = opts.displayName;
    if (opts.pin) params.pin = true;
    await invoke(o.url, "uda.install", params, !!o.pretty);
  });

udaCmd
  .command("uninstall")
  .description("Remove UDA install / desktop pin → uda.uninstall")
  .requiredOption("-j, --job-id <id>", "Job id")
  .action(async (opts: { jobId: string }) => {
    const o = getOpts();
    await invoke(o.url, "uda.uninstall", { jobId: opts.jobId }, !!o.pretty);
  });

udaCmd
  .command("pin")
  .description("Pin UDA app shortcut to home screen → uda.pin")
  .requiredOption("-j, --job-id <id>", "Job id")
  .action(async (opts: { jobId: string }) => {
    const o = getOpts();
    await invoke(o.url, "uda.pin", { jobId: opts.jobId }, !!o.pretty);
  });

program
  .command("sandbox-list")
  .description("Alias for: aohp sandbox list")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "sandbox.list", {}, !!o.pretty);
  });

program
  .command("sandbox-exec")
  .description("Alias for: aohp sandbox exec")
  .argument("<name>", "container name")
  .argument("[command...]", "command")
  .option("-T, --timeout <ms>", "30000")
  .action(async (name: string, commandParts: string[], opts: { timeout?: string }) => {
    const o = getOpts();
    const cmd = commandParts && commandParts.length > 0 ? commandParts.join(" ") : "echo ok";
    await invoke(
      o.url,
      "sandbox.exec",
      { name, command: cmd, timeoutMs: parseInt(opts.timeout ?? "30000", 10) },
      !!o.pretty,
    );
  });

const overlayCmd = program.command("overlay").description("Agent execution overlay (RPC methods overlay.*)");

overlayCmd
  .command("task-start")
  .description("Show overlay with task text → overlay.task.start")
  .requiredOption("-r, --run-id <id>", "run / session id")
  .requiredOption("-t, --task <text>", "task prompt")
  .option("--title <text>", "panel title", "AOHP Agent")
  .action(async (opts: { runId: string; task: string; title: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "overlay.task.start",
      { runId: opts.runId, task: opts.task, title: opts.title },
      !!o.pretty,
    );
  });

overlayCmd
  .command("event-push")
  .description("Push timeline events → overlay.event.push")
  .requiredOption("-r, --run-id <id>", "run / session id")
  .requiredOption("-e, --events <json>", "JSON array of event objects")
  .action(async (opts: { runId: string; events: string }) => {
    const o = getOpts();
    const events = JSON.parse(opts.events);
    await invoke(o.url, "overlay.event.push", { runId: opts.runId, events }, !!o.pretty);
  });

overlayCmd
  .command("state")
  .description("Update overlay state / breathing color → overlay.state")
  .requiredOption("-r, --run-id <id>", "run / session id")
  .requiredOption("-s, --state <name>", "TASK_SHOWN|THINKING|TOOL_RUNNING|FINISHED|ERROR")
  .action(async (opts: { runId: string; state: string }) => {
    const o = getOpts();
    await invoke(o.url, "overlay.state", { runId: opts.runId, state: opts.state }, !!o.pretty);
  });

overlayCmd
  .command("task-finish")
  .description("Finish overlay task → overlay.task.finish")
  .requiredOption("-r, --run-id <id>", "run / session id")
  .option("-s, --status <status>", "finished|error", "finished")
  .option("--summary <text>", "summary line")
  .action(async (opts: { runId: string; status: string; summary?: string }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "overlay.task.finish",
      { runId: opts.runId, status: opts.status, summary: opts.summary ?? "" },
      !!o.pretty,
    );
  });

overlayCmd
  .command("hide")
  .description("Hide overlay immediately → overlay.hide")
  .option("-r, --run-id <id>", "optional run id filter")
  .action(async (opts: { runId?: string }) => {
    const o = getOpts();
    const params: Record<string, unknown> = {};
    if (opts.runId) params.runId = opts.runId;
    await invoke(o.url, "overlay.hide", params, !!o.pretty);
  });

overlayCmd
  .command("tap-show")
  .description("Show circular tap highlight at (x,y) → overlay.tap.show")
  .requiredOption("-x <n>", "x coordinate", (v) => parseInt(v, 10))
  .requiredOption("-y <n>", "y coordinate", (v) => parseInt(v, 10))
  .option("--radius <n>", "highlight radius in dp", (v) => parseInt(v, 10), 16)
  .option("--duration-ms <n>", "auto-hide after ms", (v) => parseInt(v, 10), 500)
  .action(async (opts: { x: number; y: number; radius: number; durationMs: number }) => {
    const o = getOpts();
    await invoke(
      o.url,
      "overlay.tap.show",
      { x: opts.x, y: opts.y, radius: opts.radius, durationMs: opts.durationMs },
      !!o.pretty,
    );
  });

overlayCmd
  .command("tap-hide")
  .description("Hide tap highlight immediately → overlay.tap.hide")
  .action(async () => {
    const o = getOpts();
    await invoke(o.url, "overlay.tap.hide", {}, !!o.pretty);
  });

program.configureHelp({ sortSubcommands: true });

program.parseAsync(process.argv).catch((e) => {
  console.error(e);
  process.exit(1);
});
