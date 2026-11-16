# Style tests

Tables of arguments in and results out for each
[argument style](style.temper.md), and goldens of help in each. Every
decision on styles in the
[design](../docs/design.md#argument-styles) has a test here.

## The test command

`Styled` declares the same arguments in whichever styles it's given,
and `run` shows a result as the [parsing tests](parse-tests.temper.md)
do.

    class Styled {
      public cli: Command;
      public verbose: Arg<Int>;
      public quiet: Arg<Boolean>;
      public color: Arg<Boolean>;
      public level: Arg<Int>;
      public output: MaybeArg<String>;
      public files: Arg<List<String>>;

      public constructor(style: Style, also: Style?) {
        let cli = new Command({ name: "frob", about: "Frobnicate files.", version: "1.2.0", style, alsoStyle: also });
        this.cli = cli;
        verbose = cli.count({ name: "verbose", short: "v", help: "Say more." });
        quiet = cli.flag({ name: "quiet", short: "q", help: "Say less." });
        color = cli.flag({ name: "color", help: "Color the output.", negatable: true });
        level = cli.optionOr(ints, 3, { name: "level", short: "l", help: "How hard." });
        output = cli.option(strings, { name: "output", short: "o", help: "Where to write.", valueName: "FILE" });
        files = cli.positionals(strings, { name: "FILE", help: "Files to frobnicate." });
      }

      public run(argv: List<String>): String {
        let result = cli.parse(argv);
        when (result) {
          is Args -> do {
            let parts = new ListBuilder<String>();
            let args = result;
            if (wasGiven(args, verbose.param)) { parts.add("verbose=${args.get(verbose)}"); }
            if (wasGiven(args, quiet.param)) { parts.add("quiet=${args.get(quiet)}"); }
            if (wasGiven(args, color.param)) { parts.add("color=${args.get(color)}"); }
            if (wasGiven(args, level.param)) { parts.add("level=${args.get(level)}"); }
            if (wasGiven(args, output.param)) { parts.add("output=${args.get(output) ?? "null"}"); }
            if (wasGiven(args, files.param)) { parts.add("files=${commas(args.get(files))}"); }
            if (parts.isEmpty) { "(nothing)" } else { parts.join(" ") { (s: String): String => s } }
          }
          is Output -> if (result.isHelp) { "help" } else { "version" };
          is ArgError -> "${result.kind}: ${result.message}";
          else -> "?";
        }
      }
    }

## `gnu`

The default, as the parsing tests cover; naming it changes nothing.

    test("gnu by default") {
      let named = new Styled(Style.gnu, null);
      assert(named.run(["-vq", "--level=5", "-ofile"]) == "verbose=1 quiet=true level=5 output=file");
      assert(named.run(["-verbose"]) == "unknownOption: unknown option -e in -verbose; did you mean --verbose?");
      assert(named.run(["/v"]) == "files=/v");
      assert(new Command({ name: "x" }).style == Style.gnu);
      assert(new Styled(Style.gnu, null).cli.help() == new Styled(Style.gnu, Style.gnu).cli.help());
    }

## `singleDash`

One dash and a name, long or short, with a value after `=` or in the
next argument; `--` before a name works the same.

    test("singleDash options") {
      let s = new Styled(Style.singleDash, null);
      assert(s.run(["-verbose"]) == "verbose=1");
      assert(s.run(["-v", "-verbose", "--v"]) == "verbose=3");
      assert(s.run(["--verbose"]) == "verbose=1");
      assert(s.run(["-level=5"]) == "level=5");
      assert(s.run(["-level", "5"]) == "level=5");
      assert(s.run(["--level", "5"]) == "level=5");
      assert(s.run(["-l=5"]) == "level=5");
      assert(s.run(["-l", "5"]) == "level=5");
      assert(s.run(["-output=a=b"]) == "output=a=b");
      assert(s.run(["-output="]) == "output=");
      assert(s.run(["a", "-quiet", "b"]) == "quiet=true files=a,b");
    }

No bundles: `-vq` is one name, and `-l5` isn't `-l 5`.

    test("singleDash has no bundles") {
      let s = new Styled(Style.singleDash, null);
      assert(s.run(["-vq"]) == "unknownOption: unknown option -vq");
      assert(s.run(["-l5"]) == "unknownOption: unknown option -l5");
      assert(s.run(["-verbos"]) == "unknownOption: unknown option -verbos; did you mean -verbose?");
      assert(s.run(["--verbos"]) == "unknownOption: unknown option --verbos; did you mean --verbose?");
    }

    test("singleDash flags, negation, and values") {
      let s = new Styled(Style.singleDash, null);
      assert(s.run(["-color", "-no-color"]) == "color=false");
      assert(s.run(["--no-color"]) == "color=false");
      assert(s.run(["-no-quiet"]) == "unknownOption: unknown option -no-quiet; -quiet can't be negated");
      assert(s.run(["-quiet=yes"]) == "unexpectedValue: option -quiet takes no value");
      assert(s.run(["-level", "-x"]) == "missingValue: option -level needs a value; to give one starting with '-', write -level=-x");
      assert(s.run(["-level"]) == "missingValue: option -level needs a value");
      assert(s.run(["-level", "-5"]) == "level=-5");
      assert(s.run(["-level=-x"]) == "invalidValue: invalid value '-x' for -level: expected an integer");
    }

Numbers are values unless they name an option; `-` and `--` are as in
`gnu`.

    test("singleDash numbers, -, and --") {
      let s = new Styled(Style.singleDash, null);
      assert(s.run(["-5", "-1.5"]) == "files=-5,-1.5");
      assert(s.run(["-"]) == "files=-");
      assert(s.run(["--", "-v"]) == "files=-v");
      let digits = new Command({ name: "d", style: Style.singleDash });
      let two = digits.flag({ name: "2" });
      digits.positionals(strings, { name: "N" });
      let args = digits.parse(["-2", "-3"]) as Args orelse panic();
      assert(args.get(two));
    }

    test("singleDash help and version") {
      let s = new Styled(Style.singleDash, null);
      assert(s.run(["-help"]) == "help");
      assert(s.run(["--help"]) == "help");
      assert(s.run(["-h"]) == "help");
      assert(s.run(["-version"]) == "version");
      assert(s.run(["-hel"]) == "unknownOption: unknown option -hel; did you mean -help?");
    }

## `windows`

`/name`, with a value after `:` or `=`, or in the next argument; `-`
and `--` before a name work the same, and names ignore case.

    test("windows options") {
      let w = new Styled(Style.windows, null);
      assert(w.run(["/v"]) == "verbose=1");
      assert(w.run(["/verbose", "/V", "/VERBOSE", "/Verbose"]) == "verbose=4");
      assert(w.run(["-verbose", "--verbose", "-v", "--v"]) == "verbose=4");
      assert(w.run(["/level:5"]) == "level=5");
      assert(w.run(["/level=5"]) == "level=5");
      assert(w.run(["/level", "5"]) == "level=5");
      assert(w.run(["/L:5"]) == "level=5");
      assert(w.run(["-level:5"]) == "level=5");
      assert(w.run(["--level=5"]) == "level=5");
      // The first `:` or `=` ends the name.
      assert(w.run(["/output:C:\\out\\x.txt"]) == "output=C:\\out\\x.txt");
      assert(w.run(["/output=a:b"]) == "output=a:b");
      assert(w.run(["/output:"]) == "output=");
      // Values keep their case.
      assert(w.run(["/OUTPUT:A.TXT"]) == "output=A.TXT");
    }

    test("windows flags, negation, and values") {
      let w = new Styled(Style.windows, null);
      assert(w.run(["/color", "/no-color"]) == "color=false");
      assert(w.run(["/NO-COLOR"]) == "color=false");
      assert(w.run(["/no-quiet"]) == "unknownOption: unknown option /no-quiet; /quiet can't be negated");
      assert(w.run(["/quiet:yes"]) == "unexpectedValue: option /quiet takes no value");
      assert(w.run(["/vq"]) == "files=/vq");
      assert(w.run(["-vq"]) == "unknownOption: unknown option -vq");
      assert(w.run(["/level"]) == "missingValue: option /level needs a value");
      assert(w.run(["/level", "-x"]) == "missingValue: option /level needs a value; to give one starting with '-', write /level:-x");
      assert(w.run(["/level", "-5"]) == "level=-5");
    }

`/word` is an option only when `word` names one; otherwise it's a
positional argument, such as a path, or, in a command without
positional arguments, an unknown option. After an option, a `/word`
that names no option is its value.

    test("windows paths and options") {
      let w = new Styled(Style.windows, null);
      assert(w.run(["/tmp/x", "/usr"]) == "files=/tmp/x,/usr");
      assert(w.run(["/verbos"]) == "files=/verbos");
      assert(w.run(["/"]) == "files=/");
      assert(w.run(["/output", "/tmp/x"]) == "output=/tmp/x");
      assert(w.run(["/output", "/v"]) == "missingValue: option /output needs a value; to give one starting with '/', write /output:/v");
      assert(w.run(["--", "/v"]) == "files=/v");
      let bare = new Command({ name: "bare", style: Style.windows });
      bare.flag({ name: "verbose", short: "v" });
      assert(outcome(bare.parse(["/verbos"])) == "unknownOption: unknown option /verbos; did you mean /verbose?");
      assert(outcome(bare.parse(["/x"])) == "unknownOption: unknown option /x");
      let error = bare.parse(["/x"]) as ArgError orelse panic();
      assert(error.text() == """
        "bare: unknown option /x
        "Usage: bare [OPTIONS]
        "Try 'bare /?' for more information.
      );
    }

    test("windows help and version") {
      let w = new Styled(Style.windows, null);
      assert(w.run(["/?"]) == "help");
      assert(w.run(["-?"]) == "help");
      assert(w.run(["/h"]) == "help");
      assert(w.run(["/HELP"]) == "help");
      assert(w.run(["--help"]) == "help");
      assert(w.run(["/version"]) == "version");
      assert(w.run(["/Version"]) == "version");
      assert(w.run(["/bogus", "/?"]) == "help");
      // A program that declares `?` itself keeps `/help` built in.
      let own = new Command({ name: "own", style: Style.windows });
      own.flag({ name: "ask", short: "?" });
      assert(outcome(own.parse(["/?"])) == "ok");
      assert(outcome(own.parse(["/help"])) == "help");
    }

## Two styles

With two styles, each argument is read in the first that knows its
name in full, then as a `gnu` bundle, and help shows the first.

    test("gnu and singleDash together") {
      let both = new Styled(Style.gnu, Style.singleDash);
      assert(both.run(["-verbose"]) == "verbose=1");
      assert(both.run(["-vq"]) == "verbose=1 quiet=true");
      assert(both.run(["-level=5"]) == "level=5");
      assert(both.run(["-level", "5"]) == "level=5");
      assert(both.run(["-l5"]) == "level=5");
      assert(both.run(["--level=5"]) == "level=5");
      assert(both.run(["-no-color"]) == "color=false");
      assert(both.run(["-help"]) == "help");
      // Neither knows it, so `gnu` reports it.
      assert(both.run(["-verbos"]) == "unknownOption: unknown option -e in -verbos; did you mean --verbose?");
      assert(both.cli.help() == new Styled(Style.gnu, null).cli.help());
    }

    test("windows and gnu together") {
      let both = new Styled(Style.windows, Style.gnu);
      assert(both.run(["/v", "-vq", "--level", "4"]) == "verbose=2 quiet=true level=4");
      assert(both.run(["-l4"]) == "level=4");
      assert(both.run(["/tmp/x"]) == "files=/tmp/x");
      assert(both.cli.usage() == "Usage: frob [OPTIONS] [FILE]...\n");
      let gnuFirst = new Styled(Style.gnu, Style.windows);
      assert(gnuFirst.run(["/level:4", "-vv"]) == "verbose=2 level=4");
      assert(gnuFirst.run(["/?"]) == "help");
    }

## Subcommands

Subcommands take their top command's styles, and the hint for a
parent's option given too late uses the form typed.

    test("subcommands take the top command's style") {
      let cli = new Command({ name: "tool", style: Style.windows });
      let dir = cli.option(strings, { name: "dir" });
      let quiet = cli.flag({ name: "quiet", short: "q", inherited: true });
      let add = cli.subcommand({ name: "add", about: "Add files." });
      let force = add.flag({ name: "force", short: "f", help: "Add ignored files too." });
      add.positionals(strings, { name: "PATH" });
      let args = cli.parse(["/dir:src", "add", "/F", "/q", "/tmp/a"]) as Args orelse panic();
      assert(same(args.command, add));
      assert(args.get(force));
      assert(args.get(quiet));
      assert(args.get(dir) == "src");
      assert(outcome(cli.parse(["add", "/dir:src"])) == "unknownOption: unknown option /dir; /dir belongs to tool, so give it before add");
      assert(outcome(cli.parse(["add", "-dir", "src"])) == "unknownOption: unknown option -dir; -dir belongs to tool, so give it before add");
      assert(outcome(cli.parse(["add", "/?"])) == "help");
      assert(outcome(cli.parse(["help", "add"])) == "help");
      assert(outcome(cli.parse(["help", "/?", "add"])) == "help");
      assert(outcome(cli.parse(["help", "add", "/?"])) == "help");
      assert(add.style == Style.windows);
      assert(add.help() == """
        "Add files.
        "
        "Usage: tool add [OPTIONS] [PATH]...
        "
        "Arguments:
        "  PATH...
        "
        "Options:
        "  /f, /force  Add ignored files too.
        "  /q, /quiet
        "  /?, /help   Show this help and exit.
      );
    }

## Mistakes in the spec

In `singleDash` and `windows`, long and short names share one
namespace, and in `windows`, names differing only in case clash.

    test("names that clash in a style") {
      let a = new Command({ name: "a", style: Style.singleDash });
      a.flag({ name: "v" });
      a.flag({ name: "verbose", short: "v" });
      assert(outcome(a.parse([])) == "invalidSpec: invalid command spec: -v declared twice");
      let fine = new Command({ name: "fine" });
      fine.flag({ name: "v" });
      fine.flag({ name: "verbose", short: "v" });
      assert(outcome(fine.parse([])) == "ok");
      let b = new Command({ name: "b", style: Style.windows });
      b.flag({ name: "verbose" });
      b.flag({ name: "Verbose" });
      assert(outcome(b.parse([])) == "invalidSpec: invalid command spec: /verbose declared twice");
      let c = new Command({ name: "c", style: Style.windows });
      c.flag({ name: "x", short: "v" });
      c.flag({ name: "y", short: "V" });
      assert(outcome(c.parse([])) == "invalidSpec: invalid command spec: /v declared twice");
      let d = new Command({ name: "d", alsoStyle: Style.windows });
      d.flag({ name: "x", short: "v" });
      d.flag({ name: "y", short: "V" });
      assert(outcome(d.parse([])) == "invalidSpec: invalid command spec: /v declared twice");
      // Inherited names clash in subcommands too.
      let e = new Command({ name: "e", style: Style.windows });
      e.flag({ name: "verbose", inherited: true });
      e.subcommand({ name: "s" }).flag({ name: "x", short: "V" });
      e.subcommand({ name: "t" }).flag({ name: "VERBOSE" });
      assert(outcome(e.parse([])) == "invalidSpec: invalid command spec: /VERBOSE declared twice in e t");
    }

With `gnu` and another style, a long name that is also a `gnu` bundle
of known short options is a mistake: flags, or flags and then an
option with its value next. A short option with letters after it is
the long name, as decided, so `-level` with `-l` is fine.

    test("long names that read as bundles") {
      let a = new Command({ name: "a", alsoStyle: Style.singleDash });
      a.flag({ name: "verbose", short: "v" });
      a.flag({ name: "quiet", short: "q" });
      a.flag({ name: "vq" });
      assert(outcome(a.parse([])) == "invalidSpec: invalid command spec: long name vq could also be read as -v -q");
      let b = new Command({ name: "b", style: Style.windows, alsoStyle: Style.gnu });
      b.flag({ name: "verbose", short: "v" });
      b.option(strings, { name: "out", short: "o" });
      b.option(strings, { name: "vo" });
      assert(outcome(b.parse([])) == "invalidSpec: invalid command spec: long name vo could also be read as -v -o");
      let c = new Command({ name: "c", alsoStyle: Style.singleDash });
      c.option(strings, { name: "level", short: "l" });
      c.flag({ name: "lx" });
      assert(outcome(c.parse([])) == "ok");
      // One style can't be read two ways.
      let d = new Command({ name: "d" });
      d.flag({ name: "verbose", short: "v" });
      d.flag({ name: "quiet", short: "q" });
      d.flag({ name: "vq" });
      assert(outcome(d.parse([])) == "ok");
      // Built-in names and -h count too.
      let e = new Command({ name: "e", alsoStyle: Style.singleDash });
      e.flag({ name: "e", short: "e" });
      e.flag({ name: "l", short: "l" });
      e.flag({ name: "p", short: "p" });
      assert(outcome(e.parse([])) == "invalidSpec: invalid command spec: long name help could also be read as -h -e -l -p");
      // An inherited long name meets a subcommand's short names there.
      let f = new Command({ name: "f", alsoStyle: Style.singleDash });
      f.flag({ name: "vq", inherited: true });
      let s = f.subcommand({ name: "s" });
      s.flag({ name: "verbose", short: "v" });
      s.flag({ name: "quiet", short: "q" });
      assert(outcome(f.parse([])) == "invalidSpec: invalid command spec: long name vq could also be read as -v -q in f s");
    }

## Help text

Help and usage lines write options in the first style.

    test("help in singleDash") {
      assert(new Styled(Style.singleDash, null).cli.help() == """
        "Frobnicate files.
        "
        "Usage: frob [OPTIONS] [FILE]...
        "
        "Arguments:
        "  FILE...             Files to frobnicate.
        "
        "Options:
        "  -v, -verbose        Say more. [repeatable]
        "  -q, -quiet          Say less.
        "      -[no-]color     Color the output.
        "  -l, -level <LEVEL>  How hard. [default: 3]
        "  -o, -output <FILE>  Where to write.
        "  -h, -help           Show this help and exit.
        "      -version        Show the version and exit.
      );
    }

    test("help in windows") {
      assert(new Styled(Style.windows, null).cli.help() == """
        "Frobnicate files.
        "
        "Usage: frob [OPTIONS] [FILE]...
        "
        "Arguments:
        "  FILE...             Files to frobnicate.
        "
        "Options:
        "  /v, /verbose        Say more. [repeatable]
        "  /q, /quiet          Say less.
        "      /[no-]color     Color the output.
        "  /l, /level:<LEVEL>  How hard. [default: 3]
        "  /o, /output:<FILE>  Where to write.
        "  /?, /help           Show this help and exit.
        "      /version        Show the version and exit.
      );
    }

Required options in the usage line, and the error report's pointer to
help, follow the style too.

    test("usage and errors in each style") {
      let usage(style: Style): String {
        let cli = new Command({ name: "u", style });
        cli.required(strings, { name: "name" });
        cli.usage()
      }
      assert(usage(Style.gnu) == "Usage: u [OPTIONS] --name <NAME>\n");
      assert(usage(Style.singleDash) == "Usage: u [OPTIONS] -name <NAME>\n");
      assert(usage(Style.windows) == "Usage: u [OPTIONS] /name:<NAME>\n");
      let error = new Styled(Style.singleDash, null).cli.parse(["-bogus"]) as ArgError orelse panic();
      assert(error.text() == """
        "frob: unknown option -bogus
        "Usage: frob [OPTIONS] [FILE]...
        "Try 'frob -help' for more information.
      );
      let missing = new Command({ name: "m", style: Style.windows });
      missing.required(strings, { name: "name" });
      assert(outcome(missing.parse([])) == "missingRequired: missing required option /name");
    }
