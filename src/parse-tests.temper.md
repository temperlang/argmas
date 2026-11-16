# Parsing tests

Tables of arguments in and results out, one line each. Every decision
on a corner case in the [design](../docs/design.md#behavior-the-same-in-every-language)
has a test here.

## The test command

`Frob` declares one of each kind of argument, and `run` shows a result
as text: each argument that was given, as `name=value` (lists joined
with commas), `help` or `version`, or an error's kind and message.

    class Frob {
      public cli: Command;
      public verbose: Counter;
      public color: Flag;
      public quiet: Flag;
      public level: Value<Int>;
      public output: MaybeValue<String>;
      public mode: MaybeValue<String>;
      public tags: Values<String>;
      public ratio: MaybeValue<Float64>;
      public files: Values<String>;

      public constructor() {
        let cli = new Command({ name: "frob", about: "Frobnicate files.", version: "1.2.0" });
        this.cli = cli;
        verbose = cli.count({ name: "verbose", short: "v", help: "Say more.", env: "FROB_VERBOSE" });
        color = cli.flag({ name: "color", help: "Color the output.", env: "FROB_COLOR", negatable: true });
        quiet = cli.flag({ name: "quiet", short: "q", help: "Say less." });
        level = cli.optionOr(ints, 3, { name: "level", short: "l", help: "How hard.", env: "FROB_LEVEL" });
        output = cli.option(strings, { name: "output", short: "o", help: "Where to write.", valueName: "FILE" });
        mode = cli.option(choices(["fast", "slow"]), { name: "mode", short: "m", help: "How." });
        tags = cli.repeated(strings, { name: "tag", short: "t", help: "A tag.", env: "FROB_TAG" });
        ratio = cli.option(floats, { name: "ratio", short: "r", help: "How much." });
        files = cli.positionals(strings, { name: "FILE", help: "Files to frobnicate." });
      }

      public run(argv: List<String>): String { show(cli.parse(argv)) }

      public runEnv(argv: List<String>, vars: List<String>): String {
        show(cli.parse(argv, envOf(vars)))
      }

      private show(result: ParseResult): String {
        when (result) {
          is Args -> do {
            let parts = new ListBuilder<String>();
            let args = result;
            if (wasGiven(args, verbose.param)) { parts.add("verbose=${args.get(verbose)}"); }
            if (wasGiven(args, color.param)) { parts.add("color=${args.get(color)}"); }
            if (wasGiven(args, quiet.param)) { parts.add("quiet=${args.get(quiet)}"); }
            if (wasGiven(args, level.param)) { parts.add("level=${args.get(level)}"); }
            if (wasGiven(args, output.param)) { parts.add("output=${args.get(output) ?? "null"}"); }
            if (wasGiven(args, mode.param)) { parts.add("mode=${args.get(mode) ?? "null"}"); }
            if (wasGiven(args, tags.param)) { parts.add("tags=${commas(args.get(tags))}"); }
            if (wasGiven(args, ratio.param)) { parts.add("ratio=${(args.get(ratio) ?? 0.0).toString()}"); }
            if (wasGiven(args, files.param)) { parts.add("files=${commas(args.get(files))}"); }
            if (parts.isEmpty) { "(nothing)" } else { parts.join(" ") { (s: String): String => s } }
          }
          is Output -> if (result.isHelp) { "help" } else { "version" };
          is ArgError -> "${result.kind}: ${result.message}";
          else -> "?";
        }
      }
    }

    let wasGiven(args: Args, p: Param): Boolean { args.source(p) != Source.absent }

    let commas(items: List<String>): String { items.join(",") { (s: String): String => s } }

`envOf(["A=1", "B=2"])` is an environment with those variables.

    let envOf(vars: List<String>): Environment {
      let map = new MapBuilder<String, String>();
      for (let v of vars) {
        let eq = v.indexOf("=");
        if (eq is StringIndex) {
          map.set(v.slice(String.begin, eq), v.slice(v.next(eq), v.end));
        }
      }
      new MapEnvironment(map.toMap())
    }

`show` for any command, with only the kind of result or the error.

    let outcome(result: ParseResult): String {
      when (result) {
        is Args -> "ok";
        is Output -> if (result.isHelp) { "help" } else { "version" };
        is ArgError -> "${result.kind}: ${result.message}";
        else -> "?";
      }
    }

## Nothing given

    test("nothing given") {
      let f = new Frob();
      assert(f.run([]) == "(nothing)");
      let args = f.cli.parse([]) as Args orelse panic();
      assert(args.get(f.verbose) == 0);
      assert(!args.get(f.color));
      assert(args.get(f.level) == 3);
      assert(args.get(f.output) == null);
      assert(args.get(f.tags).isEmpty);
      assert(args.get(f.files).isEmpty);
      assert(args.source(f.level.param) == Source.absent);
    }

## Long options

    test("long options") {
      let f = new Frob();
      assert(f.run(["--verbose"]) == "verbose=1");
      assert(f.run(["--level", "5"]) == "level=5");
      assert(f.run(["--level=5"]) == "level=5");
      assert(f.run(["--output", "a.txt"]) == "output=a.txt");
      assert(f.run(["--output=a=b"]) == "output=a=b");
      assert(f.run(["--mode", "slow", "--ratio", "0.5"]) == "mode=slow ratio=0.5");
    }

`--opt=` gives the empty string, which is a value; whether it's valid
is up to the type.

    test("empty values after =") {
      let f = new Frob();
      assert(f.run(["--output="]) == "output=");
      assert(f.run(["--level="]) == "invalidValue: invalid value '' for --level: expected an integer");
      assert(f.run(["--output", ""]) == "output=");
    }

No prefix matching: `--verb` isn't `--verbose`, though the error
suggests it.

    test("no prefix matching") {
      let f = new Frob();
      assert(f.run(["--verb"]) == "unknownOption: unknown option --verb; did you mean --verbose?");
      assert(f.run(["--lev", "3"]) == "unknownOption: unknown option --lev; did you mean --level?");
    }

## Short options

    test("short options") {
      let f = new Frob();
      assert(f.run(["-v"]) == "verbose=1");
      assert(f.run(["-l", "5"]) == "level=5");
      assert(f.run(["-l5"]) == "level=5");
      assert(f.run(["-oout.txt"]) == "output=out.txt");
      assert(f.run(["-o", "out.txt"]) == "output=out.txt");
    }

One `=` right after a short option is dropped, so `-o=file` is `file`;
a second one stays.

    test("= after a short option") {
      let f = new Frob();
      assert(f.run(["-o=file"]) == "output=file");
      assert(f.run(["-o==file"]) == "output==file");
      assert(f.run(["-l=7"]) == "level=7");
    }

    test("bundled short options") {
      let f = new Frob();
      assert(f.run(["-vq"]) == "verbose=1 quiet=true");
      assert(f.run(["-vvv"]) == "verbose=3");
      assert(f.run(["-vql9"]) == "verbose=1 quiet=true level=9");
      assert(f.run(["-vl", "9"]) == "verbose=1 level=9");
      // The option takes the rest, even letters that are options.
      assert(f.run(["-ovq"]) == "output=vq");
    }

## Counted and repeated

    test("counted flags") {
      let f = new Frob();
      assert(f.run(["-v", "-v", "--verbose"]) == "verbose=3");
      assert(f.run(["-vv", "-v"]) == "verbose=3");
    }

A plain flag given twice is still just true.

    test("plain flags given twice") {
      let f = new Frob();
      assert(f.run(["-q", "-q"]) == "quiet=true");
      assert(f.run(["-qq"]) == "quiet=true");
    }

    test("last value wins for options") {
      let f = new Frob();
      assert(f.run(["--level", "1", "-l", "2", "--level=3"]) == "level=3");
      assert(f.run(["-o", "a", "-o", "b"]) == "output=b");
    }

    test("repeated options keep every value") {
      let f = new Frob();
      assert(f.run(["-t", "a", "--tag", "b", "-tc", "--tag=d"]) == "tags=a,b,c,d");
      assert(f.run(["-t", "a", "-t", "a"]) == "tags=a,a");
    }

## Negatable flags

`--no-color` sets the flag to false; the last one given wins.

    test("negatable flags") {
      let f = new Frob();
      assert(f.run(["--color"]) == "color=true");
      assert(f.run(["--no-color"]) == "color=false");
      assert(f.run(["--color", "--no-color"]) == "color=false");
      assert(f.run(["--no-color", "--color"]) == "color=true");
    }

Only flags declared negatable take `--no-`.

    test("--no- for flags not negatable") {
      let f = new Frob();
      assert(f.run(["--no-quiet"]) == "unknownOption: unknown option --no-quiet; --quiet can't be negated");
      assert(f.run(["--no-level"]) == "unknownOption: unknown option --no-level; --level can't be negated");
      assert(f.run(["--no-such"]) == "unknownOption: unknown option --no-such");
    }

A negatable counted flag goes back to zero.

    test("negatable counted flags") {
      let cli = new Command({ name: "c" });
      let v = cli.count({ name: "verbose", short: "v", negatable: true });
      let args = cli.parse(["-vv", "--no-verbose", "-v"]) as Args orelse panic();
      assert(args.get(v) == 1);
    }

## Flags take no value

    test("flags take no value") {
      let f = new Frob();
      assert(f.run(["--quiet=yes"]) == "unexpectedValue: option --quiet takes no value");
      assert(f.run(["--no-color=1"]) == "unexpectedValue: option --no-color takes no value");
      assert(f.run(["--verbose="]) == "unexpectedValue: option --verbose takes no value");
    }

## Positional arguments

    test("positionals") {
      let f = new Frob();
      assert(f.run(["a", "b"]) == "files=a,b");
      assert(f.run(["a", "-v", "b"]) == "verbose=1 files=a,b");
    }

A lone `-` is positional, conventionally standard input, and so is any
argument after `--`, including `--` itself.

    test("- and --") {
      let f = new Frob();
      assert(f.run(["-"]) == "files=-");
      assert(f.run(["--", "-v", "--level", "--"]) == "files=-v,--level,--");
      assert(f.run(["-v", "--", "-v"]) == "verbose=1 files=-v");
      assert(f.run(["--"]) == "(nothing)");
      assert(f.run(["-o", "-"]) == "output=-");
    }

Options may come after positionals, until `--`.

    test("options after positionals") {
      let f = new Frob();
      assert(f.run(["a", "--level", "4", "b", "-q"]) == "quiet=true level=4 files=a,b");
    }

## Negative numbers

An argument that looks like a negative number is a value or a
positional, when the command has no short option that's a digit.

    test("negative numbers") {
      let f = new Frob();
      assert(f.run(["--level", "-5"]) == "level=-5");
      assert(f.run(["-l", "-5"]) == "level=-5");
      assert(f.run(["--ratio", "-1.5e1"]) == "ratio=-15.0");
      assert(f.run(["-r", "-.5"]) == "ratio=-0.5");
      assert(f.run(["-5"]) == "files=-5");
      assert(f.run(["--", "-5"]) == "files=-5");
    }

With a digit short option, they're options.

    test("negative numbers with a digit option") {
      let cli = new Command({ name: "n" });
      let one = cli.flag({ name: "one", short: "1" });
      let n = cli.optionOr(ints, 0, { name: "n" });
      let rest = cli.positionals(strings, { name: "ARG" });
      assert(outcome(cli.parse(["-1"])) == "ok");
      assert(outcome(cli.parse(["-5"])) == "unknownOption: unknown option -5");
      assert(outcome(cli.parse(["--n", "-5"])) == "missingValue: option --n needs a value; to give one starting with '-', write --n=-5");
      let args = cli.parse(["--n=-5", "--", "-5"]) as Args orelse panic();
      assert(args.get(n) == -5);
      assert(args.get(one) == false);
      assert(args.get(rest).length == 1);
    }

## Values that look like options

A separate value can't start with `-` (but for `-` itself and negative
numbers): that's more likely a forgotten value than a value. The
attached forms take anything.

    test("values that look like options") {
      let f = new Frob();
      assert(f.run(["--output", "-v"]) == "missingValue: option --output needs a value; to give one starting with '-', write --output=-v");
      assert(f.run(["-o", "--quiet"]) == "missingValue: option --output needs a value; to give one starting with '-', write --output=--quiet");
      assert(f.run(["--output=-v"]) == "output=-v");
      assert(f.run(["-o-v"]) == "output=-v");
      assert(f.run(["--output", "--"]) == "missingValue: option --output needs a value; to give one starting with '-', write --output=--");
    }

    test("missing values at the end") {
      let f = new Frob();
      assert(f.run(["--level"]) == "missingValue: option --level needs a value");
      assert(f.run(["-l"]) == "missingValue: option --level needs a value");
      assert(f.run(["-vl"]) == "missingValue: option --level needs a value");
    }

## Invalid values

    test("invalid values") {
      let f = new Frob();
      assert(f.run(["--level", "abc"]) == "invalidValue: invalid value 'abc' for --level: expected an integer");
      assert(f.run(["--ratio", "x"]) == "invalidValue: invalid value 'x' for --ratio: expected a number");
      assert(f.run(["--mode", "medium"]) == "invalidValue: invalid value 'medium' for --mode: expected one of fast, slow");
      assert(f.run(["--mode", "slo"]) == "invalidValue: invalid value 'slo' for --mode: expected one of fast, slow; did you mean slow?");
      assert(f.run(["--mode", "Fast"]) == "invalidValue: invalid value 'Fast' for --mode: expected one of fast, slow; did you mean fast?");
    }

    test("invalid positional values") {
      let cli = new Command({ name: "add" });
      cli.positionals(ints, { name: "N", min: 1 });
      assert(outcome(cli.parse(["1", "two"])) == "invalidValue: invalid value 'two' for N: expected an integer");
    }

## Unknown options and suggestions

    test("unknown options") {
      let f = new Frob();
      assert(f.run(["--verbos"]) == "unknownOption: unknown option --verbos; did you mean --verbose?");
      assert(f.run(["--colour"]) == "unknownOption: unknown option --colour; did you mean --color?");
      assert(f.run(["--frobnicate"]) == "unknownOption: unknown option --frobnicate");
      assert(f.run(["-x"]) == "unknownOption: unknown option -x");
      assert(f.run(["-vx"]) == "unknownOption: unknown option -x in -vx");
      assert(f.run(["-vqx"]) == "unknownOption: unknown option -x in -vqx");
      assert(f.run(["--hlep"]) == "unknownOption: unknown option --hlep; did you mean --help?");
      assert(f.run(["--vrsion"]) == "unknownOption: unknown option --vrsion; did you mean --version?");
    }

A single dash before a long name suggests two, and `--v` suggests `-v`.

    test("dash mix-ups") {
      let f = new Frob();
      assert(f.run(["-verbose"]) == "unknownOption: unknown option -e in -verbose; did you mean --verbose?");
      assert(f.run(["--v"]) == "unknownOption: unknown option --v; did you mean -v?");
      assert(f.run(["--q"]) == "unknownOption: unknown option --q; did you mean --quiet?");
    }

Suggestions are by edit distance, up to a third of the typed name's
length (at least 1), or a typed prefix of exactly one name.

    test("edit distance") {
      assert(editDistance("", "") == 0);
      assert(editDistance("abc", "") == 3);
      assert(editDistance("kitten", "sitting") == 3);
      assert(editDistance("verbos", "verbose") == 1);
      assert(editDistance("é", "e") == 1);
      assert(editDistance("hlep", "help") == 1);
      assert(editDistance("ab", "ba") == 1);
      assert(editDistance("ca", "abc") == 3);
      assert(nearest("lvl", ["level"]) == null);
      assert(nearest("levle", ["level"]) == "level");
      assert(nearest("ver", ["verbose", "version"]) == null);
      assert(nearest("verb", ["verbose", "version"]) == "verbose");
      assert(nearest("x", ["y", "z"]) == "y");
    }

## Help and version

    test("help and version") {
      let f = new Frob();
      assert(f.run(["--help"]) == "help");
      assert(f.run(["-h"]) == "help");
      assert(f.run(["-vh"]) == "help");
      assert(f.run(["--version"]) == "version");
      let out = f.cli.parse(["--version"]) as Output orelse panic();
      assert(out.text() == "frob 1.2.0\n");
      assert(out.exitStatus == 0);
    }

Help wins over errors anywhere before `--`, and over `--version`;
after `--` it's positional.

    test("help wins") {
      let f = new Frob();
      assert(f.run(["--bogus", "--help"]) == "help");
      assert(f.run(["--level", "abc", "-h"]) == "help");
      assert(f.run(["--version", "--help"]) == "help");
      assert(f.run(["--version", "--bogus"]) == "version");
      assert(f.run(["--", "--help"]) == "files=--help");
      assert(f.run(["--output=--help"]) == "output=--help");
      assert(f.run(["--help=x"]) == "help");
    }

Without a version, `--version` is unknown; a program may declare its
own `help`, `h`, or `version`, which then aren't built in.

    test("built-ins give way") {
      let cli = new Command({ name: "c" });
      let host = cli.option(strings, { name: "host", short: "h" });
      assert(outcome(cli.parse(["--version"])) == "unknownOption: unknown option --version");
      assert(outcome(cli.parse(["--help"])) == "help");
      let args = cli.parse(["-h", "example.org"]) as Args orelse panic();
      assert(args.get(host) == "example.org");
    }

## Required options

    test("required options") {
      let cli = new Command({ name: "c" });
      let name = cli.required(strings, { name: "name", env: "C_NAME" });
      assert(outcome(cli.parse([])) == "missingRequired: missing required option --name (or C_NAME)");
      assert(outcome(cli.parse(["--help"])) == "help");
      let args = cli.parse(["--name", "x"]) as Args orelse panic();
      assert(args.get(name) == "x");
      let fromEnv = cli.parse([], envOf(["C_NAME=y"])) as Args orelse panic();
      assert(fromEnv.get(name) == "y");
    }

## Positional counts

    test("positional counts") {
      let cli = new Command({ name: "cp" });
      let src = cli.positionals(strings, { name: "SRC", min: 1 });
      let dest = cli.positional(strings, { name: "DEST" });
      assert(outcome(cli.parse([])) == "tooFewPositionals: missing argument SRC");
      assert(outcome(cli.parse(["a"])) == "tooFewPositionals: missing argument DEST");
      let args = cli.parse(["a", "b", "c"]) as Args orelse panic();
      assert(commas(args.get(src)) == "a,b");
      assert(args.get(dest) == "c");
    }

    test("positional limits") {
      let cli = new Command({ name: "pair" });
      let two = cli.positionals(strings, { name: "X", min: 2, max: 2 });
      let maybe = cli.positionals(strings, { name: "Y", max: 1 });
      assert(outcome(cli.parse(["a"])) == "tooFewPositionals: missing argument X: needs at least 2, got 1");
      assert(outcome(cli.parse(["a", "b", "c", "d"])) == "tooManyPositionals: unexpected argument 'd'");
      let args = cli.parse(["a", "b", "c"]) as Args orelse panic();
      assert(commas(args.get(two)) == "a,b");
      assert(commas(args.get(maybe)) == "c");
    }

    test("no positionals declared") {
      let cli = new Command({ name: "c" });
      cli.flag({ name: "x" });
      assert(outcome(cli.parse(["stray"])) == "tooManyPositionals: unexpected argument 'stray'");
    }

## The environment

An argument wins over the environment, which wins over a default. An
empty variable counts as unset.

    test("environment fallbacks") {
      let f = new Frob();
      assert(f.runEnv([], ["FROB_LEVEL=7"]) == "level=7");
      assert(f.runEnv(["--level", "1"], ["FROB_LEVEL=7"]) == "level=1");
      assert(f.runEnv([], ["FROB_LEVEL="]) == "(nothing)");
      assert(f.runEnv([], ["OTHER=7"]) == "(nothing)");
      let args = f.cli.parse([], envOf(["FROB_LEVEL=7"])) as Args orelse panic();
      assert(args.source(f.level.param) == Source.environment);
    }

    test("flags from the environment") {
      let f = new Frob();
      assert(f.runEnv([], ["FROB_COLOR=1"]) == "color=true");
      assert(f.runEnv([], ["FROB_COLOR=Yes"]) == "color=true");
      assert(f.runEnv([], ["FROB_COLOR=off"]) == "color=false");
      assert(f.runEnv(["--no-color"], ["FROB_COLOR=true"]) == "color=false");
      assert(f.runEnv([], ["FROB_COLOR=maybe"]) == "invalidValue: invalid value 'maybe' for --color from FROB_COLOR: expected true or false");
      assert(f.runEnv([], ["FROB_VERBOSE=2"]) == "verbose=2");
      assert(f.runEnv(["-v"], ["FROB_VERBOSE=2"]) == "verbose=1");
      assert(f.runEnv([], ["FROB_VERBOSE=-1"]) == "invalidValue: invalid value '-1' for --verbose from FROB_VERBOSE: expected a count");
    }

A repeated option's variable is one value, not split.

    test("repeated options from the environment") {
      let f = new Frob();
      assert(f.runEnv([], ["FROB_TAG=a,b c"]) == "tags=a,b c");
      assert(f.runEnv(["-t", "x"], ["FROB_TAG=a"]) == "tags=x");
    }

    test("invalid values from the environment") {
      let f = new Frob();
      assert(f.runEnv([], ["FROB_LEVEL=high"]) == "invalidValue: invalid value 'high' for --level from FROB_LEVEL: expected an integer");
      // Not read when the argument is given.
      assert(f.runEnv(["-l", "2"], ["FROB_LEVEL=high"]) == "level=2");
    }

## Which error first

Argument errors come in the order of the arguments, before positional
counts, the environment, and required options.

    test("first error wins") {
      let cli = new Command({ name: "c" });
      cli.required(strings, { name: "name" });
      cli.optionOr(ints, 0, { name: "n", env: "C_N" });
      cli.positional(strings, { name: "X" });
      assert(outcome(cli.parse(["--bad", "--n", "x"])) == "unknownOption: unknown option --bad");
      assert(outcome(cli.parse(["--n", "x", "--bad"])) == "invalidValue: invalid value 'x' for --n: expected an integer");
      assert(outcome(cli.parse([], envOf(["C_N=x"]))) == "tooFewPositionals: missing argument X");
      assert(outcome(cli.parse(["a"], envOf(["C_N=x"]))) == "invalidValue: invalid value 'x' for --n from C_N: expected an integer");
      assert(outcome(cli.parse(["a"])) == "missingRequired: missing required option --name");
    }

## Error reports

    test("error reports") {
      let f = new Frob();
      let error = f.cli.parse(["--verbos"]) as ArgError orelse panic();
      assert(error.kind == ErrorKind.unknownOption);
      assert(error.exitStatus == 2);
      assert(error.toString() == "unknown option --verbos; did you mean --verbose?");
      assert(error.text() == """
        "frob: unknown option --verbos; did you mean --verbose?
        "Usage: frob [OPTIONS] [FILE]...
        "Try 'frob --help' for more information.
      );
    }

## Mistakes in the spec

A spec's mistakes are reported by `parse`, before any argument is read,
rather than panicking where they're declared.

    test("mistakes in the spec") {
      let a = new Command({ name: "a" });
      a.flag({ name: "x" });
      a.option(strings, { name: "x" });
      assert(outcome(a.parse([])) == "invalidSpec: invalid command spec: --x declared twice");
      let b = new Command({ name: "b" });
      b.flag({ name: "x", short: "v" });
      b.flag({ name: "y", short: "v" });
      assert(outcome(b.parse(["--help"])) == "invalidSpec: invalid command spec: -v declared twice");
      let c = new Command({ name: "c" });
      c.flag({ name: "x", short: "vv" });
      assert(outcome(c.parse([])) == "invalidSpec: invalid command spec: invalid short name 'vv' for x");
      let d = new Command({ name: "d" });
      d.flag({ name: "--x" });
      assert(outcome(d.parse([])) == "invalidSpec: invalid command spec: invalid name '--x'");
      let e = new Command({ name: "e" });
      e.positionals(strings, { name: "X", min: 3, max: 2 });
      assert(outcome(e.parse([])) == "invalidSpec: invalid command spec: positional X allows no count of arguments");
      // A positional may share an option's name.
      let g = new Command({ name: "g" });
      g.option(strings, { name: "file" });
      g.positional(strings, { name: "file" });
      assert(outcome(g.parse(["--file", "a", "b"])) == "ok");
    }

## Text

Arguments are whole Unicode strings, compared by code point.

    test("non-ASCII arguments") {
      let cli = new Command({ name: "u" });
      let name = cli.option(strings, { name: "név", short: "é" });
      let args = cli.parse(["--név=Zoë"]) as Args orelse panic();
      assert(args.get(name) == "Zoë");
      let short = cli.parse(["-éZoë"]) as Args orelse panic();
      assert(short.get(name) == "Zoë");
      assert(outcome(cli.parse(["--nev"])) == "unknownOption: unknown option --nev; did you mean --név?");
    }
