# Messages

Every piece of text Argmas writes itself, in help, errors,
suggestions, versions, completions, and completion scripts, comes from
one table of messages, so a program can translate or reword it without
changing Argmas. English is built in; a program overrides any message
by its key, and the rest stay English:

```temper inert
let cli = new Command({ name: "frob" });
cli.setMessage("usage", "Aufruf: {command}");
cli.setMessage("error.unknownOption.suggest", "unbekannte Option {option}; meinten Sie {suggestion}?");
```

What the program declares itself, such as its about text, each
argument's help, and value names, is the program's to translate.
Mistakes in the spec (`invalid command spec: ...`) stay in English:
only a program's developers see them.

## Templates

A message is a template with named placeholders in braces, such as
`{option}`, filled in when the message is written, so a translation
can put them in any order, or leave one out. `{{` and `}}` are literal
braces. Each key has its own placeholders, those its English template
uses; a template naming any other, or with a brace that doesn't pair
up, is a mistake in the spec, as is a key Argmas doesn't have, so a
typo in a translation fails the program's first run rather than
shipping. A message with a mistake isn't used: its English stands.

A message needing a count's plural, such as `error.tooFewArguments`
(at least two), has a separate key for one (`error.missingArgument`).
Full plural rules, which differ by language, are later work for a
Temper library for internationalization.

## The table

A command tree's messages, kept by its top command. Programs set them
through `Command.setMessage` and `Command.setMessages`; `text` writes
one, for value types and completers of a program's own that want to
reuse Argmas's.

    export class MessageTable {
      private overrides: MapBuilder<String, String> = new MapBuilder<String, String>();
      private mistakes: ListBuilder<String> = new ListBuilder<String>();

The template for `key`: the program's, or else English. A key Argmas
doesn't have gives itself back.

      public template(key: String): String {
        overrides.getOr(key, englishMessages.getOr(key, key))
      }

The message for `key`, with each placeholder filled in from `values`,
which are a placeholder's name followed by its value, as many times as
needed: `text("help.default", ["value", "3"])` is `[default: 3]`.

      public text(key: String, values: List<String> = []): String {
        fill(template(key), values)
      }

Uses `template` for `key` from now on, unless it's a mistake, which is
noted for the spec's problems instead.

      public set(key: String, template: String): Void {
        let english = englishMessages.getOr(key, "");
        if (english.isEmpty) {
          mistakes.add("unknown message key '${key}'");
          return;
        }
        let used = placeholders(template);
        if (used == null) {
          mistakes.add("unpaired brace in message ${key}");
          return;
        }
        let allowed = placeholders(english) ?? [];
        for (let name of used) {
          if (!isIn(name, allowed)) {
            mistakes.add("unknown placeholder {${name}} in message ${key}");
            return;
          }
        }
        overrides.set(key, template);
      }

Mistakes in the messages set, in the order set.

      public get problems(): List<String> { mistakes.toList() }

Items listed plainly, as help's notes list choices and aliases:
`fast, slow`.

      public list(items: List<String>): String {
        items.join(text("list.separator")) { (s: String): String => s }
      }

Items offered as alternatives, as in "expected one of add, rm". Two
items are joined by `list.or.pair`; with more, the last two by
`list.or.last` and the others by `list.or.separator`. English uses a
comma for each, so a translation can bring in its word for "or".

      public orList(items: List<String>): String {
        let n = items.length;
        if (n == 0) { return ""; }
        if (n == 1) { return items[0]; }
        if (n == 2) { return "${items[0]}${text("list.or.pair")}${items[1]}"; }
        let separator = text("list.or.separator");
        let out = new StringBuilder();
        for (var i = 0; i < n; i += 1) {
          if (i == n - 1) {
            out.append(text("list.or.last"));
          } else if (i > 0) {
            out.append(separator);
          }
          out.append(items[i]);
        }
        out.toString()
      }
    }

### Filling in a template

Each `{name}` takes the value given for `name`; one with no value
given stays as it is.

    let fill(template: String, values: List<String>): String {
      let out = new StringBuilder();
      var i = String.begin;
      var start = String.begin;
      while (template.hasIndex(i)) {
        let c = template[i];
        let after = template.next(i);
        if (c == char'{' || c == char'}') {
          out.append(template.slice(start, i));
          if (template.hasIndex(after) && template[after] == c) {
            out.appendCodePoint(c) orelse panic();
            i = template.next(after);
          } else if (c == char'{') {
            let close = template.indexOf("}", after);
            if (close is StringIndex) {
              let name = template.slice(after, close);
              out.append(valueFor(name, values) ?? "{${name}}");
              i = template.next(close);
            } else {
              out.append("{");
              i = after;
            }
          } else {
            out.append("}");
            i = after;
          }
          start = i;
        } else {
          i = after;
        }
      }
      out.append(template.slice(start, template.end));
      out.toString()
    }

    let valueFor(name: String, values: List<String>): String? {
      for (var k = 0; k + 1 < values.length; k += 2) {
        if (values[k] == name) { return values[k + 1]; }
      }
      null
    }

The names of a template's placeholders, in order, or null when a brace
doesn't pair up: a `{` with no `}` after it, a `}` alone, or a `{`
inside a placeholder.

    let placeholders(template: String): List<String>? {
      let out = new ListBuilder<String>();
      var i = String.begin;
      while (template.hasIndex(i)) {
        let c = template[i];
        let after = template.next(i);
        if (c == char'{' || c == char'}') {
          if (template.hasIndex(after) && template[after] == c) {
            i = template.next(after);
            continue;
          }
          if (c == char'}') { return null; }
          let close = template.indexOf("}", after);
          if (close is StringIndex) {
            let name = template.slice(after, close);
            if (contains(name, "{")) { return null; }
            out.add(name);
            i = template.next(close);
          } else {
            return null;
          }
        } else {
          i = after;
        }
      }
      out.toList()
    }

    let isIn(text: String, list: List<String>): Boolean {
      for (let item of list) {
        if (item == text) { return true; }
      }
      false
    }

A completion script's comment: each line of the message after `# `,
or `#` alone for an empty line.

    let commentLines(message: String): String {
      message.split("\n").join("\n") { (line: String): String =>
        if (line.isEmpty) { "#" } else { "# ${line}" }
      }
    }

## Keys

Every message, by its key, in English. Keys are stable names: one may
be added, but not renamed or removed while Argmas is beta without
saying so in its changes. The placeholders are those used here.

    export let englishMessages: Map<String, String> = new Map([

### Help

The usage line starts with `usage`, the command's path in `{command}`,
followed by `[OPTIONS]`, required options, positional arguments, and,
for a command with subcommands, `COMMAND` (`[COMMAND]` when it may be
left out). The headings come before each list.

      new Pair("usage", "Usage: {command}"),
      new Pair("usage.options", "[OPTIONS]"),
      new Pair("usage.command", "COMMAND"),
      new Pair("usage.optionalCommand", "[COMMAND]"),
      new Pair("help.commands", "Commands:"),
      new Pair("help.arguments", "Arguments:"),
      new Pair("help.options", "Options:"),

Notes after an item's help, each kept on one line. Lists in them are
joined with `list.separator`.

      new Pair("help.aliases", "[aliases: {aliases}]"),
      new Pair("help.default", "[default: {value}]"),
      new Pair("help.env", "[env: {name}]"),
      new Pair("help.choices", "[choices: {choices}]"),
      new Pair("help.required", "[required]"),
      new Pair("help.repeatable", "[repeatable]"),

The built-ins' help: `--help`, `--version`, the `help` subcommand,
and `--completions`, whose value is named by `builtin.completionsValue`
both in its help and after its name (`--completions <SHELL>`).

      new Pair("builtin.help", "Show this help and exit."),
      new Pair("builtin.version", "Show the version and exit."),
      new Pair("builtin.helpCommand", "Show help for a command."),
      new Pair("builtin.completions", "Print a completion script for {shell} and exit."),
      new Pair("builtin.completionsValue", "SHELL"),

What `--version` prints, before a line break: the command's path and
its version.

      new Pair("version", "{command} {version}"),

### Completions

Descriptions of candidates that help doesn't have: `--no-NAME`, which
undoes `{option}`, and `--completions`.

      new Pair("complete.negate", "Undo {option}."),
      new Pair("complete.completions", "Print a completion script for a shell and exit."),

The comment atop each shell's script, with the program's name in
`{program}`. Each line becomes a line of comment.

      new Pair("script.bash", "bash completion for {program}, generated by Argmas.\n\nSave this as ~/.local/share/bash-completion/completions/{program} for the\nbash-completion package to load when needed, or source it from\n~/.bashrc. Needs bash 4.4 or later."),
      new Pair("script.zsh", "zsh completion for {program}, generated by Argmas.\n\nSave this as _{program} in a directory on $fpath, such as ~/.zfunc with\nfpath=(~/.zfunc $fpath) before compinit in ~/.zshrc, or source it\nafter compinit."),
      new Pair("script.fish", "fish completion for {program}, generated by Argmas.\n\nSave this as ~/.config/fish/completions/{program}.fish."),
      new Pair("script.powershell", "PowerShell completion for {program}, generated by Argmas.\n\nAdd this to your profile (the file $PROFILE names), or save it and\ndot-source it from there. Needs PowerShell 5.1 or later."),

### Errors

The report printed for an error: the program's name and the message,
then the usage line, then, when help is built in, where to find more,
with the command's path and the option asking for help in `{help}`.

      new Pair("error.report", "{program}: {message}"),
      new Pair("error.tryHelp", "Try '{command} {help}' for more information."),

An option no command takes, as typed in `{option}`. With a near miss,
`suggest`, which names it in `{suggestion}`. Given after the name of
a subcommand when a command above takes it, `late`: `{name}` is the
option, `{command}` the path of the command that takes it, and
`{subcommand}` where to give it before. `--no-NAME` for a flag that
can't be negated is `notNegatable`, with the flag in `{flag}`. An
unknown option among bundled short options is `inBundle` (`-x in
-vxq`), in `{option}` of the others.

      new Pair("error.unknownOption", "unknown option {option}"),
      new Pair("error.unknownOption.suggest", "unknown option {option}; did you mean {suggestion}?"),
      new Pair("error.unknownOption.late", "unknown option {option}; {name} belongs to {command}, so give it before {subcommand}"),
      new Pair("error.unknownOption.notNegatable", "unknown option {option}; {flag} can't be negated"),
      new Pair("error.inBundle", "{option} in {bundle}"),

Values: a flag given one, an option given none (`attached` when the
next argument looks like an option, showing how to give it attached,
with `{lead}` its first character), and a value its type doesn't take,
from an argument or, in `{env}`, an environment variable, with
`suggest` for the nearest choice.

      new Pair("error.unexpectedValue", "option {option} takes no value"),
      new Pair("error.missingValue", "option {option} needs a value"),
      new Pair("error.missingValue.attached", "option {option} needs a value; to give one starting with '{lead}', write {attached}"),
      new Pair("error.invalidValue", "invalid value '{value}' for {option}: expected {expected}"),
      new Pair("error.invalidValue.suggest", "invalid value '{value}' for {option}: expected {expected}; did you mean {suggestion}?"),
      new Pair("error.invalidEnvValue", "invalid value '{value}' for {option} from {env}: expected {expected}"),
      new Pair("error.invalidEnvValue.suggest", "invalid value '{value}' for {option} from {env}: expected {expected}; did you mean {suggestion}?"),

Subcommands: a word that names none, and none given, with the names
in `{commands}` joined as alternatives.

      new Pair("error.unknownCommand", "unknown command '{command}'"),
      new Pair("error.unknownCommand.suggest", "unknown command '{command}'; did you mean {suggestion}?"),
      new Pair("error.missingCommand", "missing command; expected one of {commands}"),

Positional arguments: one missing, too few of a list that needs at
least `{min}` (two or more), with `{count}` given, and one too many.

      new Pair("error.missingArgument", "missing argument {name}"),
      new Pair("error.tooFewArguments", "missing argument {name}: needs at least {min}, got {count}"),
      new Pair("error.unexpectedArgument", "unexpected argument '{argument}'"),

A required option not given, and one that could have come from its
environment variable.

      new Pair("error.missingRequired", "missing required option {option}"),
      new Pair("error.missingRequired.env", "missing required option {option} (or {env})"),

What a valid value looks like, finishing "expected …": the built-in
value types', choices joined as alternatives, and a flag's or a
counted flag's environment variable's.

      new Pair("expected.integer", "an integer"),
      new Pair("expected.number", "a number"),
      new Pair("expected.text", "text"),
      new Pair("expected.oneOf", "one of {choices}"),
      new Pair("expected.boolean", "true or false"),
      new Pair("expected.count", "a count"),

### Lists

How lists are joined, as `MessageTable.list` and `orList` describe.

      new Pair("list.separator", ", "),
      new Pair("list.or.separator", ", "),
      new Pair("list.or.pair", ", "),
      new Pair("list.or.last", ", "),
    ]);
