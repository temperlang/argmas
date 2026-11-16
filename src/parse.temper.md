# Parsing

`cli.parse(argv, env)` reads the arguments (without the program's name)
and returns one of three results:

- `Args`, the values, read with `args.get(handle)`;
- `Output`, text to print before exiting with status 0, for `--help`
  and `--version`;
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

    export class Args(
      private found: List<Found>,
    ) extends ParseResult {
      public get exitStatus(): Int { 0 }

The value of an argument that always has one, as its handle's type.

      @overload("get")
      public getValue<T>(arg: Arg<T>): T { arg.read(foundFor(arg.param)) }

The value of an option that may be absent, or null.

      @overload("get")
      public getMaybe<T>(arg: MaybeArg<T>): T? { arg.read(foundFor(arg.param)) }

Where an argument's value came from: an argument, the environment, or
neither (`Source.absent`, so any default applies).

      public source(param: Param): Source { foundFor(param).source }

      private foundFor(param: Param): Found { found[param.index] }
    }

### Help and version

    export class Output(
      private command: Command,

Whether it's the help (true) or the version (false).

      public isHelp: Boolean,
    ) extends ParseResult {
      public get exitStatus(): Int { 0 }

The text to print to standard output, wrapped to `width` columns.

      public text(width: Int = 80): String {
        if (isHelp) {
          command.help(width)
        } else {
          "${command.spec.name} ${command.spec.version ?? ""}\n"
        }
      }
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
name, the usage, and where to find more.

      public text(width: Int = 80): String {
        let name = command.spec.name;
        let more = if (command.builtInHelpLong) { "Try '${name} --help' for more information.\n" } else { "" };
        "${name}: ${message}\n${command.usage(width)}${more}"
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
problems with arguments in the order they came, then positional
counts, then values from the environment, then missing required
options.

    let parseCommand(command: Command, argv: List<String>, env: Environment?): ParseResult {
      let problems = command.problems;
      if (!problems.isEmpty) {
        return new ArgError(command, ErrorKind.invalidSpec, "invalid command spec: ${problems[0]}");
      }
      new Parser(command, argv, env).run()
    }

    class Parser(
      private command: Command,
      private argv: List<String>,
      private env: Environment?,
    ) {
      private params: List<Param> = command.declared;
      private values: List<ListBuilder<String>> = makeBuilders(command.declared.length);
      private positionalTexts: ListBuilder<String> = new ListBuilder<String>();
      private var firstError: ArgError? = null;
      private var wantsHelp: Boolean = false;
      private var wantsVersion: Boolean = false;
      private numbersAreValues: Boolean = !hasDigitShort(command.declared);

Where each argument's values came from.

      private sources: ListBuilder<Source> = makeSources(command.declared.length);

      public run(): ParseResult {
        var i = 0;
        var onlyPositionals = false;
        let n = argv.length;
        while (i < n) {
          let arg = argv[i];
          i += 1;
          if (onlyPositionals) {
            positionalTexts.add(arg);
          } else if (arg == "--") {
            onlyPositionals = true;
          } else if (startsWith(arg, "--")) {
            i = long(arg, i);
          } else if (startsWith(arg, "-") && arg != "-" && !(numbersAreValues && looksLikeNumber(arg))) {
            i = shorts(arg, i);
          } else {
            positionalTexts.add(arg);
          }
        }
        if (wantsHelp) { return new Output(command, true); }
        if (wantsVersion) { return new Output(command, false); }
        let early = firstError;
        if (early != null) { return early; }
        assignPositionals();
        readEnvironment();
        checkRequired();
        let error = firstError;
        if (error != null) { return error; }
        let found = new ListBuilder<Found>();
        for (let p of params) {
          let texts = values[p.index].toList();
          found.add(new Found(texts, sources[p.index]));
        }
        new Args(found.toList())
      }

### Long options

`long` handles `arg` and returns the index of the next argument, past
a value it took.

      private long(arg: String, next: Int): Int {
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
            fail(ErrorKind.unknownOption, "unknown option --${name}; --${negated.name} can't be negated");
            return next;
          }
        }
        if (name == "help" && command.builtInHelpLong) {
          if (inline != null) { fail(ErrorKind.unexpectedValue, "option --help takes no value"); }
          wantsHelp = true;
          return next;
        }
        if (name == "version" && command.builtInVersion) {
          if (inline != null) { fail(ErrorKind.unexpectedValue, "option --version takes no value"); }
          wantsVersion = true;
          return next;
        }
        fail(ErrorKind.unknownOption, "unknown option --${name}${suggestLong(name)}");
        next
      }

      private takeLong(p: Param, typed: String, inline: String?, negated: Boolean, next: Int): Int {
        if (p.kind != ParamKind.option) {
          if (inline != null) {
            fail(ErrorKind.unexpectedValue, "option --${typed} takes no value");
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
            occur(p, false);
          } else if (c == "h" && command.builtInHelpShort) {
            wantsHelp = true;
          } else {
            let within = if (arg.hasAtLeast(String.begin, arg.end, 3)) { " in ${arg}" } else { "" };
            fail(ErrorKind.unknownOption, "unknown option -${c}${within}${suggestFromShort(arg)}");
            return next;
          }
          i = after;
        }
        next
      }

### Values

An option's value from the next argument, if there's one that doesn't
look like an option.

      private takeNext(p: Param, next: Int): Int {
        if (next < argv.length) {
          let candidate = argv[next];
          if (!startsWith(candidate, "-") || candidate == "-" || (numbersAreValues && looksLikeNumber(candidate))) {
            give(p, candidate);
            return next + 1;
          }
          fail(ErrorKind.missingValue, "option --${p.name} needs a value; to give one starting with '-', write --${p.name}=${candidate}");
          return next;
        }
        fail(ErrorKind.missingValue, "option --${p.name} needs a value");
        next
      }

      private give(p: Param, text: String): Void {
        if (!p.accepts(text)) {
          fail(ErrorKind.invalidValue, invalidMessage(p, text, null));
        }
        values[p.index].add(text);
        sources.set(p.index, Source.argument);
      }

A flag's occurrence: `true` (or `false` when negated) for a flag, and
one more (or back to zero) for a counted flag.

      private occur(p: Param, negated: Boolean): Void {
        let list = values[p.index];
        if (p.kind == ParamKind.count) {
          if (negated) { list.clear(); } else { list.add("1"); }
        } else {
          list.add(if (negated) { "false" } else { "true" });
        }
        sources.set(p.index, Source.argument);
      }

      private fail(kind: ErrorKind, message: String): Void {
        if (firstError == null) {
          firstError = new ArgError(command, kind, message);
        }
      }

### Positional arguments

Each positional list gets its minimum, then the rest go to the
earliest lists that take more.

      private assignPositionals(): Void {
        let texts = positionalTexts.toList();
        let groups = params.filter { (p: Param): Boolean => p.kind == ParamKind.positional };
        var needed = 0;
        for (let g of groups) { needed += g.min; }
        var extra = texts.length - needed;
        if (extra < 0) {
          // Report the first list left short.
          var left = texts.length;
          for (let g of groups) {
            if (left < g.min) {
              let message = if (g.min == 1) {
                "missing argument ${g.name}"
              } else {
                "missing argument ${g.name}: needs at least ${g.min}, got ${left.max(0)}"
              };
              fail(ErrorKind.tooFewPositionals, message);
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
              fail(ErrorKind.invalidValue, invalidMessage(g, text, null));
            }
            values[g.index].add(text);
            sources.set(g.index, Source.argument);
          }
          at += take;
        }
        if (at < texts.length) {
          fail(ErrorKind.tooManyPositionals, "unexpected argument '${texts[at]}'");
        }
      }

### The environment

An argument not given reads its environment variable, if it has one
that is set and not empty.

      private readEnvironment(): Void {
        let e = env;
        if (e == null) { return; }
        for (let p of params) {
          let name = p.env;
          if (name == null || sources[p.index] == Source.argument) { continue; }
          let text = e.get(name);
          if (text == null || text.isEmpty) { continue; }
          if (p.kind == ParamKind.flag) {
            let b = parseBoolean(text) orelse null;
            if (b == null) {
              fail(ErrorKind.invalidValue, "invalid value '${text}' for --${p.name} from ${name}: expected ${booleanExpected}");
              continue;
            }
            values[p.index].add(if (b) { "true" } else { "false" });
          } else if (p.kind == ParamKind.count) {
            let n = ints.parse(text) orelse -1;
            if (n < 0) {
              fail(ErrorKind.invalidValue, "invalid value '${text}' for --${p.name} from ${name}: expected a count");
              continue;
            }
            values[p.index].add(n.toString());
          } else {
            if (!p.accepts(text)) {
              fail(ErrorKind.invalidValue, invalidMessage(p, text, name));
              continue;
            }
            values[p.index].add(text);
          }
          sources.set(p.index, Source.environment);
        }
      }

      private checkRequired(): Void {
        for (let p of params) {
          if (p.kind == ParamKind.option && p.required && values[p.index].length == 0) {
            let orEnv = if (p.env != null) { " (or ${p.env})" } else { "" };
            fail(ErrorKind.missingRequired, "missing required option --${p.name}${orEnv}");
          }
        }
      }

### Suggestions

A near miss among the long names: one the typed name is a prefix of,
when only one is, or else the nearest by edit distance, when it's at
most a third of the typed name's length (at least 1). Ties go to the
earliest declared. `--no-NAME` for a flag that isn't negatable says
so instead.

      private suggestLong(typed: String): String {
        let names = longNames();
        let best = nearest(typed, names);
        if (best != null) { return "; did you mean --${best}?"; }
        // `--v` for `-v`.
        if (codePointCount(typed) == 1 && command.findShort(typed) != null) {
          return "; did you mean -${typed}?";
        }
        ""
      }

`-verbose`, with one dash, for `--verbose`.

      private suggestFromShort(arg: String): String {
        let word = dropFirst(arg, 1);
        if (!word.hasAtLeast(String.begin, word.end, 2)) { return ""; }
        let best = nearest(word, longNames());
        if (best != null) { "; did you mean --${best}?" } else { "" }
      }

      private longNames(): List<String> {
        let names = new ListBuilder<String>();
        for (let p of params) {
          if (p.kind != ParamKind.positional) {
            names.add(p.name);
            if (p.negatable) { names.add("no-${p.name}"); }
          }
        }
        if (command.builtInHelpLong) { names.add("help"); }
        if (command.builtInVersion) { names.add("version"); }
        names.toList()
      }
    }

    let invalidMessage(p: Param, text: String, envName: String?): String {
      let what = if (p.kind == ParamKind.positional) { p.name } else { "--${p.name}" };
      let from = if (envName != null) { " from ${envName}" } else { "" };
      let near = nearest(text, p.choices);
      let suggestion = if (near != null) { "; did you mean ${near}?" } else { "" };
      "invalid value '${text}' for ${what}${from}: expected ${p.expected}${suggestion}"
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
