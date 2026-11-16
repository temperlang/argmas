// @ts-check
// Argmas's site: the language tabs, and running `pack` in the page.
// Everything else is built into the page by build.py, so it shows before,
// and without, any script.

import { runPack, splitLine } from "./packrun.js";

const DEFAULT_LANGUAGE = "py";

// Each row of tabs. Choosing a language in one chooses it in all.
const groups = /** @type {HTMLElement[]} */ ([...document.querySelectorAll('[role="tablist"]')]).map(
  (list) => /** @type {HTMLButtonElement[]} */ ([...list.querySelectorAll('[role="tab"]')]),
);

/**
 * Shows one language's code in every row of tabs.
 *
 * @param {string} lang
 * @param {HTMLButtonElement} [focus] the tab to focus
 */
function select(lang, focus) {
  for (const tabs of groups) {
    if (!tabs.some((tab) => tab.dataset.lang === lang)) continue;
    for (const tab of tabs) {
      const on = tab.dataset.lang === lang;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      for (const id of (tab.getAttribute("aria-controls") ?? "").split(" ")) {
        const panel = document.getElementById(id);
        if (panel) panel.hidden = !on;
      }
    }
  }
  focus?.focus();
}

for (const tabs of groups) {
  for (const [i, tab] of tabs.entries()) {
    tab.addEventListener("click", () => select(tab.dataset.lang ?? DEFAULT_LANGUAGE));
    // Arrow keys move along the tabs, and Home and End go to either end, as
    // ARIA's tabs pattern has it.
    tab.addEventListener("keydown", (event) => {
      const last = tabs.length - 1;
      const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: last }[event.key];
      if (next === undefined) return;
      event.preventDefault();
      const to = tabs[(next + tabs.length) % tabs.length];
      select(to.dataset.lang ?? DEFAULT_LANGUAGE, to);
    });
  }
}

// Try it: `pack`, the JavaScript tour, run in the page (packrun.js, which
// the build also runs in Node), with Argmas and Temper's runtime from the
// page's import map, loaded on first use.

const form = /** @type {HTMLFormElement} */ (document.getElementById("try-form"));
const input = /** @type {HTMLInputElement} */ (document.getElementById("try-line"));
const tabButton = /** @type {HTMLButtonElement} */ (document.getElementById("try-tab"));
const output = /** @type {HTMLElement} */ (document.getElementById("try-output"));
const note = /** @type {HTMLElement} */ (document.getElementById("try-note"));

/** @type {Promise<[Record<string, any>, string]> | undefined} */
let loading;

function load() {
  // A name the import map resolves, kept in a variable so TypeScript
  // doesn't look for it.
  const library = "argmas";
  loading ??= Promise.all([import(library), fetchText("tour/tour.js")]);
  return loading;
}

/**
 * @param {string} url
 * @returns {Promise<string>}
 */
async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Couldn't load ${url} (${response.status}).`);
  return response.text();
}

/**
 * A span with a class and text.
 *
 * @param {string} cls
 * @param {string} text
 */
function span(cls, text) {
  const node = document.createElement("span");
  node.className = cls;
  node.textContent = text;
  return node;
}

/**
 * Shows a terminal, as build.py writes them: the command line, then what
 * follows it.
 *
 * @param {string} line
 * @param {(Node | string)[]} body
 */
function showTerm(line, body) {
  const pre = document.createElement("pre");
  pre.className = "term";
  pre.tabIndex = 0;
  pre.setAttribute("aria-label", `What ${line} prints`);
  const cmd = span("cmd", "");
  const prompt = span("prompt", "$ ");
  prompt.setAttribute("aria-hidden", "true");
  cmd.append(prompt, line);
  pre.append(cmd, "\n", ...body);
  output.replaceChildren(pre);
}

/**
 * @param {number} status
 */
function statusSpan(status) {
  return span(`status status-${status === 0 ? "ok" : "err"}`, `exit status ${status}`);
}

/** Runs the command line typed. */
async function run() {
  const line = input.value.trim();
  try {
    const { env, args } = splitLine(line);
    const [argmas, source] = await load();
    const result = await runPack(source, { argmas }, args, env);
    /** @type {(Node | string)[]} */
    const body = [result.stdout];
    if (result.stderr) body.push(span("stderr", result.stderr));
    body.push(statusSpan(result.status));
    showTerm(line, body);
    note.textContent = "Run here, in your browser, by the same JavaScript every language's tour matches.";
  } catch (error) {
    showTerm(line, [span("stderr", String(error instanceof Error ? error.message : error) + "\n")]);
  }
}

/**
 * Asks `pack` for completions of the last word typed, as a shell's script
 * does when Tab is pressed: `pack __complete INDEX WORD...`. Puts a single
 * candidate on the line, and lists more.
 */
async function complete() {
  const line = input.value;
  try {
    const { env, args } = splitLine(line);
    // A space at the end starts a new, empty word.
    if (/\s$/.test(line) || args.length === 0) args.push("");
    const [argmas, source] = await load();
    const result = await runPack(source, { argmas }, ["__complete", String(args.length - 1), ...args], env);
    const lines = result.stdout.replace(/\n$/, "").split("\n");
    const directive = lines.pop() ?? "";
    const candidates = lines.map((l) => l.split("\t"));
    const last = args[args.length - 1];
    if (candidates.length === 1 && !directive.startsWith(":files")) {
      input.value = line.slice(0, line.length - last.length) + candidates[0][0] + " ";
    }
    /** @type {(Node | string)[]} */
    const body = [];
    if (directive.startsWith(":files") || directive.startsWith(":directories")) {
      body.push(span("comp-note", directive.startsWith(":files") ? "(the shell lists files)\n" : "(the shell lists directories)\n"));
    } else if (candidates.length === 0) {
      body.push(span("comp-note", "(nothing to complete)\n"));
    } else {
      const width = Math.max(...candidates.map(([c]) => c.length));
      for (const [c, d] of candidates) {
        body.push(span("comp", c.padEnd(width)));
        if (d) body.push("  ", span("comp-desc", `-- ${d}`));
        body.push("\n");
      }
    }
    body.push(span("comp-note", `Argmas answered pack __complete ${args.length - 1} ${args.map((a) => JSON.stringify(a)).join(" ")}`));
    showTerm(`${line}⇥`, body);
    note.textContent = "Completed here, in your browser, the way bash, zsh, fish, and PowerShell ask.";
  } catch (error) {
    showTerm(line, [span("stderr", String(error instanceof Error ? error.message : error) + "\n")]);
  }
  input.focus();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  run();
});
tabButton.addEventListener("click", complete);
for (const chip of /** @type {HTMLButtonElement[]} */ ([...document.querySelectorAll(".chip")])) {
  chip.addEventListener("click", () => {
    input.value = chip.dataset.line ?? "";
    run();
  });
}
