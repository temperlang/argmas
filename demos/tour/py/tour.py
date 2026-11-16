"""A tour of Argmas, from Python: `pack`, a small archiver's command line.

The same program exists for each language Argmas supports, and they all
print the same text for the same arguments. See demos/README.md for how
to run them.
"""

import os
import sys

from argmas import (
    ArgError,
    Args,
    Command,
    CommandSpec,
    Environment,
    FlagSpec,
    OptionSpec,
    Output,
    PositionalSpec,
    Source,
    SubcommandSpec,
    choices,
    ints,
    strings,
)


class OsEnvironment(Environment):
    """The process's environment variables, which Argmas reads through
    this interface, so parsing touches nothing outside on its own."""

    def get(self, name):
        return os.environ.get(name)


def main():
    # The command, declared once. Each argument's handle has its type:
    # `level` gives an int and `files` a list of strings.
    cli = Command(CommandSpec(name="pack", about="Pack files into archives.", version="1.0.0"))
    verbose = cli.flag(FlagSpec(name="verbose", short="v", help_="Say what's happening.", inherited=True))

    add = cli.command(SubcommandSpec(name="add", about="Add files to an archive."))
    level = add.option_or(ints, 6, OptionSpec(name="level", short="l", help_="How hard to compress.", env="PACK_LEVEL"))
    mode = add.option(choices(["fast", "small"]), OptionSpec(name="mode", help_="What to favor."))
    archive = add.positional(strings, PositionalSpec(name="ARCHIVE", help_="The archive to add to."))
    files = add.positionals(strings, PositionalSpec(name="FILE", min_=1, help_="Files to add."))

    list_ = cli.command(SubcommandSpec(name="list", about="List an archive's files.", aliases=["ls"]))
    listed = list_.positional(strings, PositionalSpec(name="ARCHIVE", help_="The archive to list."))

    # Values to run with, text to print (help and version), or a mistake.
    result = cli.parse(sys.argv[1:], OsEnvironment())
    match result:
        case Args():
            args = result
            if args.command == add:
                print(f"add to {args.get_value(archive)}: {', '.join(args.get_value(files))}")
                source = args.source(level.param)
                origin = "default" if source == Source.absent else source.name
                print(f"level: {args.get_value(level)} ({origin})")
                print(f"mode: {args.get_maybe(mode) or 'any'}")
            elif args.command == list_:
                print(f"list {args.get_value(listed)}")
            print(f"verbose: {'yes' if args.get_value(verbose) else 'no'}")
        case Output():
            sys.stdout.write(result.text())
        case ArgError():
            sys.stderr.write(result.text())
    sys.exit(result.exit_status)


if __name__ == "__main__":
    main()
