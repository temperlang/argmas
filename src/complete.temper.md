# Completions

Shells complete a command line by asking the program itself: a short
[script](shells.temper.md) for each shell runs `frob __complete INDEX
WORD...` as the user presses Tab, and offers what it prints. Argmas
answers from the same spec it parses with, so completions follow
whatever the program accepts, in every [style](style.temper.md), with
nothing generated per program but a few lines of script.

`cli.complete(words, index)` is the same answer as a value: given the
words typed after the program's name and the index of the one being
completed, what could go there.

```temper inert
let cli = new Command({ name: "frob" });
cli.flag({ name: "verbose", short: "v", help: "Say more." });
cli.option(choices(["fast", "slow"]), { name: "mode" });
cli.complete(["--ver"]);          // --verbose, described "Say more."
cli.complete(["--mode", "f"]);    // fast
cli.complete(["--mode=s"]);       // --mode=slow
```

A program needs nothing more than its usual handling of `Output`:
`cli.parse(argv)` with `__complete` first returns an `Output` whose
text is the answer, for the program to print before exiting with
status 0.

## What's offered

- **Subcommands:** the names of the subcommands of the command the
  words have reached that start with the word, with their about text,
  and `help` when built in. A visible alias is offered only when the
  word starts it but not its subcommand's name (`rem` gives `remove`);
  hidden aliases never are. After `help`, the names of subcommands of
  the command named so far.
- **Options:** only once the word starts with `-`, or `/` in
  `windows`, so a plain Tab offers subcommands and positional
  arguments, as shells do for most commands. An option is offered in
  each of the command's styles, keeping the prefix typed (`--`, `-`,
  or `/`) in `singleDash` and `windows`, and in `gnu` both `-v` and
  `--verbose`; `no-` forms of negatable flags; options inherited from
  above; and the built-ins (`--help`, `-h`, `--version`,
  `--completions`). Each has its help as a description. In `windows`,
  names match ignoring case.
- **Repeats:** an option or flag already given isn't offered again,
  unless it's counted or `repeated`; a negatable flag given either way
  isn't offered either way.
- **Values:** after an option that takes one, or attached to it
  (`--mode=f`, `/mode:f`), its value: from the spec's `completer` if
  there is one, or else as its value type says (choices for `choices`,
  files for `strings` and `paths`, directories for `directories`, and
  nothing for numbers). The next positional argument's value is
  completed the same way.
- **After `--`,** only positional arguments.
- **A word that might be either,** such as `/word` in `windows`,
  gets both options and the positional argument's values.
- **With nothing to complete,** an empty word where no subcommand or
  positional argument can go, the options in the command's first style
  are offered.

Shells match candidates against the word themselves; Argmas offers
only those that start with it, so every shell sees the same list.

## The answer

A candidate is a value to put in place of the word, and a short
description, which zsh, fish, and PowerShell show.

    export class Candidate(
      public value: String,
      public description: String = "",
    ) {}

What the shell should do besides offering the candidates: nothing, or
also complete files or directories as it does for any command, which
only the shell can do well (with its own quoting, `~`, and hidden
files).

    @auto("==")
    export class Directive {
      public name: String;
      private constructor(name: String) { this.name = name; }
      public static none: Directive = doPure { new Directive("none") }
      public static files: Directive = doPure { new Directive("files") }
      public static directories: Directive = doPure { new Directive("directories") }
      public toString(): String { name }
    }

    export class Completion(
      public candidates: List<Candidate>,
      public directive: Directive = Directive.none,

For files or directories completed after an attached option, the text
before the path (`--out=` in `--out=src/`), which the shell keeps.

      public prefix: String = "",
    ) {

What `__complete` prints for a shell's script to read: a line per
candidate, its value and, when it has one, a tab and its description,
then a last line of `:` and the directive (`:none`, `:files`, or
`:directories`), with a space and the prefix when there is one. Tabs
and line breaks in descriptions become spaces, and a candidate with a
tab or line break in its value is left out.

      public text(): String {
        let out = new StringBuilder();
        for (let c of candidates) {
          if (contains(c.value, "\t") || contains(c.value, "\n") || contains(c.value, "\r")) { continue; }
          out.append(c.value);
          if (!c.description.isEmpty) {
            out.append("\t");
            out.append(oneLine(c.description));
          }
          out.append("\n");
        }
        out.append(":${directive.name}");
        if (!prefix.isEmpty) { out.append(" ${prefix}"); }
        out.append("\n");
        out.toString()
      }
    }

    let oneLine(text: String): String {
      let sb = new StringBuilder();
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {
        let c = text[i];
        sb.appendCodePoint(if (c == char'\t' || c == char'\n' || c == char'\r') { char' ' } else { c }) orelse panic();
      }
      sb.toString()
    }

## Values known when the program runs

A completer finds values as the user types, such as the names of
branches or of running jobs, for an option's or positional argument's
`completer` setting. Argmas keeps only those that start with the
partial word.

```temper inert
class Branches extends Completer {
  public complete(partial: String): List<Candidate> {
    [new Candidate("main", "default branch"), new Candidate("dev")]
  }
}
let branch = cli.option(strings, { name: "branch", completer: new Branches() });
```

A value type can do the same for every option of its type, with its
own `complete` method, which can also ask for files or directories.

    export interface Completer {
      public complete(partial: String): List<Candidate>;
    }

## The protocol

`frob __complete INDEX WORD...`: the words typed after the program's
name, and the index (from 0) of the one being completed, which is
empty when the index is past the last. The words after it are left
out. An index that isn't a number gives no candidates. Passing the
index, rather than an empty last word, lets PowerShell's script work
in versions that drop empty arguments.

`__complete` is read only as the first argument, so it can't be a top
command's subcommand (the spec reports one as a mistake), and a top
command's positional argument with that text goes after `--`. It's
not listed in help.

    let completeWord = "__complete";

    let completionRequest(command: Command, argv: List<String>): Completion {
      if (argv.length < 2) { return noCompletion(); }
      let index = ints.parse(argv[1]) orelse -1;
      if (index < 0) { return noCompletion(); }
      completeWords(command, argv.slice(2, argv.length), index)
    }

    let noCompletion(): Completion { new Completion([], Directive.none, "") }

The words before the one being completed are read as parsing reads
them, so completion knows the command they've reached, the options
given, and whether the last one waits for a value. A spec with
mistakes gets no candidates, since parsing would only report them.

    let completeWords(top: Command, words: List<String>, index: Int): Completion {
      if (!top.problems.isEmpty) { return noCompletion(); }
      let at = index.max(0).min(words.length);
      let word = if (at < words.length) { words[at] } else { "" };
      let parser = new Parser(top, words.slice(0, at), null);
      parser.scan();
      new WordCompleter(parser, word).run()
    }

    class WordCompleter(private parser: Parser, private word: String) {
      private out: ListBuilder<Candidate> = new ListBuilder<Candidate>();
      private var directive: Directive = Directive.none;
      private var prefix: String = "";

      public run(): Completion {
        let level = parser.current;
        let command = level.command;
        if (parser.lost) { return done(); }
        let target = parser.helpTarget;
        if (target != null) {
          subcommands(target, false);
          return done();
        }
        if (parser.pendingShell) {
          shells(word, "");
          return done();
        }
        let pending = parser.pending;
        if (pending != null && parser.readAs(level, word, true) == null) {
          value(pending, word, "");
          return done();
        }
        if (parser.onlyPositionals) {
          positional(level);
          return done();
        }
        let dash = startsWith(word, "-");
        let slash = command.accepts(Style.windows) && startsWith(word, "/");
        if (dash || slash) {
          if (attached(level)) { return done(); }
          options(level, command.styles);
        }
        if (!dash || looksLikeNumber(word)) {
          var room = false;
          if (!command.commands.isEmpty) {
            room = true;
            subcommands(command, true);
          }
          if (positional(level)) { room = true; }
          if (!room && word.isEmpty) { options(level, [command.style]); }
        }
        done()
      }

      private done(): Completion { new Completion(out.toList(), directive, prefix) }

      private add(value: String, description: String): Void {
        for (let c of out.toList()) {
          if (c.value == value) { return; }
        }
        out.add(new Candidate(value, description));
      }

### Subcommands

      private subcommands(command: Command, withHelp: Boolean): Void {
        for (let sub of command.commands) {
          if (startsWith(sub.spec.name, word)) {
            add(sub.spec.name, sub.spec.about);
            continue;
          }
          for (let alias of sub.aliases) {
            if (startsWith(alias, word)) {
              add(alias, sub.spec.about);
              break;
            }
          }
        }
        if (withHelp && command.builtInHelpCommand && startsWith("help", word)) {
          add("help", command.messages.text("builtin.helpCommand"));
        }
      }

### Options

Each option the command accepts and that may still be given, in each
of `styles`.

      private options(level: Level, styles: List<Style>): Void {
        let command = level.command;
        let messages = command.messages;
        for (let style of styles) {
          let lead = leadFor(style);
          let short = if (style == Style.gnu) { "-" } else { lead };
          for (let p of command.options) {
            if (exhausted(p)) { continue; }
            offer(style, "${lead}${p.name}", p.help);
            let s = p.short;
            if (s != null) { offer(style, "${short}${s}", p.help); }
            if (p.negatable) { offer(style, "${lead}no-${p.name}", messages.text("complete.negate", ["option", "${lead}${p.name}"])); }
          }
          let helpText = messages.text("builtin.help");
          if (style == Style.windows && command.builtInHelpQuestion) { offer(style, "${lead}?", helpText); }
          if (command.builtInHelpShort && style != Style.windows) { offer(style, "${short}h", helpText); }
          if (command.builtInHelpLong) { offer(style, "${lead}help", helpText); }
          if (command.builtInVersion) { offer(style, "${lead}version", messages.text("builtin.version")); }
          if (command.builtInCompletions) { offer(style, "${lead}completions", messages.text("complete.completions")); }
        }
      }

How long names start in `style`: `--` in `gnu`, and in the others,
the prefix typed, so `--name` stays `--name` in `singleDash` and
`-name` stays `-name` in `windows`.

      private leadFor(style: Style): String {
        if (style == Style.gnu) { return "--"; }
        if (startsWith(word, "--")) { return "--"; }
        if (startsWith(word, "-")) { return "-"; }
        style.prefix
      }

      private offer(style: Style, candidate: String, description: String): Void {
        let matches = if (style.ignoresCase) {
          startsWith(asciiLower(candidate), asciiLower(word))
        } else {
          startsWith(candidate, word)
        };
        if (matches) { add(candidate, description); }
      }

An option given already, which giving again would change nothing, or
only replace its value.

      private exhausted(p: Param): Boolean {
        let owner = parser.levels[p.command.depth];
        owner.sources[p.index] == Source.argument && !(p.kind == ParamKind.count || p.repeated)
      }

A value attached to an option, as in `--mode=f` or `/mode:f`, which
is completed with the option before it. Returns whether the word is
one.

      private attached(level: Level): Boolean {
        let command = level.command;
        for (let style of command.styles) {
          var name: String? = null;
          var inline: String? = null;
          if (style == Style.gnu) {
            if (startsWith(word, "--")) {
              let body = dropFirst(word, 2);
              let eq = body.indexOf("=");
              if (eq is StringIndex) {
                name = body.slice(String.begin, eq);
                inline = body.slice(body.next(eq), body.end);
              }
            }
          } else {
            let named = splitNamed(word, style);
            if (named != null) {
              name = named.name;
              inline = named.inline;
            }
          }
          let n = name;
          let v = inline;
          if (n == null || v == null) { continue; }
          let before = word.slice(String.begin, word.step(String.begin, codePointCount(word) - codePointCount(v)));
          let p = command.find(n, style, false);
          if (p != null && p.kind == ParamKind.option) {
            value(p, v, before);
            return true;
          }
          if (sameName(n, "completions", style.ignoresCase) && command.builtInCompletions) {
            shells(v, before);
            return true;
          }
        }
        false
      }

### Values

The values of `p` that start with `partial`, each after `before`.

      private value(p: Param, partial: String, before: String): Void {
        let c = p.complete(partial);
        for (let candidate of c.candidates) {
          if (startsWith(candidate.value, partial)) {
            add("${before}${candidate.value}", candidate.description);
          }
        }
        if (c.directive != Directive.none) {
          directive = c.directive;
          prefix = before;
        }
      }

      private shells(partial: String, before: String): Void {
        for (let name of shellNames) {
          if (startsWith(name, partial)) { add("${before}${name}", ""); }
        }
      }

The next positional argument's values. Returns whether the command
has room for one.

      private positional(level: Level): Boolean {
        let p = nextPositional(level);
        if (p == null) { return false; }
        value(p, word, "");
        true
      }
    }

Which positional argument the next word goes to, filling each in turn
to its most: with `SRC... DEST`, always `SRC`, since parsing gives
the last word to `DEST` only once there are no more.

    let nextPositional(level: Level): Param? {
      var before = level.positionalTexts.length;
      for (let p of level.command.declared) {
        if (p.kind != ParamKind.positional) { continue; }
        let max = p.max;
        if (max == null || before < max) { return p; }
        before -= max;
      }
      null
    }
