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
