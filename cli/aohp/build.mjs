import * as esbuild from "esbuild";
import { chmod } from "fs/promises";

await esbuild.build({
  entryPoints: ["src/index.ts"],
  bundle: true,
  platform: "node",
  target: "node20",
  format: "cjs",
  outfile: "dist/aohp.js",
  banner: {
    js: "#!/usr/bin/env node",
  },
});

await chmod("dist/aohp.js", 0o755);
console.log("Built dist/aohp.js");
