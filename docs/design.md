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
key for reading it. As built in the first slice:

```temper
let cli = new Command({ name: "frob", about: "Frobnicate files." });
let verbose = cli.flag({ name: "verbose", short: "v", help: "Say more." });
let level = cli.optionOr(ints, 3, { name: "level", help: "How hard." });
let output = cli.option(strings, { name: "output", short: "o" });
let files = cli.positionals(strings, { name: "FILE", min: 1 });

when (cli.parse(argv, env)) {
  is Args -> ...;     // args.get(level) is an Int, args.get(output) a String?
  is Output -> ...;   // --help or --version: print it, exit 0
  is ArgError -> ...; // print error.text(), exit 2
}
```

- `args.get(level)` is an `Int`, checked at compile time; a misspelled
  option is a misspelled variable, so it doesn't compile.
- The method, not a setting, decides the value's type: `flag`
  (Boolean), `count` (Int), `option` (`T?`, null when not given),
  `optionOr` (`T`, with a default), `required` (`T`), `repeated`
  (`List<T>`), `positional` (`T`, exactly one), and `positionals`
  (`List<T>`, from `min` to `max`).
- Settings are object literals (property bags), Temper's way of naming
  arguments; backends without named arguments get builders, as elsewhere
  in Temper's output.
- Value types are small parser objects (`ints`, `floats`, `strings`,
  and `choices([...])` so far; `path` and `duration` later; and
  user-defined ones through the `ValueType` interface), each with its
  own error messages and, later, completion hints.
- The environment comes in through an `Environment` interface the
  program implements (or `MapEnvironment` over a map), so parsing
  touches nothing outside.

### Typed results through `@json`

Not built yet. For a single typed result object, Argmas can turn the parsed arguments into
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

As built in the second slice:

```temper
let cli = new Command({ name: "frob", about: "Frobnicate files." });
let verbose = cli.count({ name: "verbose", short: "v", inherited: true });
let add = cli.command({ name: "add", about: "Add a file.", aliases: ["a"] });
let force = add.flag({ name: "force", short: "f" });
let rm = cli.command({ name: "rm", about: "Remove a file." });
let remote = cli.command({ name: "remote", about: "Manage remotes." });
let remoteAdd = remote.command({ name: "add", about: "Add a remote." });

// After matching `Output` and `ArgError` as above:
let args = cli.parse(argv, env) as Args orelse ...;
when (args.command) {
  add -> ...;        // args.get(force), args.get(verbose)
  rm -> ...;
  remoteAdd -> ...;
  else -> ...;
}
```

- `cli.command({ ... })` returns a `Command` with its own arguments,
  help, errors, and subcommands; `SubcommandSpec` has `name`, `about`,
  `aliases`, and `commandOptional`.
- Options and flags marked `inherited` are accepted by every
  subcommand below the command declaring them, before or after the
  subcommand's name, and help lists them under each.
- One `Args` holds the values of the command that ran and every
  command above it, so `args.get` reads any handle; a handle of a
  command that didn't run reads as absent.
- `args.command` is the command that ran: the last subcommand named,
  or the top command when none was.

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

Each corner case gets one decision, written down here, and a test
(in `src/parse-tests.temper.md` unless noted):

- **`-` alone** is positional (conventionally standard input), and can
  be a value: `-o -`.
- **`--` itself** ends options once; a later `--` is positional.
- **Options after positionals** are still options (GNU style), until
  `--`.
- **A value starting with `-`:** a separate value (`--opt value`,
  `-o value`) can't start with `-`, except `-` alone and negative
  numbers; that's a missing value, and the message shows the
  `--opt=-x` form. Attached values (`--opt=-x`, `-o-x`) take anything.
- **Negative numbers** (`-5`, `-1.5`, `-2e3`) are values and
  positionals, unless the command has a short option that's a digit;
  then they're options, as in argparse.
- **`--opt=`** gives the empty string, which its type may refuse (`ints`
  does, `strings` doesn't).
- **`-o=file`** drops one `=` after a short option, giving `file`, as
  clap does (getopt would give `=file`).
- **Bundles:** in `-vql9`, flags count until an option, which takes the
  rest (`9`), even letters that are options (`-ovq` is `-o vq`).
- **Flags given a value** (`--quiet=yes`, `--no-color=1`) are errors.
- **Repeats:** a plain flag given twice is still true; a counted flag
  counts; an option's last value wins unless it's `repeated`.
- **`--no-NAME`** works only for flags declared negatable, setting them
  false (a counted flag back to 0); the last of `--color` and
  `--no-color` wins. For other names it's an unknown option whose
  message says so.
- **No prefix matching** of long options; `--verb` is unknown, though
  the error suggests `--verbose`.
- **Suggestions:** the one name the typed name is a prefix of, or else
  the nearest by edit distance (a swap of neighbors counts as one edit,
  so `--hlep` finds `--help`), within a third of the typed length (at
  least 1); ties go to the earliest declared. `-verbose` suggests
  `--verbose`, `--v` suggests `-v`, and an invalid choice suggests the
  nearest choice.
- **Help and version win:** `--help`, `-h` (also in a bundle, `-vh`),
  and `--version` anywhere before `--` win over every error, help over
  version, so a user can always ask for help. A program may take
  `help`, `h`, or `version` for itself; the rest stay built in.
- **Error order:** otherwise the first error is reported: mistakes in
  the spec, then argument errors in argument order, then positional
  counts and values, then environment values, then missing required
  options.
- **Environment:** read only when the argument isn't given; an empty
  variable counts as unset; a repeated option's variable is one value,
  not split; a flag's takes `1`, `true`, `yes`, or `on`, or `0`,
  `false`, `no`, or `off`, in any case, and a counted flag's a count.
- **Positional lists:** each gets its minimum, and the rest go to the
  earliest that takes more, so `SRC... DEST` works.
- **Spec mistakes** (a name declared twice, a short name that isn't one
  character, a name starting with `-` or holding `=` or a space, or a
  positional count range that allows nothing) are reported by `parse`
  as an `invalidSpec` error, not a panic where they're declared.
- **Values** (`src/values-tests.temper.md`): `ints` takes an optional
  sign and ASCII digits, leading zeros allowed, within 32 bits; `floats`
  takes an optional sign, digits with an optional point and fraction
  (`.5` and `5.` too), and an optional exponent, finite only; `choices`
  match exactly, case included.
- **Help text** (`src/help-tests.temper.md`): columns are counted in
  code points; help starts two columns after the longest name, at most
  two fifths of the width in (and at least 16); longer names put their
  help on the next line; notes (`[default: 3]`, `[env: X]`,
  `[choices: a, b]`, `[required]`, `[repeatable]`) are never split; a
  negatable flag shows as `--[no-]color`.
- **Error text:** `frob: <message>`, then the usage, then
  `Try 'frob --help' for more information.` when `--help` is built in.

Subcommands (`src/subcommand-tests.temper.md`):

- **Selection:** the first positional argument that names a
  subcommand, or one of its aliases, selects it; the arguments after
  it are the subcommand's, which can select a subcommand of its own.
  Aliases give the same command, with its own name in `args.command`
  and in help.
- **Inherited options** (clap's `global`, picocli's inherited
  options) are accepted before or after the name of any subcommand
  below the command declaring them, at any depth, and count the same
  either way: an option's last value wins and a counted flag adds up
  across both places. Other options go before the subcommand's name,
  as in git, and a subcommand's options go after it.
- **A command with positional arguments and subcommands** gets its own
  positional arguments before the subcommand's name. A word that names
  a subcommand always selects it; after `--`, none does, so `--`
  passes such a word as a positional argument. Other words are
  positional arguments, not unknown commands.
- **Unknown subcommands:** in a command with subcommands and no
  positional arguments, any other word is an error, suggesting the
  nearest name or alias (or `help`) as for options.
- **Missing subcommands:** with none given, an error lists the
  subcommands' names, unless the spec sets `commandOptional`; then
  `args.command` is the command itself, and the program does what it
  likes, such as running one of them by default. The usage line ends
  with `COMMAND`, or `[COMMAND]` when it's optional. There's no
  declared default subcommand: parsing its options at the top would
  make `frob --force` work but `frob --help` not list `--force`.
- **`help` subcommand:** a command with subcommands has a built-in
  `help`, unless the program declares a subcommand of that name;
  `frob help remote add` is `frob remote add --help`. The words after
  it name subcommands, each of the one before; `-h`, `--help`, and
  `help` among them are skipped, and any other word that names none is
  an unknown command. In a subcommand without subcommands of its own,
  `help` is a positional argument like any other.
- **`--help`** gives the help of the command it's given to (`frob
  --help add` is `frob`'s), the last one when given more than once,
  and wins over errors as at the top: `frob bogus --help` gives
  `frob`'s help, which lists the commands.
- **`--version`** is built in for the top command only, as in clap;
  `frob add --version` is an unknown option.
- **Error order:** argument errors in argument order, then a missing
  subcommand, then positional counts, then environment values, then
  missing required options, each of the last three from the top
  command down. An error shows the usage of the command it happened
  in, after the top command's name: `frob: ...`, then
  `Usage: frob add ...` and `Try 'frob add --help' ...`.
- **Spec mistakes:** subcommand names and aliases follow the rules for
  long names, and no two under one command share one; a subcommand's
  option can't have the long or short name of an option inherited from
  above. They're reported for the whole tree, ending with where they
  are (`in frob add`). The same name at two levels is fine when it
  isn't inherited.
- **Parsing a subcommand** directly is parsing its path from the top
  command: `add.parse(argv)` is `cli.parse(["add", ...argv])`.
- **Help:** a command with subcommands lists them under `Commands:`,
  with each one's about text and `[aliases: ...]`, then `help`, before
  its arguments and options, all in one column. A subcommand's usage
  starts with its path (`Usage: frob add [OPTIONS] FILE...`), and its
  options list its own, then those inherited from its parent, then
  from further up.

## Argument styles (planned, after subcommands)

A `style` setting on `Command` chooses how options are written; the same
spec drives parsing, help, and completions in each style:

| Style | Looks like | Common in |
|---|---|---|
| `gnu` (default) | `-v`, `-abc`, `--verbose`, `--out=f` | most Unix tools |
| `singleDash` | `-verbose`, `-out=f`, `-out f` | Go's `flag`, Java's tools |
| `windows` | `/v`, `/out:f`, `/?` | Windows command-line tools |

- Bundling (`-abc`) exists only in `gnu`; `singleDash` treats `-abc` as
  one long name.
- `windows` also accepts `-` and `--` forms, as most current Windows tools
  do, and `/?` asks for help.
- A command may accept two styles at once, for a tool moving from one to
  the other; help shows the first.
- Not planned: `+x` to turn an option on, now rare.

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

## Temper constraints met so far

Limits of today's Temper (with tempest, the new compiler) that shaped
the API, and the choice made for each:

- **Type parameters can't be nullable**, so one `Arg<T>` can't cover an
  option that may be absent (`T` would be `Int?`). Handles split into
  `Arg<T>` and `MaybeArg<T>`, and `Args.get` is two `@overload`s: in
  Temper it's `args.get(h)` for both, and other languages see their
  own names, `getValue` and `getMaybe`.
- **A setting can't change a type**, so a default, being required, and
  repeating are methods (`optionOr`, `required`, `repeated`), not bag
  properties, and counted flags are `count`, not a `counted` setting.
- **Bags are constructor calls**, so `new Command({ ... })` passes a
  `CommandSpec` bag as `Command`'s one parameter, and each method's bag
  class comes from its parameter's type. Tempest target-types bags; the
  older Kotlin compiler matches property names instead, and since
  `FlagSpec` and `OptionSpec` share theirs (as do `CommandSpec` and
  `SubcommandSpec`), it may need `{ class: FlagSpec, ... }`.
- **No casts to a type parameter**, so a parsed result keeps each
  value's text, already checked, and a handle parses it again when read.
- **`int`, `float`, and `string` are keywords in several target
  languages**, so the value types are `ints`, `floats`, and `strings`,
  with `choices([...])` to match.
- **Only per-class `private`**, so what handles and the parser share
  (`Param`, `Found`, `Command.findLong`) is public, documented as for
  value types and tools.
- **A `when` over the sealed `ParseResult`** that produces a value still
  needs an `else` branch with tempest.
- **No identity comparison of objects**, and a class's `==` is its
  own, so `Command` defines `==` (with `@operator("==")`) as having
  the same path (`frob remote add`). That lets a program match
  `args.command` in a `when`; two separately built commands with the
  same path compare equal, so compare commands of one tree.
- **`==` on a nullable `Command` isn't translated** (tempest's code
  generation doesn't take a user-defined `==` through `?`), so
  `args.command` is never null: it's the top command when no
  subcommand ran.
- **`global` is a keyword in Python**, where generated code would have
  `global_`, so the setting is `inherited`, picocli's word for it.
- **Enums aren't translated well yet**, so kinds (`ErrorKind`,
  `ParamKind`, `Source`) are classes with static instances and
  `@auto("==")`.

## Open questions

- Subcommands: whether a declared default subcommand is worth having
  beside `commandOptional`; whether aliases need hiding from help;
  whether `--version` should reach subcommands; and a hint when a
  parent's option comes after a subcommand's name ("give --dir before
  add").
- A flag that defaults to true, for `--no-color` style flags: today a
  flag is false unless given or set by its environment variable.
- Options taking `Int64` values.
- Help counts columns in code points, so wide characters (most Chinese,
  Japanese, and Korean ones) take more room than counted.
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
