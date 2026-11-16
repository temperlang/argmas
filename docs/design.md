# Argmas design

Draft, 2026-11-16. What Argmas is for, the API it offers without
metaprogramming, the behavior it guarantees in every language, and the
questions still open. Code below is illustrative Temper; names and details
will change as it's built.

## Goals

- **An API people don't mind.** The parsers people like most use derive
  style (clap's derive in Rust, Typer and Click in Python, picocli in
  Java). Temper can't do that yet, so Argmas aims for the next best: typed
  values with no casts or string lookups, a spec that reads top to bottom,
  and good errors for free.
- **The same command-line behavior everywhere.** A tool shipped in several
  languages (an SDK's command-line tool, an internal tool ported to another
  stack) gets identical flags, help text, errors, and completions from one
  spec, so users can't tell which implementation they're running.
- **Conventional behavior, not new rules.** POSIX and GNU conventions as
  people know them from `getopt_long`, clap, and argparse, with their
  corner cases decided once and documented.
- **Pure Temper.** Parsing, help, and completions are pure functions;
  only reading `argv`, the environment, and the terminal width, and
  printing and exiting, touch the host.

## The API without metaprogramming

### Typed handles

Each argument is declared as a value that knows its type and is also the
key for reading it:

```temper
let cli = new Command({ name: "frob", about: "Frobnicate files." });
let verbose = cli.flag({ name: "verbose", short: "v", help: "Say more." });
let level = cli.option(int({ name: "level", default: 3, help: "How hard." }));
let files = cli.positionals(path({ name: "FILE", min: 1 }));

let args = cli.parse(argv) orelse cli.exitWithUsage();
if (args.get(verbose)) { ... }
let n: Int = args.get(level);
```

- `args.get(level)` is an `Int`, checked at compile time; a misspelled
  option is a misspelled variable, so it doesn't compile.
- Settings are object literals (property bags), Temper's way of naming
  arguments; backends without named arguments get builders, as elsewhere
  in Temper's output.
- Value types are small parser objects (`int`, `float`, `string`, `path`,
  `choice([...])`, `duration`, and user-defined ones through an
  interface), each with its own error messages and completion hints.

### Typed results through `@json`

For a single typed result object, Argmas can turn the parsed arguments into
the same tree `@json` decodes, so a `@json` class gets filled in directly:

```temper
@json class Options {
  public verbose: Boolean;
  public level: Int;
  public files: List<String>;
}
let options = cli.parseInto(argv, Options.jsonAdapter()) orelse ...;
```

This reuses machinery Temper already has. Help text still comes from the
spec, since classes don't carry their docs at run time (see "Later:
metaprogramming").

### Subcommands

```temper
let add = cli.command({ name: "add", about: "Add a file." });
let addForce = add.flag({ name: "force", short: "f" });
let rm = cli.command({ name: "rm", about: "Remove a file." });

let args = cli.parse(argv) orelse cli.exitWithUsage();
when (args.command) {
  add -> { ... args.get(addForce) ... }
  rm -> { ... }
}
```

Options declared on a command apply to its subcommands when marked
`global`; each subcommand has its own help and errors.

## Behavior, the same in every language

- **Short and long options:** `-v`, `-vvv` (counted), `-abc` (bundled),
  `-o file` and `-ofile`, `--output file` and `--output=file`,
  `--no-color` for negatable flags, unique prefixes of long options only
  if enabled.
- **`--`** ends options; everything after is positional.
- **Repeated options** collect into lists, or the last wins, as declared.
- **Environment fallbacks:** an option may name an environment variable
  read when it isn't given; precedence is argument, then environment,
  then default.
- **Help:** `-h` and `--help` print usage and every option with its help,
  default, environment variable, and choices, wrapped to the terminal
  width (or 80 when unknown); `--version` when a version is set.
- **Errors:** one clear line with the usage hint, and suggestions for near
  misses ("unknown option --verbos; did you mean --verbose?"), exit status
  2 as is conventional.
- **Completions:** generated scripts for bash, zsh, fish, and PowerShell,
  from the same spec, including value hints (files, choices).
- **Text:** arguments are Unicode strings; how each platform's raw
  arguments (bytes on POSIX, UTF-16 on Windows) reach them is handled per
  backend, with invalid sequences reported, not silently replaced.

Each corner case (`-` alone, an option value starting with `-`, negative
numbers, options after positionals, `--opt=` empty) gets one decision,
written down here before it's built, and a test.

## Testing

- **Parsing tables:** argv in, parsed result or error out, run on every
  backend; the same table is the behavior spec.
- **Against reference parsers:** the same inputs through `getopt_long`,
  clap, and argparse where they claim the same conventions, with every
  difference either matched or documented.
- **Help and errors:** goldens of the exact text.
- **Completions:** the generated scripts run in real bash, zsh, fish, and
  PowerShell in CI, completing sample command lines.
- **Tours:** a small example program in each language, checked in CI, as
  the other Temper libraries have.

## Later: metaprogramming

Derive style, declaring a class and getting the parser from it, needs one
of these in Temper, which are ideas, not plans:

- **Portable reflection metadata:** the compiler emitting each class's
  fields, types, defaults, and doc comments as a table every backend can
  read, so `cli.fromClass<Options>()` and help from doc comments work in
  pure Temper.
- **Compile-time reflection** in Temper code, run by the interpreter during
  compilation.
- **A built-in derive decorator** like `@json`, generating the parser per
  backend.

The typed-handle API stays either way; derive style would build on it.

## Open questions

- Value types beyond the basics: dates and durations need a format; paths
  need per-platform rules (Windows drive letters, `~`).
- Whether `parseInto` with `@json` covers enough, or a result type per
  command is better.
- Prefix matching of long options: off by default (it breaks when options
  are added), on by choice?
- Config files (TOML, INI) as another layer under the environment, or out
  of scope.
- How much terminal handling (color, width) belongs here, and how much in
  each host.
