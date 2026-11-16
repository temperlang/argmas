# /// script
# requires-python = ">=3.11"
# ///
"""Builds Argmas's site into `site/build/`.

    npm ci --prefix site
    temper build -b js -b py
    uv run site/build.py
    python3 -m http.server --bind 127.0.0.1 -d site/build

The page is static: everything on it is built into `index.html` here, and
its small script only switches the language tabs and runs `pack` in the
page when asked. Type-checks that script with TypeScript first
(`--no-check` skips that, for a quick look).

Nothing Argmas prints on the page is typed by hand. The build runs
Argmas to get it, so the page can't say what Argmas doesn't do:

- The opening and "Try it" show `pack`, the tour in `demos/tour/`. Each
  language's declaration is the `snippet: declare` part of its tour, and
  how it handles the result, under "Errors are values", the `snippet:
  results` part. What `pack` prints is from running the JavaScript tour
  here, in Node, the way the page runs it (`pack-node.mjs` and
  `packrun.js`), against the built `lib/`, for each command line in
  `demos/run.py`'s `CASES`. The build fails unless that transcript is
  exactly `demos/tour/expected.txt`, which CI checks every language's
  tour prints.
- The sections on styles, subcommands, completions, and messages show
  `site/examples.py`'s snippets and what they give, from running it with
  the Python library in `temper.out/py`.
- The styles' summaries come from `docs/design.md`'s table, the shells'
  install commands from the README's, and how to build each language's
  tour from `demos/README.md`'s.

A snippet is the lines between a comment `snippet: NAME` and a comment
`end snippet`, each alone on its line, dedented. The build fails if one
is missing, or if the page has a slot left unfilled.
"""

import difflib
import gzip
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "build"
TOUR = ROOT / "demos" / "tour"
JS = ROOT / "temper.out" / "js"
PY = ROOT / "temper.out" / "py"
REPO = "https://github.com/temperlang/argmas"

# Each language's tour, in the site's (alphabetical) order: name, id, its
# folder in demos/tour/, the program, its line comment, and the file
# naming the generated library as a dependency.
LANGUAGES = [
    ("C++", "cpp", "cpp", "tour.cpp", "//", "CMakeLists.txt"),
    ("C#", "cs", "csharp", "Program.cs", "//", "Tour.csproj"),
    ("Java", "java", "java", "src/main/java/Tour.java", "//", "build.gradle.kts"),
    ("JavaScript", "js", "js", "tour.js", "//", "package.json"),
    ("Lua", "lua", "lua", "tour.lua", "--", "paths.lua"),
    ("Python", "py", "py", "tour.py", "#", "pyproject.toml"),
    ("Rust", "rs", "rust", "src/main.rs", "//", "Cargo.toml"),
]
DEFAULT_LANGUAGE = "py"

# Which `pack` runs the opening shows.
HERO_RUNS = ["pack --help", "pack ad out.pack"]
# The command line "Try it" starts with.
TRY_FIRST = "pack add --mode quick out.pack a.txt"

STYLE_NAMES = {"gnu": "Style.gnu", "singleDash": "Style.singleDash", "windows": "Style.windows"}


def esc(text):
    return html.escape(text, quote=True)


def rel(path):
    return path.relative_to(ROOT).as_posix()


def snippets(path, comment):
    """Every snippet in a file, by name: each of its blocks, dedented,
    joined by a blank line, in order."""
    found = {}
    name = None
    block = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text.startswith(f"{comment} snippet: "):
            if name is not None:
                raise SystemExit(f"{rel(path)}: snippet {text!r} starts inside snippet {name!r}.")
            name, block = text.removeprefix(f"{comment} snippet: "), []
        elif text == f"{comment} end snippet":
            if name is None:
                raise SystemExit(f"{rel(path)}: `{comment} end snippet` outside a snippet.")
            found.setdefault(name, []).append(textwrap.dedent("\n".join(block)).strip("\n"))
            name = None
        elif name is not None:
            block.append(line)
    if name is not None:
        raise SystemExit(f"{rel(path)}: snippet {name!r} has no `{comment} end snippet`.")
    # One blank line at most, where Python's style puts two.
    return {name: re.sub(r"\n{3,}", "\n\n", "\n\n".join(blocks)) + "\n" for name, blocks in found.items()}


def snippet(path, name, comment):
    found = snippets(path, comment)
    if name not in found:
        raise SystemExit(f"{rel(path)} needs a `{comment} snippet: {name}` block.")
    return found[name]


# A small highlighter, after the one on Wherewith's and Hrefine's sites,
# run here so the page needs no script for it.
KEYWORDS = set(
    (
        "and as auto bool break case catch class const continue def do double else elif end except export "
        "false final fn for from function if import in include instanceof int let local match mut new None nil "
        "not null of or orelse panic private public return self static string struct switch then this throw true "
        "True False try type typename use using var void while Some Ok"
    ).split()
)


def highlight(source, comment):
    """Source as HTML, with comments, strings, numbers, keywords, and
    type-like names in spans."""
    comment_pattern = {"#": r"#[^\n]*", "--": r"--[^\n]*"}.get(comment, r"//[^\n]*|/\*[\s\S]*?\*/")
    token = re.compile(
        rf"({comment_pattern})|"
        r'("""[\s\S]*?"""|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\')|'
        r"\b(\d+(?:\.\d+)?)\b|([A-Za-z_]\w*)"
    )
    out = []
    last = 0
    for m in token.finditer(source):
        out.append(esc(source[last : m.start()]))
        text, is_comment, is_string, is_number, word = m[0], m[1], m[2], m[3], m[4]
        if is_comment:
            cls = "comment"
        elif is_string:
            cls = "string"
        elif is_number:
            cls = "number"
        elif word in KEYWORDS:
            cls = "keyword"
        elif re.match(r"[A-Z][a-z]", word):
            cls = "type"
        else:
            cls = None
        out.append(f'<span class="tok-{cls}">{esc(text)}</span>' if cls else esc(text))
        last = m.end()
    out.append(esc(source[last:]))
    return "".join(out)


def code_block(source, comment, label):
    return f'<pre class="source" tabindex="0" aria-label="{esc(label)}"><code>{highlight(source, comment)}</code></pre>'


def term(line, stdout="", stderr="", status=None, label=None, runs_with=None):
    """A terminal: the command line, what it printed, standard error in its
    own color, and the exit status."""
    out = [f'<span class="cmd"><span class="prompt" aria-hidden="true">$ </span>{esc(line)}</span>\n']
    out.append(esc(stdout))
    if stderr:
        out.append(f'<span class="stderr">{esc(stderr)}</span>')
    if runs_with:
        out.append(f'<span class="runs-with"><span class="runs-label">The program runs with</span>\n{esc(runs_with)}</span>')
    if status is not None:
        out.append(f'<span class="status status-{"ok" if status == 0 else "err"}">exit status {status}</span>')
    aria = esc(label or f"What {line} prints")
    return f'<pre class="term" tabindex="0" aria-label="{aria}">{"".join(out)}</pre>'


def outcome_term(run):
    """A run of an example, from examples.py: its text, or what the
    program would run with."""
    if run["kind"] == "args":
        return term(run["line"], status=run["status"], runs_with=values_text(run["values"]))
    if run["kind"] == "error":
        return term(run["line"], stderr=run["text"], status=run["status"])
    return term(run["line"], run["text"], status=run["status"])


def values_text(values):
    """What a program runs with, as the page shows it, in Python's terms,
    since the examples are Python."""

    def show(value):
        if value is None:
            return "None"
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, list):
            return "[" + ", ".join(show(v) for v in value) + "]"
        if isinstance(value, str):
            return repr(value)
        return str(value)

    return "".join(f"{name} = {show(value)}\n" for name, value in values.items())


def tabs(group, labels):
    out = [f'<div class="tabs" role="tablist" aria-label="Language">']
    for name, id in labels:
        on = id == DEFAULT_LANGUAGE
        out.append(
            f'<button type="button" role="tab" id="tab-{group}-{id}" data-lang="{id}" aria-controls="panel-{group}-{id}" '
            f'aria-selected="{str(on).lower()}" tabindex="{0 if on else -1}">{esc(name)}</button>'
        )
    out.append("</div>")
    return "".join(out)


def panel(group, id, body):
    hidden = "" if id == DEFAULT_LANGUAGE else " hidden"
    return f'<div class="lang-panel" role="tabpanel" id="panel-{group}-{id}" aria-labelledby="tab-{group}-{id}"{hidden}>{body}</div>'


def tour_code(name):
    """Tabs with each language's snippet `name` from its tour."""
    out = [tabs(name, [(n, id) for n, id, *_ in LANGUAGES])]
    for lang, id, folder, program, comment, _ in LANGUAGES:
        path = TOUR / folder / program
        source = snippet(path, name, comment)
        link = f'<a href="{REPO}/blob/main/demos/tour/{folder}/{program}"><code>demos/tour/{folder}/{program}</code></a>'
        out.append(panel(name, id, code_block(source, comment, f"{lang}, from the tour") + f'<p class="run">From {link}</p>'))
    return "".join(out)


# The tour's runs.


def tour_cases():
    """The command lines demos/run.py runs, as a shell would see them."""
    spec = importlib.util.spec_from_file_location("tour_run", ROOT / "demos" / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return ["".join(f"{k}={v} " for k, v in env.items()) + f"pack {line}" for env, line in module.CASES]


def run_pack(lines):
    """Runs the built page's JavaScript tour in Node, as the page does."""
    try:
        run = subprocess.run(
            ["node", str(SITE / "pack-node.mjs"), str(OUT)],
            input=json.dumps(lines),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        raise SystemExit("The build needs Node (24 or later), to run the JavaScript tour.")
    if run.returncode:
        raise SystemExit(f"The JavaScript tour doesn't run as the page runs it:\n{run.stderr}")
    return json.loads(run.stdout)


def check_transcript(runs):
    """Fails unless the runs, written as demos/run.py writes them, are
    exactly what every language's tour prints."""
    expected = (TOUR / "expected.txt").read_text(encoding="utf-8")
    parts = []
    for run in runs:
        parts.append(f"$ {run['line']}\n{run['stdout']}")
        if run["stderr"]:
            parts.append(f"(standard error)\n{run['stderr']}")
        parts.append(f"(exit status {run['status']})\n\n")
    actual = "".join(parts)
    if actual != expected:
        diff = difflib.unified_diff(
            expected.splitlines(keepends=True), actual.splitlines(keepends=True), "expected.txt", "in the page"
        )
        raise SystemExit(f"The JavaScript tour, run as the page runs it, prints otherwise:\n{''.join(diff)}")


def pack_term(run):
    return term(run["line"], run["stdout"], run["stderr"], run["status"])


def hero(runs):
    by_line = {run["line"]: run for run in runs}
    missing = [line for line in HERO_RUNS if line not in by_line]
    if missing:
        raise SystemExit(f"demos/run.py has no case for {missing}, which the opening shows.")
    return "".join(pack_term(by_line[line]) for line in HERO_RUNS)


def try_it(runs, first):
    chips = []
    for run in runs:
        chips.append(f'<li><button type="button" class="chip" data-line="{esc(run["line"])}">{esc(run["line"])}</button></li>')
    return {
        "TRY_CHIPS": "".join(chips),
        "TRY_LINE": esc(first["line"]),
        "TRY_OUTPUT": pack_term(first),
    }


# The examples.


def run_examples():
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(str(PY / name) for name in ("argmas", "temper-core", "std"))}
    run = subprocess.run(
        [sys.executable, str(SITE / "examples.py")], capture_output=True, text=True, encoding="utf-8", env=env
    )
    if run.returncode:
        raise SystemExit(f"site/examples.py failed:\n{run.stderr}")
    return json.loads(run.stdout)


def example_code(name):
    source = snippet(SITE / "examples.py", name, "#")
    return (
        f'<p class="code-label">In Python <a class="quiet" href="{REPO}/blob/main/site/examples.py">(site/examples.py)</a></p>'
        + code_block(source, "#", f"The {name} example, in Python")
    )


def md_table(text, heading):
    """The rows of the first Markdown table after a line starting with
    `heading`, as lists of cells, without the divider."""
    lines = text.splitlines()
    at = next((i for i, line in enumerate(lines) if line.startswith(heading)), None)
    if at is None:
        raise SystemExit(f"No table after {heading!r}.")
    start = next(i for i in range(at, len(lines)) if lines[i].startswith("|"))
    end = next((i for i in range(start, len(lines)) if not lines[i].startswith("|")), len(lines))
    rows = []
    for line in lines[start:end]:
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if not all(set(c) <= set("-: ") for c in cells):
            rows.append(cells)
    return rows


def inline_md(text):
    """A Markdown table cell as HTML: code spans, and the rest as text."""
    parts = re.split(r"(`[^`]*`)", text.strip())
    return "".join(f"<code>{esc(p[1:-1])}</code>" if p.startswith("`") else esc(p) for p in parts)


def styles_html(found):
    design = (ROOT / "docs" / "design.md").read_text(encoding="utf-8")
    rows = {re.sub(r"`Style\.(\w+)`.*", r"\1", row[0]): row for row in md_table(design, "## Argument styles")[1:]}
    out = ['<div class="styles">']
    for style in found:
        name = style["style"]
        if name not in rows:
            raise SystemExit(f"docs/design.md's style table has no {name}.")
        _, looks, common = rows[name]
        values = [f["values"] for f in style["forms"] if f["kind"] == "args"]
        if len(values) != len(style["forms"]) or any(v != values[0] for v in values):
            raise SystemExit(f"The {name} forms don't all give the same values: {style['forms']}")
        if style["mistake"]["kind"] != "error":
            raise SystemExit(f"The {name} mistake isn't an error.")
        forms = "".join(f"<li><code>{esc(f['line'])}</code></li>" for f in style["forms"])
        out.append(
            f'<article class="style-card" aria-labelledby="style-{name}">'
            f'<h3 id="style-{name}"><code>{STYLE_NAMES[name]}</code></h3>'
            f'<p class="looks">{inline_md(looks)}<br><span class="common">{inline_md(common)}</span></p>'
            f'<p class="output-label">The same, each way:</p><ul class="forms">{forms}</ul>'
            f'<p class="output-label">Each runs with:</p>'
            f'<pre class="output values" tabindex="0" aria-label="What each runs with">{esc(values_text(values[0]))}</pre>'
            f'<p class="output-label">Its help, wrapped to {style["help_width"]} columns:</p>{outcome_term(style["help"])}'
            f'<p class="output-label">A mistake:</p>{outcome_term(style["mistake"])}'
            "</article>"
        )
    out.append("</div>")
    return "".join(out)


def subcommands_html(runs):
    lines = [run["line"] for run in runs]
    for need in ["minigit -q add a.txt", "minigit add -q a.txt", "minigit add --dir repo a.txt"]:
        if need not in lines:
            raise SystemExit(f"examples.py has no run of {need}, which the page explains.")
    by = {run["line"]: run for run in runs}
    if by["minigit -q add a.txt"]["values"] != by["minigit add -q a.txt"]["values"]:
        raise SystemExit("--quiet doesn't read the same before and after add.")
    if "belongs to" not in by["minigit add --dir repo a.txt"].get("text", ""):
        raise SystemExit("The late option's error has no hint.")
    return "".join(f'<div class="run-item">{outcome_term(run)}</div>' for run in runs)


def protocol(text):
    """Argmas's answer to a shell: candidates, with descriptions, and a
    directive for the shell, on the last line."""
    lines = text.rstrip("\n").split("\n")
    directive = lines[-1]
    if not directive.startswith(":"):
        raise SystemExit(f"A completion answer doesn't end with a directive: {text!r}")
    candidates = [tuple((line.split("\t", 1) + [""])[:2]) for line in lines[:-1]]
    return candidates, directive


def completion_demo(answers):
    """A transcript of pressing Tab, from Argmas's answers: what the shell
    puts on the line, or lists."""
    steps = []
    for answer in answers:
        candidates, directive = protocol(answer["text"])
        typed = answer["line"]
        if directive.startswith((":files", ":directories")):
            what = "files" if directive.startswith(":files") else "directories"
            shown = f'<span class="comp-note">(the shell lists {what})</span>\n'
            after = typed
        elif len(candidates) == 1:
            last = answer["words"][-1]
            after = typed[: len(typed) - len(last)] + candidates[0][0] + " "
            shown = ""
        else:
            after = typed
            width = max(len(c) for c, _ in candidates)
            shown = "".join(
                f'<span class="comp">{esc(c.ljust(width))}</span>'
                + (f'  <span class="comp-desc">-- {esc(d)}</span>' if d else "")
                + "\n"
                for c, d in candidates
            )
        steps.append(
            '<div class="tab-step">'
            f'<span class="cmd"><span class="prompt" aria-hidden="true">$ </span>{shown_line(typed)}<kbd>Tab</kbd></span>\n'
            + (f'<span class="cmd done"><span class="prompt" aria-hidden="true">$ </span>{esc(after)}</span>\n' if after != typed else "")
            + shown
            + "</div>"
        )
    return f'<pre class="term tabbing" tabindex="0" aria-label="Pressing Tab, step by step">{"".join(steps)}</pre>'


def shown_line(line):
    """A command line as HTML, with a space at its end shown."""
    if line.endswith(" "):
        return esc(line[:-1]) + '<span class="space" title="a space">␣</span>'
    return esc(line)


# A tab in an answer, between a candidate and its description.
TAB_MARK = '<span class="tabchar" title="a tab">→</span>'


def completion_answers(answers):
    rows = []
    for answer in answers:
        words = " ".join(json.dumps(w) for w in answer["words"])
        text = esc(answer["text"]).replace("\t", TAB_MARK)
        rows.append(
            f'<tr><th scope="row"><code>{shown_line(answer["line"])}</code></th>'
            f'<td data-label="The script runs"><code class="call">frob __complete {len(answer["words"]) - 1} {esc(words)}</code></td>'
            f'<td data-label="Argmas answers"><pre class="answer">{text}</pre></td></tr>'
        )
    return (
        '<div class="table-scroll" tabindex="0" role="region" aria-label="What Argmas answers">'
        '<table class="answers"><thead><tr><th scope="col">Typed, then Tab</th><th scope="col">The script runs</th>'
        '<th scope="col">Argmas answers</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def install_table():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = md_table(readme, "| Shell | Install |")
    body = "".join(f'<tr><th scope="row">{esc(shell)}</th><td>{inline_md(how)}</td></tr>' for shell, how in rows[1:])
    return (
        '<div class="table-scroll" tabindex="0" role="region" aria-label="Installing the scripts">'
        '<table class="install"><thead><tr><th scope="col">Shell</th><th scope="col">Install</th></tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def scripts_html(scripts):
    out = []
    for shell, text in scripts.items():
        lines = len(text.splitlines())
        out.append(
            f'<details class="script"><summary><code>frob --completions {esc(shell)}</code> '
            f'<span class="small-note">{lines} lines</span></summary>'
            f'<pre class="output" tabindex="0" aria-label="The {esc(shell)} script">{esc(text)}</pre></details>'
        )
    return "".join(out)


def messages_html(found):
    for name in ["english", "german"]:
        if found[name]["error"]["kind"] != "error" or found[name]["help"]["kind"] != "output":
            raise SystemExit(f"The {name} messages example didn't give help and an error.")
    if "unknown message key" not in found["typo"]["help"].get("text", ""):
        raise SystemExit("The typo in a message key isn't reported.")
    cols = []
    for name, title in [("english", "English, built in"), ("german", "Partly German")]:
        cols.append(
            f'<div class="msg-col"><p class="output-label">{title}</p>'
            f"{outcome_term(found[name]['help'])}{outcome_term(found[name]['error'])}</div>"
        )
    return {
        "MESSAGES_COMPARE": f'<div class="msg-cols">{"".join(cols)}</div>',
        "MESSAGES_TYPO": outcome_term(found["typo"]["help"]),
    }


def start_html():
    """Getting started in each language: build the library, then depend on
    it the way its tour does."""
    readme = (ROOT / "demos" / "README.md").read_text(encoding="utf-8")
    rows = {row[0]: row for row in md_table(readme, "| Language |")[1:]}
    backends = {"cpp": "cpp", "cs": "csharp", "java": "java", "js": "js", "lua": "lua", "py": "py", "rs": "rust"}
    out = [tabs("start", [(n, id) for n, id, *_ in LANGUAGES])]
    for lang, id, folder, program, _, manifest in LANGUAGES:
        if lang not in rows:
            raise SystemExit(f"demos/README.md's table has no {lang}.")
        if not (TOUR / folder / manifest).exists():
            raise SystemExit(f"demos/tour/{folder}/{manifest} doesn't exist.")
        commands = rows[lang][2].strip("`")
        tour = f"{REPO}/tree/main/demos/tour/{folder}"
        body = (
            '<ol class="steps">'
            f"<li>Build the {esc(lang)} library, from a clone of Argmas: "
            f'<pre class="output cmdline" tabindex="0"><code>temper build -b {backends[id]}</code></pre>'
            f"It lands in <code>temper.out/{backends[id]}/</code>.</li>"
            f'<li>Depend on it by path, as <a href="{tour}/{manifest}"><code>demos/tour/{folder}/{manifest}</code></a> does.</li>'
            f'<li>Or run the tour, in <a href="{tour}"><code>demos/tour/{folder}</code></a>: '
            f'<pre class="output cmdline" tabindex="0"><code>{esc(commands)}</code></pre></li>'
            "</ol>"
        )
        out.append(panel("start", id, body))
    return "".join(out)


# Files.


def copy_module(source, dest):
    """A JS module without its source map comment, as the maps aren't copied."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8")
    dest.write_text(re.sub(r"\n//# sourceMappingURL=\S+\s*$", "\n", text), encoding="utf-8")


def link_modules(name):
    """Gives each `./x.js` that a built module imports its file's hash, as
    the page's references get theirs."""
    path = OUT / name
    text = path.read_text(encoding="utf-8")

    def hashed(m):
        digest = hashlib.sha256((OUT / m[2]).read_bytes()).hexdigest()[:10]
        return f'{m[1]}"./{m[2]}?v={digest}";'

    path.write_text(re.sub(r'^(import .* from )"\./([\w-]+\.js)";$', hashed, text, flags=re.M), encoding="utf-8")


def sizes(files):
    data = b"".join(f.read_bytes() for f in files)
    return len(data), len(gzip.compress(data, 9))


def check_js():
    """Type-checks the page's scripts, as Wherewith's site does."""
    tsc = SITE / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        raise SystemExit("Install the site's tools first (npm ci --prefix site), or pass --no-check.")
    subprocess.run(["npm", "run", "-s", "check"], cwd=SITE, check=True)


def main():
    if not (JS / "argmas" / "argmas.internal.js").exists() or not (PY / "argmas").exists():
        raise SystemExit("Build the libraries first: temper build -b js -b py")
    if "--no-check" not in sys.argv[1:]:
        check_js()

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    # GitHub Pages serves files as they are, without Jekyll.
    (OUT / ".nojekyll").touch()
    for name in ["style.css", "app.js", "packrun.js"]:
        shutil.copyfile(SITE / name, OUT / name)
    link_modules("app.js")

    # The library, for running `pack` in the page.
    lib = []
    for package in ["argmas", "temper-core"]:
        for path in sorted((JS / package).glob("*.js")):
            copy_module(path, OUT / "lib" / package / path.name)
            lib.append(OUT / "lib" / package / path.name)
    (OUT / "tour").mkdir()
    shutil.copyfile(TOUR / "js" / "tour.js", OUT / "tour" / "tour.js")

    runs = run_pack(tour_cases())
    check_transcript(runs)
    first = run_pack([TRY_FIRST])[0]
    examples = run_examples()

    page = (SITE / "index.html").read_text(encoding="utf-8")
    parts = {
        "HERO_CODE": tour_code("declare"),
        "HERO_RUNS": hero(runs),
        **try_it(runs, first),
        "CASE_COUNT": str(len(runs)),
        "STYLES_CODE": example_code("styles"),
        "STYLES": styles_html(examples["styles"]),
        "SUBCOMMANDS_CODE": example_code("subcommands"),
        "SUBCOMMANDS": subcommands_html(examples["subcommands"]),
        "COMPLETIONS_CODE": example_code("completions"),
        "COMPLETIONS_DEMO": completion_demo(examples["completions"]["answers"]),
        "COMPLETIONS_ANSWERS": completion_answers(examples["completions"]["answers"]),
        "COMPLETIONS_INSTALL": install_table(),
        "COMPLETIONS_SCRIPTS": scripts_html(examples["completions"]["scripts"]),
        "MESSAGES_CODE": example_code("messages"),
        **messages_html(examples["messages"]),
        "RESULTS_CODE": tour_code("results"),
        "START": start_html(),
    }
    for key, value in parts.items():
        if f"<!--{key}-->" not in page:
            raise SystemExit(f"index.html has no <!--{key}-->.")
        page = page.replace(f"<!--{key}-->", value)
    left = re.findall(r"<!--[A-Z_]+-->", page)
    if left:
        raise SystemExit(f"Unfilled in index.html: {', '.join(left)}")
    # Each reference gets its file's hash, so browsers fetch changed files
    # instead of reusing cached ones.
    for ref in ["style.css", "app.js"]:
        digest = hashlib.sha256((OUT / ref).read_bytes()).hexdigest()[:10]
        page = page.replace(f'"{ref}"', f'"{ref}?v={digest}"')
    (OUT / "index.html").write_text(page, encoding="utf-8")

    raw, gz = sizes([OUT / "index.html", OUT / "style.css", OUT / "app.js", OUT / "packrun.js"])
    print(f"The page, with its style and scripts: {raw} bytes, {gz} gzipped")
    raw, gz = sizes(lib)
    print(f"Argmas and Temper's JS runtime, loaded to run pack: {raw} bytes, {gz} gzipped")
    print(f"Built {rel(OUT)}")


if __name__ == "__main__":
    main()
