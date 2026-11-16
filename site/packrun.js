// @ts-check
// Runs the JavaScript tour, `pack`, on a command line, in a page or in
// Node for the build (pack-node.mjs), the same way in both: the tour's
// source becomes the body of an async function, each import becomes its
// parameters, and `process` is a stand-in holding the command line's
// arguments and environment, and collecting what it prints.

/**
 * What a command line ran with, and what it printed.
 *
 * @typedef {{ stdout: string, stderr: string, status: number }} Run
 */

/**
 * Splits a command line as a POSIX shell does, for the few things a
 * command line typed here needs: words split at spaces, '…' and "…"
 * quotes, backslash escapes, and NAME=value settings before the program's
 * name. The program's name, `pack`, may be left out.
 *
 * @param {string} line
 * @returns {{ env: Record<string, string>, args: string[] }}
 */
export function splitLine(line) {
  /** @type {string[]} */
  const words = [];
  let word = "";
  let inWord = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === " " || c === "\t") {
      if (inWord) words.push(word);
      word = "";
      inWord = false;
    } else if (c === "'") {
      const end = line.indexOf("'", i + 1);
      if (end < 0) throw new Error("A ' quote isn't closed.");
      word += line.slice(i + 1, end);
      i = end;
      inWord = true;
    } else if (c === '"') {
      i++;
      for (; i < line.length && line[i] !== '"'; i++) {
        if (line[i] === "\\" && i + 1 < line.length && '"\\$`'.includes(line[i + 1])) i++;
        word += line[i];
      }
      if (i >= line.length) throw new Error('A " quote isn\'t closed.');
      inWord = true;
    } else if (c === "\\" && i + 1 < line.length) {
      word += line[++i];
      inWord = true;
    } else {
      word += c;
      inWord = true;
    }
  }
  if (inWord) words.push(word);
  /** @type {Record<string, string>} */
  const env = {};
  while (words.length && /^[A-Za-z_]\w*=/.test(words[0])) {
    const [name, ...rest] = /** @type {string} */ (words.shift()).split("=");
    env[name] = rest.join("=");
  }
  if (words[0] === "pack") words.shift();
  return { env, args: words };
}

/**
 * Runs the tour's source with arguments and environment variables,
 * giving it the modules it imports, by specifier.
 *
 * @param {string} source
 * @param {Record<string, any>} modules
 * @param {string[]} args
 * @param {Record<string, string>} env
 * @returns {Promise<Run>}
 */
export async function runPack(source, modules, args, env) {
  /** @type {Map<string, unknown>} */
  const given = new Map();
  let out = "";
  let err = "";
  const process = {
    argv: ["node", "tour.js", ...args],
    env: { ...env },
    stdout: { write: (/** @type {string} */ text) => void (out += text) },
    stderr: { write: (/** @type {string} */ text) => void (err += text) },
    exitCode: 0,
  };
  const console = { log: (/** @type {unknown[]} */ ...items) => void (out += items.map(String).join(" ") + "\n") };
  const code = source
    .replace(/^import (\w+) from "node:process";$/m, (_, name) => {
      given.set(name, process);
      return "";
    })
    .replace(/^import \{([^}]*)\} from "([^"]+)";$/gm, (_, list, from) => {
      const module = modules[from];
      if (!module) throw new Error(`The tour imports ${from}, which isn't given.`);
      for (const name of String(list).split(",").map((n) => n.trim()).filter(Boolean)) {
        if (!(name in module)) throw new Error(`${from} has no ${name}.`);
        given.set(name, module[name]);
      }
      return "";
    });
  if (/^\s*import\b/m.test(code)) throw new Error("The tour has an import this can't run.");
  const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
  await new AsyncFunction(...given.keys(), "console", code)(...given.values(), console);
  return { stdout: out, stderr: err, status: process.exitCode };
}

/**
 * A run as demos/run.py writes it in a transcript, after the command
 * line: standard output, then standard error, if any, and the exit
 * status.
 *
 * @param {Run} run
 * @returns {string}
 */
export function transcript(run) {
  return `${run.stdout}${run.stderr ? `(standard error)\n${run.stderr}` : ""}(exit status ${run.status})\n`;
}
