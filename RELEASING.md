# Releasing Argmas

A `v` tag makes a release: [release.yml](.github/workflows/release.yml)
builds every language's package, with Temper's runtime (`temper-core`)
and std at the pinned compiler's version (`TEMPEST_COMMIT`, the same as
test.yml's), and attaches them and `SHA256SUMS` to a GitHub release,
marked a pre-release while Temper's libraries are beta. Nothing goes to
a package registry. The README's [Releases](README.md#releases) section
says what each file is and how to install it.

## Cutting a release

1. Set the version in [src/config.temper.md](src/config.temper.md),
   `export let version = "0.2.0";`, as MAJOR.MINOR.PATCH, and merge
   that to main with CI green.
2. Optionally, do a dry run (below) on main.
3. Tag main's commit and push the tag:

       git tag -a v0.2.0 -m "Argmas 0.2.0"
       git push origin v0.2.0

The tag must be `v` and the config's version, or the run stops at its
first job (`check`); a tag not on main only warns. Check locally first
with:

    python3 .github/release.py check v0.2.0

To redo a failed release, fix it on main, delete the GitHub release if
one was made and the tag (`git push origin :v0.2.0`), and tag again.

## Dry run

Run the workflow by hand: Actions, release, Run workflow, on a branch
(or `gh workflow run release.yml --ref BRANCH`). It builds and checks
the same files, then uploads them as the run's artifact,
`argmas-VERSION`, kept for 14 days, and makes no release.

Locally, with a `temper` built at `TEMPEST_COMMIT`, Java 8 as a Maven
toolchain, and uv, npm, and Maven:

    python3 .github/release.py assets --temper "$(which temper)" --out dist
    python3 .github/release.py smoke dist

`assets` builds into a temporary directory, not `temper.out`;
`--only py,js` limits it to some languages. `smoke` installs the
Python and JavaScript packages from those files alone and runs the
tour with each.

## What depends on the compiler

The runtimes take the compiler's version, so a dev build of Temper
(`0.7.0-alpha.0.239`) gives dev-build runtimes, which their package
files mark unpublishable. C#'s can't be packed at all then, so a
release has the C# projects' sources, and NuGet packages only when the
compiler is a Temper release. Rust's, Lua's, and C++'s packages are
source archives for now: Cargo can't pack Argmas against an unpublished
`temper-core`, and Temper's rockspecs don't yet install modules that
`require` finds.
