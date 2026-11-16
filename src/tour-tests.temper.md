# Tour

The example in the [README](../README.md), checked here so it can't
drift from what Argmas does.

    test("tour") {
      let cli = new Command({ name: "frob", about: "Frobnicate files.", version: "1.0.0" });
      let verbose = cli.count({ name: "verbose", short: "v", help: "Say more." });
      let level = cli.optionOr(ints, 3, { name: "level", short: "l", help: "How hard.", env: "FROB_LEVEL" });
      let mode = cli.option(choices(["fast", "slow"]), { name: "mode", help: "How to go about it." });
      let files = cli.positionals(strings, { name: "FILE", min: 1, help: "Files to frobnicate." });

      let args = cli.parse(["-vv", "--level=5", "a.txt", "b.txt"]) as Args orelse panic();
      let v: Int = args.get(verbose);
      let n: Int = args.get(level);
      let m: String? = args.get(mode);
      let f: List<String> = args.get(files);
      assert(v == 2);
      assert(n == 5);
      assert(m == null);
      assert(f.join(" ") { (s: String): String => s } == "a.txt b.txt");

      let fromEnv = cli.parse(["a.txt"], new MapEnvironment(new Map([new Pair("FROB_LEVEL", "9")]))) as Args orelse panic();
      assert(fromEnv.get(level) == 9);

      let error = cli.parse(["--levle", "5", "a.txt"]) as ArgError orelse panic();
      assert(error.message == "unknown option --levle; did you mean --level?");
      assert(error.exitStatus == 2);
      assert(error.text() == """
        "frob: unknown option --levle; did you mean --level?
        "Usage: frob [OPTIONS] FILE...
        "Try 'frob --help' for more information.
      );

      let help = cli.parse(["--help"]) as Output orelse panic();
      assert(help.text() == """
        "Frobnicate files.
        "
        "Usage: frob [OPTIONS] FILE...
        "
        "Arguments:
        "  FILE...              Files to frobnicate.
        "
        "Options:
        "  -v, --verbose        Say more. [repeatable]
        "  -l, --level <LEVEL>  How hard. [default: 3] [env: FROB_LEVEL]
        "      --mode <MODE>    How to go about it. [choices: fast, slow]
        "  -h, --help           Show this help and exit.
        "      --version        Show the version and exit.
      );
    }

The subcommands example.

    test("subcommands tour") {
      let git = new Command({ name: "minigit", about: "Track files." });
      let quiet = git.flag({ name: "quiet", short: "q", inherited: true });
      let add = git.subcommand({ name: "add", about: "Add files." });
      let force = add.flag({ name: "force", short: "f", help: "Add ignored files too." });
      let paths = add.positionals(strings, { name: "PATH", min: 1 });
      let rm = git.subcommand({ name: "rm", about: "Remove files.", aliases: ["remove"] });

      let args = git.parse(["add", "-qf", "a.txt"]) as Args orelse panic();
      let ran = when (args.command) {
        add -> commas(args.get(paths));
        rm -> "rm";
        else -> "?";
      };
      assert(ran == "a.txt");
      assert(args.get(force));
      assert(args.get(quiet));

      let help = git.parse(["help", "add"]) as Output orelse panic();
      assert(help.text() == add.help());
      assert((git.parse(["add", "--help"]) as Output orelse panic()).text() == add.help());
      let error = git.parse(["ad"]) as ArgError orelse panic();
      assert(error.message == "unknown command 'ad'; did you mean add?");
    }

The styles example.

    test("styles tour") {
      let cli = new Command({ name: "frob", style: Style.windows });
      let verbose = cli.flag({ name: "verbose", short: "v", help: "Say more." });
      let out = cli.option(strings, { name: "out", help: "Where to write." });
      let args = cli.parse(["/V", "/out:C:\\x.txt"]) as Args orelse panic();
      assert(args.get(verbose));
      assert(args.get(out) == "C:\\x.txt");
      assert(outcome(cli.parse(["/?"])) == "help");
      assert(cli.help() == """
        "Usage: frob [OPTIONS]
        "
        "Options:
        "  /v, /verbose    Say more.
        "      /out:<OUT>  Where to write.
        "  /?, /help       Show this help and exit.
      );
      let go = new Command({ name: "frob", style: Style.singleDash });
      let level = go.optionOr(ints, 3, { name: "level" });
      assert((go.parse(["-level=5"]) as Args orelse panic()).get(level) == 5);
      assert((go.parse(["-level", "5"]) as Args orelse panic()).get(level) == 5);
    }

The completions example.

    test("completions tour") {
      let cli = new Command({ name: "frob", completions: true });
      let verbose = cli.flag({ name: "verbose", short: "v", help: "Say more." });
      let mode = cli.option(choices(["fast", "slow"]), { name: "mode", help: "How to go about it." });
      let out = cli.option(paths, { name: "out", help: "Where to write." });
      assert(cli.complete(["--v"]).text() == "--verbose\tSay more.\n:none\n");
      assert(cli.complete(["--mode", ""]).text() == "fast\nslow\n:none\n");
      assert(cli.complete(["--out="]).text() == ":files --out=\n");
      let answer = cli.parse(["__complete", "0", "--v"]) as Output orelse panic();
      assert(answer.text() == cli.complete(["--v"]).text());
      let script = cli.parse(["--completions", "bash"]) as Output orelse panic();
      assert(script.text() == cli.completionScript(Shell.bash));
      assert(verbose.param.name == "verbose" && mode.param.name == "mode" && out.param.name == "out");
    }
