# Help tests

Goldens of the exact help and usage text, at several widths. `Frob`
is the command from the [parsing tests](parse-tests.temper.md).

    test("help at 80 columns") {
      assert(new Frob().cli.help() == """
        "Frobnicate files.
        "
        "Usage: frob [OPTIONS] [FILE]...
        "
        "Arguments:
        "  FILE...              Files to frobnicate.
        "
        "Options:
        "  -v, --verbose        Say more. [env: FROB_VERBOSE] [repeatable]
        "      --[no-]color     Color the output. [env: FROB_COLOR]
        "  -q, --quiet          Say less.
        "  -l, --level <LEVEL>  How hard. [default: 3] [env: FROB_LEVEL]
        "  -o, --output <FILE>  Where to write.
        "  -m, --mode <MODE>    How. [choices: fast, slow]
        "  -t, --tag <TAG>      A tag. [env: FROB_TAG] [repeatable]
        "  -r, --ratio <RATIO>  How much.
        "  -h, --help           Show this help and exit.
        "      --version        Show the version and exit.
      );
    }

At 40 columns, help starts at column 16, two fifths of the width, so
longer names have their help on the next line. Notes in brackets stay
whole.

    test("help at 40 columns") {
      assert(new Frob().cli.help(40) == """
        "Frobnicate files.
        "
        "Usage: frob [OPTIONS] [FILE]...
        "
        "Arguments:
        "  FILE...       Files to frobnicate.
        "
        "Options:
        "  -v, --verbose
        "                Say more.
        "                [env: FROB_VERBOSE]
        "                [repeatable]
        "      --[no-]color
        "                Color the output.
        "                [env: FROB_COLOR]
        "  -q, --quiet   Say less.
        "  -l, --level <LEVEL>
        "                How hard. [default: 3]
        "                [env: FROB_LEVEL]
        "  -o, --output <FILE>
        "                Where to write.
        "  -m, --mode <MODE>
        "                How.
        "                [choices: fast, slow]
        "  -t, --tag <TAG>
        "                A tag. [env: FROB_TAG]
        "                [repeatable]
        "  -r, --ratio <RATIO>
        "                How much.
        "  -h, --help    Show this help and exit.
        "      --version
        "                Show the version and
        "                exit.
      );
    }

## Flags that are on

A flag that's `on` shows as negatable, with `[default: on]`, a note
of its own in the [messages](messages.temper.md).

    test("flags that are on") {
      let cli = new Command({ name: "c" });
      cli.flag({ name: "pager", short: "p", help: "Page the output.", env: "C_PAGER", on: true });
      assert(cli.help() == """
        "Usage: c [OPTIONS]
        "
        "Options:
        "  -p, --[no-]pager  Page the output. [default: on] [env: C_PAGER]
        "  -h, --help        Show this help and exit.
      );
      cli.setMessage("help.on", "[an]");
      assert(contains(cli.help(), "Page the output. [an] [env: C_PAGER]"));
    }

## Required options, long names, and wrapping

    let deploy(): Command {
      let cli = new Command({
        name: "deploy",
        about: "Deploy a build to one of the environments, after checking that it passed its tests and that nobody else is deploying at the same time.",
      });
      cli.required(strings, { name: "environment", short: "e", help: "Where to deploy.", env: "DEPLOY_ENV" });
      cli.required(ints, { name: "build-number", help: "Which build." });
      cli.option(strings, {
        name: "a-very-long-option-name-indeed",
        valueName: "SOMETHING-LONG",
        help: "An option whose name is too long for the column, so its help starts on the next line instead.",
      });
      cli.flag({ name: "dry-run", short: "n", help: "Show what would happen without doing it." });
      cli.positional(strings, { name: "SERVICE", help: "The service." });
      cli.positionals(strings, { name: "HOST", max: 1, help: "One host, or all when left out." });
      cli
    }

    test("help with required options") {
      assert(deploy().help() == """
        "Deploy a build to one of the environments, after checking that it passed its
        "tests and that nobody else is deploying at the same time.
        "
        "Usage: deploy [OPTIONS] --environment <ENVIRONMENT>
        "              --build-number <BUILD-NUMBER> SERVICE [HOST]
        "
        "Arguments:
        "  SERVICE                       The service.
        "  HOST                          One host, or all when left out.
        "
        "Options:
        "  -e, --environment <ENVIRONMENT>
        "                                Where to deploy. [env: DEPLOY_ENV] [required]
        "      --build-number <BUILD-NUMBER>
        "                                Which build. [required]
        "      --a-very-long-option-name-indeed <SOMETHING-LONG>
        "                                An option whose name is too long for the column,
        "                                so its help starts on the next line instead.
        "  -n, --dry-run                 Show what would happen without doing it.
        "  -h, --help                    Show this help and exit.
      );
    }

    test("help at 50 columns") {
      assert(deploy().help(50) == """
        "Deploy a build to one of the environments, after
        "checking that it passed its tests and that nobody
        "else is deploying at the same time.
        "
        "Usage: deploy [OPTIONS]
        "              --environment <ENVIRONMENT>
        "              --build-number <BUILD-NUMBER>
        "              SERVICE [HOST]
        "
        "Arguments:
        "  SERVICE           The service.
        "  HOST              One host, or all when left
        "                    out.
        "
        "Options:
        "  -e, --environment <ENVIRONMENT>
        "                    Where to deploy.
        "                    [env: DEPLOY_ENV] [required]
        "      --build-number <BUILD-NUMBER>
        "                    Which build. [required]
        "      --a-very-long-option-name-indeed <SOMETHING-LONG>
        "                    An option whose name is too
        "                    long for the column, so its
        "                    help starts on the next line
        "                    instead.
        "  -n, --dry-run     Show what would happen without
        "                    doing it.
        "  -h, --help        Show this help and exit.
      );
    }

A unit of the usage line, such as `--environment <ENVIRONMENT>`, isn't
split, even when it's wider than the line.

    test("usage at 30 columns") {
      assert(deploy().usage(30) == """
        "Usage: deploy [OPTIONS]
        "              --environment <ENVIRONMENT>
        "              --build-number <BUILD-NUMBER>
        "              SERVICE [HOST]
      );
    }

## The smallest command

    test("help with nothing declared") {
      let cli = new Command({ name: "bare" });
      assert(cli.help() == """
        "Usage: bare [OPTIONS]
        "
        "Options:
        "  -h, --help  Show this help and exit.
      );
    }

When the program takes `-h` or `--help` for itself, only the other is
built in, and when it takes both, help isn't built in at all.

    test("help without -h") {
      let cli = new Command({ name: "srv" });
      cli.option(strings, { name: "host", short: "h", help: "The host." });
      assert(cli.help() == """
        "Usage: srv [OPTIONS]
        "
        "Options:
        "  -h, --host <HOST>  The host.
        "      --help         Show this help and exit.
      );
      let both = new Command({ name: "both" });
      both.flag({ name: "help", short: "h", help: "Mine." });
      assert(both.help() == """
        "Usage: both [OPTIONS]
        "
        "Options:
        "  -h, --help  Mine.
      );
      let error = both.parse(["--bogus"]) as ArgError orelse panic();
      assert(error.text() == """
        "both: unknown option --bogus
        "Usage: both [OPTIONS]
      );
    }

Positional forms in the usage line: `X` for exactly one, `[X]` for at
most one, `X...` for at least one, and `[X]...` for any number.

    test("positional forms") {
      let cli = new Command({ name: "p" });
      cli.positional(strings, { name: "A" });
      cli.positionals(strings, { name: "B", max: 1 });
      cli.positionals(strings, { name: "C", min: 1 });
      cli.positionals(strings, { name: "D" });
      cli.positionals(strings, { name: "E", min: 2, max: 3 });
      assert(cli.usage() == "Usage: p [OPTIONS] A [B] C... [D]... E...\n");
    }

Help without help text shows the notes alone.

    test("notes without help") {
      let cli = new Command({ name: "n" });
      cli.optionOr(floats, 0.5, { name: "ratio" });
      cli.option(choices(["a", "b"]), { name: "pick", valueName: "X" });
      assert(cli.help() == """
        "Usage: n [OPTIONS]
        "
        "Options:
        "      --ratio <RATIO>  [default: 0.5]
        "      --pick <X>       [choices: a, b]
        "  -h, --help           Show this help and exit.
      );
    }
