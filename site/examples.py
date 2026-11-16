"""The site's examples, run with Argmas's Python library at build time.

build.py runs this with `temper.out/py` on the path and reads the JSON
it prints: what each example's command lines give. The page shows each
example's code, the lines between a comment `snippet: NAME` and a
comment `end snippet`, beside that output, so neither can drift from
what Argmas does.

    PYTHONPATH=temper.out/py/argmas:temper.out/py/temper-core:temper.out/py/std \
        python3 site/examples.py
"""

import json
import sys

from argmas import (
    ArgError,
    Args,
    Command,
    CommandSpec,
    FlagSpec,
    OptionSpec,
    Output,
    PositionalSpec,
    Shell,
    Style,
    SubcommandSpec,
    choices,
    directories,
    ints,
    paths,
    strings,
)


def outcome(result, values=None, width=None):
    """A parse result as the page shows it: what a program would print
    and its exit status, or, for `Args`, what it would run with."""
    if isinstance(result, Args):
        return {"kind": "args", "status": result.exit_status, "values": values(result) if values else {}}
    if isinstance(result, Output):
        return {"kind": "output", "status": result.exit_status, "text": result.text(width)}
    if isinstance(result, ArgError):
        return {"kind": "error", "status": result.exit_status, "text": result.text()}
    raise TypeError(result)


# snippet: styles
def frob(style):
    cli = Command(CommandSpec(name="frob", about="Frobnicate files.", style=style))
    verbose = cli.flag(FlagSpec(name="verbose", short="v", help_="Say more."))
    level = cli.option_or(ints, 3, OptionSpec(name="level", short="l", help_="How hard."))
    files = cli.positionals(strings, PositionalSpec(name="FILE", help_="Files to frobnicate."))
    return cli, verbose, level, files


gnu = frob(Style.gnu)
go = frob(Style.single_dash)
windows = frob(Style.windows)
# end snippet

# Command lines each style accepts, all meaning the same, how to ask for
# help, and one mistake in each, as the page shows them.
STYLES = [
    ("gnu", gnu, ["-v --level=5 a.txt", "-vl5 a.txt", "--verbose -l 5 a.txt"], "--help", "--level=high a.txt"),
    ("singleDash", go, ["-v -level=5 a.txt", "-verbose -level 5 a.txt", "--verbose --level=5 a.txt"], "-help", "-level=high a.txt"),
    ("windows", windows, ["/v /level:5 a.txt", "/VERBOSE /level 5 a.txt", "-verbose -level=5 a.txt"], "/?", "/level:high a.txt"),
]

# The width the styles' help is wrapped to, to fit the page's cards.
HELP_WIDTH = 42


def styles():
    out = []
    for name, (cli, verbose, level, files), forms, help, mistake in STYLES:

        def values(args):
            return {"verbose": args.get_value(verbose), "level": args.get_value(level), "files": list(args.get_value(files))}

        out.append(
            {
                "style": name,
                "help": {"line": f"frob {help}", **outcome(cli.parse([help]), width=HELP_WIDTH)},
                "help_width": HELP_WIDTH,
                "forms": [{"line": f"frob {line}", **outcome(cli.parse(line.split()), values)} for line in forms],
                "mistake": {"line": f"frob {mistake}", **outcome(cli.parse(mistake.split()))},
            }
        )
    return out


# snippet: subcommands
git = Command(CommandSpec(name="minigit", about="Track files."))
quiet = git.flag(FlagSpec(name="quiet", short="q", help_="Say less.", inherited=True))
repo = git.option(directories, OptionSpec(name="dir", help_="Where the repository is."))

add = git.subcommand(SubcommandSpec(name="add", about="Add files."))
force = add.flag(FlagSpec(name="force", short="f", help_="Add ignored files too."))
added = add.positionals(paths, PositionalSpec(name="PATH", min_=1, help_="Files to add."))

rm = git.subcommand(SubcommandSpec(name="rm", about="Remove files.", aliases=["remove"]))
# end snippet

SUBCOMMAND_LINES = ["-q add a.txt", "add -q a.txt", "--dir repo add a.txt", "add --dir repo a.txt", "help add", "ad a.txt"]


def subcommands():
    def values(args):
        return {
            "command": args.command.path,
            "quiet": args.get_value(quiet),
            "dir": args.get_maybe(repo),
            "files": list(args.get_value(added)) if args.command == add else None,
        }

    return [{"line": f"minigit {line}", **outcome(git.parse(line.split()), values)} for line in SUBCOMMAND_LINES]


# snippet: completions
cli = Command(CommandSpec(name="frob", completions=True))
cli.flag(FlagSpec(name="verbose", short="v", help_="Say more."))
cli.option(choices(["fast", "slow"]), OptionSpec(name="mode", help_="How to go about it."))
cli.option(paths, OptionSpec(name="out", help_="Where to write."))
# end snippet

# What's typed before each Tab, after `frob `.
COMPLETION_LINES = ["--mo", "--mode ", "--mode f", "--", "--out="]


def completions():
    answers = []
    for line in COMPLETION_LINES:
        answers.append({"line": f"frob {line}", "words": line.split(" "), "text": cli.complete(line.split(" ")).text()})
    scripts = {}
    for shell in [Shell.bash, Shell.zsh, Shell.fish, Shell.powershell]:
        result = cli.parse(["--completions", shell.name])
        if not isinstance(result, Output):
            raise SystemExit(f"--completions {shell.name} gave no script")
        scripts[shell.name] = result.text()
    return {"answers": answers, "scripts": scripts, "help": cli.help()}


# snippet: messages
def frob_with(messages):
    cli = Command(CommandSpec(name="frob", about="Frobnicate files."))
    cli.option_or(ints, 3, OptionSpec(name="level", short="l", help_="How hard."))
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


def messages():
    out = {}
    for name, command in [("english", english), ("german", german), ("typo", typo)]:
        out[name] = {
            "help": {"line": "frob --help", **outcome(command.parse(["--help"]))},
            "error": {"line": "frob --levle 5", **outcome(command.parse(["--levle", "5"]))},
        }
    return out


def main():
    json.dump(
        {"styles": styles(), "subcommands": subcommands(), "completions": completions(), "messages": messages()},
        sys.stdout,
        indent=1,
    )


if __name__ == "__main__":
    main()
