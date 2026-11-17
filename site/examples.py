"""The site's outputs, from running the Python examples at build time.

build.py runs this with `temper.out/py` on the path and reads the JSON
it prints: what each example's command lines give. The examples
themselves, whose snippets the page shows in every language, are in
`demos/tour/py/examples.py` and its siblings.

    PYTHONPATH=temper.out/py/argmas:temper.out/py/temper-core:temper.out/py/std \
        python3 site/examples.py
"""

import importlib.util
import json
import sys
from pathlib import Path

from argmas import ArgError, Args, Output, Shell

# The Python examples, by path, as they aren't a package.
_spec = importlib.util.spec_from_file_location(
    "examples", Path(__file__).resolve().parent.parent / "demos" / "tour" / "py" / "examples.py"
)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)


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


# Command lines each style accepts, all meaning the same, how to ask for
# help, and one mistake in each, as the page shows them.
STYLES = [
    ("gnu", ex.gnu, ["-v --level=5 a.txt", "-vl5 a.txt", "--verbose -l 5 a.txt"], "--help", "--level=high a.txt"),
    ("singleDash", ex.go, ["-v -level=5 a.txt", "-verbose -level 5 a.txt", "--verbose --level=5 a.txt"], "-help", "-level=high a.txt"),
    ("windows", ex.windows, ["/v /level:5 a.txt", "/VERBOSE /level 5 a.txt", "-verbose -level=5 a.txt"], "/?", "/level:high a.txt"),
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


SUBCOMMAND_LINES = ["-q add a.txt", "add -q a.txt", "--dir repo add a.txt", "add --dir repo a.txt", "help add", "ad a.txt"]


def subcommands():
    def values(args):
        return {
            "command": args.command.path,
            "quiet": args.get_value(ex.quiet),
            "dir": args.get_maybe(ex.repo),
            "files": list(args.get_value(ex.added)) if args.command == ex.add else None,
        }

    return [{"line": f"minigit {line}", **outcome(ex.git.parse(line.split()), values)} for line in SUBCOMMAND_LINES]


# What's typed before each Tab, after `frob `.
COMPLETION_LINES = ["--mo", "--mode ", "--mode f", "--", "--out="]


def completions():
    answers = []
    for line in COMPLETION_LINES:
        answers.append({"line": f"frob {line}", "words": line.split(" "), "text": ex.cli.complete(line.split(" ")).text()})
    scripts = {}
    for shell in [Shell.bash, Shell.zsh, Shell.fish, Shell.powershell]:
        result = ex.cli.parse(["--completions", shell.name])
        if not isinstance(result, Output):
            raise SystemExit(f"--completions {shell.name} gave no script")
        scripts[shell.name] = result.text()
    return {"answers": answers, "scripts": scripts, "help": ex.cli.help()}


def messages():
    out = {}
    for name, command in [("english", ex.english), ("german", ex.german), ("typo", ex.typo)]:
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
