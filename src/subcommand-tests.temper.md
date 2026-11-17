# Subcommand tests

Tables of arguments in and results out for commands with subcommands,
and goldens of their help. Every decision on subcommands in the
[design](../docs/design.md#behavior-the-same-in-every-language) has a
test here.

## The test command

`Tree` is a small version-control tool: `-v` is inherited by every
subcommand, `-C` isn't, `remote` has subcommands of its own, and
`rm` has aliases, one of them hidden. `run` shows a result as text: the path of the
command that ran, then each argument that was given, as `name=value`,
or which command's help, or an error's kind and message.

    class Tree {
      public cli: Command;
      public verbose: Arg<Int>;
      public dir: MaybeArg<String>;
      public add: Command;
      public force: Arg<Boolean>;
      public addFiles: Arg<List<String>>;
      public rm: Command;
      public cached: Arg<Boolean>;
      public rmFile: Arg<String>;
      public remote: Command;
      public dryRun: Arg<Boolean>;
      public remoteAdd: Command;
      public remoteName: Arg<String>;
      public remoteUrl: Arg<String>;
      public remoteList: Command;

      public constructor() {
        let cli = new Command({ name: "frob", about: "Frobnicate files.", version: "1.2.0" });
        this.cli = cli;
        verbose = cli.count({ name: "verbose", short: "v", help: "Say more.", inherited: true });
        dir = cli.option(strings, { name: "dir", short: "C", help: "Run as if started in DIR." });
        let add = cli.subcommand({ name: "add", about: "Add files." });
        this.add = add;
        force = add.flag({ name: "force", short: "f", help: "Add ignored files too." });
        addFiles = add.positionals(strings, { name: "FILE", min: 1, help: "Files to add." });
        let rm = cli.subcommand({ name: "rm", about: "Remove files.", aliases: ["remove", "del"], hiddenAliases: ["erase"] });
        this.rm = rm;
        cached = rm.flag({ name: "cached", help: "Keep the file itself." });
        rmFile = rm.positional(strings, { name: "FILE", help: "The file to remove." });
        let remote = cli.subcommand({ name: "remote", about: "Manage remotes." });
        this.remote = remote;
        dryRun = remote.flag({ name: "dry-run", short: "n", help: "Change nothing.", inherited: true });
        let remoteAdd = remote.subcommand({ name: "add", about: "Add a remote." });
        this.remoteAdd = remoteAdd;
        remoteName = remoteAdd.positional(strings, { name: "NAME" });
        remoteUrl = remoteAdd.positional(strings, { name: "URL" });
        remoteList = remote.subcommand({ name: "list", about: "List remotes.", aliases: ["ls"] });
      }

      public run(argv: List<String>): String { show(cli.parse(argv)) }

      public show(result: ParseResult): String {
        when (result) {
          is Args -> do {
            let args = result;
            let parts = new ListBuilder<String>();
            parts.add("${args.command.path}:");
            if (wasGiven(args, verbose.param)) { parts.add("verbose=${args.get(verbose)}"); }
            if (wasGiven(args, dir.param)) { parts.add("dir=${args.get(dir) ?? "null"}"); }
            if (wasGiven(args, force.param)) { parts.add("force=${args.get(force)}"); }
            if (wasGiven(args, addFiles.param)) { parts.add("files=${commas(args.get(addFiles))}"); }
            if (wasGiven(args, cached.param)) { parts.add("cached=${args.get(cached)}"); }
            if (wasGiven(args, rmFile.param)) { parts.add("file=${args.get(rmFile)}"); }
            if (wasGiven(args, dryRun.param)) { parts.add("dry-run=${args.get(dryRun)}"); }
            if (wasGiven(args, remoteName.param)) { parts.add("name=${args.get(remoteName)}"); }
            if (wasGiven(args, remoteUrl.param)) { parts.add("url=${args.get(remoteUrl)}"); }
            parts.join(" ") { (s: String): String => s }
          }
          is Output -> if (result.isHelp) { "help for ${result.command.path}" } else { "version" };
          is ArgError -> "${result.kind}: ${result.message}";
          else -> "?";
        }
      }
    }

## Choosing a subcommand

The first positional argument names the subcommand, and the arguments
after it are the subcommand's.

    test("choosing a subcommand") {
      let t = new Tree();
      assert(t.run(["add", "a.txt", "b.txt"]) == "frob add: files=a.txt,b.txt");
      assert(t.run(["add", "-f", "a.txt"]) == "frob add: force=true files=a.txt");
      assert(t.run(["add", "a.txt", "--force"]) == "frob add: force=true files=a.txt");
      assert(t.run(["rm", "--cached", "a.txt"]) == "frob rm: cached=true file=a.txt");
      assert(t.run(["-C", "src", "rm", "a.txt"]) == "frob rm: dir=src file=a.txt");
    }

Aliases select the same subcommand, which keeps its own name.

    test("aliases") {
      let t = new Tree();
      assert(t.run(["remove", "a.txt"]) == "frob rm: file=a.txt");
      assert(t.run(["del", "a.txt"]) == "frob rm: file=a.txt");
      assert(t.run(["remote", "ls"]) == "frob remote list:");
    }

Hidden aliases select their subcommand too, and `help` takes them,
but help doesn't list them (see the goldens below) and suggestions
don't offer them.

    test("hidden aliases") {
      let t = new Tree();
      assert(t.run(["erase", "a.txt"]) == "frob rm: file=a.txt");
      assert(t.run(["help", "erase"]) == "help for frob rm");
      assert(t.run(["erasr", "a.txt"]) == "unknownCommand: unknown command 'erasr'");
      assert(commas(t.rm.hiddenAliases) == "erase");
      assert(commas(t.rm.aliases) == "remove,del");
    }

A program matches `args.command` against the commands it declared.

    test("matching the command that ran") {
      let t = new Tree();
      let which(argv: List<String>): String {
        let args = t.cli.parse(argv) as Args orelse panic();
        when (args.command) {
          t.add -> "add";
          t.rm -> "rm";
          t.remoteAdd -> "remote add";
          t.remoteList -> "remote list";
          else -> "other";
        }
      }
      assert(which(["add", "a"]) == "add");
      assert(which(["del", "a"]) == "rm");
      assert(which(["remote", "add", "origin", "x"]) == "remote add");
      assert(which(["remote", "ls"]) == "remote list");
      // Commands are the same by path, so `remote add` isn't `add`.
      assert(t.add != t.remoteAdd);
      assert(t.add == t.cli.findCommand("add"));
    }

## Inherited options

An option declared `inherited` may come before or after the name of
any subcommand under the command that declared it, and counts the same
either way: a counted flag adds up across both places.

    test("inherited options before and after") {
      let t = new Tree();
      assert(t.run(["-v", "add", "a"]) == "frob add: verbose=1 files=a");
      assert(t.run(["add", "-v", "a"]) == "frob add: verbose=1 files=a");
      assert(t.run(["add", "a", "--verbose"]) == "frob add: verbose=1 files=a");
      assert(t.run(["-v", "add", "-vv", "a"]) == "frob add: verbose=3 files=a");
      assert(t.run(["-v", "remote", "-v", "ls", "-v"]) == "frob remote list: verbose=3");
    }

Options that aren't inherited go before the subcommand's name, and
the error for one given after it says so, naming the subcommand right
below the command that declared it.

    test("options that aren't inherited") {
      let t = new Tree();
      assert(t.run(["-C", "src", "add", "a"]) == "frob add: dir=src files=a");
      assert(t.run(["add", "-C", "src", "a"]) == "unknownOption: unknown option -C; -C belongs to frob, so give it before add");
      assert(t.run(["add", "--dir=src", "a"]) == "unknownOption: unknown option --dir; --dir belongs to frob, so give it before add");
      assert(t.run(["add", "-fC", "src"]) == "unknownOption: unknown option -C in -fC; -C belongs to frob, so give it before add");
      assert(t.run(["remote", "add", "--dir", "x"]) == "unknownOption: unknown option --dir; --dir belongs to frob, so give it before remote");
      assert(t.run(["del", "--dir", "x"]) == "unknownOption: unknown option --dir; --dir belongs to frob, so give it before rm");
      // A subcommand's options aren't its parent's.
      assert(t.run(["-f", "add", "a"]) == "unknownOption: unknown option -f");
      // Near misses still get suggestions.
      assert(t.run(["add", "--forse"]) == "unknownOption: unknown option --forse; did you mean --force?");
    }

An inherited option of a subcommand reaches its subcommands, but not
its parent.

    test("inherited options of a subcommand") {
      let t = new Tree();
      assert(t.run(["remote", "-n", "list"]) == "frob remote list: dry-run=true");
      assert(t.run(["remote", "list", "-n"]) == "frob remote list: dry-run=true");
      assert(t.run(["remote", "add", "-vn", "o", "u"]) == "frob remote add: verbose=1 dry-run=true name=o url=u");
      assert(t.run(["-n", "remote", "list"]) == "unknownOption: unknown option -n");
    }

## Nesting

    test("nested subcommands") {
      let t = new Tree();
      assert(t.run(["remote", "add", "origin", "https://example.org/x"]) == "frob remote add: name=origin url=https://example.org/x");
      assert(t.run(["remote", "add", "origin"]) == "tooFewPositionals: missing argument URL");
      // `add` under `remote` is `remote add`, not `frob add`.
      assert(t.run(["remote", "add", "-f"]) == "unknownOption: unknown option -f");
    }

Reading an argument of a command that didn't run gives its default.

    test("arguments of commands that didn't run") {
      let t = new Tree();
      let args = t.cli.parse(["rm", "a"]) as Args orelse panic();
      assert(!args.get(t.force));
      assert(args.get(t.addFiles).isEmpty);
      assert(!args.get(t.dryRun));
      assert(args.source(t.force.param) == Source.absent);
      assert(args.get(t.rmFile) == "a");
    }

Parsing a subcommand is parsing its path from the top command.

    test("parsing a subcommand") {
      let t = new Tree();
      assert(t.show(t.add.parse(["-v", "a"])) == "frob add: verbose=1 files=a");
      assert(t.show(t.remoteAdd.parse(["o", "u"])) == "frob remote add: name=o url=u");
    }

## Unknown and missing subcommands

A word that names no subcommand is an error, suggesting the nearest
name or alias.

    test("unknown subcommands") {
      let t = new Tree();
      assert(t.run(["ad", "a"]) == "unknownCommand: unknown command 'ad'; did you mean add?");
      assert(t.run(["remov", "a"]) == "unknownCommand: unknown command 'remov'; did you mean remove?");
      assert(t.run(["frobnicate"]) == "unknownCommand: unknown command 'frobnicate'");
      assert(t.run(["remote", "lst"]) == "unknownCommand: unknown command 'lst'; did you mean list?");
      assert(t.run(["hlep"]) == "unknownCommand: unknown command 'hlep'; did you mean help?");
    }

With none given, the error lists them, unless the spec makes them
optional; `--` doesn't select one.

    test("missing subcommands") {
      let t = new Tree();
      assert(t.run([]) == "missingCommand: missing command; expected one of add, rm, remote");
      assert(t.run(["-v"]) == "missingCommand: missing command; expected one of add, rm, remote");
      assert(t.run(["remote"]) == "missingCommand: missing command; expected one of add, list");
      assert(t.run(["--", "add"]) == "missingCommand: missing command; expected one of add, rm, remote");
      let cli = new Command({ name: "opt", commandOptional: true });
      let v = cli.flag({ name: "v", short: "v" });
      let sub = cli.subcommand({ name: "sub" });
      let args = cli.parse(["-v"]) as Args orelse panic();
      assert(args.command == cli);
      assert(args.get(v));
      assert(outcome(cli.parse(["sub"])) == "ok");
      assert(outcome(cli.parse(["other"])) == "unknownCommand: unknown command 'other'");
      assert(cli.usage() == "Usage: opt [OPTIONS] [COMMAND]\n");
    }

A subcommand that takes positional arguments takes `help` and other
commands' names as values.

    test("subcommand names as values") {
      let t = new Tree();
      assert(t.run(["add", "help", "rm"]) == "frob add: files=help,rm");
    }

## Commands that take positional arguments too

A command with both gets its own positional arguments before the
subcommand's name. A word that names a subcommand selects it, after
`--` none does, and other words are positional arguments, not unknown
commands.

    test("positionals and subcommands") {
      let cli = new Command({ name: "make", commandOptional: true });
      let target = cli.positionals(strings, { name: "TARGET", max: 1 });
      let build = cli.subcommand({ name: "build" });
      let jobs = build.optionOr(ints, 1, { name: "jobs", short: "j" });
      let args = cli.parse(["x", "build", "-j", "4"]) as Args orelse panic();
      assert(args.command == build);
      assert(commas(args.get(target)) == "x");
      assert(args.get(jobs) == 4);
      let named = cli.parse(["--", "build"]) as Args orelse panic();
      assert(named.command == cli);
      assert(commas(named.get(target)) == "build");
      let other = cli.parse(["clean"]) as Args orelse panic();
      assert(commas(other.get(target)) == "clean");
      assert(outcome(cli.parse(["x", "y"])) == "tooManyPositionals: unexpected argument 'y'");
      assert(cli.usage() == "Usage: make [OPTIONS] [TARGET] [COMMAND]\n");
    }

## Help

`--help` gives the help of the command it's given to, the last one
when given more than once, and `help` gives the help of the
subcommands named after it.

    test("asking for help") {
      let t = new Tree();
      assert(t.run(["--help"]) == "help for frob");
      assert(t.run(["add", "--help"]) == "help for frob add");
      assert(t.run(["add", "-fh"]) == "help for frob add");
      assert(t.run(["--help", "add"]) == "help for frob");
      assert(t.run(["-h", "add", "-h"]) == "help for frob add");
      assert(t.run(["remote", "add", "--help"]) == "help for frob remote add");
      assert(t.run(["help"]) == "help for frob");
      assert(t.run(["help", "add"]) == "help for frob add");
      assert(t.run(["help", "del"]) == "help for frob rm");
      assert(t.run(["help", "remote", "add"]) == "help for frob remote add");
      assert(t.run(["remote", "help", "ls"]) == "help for frob remote list");
      assert(t.run(["help", "--help"]) == "help for frob");
      assert(t.run(["help", "help"]) == "help for frob");
      assert(t.run(["-v", "help", "add"]) == "help for frob add");
    }

`help` with a name that isn't a subcommand is an error.

    test("help for unknown subcommands") {
      let t = new Tree();
      assert(t.run(["help", "ad"]) == "unknownCommand: unknown command 'ad'; did you mean add?");
      assert(t.run(["help", "add", "x"]) == "unknownCommand: unknown command 'x'");
      assert(t.run(["help", "remote", "lst"]) == "unknownCommand: unknown command 'lst'; did you mean list?");
    }

Help wins over errors, as at the top: `frob bogus --help` gives
`frob`'s help, which lists the commands there are.

    test("help wins over subcommand errors") {
      let t = new Tree();
      assert(t.run(["bogus", "--help"]) == "help for frob");
      assert(t.run(["add", "--bogus", "-h"]) == "help for frob add");
      assert(t.run(["--bogus", "help", "rm"]) == "help for frob rm");
    }

A program may declare its own `help` subcommand, which then isn't
built in.

    test("a subcommand named help") {
      let cli = new Command({ name: "h" });
      let mine = cli.subcommand({ name: "help", about: "Mine." });
      let topic = mine.positionals(strings, { name: "TOPIC" });
      let args = cli.parse(["help", "x"]) as Args orelse panic();
      assert(args.command == mine);
      assert(commas(args.get(topic)) == "x");
      assert(!cli.builtInHelpCommand);
    }

`--version` belongs to the top command, and to subcommands that
declare a version of their own; it isn't inherited.

    test("version at the top only") {
      let t = new Tree();
      assert(t.run(["--version"]) == "version");
      assert(t.run(["add", "--version"]) == "unknownOption: unknown option --version");
      assert(t.run(["--version", "add", "a"]) == "version");
    }

    test("subcommand versions") {
      let cli = new Command({ name: "tool", version: "1.0.0" });
      let plugin = cli.subcommand({ name: "plugin", about: "A plugin.", version: "0.3.0" });
      plugin.subcommand({ name: "inner" });
      let version(argv: List<String>): String {
        let r = cli.parse(argv);
        when (r) {
          is Output -> r.text();
          else -> outcome(r);
        }
      }
      assert(version(["--version"]) == "tool 1.0.0\n");
      assert(version(["plugin", "--version"]) == "tool plugin 0.3.0\n");
      assert(version(["--version", "plugin"]) == "tool 1.0.0\n");
      assert(version(["plugin", "inner", "--version"]) == "unknownOption: unknown option --version");
      assert(plugin.help() == """
        "A plugin.
        "
        "Usage: tool plugin [OPTIONS] COMMAND
        "
        "Commands:
        "  inner
        "  help           Show help for a command.
        "
        "Options:
        "  -h, --help     Show this help and exit.
        "      --version  Show the version and exit.
      );
      // A subcommand may have a version when the top command has none.
      let bare = new Command({ name: "bare" });
      bare.subcommand({ name: "s", version: "2.0.0" });
      assert(outcome(bare.parse(["s", "--version"])) == "version");
      assert(outcome(bare.parse(["--version"])) == "unknownOption: unknown option --version");
    }

## Errors

An error in a subcommand shows its usage, with the top command's name
first.

    test("subcommand error reports") {
      let t = new Tree();
      let error = t.cli.parse(["add", "--forse"]) as ArgError orelse panic();
      assert(error.text() == """
        "frob: unknown option --forse; did you mean --force?
        "Usage: frob add [OPTIONS] FILE...
        "Try 'frob add --help' for more information.
      );
      let missing = t.cli.parse(["remote"]) as ArgError orelse panic();
      assert(missing.text() == """
        "frob: missing command; expected one of add, list
        "Usage: frob remote [OPTIONS] COMMAND
        "Try 'frob remote --help' for more information.
      );
    }

Argument errors come first, in the order of the arguments, then a
missing subcommand, then positional counts, the environment, and
required options, each from the top command down.

    test("subcommand error order") {
      let cli = new Command({ name: "c" });
      cli.required(strings, { name: "token", env: "C_TOKEN" });
      let sub = cli.subcommand({ name: "s" });
      sub.positional(strings, { name: "X" });
      sub.required(strings, { name: "name" });
      assert(outcome(cli.parse(["--bad", "s", "--worse"])) == "unknownOption: unknown option --bad");
      assert(outcome(cli.parse(["s", "--worse", "--bad"])) == "unknownOption: unknown option --worse");
      assert(outcome(cli.parse([])) == "missingCommand: missing command; expected one of s");
      assert(outcome(cli.parse(["s"])) == "tooFewPositionals: missing argument X");
      assert(outcome(cli.parse(["s", "x"])) == "missingRequired: missing required option --token (or C_TOKEN)");
      assert(outcome(cli.parse(["s", "x"], envOf(["C_TOKEN=t"]))) == "missingRequired: missing required option --name");
    }

## Mistakes in the spec

Subcommands' names follow the rules for long names, and no two under
one command share a name or alias. A subcommand's option can't take
the name of one inherited from above. Mistakes in subcommands say
where they are.

    test("mistakes in subcommand specs") {
      let a = new Command({ name: "a" });
      a.subcommand({ name: "x" });
      a.subcommand({ name: "x" });
      assert(outcome(a.parse([])) == "invalidSpec: invalid command spec: command x declared twice");
      let b = new Command({ name: "b" });
      b.subcommand({ name: "x", aliases: ["y"] });
      b.subcommand({ name: "y" });
      assert(outcome(b.parse([])) == "invalidSpec: invalid command spec: command y declared twice");
      let hidden = new Command({ name: "h" });
      hidden.subcommand({ name: "x", hiddenAliases: ["y"] });
      hidden.subcommand({ name: "y" });
      assert(outcome(hidden.parse([])) == "invalidSpec: invalid command spec: command y declared twice");
      let c = new Command({ name: "c" });
      c.subcommand({ name: "-x" });
      assert(outcome(c.parse([])) == "invalidSpec: invalid command spec: invalid command name '-x'");
      let d = new Command({ name: "d" });
      d.flag({ name: "verbose", short: "v", inherited: true });
      let sub = d.subcommand({ name: "s" });
      sub.flag({ name: "very", short: "v" });
      assert(outcome(d.parse(["s"])) == "invalidSpec: invalid command spec: -v declared twice in d s");
      let e = new Command({ name: "e" });
      let deeper = e.subcommand({ name: "s" }).subcommand({ name: "t" });
      deeper.flag({ name: "x" });
      deeper.flag({ name: "x" });
      assert(outcome(e.parse([])) == "invalidSpec: invalid command spec: --x declared twice in e s t");
      // The same name at two levels is fine when it isn't inherited.
      let f = new Command({ name: "f" });
      f.flag({ name: "x" });
      f.subcommand({ name: "s" }).flag({ name: "x" });
      assert(outcome(f.parse(["--x", "s", "--x"])) == "ok");
    }

## Help text

A command with subcommands lists them, with their aliases, before its
options; its usage ends with `COMMAND`.

    test("help for a command with subcommands") {
      assert(new Tree().cli.help() == """
        "Frobnicate files.
        "
        "Usage: frob [OPTIONS] COMMAND
        "
        "Commands:
        "  add              Add files.
        "  rm               Remove files. [aliases: remove, del]
        "  remote           Manage remotes.
        "  help             Show help for a command.
        "
        "Options:
        "  -v, --verbose    Say more. [repeatable]
        "  -C, --dir <DIR>  Run as if started in DIR.
        "  -h, --help       Show this help and exit.
        "      --version    Show the version and exit.
      );
    }

A subcommand's help has its path in the usage line, and its options
include those inherited, after its own.

    test("help for a subcommand") {
      assert(new Tree().add.help() == """
        "Add files.
        "
        "Usage: frob add [OPTIONS] FILE...
        "
        "Arguments:
        "  FILE...        Files to add.
        "
        "Options:
        "  -f, --force    Add ignored files too.
        "  -v, --verbose  Say more. [repeatable]
        "  -h, --help     Show this help and exit.
      );
    }

    test("help for nested subcommands") {
      let t = new Tree();
      assert(t.remote.help() == """
        "Manage remotes.
        "
        "Usage: frob remote [OPTIONS] COMMAND
        "
        "Commands:
        "  add            Add a remote.
        "  list           List remotes. [aliases: ls]
        "  help           Show help for a command.
        "
        "Options:
        "  -n, --dry-run  Change nothing.
        "  -v, --verbose  Say more. [repeatable]
        "  -h, --help     Show this help and exit.
      );
      assert(t.remoteAdd.usage() == "Usage: frob remote add [OPTIONS] NAME URL\n");
      let help = t.cli.parse(["help", "remote", "add"]) as Output orelse panic();
      assert(help.text() == t.remoteAdd.help());
    }
