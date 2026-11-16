# Completion tests

Tables of words in and candidates out, for
[completions](complete.temper.md) in each style, with subcommands,
inherited options, values, `--`, and repeats. Every decision on
completions in the [design](../docs/design.md#completions) has a test
here.

`shown` writes a completion on one line: its candidates' values, then
the directive and any prefix when there's one, as `:files --out=`.

    let shown(c: Completion): String {
      let parts = new ListBuilder<String>();
      for (let candidate of c.candidates) { parts.add(candidate.value); }
      if (c.directive != Directive.none) {
        parts.add(if (c.prefix.isEmpty) { ":${c.directive}" } else { ":${c.directive} ${c.prefix}" });
      }
      if (parts.isEmpty) { "(none)" } else { parts.join(" ") { (s: String): String => s } }
    }

## The test commands

`frob` takes options of each kind and files; `Branches` finds values
when asked, as a program reading its repository would.

    class Branches extends Completer {
      public complete(partial: String): List<Candidate> {
        [new Candidate("main", "The default branch."), new Candidate("dev"), new Candidate("docs")]
      }
    }

    let frob(style: Style, also: Style?): Command {
      let cli = new Command({ name: "frob", about: "Frobnicate files.", version: "1.2.0", style, alsoStyle: also, completions: true });
      cli.count({ name: "verbose", short: "v", help: "Say more." });
      cli.flag({ name: "quiet", short: "q", help: "Say less." });
      cli.flag({ name: "color", help: "Color the output.", negatable: true });
      cli.optionOr(ints, 3, { name: "level", short: "l", help: "How hard." });
      cli.option(choices(["fast", "slow"]), { name: "mode", help: "How to go about it." });
      cli.repeated(strings, { name: "tag", help: "A tag." });
      cli.option(paths, { name: "out", short: "o", help: "Where to write." });
      cli.option(directories, { name: "dir", help: "Where to work." });
      cli.option(strings, { name: "branch", help: "Which branch.", completer: new Branches() });
      cli.positionals(strings, { name: "FILE", help: "Files to frobnicate." });
      cli
    }

`minigit` has subcommands, aliases, an inherited option, and
positional arguments of each kind.

    let minigit(): Command {
      let git = new Command({ name: "minigit", about: "Track files." });
      git.count({ name: "verbose", short: "v", inherited: true, help: "Say more." });
      git.option(directories, { name: "dir", help: "Where the repository is." });
      let add = git.command({ name: "add", about: "Add files.", aliases: ["stage"] });
      add.flag({ name: "force", short: "f", help: "Add ignored files too." });
      add.positionals(paths, { name: "PATH", min: 1 });
      git.command({ name: "rm", about: "Remove files.", aliases: ["remove"], hiddenAliases: ["del"] });
      let remote = git.command({ name: "remote", about: "Manage remotes." });
      let remoteAdd = remote.command({ name: "add", about: "Add a remote." });
      remoteAdd.positional(strings, { name: "NAME", completer: new Branches() });
      remoteAdd.positional(choices(["https", "ssh"]), { name: "KIND" });
      remote.command({ name: "list", about: "List remotes." });
      git
    }

## Options in `gnu`

Options are offered once the word starts with `-`: short and long
names, `no-` forms, and the built-ins, each only if it starts with the
word.

    test("gnu option names") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete(["--ver"])) == "--verbose --version");
      assert(shown(cli.complete(["--c"])) == "--color --completions");
      assert(shown(cli.complete(["--no"])) == "--no-color");
      assert(shown(cli.complete(["-"])) == "--verbose -v --quiet -q --color --no-color --level -l --mode --tag --out -o --dir --branch -h --help --version --completions");
      assert(shown(cli.complete(["-v"])) == "-v");
      assert(shown(cli.complete(["--x"])) == "(none)");
    }

A plain word gets positional arguments' values, here files, since
`FILE` is `strings`; options only when nothing else can go there.

    test("gnu words") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete([""])) == ":files");
      assert(shown(cli.complete(["a"])) == ":files");
      assert(shown(cli.complete([])) == ":files");
      let bare = new Command({ name: "bare" });
      bare.flag({ name: "all", short: "a" });
      assert(shown(bare.complete([""])) == "--all -a -h --help");
      assert(shown(bare.complete(["x"])) == "(none)");
    }

Descriptions come from help, and the protocol's text has a line for
each candidate and one for the directive.

    test("descriptions and protocol text") {
      let cli = frob(Style.gnu, null);
      let c = cli.complete(["--ver"]);
      assert(c.candidates[0].description == "Say more.");
      assert(c.text() == "--verbose\tSay more.\n--version\tShow the version and exit.\n:none\n");
      assert(cli.complete(["--out=s"]).text() == ":files --out=\n");
      assert(cli.complete(["--mode", ""]).text() == "fast\nslow\n:none\n");
      let odd = new Completion([new Candidate("a\tb"), new Candidate("ok", "two\nlines")], Directive.none, "");
      assert(odd.text() == "ok\ttwo lines\n:none\n");
    }

## Repeats

An option or flag given already isn't offered again, unless it's
counted or repeated; a negatable flag given either way isn't offered
either way.

    test("repeats") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete(["-v", "--ver"])) == "--verbose --version");
      assert(shown(cli.complete(["-q", "--q"])) == "(none)");
      assert(shown(cli.complete(["--quiet", "-q"])) == "(none)");
      assert(shown(cli.complete(["--no-color", "--c"])) == "--completions");
      assert(shown(cli.complete(["--mode", "fast", "--m"])) == "(none)");
      assert(shown(cli.complete(["--tag", "a", "--t"])) == "--tag");
      assert(shown(cli.complete(["-l5", "--l"])) == "(none)");
    }

## Values

After an option that takes a value, or attached to it, its values: the
choices, files or directories for the shell to complete, or what a
completer finds, each only if it starts with the word.

    test("values") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete(["--mode", ""])) == "fast slow");
      assert(shown(cli.complete(["--mode", "f"])) == "fast");
      assert(shown(cli.complete(["--mode=s"])) == "--mode=slow");
      assert(shown(cli.complete(["--mode="])) == "--mode=fast --mode=slow");
      assert(shown(cli.complete(["--out", ""])) == ":files");
      assert(shown(cli.complete(["-o", "sr"])) == ":files");
      assert(shown(cli.complete(["--out=sr"])) == ":files --out=");
      assert(shown(cli.complete(["--dir", ""])) == ":directories");
      assert(shown(cli.complete(["--level", ""])) == "(none)");
      assert(shown(cli.complete(["--branch", "d"])) == "dev docs");
      assert(shown(cli.complete(["--branch="])) == "--branch=main --branch=dev --branch=docs");
      assert(cli.complete(["--branch", "m"]).candidates[0].description == "The default branch.");
      assert(shown(cli.complete(["-vl", ""])) == "(none)");
    }

A word that looks like an option isn't taken as the value; `-` alone
and negative numbers are.

    test("values that look like options") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete(["--mode", "--q"])) == "--quiet");
      assert(shown(cli.complete(["--out", "-"])) == ":files");
      assert(shown(cli.complete(["--level", "-5"])) == "(none)");
    }

## `--`

After `--`, only positional arguments.

    test("after --") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete(["--", "--v"])) == ":files");
      assert(shown(cli.complete(["--", ""])) == ":files");
      // `--` itself, being completed, starts the long names.
      assert(shown(cli.complete(["--"])) == "--verbose --quiet --color --no-color --level --mode --tag --out --dir --branch --help --version --completions");
    }

## Subcommands

Subcommands' names, with their about text; a visible alias only when
it starts with the word and its name doesn't; never a hidden one.

    test("subcommand names") {
      let git = minigit();
      assert(shown(git.complete([""])) == "add rm remote help");
      assert(shown(git.complete(["r"])) == "rm remote");
      assert(shown(git.complete(["st"])) == "stage");
      assert(shown(git.complete(["d"])) == "(none)");
      assert(git.complete(["a"]).candidates[0].description == "Add files.");
      assert(shown(git.complete(["remote", ""])) == "add list help");
      assert(shown(git.complete(["-v", "remote", "l"])) == "list");
    }

A subcommand's options are its own and those inherited; a parent's
other options aren't offered after its name.

    test("subcommand options") {
      let git = minigit();
      assert(shown(git.complete(["-"])) == "--verbose -v --dir -h --help");
      assert(shown(git.complete(["add", "-"])) == "--force -f --verbose -v -h --help");
      assert(shown(git.complete(["-v", "add", "--v"])) == "--verbose");
      assert(shown(git.complete(["add", "-f", "-"])) == "--verbose -v -h --help");
      assert(shown(git.complete(["--dir", ""])) == ":directories");
    }

Positional arguments of subcommands, in turn: `NAME` from a
completer, then `KIND`'s choices, then nothing.

    test("subcommand positionals") {
      let git = minigit();
      assert(shown(git.complete(["add", ""])) == ":files");
      assert(shown(git.complete(["stage", "a", ""])) == ":files");
      assert(shown(git.complete(["remote", "add", ""])) == "main dev docs");
      assert(shown(git.complete(["remote", "add", "x", ""])) == "https ssh");
      assert(shown(git.complete(["remote", "add", "x", "ssh", ""])) == "--verbose -v -h --help");
      assert(shown(git.complete(["rm", ""])) == "--verbose -v -h --help");
    }

After `help`, the subcommands of the command named so far.

    test("after help") {
      let git = minigit();
      assert(shown(git.complete(["help", ""])) == "add rm remote");
      assert(shown(git.complete(["help", "remote", "l"])) == "list");
      assert(shown(git.complete(["help", "bogus", ""])) == "(none)");
    }

A subcommand's `complete` is its top command's with its path first,
as for `parse`.

    test("complete on a subcommand") {
      let git = minigit();
      let remote = git.findCommand("remote") ?? panic();
      assert(shown(remote.complete(["l"])) == "list");
      assert(shown(remote.complete(["add", "x", "h"])) == "https");
    }

## Index

The index picks the word completed; words after it are left out, and
an index past the last completes an empty word.

    test("index") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete(["--mode", "s", "--quiet"], 1)) == "slow");
      assert(shown(cli.complete(["--mode"], 1)) == "fast slow");
      assert(shown(cli.complete(["--mode"], 5)) == "fast slow");
      assert(shown(cli.complete(["--ver", "x"], 0)) == "--verbose --version");
    }

## `__complete`

Through `parse`, `__complete` first gives an `Output` with the
protocol's text; a bad index gives no candidates, and `__complete`
anywhere else is an ordinary word.

    test("__complete through parse") {
      let cli = frob(Style.gnu, null);
      let out = cli.parse(["__complete", "1", "--mode", "f"]) as Output orelse panic();
      assert(out.kind == OutputKind.completions);
      assert(out.exitStatus == 0);
      assert(out.text() == "fast\n:none\n");
      assert((cli.parse(["__complete", "0"]) as Output orelse panic()).text() == ":files\n");
      assert((cli.parse(["__complete", "x", "--v"]) as Output orelse panic()).text() == ":none\n");
      assert((cli.parse(["__complete"]) as Output orelse panic()).text() == ":none\n");
      let args = cli.parse(["a", "__complete"]) as Args orelse panic();
      assert(args.command.path == "frob");
      let git = minigit();
      assert((git.parse(["__complete", "1", "remote", "l"]) as Output orelse panic()).text() == "list\tList remotes.\n:none\n");
    }

`__complete` can't be a top command's subcommand, which would hide
it, though a deeper one may have the name. A spec with mistakes gets
no candidates.

    test("__complete is reserved") {
      let cli = new Command({ name: "frob" });
      cli.command({ name: "__complete" });
      let error = cli.parse(["x"]) as ArgError orelse panic();
      assert(error.message == "invalid command spec: command name '__complete' is reserved for completions");
      assert(shown(cli.complete([""])) == "(none)");
      let deeper = new Command({ name: "frob" });
      let sub = deeper.command({ name: "sub" });
      sub.command({ name: "__complete" });
      assert(deeper.problems.isEmpty);
    }

## Other styles

In `singleDash`, names keep the prefix typed, one dash or two.

    test("singleDash completions") {
      let cli = frob(Style.singleDash, null);
      assert(shown(cli.complete(["-ver"])) == "-verbose -version");
      assert(shown(cli.complete(["--ver"])) == "--verbose --version");
      assert(shown(cli.complete(["-q"])) == "-quiet -q");
      assert(shown(cli.complete(["-mode=f"])) == "-mode=fast");
      assert(shown(cli.complete(["-out=x"])) == ":files -out=");
      assert(shown(cli.complete(["-mode", ""])) == "fast slow");
      assert(shown(cli.complete(["-no"])) == "-no-color");
      assert(shown(cli.complete(["-h"])) == "-h -help");
    }

In `windows`, names start with `/` unless a dash is typed, match
ignoring case, and values attach with `:` (or `=`). A `/` word could
be a path too, so it gets the positional argument's files as well.

    test("windows completions") {
      let cli = frob(Style.windows, null);
      assert(shown(cli.complete(["/ver"])) == "/verbose /version :files");
      assert(shown(cli.complete(["/VER"])) == "/verbose /version :files");
      assert(shown(cli.complete(["-ver"])) == "-verbose -version");
      assert(shown(cli.complete(["/mode:"])) == "/mode:fast /mode:slow");
      assert(shown(cli.complete(["/mode=s"])) == "/mode=slow");
      assert(shown(cli.complete(["/out:C:\\x"])) == ":files /out:");
      assert(shown(cli.complete(["/mode", "f"])) == "fast");
      assert(shown(cli.complete(["/?"])) == "/? :files");
      assert(shown(cli.complete(["/completions:p"])) == "/completions:powershell");
      let noFiles = new Command({ name: "w", style: Style.windows });
      noFiles.flag({ name: "all" });
      assert(shown(noFiles.complete(["/"])) == "/all /? /help");
      assert(shown(noFiles.complete([""])) == "/all /? /help");
    }

With two styles, options are offered in both.

    test("two styles") {
      let both = frob(Style.gnu, Style.singleDash);
      assert(shown(both.complete(["-qu"])) == "-quiet");
      assert(shown(both.complete(["--qu"])) == "--quiet");
      assert(shown(both.complete(["-mode=f"])) == "-mode=fast");
      let win = frob(Style.windows, Style.gnu);
      assert(shown(win.complete(["--qu"])) == "--quiet");
      assert(shown(win.complete(["/qu"])) == "/quiet :files");
      assert(shown(win.complete(["-q"])) == "-quiet -q");
    }

## `--completions`

A built-in option, when the spec asks: its shell completes too, and it
prints the script, winning over errors other than asking for help.

    test("--completions") {
      let cli = frob(Style.gnu, null);
      assert(shown(cli.complete(["--completions", ""])) == "bash zsh fish powershell");
      assert(shown(cli.complete(["--completions=f"])) == "--completions=fish");
      let out = cli.parse(["--completions", "fish"]) as Output orelse panic();
      assert(out.kind == OutputKind.completionScript);
      assert(out.text() == cli.completionScript(Shell.fish));
      assert((cli.parse(["--bogus", "--completions=zsh"]) as Output orelse panic()).text() == cli.completionScript(Shell.zsh));
      assert((cli.parse(["--completions=zsh", "--help"]) as Output orelse panic()).isHelp);
      let error = cli.parse(["--completions", "cmd"]) as ArgError orelse panic();
      assert(error.message == "invalid value 'cmd' for --completions: expected one of bash, zsh, fish, powershell");
      let near = cli.parse(["--completions", "fihs"]) as ArgError orelse panic();
      assert(near.message == "invalid value 'fihs' for --completions: expected one of bash, zsh, fish, powershell; did you mean fish?");
      let missing = cli.parse(["--completions"]) as ArgError orelse panic();
      assert(missing.message == "option --completions needs a value");
      let win = frob(Style.windows, null);
      assert((win.parse(["/COMPLETIONS:bash"]) as Output orelse panic()).text() == win.completionScript(Shell.bash));
    }

It's off by default, only on the top command, and a program may take
the name for itself.

    test("--completions is opt-in") {
      let plain = new Command({ name: "frob" });
      assert(!plain.builtInCompletions);
      let error = plain.parse(["--completions", "bash"]) as ArgError orelse panic();
      assert(error.message == "unknown option --completions");
      let git = new Command({ name: "minigit", completions: true });
      let add = git.command({ name: "add" });
      assert(git.builtInCompletions);
      assert(!add.builtInCompletions);
      let own = new Command({ name: "own", completions: true });
      own.flag({ name: "completions" });
      assert(!own.builtInCompletions);
    }

Help lists it last, with the shells.

    test("--completions in help") {
      let cli = new Command({ name: "frob", completions: true });
      assert(cli.help() == """
        "Usage: frob [OPTIONS]
        "
        "Options:
        "  -h, --help                 Show this help and exit.
        "      --completions <SHELL>  Print a completion script for SHELL and exit.
        "                             [choices: bash, zsh, fish, powershell]
      );
    }
