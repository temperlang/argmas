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

Whether `--completions SHELL` is built in, printing a script that sets
up [completions](complete.temper.md) in that shell. Off by default,
since it's another option in help; a program can instead print
`cli.completionScript(shell)` from a subcommand of its own.

      public completions: Boolean = false,
    ) {}

Settings for a subcommand, declared with `cli.subcommand`: its name,
what it's about (shown in its parent's list of commands and atop its
own help), other names it answers to, and, as for `CommandSpec`,
whether its own subcommands may be left out.

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

Whether the flag is on (true) when it isn't given, for a flag such as
`--color` that users turn off with `--no-color`. Such a flag is
negatable whether `negatable` is set or not, since otherwise only its
environment variable could turn it off. Help shows `[default: on]`.
Last, so that languages passing settings in order keep their places.
A counted flag can't be on.

      public on: Boolean = false,
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

What shells offer when completing its value, found when the program
runs, such as the names of branches; without one, its value type
decides.

      public completer: Completer? = null,
    ) {}

Settings for positional arguments: a name for usage and help (`FILE`),
and for `positionals`, how many are allowed.

    export class PositionalSpec(
      public name: String,
      public help: String = "",
      public min: Int = 0,

The most allowed, or null for no limit.

      public max: Int? = null,
      public completer: Completer? = null,
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

Whether a flag is true when not given.

      public on: Boolean,

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

Where the parsed result keeps its values.

      public index: Int,
      private checker: Checker,
      private completer: Completer?,

The command that declared it.

      public command: Command,
    ) {

Whether `text` is a valid value.

      public accepts(text: String): Boolean { checker.accepts(text) }

What a valid value looks like, for errors, in `messages`.

      public expected(messages: MessageTable): String { checker.expected(messages) }

How a shell completes a value starting with `partial`: from the
spec's completer, if any, or else as its value type says.

      public complete(partial: String): Completion {
        let c = completer;
        if (c != null) { return new Completion(c.complete(partial), Directive.none, ""); }
        checker.complete(partial)
      }
    }

A `Param`'s settings as the methods declaring arguments give them to
`addParam`, with defaults, so each names only what differs. It's
internal; `Param` keeps its own constructor. An option's `required`,
`repeated`, and `defaultText` are `var`, set by the method that
declares it.

`max` has no default because a default also replaces an explicit
`null`, which here means no limit; flags and options give 0.

    class ParamSettings(
      public kind: ParamKind,
      public name: String,
      public checker: Checker,
      public max: Int?,
      public short: String? = null,
      public help: String = "",
      public env: String? = null,
      public valueName: String = "",
      public negatable: Boolean = false,
      public on: Boolean = false,
      public inherited: Boolean = false,
      public var required: Boolean = false,
      public var repeated: Boolean = false,
      public min: Int = 0,
      public var defaultText: String? = null,
      public choices: List<String> = [],
      public completer: Completer? = null,
    ) {}

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
      public complete(partial: String): Completion;
      public expected(messages: MessageTable): String;
    }

    class TypeChecker<T>(private type: ValueType<T>) extends Checker {
      public accepts(text: String): Boolean {
        do { type.parse(text); true } orelse false
      }
      public complete(partial: String): Completion { type.complete(partial) }
      public expected(messages: MessageTable): String { type.expectedIn(messages) }
    }

Flags take no value on the command line; `expectedKey` is the message
for what their environment variable holds.

    class NoValueChecker(private expectedKey: String) extends Checker {
      public expected(messages: MessageTable): String { messages.text(expectedKey) }
      public accepts(text: String): Boolean { false }
      public complete(partial: String): Completion { new Completion([], Directive.none, "") }
    }

## Handles

A handle reads its argument's value from a parsed result. `args.get`
takes any handle: those that always have a value are `Arg`s, and those
that might not are `MaybeArg`s, whose `get` is nullable. (Temper's
type parameters can't stand for nullable types, so one interface can't
cover both.) Declaring an argument returns one of these two
interfaces, not the class below that implements it, so every language
sees the value's type in the handle's: C++ deduces `getValue`'s type,
and Rust needs no wrapping.

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
(false, unless it's `on`) when absent.

    class Flag(public param: Param) extends Arg<Boolean> {
      public read(found: Found): Boolean {
        let last = found.last;
        if (last == null) { param.on } else { last == "true" }
      }
    }

A counted flag reads as the sum of its counts: one per `-v`, or the
number from the environment.

    class Counter(public param: Param) extends Arg<Int> {
      public read(found: Found): Int {
        var n = 0;
        for (let v of found.values) { n += ints.parse(v) orelse 0; }
        n
      }
    }

An option with no default and not required might be absent.

    class MaybeValue<T>(
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

    class Value<T>(
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

    class Values<T>(
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
names it answers to, all set by `subcommand`.

      private var up: Command? = null;
      private subs: ListBuilder<Command> = new ListBuilder<Command>();
      private var otherNames: List<String> = [];
      private var hiddenNames: List<String> = [];

The [messages](messages.temper.md) of the command tree, used only in
the top command.

      private table: MessageTable = new MessageTable();

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
variable says), or true when not given if it's `on`.

      public flag(spec: FlagSpec): Arg<Boolean> {
        new Flag(addParam({
          kind: ParamKind.flag, name: spec.name, checker: new NoValueChecker("expected.boolean"), max: 0,
          short: spec.short, help: spec.help, env: spec.env,
          negatable: spec.negatable || spec.on, on: spec.on, inherited: spec.inherited,
        }))
      }

A counted flag: the number of times it's given, so `-vvv` is 3.

      public count(spec: FlagSpec): Arg<Int> {
        if (spec.on) {
          specProblems.add("counted flag --${spec.name} can't be on");
        }
        new Counter(addParam({
          kind: ParamKind.count, name: spec.name, checker: new NoValueChecker("expected.count"), max: 0,
          short: spec.short, help: spec.help, env: spec.env,
          negatable: spec.negatable, inherited: spec.inherited, repeated: true,
        }))
      }

An option that may be left out; its value is null then. Given more
than once, the last value wins.

      public option<T>(type: ValueType<T>, spec: OptionSpec): MaybeArg<T> {
        new MaybeValue<T>(addParam(optionSettings(type, spec)), type)
      }

An option with a default, used when it's given neither as an argument
nor in its environment variable.

      public optionOr<T>(type: ValueType<T>, fallback: T, spec: OptionSpec): Arg<T> {
        let settings = optionSettings(type, spec);
        settings.defaultText = type.format(fallback);
        new Value<T>(addParam(settings), type, fallback)
      }

An option that must be given, as an argument or in its environment
variable.

      public required<T>(type: ValueType<T>, spec: OptionSpec): Arg<T> {
        let settings = optionSettings(type, spec);
        settings.required = true;
        new Value<T>(addParam(settings), type, null)
      }

An option that may be given any number of times, keeping every value.
Its environment variable gives one value.

      public repeated<T>(type: ValueType<T>, spec: OptionSpec): Arg<List<T>> {
        let settings = optionSettings(type, spec);
        settings.repeated = true;
        new Values<T>(addParam(settings), type)
      }

One positional argument, which must be there.

      public positional<T>(type: ValueType<T>, spec: PositionalSpec): Arg<T> {
        let one: PositionalSpec = { name: spec.name, help: spec.help, min: 1, max: 1, completer: spec.completer };
        new Value<T>(positionalParam(type, one), type, null)
      }

Positional arguments, from `spec.min` to `spec.max`. With several
lists, each gets its minimum, and the rest go to the earliest that
takes more, so `SRC... DEST` works.

      public positionals<T>(type: ValueType<T>, spec: PositionalSpec): Arg<List<T>> {
        new Values<T>(positionalParam(type, spec), type)
      }

An option's settings, before its method sets whether it's required or
repeated, or its default.

      private optionSettings<T>(type: ValueType<T>, spec: OptionSpec): ParamSettings {
        {
          class: ParamSettings,
          kind: ParamKind.option, name: spec.name, checker: new TypeChecker<T>(type), max: 0,
          short: spec.short, help: spec.help, env: spec.env,
          valueName: spec.valueName ?? asciiUpper(spec.name), inherited: spec.inherited,
          choices: type.choices, completer: spec.completer,
        }
      }

      private positionalParam<T>(type: ValueType<T>, spec: PositionalSpec): Param {
        let name = spec.name;
        let min = spec.min;
        let max = spec.max;
        if (min < 0 || (max != null && max < min) || max == 0) {
          specProblems.add("positional ${name} allows no count of arguments");
        }
        addParam({
          kind: ParamKind.positional, name: name, checker: new TypeChecker<T>(type),
          help: spec.help, valueName: name, required: min > 0, repeated: true,
          min: min, max: max, choices: type.choices, completer: spec.completer,
        })
      }

      private addParam(s: ParamSettings): Param {
        checkNames(s.kind, s.name, s.short);
        let p = new Param(
          s.kind, s.name, s.short, s.help, s.env, s.valueName, s.negatable, s.on, s.inherited,
          s.required, s.repeated, s.min, s.max, s.defaultText, s.choices,
          params.length, s.checker, s.completer, this,
        );
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

## Messages

Every text Argmas writes itself comes from one
[table of messages](messages.temper.md), English unless the program
sets its own. `setMessage` replaces the message for `key`, such as
`error.unknownOption.suggest`, with `template`, which may use that
key's placeholders, such as `{option}`, in any order; `setMessages`
does so for every entry in `templates`, such as a whole translation.
Messages belong to the whole command tree, so a subcommand's are its
top command's. A key or placeholder Argmas doesn't have is a mistake
in the spec, which `parse` reports.

      public setMessage(key: String, template: String): Void {
        top.table.set(key, template);
      }

      public setMessages(templates: Mapped<String, String>): Void {
        let messageTable = top.table;
        templates.forEach { (key: String, template: String): Void => messageTable.set(key, template); }
      }

The messages in use, for writing them.

      public get messages(): MessageTable { top.table }

What a shell offers for the word at `index` in `words`, the arguments
typed so far (without the program's name), as
[completions](complete.temper.md) describes; by default, for the last
word. As with `parse`, a subcommand's are its top command's with its
path first.

      public complete(words: List<String>, index: Int? = null): Completion {
        let at = index ?? (words.length - 1).max(0);
        let parent = up;
        if (parent != null) {
          let withName = new ListBuilder<String>();
          withName.add(spec.name);
          for (let word of words) { withName.add(word); }
          return parent.complete(withName.toList(), at + 1);
        }
        completeWords(this, words, at)
      }

The script that sets up completions for this command in `shell`, as
[shells](shells.temper.md) describes. It asks the program itself for
completions as the user types, so it needn't change when the program
does.

      public completionScript(shell: Shell): String { top.scriptFor(shell) }

      private scriptFor(shell: Shell): String { shellScript(shell, spec.name, table) }

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

Whether `--completions` is built in: for the top command, when its spec
asks for it and the program doesn't take the name.

      public get builtInCompletions(): Boolean { up == null && spec.completions && !answers("completions", false) }

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

`cli.subcommand({ name: "add", about: "Add a file." })` declares a
subcommand and returns its own `Command`, with its own arguments, help,
errors, and, if it likes, subcommands of its own.

      public subcommand(spec: SubcommandSpec): Command {
        let sub = new Command({ class: CommandSpec, name: spec.name, about: spec.about, version: spec.version, commandOptional: spec.commandOptional });
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
          } else if (name == completeWord && up == null) {
            specProblems.add("command name '${name}' is reserved for completions");
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
        if (up == null) {
          for (let problem of table.problems) { out.add(problem); }
        }
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
        collectBundleProblems(out, location);
        for (let sub of subs.toList()) { sub.collectProblems(out); }
      }

With `gnu` and another style, a long name could also be a `gnu`
bundle of short options: with `vq`, `v`, and `q`, `-vq` would be
`-vq` in `singleDash` or `windows` but `-v -q` in `gnu`, as would
`vo` with a flag `v` and an option `o` (`-v -o` and a value next).
A short option followed by more letters, as `-l evel` for `-level`,
isn't reported: a long name read in full always wins over a value
attached to a short option, as styles decide. Parsing
reads it as the long name, so the bundle can't be given that way, and
users can't know which they get; this reports it, so a spec with it
can't ship. Each is reported where it first appears: a long name
inherited from above meets this command's short names here.

      private collectBundleProblems(out: ListBuilder<String>, location: String): Void {
        var hasGnu = false;
        var hasOther = false;
        for (let style of styles) {
          if (style == Style.gnu) { hasGnu = true; } else { hasOther = true; }
        }
        if (!hasGnu || !hasOther) { return; }
        let all = options;
        let names = new ListBuilder<String>();
        let owned = new ListBuilder<Boolean>();
        for (let p of all) {
          // Own, not inherited: those come from commands further up.
          let own = p.command == this;
          names.add(p.name);
          owned.add(own);
          if (p.negatable) {
            names.add("no-${p.name}");
            owned.add(own);
          }
        }
        let isTop = up == null;
        if (builtInHelpLong) { names.add("help"); owned.add(isTop); }
        if (builtInVersion) { names.add("version"); owned.add(isTop); }
        if (builtInCompletions) { names.add("completions"); owned.add(true); }
        let nameList = names.toList();
        for (var k = 0; k < nameList.length; k += 1) {
          let name = nameList[k];
          if (!name.hasAtLeast(String.begin, name.end, 2)) { continue; }
          let reading = bundleReading(name, all);
          if (reading == null) { continue; }
          if (owned[k] || reading.ownedBy(this)) {
            out.add("long name ${name} could also be read as ${reading.text}${location}");
          }
        }
      }

How `-name` reads as a `gnu` bundle of this command's short options,
or null when it doesn't: each a flag until one takes a value, which
takes the rest of the name, or the next argument.

      private bundleReading(name: String, all: List<Param>): BundleReading? {
        let parts = new ListBuilder<String>();
        let used = new ListBuilder<Param>();
        var i = String.begin;
        while (name.hasIndex(i)) {
          let after = name.next(i);
          let c = name.slice(i, after);
          let p = findIn(all, c, Style.gnu, true);
          if (p != null) {
            used.add(p);
            parts.add("-${c}");
            if (p.kind == ParamKind.option) {
              // An attached value, as in `-l evel` for `-level`, is
              // decided: the long name wins, as styles say.
              if (name.hasIndex(after)) { return null; }
              return new BundleReading(parts.join(" ") { (s: String): String => s }, used.toList());
            }
          } else if (c == "h" && builtInHelpShort) {
            parts.add("-h");
          } else {
            return null;
          }
          i = after;
        }
        new BundleReading(parts.join(" ") { (s: String): String => s }, used.toList())
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

How a long name reads as a bundle, and the options it uses.

    class BundleReading(public text: String, public used: List<Param>) {
      public ownedBy(command: Command): Boolean {
        for (let p of used) {
          if (p.command == command) { return true; }
        }
        false
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
