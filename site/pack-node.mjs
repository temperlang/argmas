// Runs the built site's JavaScript tour in Node, as the page's "Run" button
// does (packrun.js), on each command line given as JSON on standard input,
// and prints what each printed, as JSON. build.py runs it on the built site
// for the tour's command lines, and the page shows what it gives.
//
//     echo '["pack --help"]' | node site/pack-node.mjs site/build
//
// Loads Argmas from the built site's `lib/`, the files the page loads,
// resolving the page's import map names the same way.

import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { pathToFileURL } from "node:url";
import { runPack, splitLine } from "./packrun.js";

const build = pathToFileURL(`${process.argv[2] ?? "site/build"}/`);
// As in index.html's import map.
const imports = {
  argmas: new URL("lib/argmas/index.js", build).href,
  "@temperlang/core": new URL("lib/temper-core/index.js", build).href,
};
registerHooks({
  resolve: (specifier, context, next) =>
    Object.hasOwn(imports, specifier)
      ? { url: imports[/** @type {keyof imports} */ (specifier)], shortCircuit: true }
      : next(specifier, context),
});

const modules = { argmas: await import("argmas") };
const source = readFileSync(new URL("tour/tour.js", build), "utf8");
const lines = JSON.parse(readFileSync(0, "utf8"));
const runs = [];
for (const line of lines) {
  const { env, args } = splitLine(line);
  runs.push({ line, args, env, ...(await runPack(source, modules, args, env)) });
}
process.stdout.write(JSON.stringify(runs, null, 1));
