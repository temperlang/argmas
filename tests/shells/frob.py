"""A small program using Argmas from Python, for the shell tests.

run.py puts the generated library in temper.out/py on the path and
runs this as `frob`. Its completions come from Argmas through the
`__complete` protocol, and `frob --completions SHELL` prints a script.
"""

import os
import sys

from argmas import (
    Candidate,
    Command,
    CommandSpec,
    Completer,
    FlagSpec,
    OptionSpec,
    PositionalSpec,
    Style,
    SubcommandSpec,
    choices,
    directories,
    paths,
    strings,
)
from argmas import ArgError, Args, Output


class Branches(Completer):
    """Values found when the program runs, as from a repository."""

    def complete(self, partial):
        return [Candidate("main", "The default branch."), Candidate("dev"), Candidate("docs")]


def command(style):
    cli = Command(CommandSpec(name="frob", about="Frobnicate files.", version="1.0.0", completions=True, style=style))
    cli.count(FlagSpec(name="verbose", short="v", help_="Say more.", inherited=True))
    cli.flag(FlagSpec(name="color", help_="Color the output.", negatable=True))
    cli.option(choices(["fast", "slow"]), OptionSpec(name="mode", help_="How to go about it."))
    cli.option(paths, OptionSpec(name="out", short="o", help_="Where to write."))
    cli.option(directories, OptionSpec(name="dir", help_="Where to work."))
    cli.option(strings, OptionSpec(name="branch", help_="Which branch.", completer=Branches()))
    add = cli.subcommand(SubcommandSpec(name="add", about="Add files.", aliases=["stage"]))
    add.flag(FlagSpec(name="force", short="f", help_="Add ignored files too."))
    add.positionals(paths, PositionalSpec(name="PATH"))
    remote = cli.subcommand(SubcommandSpec(name="remote", about="Manage remotes."))
    remote.subcommand(SubcommandSpec(name="add", about="Add a remote."))
    remote.subcommand(SubcommandSpec(name="list", about="List remotes."))
    return cli


def main():
    # FROB_STYLE=windows tries the same command in another style.
    style = Style.windows if os.environ.get("FROB_STYLE") == "windows" else Style.gnu
    result = command(style).parse(sys.argv[1:])
    if isinstance(result, Output):
        sys.stdout.write(result.text())
    elif isinstance(result, ArgError):
        sys.stderr.write(result.text())
    elif isinstance(result, Args):
        print(f"ran {result.command.path}")
    sys.exit(result.exit_status)


main()
