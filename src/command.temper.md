# Commands

A `Command` is the spec of one command line: its name, what it's
about, and each argument it takes. Declaring an argument returns a
*handle*, which is also the key for reading the argument's value
after [parsing](parse.temper.md), with its type checked when the
program compiles:

```temper inert
let cli = new Command({ name: "frob", about: "Frobnicate files." });
let verbose = cli.flag({ name: "verbose", short: "v", help: "Say more." });
let level = cli.optionOr(ints, 3, { name: "level", help: "How hard." });
// In a parsed result, `args.get(verbose)` is a Boolean and
// `args.get(level)` an Int.
```

Settings come in property bags (object literals), so each reads with
its name; the class of each bag is the type of the parameter it's
passed to. Settings that change the type of the value, such as having
a default, being required, or repeating, are separate methods instead,
since a setting's value can't change a type.

## Settings

The command's own settings.

    export class CommandSpec(

The program's name, for usage lines, errors, and `--version`.

      public name: String,

One or more sentences on what the command does, the first thing in its
help.

      public about: String = "",

The version `--version` prints. Without one, there's no `--version`.

      public version: String? = null,

Whether a command with [subcommands](#subcommands) may be run without
one. By default, leaving the subcommand out is an error listing them.

      public commandOptional: Boolean = false,

How options are written: `Style.gnu` (`--verbose`, `-v`), the
default, `Style.singleDash` (`-verbose`), or `Style.windows`
(`/verbose`), as [styles](style.temper.md) describes. Subcommands
take their top command's.

      public style: Style = Style.gnu,

A second style also accepted, for a tool moving from one style to the
other; help shows the first.

      public alsoStyle: Style? = null,
    ) {}

Settings for a subcommand, declared with `cli.command`: its name, what
it's about (shown in its parent's list of commands and atop its own
help), other names it answers to, and, as for `CommandSpec`, whether
its own subcommands may be left out.

    export class SubcommandSpec(
      public name: String,
      public about: String = "",

Other names it answers to, listed in its parent's help.

      public aliases: List<String> = [],

Other names it answers to that help doesn't show, such as old names
kept working; suggestions don't offer them either.

      public hiddenAliases: List<String> = [],
      public commandOptional: Boolean = false,

Its own version, which gives it its own `--version`; without one,
only the top command has `--version`.

      public version: String? = null,
    ) {}

Settings for a flag, which takes no value: `--verbose`, or `-v` with a
`short` name of one character.

    export class FlagSpec(
      public name: String,
      public short: String? = null,
      public help: String = "",

An environment variable read when the flag isn't given, holding `1`,
`true`, `yes`, or `on`, or `0`, `false`, `no`, or `off` (for a counted
flag, a count).

      public env: String? = null,

Whether `--no-NAME` is also accepted, setting the flag back to false
(or a count back to zero), so a later argument can undo an earlier one
or a default from the environment.

      public negatable: Boolean = false,

Whether the command's subcommands accept it too, before or after their
names, as for all settings below.

      public inherited: Boolean = false,
    ) {}

Settings for an option, which takes a value: `--level 3`,
`--level=3`, `-l 3`, or `-l3`.

    export class OptionSpec(
      public name: String,
      public short: String? = null,
      public help: String = "",
      public env: String? = null,

What help calls the value, as in `--level <N>`; the name in capitals
when not set.

      public valueName: String? = null,

Whether the command's subcommands, and theirs, accept it too, before
or after their names: `frob -v add` and `frob add -v` are the same.
Help lists it under each.

      public inherited: Boolean = false,
    ) {}

Settings for positional arguments: a name for usage and help (`FILE`),
and for `positionals`, how many are allowed.

    export class PositionalSpec(
      public name: String,
      public help: String = "",
      public min: Int = 0,

The most allowed, or null for no limit.

      public max: Int? = null,
    ) {}

## What a command knows about each argument

A `Param` is one declared argument, for parsing, help, and later
completions. Programs don't usually need it, but each handle has its
`param`.

    export class Param(
      public kind: ParamKind,

The long name (without `--`), or a positional argument's name.

      public name: String,
      public short: String?,
      public help: String,
      public env: String?,

What help calls the value; empty for flags.

      public valueName: String,
      public negatable: Boolean,

Whether subcommands accept it too.

      public inherited: Boolean,
      public required: Boolean,

Whether every value is kept (repeated options, positional lists),
rather than only the last.

      public repeated: Boolean,

How many positional arguments it takes, at least and at most (null for
no limit).

      public min: Int,
      public max: Int?,

The default, as help shows it, if there is one.

      public defaultText: String?,
      public choices: List<String>,

What a valid value looks like, for errors.

      public expected: String,

Where the parsed result keeps its values.

      public index: Int,
      private checker: Checker,

The command that declared it.

      public command: Command,
    ) {

Whether `text` is a valid value.

      public accepts(text: String): Boolean { checker.accepts(text) }
    }

The kinds of argument, as named singletons.

    @auto("==")
    export class ParamKind {
      public name: String;
      private constructor(name: String) { this.name = name; }
      public static flag: ParamKind = doPure { new ParamKind("flag") }
      public static count: ParamKind = doPure { new ParamKind("count") }
      public static option: ParamKind = doPure { new ParamKind("option") }
      public static positional: ParamKind = doPure { new ParamKind("positional") }
      public toString(): String { name }
    }

A `Param` checks text through its value type without knowing the
value's type, with a `Checker`.

    export interface Checker {
      public accepts(text: String): Boolean;
    }

    class TypeChecker<T>(private type: ValueType<T>) extends Checker {
      public accepts(text: String): Boolean {
        do { type.parse(text); true } orelse false
      }
    }

    class NoValueChecker extends Checker {
      public accepts(text: String): Boolean { false }
    }

## Handles

A handle reads its argument's value from a parsed result. `args.get`
takes any handle: those that always have a value are `Arg`s, and those
that might not are `MaybeArg`s, whose `get` is nullable. (Temper's
type parameters can't stand for nullable types, so one interface can't
cover both.)

    export interface Arg<T> {
      public get param(): Param;
      public read(found: Found): T;
    }

    export interface MaybeArg<T> {
      public get param(): Param;
      public read(found: Found): T?;
    }

What a parse found for one argument: the text of each value in order
(for flags, `true` or `false`; for counted flags, a count) and where
it came from.

    export class Found(
      public values: List<String>,
      public source: Source,
    ) {
      public get last(): String? {
        if (values.isEmpty) { null } else { values[values.length - 1] }
      }
    }

Where an argument's value came from, as named singletons.

    @auto("==")
    export class Source {
      public name: String;
      private constructor(name: String) { this.name = name; }
      public static argument: Source = doPure { new Source("argument") }
      public static environment: Source = doPure { new Source("environment") }

Not given, so any default applies.

      public static absent: Source = doPure { new Source("absent") }
      public toString(): String { name }
    }

A flag reads as true when its last occurrence set it, or its default
(false) when absent.

    export class Flag(public param: Param) extends Arg<Boolean> {
      public read(found: Found): Boolean { found.last == "true" }
    }

A counted flag reads as the sum of its counts: one per `-v`, or the
number from the environment.

    export class Counter(public param: Param) extends Arg<Int> {
      public read(found: Found): Int {
        var n = 0;
        for (let v of found.values) { n += ints.parse(v) orelse 0; }
        n
      }
    }

An option with no default and not required might be absent.

    export class MaybeValue<T>(
      public param: Param,
      private type: ValueType<T>,
    ) extends MaybeArg<T> {
      public read(found: Found): T? {
        let text = found.last;
        if (text == null) { return null; }
        type.parse(text) orelse panic()
      }
    }

An option with a default, a required option, or a single positional
argument always has a value.

    export class Value<T>(
      public param: Param,
      private type: ValueType<T>,
      private fallback: T?,
    ) extends Arg<T> {
      public read(found: Found): T {
        let text = found.last;
        if (text != null) { return type.parse(text) orelse panic(); }
        fallback ?? panic()
      }
    }

A repeated option or a list of positional arguments has every value
given, in order.

    export class Values<T>(
      public param: Param,
      private type: ValueType<T>,
    ) extends Arg<List<T>> {
      public read(found: Found): List<T> {
        let out = new ListBuilder<T>();
        for (let text of found.values) { out.add(type.parse(text) orelse panic()); }
        out.toList()
      }
    }

Values were checked when parsing, so `read` parses them again rather
than keeping them untyped, which Temper couldn't cast back to `T`.

## The command

    export class Command(public spec: CommandSpec) {
      private params: ListBuilder<Param> = new ListBuilder<Param>();

Mistakes in the spec, such as a name used twice, which `parse` reports
before reading any arguments.

      private specProblems: ListBuilder<String> = new ListBuilder<String>();

The command this is a subcommand of, its subcommands, and the other
names it answers to, all set by `command`.

      private var up: Command? = null;
      private subs: ListBuilder<Command> = new ListBuilder<Command>();
      private var otherNames: List<String> = [];
      private var hiddenNames: List<String> = [];

Every argument declared, in order.

      public get declared(): List<Param> { params.toList() }

The spec's mistakes, this command's and then its subcommands', each
subcommand's ending with where it is (`in frob add`).

      public get problems(): List<String> {
        let out = new ListBuilder<String>();
        collectProblems(out);
        out.toList()
      }

A flag: true when given, false when not (or as its environment
variable says).

      public flag(spec: FlagSpec): Flag {
        new Flag(addParam(ParamKind.flag, spec.name, spec.short, spec.help, spec.env, "", spec.negatable, spec.inherited, false, false, 0, 0, null, [], booleanExpected, new NoValueChecker()))
      }

A counted flag: the number of times it's given, so `-vvv` is 3.

      public count(spec: FlagSpec): Counter {
        new Counter(addParam(ParamKind.count, spec.name, spec.short, spec.help, spec.env, "", spec.negatable, spec.inherited, false, true, 0, 0, null, [], "a count", new NoValueChecker()))
      }

An option that may be left out; its value is null then. Given more
than once, the last value wins.

      public option<T>(type: ValueType<T>, spec: OptionSpec): MaybeValue<T> {
        new MaybeValue<T>(optionParam(type, spec, false, false, null), type)
      }

An option with a default, used when it's given neither as an argument
nor in its environment variable.

      public optionOr<T>(type: ValueType<T>, fallback: T, spec: OptionSpec): Value<T> {
        new Value<T>(optionParam(type, spec, false, false, type.format(fallback)), type, fallback)
      }

An option that must be given, as an argument or in its environment
variable.

      public required<T>(type: ValueType<T>, spec: OptionSpec): Value<T> {
        new Value<T>(optionParam(type, spec, true, false, null), type, null)
      }

An option that may be given any number of times, keeping every value.
Its environment variable gives one value.

      public repeated<T>(type: ValueType<T>, spec: OptionSpec): Values<T> {
        new Values<T>(optionParam(type, spec, false, true, null), type)
      }

One positional argument, which must be there.

      public positional<T>(type: ValueType<T>, spec: PositionalSpec): Value<T> {
        new Value<T>(positionalParam(type, spec.name, spec.help, 1, 1), type, null)
      }

Positional arguments, from `spec.min` to `spec.max`. With several
lists, each gets its minimum, and the rest go to the earliest that
takes more, so `SRC... DEST` works.

      public positionals<T>(type: ValueType<T>, spec: PositionalSpec): Values<T> {
        new Values<T>(positionalParam(type, spec.name, spec.help, spec.min, spec.max), type)
      }

      private optionParam<T>(type: ValueType<T>, spec: OptionSpec, required: Boolean, repeated: Boolean, defaultText: String?): Param {
        let valueName = spec.valueName ?? asciiUpper(spec.name);
        addParam(ParamKind.option, spec.name, spec.short, spec.help, spec.env, valueName, false, spec.inherited, required, repeated, 0, 0, defaultText, type.choices, type.expected, new TypeChecker<T>(type))
      }

      private positionalParam<T>(type: ValueType<T>, name: String, help: String, min: Int, max: Int?): Param {
        if (min < 0 || (max != null && max < min) || max == 0) {
          specProblems.add("positional ${name} allows no count of arguments");
        }
        addParam(ParamKind.positional, name, null, help, null, name, false, false, min > 0, true, min, max, null, type.choices, type.expected, new TypeChecker<T>(type))
      }

      private addParam(
        kind: ParamKind, name: String, short: String?, help: String, env: String?,
        valueName: String, negatable: Boolean, inherited: Boolean, required: Boolean,
        repeated: Boolean, min: Int, max: Int?, defaultText: String?,
        choiceList: List<String>, expected: String, checker: Checker,
      ): Param {
        checkNames(kind, name, short);
        let p = new Param(kind, name, short, help, env, valueName, negatable, inherited, required, repeated, min, max, defaultText, choiceList, expected, params.length, checker, this);
        params.add(p);
        p
      }

Long names are one or more characters, not starting with `-` and
without `=` or spaces; short names are one character other than `-`.
No two arguments share a name. `help`, `h`, and `version` may be
taken, which leaves `--help`, `-h`, or `--version` to the program.

      private checkNames(kind: ParamKind, name: String, short: String?): Void {
        let isPositional = kind == ParamKind.positional;
        if (!validName(name)) {
          specProblems.add("invalid name '${name}'");
        }
        if (short != null) {
          if (short.isEmpty || short.hasAtLeast(String.begin, short.end, 2) || short == "-") {
            specProblems.add("invalid short name '${short}' for ${name}");
          }
        }
        for (let p of params.toList()) {
          let bothPositional = p.kind == ParamKind.positional;
          if (p.name == name && bothPositional == isPositional) {
            specProblems.add("${if (isPositional) { name } else { "--${name}" }} declared twice");
          }
          if (short != null && p.short == short) {
            specProblems.add("-${short} declared twice");
          }
        }
      }

Parsing and help are in [their own file](parse.temper.md) and
[another](help.temper.md); these call them. Parsing a subcommand is
parsing its top command with the subcommand's path first:
`add.parse(["a.txt"])` is `cli.parse(["add", "a.txt"])`.

      public parse(argv: List<String>, env: Environment? = null): ParseResult {
        let parent = up;
        if (parent != null) {
          let withName = new ListBuilder<String>();
          withName.add(spec.name);
          for (let arg of argv) { withName.add(arg); }
          return parent.parse(withName.toList(), env);
        }
        parseCommand(this, argv, env)
      }

      public help(width: Int = 80): String { helpText(this, width) }

      public usage(width: Int = 80): String { usageText(this, width) }

Whether `--help`, `-h`, and `--version` are built in (in `windows`
style, `/?` too): they are unless the program declares those names
itself, in any of its styles (or, for `--version`, has no version,
which a subcommand has only when its spec gives one).

      public get builtInHelpLong(): Boolean { !answers("help", false) }
      public get builtInHelpShort(): Boolean { !answers("h", true) }
      public get builtInHelpQuestion(): Boolean {
        accepts(Style.windows) && find("?", Style.windows, true) == null
      }
      public get builtInVersion(): Boolean { spec.version != null && !answers("version", false) }

      private answers(name: String, asShort: Boolean): Boolean {
        for (let style of styles) {
          if (find(name, style, asShort) != null) { return true; }
        }
        false
      }

The styles this command accepts, its top command's: the first, then
any second.

      public get styles(): List<Style> {
        let topSpec = top.spec;
        let also = topSpec.alsoStyle;
        if (also != null && also != topSpec.style) { [topSpec.style, also] } else { [topSpec.style] }
      }

The first style, which help and messages use.

      public get style(): Style { top.spec.style }

      public accepts(style: Style): Boolean {
        for (let s of styles) {
          if (s == style) { return true; }
        }
        false
      }

The option or flag this command accepts with this name in `style`: in
`gnu`, a short name when `asShort` and a long one otherwise; in the
other styles, either, ignoring case in `windows`.

      public find(name: String, style: Style, asShort: Boolean): Param? {
        findIn(options, name, style, asShort)
      }

The option or flag this command accepts with this long or short name,
if any: its own, or one its parents declared `inherited`.

      public findLong(name: String): Param? {
        for (let p of options) {
          if (p.name == name) { return p; }
        }
        null
      }

      public findShort(short: String): Param? {
        for (let p of options) {
          if (p.short == short) { return p; }
        }
        null
      }

The options and flags this command accepts: its own in the order
declared, then those its parent declared `inherited`, then its
grandparent's, and so on.

      public get options(): List<Param> {
        let out = new ListBuilder<Param>();
        for (let p of params.toList()) {
          if (p.kind != ParamKind.positional) { out.add(p); }
        }
        for (let ancestor of ancestors) {
          for (let p of ancestor.declared) {
            if (p.inherited && p.kind != ParamKind.positional) { out.add(p); }
          }
        }
        out.toList()
      }

      public get takesPositionals(): Boolean {
        for (let p of params.toList()) {
          if (p.kind == ParamKind.positional) { return true; }
        }
        false
      }

## Subcommands

`cli.command({ name: "add", about: "Add a file." })` declares a
subcommand and returns its own `Command`, with its own arguments, help,
errors, and, if it likes, subcommands of its own.

      public command(spec: SubcommandSpec): Command {
        let sub = new Command(new CommandSpec(spec.name, spec.about, spec.version, spec.commandOptional, Style.gnu, null));
        sub.up = this;
        sub.otherNames = spec.aliases;
        sub.hiddenNames = spec.hiddenAliases;
        let names = new ListBuilder<String>();
        names.add(spec.name);
        for (let alias of spec.aliases) { names.add(alias); }
        for (let alias of spec.hiddenAliases) { names.add(alias); }
        for (let name of names.toList()) {
          if (!validName(name)) {
            specProblems.add("invalid command name '${name}'");
          } else if (findCommand(name) != null) {
            specProblems.add("command ${name} declared twice");
          }
        }
        subs.add(sub);
        sub
      }

The command this is a subcommand of, or null for the top command.

      public get parent(): Command? { up }

The subcommands declared, in order.

      public get commands(): List<Command> { subs.toList() }

The other names this subcommand answers to that help shows, and those
it doesn't.

      public get aliases(): List<String> { otherNames }
      public get hiddenAliases(): List<String> { hiddenNames }

The top command's name, then each subcommand's down to this one, as
usage lines show it: `frob remote add`.

      public get path(): String {
        let parent = up;
        if (parent == null) { spec.name } else { "${parent.path} ${spec.name}" }
      }

How many commands up the top command is: 0 for the top command itself.

      public get depth(): Int {
        let parent = up;
        if (parent == null) { 0 } else { parent.depth + 1 }
      }

The commands above this one, nearest first.

      public get ancestors(): List<Command> {
        let out = new ListBuilder<Command>();
        var ancestor = up;
        while (true) {
          let a = ancestor;
          if (a == null) { break; }
          out.add(a);
          ancestor = a.parent;
        }
        out.toList()
      }

      public get top(): Command {
        let parent = up;
        if (parent == null) { this } else { parent.top }
      }

The subcommand with this name or alias, if any.

      public findCommand(name: String): Command? {
        for (let sub of subs.toList()) {
          if (sub.spec.name == name) { return sub; }
          for (let alias of sub.aliases) {
            if (alias == name) { return sub; }
          }
          for (let alias of sub.hiddenAliases) {
            if (alias == name) { return sub; }
          }
        }
        null
      }

Whether `help` is a built-in subcommand, as `frob help add`: it is for
a command with subcommands, unless one of them takes the name.

      public get builtInHelpCommand(): Boolean {
        !subs.isEmpty && findCommand("help") == null
      }

Commands are the same when their paths are, so a program can match
`args.command` against the commands it declared.

      @operator("==")
      public eq(other: Command): Boolean { path == other.path }

Mistakes are collected from the whole tree, including an option that
has the name of one its parents declared `inherited`.

      private collectProblems(out: ListBuilder<String>): Void {
        let location = if (up != null) { " in ${path}" } else { "" };
        for (let problem of specProblems.toList()) { out.add("${problem}${location}"); }
        for (let ancestor of ancestors) {
          for (let q of ancestor.declared) {
            if (!q.inherited || q.kind == ParamKind.positional) { continue; }
            for (let p of params.toList()) {
              if (p.kind == ParamKind.positional) { continue; }
              if (p.name == q.name) { out.add("--${p.name} declared twice${location}"); }
              let short = p.short;
              if (short != null && q.short == short) { out.add("-${short} declared twice${location}"); }
            }
          }
        }
        collectStyleProblems(out, location);
        for (let sub of subs.toList()) { sub.collectProblems(out); }
      }

In `singleDash` and `windows`, long and short names share one
namespace, and in `windows` case doesn't tell names apart, so names
that differ only that way are declared twice. (Those equal in `gnu`
are reported above.)

      private collectStyleProblems(out: ListBuilder<String>, location: String): Void {
        let all = options;
        let ownCount = params.toList().filter { (p: Param): Boolean => p.kind != ParamKind.positional }.length;
        for (let style of styles) {
          if (!style.oneNamespace) { continue; }
          for (var j = 0; j < ownCount; j += 1) {
            let p = all[j];
            for (var k = 0; k < all.length; k += 1) {
              if (k == j || (k < ownCount && k < j)) { continue; }
              let q = all[k];
              let clash = styleClash(p, q, style);
              if (clash != null) { out.add("${style.shortPrefix}${clash} declared twice${location}"); }
            }
          }
        }
      }
    }

The name `p` shares with `q` in `style`, if any, beyond the same long
or the same short name, which `gnu` reports already.

    let styleClash(p: Param, q: Param, style: Style): String? {
      let ic = style.ignoresCase;
      let ps = p.short;
      let qs = q.short;
      if (p.name != q.name && sameName(p.name, q.name, ic)) { return p.name; }
      if (qs != null && sameName(p.name, qs, ic)) { return p.name; }
      if (ps != null) {
        if (sameName(ps, q.name, ic)) { return ps; }
        if (qs != null && ps != qs && sameName(ps, qs, ic)) { return ps; }
      }
      null
    }

The option or flag in `params` with this name, as `Command.find`
describes.

    let findIn(params: List<Param>, name: String, style: Style, asShort: Boolean): Param? {
      let ic = style.ignoresCase;
      for (let p of params) {
        if (p.kind == ParamKind.positional) { continue; }
        let short = p.short;
        if (style.oneNamespace) {
          if (sameName(p.name, name, ic) || (short != null && sameName(short, name, ic))) { return p; }
        } else if (asShort) {
          if (short == name) { return p; }
        } else if (p.name == name) {
          return p;
        }
      }
      null
    }

A long name or a command's name is one or more characters, not
starting with `-`, and without `=` or spaces.

    let validName(name: String): Boolean {
      !(name.isEmpty || startsWith(name, "-") || contains(name, "=") || contains(name, " "))
    }

## Text helpers

    let startsWith(text: String, prefix: String): Boolean {
      var i = String.begin;
      var j = String.begin;
      while (prefix.hasIndex(j)) {
        if (!text.hasIndex(i) || text[i] != prefix[j]) { return false; }
        i = text.next(i);
        j = prefix.next(j);
      }
      true
    }

    let contains(text: String, part: String): Boolean {
      text.indexOf(part) != StringIndex.none
    }

The text after the first `n` code points.

    let dropFirst(text: String, n: Int): String {
      text.slice(text.step(String.begin, n), text.end)
    }

    let asciiUpper(text: String): String {
      let sb = new StringBuilder();
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {
        let c = text[i];
        sb.appendCodePoint(if (c >= char'a' && c <= char'z') { c - 32 } else { c }) orelse panic();
      }
      sb.toString()
    }

    let codePointCount(text: String): Int { text.countBetween(String.begin, text.end) }
