# Help

`cli.help(width)` is the text `--help` prints, and `cli.usage(width)`
the usage line errors show, both wrapped to `width` columns (80 when
the program doesn't know the terminal's). Columns are counted in code
points, so wide characters, such as most Chinese, Japanese, and Korean
ones, take more room than counted.

```text
Frobnicate files.

Usage: frob [OPTIONS] FILE...

Arguments:
  FILE...  Files to frobnicate.

Options:
  -v, --verbose          Say more. [repeatable]
      --[no-]color       Color the output. [env: FROB_COLOR]
  -l, --level <LEVEL>    How hard. [default: 3] [env: FROB_LEVEL]
  -h, --help             Show this help and exit.
```

- The usage line has `[OPTIONS]` when any option is optional, then
  each required option, then the positional arguments: `FILE` for
  exactly one, `[FILE]` for at most one, and `FILE...` or `[FILE]...`
  for more, by whether at least one is needed.
- Each option shows its short and long names, its value's name, and
  after its help its default, environment variable, choices, and
  whether it's required or repeatable.
- Help starts in one column for all, two after the longest name, but
  no further than two fifths of the width (and at least 16 columns in);
  a longer name has its help on the next line. Help wraps at spaces,
  and a word too long for the room is left whole.
- A command with subcommands lists them under "Commands:", each with
  its about text and aliases, before its arguments and options, and
  its usage line ends with `COMMAND` (`[COMMAND]` when it may be left
  out).
- A subcommand's usage line starts with its path (`frob add`), and its
  options include those its parents declared `inherited`, after its
  own. Hidden aliases aren't listed.
- With `completions` set, `--completions <SHELL>` is listed last,
  with the shells it knows.
- Option names are written in the command's first
  [style](style.temper.md): `--level <LEVEL>`, `-level <LEVEL>`, or
  `/level:<LEVEL>`, and help is `-h, --help`, `-h, -help`, or
  `/?, /help`.

The help puts these together.

    let helpText(command: Command, width: Int): String {
      let out = new StringBuilder();
      let spec = command.spec;
      let messages = command.messages;
      if (!spec.about.isEmpty) {
        for (let line of wrapWords(spec.about, width)) {
          out.append("${line}\n");
        }
        out.append("\n");
      }
      out.append(usageText(command, width));

      let commands = new ListBuilder<HelpItem>();
      for (let sub of command.commands) {
        let notes = if (sub.aliases.isEmpty) { [] } else {
          [messages.text("help.aliases", ["aliases", messages.list(sub.aliases)])]
        };
        commands.add(new HelpItem("  ${sub.spec.name}", sub.spec.about, notes));
      }
      if (command.builtInHelpCommand) {
        commands.add(new HelpItem("  help", messages.text("builtin.helpCommand"), []));
      }
      let arguments = new ListBuilder<HelpItem>();
      for (let p of command.declared) {
        if (p.kind == ParamKind.positional) {
          arguments.add(new HelpItem("  ${positionalForm(p, false)}", p.help, []));
        }
      }
      let style = command.style;
      let options = new ListBuilder<HelpItem>();
      for (let p of command.options) {
        options.add(new HelpItem(optionLeft(p, style), p.help, annotations(p, messages)));
      }
      let helpShort = if (style == Style.windows && command.builtInHelpQuestion) {
        "?"
      } else if (command.builtInHelpShort) {
        "h"
      } else {
        null
      };
      if (command.builtInHelpLong || helpShort != null) {
        let shortPart = if (helpShort != null) { "  ${style.shortPrefix}${helpShort}" } else { "    " };
        let left = if (command.builtInHelpLong) {
          "${shortPart}${if (helpShort != null) { ", " } else { "  " }}${style.prefix}help"
        } else {
          shortPart
        };
        options.add(new HelpItem(left, messages.text("builtin.help"), []));
      }
      if (command.builtInVersion) {
        options.add(new HelpItem("      ${style.prefix}version", messages.text("builtin.version"), []));
      }
      if (command.builtInCompletions) {
        let shell = messages.text("builtin.completionsValue");
        let shellForm = if (style == Style.windows) { ":<${shell}>" } else { " <${shell}>" };
        let choicesNote = messages.text("help.choices", ["choices", messages.list(shellNames)]);
        let about = messages.text("builtin.completions", ["shell", shell]);
        options.add(new HelpItem("      ${style.prefix}completions${shellForm}", about, [choicesNote]));
      }

      var longest = 0;
      for (let item of commands.toList()) { longest = longest.max(codePointCount(item.left)); }
      for (let item of arguments.toList()) { longest = longest.max(codePointCount(item.left)); }
      for (let item of options.toList()) { longest = longest.max(codePointCount(item.left)); }
      let column = (longest + 2).min((width * 2 / 5).max(16));

      if (!commands.isEmpty) {
        out.append("\n${messages.text("help.commands")}\n");
        for (let item of commands.toList()) { appendItem(out, item, column, width); }
      }
      if (!arguments.isEmpty) {
        out.append("\n${messages.text("help.arguments")}\n");
        for (let item of arguments.toList()) { appendItem(out, item, column, width); }
      }
      out.append("\n${messages.text("help.options")}\n");
      for (let item of options.toList()) { appendItem(out, item, column, width); }
      out.toString()
    }

An item's help is its words, then its notes, each of which stays on
one line.

    class HelpItem(public left: String, public help: String, public notes: List<String>) {
      public get units(): List<String> {
        let out = new ListBuilder<String>();
        for (let word of help.split(" ")) {
          if (!word.isEmpty) { out.add(word); }
        }
        for (let note of notes) { out.add(note); }
        out.toList()
      }
    }

    let appendItem(out: StringBuilder, item: HelpItem, column: Int, width: Int): Void {
      let lines = wrapUnits(item.units, (width - column).max(10));
      let leftLength = codePointCount(item.left);
      out.append(item.left);
      var rest = 0;
      if (lines.isEmpty) {
        rest = 0;
      } else if (leftLength + 2 <= column) {
        out.append(spaces(column - leftLength));
        out.append(lines[0]);
        rest = 1;
      }
      out.append("\n");
      for (var i = rest; i < lines.length; i += 1) {
        out.append("${spaces(column)}${lines[i]}\n");
      }
    }

## The usage line

    let usageText(command: Command, width: Int): String {
      let messages = command.messages;
      let units = new ListBuilder<String>();
      var anyOptional = command.builtInHelpLong || command.builtInHelpShort || command.builtInVersion;
      for (let p of command.options) {
        if (!p.required) { anyOptional = true; }
      }
      if (anyOptional) { units.add(messages.text("usage.options")); }
      let style = command.style;
      for (let p of command.options) {
        if (p.kind == ParamKind.option && p.required) {
          units.add("${style.prefix}${p.name}${valueForm(p, style)}");
        }
      }
      for (let p of command.declared) {
        if (p.kind == ParamKind.positional) { units.add(positionalForm(p, true)); }
      }
      if (!command.commands.isEmpty) {
        units.add(messages.text(if (command.spec.commandOptional) { "usage.optionalCommand" } else { "usage.command" }));
      }
      let lead = messages.text("usage", ["command", command.path]);
      let indent = spaces((codePointCount(lead) + 1).min(width / 2));
      let out = new StringBuilder();
      out.append(lead);
      var column = codePointCount(lead);
      for (let unit of units.toList()) {
        let length = codePointCount(unit);
        if (column + 1 + length > width && column > codePointCount(indent)) {
          out.append("\n${indent}${unit}");
          column = codePointCount(indent) + length;
        } else {
          out.append(" ${unit}");
          column += 1 + length;
        }
      }
      out.append("\n");
      out.toString()
    }

How a positional argument shows: `FILE`, `FILE...`, and in the usage
line, `[FILE]` or `[FILE]...` when it may be left out.

    let positionalForm(p: Param, brackets: Boolean): String {
      let max = p.max;
      let many = max == null || max > 1;
      let base = if (brackets && p.min == 0) { "[${p.name}]" } else { p.name };
      if (many) { "${base}..." } else { base }
    }

## Options

An option's names in `style`: `-l, --level <LEVEL>` in `gnu`,
`-l, -level <LEVEL>` in `singleDash`, and `/l, /level:<LEVEL>` in
`windows`.

    let optionLeft(p: Param, style: Style): String {
      let s = p.short;
      let shortPart = if (s != null) { "  ${style.shortPrefix}${s}, " } else { "      " };
      let negation = if (p.negatable) { "[no-]" } else { "" };
      "${shortPart}${style.prefix}${negation}${p.name}${valueForm(p, style)}"
    }

    let valueForm(p: Param, style: Style): String {
      if (p.kind != ParamKind.option) {
        ""
      } else if (style == Style.windows) {
        ":<${p.valueName}>"
      } else {
        " <${p.valueName}>"
      }
    }

    let annotations(p: Param, messages: MessageTable): List<String> {
      let out = new ListBuilder<String>();
      let fallback = p.defaultText;
      if (fallback != null) { out.add(messages.text("help.default", ["value", fallback])); }
      if (p.on) { out.add(messages.text("help.on")); }
      let env = p.env;
      if (env != null) { out.add(messages.text("help.env", ["name", env])); }
      if (!p.choices.isEmpty) {
        out.add(messages.text("help.choices", ["choices", messages.list(p.choices)]));
      }
      if (p.required) { out.add(messages.text("help.required")); }
      if (p.repeated) { out.add(messages.text("help.repeatable")); }
      out.toList()
    }

## Wrapping

`text`'s words, split at spaces, in lines of at most `width` columns.

    let wrapWords(text: String, width: Int): List<String> {
      let words = new ListBuilder<String>();
      for (let word of text.split(" ")) {
        if (!word.isEmpty) { words.add(word); }
      }
      wrapUnits(words.toList(), width)
    }

The same for units that may hold spaces, each kept on one line. A unit
longer than a line gets one to itself.

    let wrapUnits(units: List<String>, width: Int): List<String> {
      let lines = new ListBuilder<String>();
      let line = new StringBuilder();
      var column = 0;
      var empty = true;
      for (let unit of units) {
        let length = codePointCount(unit);
        if (empty) {
          line.append(unit);
          column = length;
          empty = false;
        } else if (column + 1 + length <= width) {
          line.append(" ");
          line.append(unit);
          column += 1 + length;
        } else {
          lines.add(line.toString());
          line.clear();
          line.append(unit);
          column = length;
        }
      }
      if (!empty) { lines.add(line.toString()); }
      lines.toList()
    }

    let spaces(n: Int): String {
      let sb = new StringBuilder();
      for (var i = 0; i < n; i += 1) { sb.append(" "); }
      sb.toString()
    }
