# Argmas

Command-line arguments, parsed the same way in every language. Declare a
command once, in Temper, and get typed options, subcommands, generated
help, clear errors with suggestions, and shell completions, with the same
behavior in C++, C#, Java, JavaScript, Lua, Python, and Rust.

**Status: early.** Options, flags, positional arguments, environment
fallbacks, subcommands, argument styles, help, errors, and shell
completions work.
See [docs/design.md](docs/design.md). It stays beta until Temper's
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

Subcommands are commands of their own, with their own arguments and
help, and options marked `inherited` work before or after their names:

```temper
let git = new Command({ name: "minigit", about: "Track files." });
let quiet = git.flag({ name: "quiet", short: "q", inherited: true });
let add = git.command({ name: "add", about: "Add files." });
let force = add.flag({ name: "force", short: "f", help: "Add ignored files too." });
let paths = add.positionals(strings, { name: "PATH", min: 1 });
let rm = git.command({ name: "rm", about: "Remove files.", aliases: ["remove"] });

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
candidates. `cmd.exe` has no programmable completion, so it isn't
supported. Options and values can have completers that find values
when the program runs, such as branch names; the
[design](docs/design.md#completions) has the details.

A program usually matches on the result: `Args` to run, `Output` to
print and exit with status 0, and `ArgError` to print to standard error
and exit with status 2. Parsing touches nothing outside: the program
passes the arguments and, for environment variables, an `Environment`.
The [design](docs/design.md) has how each corner case is decided,
from `-` alone to negative numbers.

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

## Development

Written with Claude Code and Opus 5.5.

Run tests with [Temper](https://temperlang.dev/), on the interpreter
while working:

    temper test -b interp

Or on every backend:

    temper test -b cpp -b csharp -b java -b js -b lua -b py -b rust

Source files in `src/` are literate Markdown: `command.temper.md`
declares commands and their arguments, `parse.temper.md` parses,
`help.temper.md` writes help, `style.temper.md` has the argument
styles, `values.temper.md` has the value types, `complete.temper.md`
answers completions, and `shells.temper.md` has the shells' scripts,
with tests beside them in `-tests` files and subcommands' tests in
`subcommand-tests.temper.md`. `tour-tests.temper.md` checks the
examples above.

`tests/shells/run.py` installs each shell's script in a throwaway
directory and completes command lines in the real shells, skipping
those not installed:

    uv run tests/shells/run.py [SHELL ...]

## License

Apache-2.0 OR MIT, at your option; see [COPYRIGHT](COPYRIGHT).
