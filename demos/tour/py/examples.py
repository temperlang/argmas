"""The site's section examples, from Python.

Each `snippet:` block is shown on the site under its section, beside the
same example in every other language; `demos/run.py` runs this program
in each language and checks it prints `demos/tour/examples.txt`. The
site's Python outputs come from these same objects (site/examples.py).
"""

import sys

from argmas import (
    ArgError,
    Command,
    CommandSpec,
    FlagSpec,
    OptionSpec,
    Output,
    PositionalSpec,
    Style,
    SubcommandSpec,
    choices,
    directories,
    ints,
    paths,
    strings,
)


# snippet: styles
def frob(style):
    cli = Command(CommandSpec(name="frob", about="Frobnicate files.", style=style))
    verbose = cli.flag(FlagSpec(name="verbose", short="v", help="Say more."))
    level = cli.option_or(ints, 3, OptionSpec(name="level", short="l", help="How hard."))
    files = cli.positionals(strings, PositionalSpec(name="FILE", help="Files to frobnicate."))
    return cli, verbose, level, files


gnu = frob(Style.gnu)
go = frob(Style.single_dash)
windows = frob(Style.windows)
# end snippet

# snippet: subcommands
git = Command(CommandSpec(name="minigit", about="Track files."))
quiet = git.flag(FlagSpec(name="quiet", short="q", help="Say less.", inherited=True))
repo = git.option(directories, OptionSpec(name="dir", help="Where the repository is."))

add = git.subcommand(SubcommandSpec(name="add", about="Add files."))
force = add.flag(FlagSpec(name="force", short="f", help="Add ignored files too."))
added = add.positionals(paths, PositionalSpec(name="PATH", min=1, help="Files to add."))

rm = git.subcommand(SubcommandSpec(name="rm", about="Remove files.", aliases=["remove"]))
# end snippet

# snippet: completions
cli = Command(CommandSpec(name="frob", completions=True))
cli.flag(FlagSpec(name="verbose", short="v", help="Say more."))
cli.option(choices(["fast", "slow"]), OptionSpec(name="mode", help="How to go about it."))
cli.option(paths, OptionSpec(name="out", help="Where to write."))
# end snippet


# snippet: messages
def frob_with(messages):
    cli = Command(CommandSpec(name="frob", about="Frobnicate files."))
    cli.option_or(ints, 3, OptionSpec(name="level", short="l", help="How hard."))
    cli.set_messages(messages)
    return cli


english = frob_with({})
# A partial translation: what isn't set stays English.
german = frob_with(
    {
        "usage": "Aufruf: {command}",
        "usage.options": "[OPTIONEN]",
        "help.options": "Optionen:",
        "help.default": "[Vorgabe: {value}]",
        "error.unknownOption.suggest": "unbekannte Option {option}; meinten Sie {suggestion}?",
        "error.tryHelp": "Mehr dazu mit '{command} {help}'.",
    }
)
# A typo in a key is a mistake in the spec, found on the first run.
typo = frob_with({"usge": "Aufruf: {command}"})
# end snippet


def show(command, line):
    """Parses a command line's words after the program's name, split at
    spaces, and prints the line, any text Argmas gives, and the exit
    status."""
    result = command.parse(line.split(" ")[1:])
    print(f"$ {line}")
    if isinstance(result, (Output, ArgError)):
        sys.stdout.write(result.text())
    print(f"(exit status {result.exit_status})\n")


def main():
    show(gnu[0], "frob --help")
    show(gnu[0], "frob --level=high a.txt")
    show(go[0], "frob -help")
    show(go[0], "frob -level=high a.txt")
    show(windows[0], "frob /?")
    show(windows[0], "frob /level:high a.txt")
    show(git, "minigit -q add a.txt")
    show(git, "minigit help add")
    show(git, "minigit ad a.txt")
    show(git, "minigit add --dir repo a.txt")
    show(cli, "frob --help")
    show(cli, "frob __complete 0 --mo")
    show(cli, "frob __complete 1 --mode f")
    show(english, "frob --levle 5")
    show(german, "frob --help")
    show(german, "frob --levle 5")
    show(typo, "frob --help")


if __name__ == "__main__":
    main()
