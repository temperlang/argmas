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
  (`List<T>`, from `min` to `max`). Each returns its handle as
  `Arg<T>`, or `MaybeArg<T>` for `option`, the types `args.get`
  takes, so every language sees the value's type in the handle's.
- Settings are object literals (property bags), Temper's way of naming
  arguments; backends without named arguments get builders, as elsewhere
  in Temper's output.
- Value types are small parser objects (`ints`, `floats`, `strings`,
  `paths`, `directories`, and `choices([...])` so far; `duration`
  later; and user-defined ones through the `ValueType` interface),
  each with its own error messages and completions.
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
let add = cli.subcommand({ name: "add", about: "Add a file.", aliases: ["a"] });
let force = add.flag({ name: "force", short: "f" });
let rm = cli.subcommand({ name: "rm", about: "Remove a file." });
let remote = cli.subcommand({ name: "remote", about: "Manage remotes." });
let remoteAdd = remote.subcommand({ name: "add", about: "Add a remote." });

// After matching `Output` and `ArgError` as above:
let args = cli.parse(argv, env) as Args orelse ...;
when (args.command) {
  add -> ...;        // args.get(force), args.get(verbose)
  rm -> ...;
  remoteAdd -> ...;
  else -> ...;
}
```

- `cli.subcommand({ ... })` returns a `Command` with its own arguments,
  help, errors, and subcommands; `SubcommandSpec` has `name`, `about`,
  `aliases`, `hiddenAliases`, `commandOptional`, and `version`.
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
- **Completions:** answered by the program itself from the same spec,
  through short scripts for bash, zsh, fish, and PowerShell, including
  values (choices, files, directories, and values found at run time);
  see [Completions](#completions).
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
  character, a name starting with `-` or holding `=` or a space, a
  positional count range that allows nothing, or, with two styles, a
  long name that also reads as a bundle of short options, as
  [styles](#argument-styles) describes) are reported by `parse` as an
  `invalidSpec` error, not a panic where they're declared, so a spec
  with one can't ship unnoticed: its first run fails.
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
  subcommand, or one of its aliases (hidden or not), selects it; the arguments after
  it are the subcommand's, which can select a subcommand of its own.
  Aliases give the same command, with its own name in `args.command`
  and in help.
- **Inherited options** (clap's `global`, picocli's inherited
  options) are accepted before or after the name of any subcommand
  below the command declaring them, at any depth, and count the same
  either way: an option's last value wins and a counted flag adds up
  across both places. Other options go before the subcommand's name,
  as in git, and a subcommand's options go after it.
- **A parent's option after a subcommand's name:** an option a command
  above declared without `inherited`, given after a subcommand's name,
  is an unknown option whose message says where it goes instead of
  suggesting a near miss: "unknown option --dir; --dir belongs to
  frob, so give it before add", naming the subcommand right below the
  command that declared it (`remote` in `frob remote add --dir x`) by
  its own name, even when an alias was typed. Options of a subcommand
  given before its name get no hint, since the subcommand isn't known
  yet.
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
  declared default subcommand, decided for now (2026-11-16):
  parsing its options at the top would make `frob --force` work but
  `frob --help` not list `--force`, and `commandOptional` covers
  running one by default.
- **Hidden aliases** (`hiddenAliases`, such as old names kept
  working) select their subcommand and work after `help`, but help
  doesn't list them and suggestions don't offer them, so they stay
  out of sight; no two names or aliases, hidden or not, under one
  command are the same.
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
- **`--version`** is built in for the top command, and for a
  subcommand only when its spec sets its own `version` (decided
  2026-11-16); it isn't inherited, so `frob add --version` is an
  unknown option unless `add` has a version, and then it prints
  `frob add 2.0.0`, the command's path and its version. Like
  `--help`, it's the version of the command it's given to:
  `frob --version add` is `frob`'s.
- **Error order:** argument errors in argument order, then a missing
  subcommand, then positional counts, then environment values, then
  missing required options, each of the last three from the top
  command down. An error shows the usage of the command it happened
  in, after the top command's name: `frob: ...`, then
  `Usage: frob add ...` and `Try 'frob add --help' ...`.
- **Spec mistakes:** subcommand names and aliases follow the rules for
  long names, and no two under one command share one; the top
  command's can't be `__complete`, which asks for
  [completions](#completions); a subcommand's
  option can't have the long or short name of an option inherited from
  above. They're reported for the whole tree, ending with where they
  are (`in frob add`). The same name at two levels is fine when it
  isn't inherited.
- **Parsing a subcommand** directly is parsing its path from the top
  command: `add.parse(argv)` is `cli.parse(["add", ...argv])`.
- **Help:** a command with subcommands lists them under `Commands:`,
  with each one's about text and `[aliases: ...]` (not its hidden
  ones), then `help`, before
  its arguments and options, all in one column. A subcommand's usage
  starts with its path (`Usage: frob add [OPTIONS] FILE...`), and its
  options list its own, then those inherited from its parent, then
  from further up.

## Argument styles

As built in the third slice, a `style` setting on `Command` chooses
how options are written; the same spec drives parsing, help, and
usage lines (and later completions) in each style:

| Style | Looks like | Common in |
|---|---|---|
| `Style.gnu` (default) | `-v`, `-abc`, `--verbose`, `--out=f` | most Unix tools |
| `Style.singleDash` | `-verbose`, `-out=f`, `-out f` | Go's `flag`, Java's tools |
| `Style.windows` | `/v`, `/out:f`, `/out f`, `/?` | Windows command-line tools |

```temper
let cli = new Command({ name: "frob", style: Style.windows });
let verbose = cli.flag({ name: "verbose", short: "v" });
// frob /v, frob /Verbose, frob -verbose, and frob --verbose all set it.

let go = new Command({ name: "frob", style: Style.singleDash });
// -level=5, -level 5, and --level 5 all give 5; -vq is one name.

let moving = new Command({ name: "frob", alsoStyle: Style.singleDash });
// gnu first, so help shows --verbose, but -verbose works too.
```

Decisions, each tested in `src/style-tests.temper.md`:

- **Bundling** (`-abc`, `-ofile`) exists only in `gnu`. In
  `singleDash`, `-abc` is one name, long or short, and `-ofile` is an
  unknown option; `--name` is the same as `-name`, as in Go's `flag`.
- **`windows`** takes `/name`, `/name:value`, `/name=value`, and
  `/name value`: `:` as in MSBuild and csc, and a separate value as in
  `taskkill /pid 42` and `schtasks /tn name`. The first `:` or `=` ends
  the name, so `/out:C:\x` gives `C:\x`. `-name` and `--name` work
  the same, as in most current Windows tools, and nothing is bundled.
- **Case:** `windows` names ignore ASCII case (`/V`, `/VERBOSE`), as
  Windows tools do; values and subcommands' names keep theirs.
- **Help in `windows`:** `/?` and `-?`, and `/help` and `/h` (in any
  case); help lists `/?, /help`, and errors end with
  `Try 'frob /?' for more information.`
- **`/word` in `windows`** is an option only when `word` (before any
  `:` or `=`) is the name of one, `no-` and a negatable flag's name, or
  a built-in; other words starting with `/` are positional arguments,
  so `/usr/bin/x` passes as a path. In a command without positional
  arguments they're unknown options, with suggestions, as is a parent's
  option given after a subcommand's name, for its hint. After an
  option, a `/word` that names no option is its value: `/out /tmp/x`.
  A path that is also an option's name goes after `--`.
- **Negation** is `no-` before the name in every style:
  `--no-color`, `-no-color`, `/no-color`.
- **Values that look like options:** as in `gnu`, a separate value
  can't start with `-` (except `-` alone and numbers), nor, in
  `windows`, be `/` and an option's name; the message shows the
  attached form (`-level=-x`, `/level:-x`).
- **Numbers** in `singleDash` and `windows` (`-5`, `-1.5`) are
  options only when they name one; otherwise values.
- **One namespace:** in `singleDash` and `windows`, long and short
  names are read the same way, so one option's long name can't be
  another's short name, and in `windows`, names differing only in case
  clash; the spec reports either as declared twice (`-v declared
  twice`). `gnu` allows both.
- **Two styles:** `alsoStyle` adds a second style, for a tool moving
  from one to the other. Each argument is read in the first style
  where it names an option or built-in in full, then as a `gnu` bundle
  of known short options (so `-level` with both `gnu` and `singleDash`
  is `-level`, not `-l evel`), and otherwise in the first style that
  takes it for an option at all, which reports the error.
- **Messages** name a known option in the first style (`option -level
  needs a value`, `missing required option /name`); an unknown option
  is echoed as typed, with a suggestion using the prefix typed.
- **Subcommands** take their top command's styles; `SubcommandSpec`
  has no `style`.
- **Long names that read as bundles** (decided 2026-11-16): with
  `gnu` and another style, a long name that is also a `gnu` bundle of
  known short options, such as `vq` beside `-v` and `-q`, or `vo`
  beside a flag `-v` and an option `-o` (its value next), is a spec
  mistake: `long name vq could also be read as -v -q`. Parsing would
  read `-vq` as the long name, so the bundle could never be given and
  users couldn't tell which they'd get. Built-in names count (`-help`
  with flags `-e`, `-l`, and `-p`), as do `no-` forms and inherited
  options, reported in the subcommand where the two meet. A short
  option with letters after it that aren't all short flags, as
  `-level` with `-l`, isn't reported: that's `-level`, as decided
  above.
- **Not planned:** `+x` to turn an option on, now rare.

## Completions

As built in the fourth slice (decided with the user 2026-11-16):
completion is dynamic. A short script per shell asks the program
itself as the user presses Tab, and Argmas answers from the spec it
parses with, so completions can't drift from what the program
accepts, follow every style, and include values only known at run
time. Static scripts generated per program (as clap and argcomplete
can) would need regenerating with each release and couldn't run a
completer.

```temper
let cli = new Command({ name: "frob", completions: true });
let mode = cli.option(choices(["fast", "slow"]), { name: "mode" });
let out = cli.option(paths, { name: "out", short: "o" });
let branch = cli.option(strings, { name: "branch", completer: new Branches() });

cli.complete(["--mode", "f"]);   // fast
cli.complete(["--out=sr"]);      // files after --out=, by the shell
// `frob --completions bash` prints the bash script, as does
// cli.completionScript(Shell.bash); `frob __complete 1 --mode f`
// prints what the script reads: "fast\n:none\n".
```

Decisions, each tested in `src/complete-tests.temper.md` and
`src/shells-tests.temper.md`:

- **The protocol:** `frob __complete INDEX WORD...`, with the words
  after the program's name and the index (from 0) of the word being
  completed, empty when past the last; words after it are ignored. The
  index, rather than an empty last word, keeps PowerShell before 7.3,
  which drops empty arguments, working. The answer is a line per
  candidate, `value` or `value<TAB>description`, then `:none`,
  `:files`, or `:directories`, with a space and a prefix to keep
  (`:files --out=`) for a path attached to an option. Descriptions
  are the help text on one line.
- **Routing:** `cli.parse(argv)` with `__complete` as the first
  argument returns an `Output` (kind `OutputKind.completions`) whose
  text is the answer, so a program's usual handling of `Output`
  (print, exit 0) serves completions with no more code. It's not in
  help. `__complete` anywhere else is an ordinary word; a top
  command's subcommand can't have the name (a spec mistake), and a
  positional argument with that text goes after `--`. A spec with
  mistakes answers nothing.
- **The pure function:** `cli.complete(words, index)` returns a
  `Completion` (candidates with descriptions, a `Directive`, and the
  prefix); the index defaults to the last word. A subcommand's is
  its top command's with its path first, as for `parse`.
- **What's offered:** the words before the one completed are read as
  parsing reads them, so completion knows the command reached, the
  options given, and whether a value is due. Subcommand names (with
  about text, and `help` when built in); a visible alias only when the
  word starts it and not its name (`rem` gives `remove`), hidden
  aliases never; after `help`, the named command's subcommands. The
  next positional argument's values. Options only once the word starts
  with `-` (or `/` in `windows`), unless nothing else can go there.
- **Options in styles:** each option in each of the command's styles:
  in `gnu`, `-v` and `--verbose`; in `singleDash` and `windows`, the
  prefix typed is kept (`-name`, `--name`, or `/name`, `/` when
  nothing is typed); `no-` forms of negatable flags; inherited options;
  and the built-ins (`--help`, `-h`, `/?`, `--version`,
  `--completions`). `windows` names match ignoring case. A `/word` in
  `windows` gets the positional argument's values (paths) too, since
  it may be one.
- **Repeats:** an option already given isn't offered again unless it's
  counted or `repeated`; a negatable flag given either way isn't
  offered either way.
- **Values:** after an option, or attached (`--mode=f`, `-mode=f`,
  `/mode:f`), from the option's `completer` setting if any, else its
  value type's `complete`: choices for `choices`, nothing for numbers,
  files for `strings` (shells complete files for arguments they know
  nothing about, and text arguments are so often paths) and `paths`,
  and directories for `directories`. Files and directories are left to
  the shell, which knows its quoting, `~`, and hidden files. A word
  that looks like an option isn't a value, as in parsing. After `--`,
  only positional arguments. Argmas offers only candidates that start
  with the word, so every shell sees the same list.
- **Custom completers:** the `Completer` interface, given the partial
  word, returns `Candidate`s (a value and an optional description),
  for an option's or positional argument's `completer`; a `ValueType`
  can override `complete` to do the same for every option of its type,
  or to ask for files or directories.
- **Scripts:** bash (4.4 or later), zsh, fish, and PowerShell (5.1 or
  later, with `Register-ArgumentCompleter -Native`), each a few dozen
  lines, the same for every program but its name, so they needn't be
  regenerated when the program changes. zsh, fish, and PowerShell show
  descriptions; bash can't. bash reads words from `COMP_LINE`, since
  `COMP_WORDS` splits at `=` and `:`, and hands bash back only the
  part after the last of those it completes. PowerShell completes
  paths itself when a completer offers nothing, so values with no
  candidates get paths there; its script leaves files to that, but
  completes directories itself, keeping only containers, since
  PowerShell's own would offer files too.
- **Printing scripts:** `cli.completionScript(shell)` with `Shell.bash`,
  `zsh`, `fish`, or `powershell`, and an opt-in built-in
  `--completions SHELL` (`completions: true` in `CommandSpec`), an
  option rather than a subcommand so it works for commands with
  positional arguments and no subcommands; a program wanting
  `frob completions bash` declares that subcommand and prints
  `completionScript`. Like `--version`, it's only on the top command,
  its output wins over errors other than asking for help, and a
  program may take the name. Help lists it last with the shells.
- **Print only:** Argmas never edits a user's shell setup. Each script
  starts with a comment saying where its shell looks for it, and the
  README lists them: the bash-completion directory
  (`~/.local/share/bash-completion/completions/frob`) or `~/.bashrc`,
  a directory on zsh's `$fpath` as `_frob`,
  `~/.config/fish/completions/frob.fish`, and the PowerShell profile.
- **Not supported:** `cmd.exe`, which has no programmable completion.

## Messages

As built in the fifth slice: every text Argmas writes itself comes
from one table of messages, so a program can translate or reword it
without forking: help's headings, notes, and built-in options, errors
and their suggestions and hints, the version line, completions'
descriptions, and the comments atop completion scripts. English is
built in, in `src/messages.temper.md`.

```temper
let cli = new Command({ name: "frob" });
cli.setMessage("usage", "Aufruf: {command}");
cli.setMessage("error.unknownOption.suggest", "{suggestion}? Es gibt kein {option}.");
cli.setMessages(german);  // a Map of keys to templates, such as a whole table
```

Decisions, each tested in `src/messages-tests.temper.md`:

- **Templates with named placeholders:** `{option}`, filled in when
  the message is written, so a translation can reorder them or leave
  one out; `{{` and `}}` are literal braces. Messages are whole
  sentences, never pieced together, so a near miss or a hint is its
  own key (`error.unknownOption`, `.suggest`, `.late`). The one nesting
  is a noun phrase, `error.inBundle` (`-x in -vxq`), which fills
  another message's `{option}`.
- **Keys** are stable dotted names, listed below. A key's placeholders
  are those its English template uses.
- **The API:** `setMessage(key, template)` for one message and
  `setMessages(map)` for many, on any command of a tree, since
  messages belong to the whole tree; nothing set means English, and
  a key not set falls back to English, so a full translation and a
  few overrides are the same call. Methods rather than a
  `CommandSpec` setting, since a map is awkward in some languages
  (see [languages](languages.md)) and two strings aren't.
  `cli.messages` is the table in use, whose `text(key, values)` a
  program's own value types and completers may use; `ValueType` has
  `expectedIn(messages)`, which defaults to its English `expected`.
- **Mistakes:** a key Argmas doesn't have, a placeholder its key
  doesn't have, and a brace that doesn't pair up are spec mistakes,
  reported by `parse` like the others (`invalid command spec: unknown
  message key 'usge'`), so a typo in a translation fails its first
  run. The message with the mistake isn't used: its English stands,
  so `help()` still works.
- **Not in the table:** what the program declares (about text, help,
  value names), which is its own to translate; spec mistakes, which
  only its developers see; syntax (`--`, `[no-]`, `<NAME>`, `...`);
  and the completion protocol.
- **Lists:** plain lists (`[choices: a, b]`) are joined with
  `list.separator`; alternatives (`expected one of a, b`) with
  `list.or.pair` for two and `list.or.separator` and `list.or.last`
  for more, all `, ` in English, so a language can bring in its word
  for "or".
- **Locale comes from the host.** Argmas never reads the environment
  or the system for a language; the program picks a table, as the
  [README](../README.md#messages-and-translations) shows.
- **Plurals:** a message needing a count's plural has a key for one
  and a key for more (`error.missingArgument`,
  `error.tooFewArguments`), the hook until plural rules exist.

### Keys

Every key and its English template. `script.*` are several lines, each
written as a comment line.

| Key | English |
|---|---|
| `usage` | Usage: {command} |
| `usage.options` | [OPTIONS] |
| `usage.command` | COMMAND |
| `usage.optionalCommand` | [COMMAND] |
| `help.commands` | Commands: |
| `help.arguments` | Arguments: |
| `help.options` | Options: |
| `help.aliases` | [aliases: {aliases}] |
| `help.default` | [default: {value}] |
| `help.env` | [env: {name}] |
| `help.choices` | [choices: {choices}] |
| `help.required` | [required] |
| `help.repeatable` | [repeatable] |
| `builtin.help` | Show this help and exit. |
| `builtin.version` | Show the version and exit. |
| `builtin.helpCommand` | Show help for a command. |
| `builtin.completions` | Print a completion script for {shell} and exit. |
| `builtin.completionsValue` | SHELL |
| `version` | {command} {version} |
| `complete.negate` | Undo {option}. |
| `complete.completions` | Print a completion script for a shell and exit. |
| `script.bash` | bash completion for {program}, generated by Argmas. Then where to save it, on more lines. |
| `script.zsh` | zsh completion for {program}, generated by Argmas. Then where to save it, on more lines. |
| `script.fish` | fish completion for {program}, generated by Argmas. Then where to save it, on more lines. |
| `script.powershell` | PowerShell completion for {program}, generated by Argmas. Then where to save it, on more lines. |
| `error.report` | {program}: {message} |
| `error.tryHelp` | Try '{command} {help}' for more information. |
| `error.unknownOption` | unknown option {option} |
| `error.unknownOption.suggest` | unknown option {option}; did you mean {suggestion}? |
| `error.unknownOption.late` | unknown option {option}; {name} belongs to {command}, so give it before {subcommand} |
| `error.unknownOption.notNegatable` | unknown option {option}; {flag} can't be negated |
| `error.inBundle` | {option} in {bundle} |
| `error.unexpectedValue` | option {option} takes no value |
| `error.missingValue` | option {option} needs a value |
| `error.missingValue.attached` | option {option} needs a value; to give one starting with '{lead}', write {attached} |
| `error.invalidValue` | invalid value '{value}' for {option}: expected {expected} |
| `error.invalidValue.suggest` | invalid value '{value}' for {option}: expected {expected}; did you mean {suggestion}? |
| `error.invalidEnvValue` | invalid value '{value}' for {option} from {env}: expected {expected} |
| `error.invalidEnvValue.suggest` | invalid value '{value}' for {option} from {env}: expected {expected}; did you mean {suggestion}? |
| `error.unknownCommand` | unknown command '{command}' |
| `error.unknownCommand.suggest` | unknown command '{command}'; did you mean {suggestion}? |
| `error.missingCommand` | missing command; expected one of {commands} |
| `error.missingArgument` | missing argument {name} |
| `error.tooFewArguments` | missing argument {name}: needs at least {min}, got {count} |
| `error.unexpectedArgument` | unexpected argument '{argument}' |
| `error.missingRequired` | missing required option {option} |
| `error.missingRequired.env` | missing required option {option} (or {env}) |
| `expected.integer` | an integer |
| `expected.number` | a number |
| `expected.text` | text |
| `expected.oneOf` | one of {choices} |
| `expected.boolean` | true or false |
| `expected.count` | a count |
| `list.separator` | `, ` |
| `list.or.separator` | `, ` |
| `list.or.pair` | `, ` |
| `list.or.last` | `, ` |

### Later

- **Plural rules** per language (CLDR's categories: one, few, many,
  and so on), selected by a count, as part of a shared Temper library
  for internationalization rather than in Argmas.
- **Display width:** help counts columns in code points, so text in
  Chinese, Japanese, or Korean lines up only once wide characters
  count as two.
- **Shipped translations:** none yet; they'd come with that shared
  library, reviewed by speakers, rather than from Argmas alone.
- **Messages from that library:** once it exists, Argmas's keys can
  move into its format, with the same keys and placeholders.

## Testing

- **Parsing tables:** argv in, parsed result or error out, run on every
  backend; the same table is the behavior spec.
- **Against reference parsers:** the same inputs through `getopt_long`,
  clap, and argparse where they claim the same conventions, with every
  difference either matched or documented.
- **Help and errors:** goldens of the exact text, in English and with
  a program's own messages, including a partial German table kept as
  a test fixture, not a translation.
- **Completions:** tables of words in and candidates out, goldens of
  each script, and `tests/shells/run.py`, which installs each script
  in a throwaway directory and completes command lines in the real
  bash, zsh, fish, and PowerShell, skipping those not installed; CI
  runs it on Linux, macOS, and Windows with each platform's shells.
- **Tours:** a small program in each language, `pack` in
  [demos](../demos/README.md), run with the same command lines, whose
  output CI checks is the same in every language.

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
  `ParamKind`, `Source`, `Style`) are classes with static instances and
  `@auto("==")`; such an instance works as a bag property's default
  (`style: Style = Style.gnu`).

## Open questions

- Completions: quotes typed on a bash line reach the program as typed;
  whether to unquote them. PowerShell falls back to paths when nothing
  is offered; whether to stop it (Cobra adds a dummy candidate). The
  zsh, fish, and PowerShell scripts haven't been driven in their
  shells here yet.
- A declared default subcommand, decided against for now; revisit if
  `commandOptional` proves awkward.
- `args.within(cmd)`, true when `cmd` or a subcommand under it ran,
  for code shared by a group of subcommands (`remote add` and `remote
  rm` both under `remote`). Deferred until a program needs it;
  `args.command.ancestors` covers it meanwhile.
- `args.command == add` reads poorly in C# and Java (`Eq`, `eq`) only
  because tempest translates a user-defined `@operator("==")` to an
  `eq` method rather than to the language's own equality. That's a
  planned tempest fix, so Argmas keeps `==` rather than adding a
  method such as `args.ran(add)`.
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

## Work plan

In this order, as agreed (2026-11-16):

1. The message table (done).
2. A project site, with the tours as its seed (done: `site/`, published
   from main; per-language tabs for the examples beyond the tour later).
3. Testing against reference parsers: `getopt_long`, clap, and
   argparse.
4. Small open items: flags that default to true, `Int64` values, the
   decision on prefix matching, and unquoting on bash lines in
   completions.
5. `parseInto` with `@json`, or a result type per command.

Later: display width, date, duration, and path value types,
translations through a Temper library for internationalization, and
property tests once Temper has a framework for them.
