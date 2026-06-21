import type { Command } from "commander";

/** Options produced by Commander for `act key` / `act-key`. */
export type ActKeyCliOpts = {
  display: number;
  keyCode?: number;
  key?: string;
  back?: boolean;
  home?: boolean;
  enter?: boolean;
  menu?: boolean;
  recents?: boolean;
  volumeUp?: boolean;
  volumeDown?: boolean;
  power?: boolean;
  tab?: boolean;
  del?: boolean;
  forwardDel?: boolean;
  escape?: boolean;
  dpadUp?: boolean;
  dpadDown?: boolean;
  dpadLeft?: boolean;
  dpadRight?: boolean;
  dpadCenter?: boolean;
};

const SHORTHAND_KEYS: (keyof ActKeyCliOpts)[] = [
  "back",
  "home",
  "enter",
  "menu",
  "recents",
  "volumeUp",
  "volumeDown",
  "power",
  "tab",
  "del",
  "forwardDel",
  "escape",
  "dpadUp",
  "dpadDown",
  "dpadLeft",
  "dpadRight",
  "dpadCenter",
];

function parseKeyCodeArg(v: string): number {
  const s = v.trim();
  if (/^0x[0-9a-fA-F]+$/.test(s)) {
    return parseInt(s.slice(2), 16);
  }
  return parseInt(s, 10);
}

/**
 * Build JSON-RPC params for `act.key`. Returns `{ error }` if the user combined
 * incompatible options or omitted a key specification.
 */
export function buildActKeyParams(
  opts: ActKeyCliOpts,
): Record<string, unknown> | { error: string } {
  const displayId = opts.display;
  const base: Record<string, unknown> = { displayId };

  const hasKeyCode = typeof opts.keyCode === "number" && !Number.isNaN(opts.keyCode);
  const keyToken = (opts.key ?? "").trim();
  const hasKeyName = keyToken.length > 0;
  const activeShorthands = SHORTHAND_KEYS.filter((k) => opts[k] === true);

  const nShorthand = activeShorthands.length;
  const nSources = [hasKeyCode, hasKeyName, nShorthand > 0].filter(Boolean).length;

  if (nSources > 1) {
    return {
      error:
        "use only one of -k/--key-code, -K/--key, or a single shortcut flag (--back, --home, …)",
    };
  }
  if (nShorthand > 1) {
    return { error: "at most one of --back/--home/… may be set" };
  }
  if (nSources === 0) {
    return {
      error: "specify -k/--key-code, -K/--key, or one shortcut (--back, --home, --recents, …)",
    };
  }

  if (hasKeyCode) {
    return { ...base, keyCode: opts.keyCode };
  }
  if (hasKeyName) {
    return { ...base, keyName: keyToken };
  }
  const flag = activeShorthands[0]!;
  return { ...base, [flag]: true };
}

/** Shared Commander options for `act key` and top-level `act-key`. */
export function attachActKeyOptions(cmd: Command): Command {
  return cmd
    .requiredOption("-d, --display <n>", "", (v) => parseInt(v, 10))
    .option(
      "-k, --key-code <n>",
      "Android KeyEvent code (decimal or 0x hex); same numeric space as `adb shell input keyevent`",
      parseKeyCodeArg,
    )
    .option(
      "-K, --key <token>",
      "key token like adb: decimal, 0x hex, or name (BACK, HOME, APP_SWITCH, VOLUME_UP, …)",
    )
    .option("--back", "KEYCODE_BACK", false)
    .option("--home", "KEYCODE_HOME", false)
    .option("--enter", "KEYCODE_ENTER", false)
    .option("--menu", "KEYCODE_MENU", false)
    .option("--recents", "KEYCODE_APP_SWITCH (overview)", false)
    .option("--volume-up", "KEYCODE_VOLUME_UP", false)
    .option("--volume-down", "KEYCODE_VOLUME_DOWN", false)
    .option("--power", "KEYCODE_POWER", false)
    .option("--tab", "KEYCODE_TAB", false)
    .option("--del", "KEYCODE_DEL (backspace)", false)
    .option("--forward-del", "KEYCODE_FORWARD_DEL", false)
    .option("--escape", "KEYCODE_ESCAPE", false)
    .option("--dpad-up", "KEYCODE_DPAD_UP", false)
    .option("--dpad-down", "KEYCODE_DPAD_DOWN", false)
    .option("--dpad-left", "KEYCODE_DPAD_LEFT", false)
    .option("--dpad-right", "KEYCODE_DPAD_RIGHT", false)
    .option("--dpad-center", "KEYCODE_DPAD_CENTER", false);
}
