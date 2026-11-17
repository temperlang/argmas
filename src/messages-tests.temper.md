# Message tests

Tests of the [message table](messages.temper.md): a program's own
messages in help, errors, and suggestions, the fallback to English,
and mistakes in a program's messages. `Frob` is the command from the
[parsing tests](parse-tests.temper.md).

## Templates

    test("filling in templates") {
      assert(fill("unknown option {option}", ["option", "--x"]) == "unknown option --x");
      assert(fill("{b} before {a}", ["a", "1", "b", "2"]) == "2 before 1");
      assert(fill("{a}{a}", ["a", "x"]) == "xx");
      assert(fill("{{literal}} {a}", ["a", "x"]) == "{literal} x");
      assert(fill("no value: {a}", []) == "no value: {a}");
      assert(fill("left { and right }", []) == "left { and right }");
    }

    test("placeholders") {
      assert(commas(placeholders("{b} and {a}, {{c}}") ?? ["(null)"]) == "b,a");
      assert(commas(placeholders("plain") ?? ["(null)"]) == "");
      assert(placeholders("open {a") == null);
      assert(placeholders("close a}") == null);
      assert(placeholders("{a{b}") == null);
    }

Every English template is well formed, so each key's placeholders are
known.

    test("English messages are well formed") {
      englishMessages.forEach { (key: String, template: String): Void =>
        assert(placeholders(template) != null) { "${key} is well formed" }
      }
    }

The [design](../docs/design.md#keys) lists every key; this count is
a reminder to update that list when a key is added.

    test("every key is listed in the design") {
      assert(englishMessages.length == 57);
    }

## A table of the program's own

Messages reworded, some with their placeholders in another order.

    let reworded(): Frob {
      let f = new Frob();
      let cli = f.cli;
      cli.setMessage("usage", "How to run {command}:");
      cli.setMessage("help.options", "Flags and options:");
      cli.setMessage("help.default", "(defaults to {value})");
      cli.setMessage("builtin.help", "Print this.");
      cli.setMessage("error.report", "error from {program}: {message}");
      cli.setMessage("error.tryHelp", "See {help} after {command}.");
      cli.setMessage("error.unknownOption.suggest", "{suggestion}, perhaps? There's no {option}.");
      cli.setMessage("error.invalidValue.suggest", "{option} takes {expected}, not {value} (try {suggestion})");
      cli.setMessage("expected.oneOf", "{choices}");
      cli.setMessage("list.or.pair", " or ");
      cli.setMessage("version", "{command}, version {version}");
      f
    }

    test("a program's messages in help") {
      let help = reworded().cli.help(60);
      assert(help == """
        "Frobnicate files.
        "
        "How to run frob: [OPTIONS] [FILE]...
        "
        "Arguments:
        "  FILE...              Files to frobnicate.
        "
        "Flags and options:
        "  -v, --verbose        Say more. [env: FROB_VERBOSE]
        "                       [repeatable]
        "      --[no-]color     Color the output. [env: FROB_COLOR]
        "  -q, --quiet          Say less.
        "  -l, --level <LEVEL>  How hard. (defaults to 3)
        "                       [env: FROB_LEVEL]
        "  -o, --output <FILE>  Where to write.
        "  -m, --mode <MODE>    How. [choices: fast, slow]
        "  -t, --tag <TAG>      A tag. [env: FROB_TAG] [repeatable]
        "  -r, --ratio <RATIO>  How much.
        "  -h, --help           Print this.
        "      --version        Show the version and exit.
      ) { help }
    }

    test("a program's messages in errors and suggestions") {
      let f = reworded();
      assert(f.run(["--verbos"]) == "unknownOption: --verbose, perhaps? There's no --verbos.");
      assert(f.run(["--mode", "fats"]) == "invalidValue: --mode takes fast or slow, not fats (try fast)");
      let error = f.cli.parse(["--verbos"]) as ArgError orelse panic();
      assert(error.text() == """
        "error from frob: --verbose, perhaps? There's no --verbos.
        "How to run frob: [OPTIONS] [FILE]...
        "See --help after frob.
      ) { error.text() }
      let version = f.cli.parse(["--version"]) as Output orelse panic();
      assert(version.text() == "frob, version 1.2.0\n");
    }

Messages not set stay English, as do keys whose message has a mistake.

    test("English for messages not set") {
      let f = reworded();
      assert(f.run(["--bogus"]) == "unknownOption: unknown option --bogus");
      assert(f.run(["--level", "x"]) == "invalidValue: invalid value 'x' for --level: expected an integer");
      assert(f.run(["--quiet=1"]) == "unexpectedValue: option --quiet takes no value");
      assert(f.cli.messages.template("help.env") == "[env: {name}]");
      assert(f.cli.messages.template("help.default") == "(defaults to {value})");
    }

Messages belong to the whole tree: a subcommand's are its top
command's, whichever command sets them.

    test("subcommands share their top command's messages") {
      let cli = new Command({ name: "frob" });
      let add = cli.subcommand({ name: "add" });
      add.setMessage("error.missingCommand", "which one? {commands}");
      cli.setMessage("list.or.last", ", or ");
      cli.subcommand({ name: "rm" });
      cli.subcommand({ name: "mv" });
      assert(outcome(cli.parse([])) == "missingCommand: which one? add, rm, or mv");
      assert(add.messages.template("list.or.last") == ", or ");
      assert(add.usage() == "Usage: frob add [OPTIONS]\n");
    }

## Mistakes in a program's messages

A key Argmas doesn't have, a placeholder its key doesn't have, and a
brace that doesn't pair up are mistakes in the spec, reported by
`parse` before reading any arguments, so they can't ship unnoticed.
The message with the mistake isn't used.

    test("mistakes in messages") {
      let f = new Frob();
      f.cli.setMessage("error.unknownOptoin", "no {option}");
      f.cli.setMessage("error.unknownOption", "no {opt}");
      f.cli.setMessage("help.options", "Options {");
      f.cli.setMessage("help.arguments", "Arguments}:");
      assert(commas(f.cli.problems) == "unknown message key 'error.unknownOptoin',unknown placeholder {opt} in message error.unknownOption,unpaired brace in message help.options,unpaired brace in message help.arguments");
      assert(f.run(["a.txt"]) == "invalidSpec: invalid command spec: unknown message key 'error.unknownOptoin'");
      assert(f.cli.messages.text("error.unknownOption", ["option", "--x"]) == "unknown option --x");
      assert(contains(f.cli.help(), "\nOptions:\n"));
      assert(f.cli.complete(["--ver"]).text() == ":none\n");
    }

    test("mistakes in a subcommand's messages") {
      let cli = new Command({ name: "frob" });
      let add = cli.subcommand({ name: "add" });
      add.setMessage("usage", "{program}");
      assert(outcome(add.parse([])) == "invalidSpec: invalid command spec: unknown placeholder {program} in message usage");
    }

## A second language

A small, partial German table, as a test fixture only: Argmas ships
English alone, and this isn't a reviewed translation. It's set from a
map, as a program would set a table it picked for the user's language,
with "oder" for the last of a list of alternatives.

    let germanFixture(): Map<String, String> {
      new Map([
        new Pair("usage", "Aufruf: {command}"),
        new Pair("usage.options", "[OPTIONEN]"),
        new Pair("usage.command", "BEFEHL"),
        new Pair("help.commands", "Befehle:"),
        new Pair("help.options", "Optionen:"),
        new Pair("help.aliases", "[auch: {aliases}]"),
        new Pair("builtin.help", "Diese Hilfe zeigen und beenden."),
        new Pair("builtin.helpCommand", "Hilfe zu einem Befehl zeigen."),
        new Pair("error.tryHelp", "Mehr unter '{command} {help}'."),
        new Pair("error.unknownCommand.suggest", "unbekannter Befehl '{command}'; meinten Sie {suggestion}?"),
        new Pair("error.unknownOption.late", "unbekannte Option {option}: {command} nimmt {name}, also vor {subcommand} angeben"),
        new Pair("error.missingCommand", "Befehl fehlt; erwartet: {commands}"),
        new Pair("list.or.pair", " oder "),
        new Pair("list.or.last", " oder "),
        new Pair("script.fish", "fish-Vervollständigung für {program}, von Argmas erzeugt."),
      ])
    }

    let germanGit(): Command {
      let git = new Command({ name: "minigit", about: "Track files.", completions: true });
      git.setMessages(germanFixture());
      git.flag({ name: "dry-run", short: "n", help: "Change nothing." });
      let add = git.subcommand({ name: "add", about: "Add files.", aliases: ["a"] });
      add.positionals(strings, { name: "PATH" });
      git.subcommand({ name: "rm", about: "Remove files." });
      git.subcommand({ name: "mv", about: "Move files." });
      git
    }

    test("a second language") {
      let git = germanGit();
      let help = git.help();
      assert(help == """
        "Track files.
        "
        "Aufruf: minigit [OPTIONEN] BEFEHL
        "
        "Befehle:
        "  add                        Add files. [auch: a]
        "  rm                         Remove files.
        "  mv                         Move files.
        "  help                       Hilfe zu einem Befehl zeigen.
        "
        "Optionen:
        "  -n, --dry-run              Change nothing.
        "  -h, --help                 Diese Hilfe zeigen und beenden.
        "      --completions <SHELL>  Print a completion script for SHELL and exit.
        "                             [choices: bash, zsh, fish, powershell]
      ) { help }
      assert(outcome(git.parse([])) == "missingCommand: Befehl fehlt; erwartet: add, rm oder mv");
      assert(outcome(git.parse(["ad"])) == "unknownCommand: unbekannter Befehl 'ad'; meinten Sie add?");
      let late = git.parse(["add", "--dry-run"]) as ArgError orelse panic();
      assert(late.text() == """
        "minigit: unbekannte Option --dry-run: minigit nimmt --dry-run, also vor add angeben
        "Aufruf: minigit add [OPTIONEN] [PATH]...
        "Mehr unter 'minigit add --help'.
      ) { late.text() }
      assert(git.complete(["h"]).text() == "help\tHilfe zu einem Befehl zeigen.\n:none\n");
      assert(startsWith(git.completionScript(Shell.fish), "# fish-Vervollständigung für minigit, von Argmas erzeugt.\n\nfunction __minigit_argmas\n"));
    }

## Value types of the program's own

A program's value type can use the table too, through `expectedIn`.

    class Even extends ValueType<Int> {
      public get expected(): String { "an even integer" }
      public expectedIn(messages: MessageTable): String {
        "${expected} (${messages.text("expected.integer")})"
      }
      public parse(text: String): Int throws Bubble {
        let n = ints.parse(text);
        if (n % 2 != 0) { bubble() }
        n
      }
      public format(value: Int): String { value.toString() }
    }

    test("a value type using messages") {
      let cli = new Command({ name: "pair" });
      cli.setMessage("expected.integer", "eine ganze Zahl");
      cli.optionOr(new Even(), 2, { name: "size" });
      assert(outcome(cli.parse(["--size", "3"])) == "invalidValue: invalid value '3' for --size: expected an even integer (eine ganze Zahl)");
      assert(ints.expected == "an integer");
      assert(ints.expectedIn(cli.messages) == "eine ganze Zahl");
    }
