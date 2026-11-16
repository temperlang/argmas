# /// script
# requires-python = ">=3.11"
# ///
"""Runs Argmas's tour in each language and checks the output matches.

Usage, from anywhere in the repo, after building the libraries:

    temper build -b cpp -b csharp -b java -b js -b lua -b py -b rust
    uv run demos/run.py [LANGUAGE ...]

Each `demos/tour/<language>/` builds with that language's usual tools,
as demos/README.md shows, into a program named `pack`. This builds it,
then runs it once for each command line in CASES, as a shell would, and
writes a transcript: each command line, what the program printed to
standard output and to standard error, and its exit status. Every
language's transcript must be exactly `demos/tour/expected.txt`. Exits
non-zero on any failure.
"""

import argparse
import difflib
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOUR = ROOT / "demos" / "tour"

# Per language, run in its directory: the commands that build the tour,
# and the command that runs it, to which each case's arguments are added.
LANGUAGES = {
    "cpp": (
        [
            ["cmake", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"],
            ["cmake", "--build", "build", "--target", "tour", "-j", "2"],
        ],
        ["build/tour"],
    ),
    # Building first keeps compiler warnings out of the tour's output. No
    # build servers, which would stay running after.
    "csharp": (
        [["dotnet", "build", "-v", "q", "--nologo", "-nodeReuse:false", "-p:UseSharedCompilation=false"]],
        ["dotnet", "run", "--no-build", "--"],
    ),
    # installDist puts a launcher script in build/install, so each case
    # runs without Gradle.
    "java": (
        [["./gradlew", "-q", "--no-daemon", "installDist"]],
        ["build/install/tour/bin/tour"],
    ),
    # ci, not install: it re-copies the generated library after a rebuild.
    "js": ([["npm", "ci", "--silent", "--no-audit", "--no-fund"]], ["node", "tour.js"]),
    "lua": ([], [os.environ.get("LUA", "lua"), "-l", "paths", "tour.lua"]),
    "py": ([["uv", "sync", "-q"]], ["uv", "run", "-q", "--no-sync", "tour.py"]),
    "rust": (
        [["cargo", "build", "-q", "--release"]],
        ["target/release/tour"],
    ),
}

# The command lines the tour runs, each with environment variables to
# set, as `pack` would be run from a shell.
CASES = [
    ({}, "add -v --level=9 --mode fast out.pack a.txt b.txt"),
    ({"PACK_LEVEL": "7"}, "add out.pack a.txt"),
    ({}, "-v ls out.pack"),
    ({}, "--help"),
    ({}, "add --help"),
    ({}, "--version"),
    ({}, "add --mode quick out.pack a.txt"),
    ({}, "ad out.pack"),
    ({}, "add out.pack"),
]


def run(args, dir, env=None):
    """Runs one command in `dir`, returning what it printed."""
    return subprocess.run(args, cwd=dir, capture_output=True, encoding="utf-8", env=env)


def transcript(language):
    """Builds the tour and runs every case, returning the transcript."""
    dir = TOUR / language
    build, command = LANGUAGES[language]
    for args in build:
        result = run(args, dir)
        if result.returncode != 0:
            raise RuntimeError(f"{' '.join(args)} failed:\n{result.stderr}{result.stdout}")
    out = []
    for extra, line in CASES:
        env = {k: v for k, v in os.environ.items() if not k.startswith("PACK_")}
        env.update(extra)
        result = run([*command, *shlex.split(line)], dir, env)
        settings = "".join(f"{k}={v} " for k, v in extra.items())
        out.append(f"$ {settings}pack {line}\n")
        out.append(result.stdout)
        if result.stderr:
            out.append("(standard error)\n")
            out.append(result.stderr)
        out.append(f"(exit status {result.returncode})\n\n")
    return "".join(out).replace("\r\n", "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("languages", nargs="*", metavar="LANGUAGE", help=", ".join(LANGUAGES))
    languages = parser.parse_args().languages or list(LANGUAGES)
    unknown = set(languages) - set(LANGUAGES)
    if unknown:
        parser.error(f"unknown: {', '.join(sorted(unknown))}")
    expected = (TOUR / "expected.txt").read_text(encoding="utf-8")
    failed = []
    for language in languages:
        try:
            actual = transcript(language)
        except (RuntimeError, OSError) as error:
            print(f"{language}: error\n{error}")
            failed.append(language)
            continue
        if actual == expected:
            print(f"{language}: ok, {len(CASES)} command lines match")
        else:
            print(f"{language}: output differs")
            diff = difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                "expected.txt",
                language,
            )
            sys.stdout.writelines(diff)
            failed.append(language)
    if failed:
        print(f"Failed: {' '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
