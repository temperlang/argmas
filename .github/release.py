# /// script
# requires-python = ">=3.11"
# ///
"""The release workflow's steps (.github/workflows/release.yml), which
RELEASING.md describes. Standard library only, so plain `python3` runs
it too.

    release.py check [TAG]
    release.py assets --temper PATH --out DIR [--only py,js,...]
    release.py smoke DIR

`check` prints `version=` (the library's version, from
src/config.temper.md) and `compiler=` (TEMPEST_COMMIT, which must be
the same in test.yml and release.yml) for $GITHUB_OUTPUT. Given a tag,
it fails unless the tag is `v` and that version.

`assets` builds Argmas for every backend with that temper and packs
each language's package, with the runtime (temper-core) and std at the
compiler's version, into DIR, flat, then writes SHA256SUMS:

- Python: a wheel and an sdist each, by `uv build` (hatchling)
- JavaScript: npm tarballs, by `npm pack`
- Java: one Maven repository zip, the layout of ~/.m2/repository, with
  each artifact's pom, jar, sources, and javadoc
- C#: a source zip of the three projects; and NuGet packages, but only
  when the compiler is a release, as a dev build's runtime refuses
  packing (IsPackable)
- Rust, Lua, and C++: a source tarball of the three directories, as
  `temper build` writes them; Cargo can't pack against an unpublished
  temper-core, and generated rockspecs don't yet install modules
  `require` finds

It checks that every package file names the library's version, and
fails at the end naming each problem.

`smoke` installs the Python and JavaScript packages from DIR alone, in
a scratch venv and npm project, and runs the tour's first case
(demos/tour/expected.txt) with each.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "config.temper.md"
WORKFLOWS = ROOT / ".github" / "workflows"
NAME = "argmas"
LANGUAGES = ("cpp", "csharp", "java", "js", "lua", "py", "rust")
# Each language's libraries, as `temper build` names their directories.
LIBRARIES = (NAME, "temper-core", "std")
# Beside the libraries in each source archive.
LEGAL = ("COPYRIGHT", "LICENSE-APACHE", "LICENSE-MIT", "NOTICE")
# Build output and test leftovers, kept out of source archives.
JUNK = {"bin", "obj", "target", "build", "node_modules", "__pycache__", "test-results.xml"}
# Build dependencies for the wheels and sdists, at exact versions.
PY_BUILD_CONSTRAINTS = "hatchling==1.27.0\n"
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z")


def library_version() -> str:
    m = re.search(r'^\s*export let version = "([^"]*)";', CONFIG.read_text(), re.M)
    if not m:
        raise ValueError(f"{CONFIG.relative_to(ROOT)}: no `export let version = \"...\";`")
    if not VERSION.match(m.group(1)):
        raise ValueError(
            f"{CONFIG.relative_to(ROOT)}: version {m.group(1)!r} isn't MAJOR.MINOR.PATCH, "
            "which every ecosystem spells the same"
        )
    return m.group(1)


def tempest_commit(workflow: Path) -> str:
    m = re.search(r"^\s*TEMPEST_COMMIT:\s*([0-9a-f]{40})\s*$", workflow.read_text(), re.M)
    if not m:
        raise ValueError(f"{workflow.name}: no TEMPEST_COMMIT")
    return m.group(1)


def check(tag: str | None) -> dict[str, str]:
    version = library_version()
    if tag is not None and tag != f"v{version}":
        raise ValueError(
            f"{tag}: the library's version (src/config.temper.md) is {version}; "
            f"tag v{version}, or change the version first"
        )
    test, release = (tempest_commit(WORKFLOWS / f) for f in ("test.yml", "release.yml"))
    if test != release:
        raise ValueError(f"TEMPEST_COMMIT differs: {test} in test.yml, {release} in release.yml")
    return {"version": version, "compiler": test}


def run(*args: str | Path, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    print("+", " ".join(str(a) for a in args), flush=True)
    program = shutil.which(str(args[0])) or str(args[0])
    out = subprocess.run(
        [program, *map(str, args[1:])],
        cwd=cwd,
        env={**os.environ, **(env or {})},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(out.stdout, end="", flush=True)
    if out.returncode != 0:
        raise RuntimeError(f"{args[0]} exited with {out.returncode}")
    return out.stdout


def source_archive(build: Path, language: str, version: str, out: Path, zip: bool = False) -> None:
    """The three libraries' directories under `argmas-LANGUAGE-VERSION/`,
    with Argmas's license files, in a stable order with fixed times."""
    top = f"{NAME}-{language}-{version}"
    files: list[tuple[Path, str]] = [(ROOT / f, f"{top}/{f}") for f in LEGAL]
    for library in LIBRARIES:
        base = build / language
        for file in sorted((base / library).rglob("*")):
            parts = file.relative_to(base).parts
            if file.is_file() and not JUNK.intersection(parts):
                files.append((file, f"{top}/{'/'.join(parts)}"))
    if zip:
        with zipfile.ZipFile(out / f"{top}.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for file, name in files:
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, file.read_bytes())
    else:
        with tarfile.open(out / f"{top}.tar.gz", "w:gz") as t:
            for file, name in files:
                info = t.gettarinfo(file, name)
                info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
                info.mode = 0o644
                with open(file, "rb") as f:
                    t.addfile(info, f)


def py(build: Path, out: Path, version: str, release: bool) -> list[str]:
    constraints = build / "py-build-constraints.txt"
    constraints.write_text(PY_BUILD_CONSTRAINTS)
    for library in LIBRARIES:
        run(
            "uv", "build", "--sdist", "--wheel", "--no-config",
            "--build-constraints", constraints, "--out-dir", out,
            cwd=build / "py" / library,
        )
    for junk in out.glob(".gitignore"):
        junk.unlink()
    return []


def js(build: Path, out: Path, version: str, release: bool) -> list[str]:
    for library in LIBRARIES:
        run("npm", "pack", "--pack-destination", out, cwd=build / "js" / library)
    return []


def java(build: Path, out: Path, version: str, release: bool) -> list[str]:
    """One zip in Maven's repository layout: each artifact's pom, jar,
    sources, and javadoc, which unzip into ~/.m2/repository or serve as
    a `file:` repository."""
    # A local repository of its own, so these builds don't land in
    # ~/.m2 beside others of the same version. temper-core's pom asks
    # for a JDK 8 toolchain (~/.m2/toolchains.xml, `<version>8</version>`).
    repo = build / "maven-repository"
    mvn = ["mvn", "-B", "-ntp", "-Dgpg.skip", "-Dmaven.test.skip=true", f"-Dmaven.repo.local={repo}"]
    run(*mvn, "install", cwd=build / "java" / "temper-core")
    run(*mvn, "install", cwd=build / "java" / "std")
    run(*mvn, "package", cwd=build / "java" / NAME)
    files: list[tuple[Path, str]] = []
    for library in LIBRARIES:
        project = build / "java" / library
        pom = (project / "pom.xml").read_text()
        group = re.search(r"<groupId>([^<]+)</groupId>", pom).group(1)
        artifact = re.search(r"<artifactId>([^<]+)</artifactId>", pom).group(1)
        artifact_version = re.search(r"<version>([^<]+)</version>", pom).group(1)
        dir = "/".join([*group.split("."), artifact, artifact_version])
        stem = f"{artifact}-{artifact_version}"
        files.append((project / "pom.xml", f"{dir}/{stem}.pom"))
        for want in [f"{stem}.jar", f"{stem}-sources.jar", f"{stem}-javadoc.jar"]:
            jar = project / "target" / want
            if not jar.is_file():
                raise RuntimeError(f"Maven: no {want} in {project / 'target'}")
            files.append((jar, f"{dir}/{want}"))
    with zipfile.ZipFile(out / f"{NAME}-java-{version}-maven.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for file, name in files:
            data = file.read_bytes()
            for suffix, digest in [("", None), (".md5", hashlib.md5), (".sha1", hashlib.sha1)]:
                info = zipfile.ZipInfo(name + suffix, (1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data if digest is None else digest(data).hexdigest())
    return []


def csharp(build: Path, out: Path, version: str, release: bool) -> list[str]:
    source_archive(build, "csharp", version, out, zip=True)
    if not release:
        return ["NuGet packages: a dev build's runtime isn't packable (IsPackable), so only the source zip"]
    env = {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}
    for project in ["temper-core/TemperLang.Core.csproj", "std/src/TemperLang.Std.csproj", f"{NAME}/src/Argmas.csproj"]:
        run("dotnet", "pack", build / "csharp" / project, "-c", "Release", "-o", out, env=env)
    return []


def archive_only(language: str):
    def pack(build: Path, out: Path, version: str, release: bool) -> list[str]:
        source_archive(build, language, version, out)
        return []
    return pack


PACK = {
    "py": py,
    "js": js,
    "java": java,
    "csharp": csharp,
    "rust": archive_only("rust"),
    "lua": archive_only("lua"),
    "cpp": archive_only("cpp"),
}

# Where each package file names the library's version.
VERSION_SPOTS = {
    "py": ("pyproject.toml", r'^version = "{v}"$'),
    "js": ("package.json", r'^\s*"version": "{v}",?$'),
    "java": ("pom.xml", r"^  <version>{v}</version>$"),
    "csharp": ("src/Argmas.csproj", r"<Version>{v}</Version>"),
    "rust": ("Cargo.toml", r'^version = "{v}"$'),
    "lua": (f"{NAME}-{{v}}-1.rockspec", r"^version = '{v}-1'$"),
    "cpp": ("CMakeLists.txt", r"^project\({n} VERSION {v} "),
}


def version_problems(build: Path, version: str, languages: list[str]) -> list[str]:
    problems = []
    for language in languages:
        file, pattern = VERSION_SPOTS[language]
        path = build / language / NAME / file.format(v=version)
        text = path.read_text() if path.is_file() else ""
        if not re.search(pattern.format(v=re.escape(version), n=NAME), text, re.M):
            problems.append(f"{language}: {path.relative_to(build)} doesn't name version {version}")
    return problems


def assets(temper: Path, out: Path, only: list[str]) -> int:
    version = library_version()
    said = run(temper, "--version").split()
    compiler = said[1] if len(said) > 1 else ""
    # A dev build or pre-release of the compiler, whose runtimes refuse
    # publishing (and C#'s, packing).
    release = bool(VERSION.match(compiler))
    out.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    problems: list[str] = []
    notes: list[str] = []
    with tempfile.TemporaryDirectory(prefix="argmas-release-") as temp:
        build = Path(temp) / "build"
        backends = [arg for language in only for arg in ("-b", language)]
        try:
            run(temper, "build", "-w", ROOT, "-o", build, *backends)
        except RuntimeError as e:
            print(f"release.py: temper build: {e}", file=sys.stderr)
            return 1
        problems += version_problems(build, version, only)
        for language in only:
            try:
                notes += PACK[language](build, out, version, release)
            except Exception as e:
                problems.append(f"{language}: {e}")
    sums = out / "SHA256SUMS"
    files = sorted(f for f in out.iterdir() if f.is_file() and f != sums)
    sums.write_text("".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in files))
    print(f"\nArgmas {version}, with Temper {compiler}'s runtimes, in {out}:")
    for file in files:
        print(f"  {file.stat().st_size:>9}  {file.name}")
    for note in notes:
        print(f"Left out: {note}")
    for problem in problems:
        print(f"release.py: {problem}", file=sys.stderr)
    return 1 if problems else 0


def first_case() -> tuple[list[str], str]:
    """The tour's first case, its arguments and its standard output."""
    lines = (ROOT / "demos" / "tour" / "expected.txt").read_text().splitlines()
    command = shlex.split(lines[0].removeprefix("$ "))
    if command[0] != "pack":
        raise ValueError(f"expected.txt: the first case isn't a plain `pack` command: {lines[0]}")
    end = lines.index("(exit status 0)")
    return command[1:], "".join(line + "\n" for line in lines[1:end])


def smoke(dist: Path) -> int:
    args, expected = first_case()
    tour = ROOT / "demos" / "tour"
    version = library_version()
    problems = []
    with tempfile.TemporaryDirectory(prefix="argmas-smoke-") as temp:
        temp = Path(temp)
        try:
            # Python, from the wheels alone.
            venv = temp / "venv"
            run("uv", "venv", venv)
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run("uv", "pip", "install", "--python", python, "--no-index", "--find-links", dist, f"{NAME}=={version}")
            shutil.copy(tour / "py" / "tour.py", temp / "tour.py")
            got = run(python, "-I", temp / "tour.py", *args, cwd=temp)
            if got != expected:
                problems.append(f"py: the tour printed {got!r}, not {expected!r}")
        except RuntimeError as e:
            problems.append(f"py: {e}")
        try:
            # JavaScript, from the tarballs alone.
            project = temp / "js"
            project.mkdir()
            (project / "package.json").write_text(json.dumps({"private": True, "type": "module"}))
            tarballs = sorted(str(p) for p in dist.glob("*.tgz"))
            run("npm", "install", "--offline", "--no-audit", "--no-fund", *tarballs, cwd=project)
            shutil.copy(tour / "js" / "tour.js", project / "tour.js")
            got = run("node", "tour.js", *args, cwd=project)
            if got != expected:
                problems.append(f"js: the tour printed {got!r}, not {expected!r}")
        except RuntimeError as e:
            problems.append(f"js: {e}")
    for problem in problems:
        print(f"release.py: {problem}", file=sys.stderr)
    if not problems:
        print("release.py: the Python and JavaScript packages install and run the tour")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="the library's version, checked against a tag")
    c.add_argument("tag", nargs="?")
    a = sub.add_parser("assets", help="build and pack every language's package")
    a.add_argument("--temper", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--only", default=",".join(LANGUAGES), help="comma-separated, of " + ", ".join(LANGUAGES))
    s = sub.add_parser("smoke", help="install the Python and JavaScript packages and run the tour")
    s.add_argument("dist", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "check":
            for key, value in check(args.tag).items():
                print(f"{key}={value}")
            return 0
        if args.command == "smoke":
            return smoke(args.dist.resolve())
    except ValueError as e:
        print(f"release.py: {e}", file=sys.stderr)
        return 1
    only = [language for language in args.only.split(",") if language]
    unknown = [language for language in only if language not in LANGUAGES]
    if unknown:
        parser.error(f"--only: unknown {', '.join(unknown)}")
    return assets(args.temper.resolve(), args.out, only)


if __name__ == "__main__":
    sys.exit(main())
