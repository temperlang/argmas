# /// script
# requires-python = ">=3.11"
# ///
"""Compares Argmas's parsing with reference parsers on the same inputs.

Usage, from anywhere in the repo:

    uv run tests/reference/run.py [--no-build] [--require] [-v] [PARSER ...]

Builds the Python library with Temper (`$TEMPER`, or `temper` on PATH),
unless `--no-build`, then parses each command line in CASES with Argmas
(the Python library in temper.out/py) and with each reference parser,
all declaring the same spec from SPECS:

- `getopt`: glibc's `getopt_long`, in getopt.c, compiled with `cc` (or
  `$CC`) into a throwaway directory. Only on glibc, since other C
  libraries' getopt_long differ.
- `argparse`: Python's own, in this process, with its defaults.
- `clap`: Rust's clap, its builder API, in clap/, built with `cargo`
  (or `$CARGO`) into clap/target, from its Cargo.lock.

Each result is summed up the same way: `error: KIND` (Argmas's error
kinds, plus `ambiguousOption` and `givenTwice`, which only references
give), `output: help`, or the values not at their defaults, with the
command's path when it has subcommands. A reference that gives what Argmas gives
matches; one that doesn't must give what differences.toml says, with
why, or the run fails. An entry there that no longer differs fails
too, so the file stays true. Parsers that can't run are skipped (with
`--require`, as CI runs it, they fail instead). `-v` prints every case.

Another reference is a program that takes the spec in the environment
variable REFERENCE_SPEC and the case's arguments as its own, and prints
its result as one line of JSON, as getopt.c does: `{"error": KIND}`,
`{"output": "help"}`, or `{"command": PATH, "values": {NAME: VALUE}}`
with every value of each command on the path. REFERENCE_SPEC has one
line per command and argument, from `spec_text`:

    command NAME                      (the first is the top command; each
                                       later one is a subcommand of it)
    KIND NAME SHORT TYPE MIN MAX      (`-` where there's none)

KIND is flag, count, negatable, option, required, repeated,
positional, or positionals, and TYPE string or int. Add it to
`EXTERNAL`, with how it's built, as `build_getopt` and `build_clap`
do.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "temper.out" / "py"

# Specs: (kind, name, short, type, min, max) per argument, and
# subcommands, each a spec of its own without subcommands.
SPECS = {
    "frob": {
        "args": [
            ("count", "verbose", "v", "string", 0, None),
            ("flag", "quiet", "q", "string", 0, None),
            ("negatable", "color", None, "string", 0, None),
            ("option", "output", "o", "string", 0, None),
            ("option", "name", None, "string", 0, None),
            ("option", "level", "l", "int", 0, None),
            ("repeated", "include", "I", "string", 0, None),
            ("positionals", "FILE", None, "string", 0, None),
        ],
    },
    "req": {
        "args": [
            ("flag", "quiet", "q", "string", 0, None),
            ("required", "output", "o", "string", 0, None),
            ("positional", "FILE", None, "string", 1, 1),
        ],
    },
    "cp": {
        "args": [
            ("positionals", "SRC", None, "string", 1, None),
            ("positional", "DEST", None, "string", 1, 1),
        ],
    },
    "git": {
        "args": [
            ("count", "verbose", "v", "string", 0, None),
            ("option", "dir", "C", "string", 0, None),
        ],
        "subs": {
            "add": [
                ("flag", "force", "f", "string", 0, None),
                ("positionals", "PATH", None, "string", 0, None),
            ],
            "rm": [
                ("flag", "cached", None, "string", 0, None),
                ("positionals", "PATH", None, "string", 1, None),
            ],
        },
    },
}

# Each case: an id, the spec, and the arguments.
CASES = [
    # Short options and bundles.
    ("short-flag", "frob", ["-q"]),
    ("short-count", "frob", ["-vvv"]),
    ("short-counts-apart", "frob", ["-v", "-v"]),
    ("bundle", "frob", ["-vq"]),
    ("bundle-then-value", "frob", ["-vqo", "out"]),
    ("bundle-attached-value", "frob", ["-vqoout"]),
    ("bundle-value-takes-rest", "frob", ["-ovq"]),
    ("short-attached", "frob", ["-ofile"]),
    ("short-separate", "frob", ["-o", "file"]),
    ("short-equals", "frob", ["-o=file"]),
    ("short-int-attached", "frob", ["-l5"]),
    ("bundle-value-missing", "frob", ["-vo"]),
    ("bundle-dash", "frob", ["-v-"]),
    ("short-flag-equals", "frob", ["-q=yes"]),
    # Long options.
    ("long-equals", "frob", ["--output=file"]),
    ("long-separate", "frob", ["--output", "file"]),
    ("long-empty", "frob", ["--name="]),
    ("long-empty-separate", "frob", ["--name", ""]),
    ("long-value-with-equals", "frob", ["--name=a=b"]),
    ("long-count", "frob", ["--verbose", "--verbose", "-v"]),
    ("long-non-ascii-value", "frob", ["--name=h\u00e9llo"]),
    ("long-flag-empty-value", "frob", ["--quiet="]),
    ("long-empty-name", "frob", ["--=x"]),
    ("triple-dash", "frob", ["---x"]),
    ("long-int", "frob", ["--level=7"]),
    ("long-int-invalid", "frob", ["--level=seven"]),
    ("long-int-empty", "frob", ["--level="]),
    ("long-int-too-big", "frob", ["--level=99999999999"]),
    # `--` and `-`.
    ("double-dash", "frob", ["--", "-v", "--output=x"]),
    ("double-dash-twice", "frob", ["a", "--", "--", "b"]),
    ("double-dash-as-value", "frob", ["--name", "--"]),
    ("dash-positional", "frob", ["-"]),
    ("dash-value", "frob", ["-o", "-"]),
    ("empty-positional", "frob", [""]),
    ("positional-lists", "cp", ["a", "b", "c"]),
    ("positional-lists-least", "cp", ["a", "b"]),
    ("positional-lists-too-few", "cp", ["a"]),
    # Permutation: options after positional arguments.
    ("options-after-positionals", "frob", ["a", "-v", "b", "--output=x"]),
    ("options-after-one-positional", "frob", ["a", "-v"]),
    # Negatable flags.
    ("negatable-on", "frob", ["--color"]),
    ("negatable-off", "frob", ["--no-color"]),
    ("negatable-last-wins", "frob", ["--color", "--no-color"]),
    ("negatable-last-wins-on", "frob", ["--no-color", "--color"]),
    ("not-negatable", "frob", ["--no-quiet"]),
    ("negatable-given-value", "frob", ["--no-color=1"]),
    # Repeats.
    ("repeated-collects", "frob", ["-I", "a", "--include=b", "-Ic"]),
    ("option-last-wins", "frob", ["-o", "a", "--output", "b"]),
    ("flag-twice", "frob", ["-q", "--quiet"]),
    # Errors.
    ("unknown-long", "frob", ["--bogus"]),
    ("unknown-short", "frob", ["-x"]),
    ("unknown-in-bundle", "frob", ["-vx"]),
    ("flag-given-value", "frob", ["--quiet=yes"]),
    ("missing-value-long", "frob", ["--output"]),
    ("missing-value-short", "frob", ["-o"]),
    ("missing-value-before-option", "frob", ["--output", "--quiet"]),
    ("missing-value-short-before-option", "frob", ["-o", "-q"]),
    ("missing-required", "req", ["a"]),
    ("missing-required-and-positional", "req", []),
    ("required-given", "req", ["-o", "x", "a"]),
    ("too-few-positionals", "req", ["-o", "x"]),
    ("too-many-positionals", "req", ["-o", "x", "a", "b"]),
    # Prefixes of long options.
    ("prefix-unique", "frob", ["--verb"]),
    ("prefix-unique-value", "frob", ["--out=x"]),
    ("prefix-ambiguous", "frob", ["--n=x"]),
    # Values starting with `-`.
    ("dash-value-attached-long", "frob", ["--output=-x"]),
    ("dash-value-attached-short", "frob", ["-o-x"]),
    ("dash-value-separate", "frob", ["--output", "-x"]),
    # Negative numbers.
    ("negative-value-long", "frob", ["--level", "-5"]),
    ("negative-value-short", "frob", ["-l", "-5"]),
    ("negative-value-attached", "frob", ["-l-5"]),
    ("negative-string-value", "frob", ["-o", "-5"]),
    ("negative-positional", "frob", ["-5"]),
    ("negative-float-positional", "frob", ["-1.5"]),
    # Help.
    ("help-long", "frob", ["--help"]),
    ("help-short", "frob", ["-h"]),
    ("help-in-bundle", "frob", ["-vh"]),
    ("help-after-error", "frob", ["--bogus", "--help"]),
    ("help-before-error", "frob", ["--help", "--bogus"]),
    ("help-after-double-dash", "frob", ["--", "--help"]),
    # Subcommands.
    ("sub", "git", ["add", "a"]),
    ("sub-options", "git", ["-v", "add", "-f", "a"]),
    ("sub-option-attached", "git", ["-Cdir", "rm", "--cached", "a"]),
    ("sub-double-dash", "git", ["add", "--", "-f"]),
    ("sub-after-double-dash", "git", ["--", "add"]),
    ("sub-separate-value", "git", ["-C", "dir", "add"]),
    ("sub-unknown", "git", ["ad"]),
    ("sub-missing", "git", []),
    ("sub-missing-after-options", "git", ["-v"]),
    ("sub-parent-option-after", "git", ["add", "-v"]),
    ("sub-option-before", "git", ["-f", "add"]),
    ("sub-too-few", "git", ["rm"]),
    ("sub-help", "git", ["add", "--help"]),
]


def spec_text(spec_name):
    """The spec in REFERENCE_SPEC's lines."""
    spec = SPECS[spec_name]

    def lines(args):
        for kind, name, short, type_name, low, high in args:
            yield f"{kind} {name} {short or '-'} {type_name} {low} {'-' if high is None else high}"

    out = [f"command {spec_name}", *lines(spec["args"])]
    for sub, args in spec.get("subs", {}).items():
        out += [f"command {sub}", *lines(args)]
    return "\n".join(out) + "\n"


def all_args(spec):
    """The arguments of a spec and its subcommands."""
    out = list(spec["args"])
    for args in spec.get("subs", {}).values():
        out += args
    return out


def default(kind):
    return {"count": 0, "flag": False, "negatable": False, "repeated": [], "positionals": []}.get(kind)


def summary(spec_name, result):
    """What a result comes to: an error's kind, help, or the values not
    at their defaults."""
    if "error" in result:
        return f"error: {result['error']}"
    if "output" in result:
        return f"output: {result['output']}"
    spec = SPECS[spec_name]
    kinds = {name: kind for kind, name, *_ in all_args(spec)}
    out = {}
    if "subs" in spec:
        out["command"] = result["command"]
    for name, value in result["values"].items():
        if value != default(kinds[name]):
            out[name] = value
    return out


def show(summed):
    return summed if isinstance(summed, str) else json.dumps(summed)


# Argmas, from the Python library.


def argmas_parser():
    path = [str(OUT / name) for name in ("argmas", "temper-core", "std")]
    if not all(Path(p).is_dir() for p in path):
        return None, f"no Python library in {OUT}"
    sys.path[:0] = path
    import argmas

    def declare(cli, args):
        handles = []
        for kind, name, short, type_name, low, high in args:
            value_type = argmas.ints if type_name == "int" else argmas.strings
            if kind in ("flag", "count", "negatable"):
                spec = argmas.FlagSpec(name=name, short=short, negatable=kind == "negatable")
                handle = cli.count(spec) if kind == "count" else cli.flag(spec)
            elif kind == "positional":
                handle = cli.positional(value_type, argmas.PositionalSpec(name=name))
            elif kind == "positionals":
                handle = cli.positionals(value_type, argmas.PositionalSpec(name=name, min=low, max=high))
            else:
                handle = getattr(cli, kind)(value_type, argmas.OptionSpec(name=name, short=short))
            handles.append((name, kind, handle))
        return handles

    def parse(spec_name, argv):
        spec = SPECS[spec_name]
        cli = argmas.Command(argmas.CommandSpec(name=spec_name))
        top = declare(cli, spec["args"])
        subs = {}
        for sub, args in spec.get("subs", {}).items():
            command = cli.subcommand(argmas.SubcommandSpec(name=sub))
            subs[sub] = (command, declare(command, args))
        result = cli.parse(argv, argmas.MapEnvironment({}))
        if isinstance(result, argmas.ArgError):
            return {"error": result.kind.name}
        if isinstance(result, argmas.Output):
            return {"output": result.kind.name}
        handles = list(top)
        for command, sub_handles in subs.values():
            if result.command == command:
                handles += sub_handles
        values = {}
        for name, kind, handle in handles:
            get = result.get_maybe if kind == "option" else result.get_value
            value = get(handle)
            values[name] = list(value) if kind in ("repeated", "positionals") else value
        return {"command": result.command.path, "values": values}

    return parse, None


# Python's argparse, with its defaults.


class ArgparseError(Exception):
    pass


class ArgparseHelp(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgparseError(message)

    def print_help(self, file=None):
        raise ArgparseHelp()


def argparse_kind(message, spec):
    """Argmas's kind for an argparse error, from its message."""
    if message.startswith("unrecognized arguments: "):
        word = message.removeprefix("unrecognized arguments: ").split(" ")[0]
        return "unknownOption" if word.startswith("-") and word != "-" else "tooManyPositionals"
    if message.startswith("ambiguous option: "):
        return "ambiguousOption"
    if "expected one argument" in message:
        return "missingValue"
    if "ignored explicit argument" in message:
        return "unexpectedValue"
    if "invalid choice" in message and "subs" in spec:
        return "unknownCommand"
    if "invalid int value" in message:
        return "invalidValue"
    if message.startswith("the following arguments are required: "):
        first = message.removeprefix("the following arguments are required: ").split(", ")[0]
        if first.startswith("-"):
            return "missingRequired"
        return "missingCommand" if first == "_command" else "tooFewPositionals"
    return f"unclassified ({message})"


def argparse_parser():
    def declare(parser, args):
        for kind, name, short, type_name, low, high in args:
            names = [f"-{short}"] if short else []
            if kind not in ("positional", "positionals"):
                names.append(f"--{name}")
            options = {"dest": name}
            value_type = int if type_name == "int" else str
            if kind == "flag":
                options["action"] = "store_true"
            elif kind == "count":
                options.update(action="count", default=0)
            elif kind == "negatable":
                options.update(action=argparse.BooleanOptionalAction, default=False)
            elif kind in ("option", "required"):
                options.update(type=value_type, required=kind == "required")
            elif kind == "repeated":
                options.update(type=value_type, action="append")
            else:
                # Positional arguments take their name as dest.
                del options["dest"]
                names = [name]
                options["type"] = value_type
                if kind == "positionals":
                    options["nargs"] = {(0, None): "*", (1, None): "+", (0, 1): "?"}[(low, high)]
            parser.add_argument(*names, **options)

    def parse(spec_name, argv):
        spec = SPECS[spec_name]
        lists = {name for kind, name, *_ in all_args(spec) if kind == "repeated"}
        parser = Parser(prog=spec_name)
        declare(parser, spec["args"])
        if "subs" in spec:
            subparsers = parser.add_subparsers(dest="_command", required=True)
            for sub, args in spec["subs"].items():
                declare(subparsers.add_parser(sub), args)
        try:
            namespace = vars(parser.parse_args(argv))
        except ArgparseHelp:
            return {"output": "help"}
        except ArgparseError as error:
            return {"error": argparse_kind(str(error), spec)}
        command = namespace.pop("_command", None)
        # A repeated option not given is None, not a list.
        values = {name: [] if value is None and name in lists else value for name, value in namespace.items()}
        return {"command": f"{spec_name} {command}" if command else spec_name, "values": values}

    return parse, None


# Reference programs, run once per case.


def build_getopt(tmp):
    if platform.system() != "Linux" or platform.libc_ver()[0] != "glibc":
        return None, "needs glibc"
    cc = os.environ.get("CC", "cc")
    if shutil.which(cc) is None:
        return None, f"{cc} isn't installed"
    program = Path(tmp) / "getopt"
    subprocess.run([cc, "-std=c11", "-O1", "-Wall", "-Werror", "-o", str(program), str(HERE / "getopt.c")], check=True)
    return [str(program)], None


def build_clap(tmp):
    cargo = os.environ.get("CARGO", "cargo")
    if shutil.which(cargo) is None:
        return None, f"{cargo} isn't installed"
    manifest = HERE / "clap" / "Cargo.toml"
    subprocess.run([cargo, "build", "--locked", "--release", "--quiet", "--manifest-path", str(manifest)], check=True)
    program = HERE / "clap" / "target" / "release" / "argmas-reference-clap"
    return [str(program.with_suffix(".exe") if os.name == "nt" else program)], None


EXTERNAL = {"getopt": build_getopt, "clap": build_clap}


def external_parser(command):
    def parse(spec_name, argv):
        # Nothing from outside, such as POSIXLY_CORRECT, changes it.
        env = {"PATH": os.environ.get("PATH", ""), "REFERENCE_SPEC": spec_text(spec_name)}
        done = subprocess.run(command + argv, env=env, capture_output=True, text=True, timeout=30)
        if done.returncode != 0:
            raise RuntimeError(f"{command[0]} failed: {done.stderr.strip()}")
        return json.loads(done.stdout)

    return parse


REFERENCES = ["getopt", "argparse", "clap"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-build", action="store_true", help="use temper.out/py as it is")
    parser.add_argument("--require", action="store_true", help="fail when a reference can't run")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every case")
    parser.add_argument("references", nargs="*", metavar="PARSER", help=", ".join(REFERENCES))
    options = parser.parse_args()
    references = options.references or REFERENCES
    unknown = set(references) - set(REFERENCES)
    if unknown:
        parser.error(f"unknown: {', '.join(sorted(unknown))}")
    if not options.no_build:
        temper = os.environ.get("TEMPER", "temper")
        subprocess.run([temper, "build", "-b", "py"], cwd=ROOT, check=True)

    documented = {}
    for entry in tomllib.loads((HERE / "differences.toml").read_text())["difference"]:
        documented[(entry["case"], entry["parser"])] = entry["gives"]
    ids = [case_id for case_id, _, _ in CASES]
    duplicates = {i for i in ids if ids.count(i) > 1}
    problems = [f"case {i} is in CASES twice" for i in sorted(duplicates)]
    problems += [f"differences.toml: no case {c}" for c, _ in documented if c not in ids]

    argmas_parse, why = argmas_parser()
    if argmas_parse is None:
        sys.exit(f"argmas: {why}")
    failed = bool(problems)
    with tempfile.TemporaryDirectory(prefix="argmas-reference-") as tmp:
        parsers = {}
        for name in references:
            if name in EXTERNAL:
                command, why = EXTERNAL[name](tmp)
                parse = external_parser(command) if command else None
            else:
                parse, why = argparse_parser()
            if parse is None:
                print(f"{name}: skipped, {why}")
                failed = failed or options.require
                continue
            parsers[name] = parse
        print(f"Python {platform.python_version()}, {' '.join(platform.libc_ver())}")

        counts = {name: {"match": 0, "documented": 0} for name in parsers}
        for case_id, spec_name, argv in CASES:
            want = summary(spec_name, argmas_parse(spec_name, argv))
            line = [f"{case_id}: {argv} -> argmas {show(want)}"]
            for name, parse in parsers.items():
                got = summary(spec_name, parse(spec_name, argv))
                expected = documented.get((case_id, name))
                if got == want and expected is None:
                    counts[name]["match"] += 1
                elif got == want:
                    problems.append(f"{case_id}: {name} now gives what argmas gives; drop it from differences.toml")
                elif expected is None:
                    problems.append(f"{case_id}: {argv}: argmas gives {show(want)}, {name} {show(got)}, undocumented")
                elif got != expected:
                    problems.append(f"{case_id}: {name} gives {show(got)}, not {show(expected)} as documented")
                else:
                    counts[name]["documented"] += 1
                    line.append(f"    {name} {show(got)} (documented)")
            if options.verbose:
                print("\n".join(line))

    for name, count in counts.items():
        print(f"{name}: {count['match']} of {len(CASES)} cases match, {count['documented']} differ as documented")
    for problem in problems:
        print(f"FAIL {problem}")
    sys.exit(1 if failed or problems else 0)


if __name__ == "__main__":
    main()
