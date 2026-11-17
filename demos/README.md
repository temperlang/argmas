# Demos

## Tour

`tour/` has the same small program in each supported language: `pack`,
an archiver's command line, with a flag every subcommand takes
(`--verbose`), a subcommand with an option that has a default and an
environment variable (`--level`), an option with choices (`--mode`),
and positional arguments, and a second subcommand with an alias. Each
parses its real arguments, prints the values it got, prints help and
the version when asked, and prints mistakes to standard error with exit
status 2. [docs/languages.md](../docs/languages.md) says what the API
looks like in each language.

`run.py` runs each one with the command lines in its `CASES` and
compares the transcript with `tour/expected.txt`, so the tours double
as a cross-language test of parsing, help, and errors.

Beside each tour, `examples` (`examples.py`, `examples.cpp`, and so on;
C#'s is the project in `csharp/examples/`, Rust's
`src/site_examples.rs`) holds the
[site](https://temperlang.github.io/argmas/)'s section examples, each
between `snippet:` comments, built with the tour. `run.py` runs it too
and compares what it prints with `tour/examples.txt`.

First build the libraries from the repo's top, with
[Temper](https://temperlang.dev/):

    temper build -b cpp -b csharp -b java -b js -b lua -b py -b rust

Each tour uses the generated library in `temper.out/` by relative path.
Build and run one from its directory:

| Language | In `tour/…` | Commands |
|---|---|---|
| C++ | `cpp` | `cmake -B build && cmake --build build --target tour && ./build/tour add -v out.pack a.txt` |
| C# | `csharp` | `dotnet run -- add -v out.pack a.txt` |
| Java | `java` | `./gradlew installDist && build/install/tour/bin/tour add -v out.pack a.txt` |
| JavaScript | `js` | `npm ci && node tour.js add -v out.pack a.txt` |
| Lua | `lua` | `lua -l paths tour.lua add -v out.pack a.txt` |
| Python | `py` | `uv run tour.py add -v out.pack a.txt` |
| Rust | `rust` | `cargo run -- add -v out.pack a.txt` |

Or run them all and compare each with `expected.txt`:

    uv run demos/run.py [LANGUAGE ...]

CI does the same for each backend, after its tests.

C++ builds Argmas with the CMake project Temper generates. Java's
Gradle build compiles the generated sources along with the tour, so the
generated Maven projects needn't be installed first. Python's tour
names Temper's runtime as a dependency too, so it comes from
`temper.out/`, not from older releases on PyPI.
