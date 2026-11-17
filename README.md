# Argmas

Command-line arguments, parsed the same way in every language. Declare a
command once, in Temper, and get typed options, subcommands, generated
help, clear errors with suggestions, and shell completions, with the same
behavior in C++, C#, Java, JavaScript, Lua, Python, and Rust.

**Status: early.** Options, flags, positional arguments, environment
fallbacks, subcommands, argument styles, help, errors, shell
completions, and a message table for translations work.
See [docs/design.md](docs/design.md), and the
[project site](https://temperlang.github.io/argmas/) to try it in the
browser. It stays beta until Temper's
translations reach 1.0, and the API may change.

## Example

In Temper:

```temper
let cli = new Command({ name: "frob", about: "Frobnicate files.", version: "1.0.0" });
let verbose = cli.count({ name: "verbose", short: "v", help: "Say more." });
let level = cli.optionOr(ints, 3, { name: "level", short: "l", help: "How hard.", env: "FROB_LEVEL" });
let mode = cli.option(choices(["fast", "slow"]), { name: "mode", help: "How to go about it." });
let files = cli.positionals(strings, { name: "FILE", min: 1, help: "Files to frobnicate." });

// Each value has its handle's type, checked when the program compiles.
let args = cli.parse(["-vv", "--level=5", "a.txt", "b.txt"]) as Args orelse panic();
args.get(verbose); // 2, an Int
args.get(level);   // 5, an Int (3 by default, or from FROB_LEVEL)
args.get(mode);    // null, a String?
args.get(files);   // ["a.txt", "b.txt"], a List<String>

// Mistakes are values, not exceptions, with a suggestion when there's
// a near miss.
let error = cli.parse(["--levle", "5", "a.txt"]) as ArgError orelse panic();
error.text();
// frob: unknown option --levle; did you mean --level?
// Usage: frob [OPTIONS] FILE...
// Try 'frob --help' for more information.

// --help gives the help, wrapped to the width given (80 by default).
(cli.parse(["--help"]) as Output orelse panic()).text();
// Frobnicate files.
//
// Usage: frob [OPTIONS] FILE...
//
// Arguments:
//   FILE...              Files to frobnicate.
//
// Options:
//   -v, --verbose        Say more. [repeatable]
//   -l, --level <LEVEL>  How hard. [default: 3] [env: FROB_LEVEL]
//       --mode <MODE>    How to go about it. [choices: fast, slow]
//   -h, --help           Show this help and exit.
//       --version        Show the version and exit.
```

A flag can be `on` unless turned off, as `--no-color` style flags
are, and `ints64` takes integers past 32 bits:

```temper
let color = cli.flag({ name: "color", help: "Color the output.", on: true });
let size = cli.optionOr(ints64, 4294967296i64, { name: "size", help: "Bytes to read." });
// Help shows `--[no-]color  Color the output. [default: on]`; long
// options are never matched by prefix, so `--siz` is an error.
```

Subcommands are commands of their own, with their own arguments and
help, and options marked `inherited` work before or after their names:

```temper
let git = new Command({ name: "minigit", about: "Track files." });
let quiet = git.flag({ name: "quiet", short: "q", inherited: true });
let add = git.subcommand({ name: "add", about: "Add files." });
let force = add.flag({ name: "force", short: "f", help: "Add ignored files too." });
let paths = add.positionals(strings, { name: "PATH", min: 1 });
let rm = git.subcommand({ name: "rm", about: "Remove files.", aliases: ["remove"] });

let args = git.parse(["add", "-qf", "a.txt"]) as Args orelse panic();
when (args.command) {
  add -> args.get(paths);  // ["a.txt"], with args.get(force) and args.get(quiet) true
  rm -> ...;
  else -> ...;
}
// `minigit help add` and `minigit add --help` give add's help, and
// `minigit ad` says "unknown command 'ad'; did you mean add?".
```

Options are written GNU style by default (`-v`, `-vq`, `--out=f`), or
in the style a command chooses, with help to match: `Style.singleDash`
(`-verbose`, `-level=5`, as in Go) or `Style.windows` (`/v`,
`/out:f`, `/?`):

```temper
let cli = new Command({ name: "frob", style: Style.windows });
let verbose = cli.flag({ name: "verbose", short: "v", help: "Say more." });
let out = cli.option(strings, { name: "out", help: "Where to write." });
let args = cli.parse(["/V", "/out:C:\\x.txt"]) as Args orelse panic();
args.get(verbose); // true: Windows names ignore case
args.get(out);     // "C:\\x.txt"
// `frob /?` gives the help:
// Usage: frob [OPTIONS]
//
// Options:
//   /v, /verbose    Say more.
//       /out:<OUT>  Where to write.
//   /?, /help       Show this help and exit.
```

Shells complete command lines by asking the program, through a short
script Argmas prints for bash, zsh, fish, and PowerShell, so
completions always match what the program accepts, values included:

```temper
let cli = new Command({ name: "frob", completions: true });
let verbose = cli.flag({ name: "verbose", short: "v", help: "Say more." });
let mode = cli.option(choices(["fast", "slow"]), { name: "mode", help: "How to go about it." });
let out = cli.option(paths, { name: "out", help: "Where to write." });

// What a shell gets for `frob --v<Tab>`, `frob --mode <Tab>`, and
// `frob --out=<Tab>`: candidates, with descriptions, then what else
// the shell should complete.
cli.complete(["--v"]).text();        // "--verbose\tSay more.\n:none\n"
cli.complete(["--mode", ""]).text(); // "fast\nslow\n:none\n"
cli.complete(["--out="]).text();     // ":files --out=\n": files, after --out=
```

The script runs `frob __complete INDEX WORD...` as the user presses
Tab, which `cli.parse` answers with an `Output`, so a program that
prints `Output` already serves completions. With `completions: true`,
`frob --completions SHELL` prints the script (or a program prints
`cli.completionScript(Shell.bash)` its own way). Argmas only prints
it; users install it where their shell looks:

| Shell | Install |
|---|---|
| bash 4.4+ | `frob --completions bash > ~/.local/share/bash-completion/completions/frob` (with the bash-completion package), or `source <(frob --completions bash)` in `~/.bashrc` |
| zsh | `frob --completions zsh > ~/.zfunc/_frob`, with `fpath=(~/.zfunc $fpath)` before `compinit` in `~/.zshrc` |
| fish | `frob --completions fish > ~/.config/fish/completions/frob.fish` |
| PowerShell 5.1+ | `frob --completions powershell \| Out-String \| Invoke-Expression` in your profile (`$PROFILE`) |

zsh, fish, and PowerShell show descriptions; bash shows only the
candidates. Quotes typed on the line are removed before the program
sees a word (`frob --branch "my w<Tab>` asks about `my w`), and every
shell quotes what it inserts (`"my work"`). `cmd.exe` has no programmable completion, so it isn't
supported. Options and values can have completers that find values
when the program runs, such as branch names; the
[design](docs/design.md#completions) has the details.

A program usually matches on the result: `Args` to run, `Output` to
print and exit with status 0, and `ArgError` to print to standard error
and exit with status 2. Parsing touches nothing outside: the program
passes the arguments and, for environment variables, an `Environment`.
The [design](docs/design.md) has how each corner case is decided,
from `-` alone to negative numbers. To pass the values around as one
object, a program builds its own record, dataclass, or struct from
`args`, each field still typed by its handle; the design says
[why](docs/design.md#typed-results) Argmas doesn't fill one itself.

## Messages and translations

Everything Argmas writes itself, from `Usage:` and `Options:` to each
error, suggestion, and completion script's comment, comes from one
table of messages, in English unless the program sets its own. Each
message has a stable key and named placeholders, so a translation can
put them in its own order:

```temper
let cli = new Command({ name: "frob" });
cli.setMessage("usage", "Aufruf: {command}");
cli.setMessage("error.unknownOption.suggest", "unbekannte Option {option}; meinten Sie {suggestion}?");
// Or many at once, such as a whole table: cli.setMessages(german), a Map.
```

Messages not set stay English. A key or placeholder Argmas doesn't
have is reported as a mistake in the spec on the first run, so typos
can't ship. The [design](docs/design.md#messages) lists every key with
its English text. What the program declares itself, such as help for
its options, is the program's to translate.

Argmas never reads the environment for a language; the program picks
a table and passes it. On Linux and macOS, the language is in the
first set of `LC_ALL`, `LC_MESSAGES`, and `LANG`, as in
`de_DE.UTF-8`; `C` and `POSIX` mean the default. On Windows, it's the
user's display language (`GetUserDefaultUILanguage`, or .NET's
`CultureInfo.CurrentUICulture`). In Python, for example:

```python
import os, sys

def language():
    if sys.platform == "win32":
        import ctypes, locale
        return locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "")
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(name):
            return os.environ[name].split(".")[0].split("@")[0]  # de_DE
    return ""

table = TABLES.get(language().split("_")[0])  # your tables, by language
if table:
    cli.set_messages(table)
```

## Languages

Made in Temper, Argmas supports these languages, and its tests run on
each:

- C++
- C\#
- Java
- JavaScript
- Lua
- Python
- Rust

A [tour](demos/README.md), `pack`, uses Argmas from each one, with
identical output, and [docs/languages.md](docs/languages.md) shows
what the API looks like in each.

## Releases

Argmas is beta, as all Temper libraries are until Temper's
translations reach 1.0, so its API may still change, and each
[release](https://github.com/temperlang/argmas/releases) is marked a
pre-release. It isn't on any package registry yet: each release
carries every language's package, with Temper's runtime
(`temper-core`) and std beside it, at the version Argmas was built
with, so it installs from the release's files alone.

Download a release's files, and check them:

    gh release download v0.1.0 -R temperlang/argmas -D argmas-0.1.0
    cd argmas-0.1.0 && sha256sum -c SHA256SUMS && cd ..

Or download single files from the release's page, or with
`curl -LO https://github.com/temperlang/argmas/releases/download/v0.1.0/FILE`
(`sha256sum -c --ignore-missing SHA256SUMS` checks just those). Then,
for each language:

- C++: `tar xzf argmas-cpp-0.1.0.tar.gz`, then in your CMakeLists.txt
  `add_subdirectory(argmas-cpp-0.1.0/argmas)` and
  `target_link_libraries(app PRIVATE argmas)`
- C#: `unzip argmas-csharp-0.1.0.zip`, then
  `dotnet add reference argmas-csharp-0.1.0/argmas/src/Argmas.csproj`
- Java: `unzip argmas-java-0.1.0-maven.zip -d ~/.m2/repository` (a
  Maven repository, which Gradle can also use as a `maven { url }`),
  then depend on `argmas:argmas:0.1.0`
- JavaScript: `npm install ./argmas-0.1.0/*.tgz`
- Lua: `tar xzf argmas-lua-0.1.0.tar.gz`, then put
  `argmas-lua-0.1.0/?/init.lua;argmas-lua-0.1.0/?.lua` on `LUA_PATH`
  (or `package.path`); its rockspecs don't yet install with LuaRocks
- Python: `pip install --no-index --find-links argmas-0.1.0 argmas` (or
  the same with `uv pip install`)
- Rust: `tar xzf argmas-rust-0.1.0.tar.gz`, then in Cargo.toml
  `argmas = { path = "argmas-rust-0.1.0/argmas" }`

[RELEASING.md](RELEASING.md) says how releases are made.

## Development

Written with Claude Code and Opus 5.5.

Run tests with [Temper](https://temperlang.dev/), on the interpreter
while working:

    temper test -b interp

Or on every backend:

    temper test -b cpp -b csharp -b java -b js -b lua -b py -b rust

Source files in `src/` are literate Markdown: `command.temper.md`
declares commands and their arguments, `parse.temper.md` parses,
`help.temper.md` writes help, `messages.temper.md` has the
messages, `style.temper.md` has the argument styles, `values.temper.md` has the value types, `complete.temper.md`
answers completions, and `shells.temper.md` has the shells' scripts,
with tests beside them in `-tests` files and subcommands' tests in
`subcommand-tests.temper.md`. `tour-tests.temper.md` checks the
examples above.

Run the tours, after `temper build` for their languages, and compare
their output (see [demos](demos/README.md)):

    uv run demos/run.py [LANGUAGE ...]

`tests/shells/run.py` installs each shell's script in a throwaway
directory and completes command lines in the real shells, skipping
those not installed:

    uv run tests/shells/run.py [SHELL ...]

`tests/reference/run.py` parses the same command lines with Argmas,
glibc's `getopt_long`, Python's argparse, and Rust's clap, and fails on
any difference not documented in `tests/reference/differences.toml`,
skipping references it can't build (getopt needs `cc` on glibc, clap
needs `cargo`):

    uv run tests/reference/run.py [-v] [PARSER ...]

The [site](https://temperlang.github.io/argmas/) is built from the
tours and their examples, running the JavaScript and Python libraries
for everything Argmas prints on it (see `site/build.py`):

    npm ci --prefix site
    temper build -b js -b py
    uv run site/build.py
    python3 -m http.server --bind 127.0.0.1 -d site/build

CI ([test.yml](.github/workflows/test.yml)) runs the tests on every
backend, the tours, the reference parsers, and the shells: bash, zsh,
fish, and PowerShell on Linux, bash, zsh, and fish on macOS, and
PowerShell on Windows. A `v` tag makes a release
([release.yml](.github/workflows/release.yml), [RELEASING.md](RELEASING.md)).

## License

Apache-2.0 OR MIT, at your option; see [COPYRIGHT](COPYRIGHT).
