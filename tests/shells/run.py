# /// script
# requires-python = ">=3.11"
# ///
"""Drives real shells' completion through the scripts Argmas prints.

Usage, from anywhere in the repo:

    uv run tests/shells/run.py [--no-build] [--require] [SHELL ...]

Builds the Python library with Temper (`$TEMPER`, or `temper` on PATH),
unless `--no-build`, then puts tests/shells/frob.py on PATH as `frob` in
a throwaway directory, installs each shell's script there as `frob
--completions SHELL` prints it, and completes the command lines in CASES
in the real shell, comparing what it offers. SHELL is any of bash, zsh,
fish, and powershell (pwsh); shells that aren't installed are skipped,
and the report says which ran (with `--require`, as CI runs it, a
missing shell fails instead). Each shell runs without the user's
configuration, with HOME in the throwaway directory, so nothing outside
it changes, and in a directory of its own beside HOME, so the files a
shell keeps there aren't offered. On Windows, `frob` is a batch file,
and only PowerShell runs.

bash and zsh are driven through a pseudo-terminal, as a user would:
bash inserts every completion into the line (readline's
insert-completions) and the line is printed, and zsh lists them
(delete-char-or-list), once its line editor is reading. fish uses
`complete -C`, and PowerShell `TabExpansion2`. Exits non-zero on any
difference.
"""

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WINDOWS = os.name == "nt"
OUT = ROOT / "temper.out" / "py"

# Command lines, with the cursor at the end, and what should be offered.
# Paths are compared without a leading `./` or trailing `/`, which shells
# add in their own ways. The working directory holds alpha.txt,
# gamma.txt, and the directory beta.
CASES = [
    ("frob --ver", ["--verbose", "--version"]),
    ("frob --mode ", ["fast", "slow"]),
    ("frob --mode=s", ["--mode=slow"]),
    ("frob --branch d", ["dev", "docs"]),
    ("frob ", ["add", "help", "remote"]),
    ("frob st", ["stage"]),
    ("frob remote ", ["add", "help", "list"]),
    ("frob add --f", ["--force"]),
    ("frob add -v --verb", ["--verbose"]),
    ("frob --color --co", ["--completions"]),
    ("frob --completions ", ["bash", "fish", "powershell", "zsh"]),
    ("frob --dir ", ["beta"]),
    ("frob add a", ["alpha.txt"]),
    ("frob --out=g", ["--out=gamma.txt"]),
    ("windows: frob /ver", ["/verbose", "/version"]),
    ("windows: frob /mode:s", ["/mode:slow"]),
]

SHELLS = {"bash": "bash", "zsh": "zsh", "fish": "fish", "powershell": "pwsh"}


def normalized(candidates):
    out = set()
    for c in candidates:
        c = c.strip().strip("'\"")
        c = re.sub(r"(^|[=:])\.[/\\]", r"\1", c)
        c = c.rstrip("/\\")
        if c:
            out.add(c)
    return sorted(out)


def split_case(case):
    """The line and the environment for one case."""
    if case.startswith("windows: "):
        return case.removeprefix("windows: "), {"FROB_STYLE": "windows"}
    return case, {}


class Pty:
    """A shell in a pseudo-terminal, read until a marker comes."""

    def __init__(self, argv, env, cwd):
        # Not on Windows, which has no pseudo-terminals.
        import pty

        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(cwd)
            os.execvpe(argv[0], argv, env)
        self.buffer = b""

    def send(self, text):
        os.write(self.fd, text.encode())

    def until(self, marker, timeout=20.0):
        import select

        end = time.time() + timeout
        while marker.encode() not in self.buffer:
            if time.time() > end:
                raise RuntimeError(f"timed out waiting for {marker!r}; got {self.buffer[-500:]!r}")
            ready, _, _ = select.select([self.fd], [], [], 0.1)
            if ready:
                try:
                    self.buffer += os.read(self.fd, 65536)
                except OSError:
                    break
        text, _, rest = self.buffer.partition(marker.encode())
        self.buffer = rest
        return text.decode(errors="replace")

    def close(self):
        try:
            self.send("exit\r")
            time.sleep(0.2)
        finally:
            os.close(self.fd)
            os.waitpid(self.pid, 0)


ANSI = re.compile(r"\x1b(\[[0-9;?]*[ -/]*[@-~]|[()][0-9A-Za-z]|[=>]|\][^\x07]*\x07)")


def drive_bash(work, env):
    script = work.parent / "frob.bash"
    shell = Pty(["bash", "--norc", "--noprofile", "-i"], {**env, "INPUTRC": str(work.parent / "inputrc")}, work)
    shell.send(f"PS1='' PS2=''; source {shlex.quote(str(script))}; echo READY''\r")
    shell.until("READY\r\n")
    results = []
    for n, (case, _) in enumerate(CASES):
        line, extra = split_case(case)
        exports = "".join(f"export {k}={v}; " for k, v in extra.items()) or "unset FROB_STYLE; "
        shell.send(f"{exports}echo BEGIN{n}''\r")
        shell.until(f"BEGIN{n}\r\n")
        # Insert every completion, then print the line's words.
        shell.send(line + "\x1b*" + "\x01" + "printf '<%s>\\n' " + "\r")
        shell.send(f"echo END{n}''\r")
        text = ANSI.sub("", shell.until(f"END{n}\r\n"))
        words = re.findall(r"^<(.*)>\r?$", text, re.M)
        before = len(line.split()) - (0 if line.endswith(" ") else 1)
        results.append(words[before:])
    shell.close()
    return results


# What zsh's line editor prints as it starts reading a line.
ZLE_READY = "<ZLE-READY>"


def drive_zsh(work, env):
    script = work.parent / "frob.zsh"
    shell = Pty(["zsh", "-f", "-i"], env, work)
    shell.send(
        "PROMPT='' RPROMPT=''; unsetopt beep; autoload -Uz compinit; compinit -u -d $HOME/.zcompdump; "
        f"source {shlex.quote(str(script))}; zstyle ':completion:*' list-packed false; "
        "zle-line-init() { print -n '<ZLE''-READY>' }; zle -N zle-line-init; echo READY''\r"
    )
    shell.until("READY\r\n")
    results = []
    for n, (case, _) in enumerate(CASES):
        line, extra = split_case(case)
        exports = "".join(f"export {k}={v}; " for k, v in extra.items()) or "unset FROB_STYLE; "
        shell.send(f"{exports}echo BEGIN{n}''\r")
        shell.until(f"BEGIN{n}\r\n")
        # Typed before the line editor reads, while the terminal still
        # reads whole lines, Ctrl-D would be taken as end of input, so
        # wait for it, and a moment more.
        shell.until(ZLE_READY)
        time.sleep(0.2)
        # List the completions, then clear the line.
        shell.send(line + "\x04")
        time.sleep(1.0)
        shell.send("\x15" + f"echo END{n}''\r")
        text = ANSI.sub("", shell.until(f"END{n}\r\n"))
        found = []
        for row in text.replace("\r", "").split("\n"):
            if not row.strip() or line.strip() in row or "echo END" in row or ZLE_READY in row:
                continue
            # `value  -- description` from _describe, or columns of values.
            found.extend(row.split(" -- ")[0].split())
        # zsh lists paths without the part of the word the script keeps
        # in front of them (`--out=` in `--out=g`), as it does for any
        # command, though it completes the whole word.
        word = "" if line.endswith(" ") else line.split()[-1]
        kept = re.match(r"(.*?[=:])", word)
        if kept:
            found = [f if f.startswith(kept[1]) else kept[1] + f for f in found]
        results.append(found)
    shell.close()
    return results


def drive_fish(work, env):
    script = work.parent / "frob.fish"
    results = []
    for case, _ in CASES:
        line, extra = split_case(case)
        command = f"source {shlex.quote(str(script))}; complete -C {shlex.quote(line)}"
        out = subprocess.run(
            ["fish", "--no-config", "-c", command], env={**env, **extra}, cwd=work,
            capture_output=True, text=True, timeout=60,
        )
        results.append([row.split("\t")[0] for row in out.stdout.splitlines()])
    return results


def drive_powershell(work, env):
    script = work.parent / "frob.ps1"
    results = []
    for case, _ in CASES:
        line, extra = split_case(case)
        command = (
            f". '{script}'; "
            "(TabExpansion2 -inputScript $env:LINE -cursorColumn $env:LINE.Length).CompletionMatches"
            " | ForEach-Object { $_.CompletionText }"
        )
        out = subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
            env={**env, **extra, "LINE": line}, cwd=work, capture_output=True, text=True, timeout=60,
        )
        results.append(out.stdout.splitlines())
    return results


DRIVERS = {"bash": drive_bash, "zsh": drive_zsh, "fish": drive_fish, "powershell": drive_powershell}
EXTENSIONS = {"bash": "bash", "zsh": "zsh", "fish": "fish", "powershell": "ps1"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-build", action="store_true", help="use temper.out/py as it is")
    parser.add_argument("--require", action="store_true", help="fail when a shell isn't installed")
    parser.add_argument("shells", nargs="*", metavar="SHELL", help=", ".join(SHELLS))
    options = parser.parse_args()
    shells = options.shells or list(SHELLS)
    unknown = set(shells) - set(SHELLS)
    if unknown:
        parser.error(f"unknown: {', '.join(sorted(unknown))}")
    if not options.no_build:
        temper = os.environ.get("TEMPER", "temper")
        subprocess.run([temper, "build", "-b", "py"], cwd=ROOT, check=True)

    failed = False
    with tempfile.TemporaryDirectory(prefix="argmas-shells-") as tmp:
        # Scripts and `frob` in tmp, files to complete in tmp/work, and
        # HOME in tmp/home, where shells keep their own files.
        bin_dir = Path(tmp)
        work = bin_dir / "work"
        work.mkdir()
        home = bin_dir / "home"
        home.mkdir()
        path = os.pathsep.join(str(OUT / name) for name in ("argmas", "temper-core", "std"))
        if WINDOWS:
            # write_text ends lines with CRLF there.
            frob = bin_dir / "frob.cmd"
            frob.write_text(f'@echo off\nset "PYTHONPATH={path}"\n"{sys.executable}" "{HERE / "frob.py"}" %*\n')
        else:
            frob = bin_dir / "frob"
            frob.write_text(
                "#!/bin/sh\n"
                f"PYTHONPATH={shlex.quote(path)} exec {shlex.quote(sys.executable)} "
                f"{shlex.quote(str(HERE / 'frob.py'))} \"$@\"\n"
            )
            frob.chmod(0o755)
        (work / "alpha.txt").write_text("")
        (work / "gamma.txt").write_text("")
        (work / "beta").mkdir()
        (bin_dir / "inputrc").write_text("set bell-style none\nset enable-bracketed-paste off\n")
        # Windows programs need some of the system's variables, such as
        # SystemRoot, so they're kept there.
        env = {
            **(os.environ if WINDOWS else {}),
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "TERM": "dumb",
            "LANG": "C.UTF-8",
        }
        for shell in shells:
            program = SHELLS[shell]
            if shutil.which(program) is None:
                print(f"{shell}: skipped, {program} isn't installed")
                failed = failed or options.require
                continue
            script = subprocess.run(
                [str(frob), "--completions", shell], env=env, capture_output=True, text=True, check=True
            ).stdout
            (bin_dir / f"frob.{EXTENSIONS[shell]}").write_text(script)
            try:
                results = DRIVERS[shell](work, env)
            except (RuntimeError, OSError, subprocess.SubprocessError) as error:
                print(f"{shell}: error: {error}")
                failed = True
                continue
            bad = 0
            for (case, expected), got in zip(CASES, results):
                if normalized(got) != sorted(expected):
                    bad += 1
                    print(f"{shell}: {case!r}: expected {sorted(expected)}, got {normalized(got)}")
            print(f"{shell}: {len(CASES) - bad} of {len(CASES)} cases match")
            failed = failed or bad > 0
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
