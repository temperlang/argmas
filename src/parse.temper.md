# Parsing

`cli.parse(argv, env)` reads the arguments (without the program's name)
and returns one of three results:

- `Args`, the values, read with `args.get(handle)`;
- `Output`, text to print before exiting with status 0, for `--help`,
  `--version`, `--completions`, and a shell asking for
  [completions](complete.temper.md);
- `ArgError`, a mistake in the arguments, with a one-line message and
  a report to print before exiting with status 2.

```temper inert
when (cli.parse(argv, env)) {
  is Args -> ...;
  is Output -> ...;
  is ArgError -> ...;
}
```

Parsing never panics and touches nothing outside: the program passes
the arguments and a way to read the environment, and does any printing
and exiting itself.

## The environment

Environment variables reach the parser through this interface, which
each program implements over its platform's environment, or with
`MapEnvironment` over a map.

    export interface Environment {

The variable's value, or null when it isn't set.

      public get(name: String): String?;
    }

    export class MapEnvironment(private vars: Mapped<String, String>) extends Environment {
      public get(name: String): String? { vars.get(name) orelse null }
    }

## Results

    export sealed interface ParseResult {

The exit status conventional for this result: 0 for success, help, and
version, and 2 for errors.

      public get exitStatus(): Int;
    }

### Values

`Args` has the values for the command that ran and each command above
it, from the top command down.

    export class Args(
      private path: List<Command>,
      private found: List<List<Found>>,
    ) extends ParseResult {
      public get exitStatus(): Int { 0 }

The command that ran: the last subcommand named, or the top command
when none was. A program matches it against the commands it declared:

```temper inert
when (args.command) {
  add -> ...;
  rm -> ...;
  else -> ...;
}
```

      public get command(): Command { path[path.length - 1] }

The value of an argument that always has one, as its handle's type.

      @overload("get")
      public getValue<T>(arg: Arg<T>): T { arg.read(foundFor(arg.param)) }

The value of an option that may be absent, or null.

      @overload("get")
      public getMaybe<T>(arg: MaybeArg<T>): T? { arg.read(foundFor(arg.param)) }

Where an argument's value came from: an argument, the environment, or
neither (`Source.absent`, so any default applies).

      public source(param: Param): Source { foundFor(param).source }

An argument of a command that didn't run is absent, so it reads as its
default: false, 0, null, an empty list, or the default given. A
required option or a single positional argument has none, so reading
one of those panics; check `args.command` first.

      private foundFor(param: Param): Found {
        let depth = param.command.depth;
        if (depth < path.length && path[depth] == param.command) {
          return found[depth][param.index];
        }
        absentFound()
      }
    }

Outside `Args`, since in C# its method `Source` would hide the class.

    let absentFound(): Found { new Found([], Source.absent) }

### Help, version, and completions

    export class Output(

The command whose help or version it is.

      public command: Command,

What it is: help, a version, completions, or a completion script.

      public kind: OutputKind,

The text of completions or a script.

      private content: String = "",
    ) extends ParseResult {
      public get exitStatus(): Int { 0 }

      public get isHelp(): Boolean { kind == OutputKind.help }

The text to print to standard output, wrapped to `width` columns.

A version is the command's path and its version: `frob 1.2.0`, or
`frob add 2.0.0` for a subcommand with its own.

      public text(width: Int = 80): String {
        if (kind == OutputKind.help) {
          command.help(width)
        } else if (kind == OutputKind.version) {
          let line = command.messages.text("version", ["command", command.path, "version", command.spec.version ?? ""]);
          "${line}\n"
        } else {
          content
        }
      }
    }

The kinds of output, as named singletons.

    @auto("==")
    export class OutputKind {
      public name: String;
      private constructor(name: String) { this.name = name; }
      public static help: OutputKind = doPure { new OutputKind("help") }
      public static version: OutputKind = doPure { new OutputKind("version") }

What a shell asked for with `__complete`, in the form its script
reads.

      public static completions: OutputKind = doPure { new OutputKind("completions") }

A script for `--completions SHELL`.

      public static completionScript: OutputKind = doPure { new OutputKind("completionScript") }
      public toString(): String { name }
    }

### Errors

    export class ArgError(
      private command: Command,
      public kind: ErrorKind,

One line, without the program's name, such as "unknown option
--verbos; did you mean --verbose?".

      public message: String,
    ) extends ParseResult {
      public get exitStatus(): Int { 2 }

The report to print to standard error: the message after the program's
name, the usage of the command where it went wrong, and where to find
more.

      public text(width: Int = 80): String {
        let messages = command.messages;
        let name = command.top.spec.name;
        let ask = helpOption(command);
        let more = if (ask != null) {
          let line = messages.text("error.tryHelp", ["command", command.path, "help", ask]);
          "${line}\n"
        } else { "" };
        let report = messages.text("error.report", ["program", name, "message", message]);
        "${report}\n${command.usage(width)}${more}"
      }

      public toString(): String { message }
    }

The kinds of error, as named singletons, so programs and tests can
tell them apart without matching text.

    @auto("==")
    export class ErrorKind {
      public name: String;
      private constructor(name: String) { this.name = name; }

`--verbos`, `-x`, or `--no-level` when there's no such option.

      public static unknownOption: ErrorKind = doPure { new ErrorKind("unknownOption") }

An option at the end, or followed by something that looks like an
option.

      public static missingValue: ErrorKind = doPure { new ErrorKind("missingValue") }

`--verbose=yes` for a flag.

      public static unexpectedValue: ErrorKind = doPure { new ErrorKind("unexpectedValue") }

A value its type doesn't take, from an argument or the environment.

      public static invalidValue: ErrorKind = doPure { new ErrorKind("invalidValue") }
      public static missingRequired: ErrorKind = doPure { new ErrorKind("missingRequired") }
      public static tooFewPositionals: ErrorKind = doPure { new ErrorKind("tooFewPositionals") }
      public static tooManyPositionals: ErrorKind = doPure { new ErrorKind("tooManyPositionals") }

A word that names no subcommand where one is expected, as `frob ad`,
or in `frob help ad`.

      public static unknownCommand: ErrorKind = doPure { new ErrorKind("unknownCommand") }

No subcommand given to a command that needs one.

      public static missingCommand: ErrorKind = doPure { new ErrorKind("missingCommand") }

A mistake in the command's spec, not the arguments, such as a name
declared twice.

      public static invalidSpec: ErrorKind = doPure { new ErrorKind("invalidSpec") }
      public toString(): String { name }
    }

## The parser

Arguments are read left to right:

- `--` ends options; everything after it is positional.
- `--name` and `--name=value` are long options, with no prefix
  matching; `--no-name` turns off a negatable flag.
- `-abc` is short options bundled; an option among them takes the rest
  of the argument as its value (`-ofile`, with one `=` after the option
  dropped, so `-o=file` is `file`), or the next argument.
- `-` alone, and anything not starting with `-`, is positional, and
  options may come after positionals.
- An argument that looks like a negative number (`-5`, `-1.5`, `-2e3`)
  is a value or positional, unless the command has a short option that
  is a digit.

An option's value can be the next argument unless that looks like an
option (it starts with `-`, isn't `-` alone, and isn't a negative
number); then it's a missing value, and `--name=-x` or `-n-x` passes
such a value.

`--help` (or `-h`) and `--version` win over any error, wherever they
come before `--`, so a user can always ask for help. Otherwise the
first error is reported, in this order: problems in the spec, then
problems with arguments in the order they came, then a missing
subcommand, then positional counts, then values from the environment,
then missing required options, each of the last three from the top
command down.

### Styles

In `singleDash` and `windows` [styles](style.temper.md), an option is
one name after its prefix, with any value after `=` (or, in `windows`,
`:`), and nothing is bundled. With two styles, each argument is read
in the first that knows its name.

### Subcommands

In a command with subcommands, a positional argument that names one
(or one of its aliases) selects it, and the arguments after it are the
subcommand's: its own options, any its parents declared `inherited`,
and its positional arguments, or the name of a subcommand of its own.
So `frob -v add -f a.txt` gives `-v` to `frob`, and `-f` and `a.txt`
to `add`. The parent's options that aren't inherited go before the
subcommand's name, as in git and clap.

- A command with subcommands that takes positional arguments too gets
  those before the subcommand's name; a word that names a subcommand
  always selects it, and after `--` none does, so `--` passes such a
  word as a positional argument.
- Otherwise, a word that names no subcommand is an error, suggesting
  the nearest name.
- `help` selects the help of the subcommand named after it, as
  `frob help add`, unless the program declares a subcommand `help`.
- With no subcommand given, a command that has them reports the error
  listing them, unless its spec sets `commandOptional`.
- `--help` shows the help of the command it's given to: `frob --help
  add` shows `frob`'s, `frob add --help` shows `add`'s, and the last
  one given wins.

Parsing checks the spec first, then reads the arguments. A shell's
script asking for completions, with `__complete` first, gets them
instead.

    let parseCommand(command: Command, argv: List<String>, env: Environment?): ParseResult {
      if (!argv.isEmpty && argv[0] == completeWord) {
        return new Output(command, OutputKind.completions, completionRequest(command, argv).text());
      }
      let problems = command.problems;
      if (!problems.isEmpty) {
        return new ArgError(command, ErrorKind.invalidSpec, "invalid command spec: ${problems[0]}");
      }
      new Parser(command, argv, env).run()
    }

What the parser keeps for each command on the way down: each declared
argument's values and where they came from, and the positional
arguments given to it.

    class Level(public command: Command) {
      public values: List<ListBuilder<String>> = makeBuilders(command.declared.length);
      public sources: ListBuilder<Source> = makeSources(command.declared.length);
      public positionalTexts: ListBuilder<String> = new ListBuilder<String>();
      public numbersAreValues: Boolean = !hasDigitShort(command.options);
    }

    class Parser(
      private top: Command,
      private argv: List<String>,
      private env: Environment?,
    ) {

One level for the top command, and one more for each subcommand named.

      public levels: ListBuilder<Level> = firstLevel(top);
      private var firstError: ArgError? = null;

Whether `--` came, so the rest are positional arguments.

      public var onlyPositionals: Boolean = false;

For completions, what the last argument read left waiting: the option
whose value comes next, `--completions` without its shell, or the
command whose subcommands come next after `help`.

      public var pending: Param? = null;
      public var pendingShell: Boolean = false;
      public var helpTarget: Command? = null;

Whether a word after `help` named no subcommand, so nothing can
follow.

      public var lost: Boolean = false;

The command whose help was asked for, if any.

      private var helpFor: Command? = null;

The command whose version was asked for, if any.

      private var versionFor: Command? = null;

The shell whose completion script was asked for, if any.

      private var scriptShell: Shell? = null;

      public get current(): Level { levels[levels.length - 1] }

A message from the command's [table](messages.temper.md).

      private say(key: String, values: List<String>): String { top.messages.text(key, values) }

      public run(): ParseResult {
        scan();
        let help = helpFor;
        if (help != null) { return new Output(help, OutputKind.help); }
        let version = versionFor;
        if (version != null) { return new Output(version, OutputKind.version); }
        let shell = scriptShell;
        if (shell != null) { return new Output(top, OutputKind.completionScript, top.completionScript(shell)); }
        finish()
      }

Reads every argument, noting what it finds.

      public scan(): Void {
        var i = 0;
        let n = argv.length;
        while (i < n) {
          let arg = argv[i];
          i += 1;
          if (onlyPositionals) {
            current.positionalTexts.add(arg);
          } else if (arg == "--") {
            onlyPositionals = true;
          } else {
            let style = readAs(current, arg, false);
            if (style == null) {
              i = word(arg, i);
            } else if (style != Style.gnu) {
              i = named(arg, style, i);
            } else if (startsWith(arg, "--")) {
              i = long(arg, i);
            } else {
              i = shorts(arg, i);
            }
          }
        }
      }

What comes after reading the arguments: errors found, then the
positional arguments, the environment, and required options.

      private finish(): ParseResult {
        let early = firstError;
        if (early != null) { return early; }
        let last = current.command;
        if (!last.commands.isEmpty && !last.spec.commandOptional) {
          let names = top.messages.orList(last.commands.map { (c: Command): String => c.spec.name });
          fail(last, ErrorKind.missingCommand, say("error.missingCommand", ["commands", names]));
        }
        for (let level of levels.toList()) { assignPositionals(level); }
        for (let level of levels.toList()) { readEnvironment(level); }
        for (let level of levels.toList()) { checkRequired(level); }
        let error = firstError;
        if (error != null) { return error; }
        let path = new ListBuilder<Command>();
        let found = new ListBuilder<List<Found>>();
        for (let level of levels.toList()) {
          path.add(level.command);
          let foundHere = new ListBuilder<Found>();
          for (let p of level.command.declared) {
            foundHere.add(new Found(level.values[p.index].toList(), level.sources[p.index]));
          }
          found.add(foundHere.toList());
        }
        new Args(path.toList(), found.toList())
      }

### Words

A positional argument, or the name of a subcommand. Returns the index
of the next argument to read.

      private word(arg: String, next: Int): Int {
        let level = current;
        let command = level.command;
        if (!command.commands.isEmpty) {
          let sub = command.findCommand(arg);
          if (sub != null) {
            levels.add(new Level(sub));
            return next;
          }
          if (arg == "help" && command.builtInHelpCommand) {
            return helpPath(command, next);
          }
          if (!command.takesPositionals) {
            fail(command, ErrorKind.unknownCommand, unknownCommand(command, arg));
            return next;
          }
        }
        level.positionalTexts.add(arg);
        next
      }

After `help`, every argument names a subcommand of the one before, and
the help is the last one's. `-h`, `--help` (or `/?` and the like in
other styles), and `help` itself are skipped, so `frob help --help` is `frob`'s help too.

      private helpPath(command: Command, next: Int): Int {
        var target = command;
        for (var i = next; i < argv.length; i += 1) {
          let name = argv[i];
          if (asksForHelp(target, name) || (name == "help" && target.builtInHelpCommand)) { continue; }
          let sub = target.findCommand(name);
          if (sub == null) {
            fail(target, ErrorKind.unknownCommand, unknownCommand(target, name));
            lost = true;
            return argv.length;
          }
          target = sub;
        }
        helpFor = target;
        helpTarget = target;
        argv.length
      }

      private unknownCommand(command: Command, typed: String): String {
        let names = new ListBuilder<String>();
        for (let sub of command.commands) {
          names.add(sub.spec.name);
          for (let alias of sub.aliases) { names.add(alias); }
        }
        if (command.builtInHelpCommand) { names.add("help"); }
        let best = nearest(typed, names.toList());
        if (best != null) {
          say("error.unknownCommand.suggest", ["command", typed, "suggestion", best])
        } else {
          say("error.unknownCommand", ["command", typed])
        }
      }

### Long options

`long` handles `arg` and returns the index of the next argument, past
a value it took.

      private long(arg: String, next: Int): Int {
        let command = current.command;
        let body = dropFirst(arg, 2);
        let eq = body.indexOf("=");
        var name = body;
        var inline: String? = null;
        if (eq is StringIndex) {
          name = body.slice(String.begin, eq);
          inline = body.slice(body.next(eq), body.end);
        }
        let p = command.findLong(name);
        if (p != null) {
          return takeLong(p, name, inline, false, next);
        }
        if (startsWith(name, "no-")) {
          let negated = command.findLong(dropFirst(name, 3));
          if (negated != null && negated.negatable) {
            return takeLong(negated, name, inline, true, next);
          }
          if (negated != null) {
            fail(command, ErrorKind.unknownOption, say("error.unknownOption.notNegatable", ["option", "--${name}", "flag", "--${negated.name}"]));
            return next;
          }
        }
        if (name == "help" && command.builtInHelpLong) {
          if (inline != null) { fail(command, ErrorKind.unexpectedValue, say("error.unexpectedValue", ["option", "--help"])); }
          helpFor = command;
          return next;
        }
        if (name == "version" && command.builtInVersion) {
          if (inline != null) { fail(command, ErrorKind.unexpectedValue, say("error.unexpectedValue", ["option", "--version"])); }
          versionFor = command;
          return next;
        }
        if (name == "completions" && command.builtInCompletions) {
          return shellOption(command, inline, next);
        }
        let typed = "--${name}";
        unknownOption(command, typed, typed, lateFor(command, name, Style.gnu, false), suggestLong(command, name));
        next
      }

      private takeLong(p: Param, typed: String, inline: String?, negated: Boolean, next: Int): Int {
        if (p.kind != ParamKind.option) {
          if (inline != null) {
            fail(current.command, ErrorKind.unexpectedValue, say("error.unexpectedValue", ["option", "--${typed}"]));
          } else {
            occur(p, negated);
          }
          return next;
        }
        if (inline != null) {
          give(p, inline);
          return next;
        }
        takeNext(p, next)
      }

### Short options

      private shorts(arg: String, next: Int): Int {
        let command = current.command;
        var i = arg.next(String.begin);
        while (arg.hasIndex(i)) {
          let after = arg.next(i);
          let c = arg.slice(i, after);
          let p = command.findShort(c);
          if (p != null && p.kind == ParamKind.option) {
            if (arg.hasIndex(after)) {
              var start = after;
              if (arg[start] == char'=') { start = arg.next(start); }
              give(p, arg.slice(start, arg.end));
              return next;
            }
            return takeNext(p, next);
          } else if (p != null) {
            // `=` right after a flag is a value it doesn't take, as
            // `--quiet=yes` is, unless `=` is a short name itself.
            if (arg.hasIndex(after) && arg[after] == char'=' && command.findShort("=") == null) {
              fail(command, ErrorKind.unexpectedValue, say("error.unexpectedValue", ["option", "-${c}"]));
              return next;
            }
            occur(p, false);
          } else if (c == "h" && command.builtInHelpShort) {
            helpFor = command;
          } else {
            let typed = "-${c}";
            let shown = if (arg.hasAtLeast(String.begin, arg.end, 3)) {
              say("error.inBundle", ["option", typed, "bundle", arg])
            } else {
              typed
            };
            unknownOption(command, shown, typed, lateFor(command, c, Style.gnu, true), suggestFromShort(command, arg));
            return next;
          }
          i = after;
        }
        next
      }

### Options in `singleDash` and `windows`

One name after `-`, `--`, or (in `windows`) `/`, with an attached
value after `=` or (in `windows`) `:`.

      private named(arg: String, style: Style, next: Int): Int {
        let command = current.command;
        let parts = splitNamed(arg, style) ?? panic();
        let name = parts.name;
        let typed = "${parts.prefix}${name}";
        let inline = parts.inline;
        let ic = style.ignoresCase;
        let p = command.find(name, style, false);
        if (p != null) {
          return takeNamed(p, typed, inline, false, next);
        }
        if (startsWith(asciiLowerIf(name, ic), "no-")) {
          let negated = command.find(dropFirst(name, 3), style, false);
          if (negated != null && negated.negatable) {
            return takeNamed(negated, typed, inline, true, next);
          }
          if (negated != null) {
            fail(command, ErrorKind.unknownOption, say("error.unknownOption.notNegatable", ["option", typed, "flag", "${parts.prefix}${negated.name}"]));
            return next;
          }
        }
        let help = (sameName(name, "help", ic) && command.builtInHelpLong) ||
          (sameName(name, "h", ic) && command.builtInHelpShort) ||
          (name == "?" && style == Style.windows && command.builtInHelpQuestion);
        if (help) {
          if (inline != null) { fail(command, ErrorKind.unexpectedValue, say("error.unexpectedValue", ["option", typed])); }
          helpFor = command;
          return next;
        }
        if (sameName(name, "version", ic) && command.builtInVersion) {
          if (inline != null) { fail(command, ErrorKind.unexpectedValue, say("error.unexpectedValue", ["option", typed])); }
          versionFor = command;
          return next;
        }
        if (sameName(name, "completions", ic) && command.builtInCompletions) {
          return shellOption(command, inline, next);
        }
        let best = nearest(name, longNames(command));
        let suggestion = if (best != null) { "${parts.prefix}${best}" } else { null };
        unknownOption(command, typed, typed, lateFor(command, name, style, false), suggestion);
        next
      }

      private takeNamed(p: Param, typed: String, inline: String?, negated: Boolean, next: Int): Int {
        if (p.kind != ParamKind.option) {
          if (inline != null) {
            fail(current.command, ErrorKind.unexpectedValue, say("error.unexpectedValue", ["option", typed]));
          } else {
            occur(p, negated);
          }
          return next;
        }
        if (inline != null) {
          give(p, inline);
          return next;
        }
        takeNext(p, next)
      }

### Completion scripts

`--completions SHELL`, when built in, takes the shell's name as an
option takes its value, and like `--version` its output wins over
errors other than asking for help.

      private shellOption(command: Command, inline: String?, next: Int): Int {
        let shown = "${command.style.prefix}completions";
        var name = "";
        var after = next;
        if (inline != null) {
          name = inline;
        } else if (next < argv.length && argv[next] != "--" && readAs(current, argv[next], true) == null) {
          name = argv[next];
          after = next + 1;
        } else {
          if (next >= argv.length) { pendingShell = true; }
          fail(command, ErrorKind.missingValue, say("error.missingValue", ["option", shown]));
          return next;
        }
        let shell = Shell.named(name);
        if (shell == null) {
          let expected = say("expected.oneOf", ["choices", top.messages.orList(shellNames)]);
          fail(command, ErrorKind.invalidValue, invalidValueMessage(top.messages, name, shown, null, expected, nearest(name, shellNames)));
        } else if (scriptShell == null) {
          scriptShell = shell;
        }
        after
      }

### Options given after a subcommand's name

An option a command above declared, but didn't make `inherited`, given
after a subcommand's name gets a hint instead of a suggestion: "unknown
option --dir; --dir belongs to frob, so give it before add". `lateFor`
finds the subcommand to give it before, whose parent declared it, if
any.

      private lateFor(command: Command, name: String, style: Style, asShort: Boolean): Command? {
        var below = command;
        for (let ancestor of command.ancestors) {
          if (findIn(ancestor.declared, name, style, asShort) != null) {
            return below;
          }
          below = ancestor;
        }
        null
      }

An unknown option's error: `shown` as typed (or within a bundle), with
the hint for an option given too late, if any, or else the suggestion.

      private unknownOption(command: Command, shown: String, typed: String, late: Command?, suggestion: String?): Void {
        let message = if (late != null) {
          let owner = late.parent ?? panic();
          say("error.unknownOption.late", ["option", shown, "name", typed, "command", owner.path, "subcommand", late.spec.name])
        } else if (suggestion != null) {
          say("error.unknownOption.suggest", ["option", shown, "suggestion", suggestion])
        } else {
          say("error.unknownOption", ["option", shown])
        };
        fail(command, ErrorKind.unknownOption, message);
      }

### Values

An option's value from the next argument, if there's one that doesn't
look like an option. The message names the option in the command's
first style.

      private takeNext(p: Param, next: Int): Int {
        let command = current.command;
        let shown = longForm(command.style, p);
        if (next < argv.length) {
          let candidate = argv[next];
          if (candidate != "--" && readAs(current, candidate, true) == null) {
            give(p, candidate);
            return next + 1;
          }
          let attached = "${shown}${command.style.joiner}${candidate}";
          let lead = if (startsWith(candidate, "/")) { "/" } else { "-" };
          fail(command, ErrorKind.missingValue, say("error.missingValue.attached", ["option", shown, "lead", lead, "attached", attached]));
          return next;
        }
        pending = p;
        fail(command, ErrorKind.missingValue, say("error.missingValue", ["option", shown]));
        next
      }

### Choosing a style

The style an argument is read in, or null when it's a word (a
positional argument or a subcommand's name): the first of the
command's styles in which it names an option or a built-in in full,
then the first in which it's a `gnu` bundle of known short options (so
with `gnu` and `singleDash`, `-level` is `-level`, not `-l evel`), or
else the first in which it's shaped like an option at all, to report
it there. A value after an option (`forValue`) isn't read as an
unknown `/word`, so `/out /tmp/x` gives `/tmp/x` to `/out`.

      public readAs(level: Level, arg: String, forValue: Boolean): Style? {
        let command = level.command;
        let styles = command.styles;
        for (let style of styles) {
          if (knows(level, style, arg, false)) { return style; }
        }
        for (let style of styles) {
          if (knows(level, style, arg, true)) { return style; }
        }
        for (let style of styles) {
          if (shapedAsOption(level, style, arg, forValue)) { return style; }
        }
        null
      }

Whether `arg` names a known option, or a built-in, in `style`; for a
`gnu` argument with one dash, whether it's a bundle of known short
options, when `bundles`.

      private knows(level: Level, style: Style, arg: String, bundles: Boolean): Boolean {
        let command = level.command;
        if (style == Style.gnu) {
          if (!startsWith(arg, "-") || arg == "-" || (level.numbersAreValues && looksLikeNumber(arg))) { return false; }
          if (startsWith(arg, "--")) {
            let body = dropFirst(arg, 2);
            let eq = body.indexOf("=");
            let name = if (eq is StringIndex) { body.slice(String.begin, eq) } else { body };
            return !bundles && knownName(command, name, style, false);
          }
          if (!bundles) { return false; }
          var i = arg.next(String.begin);
          while (arg.hasIndex(i)) {
            let after = arg.next(i);
            let c = arg.slice(i, after);
            let p = command.find(c, style, true);
            if (p != null && p.kind == ParamKind.option) { return true; }
            if (p == null && !(c == "h" && command.builtInHelpShort)) { return false; }
            i = after;
          }
          return true;
        }
        let named = splitNamed(arg, style);
        if (bundles || named == null) { return false; }
        knownName(command, named.name, style, false)
      }

Whether `name` (after the prefix, before any value) is an option, a
negated flag, or a built-in in `style`. A `no-` name of an option that
isn't negatable counts, for its error.

      private knownName(command: Command, name: String, style: Style, asShort: Boolean): Boolean {
        if (command.find(name, style, asShort) != null) { return true; }
        let ic = style.ignoresCase;
        if (startsWith(asciiLowerIf(name, ic), "no-") && command.find(dropFirst(name, 3), style, false) != null) { return true; }
        if (sameName(name, "help", ic) && command.builtInHelpLong) { return true; }
        if (sameName(name, "version", ic) && command.builtInVersion) { return true; }
        if (sameName(name, "completions", ic) && command.builtInCompletions) { return true; }
        if (style.oneNamespace && sameName(name, "h", ic) && command.builtInHelpShort) { return true; }
        name == "?" && style == Style.windows && command.builtInHelpQuestion
      }

Whether `arg` has the shape of an option in `style`, known or not.

      private shapedAsOption(level: Level, style: Style, arg: String, forValue: Boolean): Boolean {
        if (startsWith(arg, "-")) {
          if (arg == "-") { return false; }
          if (style == Style.gnu) { return !(level.numbersAreValues && looksLikeNumber(arg)); }
          return !looksLikeNumber(arg);
        }
        if (style == Style.windows && startsWith(arg, "/") && arg != "/") {
          if (forValue) { return false; }
          if (!level.command.takesPositionals) { return true; }
          // An option of a command above, given too late, for its hint.
          let named = splitNamed(arg, style) ?? panic();
          for (let ancestor of level.command.ancestors) {
            if (findIn(ancestor.declared, named.name, style, false) != null) { return true; }
          }
        }
        false
      }

An argument's values are kept with the command that declared it, so an
inherited option given after a subcommand's name counts the same as
before it.

      private owner(p: Param): Level { levels[p.command.depth] }

      private give(p: Param, text: String): Void {
        if (!p.accepts(text)) {
          fail(current.command, ErrorKind.invalidValue, invalidMessage(p, text, null));
        }
        let level = owner(p);
        level.values[p.index].add(text);
        level.sources.set(p.index, Source.argument);
      }

A flag's occurrence: `true` (or `false` when negated) for a flag, and
one more (or back to zero) for a counted flag.

      private occur(p: Param, negated: Boolean): Void {
        let level = owner(p);
        let list = level.values[p.index];
        if (p.kind == ParamKind.count) {
          if (negated) { list.clear(); } else { list.add("1"); }
        } else {
          list.add(if (negated) { "false" } else { "true" });
        }
        level.sources.set(p.index, Source.argument);
      }

Errors are reported with the command where they happened, for its
usage line.

      private fail(command: Command, kind: ErrorKind, message: String): Void {
        if (firstError == null) {
          firstError = new ArgError(command, kind, message);
        }
      }

### Positional arguments

Each positional list gets its minimum, then the rest go to the
earliest lists that take more.

      private assignPositionals(level: Level): Void {
        let command = level.command;
        let texts = level.positionalTexts.toList();
        let groups = command.declared.filter { (p: Param): Boolean => p.kind == ParamKind.positional };
        var needed = 0;
        for (let g of groups) { needed += g.min; }
        var extra = texts.length - needed;
        if (extra < 0) {
          // Report the first list left short.
          var left = texts.length;
          for (let g of groups) {
            if (left < g.min) {
              let message = if (g.min == 1) {
                say("error.missingArgument", ["name", g.name])
              } else {
                say("error.tooFewArguments", ["name", g.name, "min", g.min.toString(), "count", left.max(0).toString()])
              };
              fail(command, ErrorKind.tooFewPositionals, message);
              return;
            }
            left -= g.min;
          }
          return;
        }
        var at = 0;
        for (let g of groups) {
          var take = g.min;
          let max = g.max;
          let room = if (max == null) { extra } else { (max - g.min).min(extra) };
          take += room;
          extra -= room;
          for (var k = 0; k < take; k += 1) {
            let text = texts[at + k];
            if (!g.accepts(text)) {
              fail(command, ErrorKind.invalidValue, invalidMessage(g, text, null));
            }
            level.values[g.index].add(text);
            level.sources.set(g.index, Source.argument);
          }
          at += take;
        }
        if (at < texts.length) {
          fail(command, ErrorKind.tooManyPositionals, say("error.unexpectedArgument", ["argument", texts[at]]));
        }
      }

### The environment

An argument not given reads its environment variable, if it has one
that is set and not empty.

      private readEnvironment(level: Level): Void {
        let e = env;
        if (e == null) { return; }
        let command = level.command;
        for (let p of command.declared) {
          let name = p.env;
          if (name == null || level.sources[p.index] == Source.argument) { continue; }
          let text = e.get(name);
          if (text == null || text.isEmpty) { continue; }
          if (p.kind == ParamKind.flag) {
            let b = parseBoolean(text) orelse null;
            if (b == null) {
              fail(command, ErrorKind.invalidValue, invalidValueMessage(top.messages, text, longForm(command.style, p), name, p.expected(top.messages), null));
              continue;
            }
            level.values[p.index].add(if (b) { "true" } else { "false" });
          } else if (p.kind == ParamKind.count) {
            let n = ints.parse(text) orelse -1;
            if (n < 0) {
              fail(command, ErrorKind.invalidValue, invalidValueMessage(top.messages, text, longForm(command.style, p), name, p.expected(top.messages), null));
              continue;
            }
            level.values[p.index].add(n.toString());
          } else {
            if (!p.accepts(text)) {
              fail(command, ErrorKind.invalidValue, invalidMessage(p, text, name));
              continue;
            }
            level.values[p.index].add(text);
          }
          level.sources.set(p.index, Source.environment);
        }
      }

      private checkRequired(level: Level): Void {
        for (let p of level.command.declared) {
          if (p.kind == ParamKind.option && p.required && level.values[p.index].length == 0) {
            let shown = longForm(level.command.style, p);
            let env = p.env;
            let message = if (env != null) {
              say("error.missingRequired.env", ["option", shown, "env", env])
            } else {
              say("error.missingRequired", ["option", shown])
            };
            fail(level.command, ErrorKind.missingRequired, message);
          }
        }
      }

### Suggestions

A near miss among the long names: one the typed name is a prefix of,
when only one is, or else the nearest by edit distance, when it's at
most a third of the typed name's length (at least 1). Ties go to the
earliest declared. `--no-NAME` for a flag that isn't negatable says
so instead.

      private suggestLong(command: Command, typed: String): String? {
        let names = longNames(command);
        let best = nearest(typed, names);
        if (best != null) { return "--${best}"; }
        // `--v` for `-v`.
        if (codePointCount(typed) == 1 && command.findShort(typed) != null) {
          return "-${typed}";
        }
        null
      }

`-verbose`, with one dash, for `--verbose`.

      private suggestFromShort(command: Command, arg: String): String? {
        let word = dropFirst(arg, 1);
        if (!word.hasAtLeast(String.begin, word.end, 2)) { return null; }
        let best = nearest(word, longNames(command));
        if (best != null) { "--${best}" } else { null }
      }

      private longNames(command: Command): List<String> {
        let names = new ListBuilder<String>();
        for (let p of command.options) {
          names.add(p.name);
          if (p.negatable) { names.add("no-${p.name}"); }
        }
        if (command.builtInHelpLong) { names.add("help"); }
        if (command.builtInVersion) { names.add("version"); }
        if (command.builtInCompletions) { names.add("completions"); }
        names.toList()
      }
    }

How messages and help write an option's long name in `style`:
`--level`, `-level`, or `/level`.

    let longForm(style: Style, p: Param): String { "${style.prefix}${p.name}" }

    let asciiLowerIf(text: String, lower: Boolean): String {
      if (lower) { asciiLower(text) } else { text }
    }

Whether `arg` asks for the command's help, in any of its styles: `-h`,
`--help`, `-help`, `/?`, and so on.

    let asksForHelp(command: Command, arg: String): Boolean {
      for (let style of command.styles) {
        if (style == Style.gnu) {
          if (arg == "--help" && command.builtInHelpLong) { return true; }
          if (arg == "-h" && command.builtInHelpShort) { return true; }
        } else {
          let named = splitNamed(arg, style);
          if (named != null && named.inline == null) {
            let ic = style.ignoresCase;
            if (sameName(named.name, "help", ic) && command.builtInHelpLong) { return true; }
            if (sameName(named.name, "h", ic) && command.builtInHelpShort) { return true; }
            if (named.name == "?" && style == Style.windows && command.builtInHelpQuestion) { return true; }
          }
        }
      }
      false
    }

The option that asks for help, as the error report suggests it, in the
command's first style, or null when the program took help's names.

    let helpOption(command: Command): String? {
      let style = command.style;
      if (style == Style.windows && command.builtInHelpQuestion) { return "/?"; }
      if (command.builtInHelpLong) { return "${style.prefix}help"; }
      null
    }

    let firstLevel(top: Command): ListBuilder<Level> {
      let out = new ListBuilder<Level>();
      out.add(new Level(top));
      out
    }

    let invalidMessage(p: Param, text: String, envName: String?): String {
      let what = if (p.kind == ParamKind.positional) { p.name } else { longForm(p.command.style, p) };
      let messages = p.command.messages;
      invalidValueMessage(messages, text, what, envName, p.expected(messages), nearest(text, p.choices))
    }

A value its type doesn't take, for `what` (the option or positional
argument), from an argument or the environment variable `envName`,
with the nearest valid value if there's one close enough.

    let invalidValueMessage(messages: MessageTable, text: String, what: String, envName: String?, expected: String, suggestion: String?): String {
      let values = ["value", text, "option", what, "expected", expected, "env", envName ?? "", "suggestion", suggestion ?? ""];
      let key = if (envName != null) { "error.invalidEnvValue" } else { "error.invalidValue" };
      messages.text(if (suggestion != null) { "${key}.suggest" } else { key }, values)
    }

The nearest candidate, as `suggestLong` describes, or null.

    let nearest(typed: String, candidates: List<String>): String? {
      var prefixed: String? = null;
      var prefixCount = 0;
      for (let c of candidates) {
        if (startsWith(c, typed) && c != typed) {
          prefixCount += 1;
          if (prefixed == null) { prefixed = c; }
        }
      }
      if (prefixCount == 1 && !typed.isEmpty) { return prefixed; }
      let limit = (codePointCount(typed) / 3).max(1);
      var best: String? = null;
      var bestDistance = limit + 1;
      for (let c of candidates) {
        let d = editDistance(typed, c);
        if (d < bestDistance) {
          best = c;
          bestDistance = d;
        }
      }
      best
    }

Edit distance over code points: the fewest insertions, deletions,
substitutions, and swaps of neighbors turning one into the other (the
optimal string alignment distance), so `--hlep` is one away from
`--help`.

    let editDistance(a: String, b: String): Int {
      let xs = codePoints(a);
      let bs = codePoints(b);
      let columns = bs.length + 1;
      // Rows i - 2, i - 1, and i of the table, as one list each.
      var older = new ListBuilder<Int>();
      var previous = new ListBuilder<Int>();
      for (var j = 0; j < columns; j += 1) { previous.add(j); }
      for (var i = 1; i <= xs.length; i += 1) {
        let current = new ListBuilder<Int>();
        current.add(i);
        for (var j = 1; j < columns; j += 1) {
          let cost = if (xs[i - 1] == bs[j - 1]) { 0 } else { 1 };
          var best = (previous[j] + 1).min(current[j - 1] + 1).min(previous[j - 1] + cost);
          if (i > 1 && j > 1 && xs[i - 1] == bs[j - 2] && xs[i - 2] == bs[j - 1]) {
            best = best.min(older[j - 2] + 1);
          }
          current.add(best);
        }
        older = previous;
        previous = current;
      }
      previous[columns - 1]
    }

    let codePoints(text: String): List<Int> {
      let out = new ListBuilder<Int>();
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) { out.add(text[i]); }
      out.toList()
    }

Whether the text is a negative (or signed) number, such as `-5`,
`-1.5`, or `-2e3`, which is a value rather than an option.

    let looksLikeNumber(text: String): Boolean {
      do { floats.parse(text); true } orelse false
    }

    let hasDigitShort(params: List<Param>): Boolean {
      for (let p of params) {
        let s = p.short;
        if (s != null && !s.isEmpty && isDigit(s[String.begin])) { return true; }
      }
      false
    }

    let makeBuilders(n: Int): List<ListBuilder<String>> {
      let out = new ListBuilder<ListBuilder<String>>();
      for (var i = 0; i < n; i += 1) { out.add(new ListBuilder<String>()); }
      out.toList()
    }

    let makeSources(n: Int): ListBuilder<Source> {
      let out = new ListBuilder<Source>();
      for (var i = 0; i < n; i += 1) { out.add(Source.absent); }
      out
    }
